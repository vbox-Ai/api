# -*- coding: utf-8 -*-
"""
目标站: 323影视 (323433ssdfd.top)
站点类型: Vue.js SPA + Protobuf API
功能: 首页推荐、分类、搜索、详情、播放
版本: V4.1 - 修复 dr_py 环境兼容性

V4.1 关键修复:
  [修复] 1. 类名使用 Spider（dr_py 按模块名+类名注册源）
  [修复] 2. _api_get 增加 urllib 兜底（self.fetch 兼容性）

V4.0 关键修复:
  [致命] 1. 线路过滤: 根据 decode_status 过滤禁用线路，只显示可用播放源
  [增强] 2. 线路排序: 按 sort 字段降序排列，高优先级线路排前面
  [增强] 3. 播放降级: 解码失败时验证URL有效性，支持URL解码二次检查

V3.0 关键修复:
  [致命] 1. 播放地址解码: 纯Python实现，无需 Node.js / WASM / wasmtime
  [架构] 2. 逆向WASM签名算法: SHA-256(finger=...&id=...&nonce=...&sk=...&time=...&v=1)
  [架构] 3. 纯Python Protobuf 编码/解码
  [认证] 4. 添加 X-Client 和 web-sign 认证头
  [修复] 5. 分类列表使用 type_name 参数（非 type_id）
  [修复] 6. 播放源解析: 支持 $$$ 分隔多线路、# 分隔多集数
  [增强] 7. 多HTTP后端: urllib → curl 降级策略
  [兼容] 8. 标准库实现，TVBox环境零依赖
"""

import re
import sys
import os
import json
import time
import hashlib
import struct
import subprocess
import urllib.parse
import urllib.request

sys.path.append('..')
from base.spider import Spider as SpiderBase


