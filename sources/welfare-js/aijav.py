#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""AiJav（aijav）— vbox 自包含适配器

协议来源：libapp.so blutter 反汇编
    package:avbox/module/aijav/network/interceptor.dart  (onRequest @0x8d544c / onResponse @0x8efe30)
    package:avbox/module/aijav/network/service.dart
    package:avbox/module/aijav/page/{home,video,classify,actor,series,search}_page.dart
────────────────────────────────────────────────────────────────────────────
与 mdtv 同构（同一套 encrypt 包胶水层），差异只在 4 个常量：

    SECRET  = "&NRkw0g3iJLDvw5tJ5PuVt5276z0SOuyL"        libapp.so @500125
    KEY     = "0XxdjmI55ZjjqQLO3nI7gGqrBP0Vz9jS"  (32B)  libapp.so @322372
    REQ_IV  = "RWf23muavYNWSdef"                 (16B)  libapp.so @944669
    头      suffix: "NWSdef"                             libapp.so @572092
    响应 IV = "RWf23muavY" + 响应体 suffix               @0x8efe68

请求：biz → 塞入毫秒 timestamp → 按键排序拼 "k=v&…" → encode_sign=MD5(串+SECRET)
      → base64(AES-256-CBC(json)) 装 {"post-data"}；头 Content-Type + suffix
响应：{"suffix","data"} → iv="RWf23muavY"+suffix → AES-256-CBC → JSON；**成功码是 1 不是 0**

接口
    video/lists     首页 {page,limit:54,type:8}
                    分区 {page,limit:40,tag_id|actor_id|publisher_id:<id>}
                    搜索 {page,limit,keyword}
    video/info      详情 {vid:<id>}        ← 参数名是 vid，不是 id（id 会报 3001 视频不存在）
    tag/lists       标签 {page,limit}
    actor/lists     演员 {page,limit}
    publisher/lists 片商 {page,limit}

播放：**受限**。列表项与 video/info 都不含媒体直链（只有 thumb/preview 图片、字幕 vtt），
      `private` / `video_point` / `is_purchase` 是购买标记；取流相关路由
      （video/play|url|m3u8|source…）全部 999「网络异常」= 路由不存在，
      `video/purchase`、`video/collect` 返回 2000「登录已失效」。
      → 结论：播放需登录 + 点数购买，匿名态拿不到 m3u8。本适配器交付分类/列表/详情三能力。

坑
    1) 成功码是 1（不是 0），判空别只认 code==0
    2) 路由不存在 = {"code":999}，参数/业务错 = 其它业务码 —— 用这个判据扫接口比猜路径快
    3) **别照抄 mdtv 的键名**：这里详情是 vid，列表是 page/limit（mdtv 是 list_row + type）
