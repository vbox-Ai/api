#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""直播盒子（live）— vbox 自包含适配器

协议来源：libapp.so blutter 反汇编（package:avbox/module/live/*）
零鉴权、零加密、纯 JSON 配置：

    GET /mf/json.txt
        {"pingtai":[{"address":"jsonkawayi.txt","xinimg":"封面","Number":"99","title":"卡哇伊"}, …]}
        共 130 个平台

    GET /mf/{address}
        {"zhubo":[{"address":"http://…/live/cx_15601.flv?wsSecret=…&wsTime=…",
                   "img":"封面","title":"撸管专用系列@"}, …]}
        每个平台 90+ 个主播，address 即 FLV 直播直链（签名已在 URL 内）

映射
    平台(pingtai) → vbox 分类
    主播(zhubo)   → vbox 列表项，vod_id 用 base64 包裹播放地址
    播放          → 直接返回 FLV 直链（parse=0）
"""

import base64
import gzip
import json
import os
import ssl
import sys
import time
import urllib.error
import urllib.parse
import urllib.request

try:
    from base.spider import Spider as SpiderBase
except ImportError:
    class SpiderBase(object):
        def getCache(self, key):
            return None

        def setCache(self, key, value):
            return "fail"

        def delCache(self, key):
            return "fail"


BASE_DEFAULT = "http://api.hclyz.com:81"
UA = "okhttp/3.14.9"


def _enc_id(url):
    return base64.urlsafe_b64encode(url.encode("utf-8")).decode().rstrip("=")


def _dec_id(vid):
    s = str(vid)
    if s.startswith("http"):
        return s
    try:
        s += "=" * ((4 - len(s) % 4) % 4)
        return base64.urlsafe_b64decode(s).decode("utf-8")
    except Exception:
        return s


class LiveCore(object):
    def __init__(self, spider):
        self.sp = spider
        self.base = BASE_DEFAULT
        self.timeout = 20
        self._plats = None
        self._plats_ts = 0

    def _open(self, req, timeout=None):
        t = timeout or self.timeout
        try:
            return urllib.request.urlopen(req, timeout=t)
        except Exception:
            op = urllib.request.build_opener(urllib.request.ProxyHandler({}))
            return op.open(req, timeout=t)

    def _get_json(self, path):
        url = path if path.startswith("http") else self.base.rstrip("/") + "/" + path.lstrip("/")
        req = urllib.request.Request(url, headers={
            "User-Agent": UA, "Accept": "application/json, text/plain, */*",
            "Referer": self.base + "/"})
        try:
            with self._open(req) as r:
                raw = r.read()
        except urllib.error.HTTPError as e:
            try:
                raw = e.read()
            except Exception:
                return {}
        except Exception:
            return {}
        if raw[:2] == b"\x1f\x8b":
            try:
                raw = gzip.decompress(raw)
            except Exception:
                pass
        for code in ("utf-8", "gb18030", "latin-1"):
            try:
                return json.loads(raw.decode(code))
            except Exception:
                continue
        return {}

    # ---------------- 能力 ----------------
    def platforms(self):
        now = time.time()
        if self._plats and (now - self._plats_ts) < 1800:
            return self._plats
        j = self._get_json("/mf/json.txt")
        plats = j.get("pingtai") or []
        out = []
        for p in plats:
            addr = (p.get("address") or "").strip()
            title = (p.get("title") or "").strip()
            if not addr or not title:
                continue
            out.append({
                "type_id": addr,
                "type_name": title,
                "_img": p.get("xinimg") or "",
                "_n": p.get("Number") or "",
            })
        self._plats = out
        self._plats_ts = now
        return out

    def categories(self):
        return [{"type_id": p["type_id"], "type_name": p["type_name"]}
                for p in self.platforms()]

    def list(self, tid, page):
        tid = str(tid or "").strip()
        if not tid:
            ps = self.platforms()
            tid = ps[0]["type_id"] if ps else "jsonkawayi.txt"
        # 平台配置是一次性全量下发，无分页
        if int(page or 1) > 1:
            return []
        j = self._get_json("/mf/" + tid.lstrip("/"))
        hosts = j.get("zhubo") or []
        out = []
        for h in hosts:
            addr = (h.get("address") or "").strip()
            title = (h.get("title") or "").strip()
            if not addr:
                continue
            if addr.startswith("//"):
                addr = "http:" + addr
            out.append({
                "vod_id": _enc_id(addr),
                "vod_name": title or "直播间",
                "vod_pic": h.get("img") or "",
                "vod_remarks": "直播中",
                "style": {"type": "rect", "ratio": 0.75},
            })
        return out

    def detail(self, vid):
        url = _dec_id(vid)
        if not url:
            return {}
        return {
            "vod_id": str(vid),
            "vod_name": "直播间",
            "vod_pic": "",
            "vod_content": "直播直链：%s" % url,
            "vod_play_url": "直播$%s" % url,
        }

    def play(self, vid):
        url = _dec_id(vid)
        if url.startswith("http"):
            return {"parse": 0, "url": url,
                    "header": {"User-Agent": UA, "Referer": self.base + "/"}}
        return None


