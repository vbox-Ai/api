#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""黄色仓库（hsck）— vbox 自包含适配器

协议来源：libapp.so blutter 反汇编（package:avbox/module/hsck/*）
站点是苹果CMS 模板（stui-vodlist），**纯 HTML**，无加密、无签名、无 token。

要点
    1) 站点对任何请求返回 **HTTP 418**，但 body 是完整真实页面（不是挑战页）。
       所以不能用 status==200 判断成功，必须看 body 内容。
    2) 页面编码 UTF-8（用 gb18030 解会乱码）。
    3) 播放地址伪装在详情页的 img 标签里：
           <img id="video_img" alt="封面" src="https://t0.97img.com/xxxx/a.m3u8">
       正则抓 id="video_img" 的 src 即为 m3u8 直链。

结构
    列表  首页 或 /vodtype/{typeId}-{page}.html
          项: <a class="stui-vodlist__thumb" href="/view/?id=xxx" title="标题" data-original="封面">
    详情  /view/?id={id}
    分类  首页导航里的 /vodtype/{n}.html
"""

import gzip
import html as html_lib
import json
import os
import re
import ssl
import sys
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


BASE_DEFAULT = "https://hsck3.u0u0.cc"
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


UA = ("Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) "
      "AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Mobile/15E148 Safari/604.1")

RE_ITEM = re.compile(
    r'<a[^>]+class="[^"]*stui-vodlist__thumb[^"]*"[^>]*href="([^"]+)"[^>]*?'
    r'title="([^"]*)"[^>]*?data-original="([^"]+)"', re.S)
RE_ITEM2 = re.compile(
    r'href="(/view/\?id=[^"]+)"[^>]*?title="([^"]*)"[^>]*?data-original="([^"]+)"', re.S)
RE_NAV = re.compile(
    r'href="/\?type=([a-z0-9]+)&p=1">\s*<span[^>]*>[^<]*</span>\s*([^<]+?)\s*</a>', re.S)
RE_M3U8 = re.compile(r'<img[^>]+id="video_img"[^>]+src="([^"]+)"', re.S)
RE_M3U8_ALT = re.compile(r'(https?://[^\s"\'<>]+?\.m3u8[^\s"\'<>]*)')


class HsckCore(object):
    def __init__(self, spider):
        self.sp = spider
        self.base = BASE_DEFAULT
        self.timeout = 20
        self._cats = None
        self._cats_ts = 0

    def _open(self, req, timeout=None):
        t = timeout if timeout is not None else getattr(self, "timeout", 20)
        return _vbox_opener(getattr(self, "sp", None)).open(req, timeout=t)

    def get_html(self, path, timeout=None):
        url = path if path.startswith("http") else self.base.rstrip("/") + "/" + path.lstrip("/")
        req = urllib.request.Request(url, headers={
            "User-Agent": UA,
            "Accept": "text/html,application/xhtml+xml,*/*",
            "Accept-Language": "zh-CN,zh;q=0.9",
            "Referer": self.base + "/",
        })
        try:
            with self._open(req, timeout) as r:
                raw = r.read()
                if raw[:2] == b"\x1f\x8b":
                    try:
                        raw = gzip.decompress(raw)
                    except Exception:
                        pass
                return raw.decode("utf-8", "replace")
        except urllib.error.HTTPError as e:
            # 站点恒返 418，body 仍有效
            try:
                return e.read().decode("utf-8", "replace")
            except Exception:
                return ""
        except Exception:
            return ""

    # ---------------- 解析 ----------------
    def parse_items(self, html):
        out = []
        seen = set()
        for href, title, pic in (RE_ITEM.findall(html) or RE_ITEM2.findall(html)):
            t = html_lib.unescape(re.sub(r"<[^>]+>", "", title)).strip()
            if not href or not t:
                continue
            vid = self._vid_of(href)
            if not vid or vid in seen:
                continue
            seen.add(vid)
            out.append({
                "vod_id": vid,
                "vod_name": t,
                "vod_pic": pic if pic.startswith("http") else (self.base + pic if pic else ""),
                "vod_remarks": "",
                "style": {"type": "rect", "ratio": 0.75},
            })
        return out

    @staticmethod
    def _vid_of(href):
        m = re.search(r"[?&]id=([A-Za-z0-9]+)", href)
        if m:
            return m.group(1)
        if href.startswith("/view/"):
            return href.strip("/").replace("view", "").strip("/?=") or href
        return ""

    def categories(self):
        import time as _t
        now = _t.time()
        if self._cats and (now - self._cats_ts) < 1800:
            return self._cats
        html = self.get_html("/")
        cats = []
        seen = set()
        for tid, name in RE_NAV.findall(html):
            n = html_lib.unescape(name).strip()
            if not n or tid in seen:
                continue
            seen.add(tid)
            cats.append({"type_id": tid, "type_name": n})
        if not cats:
            # 兜底：站点实际分类代码（来自首页导航 /?type=xx&p=1）
            cats = [{"type_id": t, "type_name": n} for t, n in (
                ("ycgc", "国产新片"), ("gcjp", "國產舊篇"), ("wz", "无码中文字幕"),
                ("yz", "有码中文字幕"), ("rw", "日本无码"), ("ry", "日本有码"),
                ("om", "欧美高清"), ("dm", "动漫剧情"),
            )]
        self._cats = cats
        self._cats_ts = now
        return cats

    def list(self, tid, page):
        page = max(1, int(page))
        tid = str(tid or "").strip()
        if tid and re.match(r"^[a-z0-9]+$", tid):
            path = "/?type=%s&p=%d" % (tid, page)
        else:
            path = "/?p=%d" % page
        html = self.get_html(path)
        return self.parse_items(html)

    def detail(self, vid):
        html = self.get_html("/view/?id=%s" % vid)
        if not html:
            return {}
        title = ""
        m = re.search(r"<title>(.*?)</title>", html, re.S)
        if m:
            title = re.sub(r"\s*-\s*黄色仓库.*$", "", html_lib.unescape(m.group(1))).strip()
        if not title:
            m = re.search(r'<h1[^>]*>(.*?)</h1>', html, re.S)
            if m:
                title = re.sub(r"<[^>]+>", "", m.group(1)).strip()

        play = ""
        m = RE_M3U8.search(html)
        if m:
            play = m.group(1).strip()
        if not play:
            m = RE_M3U8_ALT.search(html)
            if m:
                play = m.group(1)

        pic = ""
        m = re.search(r'<img[^>]+id="video_img"[^>]+alt="([^"]+)"', html)
        if m and m.group(1).startswith("http"):
            pic = m.group(1)
        if not pic:
            m = re.search(r'data-original="([^"]+)"', html)
            if m:
                pic = m.group(1)

        desc_bits = []
        m = re.search(r'<div[^>]+class="[^"]*(?:detail-content|desc|content)[^"]*"[^>]*>(.*?)</div>',
                      html, re.S)
        if m:
            t = re.sub(r"<[^>]+>", " ", m.group(1))
            t = re.sub(r"\s+", " ", html_lib.unescape(t)).strip()
            if t:
                desc_bits.append(t[:400])
        if play:
            desc_bits.append("直链：%s" % play)
        desc = "\n".join(desc_bits)
        desc = desc.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")

        return {
            "vod_id": str(vid),
            "vod_name": title or ("黄色仓库 #%s" % vid),
            "vod_pic": pic,
            "vod_content": desc,
            "vod_play_url": ("正片$%s" % play) if play else "",
        }

    def search(self, kw, page=1):
        kw_enc = urllib.parse.quote(str(kw))
        for path in ("/?search2=%s" % kw_enc,
                     "/?search2=%s&p=%d" % (kw_enc, page)):
            html = self.get_html(path)
            items = self.parse_items(html)
            if items:
                return items
        return []


class Spider(SpiderBase):
    MODULE = "hsck"
    NAME = "黄色仓库"

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
        self._core = HsckCore(self)
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
                    if hasattr(self, _inj if False else _attr):
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
            self._core = HsckCore(self)
        return self._core

    def homeContent(self, filter):
        try:
            cls = self._c().categories()
        except Exception:
            cls = []
        return {"class": cls or [{"type_id": "15", "type_name": "最新"}], "list": []}

    def homeVideoContent(self):
        try:
            return {"list": self._c().list("", 1)}
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
        return {"parse": 0, "url": url,
                "header": {"User-Agent": UA, "Referer": self._c().base + "/"}}

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
            "total": 9999 if items else 0,
        }

    def localProxy(self, param):
        return [404, "text/plain; charset=utf-8", b"", {}]