class Spider(SpiderBase):
    # ================================================================
    # ★★★ 源名称（播放器/客户端里显示的名称）修改处 ① ★★★
    # 下面的 name 和 getName() 决定你在 TVBox/Pluto 里看到的源名。
    # 想改名字，直接改这两处即可，两处保持一样。
    # ================================================================
    name = "323影视"          # ← ① 改这里：源名称（有些客户端读这个）

    # ================================================================
    # ★★★ 播放线路改名映射表（key=线路代码，value=显示名） ★★★
    # 客户端只显示 value（显示名），不再显示 @@后面的代码。
    # 想改名：改 value；线路有新增：加一行 key: value。
    # ⚠️ key 是线路代码（解码要用），只能按实际情况填写/新增，不能改
    # ================================================================
    RENAME_MAP = {
        "CO4K": "4K专线",
        "co": "CO蓝光",
        "YYNB": "YY蓝光",
        "NBY": "NB蓝光",
        "qsvip": "青山蓝光",
        "BBA": "BB蓝光",
    }

    def init(self, extend=""):
        try:
            super().init(extend)
        except Exception:
            pass
        self.extend = extend
        self.site_url = "https://323433ssdfd.top"
        self.api_base = self.site_url + "/api.php/web"
        self.timeout = 15
        # API 认证头
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Referer': self.site_url + '/',
            'Accept': 'application/json',
            'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
            'X-Client': '8f3d2a1c7b6e5d4c9a0b1f2e3d4c5b6a',
            'web-sign': 'ddtvf65f3a83d6d9ad6f',
        }
        # 分类列表（与首页 API 返回一致）
        self.categories = [
            {"type_id": "1", "type_name": "电影"},
            {"type_id": "2", "type_name": "剧集"},
            {"type_id": "3", "type_name": "动漫"},
            {"type_id": "4", "type_name": "综艺"},
        ]
        # ==================== 解码常量（逆向自 WASM） ====================
        self._finger = "WF-2c064bc5b3400788f31b848849bc3a60f835423ba2dfe69d7ea93974c216e4f2"
        self._app_id = "com.web.player"
        self._app_sk = "WEB-50a8e9c84a1dc05669a692ded99a2dac46527229e607a7be15db88dbc59059d1"
        self._app_v = "1"
        self._nonce = "00000000000000000000000000000000"

    # ================================================================
    # ★★★ 源名称 修改处 ②（大部分客户端最终读的是这个方法） ★★★
    # ================================================================
    def getName(self):
        return "323影视"      # ← ② 改这里：源名称（与 name 保持一致）

    def getDependence(self):
        return []

    def isVideoFormat(self, url):
        return bool(re.search(r'\.(m3u8|mp4|flv|avi|mkv|wmv|ts|m4a|aac)(\?|$)', url, re.I))

    def manualVideoCheck(self):
        return True

    # ==================== Protobuf 编解码（纯Python实现） ====================

    @staticmethod
    def _encode_varint(value):
        """编码 protobuf varint"""
        result = bytearray()
        value = int(value)
        while value > 0x7f:
            result.append((value & 0x7f) | 0x80)
            value >>= 7
        result.append(value & 0x7f)
        return bytes(result)

    @classmethod
    def _encode_string_field(cls, field_num, value):
        """编码 protobuf string 字段 (wire type 2)"""
        encoded = value.encode('utf-8') if isinstance(value, str) else value
        tag = (field_num << 3) | 2
        return cls._encode_varint(tag) + cls._encode_varint(len(encoded)) + encoded

    @classmethod
    def _encode_varint_field(cls, field_num, value):
        """编码 protobuf varint 字段 (wire type 0)"""
        tag = (field_num << 3) | 0
        return cls._encode_varint(tag) + cls._encode_varint(value)

    @staticmethod
    def _parse_protobuf(data):
        """解析 protobuf 二进制数据，返回 {field_num: value} 字典"""
        offset = 0
        fields = {}
        while offset < len(data):
            tag = data[offset]
            field_num = tag >> 3
            wire_type = tag & 0x07
            offset += 1
            if wire_type == 0:  # varint
                value = 0
                shift = 0
                while offset < len(data) and data[offset] & 0x80:
                    value |= (data[offset] & 0x7f) << shift
                    shift += 7
                    offset += 1
                if offset < len(data):
                    value |= data[offset] << shift
                    offset += 1
                fields[field_num] = value
            elif wire_type == 2:  # length-delimited (string/bytes)
                field_len = 0
                shift = 0
                while offset < len(data) and data[offset] & 0x80:
                    field_len |= (data[offset] & 0x7f) << shift
                    shift += 7
                    offset += 1
                if offset < len(data):
                    field_len |= data[offset] << shift
                    offset += 1
                fields[field_num] = data[offset:offset + field_len].decode('utf-8', errors='replace')
                offset += field_len
            else:
                break
        return fields

    # ==================== 签名生成（纯Python实现） ====================

    def _generate_signature(self, timestamp_ms):
        """生成签名: SHA-256(finger=...&id=...&nonce=...&sk=...&time=...&v=1)"""
        sign_str = "finger={}&id={}&nonce={}&sk={}&time={}&v={}".format(
            self._finger, self._app_id, self._nonce, self._app_sk, timestamp_ms, self._app_v
        )
        return hashlib.sha256(sign_str.encode('utf-8')).hexdigest().upper()

    def _build_decode_request(self, play_url, from_str):
        """构建 protobuf 解码请求"""
        timestamp_ms = int(time.time() * 1000)
        signature = self._generate_signature(timestamp_ms)

        proto = b""
        proto += self._encode_string_field(1, play_url)       # url
        proto += self._encode_string_field(2, from_str)        # from
        proto += self._encode_varint_field(3, timestamp_ms)    # time (varint)
        proto += self._encode_string_field(4, self._nonce)    # nonce
        proto += self._encode_string_field(5, signature)      # sign
        proto += self._encode_string_field(6, self._app_id)   # aid
        proto += self._encode_varint_field(7, int(self._app_v))  # ave

        return proto

    # ==================== HTTP 工具 ====================

    def _api_get(self, path, params=None):
        """GET 请求 API（self.fetch 优先，urllib 兜底）"""
        url = self.api_base + path
        if params:
            url += "?" + urllib.parse.urlencode(params)

        # 方法1: self.fetch（dr_py 内置，兼容多种签名）
        try:
            resp = self.fetch(url, headers=self.headers, timeout=self.timeout)
            if resp and getattr(resp, 'text', None):
                return json.loads(resp.text)
        except Exception as e:
            print("[323影视] fetch 失败: {} -> {}".format(path, e))

        # 方法2: urllib.request 兜底（dr_py 环境没有 fetch 时）
        try:
            req = urllib.request.Request(url, headers=self.headers)
            with urllib.request.urlopen(req, timeout=self.timeout) as resp:
                raw = resp.read().decode('utf-8')
                return json.loads(raw)
        except Exception as e:
            print("[323影视] API请求失败: {} -> {}".format(path, e))
        return None

    def _http_post_binary(self, url, data, headers=None):
        """POST 二进制数据，返回二进制响应（多后端降级）"""
        req_headers = headers or {}
        # 方法1: urllib.request
        try:
            req = urllib.request.Request(url, data=data, headers=req_headers, method='POST')
            with urllib.request.urlopen(req, timeout=self.timeout) as resp:
                return resp.read()
        except Exception as e:
            print("[323影视] urllib POST 失败: {}".format(e))

        # 方法2: curl 子进程
        try:
            import tempfile
            with tempfile.NamedTemporaryFile(delete=False, suffix='.bin') as f:
                f.write(data)
                tmp_path = f.name
            try:
                cmd = ['curl', '-s', '--max-time', str(self.timeout), '-X', 'POST', url]
                for k, v in req_headers.items():
                    cmd.extend(['-H', '{}: {}'.format(k, v)])
                cmd.extend(['--data-binary', '@{}'.format(tmp_path)])
                result = subprocess.run(cmd, capture_output=True, timeout=self.timeout + 5)
                if result.returncode == 0 and result.stdout:
                    return result.stdout
            finally:
                try:
                    os.unlink(tmp_path)
                except Exception:
                    pass
        except Exception as e:
            print("[323影视] curl POST 失败: {}".format(e))

        return None

    # ==================== 播放地址解码（纯Python） ====================

    def _decode_url(self, play_url, from_str):
        """纯Python解码播放地址 - 无需 Node.js / WASM"""
        if not play_url or not from_str:
            return None

        try:
            # 1. 构建 protobuf 请求
            proto = self._build_decode_request(play_url, from_str)

            # 2. POST 到解码 API
            decode_url = self.api_base + "/decode/url"
            decode_headers = {
                'Content-Type': 'application/x-protobuf',
                'Accept': 'application/x-protobuf',
                'X-Client': self.headers['X-Client'],
                'web-sign': self.headers['web-sign'],
                'User-Agent': self.headers['User-Agent'],
                'Referer': self.site_url + '/',
            }
            resp_data = self._http_post_binary(decode_url, proto, decode_headers)
            if not resp_data:
                print("[323影视] 解码API无响应")
                return None

            # 3. 解析 protobuf 响应
            resp_fields = self._parse_protobuf(resp_data)
            # Field 1 (varint): code (1=成功)
            # Field 2 (string): msg
            # Field 3 (string): data (解码后的URL)
            if resp_fields.get(1) == 1 and resp_fields.get(3):
                return resp_fields[3]
            else:
                msg = resp_fields.get(2, "未知错误")
                print("[323影视] 解码失败: code={}, msg={}".format(resp_fields.get(1), msg))
        except Exception as e:
            print("[323影视] 解码异常: {}".format(e))
        return None

    # ==================== 通用工具 ====================

    @staticmethod
    def _clean_html(text):
        if not text:
            return ""
        text = re.sub(r'<[^>]+>', '', text)
        text = re.sub(r'&[a-z]+;', ' ', text)
        return text.strip()

    @staticmethod
    def _format_area(vod_area):
        if not vod_area:
            return ""
        if isinstance(vod_area, list):
            return ",".join(str(a) for a in vod_area)
        return str(vod_area)

    @staticmethod
    def _format_class(vod_class):
        if not vod_class:
            return ""
        if isinstance(vod_class, list):
            return ",".join(str(c) for c in vod_class)
        return str(vod_class)

    @staticmethod
    def _format_video_list(items):
        videos = []
        for item in items:
            vod_id = str(item.get("vod_id", ""))
            if not vod_id:
                continue
            videos.append({
                "vod_id": vod_id,
                "vod_name": item.get("vod_name", ""),
                "vod_pic": item.get("vod_pic", ""),
                "vod_remarks": item.get("vod_remarks", ""),
                "vod_year": str(item.get("vod_year", "")),
                "vod_area": Spider._format_area(item.get("vod_area")),
                "vod_actor": item.get("vod_actor", ""),
                "vod_director": item.get("vod_director", ""),
                "vod_type": Spider._format_class(item.get("vod_class")),
                "vod_score": str(item.get("vod_douban_score", "")),
            })
        return videos

    # ==================== TVBox 接口 ====================

    def homeContent(self, filter=False):
        result = {"class": self.categories, "list": [], "filters": {}}
        data = self._api_get("/index/home")
        if not data or data.get("code") != 200:
            return result

        home_data = data.get("data", {})

        # 更新分类列表
        cats = home_data.get("categories", [])
        if cats:
            self.categories = [
                {"type_id": str(c["type_id"]), "type_name": c["type_name"]}
                for c in cats
            ]
            result["class"] = self.categories

        # 收集所有分类下的推荐视频
        videos = []
        seen = set()
        for cat in cats:
            for v in cat.get("videos", []):
                vid = str(v.get("vod_id", ""))
                if vid and vid not in seen:
                    seen.add(vid)
                    videos.append({
                        "vod_id": vid,
                        "vod_name": v.get("vod_name", ""),
                        "vod_pic": v.get("vod_pic", ""),
                        "vod_remarks": v.get("vod_remarks", ""),
                    })

        result["list"] = videos[:30]
        return result

    def homeVideoContent(self):
        return self.homeContent(False)

    def categoryContent(self, tid, pg, filter=False, extend=None):
        page = int(pg) if pg else 1

        # 通过 type_id 查找 type_name
        type_name = ""
        for c in self.categories:
            if str(c["type_id"]) == str(tid):
                type_name = c["type_name"]
                break

        if not type_name:
            return {"list": [], "page": page, "pagecount": 1, "limit": 20, "total": 0}

        params = {
            "type_name": type_name,
            "page": page,
            "sort": "hits",
        }
        if extend:
            if extend.get("class"):
                params["class"] = extend["class"]
            if extend.get("area"):
                params["area"] = extend["area"]
            if extend.get("year"):
                params["year"] = extend["year"]

        data = self._api_get("/filter/vod", params)

        empty_result = {"list": [], "page": page, "pagecount": 1, "limit": 20, "total": 0}
        if not data or data.get("code") != 200:
            return empty_result

        items = data.get("data", [])
        if not isinstance(items, list):
            return empty_result

        videos = self._format_video_list(items)
        has_more = len(items) >= 18

        return {
            "list": videos,
            "page": page,
            "pagecount": page + 1 if has_more else page,
            "limit": max(len(videos), 1),
            "total": len(videos),
        }

    def detailContent(self, ids):
        vid = ids[0] if isinstance(ids, list) else ids
        if not vid:
            return {"list": []}

        data = self._api_get("/vod/get_detail", {"vod_id": str(vid)})
        if not data or data.get("code") != 200:
            return {"list": []}

        items = data.get("data", [])
        if not items or not isinstance(items, list):
            return {"list": []}

        vod = items[0]
        vodplayer = data.get("vodplayer", [])

        play_from_raw = vod.get("vod_play_from", "")
        play_url_raw = vod.get("vod_play_url", "")

        # 构建播放源信息映射: from_code -> {show, decode_status, sort}
        player_info = {}
        if isinstance(vodplayer, list):
            for p in vodplayer:
                from_code = p.get("from", "")
                if from_code:
                    player_info[from_code] = {
                        "show": p.get("show", "") or from_code,
                        "decode_status": str(p.get("decode_status", "1")),
                        "sort": float(p.get("sort", "0")) if p.get("sort") else 0,
                    }

        # 解析原始播放源和URL
        from_codes_raw = [c.strip() for c in play_from_raw.split("$$$") if c.strip()] if play_from_raw else []
        url_groups_raw = play_url_raw.split("$$$") if play_url_raw else []

        # 过滤: 只保留 decode_status=1 的线路，并按 sort 降序排列（sort值越大优先级越高）
        enabled_lines = []
        for i, from_code in enumerate(from_codes_raw):
            info = player_info.get(from_code, {})
            decode_status = info.get("decode_status", "1")
            sort_val = info.get("sort", 0)
            url_group = url_groups_raw[i] if i < len(url_groups_raw) else ""
            enabled_lines.append({
                "from_code": from_code,
                "show": info.get("show", from_code),
                "decode_status": decode_status,
                "sort": sort_val,
                "url_group": url_group,
            })

        # 先按 decode_status 优先（1在前），再按 sort 降序
        enabled_lines.sort(key=lambda x: (x["decode_status"] != "1", -x["sort"]))

        # 如果全部禁用，保留全部（降级显示，至少用户能看到内容）
        has_enabled = any(l["decode_status"] == "1" for l in enabled_lines)
        if has_enabled:
            enabled_lines = [l for l in enabled_lines if l["decode_status"] == "1"]

        # ================================================================
        # ★★★ 播放线路名称 修改处 ③ ★★★
        # 线路名显示：只返回显示名（RENAME_MAP 里的 value），
        # 不带 @@代码 —— 代码通过 playerContent 里的反向映射还原，不影响播放。
        # ================================================================
        display_parts = []
        url_parts = []
        for line in enabled_lines:
            # 统一改名：优先按线路代码匹配，其次按原名匹配，都没有就保留原名
            show_name = self.RENAME_MAP.get(line["from_code"]) or self.RENAME_MAP.get(line["show"]) or line["show"]
            display_parts.append(show_name)      # 只显示名，不带 @@代码
            url_parts.append(line["url_group"])

        vod_play_from = "$$$".join(display_parts)
        vod_play_url = "$$$".join(url_parts)

        content = self._clean_html(vod.get("vod_content", ""))

        result_vod = {
            "vod_id": str(vod.get("vod_id", vid)),
            "vod_name": vod.get("vod_name", ""),
            "vod_pic": vod.get("vod_pic", ""),
            "vod_content": content,
            "vod_year": str(vod.get("vod_year", "")),
            "vod_area": self._format_area(vod.get("vod_area")),
            "vod_actor": vod.get("vod_actor", ""),
            "vod_director": vod.get("vod_director", ""),
            "vod_remarks": vod.get("vod_remarks", ""),
            "vod_class": self._format_class(vod.get("vod_class")),
            "vod_play_from": vod_play_from,
            "vod_play_url": vod_play_url,
        }

        return {"list": [result_vod]}

    def searchContent(self, key, quick=False, pg="1"):
        page = int(pg) if pg else 1

        data = self._api_get("/search/index", {
            "wd": key,
            "page": page,
            "limit": 15,
        })

        if not data or data.get("code") != 200:
            return {"list": [], "page": page, "pagecount": 1}

        items = data.get("data", [])
        if not isinstance(items, list):
            return {"list": [], "page": page, "pagecount": 1}

        videos = self._format_video_list(items)
        pagecount = page + 1 if len(items) >= 15 else page

        return {"list": videos, "page": page, "pagecount": pagecount}

    def _resolve_from_code(self, flag):
        """从 flag 反查线路代码（兼容三种格式）
        - "显示名@@from_code" → 取 @@ 后面的代码
        - 纯显示名（如"4K专线"）→ 在 RENAME_MAP 里反查代码
        - 纯代码（如"CO4K"）  → 直接用
        """
        if not flag:
            return ""
        flag = flag.strip()
        # 格式1: 显示名@@代码
        if "@@" in flag:
            return flag.split("@@")[-1].strip()
        # 格式2: 纯显示名 → 反查 RENAME_MAP
        for code, name in self.RENAME_MAP.items():
            if flag == name:
                return code
        # 格式3: 直接当代码用（没在映射表里的线路）
        return flag

    def playerContent(self, flag, id, vipFlags=None):
        """获取播放地址"""
        play_url = (id.strip() if id else "").strip()
        play_url = urllib.parse.unquote(play_url) if play_url else ""

        # 如果已经是直链（http开头的m3u8/mp4等），直接返回
        if play_url and re.match(r'^https?://', play_url, re.I):
            return {
                "parse": 0,
                "url": play_url,
                "header": {
                    "User-Agent": self.headers["User-Agent"],
                    "Referer": self.site_url + "/"
                }
            }

        # 从 flag 中提取 from_code
        # flag 可能是: "显示名@@from_code" / 纯显示名 / 纯 from_code
        from_code = self._resolve_from_code(flag)

        # 纯Python解码播放地址
        if play_url and from_code:
            decoded_url = self._decode_url(play_url, from_code)
            if decoded_url:
                # 验证解码后的URL是否为有效链接
                if re.match(r'^https?://', decoded_url, re.I):
                    return {
                        "parse": 0,
                        "url": decoded_url,
                        "header": {
                            "User-Agent": self.headers["User-Agent"],
                            "Referer": self.site_url + "/"
                        }
                    }
                # 解码返回了非链接（可能是错误消息），尝试 URL 解码后再次检查
                decoded_url_2 = urllib.parse.unquote(decoded_url)
                if re.match(r'^https?://', decoded_url_2, re.I):
                    return {
                        "parse": 0,
                        "url": decoded_url_2,
                        "header": {
                            "User-Agent": self.headers["User-Agent"],
                            "Referer": self.site_url + "/"
                        }
                    }

        # 降级：返回原始 URL 让播放器尝试解析
        return {
            "parse": 1,
            "url": play_url or self.site_url,
            "header": {
                "User-Agent": self.headers["User-Agent"],
                "Referer": self.site_url + "/"
            }
        }

    def localProxy(self, param):
        return None
