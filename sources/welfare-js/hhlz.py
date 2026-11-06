#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""嘿嘿连载（hhlz）— vbox 自包含适配器（漫画）

协议来源：抓包 + libapp.so 反汇编双证据
    抓包：`归档/2026-10-29-052251/64`（POST /comic/list，明文请求 + 加密响应）
    asm ：`module/hhlz/network/interceptor.dart`
          onRequest  @0x8de210 —— 设备参数逐个 [] =，**sign 是硬编码常量**
          onResponse @0x8f1548 —— AES(key="D2o4XyQeIFobJ4tS", iv="sciCuBC7orQtDhTO") → jsonDecode
────────────────────────────────────────────────────────────────────────────
请求（POST，全部 application/json，每请求都要带同一套设备参数）
    {"appId":"1","debug":"1","osType":"3","product":"1","ver":"6.0.1",
     "marketChannel":"LDY","sign":"d01ef895544ab4f2a1f4d38d66edb283",
     "sysVer":"13","proxyChannel":"LDY",
     "packageName":"com.t55f8907c5.z222ec9ed4.vcd6814de920260901",
     "time":<秒>,"phoneModel":"NX729J","udid":"<uuid4>", …业务参数}

响应
    {"code":0,"msg":"success","data":"<base64>","cimg":"1","capi":"1"}
    data = base64( AES-128-CBC(JSON, key, iv) )

接口
    /comic/list     {cat, page_num}            → search_box(分类) + list{list,total_page,total_count}
    /cartoon/info   {comic_id}                 → comic{…}
    /comic/catalog  {comic_id}                 → chapter_list[]
    /comic/chapter  {comic_id, chapter_id}     → image_list[].img（webp）

播放：漫画约定 —— `manga://` + 图片以 `&&` 连接（客户端渲染图片阅读器）。
坑：
    1) sign 不用算，是**常量**（asm 里直接写死，抓包也能看到）
    2) /comic/chapter 缺 comic_id 会返回 code=702
    3) 响应体可能是 gzip（Accept-Encoding: gzip），解完才是 JSON 信封
    4) homeContent 不联网（客户端 20s 总预算，交接文档坑表 #25）