"""

import base64
import hashlib
import json
import time
import urllib.error
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


BASE_DEFAULT = "https://newavapi.9xyrp3kg4b86.com"
KEY = b"0XxdjmI55ZjjqQLO3nI7gGqrBP0Vz9jS"      # 32B → AES-256
REQ_IV = b"RWf23muavYNWSdef"                   # 16B（"RWf23muavY" + suffix 头值）
RESP_IV_HEAD = "RWf23muavY"
SUFFIX = "NWSdef"
SECRET = "&NRkw0g3iJLDvw5tJ5PuVt5276z0SOuyL"
UA = "Dart/3.4 (dart:io)"
IMG_HOST = "https://mmjs.1vkx.cn"              # 图片相对路径的兜底前缀

# ============================================================ vbox 运行时适配
# 客户端 base.spider 只给 requests 打了「代理 + verify=False」补丁，裸 urllib 不走；
# 而 iOS CPython 无系统 CA 证书包 —— urllib 的 HTTPS 会全部 SSLError。
# 现象即「分类能显示（本地静态），点进去没有数据（联网失败）」。
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
    """带 SSL 放行 + 客户端代理 的 opener。"""
    handlers = [urllib.request.ProxyHandler(_vbox_proxy(sp))]
    if _SSL_CTX is not None:
        handlers.append(urllib.request.HTTPSHandler(context=_SSL_CTX))
    return urllib.request.build_opener(*handlers)


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


class AijavCore(object):
    CATE_HOME = "home"

    def __init__(self, spider):
        self.sp = spider
        self.base = BASE_DEFAULT
        self.timeout = 20
        self._cache = {}        # vod_id -> video/info data
        self._classes = None

    def _open(self, req, timeout=None):
        t = timeout if timeout is not None else getattr(self, "timeout", 20)
        return _vbox_opener(getattr(self, "sp", None)).open(req, timeout=t)

    # ---------------- 加解密 / 签名 ----------------
    @staticmethod
    def _sign(biz):
        mp = dict(biz)
        mp["timestamp"] = int(time.time() * 1000)
        joined = "&".join("%s=%s" % (k, mp[k]) for k in sorted(mp.keys()))
        mp["encode_sign"] = hashlib.md5((joined + SECRET).encode("utf-8")).hexdigest()
        return mp

    def _dec(self, raw):
        txt = raw.decode("utf-8", "replace").strip()
        if not txt:
            return {}
        try:
            j = json.loads(txt)
        except Exception:
            return {}
        if not isinstance(j, dict) or not isinstance(j.get("data"), str):
            return j if isinstance(j, dict) else {}
        d = j.get("data")
        suf = str(j.get("suffix") or "")
        blob = base64.b64decode(d + "=" * ((4 - len(d) % 4) % 4))
        iv = (RESP_IV_HEAD + suf)[:16].ljust(16, "\x00").encode("utf-8")
        try:
            plain = _aes_cbc(KEY, iv, blob, encrypt=False)
            return json.loads(plain.decode("utf-8", "replace").rstrip("\x00"))
        except Exception:
            return {"code": -1, "msg": "解密失败 suffix=%s" % suf}

    # ---------------- 请求 ----------------
    def call(self, path, biz=None):
        mp = self._sign(biz or {})
        plain = json.dumps(mp, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
        post = base64.b64encode(_aes_cbc(KEY, REQ_IV, plain, encrypt=True)).decode()
        body = json.dumps({"post-data": post}).encode("utf-8")
        url = self.base.rstrip("/") + "/" + str(path).lstrip("/")
        req = urllib.request.Request(url, data=body, method="POST", headers={
            "User-Agent": UA,
            "Content-Type": "application/json",
            "Accept": "*/*",
            "suffix": SUFFIX,          # ← 缺这一行就是 999/1002 一类的泛化错误
        })
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
    @staticmethod
    def _pic(path):
        p = (path or "").strip()
        if not p:
            return ""
        if p.startswith("http"):
            return p
        return IMG_HOST + (p if p.startswith("/") else "/" + p)

    def _item(self, it):
        remarks = []
        if it.get("mash"):
            remarks.append(str(it.get("mash")))
        if it.get("duration"):
            remarks.append(str(it.get("duration")))
        acts = [a.get("name") for a in (it.get("actor") or []) if isinstance(a, dict)]
        if acts:
            remarks.append(acts[0])
        return {
            "vod_id": str(it.get("id")),
            "vod_name": (it.get("title") or "").strip() or ("AiJav #%s" % it.get("id")),
            "vod_pic": self._pic(it.get("thumb") or it.get("preview")),
            "vod_remarks": " · ".join([x for x in remarks if x]),
            "style": {"type": "rect", "ratio": 1.5},
        }

    def _page(self, path, biz):
        j = self.call(path, biz)
        d = j.get("data") or {}
        items = d.get("data") if isinstance(d, dict) else None
        if not isinstance(items, list):
            items = []
        last = 1
        try:
            last = int(d.get("last_page") or 1)
        except Exception:
            pass
        return [self._item(it) for it in items if isinstance(it, dict) and it.get("id")], last

    def list_page(self, tid, page):
        t = str(tid or self.CATE_HOME)
        if t.startswith("tag:"):
            biz = {"page": int(page), "limit": 40, "tag_id": int(t[4:])}
        elif t.startswith("actor:"):
            biz = {"page": int(page), "limit": 40, "actor_id": int(t[6:])}
        elif t.startswith("publisher:"):
            biz = {"page": int(page), "limit": 40, "publisher_id": int(t[10:])}
        else:
            biz = {"page": int(page), "limit": 54, "type": 8}
        return self._page("video/lists", biz)

    def search_page(self, key, page, per=20):
        return self._page("video/lists", {"page": int(page), "limit": int(per),
                                         "keyword": str(key)})

    def classes(self):
        """首页 + 热门标签 + 主要片商（都来自服务端，失败只剩首页）。"""
        if self._classes is not None:
            return self._classes
        out = [{"type_id": self.CATE_HOME, "type_name": "最新"}]
        try:
            j = self.call("tag/lists", {"page": 1, "limit": 60})
            tags = (j.get("data") or {}).get("data") or []
            tags = [t for t in tags if isinstance(t, dict) and t.get("id") is not None]
            tags.sort(key=lambda x: -int(x.get("video_count") or 0))
            for t in tags[:30]:
                out.append({"type_id": "tag:%s" % t.get("id"),
                            "type_name": "#" + str(t.get("name") or t.get("id"))})
        except Exception:
            pass
        try:
            j = self.call("publisher/lists", {"page": 1, "limit": 30})
            pubs = (j.get("data") or {}).get("data") or []
            pubs = [p for p in pubs if isinstance(p, dict) and p.get("id") is not None]
            pubs.sort(key=lambda x: -int(x.get("video_count") or 0))
            for p in pubs[:15]:
                out.append({"type_id": "publisher:%s" % p.get("id"),
                            "type_name": str(p.get("name") or p.get("id"))})
        except Exception:
            pass
        self._classes = out
        return out

    def info(self, vid):
        key = str(vid)
        if key in self._cache:
            return self._cache[key]
        j = self.call("video/info", {"vid": int(vid)})
        d = j.get("data")
        d = d if isinstance(d, dict) else {}
        if d:
            self._cache[key] = d
        return d

    def detail(self, vid):
        d = self.info(vid)
        if not d:
            return {}
        meta = []
        if d.get("mash"):
            meta.append("番号：%s" % d.get("mash"))
        if d.get("duration"):
            meta.append("时长：%s" % d.get("duration"))
        if d.get("publish_date"):
            meta.append("发行：%s" % d.get("publish_date"))
        acts = [a.get("name") for a in (d.get("actor") or []) if isinstance(a, dict)]
        if acts:
            meta.append("演员：%s" % "、".join([x for x in acts if x]))
        pb = d.get("publisher") or {}
        if isinstance(pb, dict) and pb.get("name"):
            meta.append("片商：%s" % pb.get("name"))
        tags = [t.get("name") for t in (d.get("tags") or []) if isinstance(t, dict)]
        if tags:
            meta.append("标签：%s" % "、".join([x for x in tags if x]))
        if d.get("rating_avg"):
            meta.append("评分：%s（%s 人）" % (d.get("rating_avg"), d.get("rating_count")))
        if d.get("play"):
            meta.append("播放：%s 次" % d.get("play"))
        meta.append("点数：%s" % d.get("video_point"))
        meta.append("播放能力：需登录 + 点数购买（匿名态服务端不下发 m3u8）")
        desc = "\n".join(meta)
        if d.get("description"):
            desc += "\n\n" + str(d.get("description"))
        desc = desc.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
        return {
            "vod_id": str(vid),
            "vod_name": (d.get("title") or "").strip() or ("AiJav #%s" % vid),
            "vod_pic": self._pic(d.get("thumb") or d.get("preview")),
            "vod_content": desc,
            # 没有直链：留空更诚实，客户端不会误起播放器
            "vod_play_url": "",
        }


class Spider(SpiderBase):
    MODULE = "aijav"
    NAME = "AiJav"

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
        self._core = AijavCore(self)
        if ext.get("host"):
            self._core.base = str(ext["host"]).rstrip("/")
        try:
            self.timeout = int(ext.get("timeout") or 20)
        except Exception:
            self.timeout = 20
        self._core.timeout = self.timeout
        try:
            _inj = _vbox_host(self, "")
            if _inj:
                for _attr in ("base", "host"):
                    if hasattr(self, _attr):
                        setattr(self, _attr, _inj)
                _core = getattr(self, "_core", None)
                if _core is not None:
                    for _attr in ("base", "host"):
                        if hasattr(_core, _attr):
                            setattr(_core, _attr, _inj)
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
            self._core = AijavCore(self)
        return self._core

    # ---------------- vbox 接口 ----------------
    def homeContent(self, filter):
        try:
            cls = self._c().classes()
        except Exception:
            cls = [{"type_id": "home", "type_name": "最新"}]
        return {"class": cls, "list": []}

    def homeVideoContent(self):
        try:
            items, _ = self._c().list_page("home", 1)
            return {"list": items}
        except Exception:
            return {"list": []}

    def categoryContent(self, tid, pg, filter, extend):
        try:
            page = int(pg or 1)
        except Exception:
            page = 1
        try:
            items, last = self._c().list_page(tid, page)
        except Exception:
            items, last = [], page
        return {
            "list": items,
            "page": page,
            "pagecount": max(last, page),
            "limit": len(items),
            "total": 99999 if items else 0,
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
        # 匿名态没有直链；如后续接入账号拿到 m3u8_url，在这里换成真实地址即可
        return {"parse": 0, "url": "",
                "header": {"User-Agent": UA, "Referer": BASE_DEFAULT + "/"}}

    def searchContent(self, key, quick, pg="1"):
        try:
            page = int(pg or 1)
        except Exception:
            page = 1
        try:
            items, last = self._c().search_page(key, page)
        except Exception:
            items, last = [], page
        return {"list": items, "page": page, "pagecount": max(last, page),
                "limit": len(items), "total": 9999 if items else 0}

    def localProxy(self, param):
        return [404, "text/plain; charset=utf-8", b"", {}]
