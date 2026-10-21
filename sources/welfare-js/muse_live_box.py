# -*- coding: utf-8 -*-
"""
暮色直播盒子 — vbox 福利专区直播栏目适配版
数据源: http://api.hclyz.com:81/mf/  （明文 gzip JSON，无需签名/AES）

数据链路（实测验证 2026-10-21）:
  1. GET {host}/mf/json.txt        -> 平台列表 {"pingtai":[{"address":"jsonxxx.txt","xinimg":图标,"Number":编号,"title":平台名}]}
  2. GET {host}/mf/json{平台}.txt  -> 直播间列表 {"zhubo":[{"address":flv地址,"img":头像,"title":昵称}]}
  3. 播放 flv 直链（header: User-Agent=fsplayer）-> HTTP 200 video/x-flv

映射:
  type_id = 平台数据文件名（jsonjinbei.txt）
  vod_id  = base64(flv 播放地址)，避免 URL 中 ?wsSecret 等导致客户端异常
  播放: parse=0 + header {"User-Agent": "fsplayer"}
"""
import json
import gzip
import base64
import requests

try:
    from base.spider import Spider as BaseSpider
except ImportError:
    class BaseSpider:
        def init(self, extend=""):
            return {}


class Spider(BaseSpider):

    def getName(self):
        return "暮色直播盒子"

    def getDependence(self):
        return []

    def init(self, extend=""):
        try:
            super().init(extend)
        except Exception:
            pass
        self.host = "http://api.hclyz.com:81"
        # 读取基座注入的域名（defaultHosts 备用域名回退）
        try:
            effective_hosts = globals().get('_vbox_effective_hosts', [])
            if effective_hosts:
                self.host = effective_hosts[0].rstrip('/')
        except Exception:
            pass
        self.headers = {
            "User-Agent": "Dart/3.12 (dart:io)",
            "Accept-Encoding": "gzip",
        }
        self.play_headers = {"User-Agent": "fsplayer"}
        return {}

    # ── 工具 ──────────────────────────────────────

    def _get_json(self, path):
        """GET {host}/mf/{path}，返回 JSON（兼容 gzip 与明文）"""
        url = self.host.rstrip('/') + "/mf/" + str(path).lstrip('/')
        try:
            resp = requests.get(url, headers=self.headers, timeout=12)
        except Exception:
            return {}
        if resp.status_code != 200:
            return {}
        raw = resp.content or b""
        # 服务端可能未正确标记 Content-Encoding，若为 gzip 魔数则手动解压
        if raw[:2] == b'\x1f\x8b':
            try:
                raw = gzip.decompress(raw)
            except Exception:
                return {}
        try:
            return json.loads(raw.decode('utf-8', errors='replace'))
        except Exception:
            return {}

    def _enc(self, s):
        return base64.b64encode(str(s).encode('utf-8')).decode('ascii')

    def _dec(self, s):
        try:
            return base64.b64decode(s).decode('utf-8')
        except Exception:
            return ""

    # ── FongMi 接口 ────────────────────────────────

    def homeContent(self, filter=False):
        """首页：平台列表（136）+ 前两平台主播推荐"""
        data = self._get_json("json.txt")
        platforms = data.get("pingtai", [])
        classes = []
        vod_list = []
        for i, p in enumerate(platforms):
            addr = p.get("address")
            if not addr:
                continue
            classes.append({
                "type_id": addr,
                "type_name": p.get("title") or ("平台%d" % i),
            })
        for p in platforms[:2]:
            addr = p.get("address")
            if not addr:
                continue
            room = self._get_json(addr)
            for z in room.get("zhubo", [])[:6]:
                if not z.get("address"):
                    continue
                vod_list.append({
                    "vod_id": self._enc(z["address"]),
                    "vod_name": z.get("title") or "未知主播",
                    "vod_pic": z.get("img") or "",
                    "vod_remarks": p.get("title") or "直播",
                })
            if len(vod_list) >= 12:
                break
        return {"class": classes, "list": vod_list}

    def homeVideoContent(self):
        return {"list": []}

    def categoryContent(self, tid, pg, filter=False, extend=""):
        """分类：某平台主播列表（tid = json{平台}.txt）"""
        try:
            page = int(pg) if pg else 1
        except Exception:
            page = 1
        room = self._get_json(tid)
        vod_list = []
        for z in room.get("zhubo", []):
            if not z.get("address"):
                continue
            vod_list.append({
                "vod_id": self._enc(z["address"]),
                "vod_name": z.get("title") or "未知主播",
                "vod_pic": z.get("img") or "",
                "vod_remarks": "直播",
            })
        return {
            "page": page,
            "pagecount": 1,
            "limit": len(vod_list),
            "total": len(vod_list),
            "list": vod_list,
        }

    def detailContent(self, ids):
        """详情：解码 flv 地址，构造单线路播放"""
        if isinstance(ids, list):
            did = ids[0] if ids else ""
        else:
            did = str(ids)
        flv = self._dec(did)
        if not flv:
            return {"list": []}
        return {"list": [{
            "vod_id": did,
            "vod_name": "直播",
            "vod_pic": "",
            "vod_play_from": "直播线路",
            "vod_play_url": "直播$" + flv,
        }]}

    def searchContent(self, key, quick, pg=1):
        """直播源无搜索场景"""
        return {"list": []}

    def playerContent(self, flag, id, vipFlags=None):
        """播放：flv 直连（parse=0 + UA=fsplayer）"""
        url = str(id or "")
        if "$" in url:
            url = url.split("$", 1)[-1]
        return {"parse": 0, "url": url, "header": self.play_headers}
