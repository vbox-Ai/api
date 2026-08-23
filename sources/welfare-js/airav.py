# -*- coding: utf-8 -*-
"""
平台名称：疯AV (AirAv.io)
平台标识：airav_py
作者：原始 tvshare23 · 适配：vbox Python Spider 框架
适配日期：2026-08-23
说明：
  - 继承 base.spider.Spider，super().init() 兜底
  - 域名注入：从 _vbox_effective_hosts 取候选域名
  - 4 个候选域名并发探测，先到先用
  - 10 分钟冷静期：成功域名缓存 600s，过期重新探测
  - xpath 解析改为 re 正则（iOS 端无 lxml）
  - 返回 dict，playerContent 返回 parse=0 m3u8 直链
"""
import re
import json
import time
import requests
from urllib.parse import quote
from concurrent.futures import ThreadPoolExecutor, as_completed

try:
    from base.spider import Spider as BaseSpider
except ImportError:
    class BaseSpider:
        def init(self, extend=""): pass
        def getProxyUrl(self):
            return ''

# ── 平台配置 ──────────────────────────────────
_DEFAULT_HOSTS = [
    "https://inbggairav.net",
    "https://www.inbggairav.net",
    "https://airav.io",
    "https://www.airav.io",
]

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
    "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
    "Referer": "https://inbggairav.net/",
}

# ── 冷静期常量 ────────────────────────────────
_PROBE_COOLDOWN = 600