class Spider(SpiderBase):
    MODULE = "live"
    NAME = "直播盒子"

    def __init__(self):
        super(Spider, self).__init__()
        self._core = None
        self.timeout = 20

    def getName(self):
        return self.NAME

    def getDependence(self):
        return []

    def init(self, extend=""):
        ext = {}
        if extend:
            try:
                ext = json.loads(extend) if isinstance(extend, str) else dict(extend)
            except Exception:
                ext = {}
        self._core = LiveCore(self)
        if ext.get("host"):
            self._core.base = str(ext["host"]).rstrip("/")
        try:
            self.timeout = int(ext.get("timeout") or 20)
        except Exception:
            self.timeout = 20
        self._core.timeout = self.timeout
        return None

    def isVideoFormat(self, url):
        low = (url or "").lower()
        return any(k in low for k in (".m3u8", ".mp4", ".flv", ".mkv", ".ts"))

    def manualVideoCheck(self):
        return False

    def destroy(self):
        pass

    def action(self, action):
        return {"msg": self.NAME}

    def liveContent(self):
        return ""

    def _c(self):
        if self._core is None:
            self._core = LiveCore(self)
        return self._core

    def homeContent(self, filter):
        try:
            cls = self._c().categories()
        except Exception:
            cls = []
        return {"class": cls, "list": []}

    def homeVideoContent(self):
        try:
            cls = self._c().categories()
            if cls:
                return {"list": self._c().list(cls[0]["type_id"], 1)[:20]}
        except Exception:
            pass
        return {"list": []}

    def categoryContent(self, tid, pg, filter, extend):
        try:
            page = int(pg or 1)
        except Exception:
            page = 1
        try:
            items = self._c().list(str(tid), page)
        except Exception:
            items = []
        return {
            "list": items,
            "page": page,
            "pagecount": 1,
            "limit": len(items),
            "total": len(items),
        }

    def detailContent(self, ids):
        vid = str(ids[0]) if ids else ""
        if not vid:
            return {"list": []}
        d = self._c().detail(vid)
        if not d:
            return {"list": []}
        return {"list": [{
            "vod_id": vid,
            "vod_name": d.get("vod_name") or "直播间",
            "vod_pic": d.get("vod_pic", ""),
            "vod_content": d.get("vod_content", ""),
            "vod_play_from": self.NAME,
            "vod_play_url": d.get("vod_play_url", ""),
        }]}

    def playerContent(self, flag, id, vipFlags):
        url = _dec_id(id)
        if url and not url.startswith("http"):
            try:
                r = self._c().play(id)
            except Exception:
                r = None
            if isinstance(r, dict) and r.get("url"):
                return r
        return {"parse": 0, "url": url,
                "header": {"User-Agent": UA, "Referer": self._c().base + "/"}}

    def searchContent(self, key, quick, pg="1"):
        return {"list": [], "page": 1, "pagecount": 1, "limit": 0, "total": 0}

    def localProxy(self, param):
        return [404, "text/plain; charset=utf-8", b"", {}]