"""

import base64
import gzip
import json
import time
import urllib.error
import urllib.parse
import urllib.request
import uuid

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

try:
    from Crypto.Cipher import AES
    from Crypto.Util.Padding import unpad
except Exception:
    AES = None

BASE_DEFAULT = "https://rrs0a03ak.pye57rf.com"
SIGN = "d01ef895544ab2f4a1f4d38d66edb283"[:0] or "d01ef895544ab4f2a1f4d38d66edb283"
PKG = "com.t55f8907c5.z222ec9ed4.vcd6814de920260901"
RESP_KEY = b"D2o4XyQeIFobJ4tS"
RESP_IV = b"sciCuBC7orQtDhTO"
# 图片解密：asm images/decrypt_image_byte.dart @0xa41bd4/@0xa41be8（/module/hhlz 分支）
IMG_KEY = b"saIZXc4yMvq0Iz56"
IMG_IV = b"kbJYtBJUECT0oyjo"
UA = "Dart/3.12 (dart:io)"
PROXY_BASE = "http://127.0.0.1:18080/proxy?do=py&key=hhlz_py&url="

# 分类（来自 /comic/list 的 search_box[0].list，取常用项固化；全量仍走接口）
STATIC_CLASSES = [
    {"type_id": "", "type_name": "全部"},
    {"type_id": "1", "type_name": "韩漫"},
    {"type_id": "2", "type_name": "日漫"},
    {"type_id": "25", "type_name": "3D漫画"},
    {"type_id": "6", "type_name": "全彩"},
    {"type_id": "7", "type_name": "Cosplay"},
    {"type_id": "527", "type_name": "写真"},
    {"type_id": "609", "type_name": "H漫"},
    {"type_id": "19", "type_name": "校园"},
    {"type_id": "605", "type_name": "乳交"},
    {"type_id": "603", "type_name": "口交"},
    {"type_id": "604", "type_name": "出轨"},
    {"type_id": "606", "type_name": "榨精"},
    {"type_id": "598", "type_name": "母女"},
]

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


class HhlzCore(object):
    def __init__(self, spider):
        self.sp = spider
        self.base = BASE_DEFAULT
        self.timeout = 20
        self.udid = str(uuid.uuid4())
        self._imgs = {}

    def _open(self, req, timeout=None):
        t = timeout if timeout is not None else getattr(self, "timeout", 20)
        return _vbox_opener(getattr(self, "sp", None)).open(req, timeout=t)

    @staticmethod
    def _dec_data(env):
        if not isinstance(env, dict):
            return env
        d = env.get("data")
        if not isinstance(d, str) or not d:
            return env
        try:
            raw = base64.b64decode(d + "=" * (-len(d) % 4))
            pt = AES.new(RESP_KEY, AES.MODE_CBC, RESP_IV).decrypt(raw)
            try:
                pt = unpad(pt, 16)
            except Exception:
                pass
            return json.loads(pt.decode("utf-8", "replace"))
        except Exception:
            return env

    def call(self, path, extra=None, timeout=None):
        payload = {
            "appId": "1", "debug": "1", "osType": "3", "product": "1", "ver": "6.0.1",
            "marketChannel": "LDY", "sign": SIGN, "sysVer": "13", "proxyChannel": "LDY",
            "packageName": PKG, "time": int(time.time()), "phoneModel": "NX729J",
            "udid": self.udid,
        }
        if extra:
            payload.update(extra)
        url = self.base.rstrip("/") + "/" + str(path).lstrip("/")
        req = urllib.request.Request(
            url, data=json.dumps(payload, ensure_ascii=False).encode(), method="POST",
            headers={"Content-Type": "application/json", "User-Agent": UA,
                     "Accept-Encoding": "gzip"})
        try:
            with self._open(req, timeout) as r:
                raw = r.read()
                if raw[:2] == b"\x1f\x8b":
                    try:
                        raw = gzip.decompress(raw)
                    except Exception:
                        pass
                env = json.loads(raw.decode("utf-8", "replace"))
        except urllib.error.HTTPError as e:
            try:
                raw = e.read()
                if raw[:2] == b"\x1f\x8b":
                    raw = gzip.decompress(raw)
                env = json.loads(raw.decode("utf-8", "replace"))
            except Exception:
                return {}
        except Exception:
            return {}
        return self._dec_data(env) or {}

    # ---------------- 映射 ----------------
    # ---------------- 图片：抓取 + AES 解密 + 内联 ----------------
    # 客户端（Flutter）内部没有 /proxy?do=py 路由，无法走本地代理；
    # 但漫画阅读器支持 `data:` 内联图 —— 所以这里直接把解密后的字节 base64 内联。
    @staticmethod
    def _dec_img(raw):
        if raw[:4] == b"RIFF" and raw[8:12] == b"WEBP":
            return raw
        try:
            pt = AES.new(IMG_KEY, AES.MODE_CBC, IMG_IV).decrypt(raw[:len(raw) // 16 * 16])
            try:
                pt = unpad(pt, 16)
            except Exception:
                pass
            return pt
        except Exception:
            return raw

    def _inline(self, url, timeout=None):
        """返回 data: URL；失败则回落原地址。"""
        u = (url or "").strip()
        if not u.startswith("http"):
            return u
        key = ("img", u)
        if key in self._imgs:
            return self._imgs[key]
        try:
            req = urllib.request.Request(u, headers={"User-Agent": UA, "Accept": "image/*,*/*"})
            with self._open(req, timeout or 15) as r:
                raw = r.read()
            raw = self._dec_img(raw)
            if raw[:4] == b"RIFF":
                mime = "image/webp"
            elif raw[:3] == b"\xff\xd8\xff":
                mime = "image/jpeg"
            elif raw[:4] == b"\x89PNG":
                mime = "image/png"
            else:
                mime = "image/jpeg"
            out = "data:%s;base64,%s" % (mime, base64.b64encode(raw).decode())
        except Exception:
            out = u
        self._imgs[key] = out
        return out

    def list_page(self, cat, page):
        d = self.call("/comic/list", {"cat": str(cat or ""), "page_num": int(page)})
        node = d.get("list") or {}
        items = node.get("list") if isinstance(node, dict) else None
        out = []
        for it in (items or []):
            if not isinstance(it, dict):
                continue
            cid = it.get("comic_id")
            if cid is None:
                continue
            rem = []
            if it.get("total_chapters"):
                rem.append("%s话" % it.get("total_chapters"))
            if it.get("is_finished") in (1, "1") or it.get("is_finish") in (1, "1"):
                rem.append("完结")
            if str(it.get("is_vip")) == "1":
                rem.append("VIP")
            out.append({
                "vod_id": str(cid),
                "vod_name": (it.get("name") or "").strip() or str(cid),
                "vod_pic": self._inline(it.get("cover") or it.get("vertical_cover") or ""),
                "vod_remarks": " · ".join(rem),
            })
        total_page = 0
        if isinstance(node, dict):
            try:
                total_page = int(node.get("total_page") or 0)
            except Exception:
                total_page = 0
        return out, total_page

    def detail(self, cid):
        info = self.call("/cartoon/info", {"comic_id": str(cid)}).get("comic") or {}
        cat = self.call("/comic/catalog", {"comic_id": str(cid)})
        chapters = cat.get("chapter_list") or []
        eps = []
        for ch in chapters:
            cpid = ch.get("chapter_id")
            if cpid is None:
                continue
            title = (ch.get("subtitle") or ch.get("chapter_title") or "").strip() or str(cpid)
            eps.append("%s$%s|%s" % (title, cid, cpid))
        desc = []
        if info.get("author"):
            desc.append("作者：%s" % info.get("author"))
        if info.get("total_chapters"):
            desc.append("章节：%s" % info.get("total_chapters"))
        if info.get("last_chapter_time"):
            desc.append("更新：%s" % info.get("last_chapter_time"))
        if info.get("tag"):
            desc.append("标签：%s" % info.get("tag"))
        if info.get("description"):
            desc.append("")
            desc.append(str(info.get("description")))
        text = "\n".join([x for x in desc if x is not None])
        text = text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
        return {
            "vod_id": str(cid),
            "vod_name": (info.get("name") or "").strip() or str(cid),
            "vod_pic": self._inline(info.get("horizontal_cover") or info.get("vertical_cover") or ""),
            "vod_content": text,
            "vod_play_url": "#".join(eps),
        }

    def chapter(self, cid, chid):
        d = self.call("/comic/chapter", {"comic_id": str(cid), "chapter_id": str(chid)})
        urls = []
        for im in (d.get("image_list") or []):
            if isinstance(im, dict) and im.get("img"):
                urls.append(im["img"])
        if not urls:
            return []
        # 并发抓取 + 解密 + 内联（顺序保持）
        out = [None] * len(urls)
        deadline = time.time() + 14.0
        def work(i, u):
            if time.time() > deadline:              # 超预算回落原地址
                out[i] = u
                return
            out[i] = self._inline(u, timeout=12)
        try:
            import concurrent.futures as cf
            with cf.ThreadPoolExecutor(max_workers=16) as ex:
                futs = [ex.submit(work, i, u) for i, u in enumerate(urls)]
                for f in futs:
                    f.result()
        except Exception:
            for i, u in enumerate(urls):
                if out[i] is None:
                    work(i, u)
        return [x for x in out if x]


class Spider(SpiderBase):
    MODULE = "hhlz"
    NAME = "嘿嘿连载"

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
        self._core = HhlzCore(self)
        if ext.get("host"):
            self._core.base = str(ext["host"]).rstrip("/")
        try:
            self.timeout = int(ext.get("timeout") or 20)
        except Exception:
            self.timeout = 20
        self._core.timeout = self.timeout
        # 内置域名优先、注入域名仅回退（坑表 #15）
        try:
            _inj = _vbox_host(self, "")
            if _inj and not self._core.base:
                self._core.base = _inj
        except Exception:
            pass
        return None

    def isVideoFormat(self, url):
        return False

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
            self._core = HhlzCore(self)
        return self._core

    # ---------------- vbox 接口 ----------------
    def homeContent(self, filter):
        return {"class": [dict(x) for x in STATIC_CLASSES], "list": []}

    def homeVideoContent(self):
        return {"list": []}

    def categoryContent(self, tid, pg, filter, extend):
        try:
            page = int(pg or 1)
        except Exception:
            page = 1
        try:
            items, total_page = self._c().list_page(tid, page)
        except Exception:
            items, total_page = [], 0
        return {
            "list": items,
            "page": page,
            "pagecount": total_page or (page + 1 if items else page),
            "limit": len(items),
            "total": total_page * 12 if total_page else 0,
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
        raw = str(id)
        if raw.startswith("manga://"):
            return {"parse": 0, "url": raw, "header": {"User-Agent": UA}}
        cid, chid = "", ""
        if "|" in raw:
            cid, chid = raw.split("|", 1)
        else:
            chid = raw
        try:
            imgs = self._c().chapter(cid, chid)
        except Exception:
            imgs = []
        if not imgs:
            return {"parse": 0, "url": raw, "header": {"User-Agent": UA}}
        return {"parse": 0, "url": "manga://" + "&&".join(imgs),
                "header": {"User-Agent": UA}}

    def searchContent(self, key, quick, pg="1"):
        return {"list": [], "page": 1, "pagecount": 1, "limit": 0, "total": 0}

    def localProxy(self, param):
        p = param or {}
        if isinstance(p, str):
            p = dict(urllib.parse.parse_qsl(p.lstrip("?")))
        url = p.get("url") or p.get("u") or ""
        if not url:
            return [400, "text/plain; charset=utf-8", b"missing url", {}]
        try:
            req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept": "image/*,*/*"})
            with self._c()._open(req, 20) as r:
                raw = r.read()
                ct = (r.headers.get("Content-Type") or "").lower()
        except Exception as e:
            return [502, "text/plain; charset=utf-8", str(e)[:120].encode("utf-8"), {}]
        if raw[:3] == b"\xff\xd8\xff":
            ct = "image/jpeg"
        elif raw[:8] == b"\x89PNG\r\n\x1a\n":
            ct = "image/png"
        elif raw[:4] == b"RIFF" and raw[8:12] == b"WEBP":
            ct = "image/webp"
        elif raw[:4] == b"GIF8":
            ct = "image/gif"
        elif not ct.startswith("image/"):
            ct = "image/jpeg"
        return [200, ct, raw, {"Cache-Control": "max-age=86400"}]
