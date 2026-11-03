#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""快猫（km）— vbox 自包含适配器

协议来源：libapp.so blutter 反汇编（package:avbox/module/km/*）
────────────────────────────────────────────────────────────
请求加密（KmInterceptor → CryptoUtil）
    data = base16( AES-128-CBC( jsonEncode(业务参数),
                                key="625202f9149maomi", iv="5efd3f6060emaomi" ) )
    sig  = MD5( "data=" + data + "maomi_pass_xyz" )
    POST  form-urlencoded  {data, sig}

响应解密
    body 是纯 hex 字符串 → bytes → AES-128-CBC 同 key/iv → JSON
    信封 {"code":0,"message":"","data":{...}}

接口（全部 POST，路径即方法名）
    /api/videos/listAll   全部      body {"page":N,"limit":M}
    /api/videos/listHot   热门
    /api/videos/detail    详情      ⚠ 需登录，返回「用户未登录」→ 本适配器改用列表数据
    /api/users/getUserInfo 需登录

资源
    封面  mv_img_url   （imgs.e8eues3.xyz，实测 200 image/jpeg）
    播放  mv_play_url  （mp4 直链，**列表项里就有**，无需 detail）
          ⚠ 实测视频源 IP 119.28.204.36 直连超时 / 代理 502 —— 服务端侧不可达，
            适配器照常输出直链，能否播放取决于客户端网络环境。

坑
    1) key/iv 各 16 字符，直接 .encode()，不要补零（补了变 17 字节报错）
    2) 路径本身就是方法名，打到 /api/videos/ 会返回 501 Unknown method
    3) detail 需登录，不要指望它；列表项字段已足够做详情与播放
"""

import base64
import binascii
import gzip
import hashlib
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


BASE_DEFAULT = "https://icef4vn.xyz"
KEY = b"625202f9149maomi"      # 16 字节
IV = b"5efd3f6060emaomi"       # 16 字节
PASS = "maomi_pass_xyz"
UA = "okhttp/3.14.9"

CATEGORIES = [("listAll", "最新"), ("listHot", "热门")]


# ============================================================ AES 三档后端
def _aes_cbc(key, iv, data, encrypt=False):
    try:
        from Crypto.Cipher import AES as _A
        from Crypto.Util.Padding import pad as _p, unpad as _up
        if encrypt:
            return _A.new(key, _A.MODE_CBC, iv).encrypt(_p(data, 16))
        raw = _A.new(key, _A.MODE_CBC, iv).decrypt(data)
        try:
            return _up(raw, 16)
        except Exception:
            return raw
    except ImportError:
        pass
    try:
        from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
        c = Cipher(algorithms.AES(key), modes.CBC(iv))
        if encrypt:
            e = c.encryptor()
            return e.update(data) + e.finalize()
        d = c.decryptor()
        raw = d.update(data) + d.finalize()
        if raw and 1 <= raw[-1] <= 16:
            raw = raw[:-raw[-1]]
        return raw
    except ImportError:
        pass
    import pyaes
    m = pyaes.AESModeOfOperationCBC(key, iv=iv)
    if encrypt:
        return b"".join(m.encrypt(data[i:i + 16]) for i in range(0, len(data), 16))
    raw = b"".join(m.decrypt(data[i:i + 16]) for i in range(0, len(data), 16))
    if raw and 1 <= raw[-1] <= 16:
        raw = raw[:-raw[-1]]
    return raw


class KmCore(object):
    def __init__(self, spider):
        self.sp = spider
        self.base = BASE_DEFAULT
        self._cache = {}      # mv_id -> item
        self.timeout = 20

    def _open(self, req, timeout=None):
        t = timeout or self.timeout
        try:
            return urllib.request.urlopen(req, timeout=t)
        except Exception:
            op = urllib.request.build_opener(urllib.request.ProxyHandler({}))
            return op.open(req, timeout=t)

    # ---------------- 加解密 ----------------
    def _enc(self, obj):
        plain = json.dumps(obj, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
        data_hex = binascii.hexlify(_aes_cbc(KEY, IV, plain, encrypt=True)).decode()
        sig = hashlib.md5(("data=" + data_hex + PASS).encode()).hexdigest()
        return data_hex, sig

    def _dec(self, raw):
        txt = raw.decode("utf-8", "replace").strip()
        if not txt:
            return {}
        b = None
        try:
            b = binascii.unhexlify(txt)
        except Exception:
            try:
                s = txt.replace("-", "+").replace("_", "/")
                s += "=" * ((4 - len(s) % 4) % 4)
                b = base64.b64decode(s)
            except Exception:
                return {}
        try:
            p = _aes_cbc(KEY, IV, b, encrypt=False)
            return json.loads(p.decode("utf-8", "replace").rstrip("\x00"))
        except Exception:
            return {}

    # ---------------- 请求 ----------------
    def call(self, method, body=None):
        """method 即路径尾段，如 listAll / listHot。"""
        payload = dict(body or {})
        data_hex, sig = self._enc(payload)
        form = urllib.parse.urlencode({"data": data_hex, "sig": sig}).encode()
        url = self.base.rstrip("/") + "/api/videos/" + method
        req = urllib.request.Request(url, data=form, headers={
            "User-Agent": UA,
            "Content-Type": "application/x-www-form-urlencoded",
            "Accept": "*/*",
        }, method="POST")
        try:
            with self._open(req) as r:
                return self._dec(r.read())
        except urllib.error.HTTPError as e:
            try:
                return self._dec(e.read())
            except Exception:
                return {}
        except Exception:
            return {}

    # ---------------- 映射 ----------------
    def _item(self, it):
        mid = it.get("mv_id")
        if mid is not None:
            self._cache[str(mid)] = it
        remarks = []
        try:
            w = int(it.get("mv_play_width") or 0)
            h = int(it.get("mv_play_height") or 0)
            if w and h:
                remarks.append("%dp" % h)
        except Exception:
            pass
        if it.get("mv_like"):
            remarks.append("%s赞" % it.get("mv_like"))
        if it.get("mu_name"):
            remarks.append(str(it.get("mu_name")))
        return {
            "vod_id": str(mid),
            "vod_name": (it.get("mv_title") or "").strip() or "无标题",
            "vod_pic": it.get("mv_img_url") or "",
            "vod_remarks": " · ".join(remarks),
            "style": {"type": "rect", "ratio": 0.5625},
        }

    def list(self, tid, page):
        method = tid if tid in ("listAll", "listHot") else "listAll"
        j = self.call(method, {"page": int(page), "limit": 20})
        if j.get("code") not in (0, 200):
            return []
        d = j.get("data") or {}
        items = d.get("list") if isinstance(d, dict) else None
        if not isinstance(items, list):
            items = []
        return [self._item(it) for it in items if it.get("mv_id")]

    def find(self, vid):
        """优先缓存，miss 则翻页找（detail 接口需登录，不可用）。"""
        key = str(vid)
        if key in self._cache:
            return self._cache[key]
        for pg in range(1, 6):
            self.list("listAll", pg)
            if key in self._cache:
                return self._cache[key]
        return {}

    def detail(self, vid):
        it = self.find(vid)
        if not it:
            return {}
        title = (it.get("mv_title") or "").strip() or ("快猫 #%s" % vid)
        meta = []
        if it.get("mu_name"):
            meta.append("作者：%s" % it.get("mu_name"))
        try:
            w = int(it.get("mv_play_width") or 0)
            h = int(it.get("mv_play_height") or 0)
            if w and h:
                meta.append("分辨率：%dx%d" % (w, h))
        except Exception:
            pass
        if it.get("mv_like"):
            meta.append("点赞：%s" % it.get("mv_like"))
        if it.get("mv_comment"):
            meta.append("评论：%s" % it.get("mv_comment"))
        if it.get("mv_created"):
            meta.append("发布：%s" % it.get("mv_created"))
        play = it.get("mv_play_url") or ""
        if play:
            meta.append("直链：%s" % play)
        desc = "\n".join(meta)
        desc = desc.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
        return {
            "vod_id": str(vid),
            "vod_name": title,
            "vod_pic": it.get("mv_img_url") or "",
            "vod_content": desc,
            "vod_play_url": ("正片$%s" % play) if play else "",
        }

    def play(self, vid):
        it = self.find(vid)
        u = (it.get("mv_play_url") or "").strip()
        if u:
            return {"parse": 0, "url": u,
                    "header": {"User-Agent": UA, "Referer": self.base + "/"}}
        return None


