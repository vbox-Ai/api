# -*- coding: utf-8 -*-
"""
平台名称：JavGG
平台标识：javgg_py
作者：原始 tvshare23 · 适配：vbox Python Spider 框架
适配日期：2026-08-23
说明：
  - 继承 base.spider.Spider，super().init() 兜底
  - 域名注入：从 _vbox_effective_hosts 取候选域名
  - 并发域名探测：3 个域名同时探测，先到先用
  - 10 分钟冷静期：成功域名缓存 600s，过期重新探测
  - playerContent 优先提取 m3u8/mp4 直链，兜底 parse=1
  - 返回 dict 而非 JSON 字符串
  - localProxy 返回空（该站点不需要图片代理）
"""
import re
import json
import time
import requests
from concurrent.futures import ThreadPoolExecutor, as_completed
from urllib.parse import quote

try:
    from base.spider import Spider as BaseSpider
except ImportError:
    class BaseSpider:
        def init(self, extend=""): pass
        def fetch(self, url, headers=None, **kw):
            kw.pop('timeout', None)
            r = requests.get(url, headers=headers, timeout=15, **kw)
            r.encoding = 'utf-8'
            return r
        def getProxyUrl(self):
            return ''

# ── 平台配置 ──────────────────────────────────
DEFAULT_HOSTS = [
    "https://javgg.co",
    "https://javgg.net",
    "https://javgg.club"
]
DEFAULT_HOST = "https://javgg.co"
HEADER = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
    "Accept-Language": "zh-CN,zh;q=0.9",
    "Connection": "keep-alive"
}

# ── 冷静期常量 ────────────────────────────────
_PROBE_COOLDOWN = 600  # 10 分钟


