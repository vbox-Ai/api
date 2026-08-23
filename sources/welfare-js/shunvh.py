# -*- coding: utf-8 -*-
"""
平台名称：熟女汇
平台标识：shunvhzuna_py
作者：原始 tvshare23 · 适配：vbox Python Spider 框架
适配日期：2026-08-23
说明：
  - 继承 base.spider.Spider，super().init() 兜底
  - 域名注入：从 _vbox_effective_hosts 取候选域名
  - 并发域名探测：主域名 + 备用域名同时探测，先到先用
  - 10 分钟冷静期：成功域名缓存 600s，过期重新探测
  - 保留 iframe 嵌套 m3u8 提取
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
        return "shunvhzuna"

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
            self.host = "https://shunvhzuna.lol"

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

    def _get_effective_hosts(self):
        injected = getattr(self, "_vbox_effective_hosts", None) or []
        hosts = [str(h).rstrip("/") for h in injected if str(h).startswith("http")]
        if not hosts:
            hosts = ["https://shunvhzuna.lol"]
        return hosts

    def _resolve_host(self):
        hosts = self._get_effective_hosts()
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

    def _parse_list(self, text):
        if not text:
            return []
        items, seen = [], set()
        for m in re.finditer(
            r'<a[^>]*href="(/v/\d+[^"]*)"[^>]*>(.*?)</a>', text, re.S
        ):
            vid = m.group(1)
            if vid in seen:
                continue
            seen.add(vid)
            block = m.group(2)
            title = ""
            tm = re.search(r"<h2[^>]*>([^<]+)</h2>", block)
            if tm:
                title = tm.group(1).strip()
            if not title:
                title = vid
            pic = ""
            pm = re.search(r'data-src="([^"]+)"', block)
            if pm:
                pic = pm.group(1)
            items.append({
                "vod_id": vid,
                "vod_name": title,
                "vod_pic": pic,
                "vod_remarks": "",
            })
        return items

    def homeContent(self, filter=False):
        self._resolve_host()
        return {"class": [], "list": self._parse_list(self._fetch(self.host + "/"))}

    def homeVideoContent(self):
        return {"list": []}

    def categoryContent(self, tid, pg, filter=False, extend=None):
        self._resolve_host()
        page = int(pg) if pg else 1
        url = f"{self.host}/list/{tid}?page={page}"
        items = self._parse_list(self._fetch(url))
        return {
            "list": items,
            "page": page,
            "pagecount": page + 1,
            "limit": len(items),
            "total": len(items),
        }

    def detailContent(self, ids):
        self._resolve_host()
        vid = str(ids[0] if isinstance(ids, list) else ids)
        html = self._fetch(f"{self.host}/{vid}")
        if not html:
            return {"list": []}
        title, cover, m3u8 = "", "", ""
        tm = re.search(r"<title>(.*?)</title>", html, re.S)
        if tm:
            title = re.sub(r"<[^>]+>", "", tm.group(1)).strip()
        cm = re.search(r'data-src="([^"]+)"', html)
        if cm:
            cover = cm.group(1)
        for m in re.finditer(r'<iframe[^>]+src="([^"]+)"[^>]*>', html, re.S):
            iframe_src = m.group(1)
            if iframe_src.startswith("//"):
                iframe_src = "https:" + iframe_src
            if not iframe_src.startswith("http"):
                iframe_src = self.host + "/" + iframe_src.lstrip("/")
            iframe_html = self._fetch(iframe_src)
            if iframe_html:
                mm = re.search(r"(https?://[^\"'\s]+\.m3u8[^\"'\s]*)", iframe_html, re.I)
                if mm:
                    m3u8 = mm.group(1)
                    break
        if not m3u8:
            mm = re.search(r"(https?://[^\"'\s]+\.m3u8[^\"'\s]*)", html, re.I)
            if mm:
                m3u8 = mm.group(1)
        play_url = m3u8 if m3u8 else f"{self.host}/{vid}"
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
        self._resolve_host()
        page = int(pg) if pg else 1
        url = f"{self.host}/search?kw={quote(key)}&page={page}"
        items = self._parse_list(self._fetch(url))
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
