# -*- coding: utf-8 -*-
"""
平台名称：xHamster中文站
平台标识：xhamster_py
作者：原始 tvshare23 · 适配：vbox Python Spider 框架
适配日期：2026-08-23
说明：
  - 继承 base.spider.Spider，super().init() 兜底
  - 域名注入：从 _vbox_effective_hosts 取候选域名
  - 7 个域名并发探测，先到先用
  - 10 分钟冷静期：成功域名缓存 600s，过期重新探测
  - 保留 AV1→H264 转换（提升播放器兼容性）
  - 返回 dict，playerContent 返回 parse=0 m3u8/mp4 直链
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
SITE_DOMAINS = [
    "https://zh.xhamster1.desi",
    "https://zh.xhamster.com",
    "https://xhamster.com",
    "https://xhamster2.com",
    "https://xhamster3.com",
    "https://xhamster.desi",
    "https://xhamster18.desi",
    "https://xhamster20.desi",
]

HEADERS = {
    "User-Agent": "Mozilla/5.0 (compatible; Googlebot/2.1; +http://www.google.com/bot.html)",
    "Accept": "text/html,application/xhtml+xml",
    "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
    "Accept-Encoding": "gzip, deflate",
    "Referer": "https://zh.xhamster1.desi/",
}

PLAYER_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Referer": "https://zh.xhamster1.desi/",
}

TIMEOUT = 20

CATEGORY_LIST = [
    {"type_id": "newest",          "type_name": "最新视频"},
    {"type_id": "best/weekly",     "type_name": "本周最佳"},
    {"type_id": "best/monthly",    "type_name": "本月最佳"},
    {"type_id": "best",            "type_name": "全部最佳"},
    {"type_id": "hd",              "type_name": "高清视频"},
    {"type_id": "4k",              "type_name": "4K视频"},
    {"type_id": "categories/shorts",    "type_name": "短视频"},
    {"type_id": "categories/asian",      "type_name": "亚洲人"},
    {"type_id": "categories/japanese",   "type_name": "日本人"},
    {"type_id": "categories/chinese",    "type_name": "中国人"},
    {"type_id": "categories/korean",     "type_name": "韩国人"},
    {"type_id": "categories/jav",        "type_name": "日本AV"},
    {"type_id": "categories/uncensored", "type_name": "无码"},
    {"type_id": "categories/milf",       "type_name": "人妻"},
    {"type_id": "categories/mom",        "type_name": "人母"},
    {"type_id": "categories/mature",     "type_name": "成熟"},
    {"type_id": "categories/teen",       "type_name": "青年"},
    {"type_id": "categories/big-tits",   "type_name": "大奶子"},
    {"type_id": "categories/anal",       "type_name": "肛交"},
    {"type_id": "categories/creampie",   "type_name": "内射"},
    {"type_id": "categories/threesome",  "type_name": "3P"},
    {"type_id": "categories/amateur",    "type_name": "素人"},
    {"type_id": "categories/homemade",   "type_name": "家庭自制"},
    {"type_id": "categories/blowjob",    "type_name": "口交"},
    {"type_id": "categories/cosplay",    "type_name": "角色扮演"},
    {"type_id": "categories/hentai",     "type_name": "成人动漫"},
    {"type_id": "categories/cartoon",    "type_name": "卡通"},
    {"type_id": "categories/3d",         "type_name": "3D"},
    {"type_id": "categories/lesbian",    "type_name": "女同"},
    {"type_id": "categories/interracial","type_name": "跨人种"},
    {"type_id": "categories/group-sex",  "type_name": "群交"},
    {"type_id": "categories/gangbang",   "type_name": "多对一群交"},
    {"type_id": "categories/bdsm",       "type_name": "捆绑SM"},
    {"type_id": "categories/webcam",     "type_name": "直播"},
    {"type_id": "categories/pov",        "type_name": "第一人称"},
    {"type_id": "categories/vintage",    "type_name": "复古"},
    {"type_id": "categories/pregnant",   "type_name": "怀孕"},
    {"type_id": "categories/latina",     "type_name": "拉丁美女"},
    {"type_id": "categories/black",     "type_name": "黑人"},
    {"type_id": "categories/indian",     "type_name": "印度"},
    {"type_id": "categories/russian",    "type_name": "俄罗斯人"},
]

SORT_FILTER = {
    "key": "sort", "name": "排序", "init": "",
    "value": [{"n": "默认", "v": ""}, {"n": "最新", "v": "newest"}, {"n": "最佳", "v": "best"}]
}

QUALITY_FILTER = {
    "key": "quality", "name": "画质", "init": "",
    "value": [{"n": "全部", "v": ""}, {"n": "HD", "v": "hd"}, {"n": "4K", "v": "4k"}]
}

DURATION_FILTER = {
    "key": "duration", "name": "时长", "init": "",
    "value": [{"n": "全部", "v": ""}, {"n": "0-10分钟", "v": "0-10"}, {"n": "10-30分钟", "v": "10-30"}, {"n": "30分钟+", "v": "30-9999"}]
}

# ── 冷静期常量 ────────────────────────────────
_PROBE_COOLDOWN = 600


class Spider(BaseSpider):
    def __init__(self):
        self._probe_cache = {}

    def getName(self):
        return "xHamster中文"

    def init(self, extend=""):
        try:
            super().init(extend)
        except Exception:
            pass

        injected = getattr(self, '_vbox_effective_hosts', None) or []
        if injected:
            self._candidates = [str(h).rstrip('/') for h in injected]
        else:
            self._candidates = list(SITE_DOMAINS)

        self.domain = self._get_domain()
        self.session = requests.Session()

    def destroy(self):
        try:
            if hasattr(self, 'session'):
                self.session.close()
        except Exception:
            pass

    def isVideoFormat(self, url):
        if not url:
            return False
        return bool(re.match(r'.*\.(m3u8|mp4|flv|ts)', url, re.IGNORECASE))

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
            resp = requests.head(domain, headers=HEADERS, timeout=10, allow_redirects=True)
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

    def _fetch_html(self, url):
        headers = HEADERS.copy()
        headers["Referer"] = self.domain + "/"
        try:
            resp = requests.get(url, headers=headers, timeout=TIMEOUT, allow_redirects=True)
            if resp.status_code == 200:
                resp.encoding = resp.apparent_encoding or "utf-8"
                return resp.text
            if resp.status_code in (403, 429):
                alt = headers.copy()
                alt["User-Agent"] = (
                    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                    "AppleWebKit/605.1.15 (KHTML, like Gecko) "
                    "Version/17.4 Safari/605.1.15"
                )
                resp2 = requests.get(url, headers=alt, timeout=TIMEOUT)
                if resp2.status_code == 200:
                    resp2.encoding = resp2.apparent_encoding or "utf-8"
                    return resp2.text
        except Exception:
            pass
        return ""

    def _parse_video_list(self, html):
        if not html:
            return []
        videos = []
        seen = set()
        blocks = re.split(r'(?=data-video-id="\d+")', html)
        for block in blocks[1:]:
            try:
                href_m = re.search(r'href="(https?://[^"]*?/videos/[^"?]+)"', block)
                if not href_m:
                    continue
                video_url = href_m.group(1)
                if "/creators/" in video_url:
                    continue
                slug_m = re.search(r'/videos/([^"?]+)', video_url)
                if not slug_m:
                    continue
                vod_id = slug_m.group(1)
                if vod_id in seen:
                    continue
                seen.add(vod_id)
                sb = block[:2000]
                img_m = re.search(r'<img[^>]*?src="(https?://[^"]+)"', sb)
                if not img_m:
                    ns_m = re.search(r'<noscript>\s*<img[^>]*?src="(https?://[^"]+)"', block)
                    if ns_m:
                        img_m = ns_m
                alt_m = re.search(r'<img[^>]*?alt="([^"]*)"', sb)
                if alt_m:
                    vod_name = alt_m.group(1)
                else:
                    aria_m = re.search(r'aria-label="([^"]*)"', sb)
                    vod_name = aria_m.group(1) if aria_m else vod_id
                dur_m = re.search(r'(\d{1,2}:\d{2}(?::\d{2})?)', sb)
                videos.append({
                    "vod_id": vod_id,
                    "vod_name": vod_name,
                    "vod_pic": (img_m.group(1) if img_m else ""),
                    "vod_remarks": (dur_m.group(1) if dur_m else ""),
                })
            except Exception:
                continue
        if not videos:
            for match in re.finditer(r'<a[^>]*href="(https?://[^"]*?/videos/[^"?]+)"[^>]*>(.*?)</a>', html, re.DOTALL):
                video_url = match.group(1)
                if "/creators/" in video_url:
                    continue
                slug_m = re.search(r'/videos/([^"?]+)', video_url)
                if not slug_m:
                    continue
                vod_id = slug_m.group(1)
                if vod_id in seen:
                    continue
                seen.add(vod_id)
                content = match.group(2)
                img_m = re.search(r'<img[^>]*?src="(https?://[^"]+)"', content)
                alt_m = re.search(r'<img[^>]*?alt="([^"]*)"', content)
                if not img_m:
                    ns_m = re.search(r'<noscript>\s*<img[^>]*?src="(https?://[^"]+)"', content)
                    if ns_m:
                        img_m = ns_m
                pos = match.end()
                ctx = html[pos:pos+500]
                dur_m = re.search(r'(\d{1,2}:\d{2}(?::\d{2})?)', ctx)
                videos.append({
                    "vod_id": vod_id,
                    "vod_name": (alt_m.group(1) if alt_m else vod_id),
                    "vod_pic": (img_m.group(1) if img_m else ""),
                    "vod_remarks": (dur_m.group(1) if dur_m else ""),
                })
        return videos

    def _parse_m3u8(self, html):
        if not html:
            return ""
        m = re.search(r'<link[^>]*?rel="preload"[^>]*?href="([^"]+\.m3u8[^"]*)"', html, re.IGNORECASE)
        if m:
            url = m.group(1)
            url = url.replace(".av1.", ".h264.")
            return url
        for m in re.finditer(r'(https?://[^"\'<>\s]+\.m3u8[^"\'<>\s]*)', html):
            url = m.group(1)
            if "thumb-" not in url and "preview" not in url.lower():
                url = url.replace(".av1.", ".h264.")
                return url
        return ""

    def _parse_mp4_list(self, html):
        if not html:
            return []
        seen = set()
        result = []
        for m in re.finditer(r'(https?://[^"\'<>\s]+/\d+p\.h264\.mp4[^"\'<>\s]*)', html):
            url = m.group(1)
            if url not in seen:
                seen.add(url)
                result.append(url)
        return result

    def _parse_page_count(self, html):
        if not html:
            return 1
        max_page = 1
        for m in re.finditer(r'href="[^"]*?(?:/categories/|/search/|/newest|/best/|/hd|/4k|/shorts)[^"]*?/(\d+)"', html):
            try:
                p = int(m.group(1))
                if p > max_page:
                    max_page = p
            except ValueError:
                continue
        return min(max_page, 9999)

    def _parse_title(self, html):
        if not html:
            return ""
        m = re.search(r'<h1[^>]*>(.*?)</h1>', html, re.DOTALL)
        if m:
            t = re.sub(r'<[^>]+>', '', m.group(1)).strip()
            if t:
                return t
        m = re.search(r'<title>(.*?)(?:\s*\|\s*xHamster)?</title>', html, re.IGNORECASE)
        if m:
            return m.group(1).strip()
        return ""

    def _parse_thumbnail(self, html):
        if not html:
            return ""
        m = re.search(r'<meta[^>]*property="og:image"[^>]*content="([^"]+)"', html, re.IGNORECASE)
        if m:
            return m.group(1)
        m = re.search(r'<link[^>]*rel="preload"[^>]*href="([^"]+)"[^>]*as="image"', html, re.IGNORECASE)
        if m:
            return m.group(1)
        return ""

    def homeContent(self, filter=False):
        result = {}
        classes = []
        for cat in CATEGORY_LIST:
            classes.append({"type_id": cat["type_id"], "type_name": cat["type_name"]})
        result["class"] = classes
        if filter:
            filters = {}
            for cat in CATEGORY_LIST:
                tid = cat["type_id"]
                cf = [SORT_FILTER.copy()]
                if tid.startswith("categories/"):
                    cf.append(QUALITY_FILTER.copy())
                cf.append(DURATION_FILTER.copy())
                filters[tid] = cf
            result["filters"] = filters
        self.domain = self._get_domain()
        html = self._fetch_html(self.domain + "/")
        result["list"] = self._parse_video_list(html)
        return result

    def homeVideoContent(self):
        self.domain = self._get_domain()
        html = self._fetch_html(self.domain + "/")
        return {"list": self._parse_video_list(html)}

    def categoryContent(self, tid, pg, filter=False, extend=None):
        result = {"list": [], "page": 1, "pagecount": 1, "limit": 36, "total": 0}
        try:
            page = int(pg) if pg else 1
        except (ValueError, TypeError):
            page = 1
        result["page"] = page
        if extend is None:
            extend = {}
        if isinstance(extend, str):
            try:
                extend = json.loads(extend) if extend else {}
            except Exception:
                extend = {}
        sort = extend.get("sort", "") or ""
        quality = extend.get("quality", "") or ""
        duration = extend.get("duration", "") or ""
        url_path = tid
        if quality and tid.startswith("categories/"):
            parts = tid.split("/")
            if len(parts) == 2:
                url_path = tid + "/" + quality
        if sort and tid.startswith("categories/"):
            url_path = tid + "/" + sort
        self.domain = self._get_domain()
        if page > 1:
            url = self.domain + "/" + url_path + "/" + str(page)
        else:
            url = self.domain + "/" + url_path
        html = self._fetch_html(url)
        if html:
            videos = self._parse_video_list(html)
            if duration:
                try:
                    min_min, max_min = duration.split("-")
                    min_min = int(min_min)
                    max_min = int(max_min)
                    filtered = []
                    for v in videos:
                        remarks = v.get("vod_remarks", "")
                        if remarks:
                            p = remarks.split(":")
                            if len(p) == 2:
                                tm = int(p[0])
                            elif len(p) == 3:
                                tm = int(p[0]) * 60 + int(p[1])
                            else:
                                continue
                            if min_min <= tm <= max_min:
                                filtered.append(v)
                    videos = filtered
                except Exception:
                    pass
            result["list"] = videos
            result["pagecount"] = self._parse_page_count(html)
            result["total"] = result["pagecount"] * 36
        return result

    def detailContent(self, ids):
        result = {"list": []}
        try:
            vod_id = ids[0] if isinstance(ids, list) else ids
            self.domain = self._get_domain()
            url = f"{self.domain}/videos/{vod_id}"
            html = self._fetch_html(url)
            if html:
                title = self._parse_title(html) or vod_id
                pic = self._parse_thumbnail(html)
                m3u8_url = self._parse_m3u8(html)
                mp4_list = self._parse_mp4_list(html)
                play_from = []
                play_url = []
                if m3u8_url:
                    play_from.append("M3U8")
                    play_url.append(f"正片${m3u8_url}")
                for mp4 in mp4_list:
                    play_from.append("MP4")
                    play_url.append(f"MP4${mp4}")
                if not play_from:
                    play_from.append("播放")
                    play_url.append(f"正片${url}")
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
        try:
            page = int(pg) if pg else 1
            self.domain = self._get_domain()
            url = f"{self.domain}/search/{quote(key)}/?page={page}" if page > 1 else f"{self.domain}/search/{quote(key)}/"
            html = self._fetch_html(url)
            if html:
                result["list"] = self._parse_video_list(html)
                result["page"] = page
                result["pagecount"] = self._parse_page_count(html)
        except Exception:
            pass
        return result

    def playerContent(self, flag, id, vipFlags=None):
        if not id:
            return {"parse": 0, "url": "", "header": PLAYER_HEADERS}
        url = str(id)
        if "$" in url:
            url = url.split("$", 1)[-1]
        return {"parse": 0, "url": url, "header": PLAYER_HEADERS}

    def localProxy(self, param):
        return [404, 'text/plain', b'']

    def manualVideoCheck(self):
        return False