#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""迷妹漫画（mmmh）— vbox 自包含适配器

协议来源：libapp.so blutter 反汇编（package:avbox/module/mmmh/*）
────────────────────────────────────────────────────────────
三层结构：配置 → 鉴权 → 响应加密

1) 配置（host_pwa.txt，AES-256-CBC）
   key = base64("h7lkUI0kb25Usb3qTFLefTf8b+8Hs2Y63sANNraUm/Q=")   (32B)
   iv  = base64("k54Vcjbp6ByR6D83eIoxgw==")                        (16B)
   明文 = 32位校验前缀 + JSON + 32位尾校验
   JSON: {"api":[{url,default}], "comic":[{url,chain,tsurl,encrypt}],
          "fiction":[…], "img":[{url,encrypt}], "stream":[…]}

2) 鉴权
   Authorization: Bearer <token_mmmh>      （Django 三段式：b64payload.32hex.48hex）

3) 响应加密
   X-Response-Length 头 + base64 密文
   key = "ae52f7ffd2dd66ba5743bb180188b991"                        (32B, AES-256)
   iv  = MD5(X-Response-Length).hex[8:24]                          (16B, 动态)

接口（md 为解密后结构）
   GET /v1/animat/category                    动画分类  {"success":{"data":[{category_id,title,image}]}}
   GET /v1/animat/category/list?category_id=&type=1&page= 列表
       {"success":{title,lastPage,total,data:[{id,avkey,name,tag[],duration,cover,
                  thumbpath,coverpath,ep,max_ep,view_count,type,
                  media:{intro,720,240}(m3u8 相对路径)}]}}
   GET /v1/fiction/category                   小说分类

已知阻碍
   ⚠ media 的 m3u8 直取返回 HTTP 500（分类/列表接口正常，media 端点另有校验）
   ⚠ 封面走 image host 且 encrypt=true，需 MmMhAnimImg + chain 解密，暂未破

坑
   1) X-Response-Length 是随机数，IV 由它派生 → 每个响应 IV 都不同
   2) type 必须是整数（type=1 有效），传 "animat" 会 400
   3) 配置 JSON 前后各有 32 位校验，必须 raw_decode 只取首个对象
   4) token 必须是三段式，传 32 位 hex 会 498「Token 格式錯誤」
"""

import base64
import hashlib
import json
import os
import re
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


# ============================================================ vbox 运行时适配
try:
    import ssl as _ssl
    _SSL_CTX = _ssl.create_default_context()
    _SSL_CTX.check_hostname = False
    _SSL_CTX.verify_mode = _ssl.CERT_NONE
except Exception:
    _SSL_CTX = None


def _vbox_cfg(sp, name, default=None):
    v = getattr(sp, name, None)
    if v is None:
        v = globals().get(name)
    return default if v is None else v


def _vbox_proxy(sp=None):
    if sp is not None and not _vbox_cfg(sp, "_vbox_proxy_enabled", False):
        return {}
    if sp is None and not globals().get("_vbox_proxy_enabled", False):
        return {}
    u = (getattr(sp, "_vbox_proxy_url", None) if sp is not None else None) \
        or globals().get("_vbox_proxy_url", "") or ""
    return {"http": u, "https": u} if u else {}


def _vbox_host(sp, default=""):
    hs = _vbox_cfg(sp, "_vbox_effective_hosts", None)
    if isinstance(hs, list) and hs:
        try:
            return str(hs[0]).rstrip("/")
        except Exception:
            pass
    return default


def _vbox_opener(sp=None):
    handlers = [urllib.request.ProxyHandler(_vbox_proxy(sp))]
    if _SSL_CTX is not None:
        handlers.append(urllib.request.HTTPSHandler(context=_SSL_CTX))
    return urllib.request.build_opener(*handlers)


# ============================================================ 常量（asm 提取）
CONFIG_URL = "https://public.mino02.live/host_pwa.txt"
CFG_KEY_B64 = "h7lkUI0kb25Usb3qTFLefTf8b+8Hs2Y63sANNraUm/Q="
CFG_IV_B64 = "k54Vcjbp6ByR6D83eIoxgw=="
RESP_KEY = b"ae52f7ffd2dd66ba5743bb180188b991"
TOKEN_DEFAULT = ("eyJ1c2VyX2lkIjozMDQ1OTg4NjEsImxhc3Rsb2dpbiI6MTc2Mjg3MTA1MH0"
                 ".a568a4b03a8d6c08c14494d85c40a9f1"
                 ".7c6579106b5199d2177be390fc8c608b73bfc0cf63a2d853da78afab")
UA = "okhttp/3.14.9"


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


def _json_first(text):
    """配置/明文前后有 32 位校验，只取首个 JSON 对象。"""
    cand = [i for i in (text.find("{"), text.find("[")) if i >= 0]
    if not cand:
        return None
    i = min(cand)
    try:
        obj, _ = json.JSONDecoder().raw_decode(text[i:])
        return obj
    except Exception:
        return None


class MmMhCore(object):
    def __init__(self, spider):
        self.sp = spider
        self.timeout = 20
        self.token = TOKEN_DEFAULT
        self.base = ""          # 由配置解析得到
        self.img_host = ""
        self.comic_chain = ""
        self.stream_chain = ""
        self.stream_ts = ""
        self._cfg_ts = 0
        self._cache = {}        # id -> item（详情复用列表数据）

    # ---------------- HTTP ----------------
    def _open(self, req, timeout=None):
        t = timeout or self.timeout
        return _vbox_opener(self.sp).open(req, timeout=t)

    def _raw(self, url, hdrs=None, timeout=None):
        h = {"User-Agent": UA, "Accept": "application/json, */*"}
        if hdrs:
            h.update(hdrs)
        req = urllib.request.Request(url, headers=h)
        try:
            with self._open(req, timeout) as r:
                return r.status, dict(r.headers), r.read()
        except urllib.error.HTTPError as e:
            return e.code, dict(e.headers) if e.headers else {}, e.read()
        except Exception:
            return 0, {}, b""

    # ---------------- 配置 ----------------
    def ensure_config(self):
        if self.base and (time.time() - self._cfg_ts) < 3600:
            return self.base
        st, hd, body = self._raw(CONFIG_URL)
        if st != 200 or not body:
            self.base = self.base or "https://sdhvb.meme06.live"
            return self.base
        txt = body.decode("utf-8", "replace").strip()
        try:
            raw = base64.b64decode(txt + "=" * ((4 - len(txt) % 4) % 4))
            key = base64.b64decode(CFG_KEY_B64)
            iv = base64.b64decode(CFG_IV_B64)
            plain = _aes_cbc(key, iv, raw, encrypt=False).decode("utf-8", "replace")
            cfg = _json_first(plain) or {}
        except Exception:
            cfg = {}

        api = cfg.get("api") or []
        base = ""
        for a in api:
            if a.get("default") and a.get("status") == 1:
                base = a.get("url")
                break
        if not base and api:
            base = api[0].get("url") or ""
        self.base = (base or "https://sdhvb.meme06.live").rstrip("/")

        img = cfg.get("img") or []
        self.img_host = (img[0].get("url") if img else "https://image.meme06.live").rstrip("/")
        comic = cfg.get("comic") or []
        self.comic_chain = (comic[0].get("chain") if comic else "") or ""
        stream = cfg.get("stream") or []
        self.stream_chain = (stream[0].get("chain") if stream else "") or ""
        self.stream_ts = (stream[0].get("tsurl") if stream else "") or ""
        self._cfg_ts = time.time()
        return self.base

    # ---------------- 业务请求（含响应解密） ----------------
    def call(self, path, qp=None):
        base = self.ensure_config()
        url = base + path + (("?" + urllib.parse.urlencode(qp)) if qp else "")
        st, hd, body = self._raw(url, {"Authorization": "Bearer " + self.token})
        keys = {k.lower(): v for k, v in hd.items()}
        xlen = keys.get("x-response-length")
        if not xlen:
            # 明文（错误体）
            try:
                return json.loads(body.decode("utf-8", "replace"))
            except Exception:
                return {}
        txt = body.decode("utf-8", "replace").strip()
        try:
            raw = base64.b64decode(txt + "=" * ((4 - len(txt) % 4) % 4))
            iv = hashlib.md5(str(xlen).encode()).hexdigest()[8:24].encode()
            plain = _aes_cbc(RESP_KEY, iv, raw, encrypt=False).decode("utf-8", "replace")
            return _json_first(plain) or {}
        except Exception:
            return {}

    # ---------------- 映射 ----------------
    def _pic(self, item):
        cov = item.get("cover") or item.get("thumbpath") or item.get("coverpath") or ""
        if not cov:
            return ""
        if cov.startswith("http"):
            return cov
        return (self.img_host or "") + cov

    def _item(self, it):
        mid = it.get("id")
        if mid is not None:
            self._cache[str(mid)] = it
        remarks = []
        if it.get("duration"):
            remarks.append(str(it.get("duration")))
        if it.get("ep") and it.get("max_ep"):
            remarks.append("%s/%s集" % (it.get("ep"), it.get("max_ep")))
        if it.get("view_count"):
            remarks.append("%s播放" % it.get("view_count"))
        return {
            "vod_id": str(mid),
            "vod_name": (it.get("name") or "").strip() or "无标题",
            "vod_pic": self._pic(it),
            "vod_remarks": " · ".join(remarks),
            "style": {"type": "rect", "ratio": 0.75},
        }

    # ---------------- 能力 ----------------
    def categories(self):
        out = []
        for kind, path in (("a", "/v1/animat/category"), ("f", "/v1/fiction/category")):
            j = self.call(path)
            d = (j.get("success") or {}).get("data") if isinstance(j, dict) else None
            if not isinstance(d, list):
                continue
            for c in d:
                cid = c.get("category_id")
                title = (c.get("title") or "").strip()
                if cid is None or not title:
                    continue
                # type_id 编码：a=动画 type1，f=小说
                out.append({"type_id": "%s:%s" % (kind, cid),
                            "type_name": title})
        if not out:
            out = [{"type_id": "a:7", "type_name": "校园"}]
        return out

    def list(self, tid, page):
        tid = str(tid or "")
        kind, _, cid = tid.partition(":")
        if not cid:
            kind, cid = "a", tid
        page = max(1, int(page))
        if kind == "f":
            j = self.call("/v1/fiction/category/list",
                          {"category_id": cid, "type": 1, "page": page})
        else:
            j = self.call("/v1/animat/category/list",
                          {"category_id": cid, "type": 1, "page": page})
        d = (j.get("success") or {}) if isinstance(j, dict) else {}
        items = d.get("data") or []
        if not isinstance(items, list):
            return []
        return [self._item(it) for it in items if it.get("id")]

    def detail(self, vid):
        it = self._cache.get(str(vid))
        if not it:
            # 兜底：翻前几页找
            for c in self.categories()[:4]:
                for pg in (1, 2):
                    self.list(c["type_id"], pg)
                    if str(vid) in self._cache:
                        it = self._cache[str(vid)]
                        break
                if it:
                    break
        if not it:
            return {}

        title = (it.get("name") or "").strip() or ("迷妹 #%s" % vid)
        tags = it.get("tag") or []
        meta = []
        if it.get("avkey"):
            meta.append("番号：%s" % it.get("avkey"))
        if it.get("duration"):
            meta.append("时长：%s" % it.get("duration"))
        if it.get("ep"):
            meta.append("集数：%s/%s" % (it.get("ep"), it.get("max_ep") or "?"))
        if it.get("view_count"):
            meta.append("播放：%s" % it.get("view_count"))
        if it.get("studio"):
            meta.append("制作：%s" % it.get("studio"))
        if tags:
            meta.append("标签：%s" % " / ".join([str(t) for t in tags[:12]]))

        base = self.ensure_config()
        avkey = it.get("avkey") or ""
        plays = []
        # 按 UrlUtil::mmMhAnim 的模板拼（缺 host/chain/encrypt/token 会 500）
        if avkey:
            for label, q in (("正片 720", "720"), ("标清 240", "240"),
                             ("预览", "intro")):
                url = ("%s/v1/animat/pwa/media/%s/%s.m3u8"
                       "?host=%s&chain=%s&encrypt=true&token=%s"
                       % (base, q, avkey, self.token,
                          self.stream_chain, self.token))
                plays.append("%s$%s" % (label, url))

        desc = "\n".join(meta)
        desc = desc.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
        return {
            "vod_id": str(vid),
            "vod_name": title,
            "vod_pic": self._pic(it),
            "vod_content": desc,
            "vod_play_url": "#".join(plays),
        }

    def search(self, kw, page=1):
        out = []
        for path, qp in (("/v1/search/animat", {"keyword": kw, "page": page}),
                         ("/v1/search/fiction", {"keyword": kw, "page": page})):
            j = self.call(path, qp)
            d = (j.get("success") or {}) if isinstance(j, dict) else {}
            items = d.get("data") or []
            if isinstance(items, list):
                out += [self._item(it) for it in items if it.get("id")]
            if out:
                break
        return out


