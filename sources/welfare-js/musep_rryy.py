# -*- coding: utf-8 -*-
"""暮色资源平台「2048」（key=rryy）—— 自包含单文件版（v2）。

背景：客户端 WelfareSpiderLoader 只下载 api 指向的单个 .py 文件，不会下载
同目录依赖（如原 muse_avbox.py 引擎）。薄封装 `from muse_avbox import Spider`
在客户端环境必然 FileNotFoundError。故本文件把 rryy 所需的全部代码
（Spider 基类 + RryyAdapter + 网络工具）内联，消除跨文件依赖。

链路（2026-10-31 实测，纯 HTML 明文，无 token/AES）：
  门禁  GET /home/enter.html?to=%2F  → 种 cookie enter_site_ok
  首页  GET /home/1.html             → 导航 11 个分类 + 卡片
  分类  GET /home/{catId}.html       → 该分类列表
  详情  GET /play/{id}.html          → 标题/封面（播放需 VIP）

二级分类（sub_categories，客户端 scheme A）：
  有码  → [日本有码, 中文有码]
  无码  → [中文无码, 日本无码, 欧美无码]
  地区  → [国产强片, 日韩强片, 欧美强片]
  独立  → 三级强片 / 包罗万象 / VR专区
"""
import sys
import json
import time
import re
import ssl
import html as _html
import urllib.parse
import urllib.request
import urllib.error
import http.cookiejar

try:
    from base.spider import Spider as _B
except Exception:
    class _B(object):
        pass

UA_IOS = ('Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) '
          'AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Mobile/15E148 Safari/604.1')

HOST = "https://yy.swgongshui.com"

# rryy 二级分类分组：聚合 id -> (名称, [子分类 id 列表])
GROUPS = [
    ("yuma", "有码", ["6", "10"]),
    ("wuma", "无码", ["7", "8", "9"]),
    ("diqu", "地区", ["1", "4", "13"]),
]
GROUP_SUBS = {g[0]: g[2] for g in GROUPS}


class RryyAdapter(object):
    """2048（我为人人影院）—— 纯 HTML 明文。"""

    content_type = "video"

    def __init__(self, spider):
        self.sp = spider
        self._entered = False
        self._cats = None

    def _enter(self):
        if self._entered:
            return
        self.sp.fetch_text(HOST + "/home/enter.html?to=%2F")
        self._entered = True

    def _page(self, path):
        self._enter()
        return self.sp.fetch_text(HOST + path)

    def categories(self):
        if self._cats is not None:
            return self._cats
        html = self._page("/home/1.html")
        pat = re.compile(r'href="/home/(\d+)\.html"[^>]*>\s*<span[^>]*>([^<]{1,20})</span>', re.S)
        seen = []
        for cid, name in pat.findall(html):
            item = {"type_id": cid, "type_name": _html.unescape(name).strip()}
            if item not in seen:
                seen.append(item)
        # 重组成带二级分类的结构
        flat = {c["type_id"]: c for c in seen}
        cats = []
        used = set()
        for gid, gname, members in GROUPS:
            subs = []
            for mid in members:
                if mid in flat:
                    subs.append({"type_id": mid, "type_name": flat[mid]["type_name"]})
                    used.add(mid)
            if subs:
                cats.append({
                    "type_id": gid,
                    "type_name": gname,
                    "sub_categories": subs,
                })
        for c in seen:
            if c["type_id"] not in used:
                cats.append(c)
        self._cats = cats
        return cats

    @staticmethod
    def _cards(html):
        out, seen = [], set()
        pat = re.compile(r'href="/play/(\d+)\.html"', re.S)
        positions = [(m.start(), m.group(1)) for m in pat.finditer(html)]
        for idx, (pos, vid) in enumerate(positions):
            if vid in seen:
                continue
            seen.add(vid)
            end = positions[idx + 1][0] if idx + 1 < len(positions) else min(len(html), pos + 4000)
            block = html[pos:end]
            alt = re.search(r'alt="([^"]*)"', block)
            src = re.search(r'(?:data-src|src)="(https?://[^"]+\.(?:jpg|jpeg|png|webp|gif)[^"]*)"', block)
            name = _html.unescape(alt.group(1)).replace("\x00", "").strip() if alt else vid
            if not name or len(name) < 2:
                name = vid
            out.append({
                "vod_id": vid,
                "vod_name": name,
                "vod_pic": (src.group(1).replace("//vod_pic", "/vod_pic") if src else ""),
            })
        return out

    def list(self, tid, page):
        page = int(page or 1)
        tid = str(tid)
        # 聚合分类 → 合并各子分类第一页数据
        if tid in GROUP_SUBS:
            merged = []
            seen_ids = set()
            for sub_id in GROUP_SUBS[tid]:
                html = self._page("/home/%s.html?p=%d" % (sub_id, page))
                if not html or len(html) < 5000:
                    continue
                for card in self._cards(html):
                    if card["vod_id"] not in seen_ids:
                        seen_ids.add(card["vod_id"])
                        merged.append(card)
            return merged
        # 独立分类
        cats = {c["type_id"] for c in self.categories()}
        if tid not in cats:
            tid = "1"
        html = self._page("/home/%s.html?p=%d" % (tid, page))
        if not html or len(html) < 5000:
            return []
        return self._cards(html)

    def detail(self, vid):
        html = self._page("/play/%s.html" % urllib.parse.quote(str(vid)))
        if not html:
            return {}
        t = re.search(r"<title>([^<]*)</title>", html)
        name = _html.unescape(t.group(1)).replace("\x00", "").strip() if t else ""
        name = re.sub(r"\s*-\s*我为人人影院\s*$", "", name).strip()
        pic = re.search(r'(?:data-src|src)="(https?://[^"]+(?:vod_pic|cover)[^"]*)"', html)
        vip = "会员" in html
        return {
            "vod_id": str(vid),
            "vod_name": name or str(vid),
            "vod_pic": (pic.group(1).replace("//vod_pic", "/vod_pic") if pic else ""),
            "vod_content": "该片源播放需站点 VIP（列表与详情可用）" if vip else "",
            "vip_only": vip,
        }

    def play(self, vid):
        return {"parse": 1, "url": HOST + "/play/%s.html" % urllib.parse.quote(str(vid))}


