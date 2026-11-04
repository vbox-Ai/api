#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""麻豆TV（mdtv）— vbox 自包含适配器

协议来源：libapp.so blutter 反汇编
    package:avbox/module/mdtv/network/interceptor.dart  (MdTvInterceptor::onRequest / onResponse)
    package:avbox/module/mdtv/network/service.dart      (MdTvHttp::post)
    package:avbox/module/mdtv/page/{home,video,channel,tag,search}_page.dart
────────────────────────────────────────────────────────────────────────────
请求（onRequest 逐条对齐，0x8d5ae8~0x8d5ee4）
    biz = {业务参数}
    biz["timestamp"] = DateTime._getCurrentMicros() / 1000        ← 毫秒
    joined = "&".join(f"{encodeComponent(k)}={v}" for k in sorted(biz.keys()))
    biz["encode_sign"] = MD5(joined + SECRET)
    post-data = base64( AES-256-CBC(jsonEncode(biz), key=KEY, iv="-p9B[~PnPsJGDZMX") )
    body   = {"post-data": post-data}
    headers: suffix: JGDZMX  +  Content-Type: application/json

响应（onResponse 0x8f2f28）
    {"suffix":"<6hex>","data":"<base64>"}
    iv = "-p9B[~PnPs" + suffix（9+6=15）→ 补齐 16 → AES-256-CBC 解密 → JSON
    信封 {"code":0,"msg":"操作成功","data":{...}}

接口（全部 POST，路径不带前导斜杠）
    video/channel   分类（动态键 channel）
    video/tags      标签（动态键 tags）
    video/listcache 推荐/分区/标签列表  biz={page,list_row:120,type:4[,channel|tags]}
    video/list      搜索              biz={page,list_row,keyword}
    播放：列表项自带 video_url，是 HLS m3u8 直链（AES-128 分段，enc.key 同目录匿名可取），
          客户端没有 /video/detail 与 /video/play —— 详情页数据全部来自列表项。

坑（本轮踩实的两条，上一轮就死在这里）
    1) **请求头必须带 `suffix: JGDZMX`**。服务端用 "suffix" 头还原请求 IV
       （"-p9B[~PnPs" + 头值）。不带 → 请求体解不开 → 业务层空参 →
       {"code":1002,"msg":"参数错误"}，而响应照样能用 KEY 解开，
       于是现象极像「参数名不对」，实际与参数无关。
    2) **签名 SECRET 无反斜杠**：
         错：&m}q%ea6:LDcmS\\?aK)CeF287bPvd99@E,9Up^   （blutter 把 `?` 印成了 `\\?`）
         对：&m}q%ea6:LDcmS?aK)CeF287bPvd99@E,9Up^     （libapp.so 偏移 367007 原始字节）
       带反斜杠 → 请求体能解开但 {"code":1001,"msg":"签名错误"}。
    3) biz 的 type 常量是 4，list_row 客户端固定 120（可改小，服务端接受）。
