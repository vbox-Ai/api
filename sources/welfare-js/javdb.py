#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""JavDB（javdb）— vbox 自包含适配器

协议来源：libapp.so blutter 反汇编
    package:avbox/module/javdb/network/interceptor.dart  (JavDbInterceptor::onRequest @0x8df080)
    package:avbox/module/javdb/network/service.dart      (构造处 @0x7b9fa8 写入 SECRET)
────────────────────────────────────────────────────────────────────────────
签名（onRequest 只有 30 来条指令，全还原）：
    ts    = 秒级时间戳（micros/1000/1000，两次 sdiv）
    first = MD5( f"{ts}{SECRET}" )                     ← SECRET 是 interceptor.field_7
    headers: accept-language: zh
             jdsignature:    f"{ts}.lpw6vgqzsp.{first}"

    SECRET = 71cf27bb3c0bcdf207b64abecddc970098c7421ee7203b9cdae54478478a199e7d5a6e1a57691123c1a931c057842fb73ba3b3c83bcd69c17ccf174081e3d8aa

接口（GET，全部 JSON）
    api/v1/movies/latest?page=            最新（20 条/页）
    api/v1/movies/tags?filter_by=tag&page= 标签流
    api/v2/search?q=&page=                搜索
    api/v4/movies/{id}                    详情（movie 子对象）

播放：
    detail.movie.preview_video_url 是官方 720p 试看 m3u8（带 sign/t，服务端签发）
    detail.movie.play_sources 为空 —— 正片需登录 + VIP（show_vip_banner=true），
    列表项的 can_play 也恒 false。所以本适配器交付「分类/列表/详情 + 试看播放」。

坑：
    1) 签名 ts 是**秒**，不是毫秒（两次 sdiv 1000）
    2) jdsignature 三段式 `{ts}.lpw6vgqzsp.{md5}`，中间那串是固定字面量
    3) 路径不存在返 {"status":404}；参数缺失返 {"success":0,"action":"ParameterInvalid","message":"參數不能爲空: xxx"}
       —— 可以据此枚举必填参数（本轮就是这样定出 filter_by=tag 的）
    4) homeContent 不联网（客户端总预算 20s，见交接文档坑表 #25）