class Spider(BaseSpider):
    def getName(self):
        return "JavGG"

    def init(self, extend=""):
        # 1) 先 super，让 base.spider 注入 _vbox_effective_hosts
        try:
            super().init(extend)
        except Exception:
            pass

        # 2) 域名注入
        injected = getattr(self, '_vbox_effective_hosts', None) or []
        if injected:
            self.hosts = [str(h).rstrip('/') for h in injected]
        else:
            self.hosts = list(DEFAULT_HOSTS)

        self.host = self.hosts[0]
        self.header = dict(HEADER)
        self.header["Referer"] = self.host + "/"
        self.proxies = None
        self._probe_cache = {}  # {domain: (success, timestamp)}

    # ── 并发域名探测（带 10 分钟冷静期）────────
    def _probe_domain(self, domain):
        now = time.time()
        if domain in self._probe_cache:
            ok, ts = self._probe_cache[domain]
            if now - ts < _PROBE_COOLDOWN:
                return ok
        try:
            r = requests.get(
                domain + '/',
                headers={**self.header, "Referer": domain + "/"},
                timeout=8,
                verify=False,
                proxies=self.proxies,
                allow_redirects=True
            )
            ok = r.status_code == 200 and len(r.text) > 1500
        except Exception:
            ok = False
        self._probe_cache[domain] = (ok, now)
        return ok

    def _resolve_hosts(self):
        """并发探测所有候选域名，返回可用域名列表"""
        now = time.time()
        cached_ok = []
        need_probe = []
        for d in self.hosts:
            if d in self._probe_cache:
                ok, ts = self._probe_cache[d]
                if now - ts < _PROBE_COOLDOWN:
                    if ok:
                        cached_ok.append(d)
                    continue
            need_probe.append(d)

        if cached_ok and not need_probe:
            return cached_ok

        if need_probe:
            results = []
            with ThreadPoolExecutor(max_workers=len(need_probe)) as ex:
                futs = {ex.submit(self._probe_domain, d): d for d in need_probe}
                for f in as_completed(futs):
                    d = futs[f]
                    if f.result():
                        results.append(d)
            return cached_ok + results
        return cached_ok

    def get_html(self, url, timeout=12):
        """并发请求所有可用域名，先到先得"""
        hosts = self._resolve_hosts()
        if not hosts:
            hosts = self.hosts

        def try_host(h):
            try:
                real_url = url
                if self.host in url:
                    real_url = url.replace(self.host, h)
                elif not url.startswith("http"):
                    real_url = h.rstrip("/") + "/" + url.lstrip("/")
                r = requests.get(
                    real_url,
                    headers={**self.header, "Referer": h + "/"},
                    timeout=timeout,
                    verify=False,
                    proxies=self.proxies,
                    allow_redirects=True
                )
                if r.status_code == 200 and len(r.text) > 1500:
                    return h, r.text
            except Exception:
                pass
            return None, ""

        with ThreadPoolExecutor(max_workers=len(hosts)) as ex:
            futs = [ex.submit(try_host, h) for h in hosts]
            for f in as_completed(futs):
                h, text = f.result()
                if text:
                    self.host = h
                    self.header["Referer"] = h + "/"
                    self._probe_cache[h] = (True, time.time())
                    return text
        return ""

    def fix_url(self, url):
        if not url:
            return ""
        if url.startswith("//"):
            return "https:" + url
        if url.startswith("/"):
            return self.host + url
        return url

    def clean_text(self, text):
        if not text:
            return ""
        return re.sub(r'\s+', ' ', str(text)).strip()

    def get_pic(self, html, vod_id=""):
        patterns = [
            r'<img[^>]+(?:data-src|data-original|src)=["\']([^"\']+)["\'][^>]*(?:alt=["\'][^"\']*' + re.escape(vod_id) + r'[^"\']*["\'])?',
            r'<img[^>]+(?:data-src|data-original|src)=["\']([^"\']+(?:jpg|jpeg|png|webp)[^"\']*)["\']',
            r'property=["\']og:image["\'][^>]+content=["\']([^"\']+)["\']',
            r'<meta[^>]+content=["\']([^"\']+)["\'][^>]+property=["\']og:image["\']',
            r'data-src=["\']([^"\']+)["\']',
            r'src=["\']([^"\']+(?:cover|poster|thumb|jav)[^"\']*)["\']'
        ]
        for pat in patterns:
            m = re.search(pat, html, re.I)
            if m:
                pic = self.fix_url(m.group(1))
                if pic and ("http" in pic) and not pic.endswith(".svg"):
                    return pic
        return ""

    def _extract_items(self, html):
        """从 HTML 中提取视频列表"""
        items = re.findall(
            r'<img[^>]+(?:data-src|data-original|src)=["\']([^"\']+)["\'][^>]*>.*?(?:href=["\'][^"\']*?/jav/([a-zA-Z0-9\-_]+)/?["\'][^>]*>\s*([A-Z0-9\-_]+)|/jav/([a-zA-Z0-9\-_]+)/)',
            html, re.I | re.S
        )
        seen = set()
        result = []
        for it in items:
            try:
                pic = self.fix_url(it[0])
                vod_id = (it[1] or it[3] or "").strip("-_").lower()
                name = it[2] if it[2] else vod_id
                if not vod_id or len(vod_id) < 4 or vod_id in seen:
                    continue
                seen.add(vod_id)
                result.append({
                    "vod_id": vod_id,
                    "vod_name": self.clean_text(name) or vod_id.upper(),
                    "vod_pic": pic if "http" in pic else "",
                    "vod_remarks": ""
                })
            except Exception:
                continue

        # 兜底：只提取番号
        if len(result) < 5:
            patterns = [
                r'href=["\']([^"\']*?/jav/([a-zA-Z0-9\-_]+)/?)["\'][^>]*>\s*([A-Z0-9\-_]+)',
                r'/jav/([a-zA-Z0-9\-_]+)/["\'][^>]*>\s*([A-Z0-9\-_]+)'
            ]
            for pat in patterns:
                for it in re.findall(pat, html, re.I | re.S):
                    try:
                        if len(it) >= 2:
                            vod_id = it[1]
                            name = it[2] if len(it) > 2 else vod_id
                            vod_id = re.sub(r'[^a-zA-Z0-9\-_]', '', str(vod_id)).strip("-_").lower()
                            if not vod_id or len(vod_id) < 4 or vod_id in seen:
                                continue
                            seen.add(vod_id)
                            result.append({
                                "vod_id": vod_id,
                                "vod_name": self.clean_text(name) or vod_id.upper(),
                                "vod_pic": "",
                                "vod_remarks": ""
                            })
                    except Exception:
                        continue
                if len(result) >= 20:
                    break
        return result

    def homeContent(self, filter=False):
        classes = [
            {"type_name": "最新", "type_id": "home"},
            {"type_name": "无码", "type_id": "tag/hd-uncensored"},
            {"type_name": "有码", "type_id": "tag/censored"},
            {"type_name": "英字", "type_id": "tag/english-subtitle"},
            {"type_name": "中字", "type_id": "tag/chinese-subtitle"},
            {"type_name": "素人", "type_id": "tag/amateur-jav"},
            {"type_name": "中出", "type_id": "genre/creampie"},
            {"type_name": "巨乳", "type_id": "genre/big-tits"},
            {"type_name": "人妻", "type_id": "genre/married-woman"},
            {"type_name": "美少女", "type_id": "genre/beautiful-girl"},
            {"type_name": "熟女", "type_id": "genre/mature-woman"},
            {"type_name": "4K", "type_id": "genre/4k"}
        ]
        html = self.get_html(self.host)
        return {"class": classes, "list": self._extract_items(html) if html else []}

    def homeVideoContent(self):
        html = self.get_html(self.host)
        return {"list": self._extract_items(html) if html else []}

    def categoryContent(self, tid, pg, filter=False, extend=None):
        result = {"list": [], "page": pg, "pagecount": 9999, "limit": 40, "total": 999999}
        if tid == "home":
            url = self.host if str(pg) == "1" else f"{self.host}/page/{pg}/"
        else:
            url = f"{self.host}/{tid}/" if str(pg) == "1" else f"{self.host}/{tid}/page/{pg}/"
        html = self.get_html(url)
        if html:
            result["list"] = self._extract_items(html)
        return result

    def detailContent(self, ids):
        result = {"list": []}
        try:
            vod_id = ids[0] if isinstance(ids, list) else ids
            url = f"{self.host}/jav/{vod_id}/"
            html = self.get_html(url)
            if html:
                title_m = re.search(r'<h1[^>]*>([^<]+)</h1>', html, re.I)
                title = self.clean_text(title_m.group(1)) if title_m else vod_id.upper()
                pic = self.get_pic(html, vod_id)

                play_from = []
                play_url = []
                servers = re.findall(r'(?:Server|server)\s*([A-Z]{2})', html, re.I) or ["VH", "TB", "SW"]
                for s in servers:
                    play_from.append(s)
                    play_url.append(f"{s}${url}#{s}")

                if not play_from:
                    play_from = ["JavGG"]
                    play_url = [f"正片${url}"]

                result["list"].append({
                    "vod_id": vod_id,
                    "vod_name": title,
                    "vod_pic": pic,
                    "vod_content": "",
                    "vod_play_from": "$$$".join(play_from),
                    "vod_play_url": "$$$".join(play_url)
                })
        except Exception:
            pass
        return result

    def searchContent(self, key, quick=False, pg="1"):
        result = {"list": []}
        url = f"{self.host}/?s={quote(key)}"
        if str(pg) != "1":
            url = f"{self.host}/page/{pg}/?s={quote(key)}"
        html = self.get_html(url)
        if html:
            result["list"] = self._extract_items(html)
        return result

    def playerContent(self, flag, id, vipFlags=None):
        """播放解析：优先提取 m3u8/mp4 直链，兜底 parse=1"""
        if not id:
            return {"parse": 1, "url": "", "header": {}}

        # 直链格式直接返回
        if any(x in id.lower() for x in [".m3u8", ".mp4"]):
            return {
                "parse": 0,
                "url": id,
                "header": dict(self.header)
            }

        # 第三方播放器链接（streamwish/vidhide/filemoon/dood）→ parse=1
        if any(x in id.lower() for x in ["streamwish", "vidhide", "filemoon", "dood"]):
            return {"parse": 1, "url": id, "header": dict(self.header)}

        # javcode.net base64 解码
        if "javcode.net" in id:
            m = re.search(r'javcode\.net/(?:rg|download)/([A-Za-z0-9+/=]+)', id)
            if m:
                try:
                    decoded = base64.b64decode(m.group(1)).decode('utf-8', 'ignore')
                    if decoded:
                        url = decoded if decoded.startswith("http") else self.fix_url(decoded)
                        return {"parse": 0, "url": url, "header": dict(self.header)}
                except Exception:
                    pass
            return {"parse": 1, "url": id, "header": dict(self.header)}

        # 页面链接：尝试提取 m3u8 / mp4 / video src
        if "/jav/" in id or not id.startswith("http"):
            url = id if id.startswith("http") else f"{self.host}/jav/{id.split('#')[0].strip('/')}/"
            html = self.get_html(url)
            if html:
                # 1) m3u8 直链
                m3u8 = re.search(r'(https?://[^"\'\s]+\.m3u8[^"\'\s]*)', html, re.I)
                if m3u8:
                    return {"parse": 0, "url": m3u8.group(1), "header": dict(self.header)}
                # 2) mp4 直链
                mp4 = re.search(r'(https?://[^"\'\s]+\.mp4[^"\'\s]*)', html, re.I)
                if mp4:
                    return {"parse": 0, "url": mp4.group(1), "header": dict(self.header)}
                # 3) video 标签 src
                video = re.search(r'<video[^>]*src=["\']([^"\']+)["\']', html, re.I)
                if video:
                    return {"parse": 0, "url": video.group(1), "header": dict(self.header)}
                # 4) iframe 兜底 → parse=1
                iframe = re.search(r'<iframe[^>]+src=["\']([^"\']+)["\']', html, re.I)
                if iframe:
                    return {"parse": 1, "url": self.fix_url(iframe.group(1)), "header": dict(self.header)}
            return {"parse": 1, "url": url, "header": dict(self.header)}

        return {"parse": 1, "url": id, "header": dict(self.header)}

    def localProxy(self, param):
        return [200, "text/plain", ""]

    def isVideoFormat(self, url):
        url = str(url).lower()
        return '.m3u8' in url or '.mp4' in url or '.ts' in url or '.flv' in url

    def manualVideoCheck(self):
        return False

    def destroy(self):
        try:
            if hasattr(self, 'session'):
                self.session.close()
        except Exception:
            pass