"""

import base64
import hashlib
import json
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


BASE_DEFAULT = "https://spi.d5c4a712.com"
KEY = b"Vq234zBeSdGgYXzVTEfnnjjdmaTkk7A4"      # 32B → AES-256
REQ_IV = b"-p9B[~PnPsJGDZMX"                   # 16B（"-p9B[~PnPs" + suffix 头值）
RESP_IV_HEAD = "-p9B[~PnPs"                    # 响应 IV 前缀，后接响应 suffix
SUFFIX = "JGDZMX"                              # 平台标识，请求头 suffix
SECRET = "&m}q%ea6:LDcmS?aK)CeF287bPvd99@E,9Up^"
UA = "Dart/3.4 (dart:io)"

# ⚠ 客户端的 homeContent 有 20s 总预算（PythonBridgeEngine.timeout），
#   一旦分类拉取（video/channel + video/tags 两跳）超时，整次调用被判失败 →
#   首页报「未能解析到分类，请检查域名或网络」。
#   所以 homeContent **只给 3s 的快速预算**，拿不到就用这份内置快照（实测值，可离线）。
STATIC_CLASSES = [
    {"type_id": "rec", "type_name": "推荐"},
    {"type_id": "c:21", "type_name": "麻豆传媒映画"},
    {"type_id": "c:20", "type_name": "91制作"},
    {"type_id": "c:51", "type_name": "91茄子"},
    {"type_id": "c:23", "type_name": "探花系列"},
    {"type_id": "c:14", "type_name": "SWAG"},
    {"type_id": "c:39", "type_name": "日本AV-4K"},
    {"type_id": "c:101", "type_name": "乐播传媒"},
    # 快速路径下补上的热门标签（t: 前缀 → video/listcache 的 tags 参数）
    {"type_id": "t:99", "type_name": "#热门推荐"},
    {"type_id": "t:62", "type_name": "#国产"},
    {"type_id": "t:102", "type_name": "#麻豆"},
    {"type_id": "t:104", "type_name": "#SWAG"},
    {"type_id": "t:43", "type_name": "#巨乳"},
    {"type_id": "t:47", "type_name": "#美少女"},
    {"type_id": "t:46", "type_name": "#裤袜"},
    {"type_id": "t:27", "type_name": "#萝莉系"},
]
QUICK_TIMEOUT = 3.0

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


class MdtvCore(object):
    CATE_REC = "rec"

    def __init__(self, spider):
        self.sp = spider
        self.base = BASE_DEFAULT
        self.timeout = 20
        self._cache = {}          # vod_id -> 列表项原始 dict
        self._last_page = {}      # vod_id / tid -> last_page
        self._classes = None      # homeContent 缓存

    def _open(self, req, timeout=None):
        t = timeout if timeout is not None else getattr(self, "timeout", 20)
        return _vbox_opener(getattr(self, "sp", None)).open(req, timeout=t)

    # ---------------- 封面走客户端本地代理 ----------------
    def _px(self, url):
        """封面统一经客户端本地受控代理（127.0.0.1:18080 + key=平台标识）。

        原因：客户端 img 加载器对 `application/octet-stream` / `application/x-image`
        这类非标准 Content-Type 会直接放弃（javdb 的 tp.spfcas.com、kpsp 的 .image 都是这种）；
        另外部分 CDN 有防盗链。走代理后由 Python 侧带 UA 取字节、嗅探真实类型再回给客户端。
        """
        u = (url or "").strip()
        if not u:
            return ""
        if u.startswith("//"):
            u = "https:" + u
        if not u.startswith("http"):
            return u
        base = ""
        try:
            base = self.sp.getProxyUrl()      # 客户端 base.spider 提供（含 do=py&key=…）
        except Exception:
            base = ""
        if not base:
            base = "http://127.0.0.1:18080/proxy?do=py&key=%s" % getattr(self.sp, "MODULE", "")
        return base + "&url=" + urllib.parse.quote(u, safe="")


    # ---------------- 加解密 / 签名 ----------------
    @staticmethod
    def _sign(biz):
        """按 onRequest 顺序签名：先塞毫秒 timestamp，再按 key 排序拼串。"""
        mp = dict(biz)
        mp["timestamp"] = int(time.time() * 1000)
        joined = "&".join("%s=%s" % (k, mp[k]) for k in sorted(mp.keys()))
        mp["encode_sign"] = hashlib.md5((joined + SECRET).encode("utf-8")).hexdigest()
        return mp

    def _dec(self, raw):
        """响应解密：{"suffix","data"} → dict。"""
        txt = raw.decode("utf-8", "replace").strip()
        if not txt:
            return {}
        try:
            j = json.loads(txt)
        except Exception:
            return {}
        if not isinstance(j, dict) or "data" not in j:
            return j if isinstance(j, dict) else {}
        d = j.get("data")
        if not isinstance(d, str):
            return j
        suf = str(j.get("suffix") or "")
        body = d + "=" * ((4 - len(d) % 4) % 4)
        try:
            blob = base64.b64decode(body)
        except Exception:
            return {}
        iv = (RESP_IV_HEAD + suf)[:16].ljust(16, "\x00").encode("utf-8")
        try:
            plain = _aes_cbc(KEY, iv, blob, encrypt=False)
            return json.loads(plain.decode("utf-8", "replace").rstrip("\x00"))
        except Exception:
            return {"code": -1, "msg": "解密失败 suffix=%s" % suf}

    # ---------------- 请求 ----------------
    def call(self, path, biz=None, timeout=None):
        mp = self._sign(biz or {})
        plain = json.dumps(mp, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
        post = base64.b64encode(_aes_cbc(KEY, REQ_IV, plain, encrypt=True)).decode()
        body = json.dumps({"post-data": post}).encode("utf-8")
        url = self.base.rstrip("/") + "/" + str(path).lstrip("/")
        req = urllib.request.Request(url, data=body, method="POST", headers={
            "User-Agent": UA,
            "Content-Type": "application/json",
            "Accept": "*/*",
            "suffix": SUFFIX,          # ← 缺这一行就是 1002 参数错误
        })
        try:
            with self._open(req, timeout) as r:
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
        vid = it.get("id")
        if vid is not None:
            self._cache[str(vid)] = it
        tags = [t.get("name") for t in (it.get("tags") or []) if isinstance(t, dict)]
        remarks = []
        if it.get("comefrom_title"):
            remarks.append(str(it.get("comefrom_title")))
        if tags:
            remarks.append("/".join([x for x in tags[:3] if x]))
        pic = it.get("thumb") or it.get("preview") or it.get("panorama") or ""
        return {
            "vod_id": str(vid),
            "vod_name": (it.get("title") or "").strip() or ("麻豆 #%s" % vid),
            "vod_pic": self._px(pic),
            "vod_remarks": " · ".join([x for x in remarks if x]),
            "style": {"type": "rect", "ratio": 0.5625},
        }

    def _list_biz(self, tid, page, per=120):
        biz = {"page": int(page), "list_row": int(per), "type": 4}
        t = str(tid or self.CATE_REC)
        if t.startswith("c:"):
            try:
                biz["channel"] = int(t[2:])
            except Exception:
                pass
        elif t.startswith("t:"):
            try:
                biz["tags"] = int(t[2:])
            except Exception:
                pass
        return biz

    def list_page(self, tid, page, per=120):
        j = self.call("video/listcache", self._list_biz(tid, page, per))
        d = j.get("data") or {}
        items = d.get("data") if isinstance(d, dict) else None
        if not isinstance(items, list):
            items = []
        hits = [self._item(it) for it in items if isinstance(it, dict)]
        last = 1
        try:
            last = int(d.get("last_page") or 1)
        except Exception:
            pass
        return hits, last

    def search_page(self, key, page, per=20):
        j = self.call("video/list", {"page": int(page), "list_row": int(per),
                                     "keyword": str(key)})
        d = j.get("data") or {}
        items = d.get("data") if isinstance(d, dict) else None
        if not isinstance(items, list):
            items = []
        hits = [self._item(it) for it in items if isinstance(it, dict)]
        last = 1
        try:
            last = int(d.get("last_page") or 1)
        except Exception:
            pass
        return hits, last

    def classes(self, quick=False):
        """分类 = 推荐 + 频道（channel）+ 热门标签（tags）。

        quick=True（homeContent 用）：只给 QUICK_TIMEOUT 秒预算，失败/超时回退内置快照，
        保证首页永远能出分类（否则客户端 20s 总预算被打满 → 「未能解析到分类」）。
        """
        if self._classes is not None:
            return self._classes
        tmo = QUICK_TIMEOUT if quick else None
        out = [{"type_id": self.CATE_REC, "type_name": "推荐"}]
        try:
            j = self.call("video/channel", timeout=tmo)
            chans = j.get("data")
            if isinstance(chans, dict):
                chans = chans.get("data")
            for c in (chans or []):
                if not isinstance(c, dict) or c.get("id") is None:
                    continue
                out.append({"type_id": "c:%s" % c.get("id"),
                            "type_name": str(c.get("name") or c.get("id"))})
        except Exception:
            pass
        if quick:                              # 快速路径只拉一跳（channel），标签用内置快照补齐
            if len(out) < 2:
                self._classes = [dict(x) for x in STATIC_CLASSES]
                return self._classes
            out.extend([dict(x) for x in STATIC_CLASSES if x["type_id"].startswith("t:")])
            self._classes = out
            return out
        try:
            j = self.call("video/tags", timeout=tmo)
            tags = j.get("data")
            if isinstance(tags, dict):
                tags = tags.get("data")
            hot = [t for t in (tags or []) if isinstance(t, dict) and t.get("id") is not None]
            hot.sort(key=lambda x: (-int(x.get("is_hot") or 0), -int(x.get("order") or 0)))
            for t in hot[:40]:
                out.append({"type_id": "t:%s" % t.get("id"),
                            "type_name": "#" + str(t.get("name") or t.get("id"))})
        except Exception:
            pass
        if len(out) < 2:                      # 网络没通：用内置快照兜底
            self._classes = [dict(x) for x in STATIC_CLASSES]
            return self._classes
        self._classes = out
        return out

    def find(self, vid):
        """列表项即详情/播放的数据源，miss 则翻 3 页推荐列表回溯。"""
        key = str(vid)
        if key in self._cache:
            return self._cache[key]
        for pg in (1, 2, 3):
            self.list_page(self.CATE_REC, pg)
            if key in self._cache:
                return self._cache[key]
        return {}

    def detail(self, vid):
        it = self.find(vid)
        if not it:
            return {}
        meta = []
        if it.get("description"):
            meta.append(str(it.get("description")))
        if it.get("comefrom_title"):
            meta.append("片商：%s" % it.get("comefrom_title"))
        tags = [t.get("name") for t in (it.get("tags") or []) if isinstance(t, dict)]
        if tags:
            meta.append("标签：%s" % "、".join([x for x in tags if x]))
        if it.get("try_second"):
            meta.append("试看：%s 秒" % it.get("try_second"))
        meta.append("VIP：%s" % ("是" if int(it.get("is_vip") or 0) else "否"))
        play = (it.get("video_url") or "").strip()
        if play:
            meta.append("直链：%s" % play)
        desc = "\n".join(meta)
        desc = desc.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
        return {
            "vod_id": str(vid),
            "vod_name": (it.get("title") or "").strip() or ("麻豆 #%s" % vid),
            "vod_pic": self._px(it.get("thumb") or it.get("preview") or ""),
            "vod_content": desc,
            "vod_play_url": ("正片$%s" % play) if play else "",
        }

    def play(self, vid):
        it = self.find(vid)
        u = (it.get("video_url") or "").strip()
        if u:
            return {"parse": 0, "url": u,
                    "header": {"User-Agent": UA, "Referer": self.base.rstrip("/") + "/"}}
        tv = (it.get("test_video_url") or "").strip()   # 试看片段（相对路径）
        if tv.startswith("/"):
            m3 = "https://m3md.n6uem8.xyz" + tv
            return {"parse": 0, "url": m3,
                    "header": {"User-Agent": UA, "Referer": self.base.rstrip("/") + "/"}}
        return None


class Spider(SpiderBase):
    MODULE = "mdtv"
    NAME = "麻豆TV"

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
        self._core = MdtvCore(self)
        if ext.get("host"):
            self._core.base = str(ext["host"]).rstrip("/")
        try:
            self.timeout = int(ext.get("timeout") or 20)
        except Exception:
            self.timeout = 20
        self._core.timeout = self.timeout
        # 客户端注入的自定义域名优先于脚本内置默认值
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
            self._core = MdtvCore(self)
        return self._core

    # ---------------- vbox 接口 ----------------
    def homeContent(self, filter):
        try:
            cls = self._c().classes(quick=True)
        except Exception:
            cls = [dict(x) for x in STATIC_CLASSES]
        return {"class": cls, "list": []}

    def homeVideoContent(self):
        # 注意：客户端的首页探测会顺带调这里，联网会把 20s 总预算吃光 —— 直接返回空，
        # 首屏数据交给 categoryContent('rec', 1) 去取。
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

    def _core_open(self, req):
        return self._c()._open(req, 20)

    def localProxy(self, param):
        """受控代理：取图 → 嗅探真实类型 → 回给客户端（避免 Content-Type 被拒 / 防盗链）。"""
        p = param or {}
        if isinstance(p, str):
            p = dict(urllib.parse.parse_qsl(p.lstrip("?")))
        url = ""
        if isinstance(p, dict):
            url = p.get("url") or p.get("u") or ""
        if not url:
            return [400, "text/plain; charset=utf-8", b"missing url", {}]
        if url.startswith("//"):
            url = "https:" + url
        try:
            ref = "/".join(url.split("/")[:3]) + "/"
            req = urllib.request.Request(url, headers={
                "User-Agent": UA, "Referer": ref, "Accept": "image/*,*/*"})
            with self._core_open(req) as r:
                raw = r.read()
                ct = (r.headers.get("Content-Type") or "").lower()
        except Exception as e:
            return [502, "text/plain; charset=utf-8", str(e)[:120].encode("utf-8"), {}]
        if raw[:3] == b"\xff\xd8\xff":
            ct = "image/jpeg"
        elif raw[:8] == b"\x89PNG\r\n\x1a\n":
            ct = "image/png"
        elif raw[:4] == b"GIF8":
            ct = "image/gif"
        elif raw[:4] == b"RIFF" and raw[8:12] == b"WEBP":
            ct = "image/webp"
        elif not ct.startswith("image/"):
            ct = "image/jpeg"
        return [200, ct, raw, {"Cache-Control": "max-age=86400"}]

