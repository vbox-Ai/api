#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
星影 TVBox Python 爬虫
站点: http://43.248.128.122:8080/
框架: FongMi TV Python (fengmiTV / OK影视 / webhome 兼容)
API: 自定义 Nuxt.js SSR 后端 (/api/*)

API 结构:
  GET  /api/categories        分类列表 (type_extend 内含 class 筛选)
  GET  /api/videos?t=&page=&limit=&class=&area=&year=&by=   分类视频列表
  GET  /api/videos/{vod_id}   视频详情 (含 play_list)
  GET  /api/search?wd=&page=&limit=   搜索
  GET  /api/home/sections     首页栏目
  POST /api/parse             播放解析 (body: {url, from}, 访客模式 3 次免费)
                               返回 {url, player_type} (0=直链, 1=iframe嗅探)
                               游客额度用尽(code=40311)时自动换 Device ID 重置额度
  POST /api/auth/login-password  会员登录 (body: {phone, password}) -> access_token + refresh_token
  POST /api/auth/refresh         刷新 token (body: {refresh_token}) -> 新 access_token

认证策略 (三层 fallback):
  1. 会员模式: ext 传 {"phone":"x","password":"x"} 自动登录, token 过期自动刷新
  2. 游客模式: 无需配置, 3 次/设备, 用尽自动换 Device ID
  3. 会员失败 -> 自动降级到游客模式

播放源标识:
  rose=超清(需/api/parse解码)  co=备用(需/api/parse解码)
  qq=腾讯  qiyi=爱奇艺  youku=优酷  bilibili=哔哩哔哩 (直链平台URL, parse=1嗅探)

vbox iOS 适配:
  - 覆写 fetch 方法, urllib + ssl._create_unverified_context() 解决 iOS CA 证书缺失
  - init 参数名统一为 extend (PythonSpiderEngine 调用约定)
  - 多域名并发探测, 选最快响应, 10 分钟冷却缓存
  - homeContent 始终返回 filters
  - 关键路径 print 日志, 便于悬浮窗诊断
"""

import sys
import json
import re
import time
import datetime
import urllib.parse
import urllib.request
import urllib.error
import uuid
import ssl

sys.path.append("..")

# ---- iOS CPython SSL 适配: 无系统 CA 证书, 创建不验证上下文 ----
_ssl_ctx = ssl._create_unverified_context()

# ---- 沙箱兜底: base.spider 不存在时用 object 兜底 ----
try:
    from base.spider import Spider as _BaseSpider
except ImportError:
    _BaseSpider = object


# ---- 通用 Response 包装类 (兼容 requests 风格) ----
class _Response:
    def __init__(self, data, status_code=200, encoding="utf-8", headers=None):
        self._data = data
        self.status_code = status_code
        self.encoding = encoding
        self.headers = headers or {}
        self._text = None
        self.url = ""

    @property
    def text(self):
        if self._text is None:
            try:
                self._text = self._data.decode(self.encoding or "utf-8", errors="replace")
            except Exception:
                self._text = ""
        return self._text

    def json(self):
        return json.loads(self.text)


# ---- 常量 ----
DEFAULT_BASE_URL = "http://43.248.128.122:8080"

# 备用域名列表 (目前只有主域名, 后续添加备用域名直接在此扩展)
_BACKUP_HOSTS = [
    "http://43.248.128.122:8080",
]

_HOST_CACHE_TTL = 600  # 域名探测冷却时间: 10 分钟

UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")

SOURCE_NAMES = {
    "rose": "超清",
    "qq": "腾讯视频",
    "co": "备用线路",
    "qiyi": "爱奇艺",
    "youku": "优酷",
    "bilibili": "哔哩哔哩",
    "duanju": "短剧",
    "zijianm3u8": "自建",
}

SNIFF_DOMAINS = [
    "v.qq.com", "iqiyi.com", "youku.com", "bilibili.com",
    "mgtv.com", "le.com", "sohu.com", "pptv.com",
    "1905.com", "wasu.cn", "fun.tv", "baidu.com",
]

AREAS = [
    {"n": "全部", "v": ""},
    {"n": "中国大陆", "v": "中国大陆"},
    {"n": "内地", "v": "内地"},
    {"n": "中国香港", "v": "中国香港"},
    {"n": "中国台湾", "v": "中国台湾"},
    {"n": "美国", "v": "美国"},
    {"n": "日本", "v": "日本"},
    {"n": "韩国", "v": "韩国"},
    {"n": "英国", "v": "英国"},
    {"n": "法国", "v": "法国"},
    {"n": "印度", "v": "印度"},
    {"n": "其他", "v": "其他"},
]

SORTS = [
    {"n": "最新", "v": "time"},
    {"n": "最热", "v": "hits"},
    {"n": "评分", "v": "score"},
]

# 播放源排序优先级 (数字越小越靠前, 4K/超清优先)
SOURCE_PRIORITY = {
    "rose": 1,
    "duanju": 2,
    "co": 3,
    "zijianm3u8": 4,
    "qq": 5,
    "qiyi": 6,
    "youku": 7,
    "bilibili": 8,
}

LIVE_CATEGORIES = [
    {"n": "全部", "v": ""},
    {"n": "央视频道", "v": "央视频道"},
    {"n": "卫视频道", "v": "卫视频道"},
    {"n": "附加地方频道", "v": "附加地方频道"},
]

LIVE_TID = "live"


class Spider(_BaseSpider):

    # ==================== vbox 适配: HTTP 层 (覆写 base.spider.fetch) ====================

    def fetch(self, url, headers=None, data=None, timeout=15):
        """发起 HTTP 请求 — 覆写 base.spider.fetch
        使用 urllib + ssl._create_unverified_context() 解决 iOS CPython CA 证书缺失
        返回兼容 requests 风格的 _Response 对象
        """
        req_headers = dict(headers) if headers else {}
        try:
            req = urllib.request.Request(url, headers=req_headers, data=data)
            r = urllib.request.urlopen(req, timeout=timeout, context=_ssl_ctx)
            raw = r.read()
            resp_headers = r.headers if hasattr(r, "headers") else None
            encoding = "utf-8"
            if resp_headers and hasattr(resp_headers, "get_content_charset"):
                ce = resp_headers.get_content_charset()
                if ce:
                    encoding = ce
            resp = _Response(raw, status_code=r.status, encoding=encoding, headers=resp_headers)
            resp.url = getattr(r, "url", url)
            return resp
        except urllib.error.HTTPError as e:
            raw = b""
            try:
                raw = e.read()
            except Exception:
                pass
            resp_headers = e.headers if hasattr(e, "headers") else None
            resp = _Response(raw, status_code=e.code, encoding="utf-8", headers=resp_headers)
            resp.url = url
            return resp
        except Exception as e:
            print("[星影4K] fetch 异常: %s, url=%s" % (e, url[:120]))
            raise

    def post(self, url, headers=None, data=None, timeout=15):
        return self.fetch(url, headers=headers, data=data, timeout=timeout)

    # ==================== vbox 适配: 多域名并发探测 ====================

    def _probe_hosts(self, hosts):
        """并发探测多个域名, 返回最快响应的域名
        探测方式: GET /api/categories, 检查 code==0
        超时: 5 秒
        """
        import concurrent.futures

        def _try(host):
            try:
                url = host.rstrip("/") + "/api/categories"
                start = time.time()
                r = self.fetch(url, headers={"User-Agent": UA, "Accept": "application/json"}, timeout=5)
                elapsed = time.time() - start
                if r.status_code == 200:
                    try:
                        d = json.loads(r.text)
                        if d.get("code") == 0:
                            print("[星影4K] 域名探测成功: %s (%.2fs)" % (host, elapsed))
                            return host
                    except Exception:
                        pass
            except Exception:
                pass
            return None

        with concurrent.futures.ThreadPoolExecutor(max_workers=len(hosts)) as pool:
            futures = {pool.submit(_try, h): h for h in hosts}
            for f in concurrent.futures.as_completed(futures):
                result = f.result()
                if result:
                    # 取消剩余任务 (Python 3.9+ cancel 不保证立即停止, 但能减少等待)
                    for f2 in futures:
                        if not f2.done():
                            f2.cancel()
                    return result
        # 全部失败, 返回第一个
        print("[星影4K] 所有域名探测失败, 使用默认: %s" % hosts[0])
        return hosts[0]

    def _ensure_base_url(self):
        """确保 base_url 可用, 带 10 分钟冷却缓存"""
        now = time.time()
        if self._effective_base_url and (now - self._last_host_check) < _HOST_CACHE_TTL:
            return self._effective_base_url

        self._last_host_check = now

        # 收集所有候选域名: 用户自定义域名优先, 然后备用域名列表
        candidates = []
        if self._user_base_url and self._user_base_url not in candidates:
            candidates.append(self._user_base_url)
        for h in _BACKUP_HOSTS:
            if h not in candidates:
                candidates.append(h)

        if len(candidates) == 1:
            # 单域名直接用, 不做探测
            self._effective_base_url = candidates[0]
            print("[星影4K] 单域名模式: %s" % candidates[0])
        else:
            # 多域名并发探测选最快
            print("[星影4K] 并发探测 %d 个域名..." % len(candidates))
            best = self._probe_hosts(candidates)
            self._effective_base_url = best

        self.base_url = self._effective_base_url
        return self._effective_base_url

    # ==================== init ====================

    def init(self, extend=""):
        """vbox PythonSpiderEngine 调用约定: 参数名为 extend"""
        self.ua = UA
        self.token = ""
        self.refresh_token = ""
        self._token_expire = 0
        self._phone = ""
        self._password = ""
        self._device_id = ""
        self._auth_failed = False

        # 用户自定义域名 (从 extend 解析)
        self._user_base_url = ""
        # 当前生效的 base_url (探测结果)
        self._effective_base_url = ""
        self._last_host_check = 0

        if extend:
            extend = extend.strip()
            if extend.startswith("http"):
                self._user_base_url = extend.rstrip("/")
            else:
                try:
                    ext_data = json.loads(extend)
                    if isinstance(ext_data, dict):
                        self.token = ext_data.get("token", "")
                        self.refresh_token = ext_data.get("refresh_token", "")
                        self._phone = ext_data.get("phone", "")
                        self._password = ext_data.get("password", "")
                        if ext_data.get("base_url"):
                            self._user_base_url = ext_data["base_url"].rstrip("/")
                except Exception:
                    self.token = extend

        self.base_url = self._user_base_url or DEFAULT_BASE_URL
        self._rotate_device()

        # 域名探测
        self._ensure_base_url()

        # 配了 phone+password 但没 token: 首次自动登录
        if self._phone and self._password and not self.token and not self._auth_failed:
            self._do_login()

        print("[星影4K] init 完成, base_url=%s" % self.base_url)
        return ""

    def destroy(self):
        pass

    # ---- 会员认证 ----

    def _do_login(self):
        """POST /api/auth/login-password 自动登录获取 token"""
        try:
            post_data = json.dumps({"phone": self._phone, "password": self._password})
            result = self._fetch_json("/api/auth/login-password", post_data=post_data)
            if result.get("code") == 0 and result.get("data"):
                d = result["data"]
                self.token = d.get("access_token", "")
                self.refresh_token = d.get("refresh_token", "")
                expires_in = d.get("expires_in", 7200)
                self._token_expire = time.time() + expires_in - 300  # 提前 5 分钟刷新
                self._auth_failed = False
                self._update_auth_header()
                print("[星影4K] 会员登录成功")
                return True
        except Exception as e:
            print("[星影4K] 登录异常: %s" % e)
        self._auth_failed = True
        print("[星影4K] 会员登录失败, 降级到游客模式")
        return False

    def _do_refresh(self):
        """POST /api/auth/refresh 刷新过期 token"""
        if not self.refresh_token:
            return False
        try:
            post_data = json.dumps({"refresh_token": self.refresh_token})
            result = self._fetch_json("/api/auth/refresh", post_data=post_data)
            if result.get("code") == 0 and result.get("data"):
                d = result["data"]
                self.token = d.get("access_token", self.token)
                new_rt = d.get("refresh_token", "")
                if new_rt:
                    self.refresh_token = new_rt
                expires_in = d.get("expires_in", 7200)
                self._token_expire = time.time() + expires_in - 300
                self._auth_failed = False
                self._update_auth_header()
                return True
        except Exception:
            pass
        # refresh 失败: 尝试重新登录
        if self._phone and self._password:
            return self._do_login()
        self._auth_failed = True
        return False

    def _ensure_token(self):
        """检查 token 有效性, 过期则自动刷新或重新登录"""
        if not self.token:
            return False
        if time.time() >= self._token_expire:
            return self._do_refresh()
        return True

    def _update_auth_header(self):
        """更新 headers 中的 Authorization"""
        if self.token:
            self.headers["Authorization"] = "Bearer " + self.token
        elif "Authorization" in self.headers:
            del self.headers["Authorization"]

    # ---- 游客 Device ID 自动轮换 ----

    def _gen_device_id(self):
        return "dev_" + uuid.uuid4().hex[:12]

    def _rotate_device(self):
        self._device_id = self._gen_device_id()
        self.headers = {
            "User-Agent": self.ua,
            "Accept": "application/json, text/plain, */*",
            "Accept-Encoding": "gzip, deflate",
            "X-Device-Type": "web",
            "X-Device-ID": self._device_id,
            "X-Device-Name": "Linux",
            "X-Device-Model": "Chrome",
        }
        if self.token:
            self.headers["Authorization"] = "Bearer " + self.token

    # ---- 内部工具 ----

    def _follow_redirect(self, url, headers=None):
        """跟踪 302 重定向获取最终直链, 解决 TVBox 播放器不处理重定向导致的黑屏"""
        try:
            r = self.fetch(url, headers=headers or {
                "User-Agent": self.ua,
                "Accept-Encoding": "gzip, deflate",
            })
            final = getattr(r, "url", None)
            if final and final != url:
                return final
            loc = getattr(r, "headers", {})
            if hasattr(loc, "get"):
                loc_url = loc.get("Location", "") or loc.get("location", "")
                if loc_url:
                    return loc_url
        except Exception:
            pass
        return url

    def _fetch_json(self, path, params=None, post_data=None):
        self._ensure_base_url()
        url = self.base_url + path
        if params:
            url += "?" + urllib.parse.urlencode(params)

        headers = dict(self.headers)

        try:
            if post_data is not None:
                headers["Content-Type"] = "application/json"
                r = self.fetch(url, headers=headers, data=post_data.encode("utf-8"))
            else:
                r = self.fetch(url, headers=headers)
            return json.loads(r.text)
        except Exception as e:
            print("[星影4K] _fetch_json 异常: %s, path=%s" % (e, path))
            return {}

    def _make_card(self, item):
        if not item.get("vod_id"):
            return None
        return {
            "vod_id": str(item["vod_id"]),
            "vod_name": item.get("vod_name", ""),
            "vod_pic": item.get("vod_pic", ""),
            "vod_remarks": item.get("vod_remarks", ""),
        }

    def _clean_text(self, text):
        if not text:
            return ""
        text = re.sub(r"<br\s*/?>", "\n", text)
        text = re.sub(r"<[^>]+>", "", text)
        text = text.replace("&nbsp;", " ")
        text = text.replace("&amp;", "&")
        text = text.replace("&lt;", "<")
        text = text.replace("&gt;", ">")
        return text.strip()

    def _build_filters(self, c):
        f = []

        # 类型筛选 (从 type_extend 动态提取)
        ext_str = c.get("type_extend", "")
        class_list = []
        if ext_str:
            try:
                ext_data = json.loads(ext_str)
                class_list = ext_data.get("class", [])
            except Exception:
                pass

        if class_list:
            vals = [{"n": "全部", "v": ""}]
            for v in class_list:
                vals.append({"n": v, "v": v})
            f.append({"key": "class", "name": "类型", "value": vals})

        # 地区
        f.append({"key": "area", "name": "地区",
                   "value": [dict(x) for x in AREAS]})

        # 年份 (动态生成)
        current_year = datetime.datetime.now().year
        years = [{"n": "全部", "v": ""}]
        for y in range(current_year, current_year - 12, -1):
            years.append({"n": str(y), "v": str(y)})
        f.append({"key": "year", "name": "年份", "value": years})

        # 排序
        f.append({"key": "by", "name": "排序",
                   "value": [dict(x) for x in SORTS]})

        return f

    # ---- 五大标准方法 ----

    def homeContent(self, filter=False):
        result = {}

        # 分类列表
        cats = self._fetch_json("/api/categories")
        classes = []
        filters = {}

        if cats.get("code") == 0 and cats.get("data"):
            for c in cats["data"]:
                type_id = c.get("type_id")
                type_name = c.get("type_name", "")
                if not type_id or not type_name:
                    continue
                classes.append({"type_id": str(type_id), "type_name": type_name})
                fl = self._build_filters(c)
                if fl:
                    filters[str(type_id)] = fl

        # 补充分类栏: 直播
        classes.append({"type_id": LIVE_TID, "type_name": "直播"})
        filters[LIVE_TID] = [{
            "key": "category",
            "name": "分类",
            "value": [dict(x) for x in LIVE_CATEGORIES],
        }]

        result["class"] = classes
        # vbox 适配: 始终返回 filters
        result["filters"] = filters

        # 首页栏目
        home = self._fetch_json("/api/home/sections")
        if home.get("code") == 0 and home.get("data"):
            list_data = []
            seen = set()
            for section in home["data"]:
                for item in section.get("items", []):
                    vod = self._make_card(item)
                    if vod and vod["vod_id"] not in seen:
                        seen.add(vod["vod_id"])
                        list_data.append(vod)
            result["list"] = list_data
        else:
            result["list"] = []

        print("[星影4K] homeContent: %d 分类, %d 首页推荐" % (len(classes), len(result.get("list", []))))
        return result

    def categoryContent(self, tid, pg, filter=False, extend=None):
        result = {"list": [], "page": 1, "pagecount": 1, "limit": 20, "total": 0}

        page = int(pg) if pg else 1

        # 兼容 extend 为字符串的情况
        if extend and isinstance(extend, str):
            try:
                extend = json.loads(extend)
            except Exception:
                extend = {}
        if not extend:
            extend = {}

        # 直播分类: 从 /api/live/channels 获取
        if str(tid) == LIVE_TID:
            data = self._fetch_json("/api/live/channels")
            list_data = []
            seen = set()
            if data.get("code") == 0 and data.get("data"):
                channels = data["data"]
                cat_filter = extend.get("category", "")
                for ch in channels:
                    if cat_filter and ch.get("category", "") != cat_filter:
                        continue
                    cid = ch.get("id")
                    if not cid or str(cid) in seen:
                        continue
                    seen.add(str(cid))
                    list_data.append({
                        "vod_id": "live_" + str(cid),
                        "vod_name": ch.get("name", ""),
                        "vod_pic": ch.get("logo", ""),
                        "vod_remarks": "直播",
                    })
            total = len(list_data)
            start = (page - 1) * 20
            end = start + 20
            result["list"] = list_data[start:end]
            result["page"] = page
            result["pagecount"] = (total + 19) // 20 if total else 1
            result["limit"] = 20
            result["total"] = total
            print("[星影4K] 直播分类: page=%d, %d 条" % (page, len(result["list"])))
            return result

        params = {"t": tid, "page": page, "limit": 20}

        for key in ("class", "area", "year", "by"):
            val = extend.get(key, "")
            if val:
                params[key] = val

        data = self._fetch_json("/api/videos", params=params)

        if data.get("code") == 0 and data.get("data"):
            d = data["data"]
            list_data = []
            seen = set()
            for item in d.get("list", []):
                vod = self._make_card(item)
                if vod and vod["vod_id"] not in seen:
                    seen.add(vod["vod_id"])
                    list_data.append(vod)

            total = d.get("total", 0)
            result["list"] = list_data
            result["page"] = page
            result["pagecount"] = (total + 19) // 20 if total else 1
            result["limit"] = 20
            result["total"] = total

        print("[星影4K] 分类 tid=%s page=%d: %d 条" % (tid, page, len(result["list"])))
        return result

    def detailContent(self, ids):
        vod_id = ids[0] if isinstance(ids, list) else ids

        # 直播详情: id 格式 live_{channel_id}
        vid = str(vod_id)
        if vid.startswith("live_"):
            return self._live_detail(vid[5:])

        data = self._fetch_json("/api/videos/" + vid)

        if data.get("code") != 0 or not data.get("data"):
            return {}

        d = data["data"]

        vod = {
            "vod_id": str(d.get("vod_id", "")),
            "vod_name": d.get("vod_name", ""),
            "vod_pic": d.get("vod_pic", ""),
            "type_name": d.get("type_name", ""),
            "vod_year": str(d.get("vod_year", "")),
            "vod_area": d.get("vod_area", ""),
            "vod_class": d.get("vod_class", ""),
            "vod_remarks": d.get("vod_remarks", ""),
            "vod_actor": d.get("vod_actor", ""),
            "vod_director": d.get("vod_director", ""),
            "vod_content": self._clean_text(d.get("vod_content", "")),
        }

        # 优先使用 play_list (结构化), 回退到 vod_play_from/vod_play_url
        play_list = d.get("play_list", [])

        # 4K/超清源排序优先
        play_list.sort(key=lambda s: SOURCE_PRIORITY.get(s.get("from", ""), 99))

        play_from_list = []
        play_url_list = []

        if play_list:
            for source in play_list:
                from_id = source.get("from", "")
                source_name = SOURCE_NAMES.get(from_id, from_id)
                episodes = source.get("episodes", [])

                ep_parts = []
                for i, ep in enumerate(episodes):
                    ep_name = ep.get("name", "") or ("第" + str(i + 1) + "集")
                    ep_url = ep.get("url", "")
                    ep_parts.append(ep_name + "$" + ep_url)

                if ep_parts:
                    play_from_list.append(source_name)
                    play_url_list.append("#".join(ep_parts))
        else:
            pf = d.get("vod_play_from", "")
            pu = d.get("vod_play_url", "")
            if pf and pu:
                from_list = pf.split("$$$")
                url_list = pu.split("$$$")
                for i in range(min(len(from_list), len(url_list))):
                    fid = from_list[i]
                    name = SOURCE_NAMES.get(fid, fid)
                    play_from_list.append(name)
                    play_url_list.append(url_list[i])

        vod["vod_play_from"] = "$$$".join(play_from_list)
        vod["vod_play_url"] = "$$$".join(play_url_list)

        print("[星影4K] 详情: %s, %d 条线路" % (vod.get("vod_name", ""), len(play_from_list)))
        return {"list": [vod]}

    def _live_detail(self, channel_id):
        """直播频道详情: GET /api/live/channels/{id} -> sources"""
        data = self._fetch_json("/api/live/channels/" + str(channel_id))
        if data.get("code") != 0 or not data.get("data"):
            return {}
        d = data["data"]

        vod = {
            "vod_id": "live_" + str(d.get("id", channel_id)),
            "vod_name": d.get("name", ""),
            "vod_pic": d.get("logo", ""),
            "type_name": "直播",
            "vod_remarks": "直播",
            "vod_area": d.get("category", ""),
        }

        sources = d.get("sources", [])
        sources.sort(key=lambda s: s.get("priority", 0), reverse=True)

        play_from_list = []
        play_url_list = []
        for i, src in enumerate(sources):
            src_url = src.get("url", "")
            if not src_url:
                continue
            src_name = "线路" + str(i + 1) if not src.get("quality") else src.get("quality")
            play_from_list.append(src_name)
            play_url_list.append("直播$" + src_url)

        if not play_from_list:
            play_from_list = ["直播"]
            play_url_list = ["直播$"]

        vod["vod_play_from"] = "$$$".join(play_from_list)
        vod["vod_play_url"] = "$$$".join(play_url_list)
        return {"list": [vod]}

    def searchContent(self, key, quick, pg=1):
        result = {"list": []}
        page = int(pg) if pg else 1

        data = self._fetch_json("/api/search", params={
            "wd": key, "page": page, "limit": 20
        })

        if data.get("code") == 0 and data.get("data"):
            d = data["data"]
            list_data = []
            seen = set()
            for item in d.get("list", []):
                vod = self._make_card(item)
                if vod and vod["vod_id"] not in seen:
                    seen.add(vod["vod_id"])
                    list_data.append(vod)
            result["list"] = list_data

        print("[星影4K] 搜索 '%s': %d 条" % (key, len(result["list"])))
        return result

    def searchContentPage(self, key, quick, pg):
        return self.searchContent(key, quick, pg)

    def playerContent(self, flag, id, vipFlags):
        play_header = json.dumps({
            "User-Agent": self.ua,
            "Accept-Encoding": "gzip, deflate",
            "Referer": self.base_url,
        })

        # 直链 URL: 判断是否需要嗅探
        if id.startswith("http"):
            needs_sniff = any(domain in id for domain in SNIFF_DOMAINS)
            if needs_sniff:
                return {
                    "parse": 1,
                    "url": id,
                    "header": play_header,
                }
            # 非嗅探域名: 跟踪 302 重定向, 解决 TVBox 黑屏
            final_url = self._follow_redirect(id, json.loads(play_header))
            return {
                "parse": 0,
                "url": final_url,
                "header": play_header,
            }

        # 编码 URL (rose_xxx, co_xxx 等): 调用 /api/parse 解析
        from_id = ""
        if "_" in id:
            from_id = id.split("_", 1)[0]
        else:
            # 从 flag 反查 from_id
            for k, v in SOURCE_NAMES.items():
                if v == flag:
                    from_id = k
                    break
            if not from_id:
                from_id = flag

        post_data = json.dumps({"url": id, "from": from_id})

        # ---- 三层认证 fallback: 会员 -> token刷新 -> 游客 ----
        # 层1: 有 token 先确保有效, 会员解析无限制
        if self.token:
            self._ensure_token()

        result = self._fetch_json("/api/parse", post_data=post_data)

        # 会员 token 失效 (40110/401): 尝试刷新 token 后重试
        if result.get("code") in (40110, 401) and self.token:
            self._do_refresh()
            result = self._fetch_json("/api/parse", post_data=post_data)

        # 仍失败: 清除 token, 降级到游客模式
        if result.get("code") in (40110, 401, 40311) and self.token:
            self.token = ""
            self._update_auth_header()
            result = self._fetch_json("/api/parse", post_data=post_data)

        # 游客额度用尽 (40311): 自动换 Device ID 重置额度后重试
        if result.get("code") == 40311 and not self.token:
            self._rotate_device()
            result = self._fetch_json("/api/parse", post_data=post_data)

        # 需登录 (40110): 无 token 时也尝试换号
        if result.get("code") == 40110 and not self.token:
            self._rotate_device()
            result = self._fetch_json("/api/parse", post_data=post_data)

        if result.get("code") == 0 and result.get("data"):
            d = result["data"]
            play_url = d.get("url", "")
            player_type = d.get("player_type", 0)

            # 游客剩余额度为 0: 下次主动换号, 避免一次失败请求
            remaining = d.get("guest_remaining")
            if remaining is not None and remaining <= 0 and not self.token:
                self._rotate_device()

            if play_url:
                # player_type=0 直链: 跟踪 302 重定向解决黑屏
                # player_type=1 iframe: 直接返回让壳子嗅探
                if player_type == 0:
                    play_url = self._follow_redirect(play_url, json.loads(play_header))
                return {
                    "parse": player_type,
                    "url": play_url,
                    "header": play_header,
                }

        # 回退: 尝试嗅探
        return {
            "parse": 1,
            "url": id,
            "header": play_header,
        }

    def localProxy(self, param):
        return [200, "text/plain", "", {}]

    def isVideoFormat(self, url):
        return bool(url and any(x in url.lower() for x in (".m3u8", ".mp4", ".flv", ".mkv", ".mpd")))

    def manualVideoCheck(self):
        return False