class Spider(SpiderBase):
    MODULE = "km"
    NAME = "快猫"

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
        self._core = KmCore(self)
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
            self._core = KmCore(self)
        return self._core

    # ---------------- vbox 接口 ----------------
    def homeContent(self, filter):
        return {"class": [{"type_id": t, "type_name": n} for t, n in CATEGORIES],
                "list": []}

    def homeVideoContent(self):
        try:
            return {"list": self._c().list("listHot", 1)}
        except Exception:
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
            "pagecount": page + 1 if items else page,
            "limit": len(items),
            "total": 9999 if items else 0,
        }

    def detailContent(self, ids):
        vid = str(ids[0]) if ids else ""
        if not vid:
            return {"list": []}
        try:
            d = self._c().detail(vid)
        except Exception:
            d = {}
        if not d:
            return {"list": []}
        return {"list": [{
            "vod_id": vid,
            "vod_name": d.get("vod_name") or vid,
            "vod_pic": d.get("vod_pic", ""),
            "vod_content": d.get("vod_content", ""),
            "vod_play_from": self.NAME,
            "vod_play_url": d.get("vod_play_url", ""),
        }]}

    def playerContent(self, flag, id, vipFlags):
        url = str(id)
        if url and not url.startswith("http"):
            try:
                r = self._c().play(url)
            except Exception:
                r = None
            if isinstance(r, dict) and r.get("url"):
                return r
        return {"parse": 0, "url": url,
                "header": {"User-Agent": UA, "Referer": BASE_DEFAULT + "/"}}

    def searchContent(self, key, quick, pg="1"):
        return {"list": [], "page": 1, "pagecount": 1, "limit": 0, "total": 0}

    def localProxy(self, param):
        return [404, "text/plain; charset=utf-8", b"", {}]