"""

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


BASE_DEFAULT = "https://jdforrepam.com"
SECRET = ("71cf27bb3c0bcdf207b64abecddc970098c7421ee7203b9cdae54478478a199e7d5a6e1a57691123c1"
          "a931c057842fb73ba3b3c83bcd69c17ccf174081e3d8aa")
SIGN_MID = ".lpw6vgqzsp."
UA = ("Mozilla/5.0 (iPhone; CPU iPhone OS 18_5 like Mac OS X) AppleWebKit/605.1.15 "
      "(KHTML, like Gecko) Version/18.5 Mobile/15E148 Safari/604.1")

STATIC_CLASSES = [
    {"type_id": "latest", "type_name": "最新"},
    {"type_id": "tag", "type_name": "标签流"},
]
QUICK_TIMEOUT = 3.0

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


class JavdbCore(object):
    def __init__(self, spider):
        self.sp = spider
        self.base = BASE_DEFAULT
        self.timeout = 20
        self._cache = {}

    def _open(self, req, timeout=None):
        t = timeout if timeout is not None else getattr(self, "timeout", 20)
        return _vbox_opener(getattr(self, "sp", None)).open(req, timeout=t)

    @staticmethod
    def signature():
        ts = int(time.time())
        first = hashlib.md5(("%s%s" % (ts, SECRET)).encode()).hexdigest()
        return ts, "%s%s%s" % (ts, SIGN_MID, first)

    def call(self, path, params=None, timeout=None):
        _ts, sig = self.signature()
        url = self.base.rstrip("/") + "/" + str(path).lstrip("/")
        if params:
            url += "?" + urllib.parse.urlencode(params)
        req = urllib.request.Request(url, headers={
            "User-Agent": UA,
            "accept-language": "zh",
            "jdsignature": sig,
            "Accept": "application/json",
        })
        try:
            with self._open(req, timeout) as r:
                return json.loads(r.read().decode("utf-8", "replace"))
        except urllib.error.HTTPError as e:
            try:
                return json.loads(e.read().decode("utf-8", "replace"))
            except Exception:
                return {}
        except Exception:
            return {}

    # ---------------- 映射 ----------------
    def _item(self, m):
        mid = m.get("id")
        if mid is not None:
            self._cache[str(mid)] = m
        remarks = []
        if m.get("number"):
            remarks.append(str(m.get("number")))
        if m.get("duration"):
            try:
                remarks.append("%d分钟" % (int(m.get("duration")) // 60))
            except Exception:
                pass
        if m.get("has_cnsub"):
            remarks.append("中字")
        if m.get("has_preview_video"):
            remarks.append("试看")
        return {
            "vod_id": str(mid),
            "vod_name": (m.get("title") or m.get("origin_title") or "").strip() or str(mid),
            "vod_pic": m.get("cover_url") or m.get("thumb_url") or "",
            "vod_remarks": " · ".join([x for x in remarks if x]),
            "style": {"type": "rect", "ratio": 1.5},
        }

    def list_page(self, tid, page):
        t = str(tid or "latest")
        if t == "tag":
            j = self.call("api/v1/movies/tags", {"filter_by": "tag", "page": int(page)})
        else:
            j = self.call("api/v1/movies/latest", {"page": int(page)})
        d = j.get("data") or {}
        items = d.get("movies") if isinstance(d, dict) else None
        if not isinstance(items, list):
            items = []
        return [self._item(m) for m in items if isinstance(m, dict) and m.get("id")]

    def search_page(self, key, page):
        j = self.call("api/v2/search", {"q": str(key), "page": int(page)})
        d = j.get("data") or {}
        items = d.get("movies") if isinstance(d, dict) else None
        if not isinstance(items, list):
            items = []
        return [self._item(m) for m in items if isinstance(m, dict) and m.get("id")]

    def detail(self, vid):
        j = self.call("api/v4/movies/%s" % vid)
        d = j.get("data") or {}
        m = d.get("movie") if isinstance(d, dict) else None
        if not isinstance(m, dict):
            return {}
        meta = []
        if m.get("number"):
            meta.append("番号：%s" % m.get("number"))
        if m.get("release_date"):
            meta.append("发行：%s" % m.get("release_date"))
        if m.get("duration"):
            try:
                meta.append("时长：%d 分钟" % (int(m.get("duration")) // 60))
            except Exception:
                pass
        acts = [a.get("name") for a in (m.get("actors") or []) if isinstance(a, dict)]
        if acts:
            meta.append("演员：%s" % "、".join([x for x in acts if x]))
        for fld, label in (("maker_name", "片商"), ("publisher_name", "发行商"),
                           ("series_name", "系列"), ("director_name", "导演")):
            if m.get(fld):
                meta.append("%s：%s" % (label, m.get(fld)))
        tags = [t.get("name") for t in (m.get("tags") or []) if isinstance(t, dict)]
        if tags:
            meta.append("标签：%s" % "、".join([x for x in tags if x]))
        if m.get("score"):
            meta.append("评分：%s" % m.get("score"))
        meta.append("可播：%s（正片需登录+VIP，这里给官方试看）"
                    % ("试看" if m.get("preview_video_url") else "否"))
        desc = "\n".join(meta)
        if m.get("summary"):
            desc += "\n\n" + str(m.get("summary"))
        desc = desc.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
        play = (m.get("preview_video_url") or "").strip()
        return {
            "vod_id": str(vid),
            "vod_name": (m.get("title") or m.get("origin_title") or "").strip() or str(vid),
            "vod_pic": m.get("cover_url") or m.get("thumb_url") or "",
            "vod_content": desc,
            "vod_play_url": ("试看$%s" % play) if play else "",
        }


class Spider(SpiderBase):
    MODULE = "javdb"
    NAME = "JavDB"

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
        self._core = JavdbCore(self)
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
            self._core = JavdbCore(self)
        return self._core

    # ---------------- vbox 接口 ----------------
    def homeContent(self, filter):
        # 不联网：客户端 homeContent 总预算 20s（坑表 #25）
        return {"class": [dict(x) for x in STATIC_CLASSES], "list": []}

    def homeVideoContent(self):
        return {"list": []}

    def categoryContent(self, tid, pg, filter, extend):
        try:
            page = int(pg or 1)
        except Exception:
            page = 1
        try:
            items = self._c().list_page(tid, page)
        except Exception:
            items = []
        return {
            "list": items,
            "page": page,
            "pagecount": page + 1 if items else page,
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
        return {"parse": 0, "url": url,
                "header": {"User-Agent": UA, "Referer": BASE_DEFAULT + "/"}}

    def searchContent(self, key, quick, pg="1"):
        try:
            page = int(pg or 1)
        except Exception:
            page = 1
        try:
            items = self._c().search_page(key, page)
        except Exception:
            items = []
        return {"list": items, "page": page, "pagecount": page + 1 if items else page,
                "limit": len(items), "total": 9999 if items else 0}

    def localProxy(self, param):
        return [404, "text/plain; charset=utf-8", b"", {}]