# ====== 沙箱测试入口 ======
if __name__ == "__main__":
    s = Spider()
    s.init()

    print("=== 1. homeContent ===")
    home = s.homeContent(filter=True)
    classes = home.get("class", [])
    print("  Classes:", len(classes))
    for c in classes:
        print("    " + c["type_id"] + ": " + c["type_name"])
    has_live = any(c["type_id"] == "live" for c in classes)
    print("  Has live category:", has_live)
    assert has_live, "No live category"
    print("  Filters:", len(home.get("filters", {})))
    print("  Home list:", len(home.get("list", [])))
    if home.get("list"):
        first = home["list"][0]
        print("    First:", first["vod_id"], first["vod_name"])
        test_id = first["vod_id"]
    else:
        test_id = "62145"
    assert len(classes) > 0, "No categories"
    assert len(home.get("list", [])) > 0, "No home list"

    print("")
    print("=== 2a. categoryContent (t=1, pg=1) ===")
    cat = s.categoryContent("1", "1", filter=True)
    print("  List:", len(cat.get("list", [])), "Total:", cat.get("total"), "Pages:", cat.get("pagecount"))
    if cat.get("list"):
        print("    First:", cat["list"][0]["vod_name"])
    assert len(cat.get("list", [])) > 0, "No category list"

    print("")
    print("=== 2b. categoryContent with filter (t=2, class=古装) ===")
    cat2 = s.categoryContent("2", "1", filter=True, extend={"class": "古装"})
    print("  List:", len(cat2.get("list", [])), "Total:", cat2.get("total"))
    assert len(cat2.get("list", [])) > 0, "No filtered list"

    print("")
    print("=== 2c. live categoryContent (t=live, pg=1) ===")
    live_cat = s.categoryContent("live", "1", filter=True)
    print("  List:", len(live_cat.get("list", [])), "Total:", live_cat.get("total"), "Pages:", live_cat.get("pagecount"))
    if live_cat.get("list"):
        print("    First:", live_cat["list"][0]["vod_id"], live_cat["list"][0]["vod_name"])
        live_id = live_cat["list"][0]["vod_id"]
    else:
        live_id = "live_1138"
    assert len(live_cat.get("list", [])) > 0, "No live list"

    print("")
    print("=== 2d. live categoryContent filter (t=live, category=央视频道) ===")
    live_filtered = s.categoryContent("live", "1", filter=True, extend={"category": "央视频道"})
    print("  List:", len(live_filtered.get("list", [])), "Total:", live_filtered.get("total"))
    assert len(live_filtered.get("list", [])) > 0, "No filtered live list"

    print("")
    print("=== 3a. detailContent (id=" + str(test_id) + ") ===")
    detail = s.detailContent([test_id])
    if detail.get("list"):
        v = detail["list"][0]
        print("  Name:", v.get("vod_name"))
        pf = v.get("vod_play_from", "")
        pu = v.get("vod_play_url", "")
        print("  Play from:", pf[:80])
        print("  Play url:", pu[:80] + "...")
        assert pf, "No play_from"
        assert pu, "No play_url"

        play_from = pf.split("$$$")
        play_urls = pu.split("$$$")
        if play_from and play_urls:
            flag = play_from[0]
            first_ep = play_urls[0].split("#")[0]
            if "$" in first_ep:
                ep_url = first_ep.split("$", 1)[1]
            else:
                ep_url = first_ep

            print("")
            print("=== 5a. playerContent (flag=" + flag + ", url=" + ep_url[:50] + "...) ===")
            play = s.playerContent(flag, ep_url, [])
            play_url = play.get("url", "")
            print("  Parse:", play.get("parse"))
            print("  URL:", play_url[:80] + "...")
            assert play_url, "No play URL"
    else:
        print("  ERROR: No detail found")
    assert detail.get("list"), "No detail"

    print("")
    print("=== 3b. live detailContent (id=" + live_id + ") ===")
    live_detail = s.detailContent([live_id])
    if live_detail.get("list"):
        lv = live_detail["list"][0]
        print("  Name:", lv.get("vod_name"))
        lpf = lv.get("vod_play_from", "")
        lpu = lv.get("vod_play_url", "")
        print("  Play from:", lpf[:80])
        print("  Play url:", lpu[:80] + "...")
        assert lpf, "No live play_from"
        assert lpu, "No live play_url"

        live_flag = lpf.split("$$$")[0]
        live_ep = lpu.split("$$$")[0].split("#")[0]
        if "$" in live_ep:
            live_ep_url = live_ep.split("$", 1)[1]
        else:
            live_ep_url = ""

        if live_ep_url:
            print("")
            print("=== 5b. live playerContent (flag=" + live_flag + ") ===")
            live_play = s.playerContent(live_flag, live_ep_url, [])
            print("  Parse:", live_play.get("parse"))
            print("  URL:", str(live_play.get("url", ""))[:80] + "...")
            assert live_play.get("url"), "No live play URL"
    else:
        print("  ERROR: No live detail found")
    assert live_detail.get("list"), "No live detail"

    print("")
    print("=== 4. searchContent (key=斗罗) ===")
    search = s.searchContent("斗罗", False)
    print("  Results:", len(search.get("list", [])))
    if search.get("list"):
        print("    First:", search["list"][0]["vod_name"])
    assert len(search.get("list", [])) > 0, "No search results"

    print("")
    print("=== ALL TESTS PASSED ===")
