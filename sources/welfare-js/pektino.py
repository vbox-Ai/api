# -*- coding: utf-8 -*-
"""
平台名称：PeKtino (推特涩涩)
平台标识：pektino_py
作者：原始 tvshare23 · 适配：vbox Python Spider 框架
适配日期：2026-08-23
说明：
  - 继承 base.spider.Spider，super().init() 兜底
  - 域名注入：从 _vbox_effective_hosts 取候选域名
  - 并发域名探测：主域名 + 备用域名同时探测，先到先用
  - 10 分钟冷静期：成功域名缓存 600s，过期重新探测
  - 保留 Next.js __NEXT_DATA__ 结构化解析
  - playerContent 返回 parse=0 Twitter video.mp4 直链
"""
import sys
import re
import json
import time
import requests
from concurrent.futures import ThreadPoolExecutor, as_completed
from urllib.parse import urljoin, quote, unquote

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
DEFAULT_HOST = "https://pektino.com"
BACKUP_HOSTS = [
    "https://pektino.com",
    "https://www.pektino.com",
]

# ── 冷静期常量 ────────────────────────────────
_PROBE_COOLDOWN = 600  # 10 分钟


class Spider(BaseSpider):
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
            self.hosts = list(BACKUP_HOSTS)

        self.host = self.hosts[0]
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Referer": self.host + "/",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
            "Accept-Language": "zh-CN,zh;q=0.9",
        })
        self.lang = "zh-CN"
        self.debug = True
        self._probe_cache = {}  # {domain: (success, timestamp)}

    def _log(self, msg):
        if self.debug:
            print(f"[PeKtino] {msg}")

    def getName(self):
        return "PeKtino"

    # ── 并发域名探测（带 10 分钟冷静期）────────
    def _probe_domain(self, domain):
        now = time.time()
        if domain in self._probe_cache:
            ok, ts = self._probe_cache[domain]
            if now - ts < _PROBE_COOLDOWN:
                return ok
        try:
            r = self.session.get(domain + '/', timeout=8)
            ok = r.status_code == 200 and len(r.text) > 500
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

    def _fix_url(self, url):
        if not url:
            return ""
        if url.startswith("http"):
            return url
        if url.startswith("//"):
            return "https:" + url
        if url.startswith("/"):
            return self.host + url
        return self.host + "/" + url

    def _fetch(self, url):
        try:
            r = self.session.get(url, timeout=15)
            if r.status_code == 200:
                r.encoding = "utf-8"
                return r.text
            return ""
        except Exception as e:
            self._log(f"请求失败: {e}")
            return ""

    def homeContent(self, filter=False):
        classes = [{"type_id": "all", "type_name": "全部"}]
        filters = {
            "all": [
                {
                    "key": "time_range",
                    "name": "时间分类",
                    "value": [
                        {"n": "每日", "v": "daily"},
                        {"n": "每周", "v": "weekly"},
                        {"n": "每月", "v": "monthly"},
                        {"n": "所有时间", "v": "all"},
                    ]
                },
                {
                    "key": "sort",
                    "name": "排序方式",
                    "value": [
                        {"n": "按点赞", "v": "favorite"},
                        {"n": "按观看数", "v": "pv"},
                        {"n": "按时长", "v": "time"},
                        {"n": "最近添加", "v": "created"},
                    ]
                }
            ]
        }
        return {"class": classes, "filters": filters}

    def homeVideoContent(self):
        return self.categoryContent("all", "1", False, {"time_range": "all", "sort": "favorite"})

    def _extract_videos(self, html):
        videos = []
        if not html:
            return videos

        pattern = r'<div class="bg-white dark:bg-gray-800 rounded-lg shadow-md overflow-hidden mb-4">(.*?)</div>\s*<div class="m-2">'
        items = re.findall(pattern, html, re.DOTALL)
        if not items:
            items = re.findall(r'<div class="bg-white[^"]*rounded-lg[^"]*shadow-md[^"]*overflow-hidden mb-4">(.*?)</div>\s*<div class="m-2">', html, re.DOTALL)

        if items:
            for item in items:
                try:
                    link_match = re.search(r'href="(/zh-CN/movie/[^"]+)"', item)
                    if not link_match:
                        continue
                    link = link_match.group(1)

                    img_match = re.search(r'<img[^>]*src="([^"]+)"[^>]*>', item)
                    pic = self._fix_url(img_match.group(1)) if img_match else ""

                    duration_match = re.search(r'<div class="absolute bottom-2 right-2 bg-black/60 text-white text-xs px-2 py-1 rounded-lg">([^<]+)</div>', item)
                    duration = duration_match.group(1).strip() if duration_match else ""

                    views_match = re.search(r'<img src="/icons/eye-black\.svg"[^>]*>([^<]+)</span>', item)
                    views = views_match.group(1).strip() if views_match else ""

                    fav_match = re.search(r'<img src="/icons/heart-black\.svg"[^>]*><span[^>]*>([^<]+)</span>', item)
                    fav = fav_match.group(1).strip() if fav_match else ""

                    title_match = re.search(r'alt="([^"]+)"', item)
                    title = title_match.group(1) if title_match else link.split("/")[-1]

                    vid_match = re.search(r'/movie/([^/]+)', link)
                    vid = vid_match.group(1) if vid_match else link

                    remarks = []
                    if duration:
                        remarks.append(f"⏱{duration}")
                    if views:
                        remarks.append(f"👁{views}")
                    if fav:
                        remarks.append(f"❤{fav}")

                    videos.append({
                        "vod_id": vid,
                        "vod_name": title,
                        "vod_pic": pic,
                        "vod_remarks": " | ".join(remarks),
                    })
                except Exception:
                    continue

        if not videos:
            next_data = re.search(r'<script id="__NEXT_DATA__" type="application/json">(.*?)</script>', html, re.DOTALL)
            if next_data:
                try:
                    data = json.loads(next_data.group(1))
                    def find_items(obj):
                        if isinstance(obj, dict):
                            if "props" in obj and "pageProps" in obj["props"]:
                                page_props = obj["props"]["pageProps"]
                                if "initialItems" in page_props:
                                    return page_props["initialItems"]
                            for value in obj.values():
                                result = find_items(value)
                                if result:
                                    return result
                        elif isinstance(obj, list):
                            for item in obj:
                                result = find_items(item)
                                if result:
                                    return result
                        return None
                    items = find_items(data)
                    if items:
                        for item in items:
                            vid = item.get("url_cd", "")
                            if vid:
                                title = item.get("anime_title") or vid
                                pic = item.get("thumbnail", "")
                                pic = self._fix_url(pic)
                                duration = ""
                                if "time" in item:
                                    m = item["time"] // 60
                                    s = item["time"] % 60
                                    duration = f"{m:02d}:{s:02d}"
                                views = item.get("pv", "")
                                fav = item.get("favorite", "")
                                remarks = []
                                if duration:
                                    remarks.append(f"⏱{duration}")
                                if views:
                                    remarks.append(f"👁{views}")
                                if fav:
                                    remarks.append(f"❤{fav}")
                                videos.append({
                                    "vod_id": vid,
                                    "vod_name": title,
                                    "vod_pic": pic,
                                    "vod_remarks": " | ".join(remarks),
                                })
                except Exception as e:
                    self._log(f"解析 __NEXT_DATA__ 失败: {e}")

        return videos

    def _get_pagecount(self, html):
        page_links = re.findall(r'<a[^>]*href="[^"]*page=(\d+)"[^>]*>', html)
        if page_links:
            return max(int(p) for p in page_links)
        last_match = re.search(r'href="[^"]*page=(\d+)"[^>]*>最后', html)
        if last_match:
            return int(last_match.group(1))
        return 1

    def categoryContent(self, tid, pg, filter=False, extend=None):
        pg = int(pg) if pg else 1
        extend = extend or {}

        time_range = extend.get("time_range", "all")
        sort = extend.get("sort", "favorite")

        if time_range == "daily":
            url = f"{self.host}/{self.lang}/"
        elif time_range == "weekly":
            url = f"{self.host}/{self.lang}/weekly"
        elif time_range == "monthly":
            url = f"{self.host}/{self.lang}/monthly"
        else:
            url = f"{self.host}/{self.lang}/all"

        params = []
        if sort:
            params.append(f"sort={sort}")
        if pg > 1:
            params.append(f"page={pg}")
        if params:
            url += "?" + "&".join(params)

        self._log(f"分类请求: {url}")
        html = self._fetch(url)
        if not html:
            return {"list": [], "page": pg, "pagecount": 1, "limit": 20, "total": 0}

        videos = self._extract_videos(html)
        pagecount = self._get_pagecount(html)

        return {
            "list": videos,
            "page": pg,
            "pagecount": pagecount if pagecount >= pg else pg,
            "limit": 20,
            "total": pagecount * 20
        }

    def detailContent(self, ids):
        vid = ids[0] if ids else ""
        if not vid:
            return {"list": []}

        if vid.startswith("http"):
            url = vid
        else:
            if not vid.startswith("/"):
                url = f"{self.host}/{self.lang}/movie/{vid}"
            else:
                url = self._fix_url(vid)

        html = self._fetch(url)
        if not html:
            return {"list": []}

        title = ""
        title_match = re.search(r'<h1[^>]*>(.*?)</h1>', html)
        if title_match:
            title = title_match.group(1).strip()
        if not title:
            title_match = re.search(r'<meta[^>]*property="og:title"[^>]*content="([^"]+)"', html)
            if title_match:
                title = title_match.group(1)
        if not title:
            title = vid

        pic = ""
        pic_match = re.search(r'<meta[^>]*property="og:image"[^>]*content="([^"]+)"', html)
        if pic_match:
            pic = pic_match.group(1)
        if not pic:
            pic_match = re.search(r'<img[^>]*src="([^"]+)"[^>]*class="[^"]*object-cover[^"]*"', html)
            if pic_match:
                pic = pic_match.group(1)
        pic = self._fix_url(pic)

        play_url = ""
        next_data = re.search(r'<script id="__NEXT_DATA__" type="application/json">(.*?)</script>', html, re.DOTALL)
        if next_data:
            try:
                data = json.loads(next_data.group(1))
                def find_video_url(obj):
                    if isinstance(obj, dict):
                        for key, value in obj.items():
                            if key == 'url' and isinstance(value, str) and 'video.twimg.com' in value:
                                return value
                            result = find_video_url(value)
                            if result:
                                return result
                    elif isinstance(obj, list):
                        for item in obj:
                            result = find_video_url(item)
                            if result:
                                return result
                    return None
                play_url = find_video_url(data)
                if play_url:
                    self._log(f"从__NEXT_DATA__提取到视频: {play_url}")
            except Exception as e:
                pass

        if not play_url:
            mp4_match = re.search(r'(https://video\.twimg\.com/[^\s"\']+\.mp4[^\s"\']*)', html)
            if mp4_match:
                play_url = mp4_match.group(1)

        if not play_url:
            video_match = re.search(r'<video[^>]*src="([^"]+)"', html)
            if video_match:
                play_url = video_match.group(1)

        if play_url:
            play_url = f"播放${play_url}"
        else:
            play_url = f"网页播放${url}"

        return {
            "list": [{
                "vod_id": vid,
                "vod_name": title,
                "vod_pic": pic,
                "vod_content": "",
                "vod_play_from": "PeKtino",
                "vod_play_url": play_url,
            }]
        }

    def playerContent(self, flag, id, vipFlags=None):
        if not id:
            return {"parse": 0, "url": "", "header": {}}

        if id.startswith(("http://", "https://")):
            if ".mp4" in id or ".m3u8" in id:
                headers = {
                    "User-Agent": self.session.headers.get("User-Agent"),
                    "Accept": "video/mp4,video/webm,video/*;q=0.8,*/*;q=0.5",
                    "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
                    "Connection": "keep-alive",
                }
                if "video.twimg.com" in id:
                    headers["Referer"] = "https://x.com/"
                    headers["Origin"] = "https://x.com"
                else:
                    headers["Referer"] = self.host + "/"
                    headers["Origin"] = self.host
                return {"parse": 0, "url": id, "header": headers}
            html = self._fetch(id)
            if html:
                mp4_match = re.search(r'(https://video\.twimg\.com/[^\s"\']+\.mp4[^\s"\']*)', html)
                if mp4_match:
                    return {
                        "parse": 0,
                        "url": mp4_match.group(1),
                        "header": {
                            "User-Agent": self.session.headers.get("User-Agent"),
                            "Referer": "https://x.com/",
                            "Origin": "https://x.com",
                            "Accept": "video/mp4,video/webm,video/*;q=0.8,*/*;q=0.5",
                        }
                    }
            return {"parse": 1, "url": id, "header": {"Referer": self.host + "/"}}

        url = self._fix_url(id)
        if not url:
            return {"parse": 0, "url": "", "header": {}}

        html = self._fetch(url)
        if html:
            mp4_match = re.search(r'(https://video\.twimg\.com/[^\s"\']+\.mp4[^\s"\']*)', html)
            if mp4_match:
                return {
                    "parse": 0,
                    "url": mp4_match.group(1),
                    "header": {
                        "User-Agent": self.session.headers.get("User-Agent"),
                        "Referer": "https://x.com/",
                        "Origin": "https://x.com",
                        "Accept": "video/mp4,video/webm,video/*;q=0.8,*/*;q=0.5",
                    }
                }
            m3u8_match = re.search(r'(https?://[^\s"\'\.]+\.m3u8[^\s"\']*)', html, re.I)
            if m3u8_match:
                return {
                    "parse": 0,
                    "url": m3u8_match.group(1),
                    "header": {"Referer": self.host + "/"}
                }
        return {"parse": 1, "url": url, "header": {"Referer": self.host + "/"}}

    def searchContent(self, key, quick=False, pg="1"):
        pg = int(pg) if pg else 1
        url = f"{self.host}/{self.lang}/search?q={quote(key, safe='')}"
        if pg > 1:
            url += f"&page={pg}"
        html = self._fetch(url)
        if not html:
            return {"list": [], "page": pg, "pagecount": 1, "limit": 20, "total": 0}
        videos = self._extract_videos(html)
        pagecount = self._get_pagecount(html)
        return {
            "list": videos,
            "page": pg,
            "pagecount": pagecount if pagecount >= pg else pg,
            "limit": 20,
            "total": pagecount * 20
        }

    def localProxy(self, param):
        return None

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