class Spider(SpiderBase):
    MODULE = "mmmh"
    NAME = "迷妹漫画"

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
        self._core = MmMhCore(self)
        if ext.get("token"):
            self._core.token = str(ext["token"])
        if ext.get("host"):
            self._core.base = str(ext["host"]).rstrip("/")
        try:
            self.timeout = int(ext.get("timeout") or 20)
        except Exception:
            self.timeout = 20
        self._core.timeout = self.timeout
        # 客户端注入的自定义域名优先
        try:
            inj = _vbox_host(self, "")
            if inj:
                self._core.base = inj
        except Exception:
            pass
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
            self._core = MmMhCore(self)
        return self._core

    # ---------------- vbox 接口 ----------------
    def homeContent(self, filter):
        try:
            cls = self._c().categories()
        except Exception:
            cls = []
        return {"class": cls, "list": []}

    def homeVideoContent(self):
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
        return {"parse": 0, "url": url,
                "header": {"User-Agent": UA,
                           "Referer": (self._c().base or "https://meme06.live") + "/",
                           "Authorization": "Bearer " + self._c().token}}

    def searchContent(self, key, quick, pg="1"):
        try:
            page = int(pg or 1)
        except Exception:
            page = 1
        try:
            items = self._c().search(str(key), page)
        except Exception:
            items = []
        return {
            "list": items,
            "page": page,
            "pagecount": page + 1 if items else page,
            "limit": len(items),
            "total": len(items),
        }

    def localProxy(self, param):
        return [404, "text/plain; charset=utf-8", b"", {}]
