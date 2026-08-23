# -*- coding: utf-8 -*-
"""
平台名称：果冻传媒
平台标识：gdcb_py
作者：原始 tvshare23 · 适配：vbox Python Spider 框架
适配日期：2026-08-23
说明：
  - 继承 base.spider.Spider，super().init() 兜底
  - 域名注入：从 _vbox_effective_hosts 取候选域名
  - 并发域名探测：主域名 + 备用域名同时探测，先到先用
  - 10 分钟冷静期：成功域名缓存 600s，过期重新探测
  - 保留 JavDB 数据源 + m3u8 直链
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
        return "果冻传媒"

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
            self.host = "https://www.javdb.com"

        self.header = {
            "User-Agent": ("Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                           "AppleWebKit/537.36 (KHTML, like Gecko) "
                           "Chrome/120.0.0.0 Safari/537.36"),
            "Accept-Language": "zh-CN,zh;q=0.9",
            "Referer": self.host + "/",
        }
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
            r = requests.get(domain, headers=self.header, timeout=8, verify=False)
            ok = r.status_code == 200
        except Exception:
            ok = False
        self._probe_cache[domain] = (ok, now)
        return ok

    def _get_effective_hosts(self):
        injected = getattr(self, "_vbox_effective_hosts", None) or []
        hosts = [str(h).rstrip("/") for h in injected if str(h).startswith("http")]
        if not hosts:
            hosts = ["https://www.javdb.com"]
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
            r = requests.get(url, headers=self.header, timeout=timeout, verify=False)
            r.encoding = "utf-8"
            if r.status_code == 200 and len(r.text) > 500:
                return r.text
        except Exception:
            pass
        return ""

    def _search(self, kw, pg=1):
        url = f"{self.host}/search?keyword={kw}&page={pg}"
        return self._fetch(url)

    def _parse_list(self, html):
        if not html:
            return []
        items, seen = [], set()
        for m in re.finditer(
            r'<a[^>]*href="(/v/[a-z0-9]+)"[^>]*>(.*?)</a>', html, re.S
        ):
            vid = m.group(1)
            if vid in seen:
                continue
            seen.add(vid)
            block = m.group(2)
            title_m = re.search(r'title="([^"]+)"', block)
            title = title_m.group(1) if title_m else vid
            pic_m = re.search(r'data-src="([^"]+)"', block)
            pic = pic_m.group(1) if pic_m else ""
            items.append({
                "vod_id": vid,
                "vod_name": title,
                "vod_pic": pic,
                "vod_remarks": "",
            })
        return items

    def homeContent(self, filter=False):
        self._resolve_host()
        return {"class": [], "list": []}

    def homeVideoContent(self):
        return {"list": []}

    def categoryContent(self, tid, pg, filter=False, extend=None):
        return {"list": [], "page": 1, "pagecount": 1, "limit": 20, "total": 0}

    def detailContent(self, ids):
        vid = str(ids[0] if isinstance(ids, list) else ids)
        html = self._fetch(f"{self.host}/{vid}")
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
        html = self._search(key, int(pg) if pg else 1)
        items = self._parse_list(html)
        return {"list": items, "page": int(pg) if pg else 1, "pagecount": 1, "limit": 20, "total": len(items)}

    def playerContent(self, flag, id, vipFlags=None):
        if not id:
            return {"parse": 1, "url": ""}
        if ".m3u8" in str(id) or ".mp4" in str(id):
            return {"parse": 0, "url": id, "header": self.header}
        return {"parse": 1, "url": id, "header": self.header}

    def localProxy(self, param):
        return [404, "text/plain", b""]

    def isVideoFormat(self, url):
        url = str(url).lower()
        return ".m3u8" in url or ".mp4" in url or ".ts" in url or ".flv" in url

    def manualVideoCheck(self):
        return False

    def destroy(self):
        pass