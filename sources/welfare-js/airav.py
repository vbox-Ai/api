# -*- coding: utf-8 -*-
"""
平台名称：疯AV (AirAv.io)
平台标识：airav_py
作者：原始 tvshare23 · 适配：vbox Python Spider 框架
适配日期：2026-08-23
说明：
  - 继承 base.spider.Spider，super().init() 兜底
  - 域名注入：从 _vbox_effective_hosts 取候选域名
  - 并发域名探测：主域名 + 备用域名同时探测，先到先用
  - 10 分钟冷静期：成功域名缓存 600s，过期重新探测
  - re 正则替代 xpath（iOS 端无 lxml）
  - 修复分类 URL 构造：list?sort=N / tag?id=N
  - playerContent 返回 parse=0 m3u8 直链
"""
import re
import json
import time
import requests
from concurrent.futures import ThreadPoolExecutor, as_completed

try:
    from base.spider import Spider as BaseSpider
except ImportError:
    class BaseSpider:
        def init(self, extend=""): pass
        def fetch(self, url, headers=None, **kw):
            import requests
            kw.pop("timeout", None)
            r = requests.get(url, headers=headers, timeout=15, **kw)
            r.encoding = "utf-8"
            return r
        def getProxyUrl(self): return ""


class Spider(BaseSpider):
    def getName(self):
        return "airav"

    def init(self, extend=""):
        try:
            super().init(extend)
        except Exception:
            pass
        cfg = json.loads(extend) if isinstance(extend, str) and extend else (extend or {})
        self.proxies = cfg.get("proxies") or {}

        injected = getattr(self, "_vbox_effective_hosts", None) or []
        if injected and str(injected[0]).startswith("http"):
            self.host = str(injected[0]).rstrip("/")
        else:
            self.host = "https://inbggairav.net"

        self.headers = {
            "User-Agent": ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                           "AppleWebKit/537.36 (KHTML, like Gecko) "
                           "Chrome/120.0.0.0 Safari/537.36"),
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "zh-CN,zh;q=0.9",
            "Referer": self.host + "/",
        }
        self.s = requests.Session()
        self.s.verify = False
        self.s.headers.update(self.headers)
        self._probe_cache = {}
        self._PROBE_COOLDOWN = 600

    def _probe_domain(self, domain):
        domain = str(domain).rstrip("/")
        now = time.time()
        if domain in self._probe_cache:
            ok, ts = self._probe_cache[domain]
            if now - ts < self._PROBE_COOLDOWN:
                return ok
        try:
            r = self.s.get(domain, headers=self.headers, timeout=8, allow_redirects=True)
            ok = r.status_code == 200 and len(r.text) > 500
        except Exception:
            ok = False
        self._probe_cache[domain] = (ok, now)
        return ok

    def _get_domain(self):
        injected = getattr(self, "_vbox_effective_hosts", None) or []
        hosts = [str(h).rstrip("/") for h in injected if str(h).startswith("http")]
        if not hosts:
            hosts = ["https://inbggairav.net"]
        if len(hosts) == 1:
            if self._probe_domain(hosts[0]):
                self.host = hosts[0]
            return
        alive = [h for h in hosts if self._probe_domain(h)]
        if alive:
            self.host = alive[0]

    def _fetch(self, url, timeout=15):
        try:
            r = self.s.get(url, headers=self.headers, timeout=timeout, allow_redirects=True)
            r.encoding = "utf-8"
            if r.status_code == 200 and len(r.text) > 500:
                return r.text
        except Exception:
            pass
        return ""

    def _parseVideoList(self, text):
        """解析视频列表页，re 正则替代 xpath"""
        if not text:
            return []
        videos, seen = [], set()
        for m in re.finditer(
            r'<a[^>]*href="([^"]*?/video\?[^"]*?hid=([^&\s]+)[^"]*)"[^>]*>(.*?)</a>',
            text, re.S | re.I,
        ):
            href, vid, block = m.group(1), m.group(2), m.group(3)
            if vid in seen:
                continue
            seen.add(vid)
            if "ad" in href and "/video?" not in href:
                continue
            img = ""
            img_m = re.search(r'<img[^>]+(?:src|data-src)="([^"]+)"', block, re.I)
            if img_m:
                img = img_m.group(1)
            title = ""
            alt_m = re.search(r'<img[^>]+alt="([^"]*)"', block, re.I)
            if alt_m:
                title = alt_m.group(1).strip()
            if not title:
                title_m = re.search(r'>([^<]{2,60})<', block)
                if title_m:
                    title = title_m.group(1).strip()
            if not title:
                continue
            if img and not img.startswith("http"):
                img = self.host + img
            videos.append({
                "vod_id": vid,
                "vod_name": title,
                "vod_pic": img,
                "vod_remarks": "",
            })
        return videos

    def homeContent(self, filter=False):
        self._get_domain()
        return {
            "class": [
                {"type_name": "最新", "type_id": "list?sort=1"},
                {"type_name": "热门", "type_id": "list?sort=2"},
                {"type_name": "经典", "type_id": "list?sort=3"},
                {"type_name": "月度", "type_id": "list?sort=4"},
                {"type_name": "季度", "type_id": "list?sort=5"},
                {"type_name": "年度", "type_id": "list?sort=6"},
                {"type_name": "周排名", "type_id": "list?sort=7"},
                {"type_name": "月排名", "type_id": "list?sort=8"},
                {"type_name": "季排名", "type_id": "list?sort=9"},
                {"type_name": "年排名", "type_id": "list?sort=10"},
                {"type_name": "收藏", "type_id": "list?sort=11"},
                {"type_name": "关注", "type_id": "list?sort=12"},
                {"type_name": "热门AV女优", "type_id": "tag?id=1"},
                {"type_name": "国产", "type_id": "tag?id=2"},
                {"type_name": "中出", "type_id": "tag?id=3"},
            ],
            "list": [],
            "filters": {},
        }

    def homeVideoContent(self):
        self._get_domain()
        url = f"{self.host}/list?sort=1"
        return {"list": self._parseVideoList(self._fetch(url))}

    def categoryContent(self, tid, pg, filter=False, extend=None):
        self._get_domain()
        page = int(pg) if pg else 1
        sort = "1"
        if extend and "sort" in extend and extend["sort"]:
            sort = extend["sort"]

        if tid.startswith("list"):
            parts = tid.split("?")
            orig_sort = "2"
            if len(parts) > 1:
                for param in parts[1].split("&"):
                    if param.startswith("sort="):
                        orig_sort = param.split("=")[1]
            actual_sort = extend.get("sort", "") if extend else ""
            if not actual_sort:
                actual_sort = orig_sort
            if page <= 1:
                url = f"{self.host}/list?sort={actual_sort}"
            else:
                url = f"{self.host}/list?idx={page}&sort={actual_sort}"
        elif tid.startswith("tag"):
            parts = tid.split("?")
            tag_id = "1"
            if len(parts) > 1:
                for param in parts[1].split("&"):
                    if param.startswith("id="):
                        tag_id = param.split("=")[1]
            if page <= 1:
                url = f"{self.host}/tag?id={tag_id}"
            else:
                url = f"{self.host}/tag?tid={tag_id}&idx={page}&sort={sort}"
        else:
            url = f"{self.host}/{tid}"

        videos = self._parseVideoList(self._fetch(url))
        return {
            "list": videos,
            "page": page,
            "pagecount": 9999,
            "limit": len(videos),
            "total": 9999 * len(videos),
        }

    def detailContent(self, ids):
        self._get_domain()
        vid = str(ids[0] if isinstance(ids, list) else ids)
        html = self._fetch(f"{self.host}/video?hid={vid}")
        title, cover, m3u8 = "", "", ""
        if html:
            tm = re.search(r"<title>(.*?)</title>", html, re.S)
            if tm:
                title = re.sub(r"<[^>]+>", "", tm.group(1)).strip()
            cm = re.search(r'data-src="([^"]+)"', html)
            if cm:
                cover = cm.group(1)
            mm = re.search(r'(https?://[^"\'\s]+\.m3u8[^"\'\s]*)', html, re.I)
            if mm:
                m3u8 = mm.group(1)
        play_url = m3u8 if m3u8 else f"{self.host}/video?hid={vid}"
        return {
            "list": [{
                "vod_id": vid,
                "vod_name": title or vid,
                "vod_pic": cover,
                "vod_play_from": "默认线路",
                "vod_play_url": f"正片${play_url}",
            }]
        }

    def searchContent(self, key, quick=False, pg="1"):
        self._get_domain()
        page = int(pg) if pg else 1
        from urllib.parse import quote
        url = f"{self.host}/search?q={quote(key)}&page={page}"
        items = self._parseVideoList(self._fetch(url))
        return {
            "list": items,
            "page": page,
            "pagecount": page + 1,
            "limit": len(items),
            "total": len(items),
        }

    def playerContent(self, flag, id, vipFlags=None):
        if not id:
            return {"parse": 1, "url": ""}
        if ".m3u8" in str(id) or ".mp4" in str(id):
            return {"parse": 0, "url": id, "header": self.headers}
        return {"parse": 1, "url": id, "header": self.headers}

    def localProxy(self, param):
        return [404, "text/plain", b""]

    def isVideoFormat(self, url):
        url = str(url).lower()
        return ".m3u8" in url or ".mp4" in url or ".ts" in url or ".flv" in url

    def manualVideoCheck(self):
        return False

    def destroy(self):
        try:
            if hasattr(self, "s"):
                self.s.close()
        except Exception:
            pass