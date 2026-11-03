#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""漫蛙漫画（mw）— vbox 自包含适配器（漫画类）

协议来源：libapp.so blutter 反汇编（package:avbox/module/mw/*）
纯 HTML 明文，无加密无签名：

    列表   GET /booklist?page={n}[&tag={tag}][&gender={-1|0|1|2}]
    详情   GET /book/{bookId}        → 章节 <a href="/chapter/{chapterId}" title="章节名">
    阅读   GET /chapter/{chapterId}  → 正文图 <img data-r-src="…/upload3/book/id/{book}/{ch}/xxx.webp">
    搜索   GET /search/?keyword={k}
    封面   <img class="manga-list-2-cover-img" src="https://mwfimsvfast40.cc/static/upload3/book/id/…/cover_1.jpg">

vbox 漫画约定（与 shenshi_comic / tuiimg 一致）
    播放返回 "manga://" + 图片用 "&&" 连接，由 WelfareResultMapper 解析成图片阅读器。

坑
    1) 封面图用 src，正文图用 data-r-src（属性不同，正则不能混）
    2) 正文图必须过滤 /ads/（广告位混在 data-r-src 里）
    3) 章节链接形如 /chapter/{chapterId}，不是 /book/{id}/{n}
"""

import base64
import gzip
import html as html_lib
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


HOST_DEFAULT = "https://manwaqr.cc"
UA = ("Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) "
      "AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Mobile/15E148 Safari/604.1")

# 列表卡片：<a href="/book/N" title="名"> … </a>
RE_CARD = re.compile(
    r'<a[^>]+href="(/book/\d+)"[^>]*title="([^"]*)"[^>]*>(.*?)</a>', re.S)
# 封面候选（顺序即优先级）：搜索页/详情页真图在 data-original，src 是占位图
RE_COVER_CAND = [
    re.compile(r'data-original="([^"]+)"'),
    re.compile(r'data-home-src="([^"]+)"'),
    re.compile(r'data-src="([^"]+)"'),
    re.compile(r'<img[^>]+src="([^"]+)"'),
]
RE_ANY_COVER = [
    re.compile(r'data-original="([^"]*upload[^"]*)"'),
    re.compile(r'<img[^>]+src="([^"]+)"'),
]
RE_CHAPTER = re.compile(r'<a[^>]+href="(/chapter/\d+)"[^>]*(?:title="([^"]*)")?[^>]*>', re.S)
RE_BODY_IMG = re.compile(r'data-r-src="(https://[^"]+)"', re.S)
RE_BODY_IMG2 = re.compile(
    r'(https://[^"\'\s]+/upload3/book/id/[^"\'\s]+\.(?:webp|jpg|jpeg|png))', re.S)
RE_TAG = re.compile(r'href="/booklist/\?tag=([^"]+)"[^>]*>([^<]{1,12})<')
RE_GENDER = re.compile(r'class="[^"]*"[^>]*data-val="(-?\d)"[^>]*>([^<]{1,8})<')

# 性别维度兜底（实测：-1 全部 / 2 一般向 / 0 BL向 / 1 其它）
GENDER_FALLBACK = [("-1", "全部"), ("2", "一般向"), ("0", "BL向"), ("1", "其他")]


class MwCore(object):
    def __init__(self, spider):
        self.sp = spider
        self.host = HOST_DEFAULT
        self.timeout = 20
        self._cats = None
        self._cats_ts = 0

    def _open(self, req, timeout=None):
        t = timeout or self.timeout
        try:
            return urllib.request.urlopen(req, timeout=t)
        except Exception:
            op = urllib.request.build_opener(urllib.request.ProxyHandler({}))
            return op.open(req, timeout=t)

    def html(self, path):
        url = path if path.startswith("http") else self.host.rstrip("/") + "/" + path.lstrip("/")
        req = urllib.request.Request(url, headers={
            "User-Agent": UA,
            "Accept": "text/html,application/xhtml+xml,*/*",
            "Accept-Language": "zh-CN,zh;q=0.9",
            "Referer": self.host + "/",
        })
        try:
            with self._open(req) as r:
                raw = r.read()
        except urllib.error.HTTPError as e:
            try:
                raw = e.read()
            except Exception:
                return ""
        except Exception:
            return ""
        if raw[:2] == b"\x1f\x8b":
            try:
                raw = gzip.decompress(raw)
            except Exception:
                pass
        for code in ("utf-8", "gb18030", "latin-1"):
            try:
                return raw.decode(code)
            except Exception:
                continue
        return raw.decode("utf-8", "replace")

    # ---------------- 解析 ----------------
    @staticmethod
    def _abs(u):
        if not u:
            return ""
        if u.startswith("//"):
            return "https:" + u
        if u.startswith("http"):
            return u
        return ""

    @staticmethod
    def _pick_cover(fragment):
        """按优先级挑封面：data-original > data-home-src > data-src > src（且须含 /upload）"""
        if not fragment:
            return ""
        for rx in RE_COVER_CAND:
            for m in rx.finditer(fragment):
                u = m.group(1)
                if u and "/upload" in u:
                    return u
        return ""

    def cards(self, h):
        out = []
        seen = set()
        for m in RE_CARD.finditer(h):
            path, name, inner = m.group(1), m.group(2), m.group(3)
            bid = path.rsplit("/", 1)[-1]
            if not bid or bid in seen:
                continue
            cover = self._abs(self._pick_cover(inner))
            if not cover:
                continue
            seen.add(bid)
            out.append({
                "vod_id": bid,
                "vod_name": html_lib.unescape(name).strip() or ("漫画" + bid),
                "vod_pic": cover,
                "vod_remarks": "",
                "style": {"type": "rect", "ratio": 0.75},
            })
        return out

    # ---------------- 能力 ----------------
    def categories(self):
        now = time.time()
        if self._cats and (now - self._cats_ts) < 1800:
            return self._cats
        h = self.html("/")
        cats = []
        for raw, label in RE_TAG.findall(h):
            tag = urllib.parse.unquote(html_lib.unescape(raw)).strip()
            if not tag:
                continue
            cats.append({"type_id": "tag:" + tag, "type_name": label.strip() or tag})
        if not cats:
            cats = [{"type_id": "gender:%s" % v, "type_name": n}
                    for v, n in GENDER_FALLBACK]
        self._cats = cats[:40]
        self._cats_ts = now
        return self._cats

    def list(self, tid, page):
        page = max(1, int(page))
        tid = str(tid or "")
        q = {"page": page}
        if tid.startswith("tag:"):
            q["tag"] = tid[4:]
        elif tid.startswith("gender:"):
            q["gender"] = tid[7:]
        elif tid.isdigit():
            q["gender"] = tid
        url = "/booklist?" + urllib.parse.urlencode(q)
        return self.cards(self.html(url))

    def detail(self, vid):
        vid = str(vid).strip().rstrip("/").split("/")[-1]
        h = self.html("/book/%s" % vid)
        if not h:
            return {}
        name = ""
        m = re.search(r"<title>([^<]+)</title>", h, re.S)
        if m:
            name = html_lib.unescape(m.group(1))
            name = re.sub(r"\s*-\s*漫蛙漫画.*$", "", name).strip()
        pic = ""
        # 详情页：先 data-original，再任何含 /upload 的图
        for rx in RE_ANY_COVER:
            m = rx.search(h)
            if m and "/upload" in m.group(1):
                pic = self._abs(m.group(1))
                break

        # 章节：/chapter/{id} + 标题（去重保序）
        chs = []
        seen = set()
        for m in RE_CHAPTER.finditer(h):
            path, title = m.group(1), (m.group(2) or "")
            cid = path.rsplit("/", 1)[-1]
            if not cid or cid in seen:
                continue
            seen.add(cid)
            t = html_lib.unescape(title).strip()
            if not t:
                # 取 <a> 内文本
                seg = h[m.end():m.end() + 200]
                t = re.sub(r"<[^>]+>", "", seg).strip()[:20]
            chs.append((cid, t or ("第%s话" % len(chs) + 1)))
        if not chs:
            return {}

        desc = []
        d = re.search(r'<div[^>]+class="[^"]*detail-desc[^"]*"[^>]*>(.*?)</div>', h, re.S)
        if d:
            t = re.sub(r"<[^>]+>", " ", d.group(1))
            t = re.sub(r"\s+", " ", html_lib.unescape(t)).strip()
            if t:
                desc.append(t[:400])
        desc.append("共 %d 章" % len(chs))
        text = "\n".join(desc).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")

        return {
            "vod_id": vid,
            "vod_name": name or ("漫画" + vid),
            "vod_pic": pic,
            "vod_content": text,
            "vod_play_url": "#".join("%s$%s" % (t, cid) for cid, t in chs),
        }

    def chapter_images(self, cid):
        cid = str(cid).strip().rstrip("/").split("/")[-1]
        h = self.html("/chapter/%s" % cid)
        if not h:
            return []
        imgs = []
        for u in RE_BODY_IMG.findall(h):
            a = self._abs(u)
            if not a or "/upload3/book/id/" not in a or "/ads/" in a:
                continue
            imgs.append(a)
        if not imgs:
            for u in RE_BODY_IMG2.findall(h):
                a = self._abs(u)
                if a and "/ads/" not in a:
                    imgs.append(a)
        # 去重保序
        return list(dict.fromkeys(imgs))

    def search(self, kw, page=1):
        url = "/search/?" + urllib.parse.urlencode({"keyword": kw, "page": page})
        return self.cards(self.html(url))


class Spider(SpiderBase):
    MODULE = "mw"
    NAME = "漫蛙漫画"

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
        self._core = MwCore(self)
        if ext.get("host"):
            self._core.host = str(ext["host"]).rstrip("/")
        try:
            self.timeout = int(ext.get("timeout") or 20)
        except Exception:
            self.timeout = 20
        self._core.timeout = self.timeout
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
            self._core = MwCore(self)
        return self._core

    # ---------------- vbox 接口 ----------------
    def homeContent(self, filter):
        try:
            cls = self._c().categories()
        except Exception:
            cls = []
        return {"class": cls, "list": []}

    def homeVideoContent(self):
        try:
            return {"list": self._c().cards(self._c().html("/"))[:20]}
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
        cid = str(id).strip()
        if cid.startswith("http"):
            cid = cid.rstrip("/").split("/")[-1]
        try:
            imgs = self._c().chapter_images(cid)
        except Exception:
            imgs = []
        if imgs:
            return {"parse": 0, "url": "manga://" + "&&".join(imgs),
                    "header": {"User-Agent": UA, "Referer": self._c().host + "/"}}
        return {"parse": 0, "url": "",
                "header": {"User-Agent": UA, "Referer": self._c().host + "/"}}

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