class Spider(BaseSpider):
    def __init__(self):
        self._probe_cache = {}

    def getName(self):
        return "疯AV"

    def init(self, extend=""):
        try:
            super().init(extend)
        except Exception:
            pass

        injected = getattr(self, '_vbox_effective_hosts', None) or []
        if injected:
            self._candidates = [str(h).rstrip('/') for h in injected]
        else:
            self._candidates = list(_DEFAULT_HOSTS)

        self.host = self._get_domain()
        self.headers = HEADERS.copy()
        self.headers["Referer"] = self.host + "/"

    def destroy(self):
        pass

    def isVideoFormat(self, url):
        if not url:
            return False
        return bool(re.match(r'.*\.(m3u8|mp4|flv|avi|mkv|rmvb|wmv)(\?|#|$)', url, re.IGNORECASE))

    def manualVideoCheck(self):
        return False

    # ── 并发域名探测（带 10 分钟冷静期）────────
    def _probe_domain(self, domain):
        now = time.time()
        if domain in self._probe_cache:
            ok, ts = self._probe_cache[domain]
            if now - ts < _PROBE_COOLDOWN:
                return ok
        try:
            resp = requests.head(domain, headers=self.headers, timeout=8, allow_redirects=True)
            ok = resp.status_code < 500
        except Exception:
            ok = False
        self._probe_cache[domain] = (ok, now)
        return ok

    def _get_domain(self):
        now = time.time()
        cached_ok = []
        need_probe = []
        for d in self._candidates:
            if d in self._probe_cache:
                ok, ts = self._probe_cache[d]
                if now - ts < _PROBE_COOLDOWN:
                    if ok:
                        cached_ok.append(d)
                    continue
            need_probe.append(d)
        if cached_ok and not need_probe:
            return cached_ok[0]
        if need_probe:
            with ThreadPoolExecutor(max_workers=len(need_probe)) as ex:
                futs = {ex.submit(self._probe_domain, d): d for d in need_probe}
                for f in as_completed(futs):
                    d = futs[f]
                    if f.result():
                        cached_ok.append(d)
            if cached_ok:
                return cached_ok[0]
        return self._candidates[0]

    def _fetch(self, url):
        try:
            resp = requests.get(url, headers=self.headers, timeout=15)
            if resp.status_code == 200:
                resp.encoding = resp.apparent_encoding or "utf-8"
                return resp.text
        except Exception:
            pass
        return ""

    # ── re 正则替代 xpath ─────────────────────
    def _xpath(self, html, pattern, default=None):
        m = re.search(pattern, html, re.DOTALL)
        if m:
            return m.group(1) if m.groups() else m.group(0)
        return default

    def _xpath_all(self, html, pattern):
        return [m.group(1) if m.groups() else m.group(0) for m in re.finditer(pattern, html, re.DOTALL)]

    def homeContent(self, filter=False):
        result = {}
        classes = [
            {"type_id": "1", "type_name": "最新"},
            {"type_id": "2", "type_name": "热门"},
            {"type_id": "3", "type_name": "经典"},
            {"type_id": "4", "type_name": "国产"},
            {"type_id": "5", "type_name": "日韩"},
            {"type_id": "6", "type_name": "欧美"},
            {"type_id": "7", "type_name": "无码"},
            {"type_id": "8", "type_name": "人妻"},
            {"type_id": "9", "type_name": "熟女"},
            {"type_id": "10", "type_name": "清纯"},
            {"type_id": "11", "type_name": "制服"},
            {"type_id": "12", "type_name": "角色扮演"},
            {"type_id": "13", "type_name": "大奶子"},
            {"type_id": "14", "type_name": "美腿"},
            {"type_id": "15", "type_name": "动态"},
        ]
        result["class"] = classes
        if filter:
            filters = {}
            for cat in classes:
                filters[cat["type_id"]] = []
            result["filters"] = filters
        self.host = self._get_domain()
        html = self._fetch(self.host + "/")
        result["list"] = self._parseVideoList(html)
        return result

    def homeVideoContent(self):
        self.host = self._get_domain()
        html = self._fetch(self.host + "/")
        return {"list": self._parseVideoList(html)}

    def categoryContent(self, tid, pg, filter=False, extend=None):
        result = {"list": [], "page": 1, "pagecount": 1, "limit": 36, "total": 0}
        try:
            page = int(pg) if pg else 1
        except (ValueError, TypeError):
            page = 1
        result["page"] = page
        self.host = self._get_domain()
        url = f"{self.host}/list/{tid}/{page}/" if page > 1 else f"{self.host}/list/{tid}/"
        html = self._fetch(url)
        if html:
            result["list"] = self._parseVideoList(html)
            result["pagecount"] = self._getPageCount(html)
            result["total"] = result["pagecount"] * 36
        return result

    def _parseVideoList(self, html):
        if not html:
            return []
        videos = []
        seen = set()
        # 匹配每个视频块: <div class="list-item">...</div>
        for block in re.finditer(r'<div[^>]*class="[^"]*list-item[^"]*"[^>]*>(.*?)</div>\s*</div>', html, re.DOTALL):
            inner = block.group(1)
            try:
                href_m = re.search(r'href="([^"]+)"', inner)
                if not href_m:
                    continue
                vod_id = href_m.group(1)
                if vod_id in seen:
                    continue
                seen.add(vod_id)
                if not vod_id.startswith("http"):
                    vod_id = self.host + vod_id
                img_m = re.search(r'<img[^>]*src="([^"]+)"', inner)
                title_m = re.search(r'<img[^>]*alt="([^"]*)"', inner)
                if not title_m:
                    title_m = re.search(r'<p[^>]*class="[^"]*title[^"]*"[^>]*>(.*?)</p>', inner, re.DOTALL)
                dur_m = re.search(r'(\d{1,2}:\d{2})', inner)
                videos.append({
                    "vod_id": vod_id,
                    "vod_name": (title_m.group(1) if title_m else ""),
                    "vod_pic": (img_m.group(1) if img_m else ""),
                    "vod_remarks": (dur_m.group(1) if dur_m else ""),
                })
            except Exception:
                continue
        if not videos:
            for m in re.finditer(r'<a[^>]*href="([^"]+)"[^>]*>(.*?)</a>', html, re.DOTALL):
                href = m.group(1)
                if not href or href in seen:
                    continue
                seen.add(href)
                if not href.startswith("http"):
                    href = self.host + href
                inner = m.group(2)
                img_m = re.search(r'<img[^>]*src="([^"]+)"', inner)
                title_m = re.search(r'<img[^>]*alt="([^"]*)"', inner)
                dur_m = re.search(r'(\d{1,2}:\d{2})', inner)
                videos.append({
                    "vod_id": href,
                    "vod_name": (title_m.group(1) if title_m else ""),
                    "vod_pic": (img_m.group(1) if img_m else ""),
                    "vod_remarks": (dur_m.group(1) if dur_m else ""),
                })
        return videos

    def _getPageCount(self, html):
        if not html:
            return 1
        pages = re.findall(r'page=(\d+)', html)
        if pages:
            return max(int(p) for p in pages)
        return 1

    def detailContent(self, ids):
        result = {"list": []}
        try:
            vod_id = ids[0] if isinstance(ids, list) else ids
            self.host = self._get_domain()
            url = vod_id if vod_id.startswith("http") else self.host + vod_id
            html = self._fetch(url)
            if html:
                title = self._xpath(html, r'<h1[^>]*>(.*?)</h1>', "") or self._xpath(html, r'<title>(.*?)</title>', "") or vod_id
                pic = self._xpath(html, r'<meta[^>]*property="og:image"[^>]*content="([^"]+)"', "")
                m3u8 = self._xpath(html, r'(https?://[^"\'<>\s]+\.m3u8[^"\'<>\s]*)', "")
                play_from = []
                play_url = []
                if m3u8:
                    play_from.append("M3U8")
                    play_url.append(f"正片${m3u8}")
                else:
                    play_from.append("播放")
                    play_url.append(f"正片${url}")
                result["list"].append({
                    "vod_id": vod_id, "vod_name": title, "vod_pic": pic,
                    "vod_content": "", "vod_play_from": "$$$".join(play_from),
                    "vod_play_url": "$$$".join(play_url)
                })
        except Exception:
            pass
        return result

    def searchContent(self, key, quick=False, pg="1"):
        result = {"list": []}
        try:
            page = int(pg) if pg else 1
            self.host = self._get_domain()
            url = f"{self.host}/search/{quote(key)}/" if page == 1 else f"{self.host}/search/{quote(key)}/page/{page}/"
            html = self._fetch(url)
            if html:
                result["list"] = self._parseVideoList(html)
                result["page"] = page
                result["pagecount"] = self._getPageCount(html)
        except Exception:
            pass
        return result

    def playerContent(self, flag, id, vipFlags=None):
        if not id:
            return {"parse": 0, "url": "", "header": self.headers}
        url = str(id)
        if "$" in url:
            url = url.split("$", 1)[-1]
        return {"parse": 0, "url": url, "header": self.headers}

    def localProxy(self, param):
        return [404, 'text/plain', b'']

    def manualVideoCheck(self):
        return False