class Spider(_B):
    def __init__(self):
        super(Spider, self).__init__()
        self.timeout = 15
        self.ctx = ssl.create_default_context()
        self.ctx.check_hostname = False
        self.ctx.verify_mode = ssl.CERT_NONE
        self._jar = http.cookiejar.CookieJar()
        self._opener = urllib.request.build_opener(
            urllib.request.HTTPCookieProcessor(self._jar))
        self._adapter = None

    # ---------------- 基类接口 ----------------
    def getName(self):
        return "2048"

    def getDependence(self):
        return []

    def init(self, extend=""):
        ext = {}
        if extend:
            try:
                ext = json.loads(extend) if isinstance(extend, str) else dict(extend)
            except Exception:
                ext = {}
        if ext.get("timeout"):
            try:
                self.timeout = int(ext["timeout"])
            except Exception:
                pass
        return None

    def isVideoFormat(self, url):
        low = (url or "").lower()
        return any(k in low for k in (".m3u8", ".mp4", ".flv", ".mkv", ".ts", ".mpd"))

    def manualVideoCheck(self):
        return False

    def destroy(self):
        pass

    def action(self, action):
        pass

    # ---------------- 网络 ----------------
    def fetch_text(self, url, headers=None, data=None):
        h = {
            "User-Agent": UA_IOS,
            "Accept": "text/html,application/xhtml+xml,application/json,*/*",
            "Accept-Language": "zh-CN,zh;q=0.9",
        }
        if headers:
            h.update(headers)
        req = urllib.request.Request(url, data=data, headers=h,
                                     method="POST" if data is not None else "GET")
        try:
            with self._opener.open(req, timeout=self.timeout) as r:
                raw = r.read()
                enc = (r.headers.get("Content-Encoding") or "").lower()
                if "gzip" in enc:
                    import gzip
                    try:
                        raw = gzip.decompress(raw)
                    except Exception:
                        pass
                for code in ("utf-8", "gbk", "gb18030", "latin-1"):
                    try:
                        return raw.decode(code)
                    except Exception:
                        continue
                return raw.decode("utf-8", "replace")
        except urllib.error.HTTPError as e:
            try:
                return e.read().decode("utf-8", "replace")
            except Exception:
                return ""
        except Exception:
            return ""

    # ---------------- 适配器 ----------------
    def _get_adapter(self):
        if self._adapter is None:
            self._adapter = RryyAdapter(self)
        return self._adapter

    # ---------------- vbox 方法 ----------------
    def homeContent(self, filter):
        adapter = self._get_adapter()
        classes = adapter.categories()
        if not classes:
            classes = [{"type_id": "1", "type_name": "全部"}]
        return {"class": classes, "list": []}

    def homeVideoContent(self):
        return {"list": []}

    def categoryContent(self, tid, pg, filter, extend):
        page = int(pg or 1)
        adapter = self._get_adapter()
        try:
            items = adapter.list(tid, page)
        except Exception:
            items = []
        return {
            "list": items,
            "page": page,
            "pagecount": page + 1 if items else page,
            "limit": len(items),
            "total": 9999 if items else 0,
        }

    def searchContent(self, key, quick, pg="1"):
        page = int(pg or 1)
        return {"list": [], "page": page, "pagecount": page, "limit": 0, "total": 0}

    def detailContent(self, array):
        vid = str(array[0]) if array else ""
        adapter = self._get_adapter()
        if not vid:
            return {"list": []}
        try:
            d = adapter.detail(vid) or {}
        except Exception:
            d = {}
        if not d:
            return {"list": []}
        name = d.get("vod_name") or vid
        item = {
            "vod_id": vid,
            "vod_name": name,
            "vod_pic": d.get("vod_pic", ""),
            "vod_content": d.get("vod_content", ""),
            "vod_play_from": "2048",
            "vod_play_url": "%s$%s" % (name, vid),
        }
        return {"list": [item]}

    def playerContent(self, flag, id, vipFlags):
        adapter = self._get_adapter()
        if str(id) and not str(id).startswith("http"):
            try:
                r = adapter.play(str(id))
            except Exception:
                r = None
            if isinstance(r, dict) and r.get("url"):
                return r
        url = str(id)
        if url.startswith("http"):
            return {"parse": 0, "url": url, "header": {"User-Agent": UA_IOS}}
        return {"parse": 1, "url": url, "header": {"User-Agent": UA_IOS}, "jx": 1}
