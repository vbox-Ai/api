#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
GetAV (iOS 专用) - vbox 远程源适配版
站点: getav.net / getav.me / getav.live / getav.co / getav.top (多主机)
导航: https://getav.info/zh/ 动态域名发现
适配: 继承 SpiderBase + super().init(extend) + localProxy三元组
     + 多主机并发竞速(首个成功响应的主机缓存10分钟) + 封面走本地代理
"""
import sys
sys.path.append('..')
import os
import re
import json
import base64
import hashlib
import html as html_lib
import urllib.request
import urllib.parse
import urllib.error
from urllib.parse import urlparse, quote, unquote
import http.cookiejar
import gzip
import zlib
import ssl
import time
import threading

try:
    from base.spider import Spider as SpiderBase
except ImportError:
    class SpiderBase(object):
        def __init__(self):
            self._vbox_effective_hosts = []
        def getCache(self, key): return None
        def setCache(self, key, value): return "fail"
        def delCache(self, key): return "fail"


def clean_html_text(raw_html):
    txt = re.sub(r'<[^>]+>', '', raw_html or '')
    txt = html_lib.unescape(txt)
    return re.sub(r'[\r\n\t\s]+', ' ', txt).strip()


def format_seconds(secs):
    try:
        s = int(secs)
        h = s // 3600
        m = (s % 3600) // 60
        sec = s % 60
        if h > 0:
            return "%02d:%02d:%02d" % (h, m, sec)
        return "%02d:%02d" % (m, sec)
    except Exception:
        return ""


def generate_color_card(text, is_ctrl=False):
    """无封面时生成 SVG 色卡 (data URI, 图片加载器可直接渲染)"""
    palette = [
        ("#4f46e5", "#7c3aed"),
        ("#2563eb", "#06b6d4"),
        ("#059669", "#10b981"),
        ("#d97706", "#f59e0b"),
        ("#dc2626", "#ea580c"),
        ("#db2777", "#f43f5e"),
        ("#475569", "#334155"),
        ("#0891b2", "#0284c7")
    ]
    name_str = (text or "GetAV").strip()
    if is_ctrl:
        c1, c2 = ("#e11d48", "#be123c")
    else:
        h_val = int(hashlib.md5(name_str.encode("utf-8")).hexdigest()[:4], 16)
        c1, c2 = palette[h_val % len(palette)]

    display_title = name_str[:12]
    font_size = "40" if len(display_title) <= 6 else ("32" if len(display_title) <= 9 else "26")

    svg = (
        '<svg xmlns="http://www.w3.org/2000/svg" width="640" height="360" viewBox="0 0 640 360">'
        '<defs>'
        '<linearGradient id="g" x1="0%%" y1="0%%" x2="100%%" y2="100%%">'
        '<stop offset="0%%" stop-color="%s"/>'
        '<stop offset="100%%" stop-color="%s"/>'
        '</linearGradient>'
        '</defs>'
        '<rect width="640" height="360" rx="24" fill="url(#g)"/>'
        '<text x="50%%" y="54%%" font-size="%s" font-family="sans-serif" font-weight="bold" '
        'fill="#ffffff" text-anchor="middle" dominant-baseline="middle">'
        '%s'
        '</text>'
        '</svg>'
    ) % (c1, c2, font_size, display_title)
    b64_svg = base64.b64encode(svg.encode("utf-8")).decode("utf-8")
    return "data:image/svg+xml;base64,%s" % b64_svg


class SmartRedirectHandler(urllib.request.HTTPRedirectHandler):
    def http_error_308(self, req, fp, code, msg, headers):
        infourl = urllib.response.addinfourl(fp, headers, req.get_full_url())
        infourl.status = code
        infourl.code = code
        return self.parent.open(req.get_header('Location', ''))


_API_TTL = 600  # 竞速胜者主机缓存 10 分钟


class Spider(SpiderBase):
    PLATFORM_KEY = "getav_py"

    def __init__(self):
        try:
            super(Spider, self).__init__()
        except Exception:
            pass
        self.navSite = "https://getav.info/zh/"
        # getav.live 已实测 200 + API + 封面/m3u8 均可达, 优先;
        # getav.me 实测 302 到 huangguo.wulii.de5.net(野果封面服务, 非GetAV) 放最后
        self.hosts = [
            "https://getav.live",
            "https://getav.net",
            "https://getav.co",
            "https://getav.top",
            "https://getav.me"
        ]
        self._host_idx = 0
        self.baseHost = self.hosts[0]
        self.staticHost = "https://static.worldstatic.com"
        self.tgGroup = "https://t.me/tvshare23"
        self.brandActor = "🦋 TG群: @tvshare23"
        self.brandDirector = "🦋 蝴蝶影视"
        self._ua = "Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Mobile/15E148 Safari/604.1"
        self.options = {}

        self.ctx = ssl.create_default_context()
        self.ctx.check_hostname = False
        self.ctx.verify_mode = ssl.CERT_NONE

        self.cj = http.cookiejar.CookieJar()
        self.opener = urllib.request.build_opener(
            urllib.request.HTTPCookieProcessor(self.cj),
            urllib.request.HTTPSHandler(context=self.ctx),
            SmartRedirectHandler()
        )

        # API 主机竞速缓存
        self._api_winner = None
        self._api_winner_ts = 0.0
        self._api_lock = threading.Lock()

    def init(self, extend=""):
        try:
            super().init(extend)
        except AttributeError:
            pass
        # vbox 注入主机池合并 (优先竞速候选)
        injected = getattr(self, "_vbox_effective_hosts", None) or []
        inj = [str(h).rstrip("/") for h in injected if str(h).startswith("http")]
        if inj:
            for h in reversed(inj):
                if h not in self.hosts:
                    self.hosts.insert(0, h)
        if isinstance(extend, dict):
            self.options = extend
        elif extend:
            try:
                self.options = json.loads(extend)
            except Exception:
                self.options = {}

        custom_host = self.options.get("host") or self.options.get("siteUrl")
        if custom_host:
            custom_host = str(custom_host).rstrip("/")
            if custom_host not in self.hosts:
                self.hosts.insert(0, custom_host)
            self.baseHost = custom_host
        else:
            cached_host = self.getCache("getav_live_host")
            if cached_host and str(cached_host).startswith("http"):
                if cached_host not in self.hosts:
                    self.hosts.insert(0, cached_host)
                self.baseHost = cached_host
            else:
                self._update_live_host()
        return True

    def getName(self):
        return "GetAV"

    def isVideoFormat(self, url):
        low = (url or "").lower()
        return any(k in low for k in (".m3u8", ".mp4", ".flv", ".mkv", ".avi", ".ts", ".mpd", "index.png", "index.txt"))

    def manualVideoCheck(self):
        return False

    # ================= 动态域名发现 =================
    def _update_live_host(self):
        try:
            req = urllib.request.Request(self.navSite, headers={
                "User-Agent": self._ua,
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8"
            })
            with self.opener.open(req, timeout=5) as resp:
                raw = resp.read()
                enc = getattr(resp, "headers", {}).get("Content-Encoding", "")
                if raw.startswith(b"\x1f\x8b") or enc == "gzip":
                    raw = gzip.decompress(raw)
                html = raw.decode("utf-8", errors="ignore")

                domains = re.findall(r'getav\.(?:net|me|live|co|top|[a-z0-9]+)', html, re.I)
                clean_hosts = []
                for d in domains:
                    h = ("https://%s" % d.lower()).strip()
                    if "info" not in h and h not in clean_hosts:
                        clean_hosts.append(h)

                if clean_hosts:
                    for ch in reversed(clean_hosts):
                        if ch not in self.hosts:
                            self.hosts.insert(0, ch)
                    self.baseHost = self.hosts[0]
                    self._host_idx = 0
                    self.setCache("getav_live_host", self.baseHost)
                    return True
        except Exception:
            pass
        return False

    # ================= 多主机并发竞速 =================
    def _try_host(self, host, api_path, timeout=10):
        """单主机单次尝试, 返回 JSON 或 None"""
        if api_path.startswith("http"):
            url = re.sub(r"^https?://[^/]+", host, api_path)
        else:
            url = host + ("/" + api_path.lstrip("/"))

        headers = {
            "User-Agent": self._ua,
            "Accept": "application/json, text/plain, */*",
            "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
            "Accept-Encoding": "gzip, deflate",
            "Connection": "keep-alive",
            "Referer": host + "/zh",
            "Origin": host,
        }
        try:
            req = urllib.request.Request(url, headers=headers)
            with self.opener.open(req, timeout=timeout) as resp:
                raw = resp.read()
                enc = getattr(resp, "headers", {}).get("Content-Encoding", "")
                if raw.startswith(b"\x1f\x8b") or enc == "gzip":
                    raw = gzip.decompress(raw)
                elif enc == "deflate":
                    try:
                        raw = zlib.decompress(raw)
                    except Exception:
                        raw = zlib.decompress(raw, -zlib.MAX_WBITS)
                data = json.loads(raw.decode("utf-8", errors="ignore"))
                if data:
                    return data
        except Exception:
            pass
        return None

    def _fetch_api(self, api_path, timeout=10):
        """API 请求: 竞速胜者直接命中; 失效则全主机并发竞速 (首个响应缓存10分钟)"""
        now = time.time()
        if self._api_winner and (now - self._api_winner_ts) < _API_TTL:
            w = self._api_winner
            data = self._try_host(w, api_path, timeout)
            if data:
                return data
            self._api_winner = None  # 胜者失效, 转全量竞速

        winner = {}
        lock = threading.Lock()

        def _race(host):
            if winner.get("data"):
                return
            data = self._try_host(host, api_path, timeout)
            if data:
                with lock:
                    if not winner.get("data"):
                        winner["data"] = data
                        winner["host"] = host

        # 当前主机优先, 其余并发
        current = self.hosts[self._host_idx] if self._host_idx < len(self.hosts) else self.hosts[0]
        ordered = [current] + [h for h in self.hosts if h != current]
        threads = [threading.Thread(target=_race, args=(h,), daemon=True) for h in ordered]
        for t in threads:
            t.start()
        deadline = time.time() + 12
        while time.time() < deadline:
            with lock:
                if winner.get("data"):
                    break
            time.sleep(0.2)

        if winner.get("data"):
            self.baseHost = winner["host"]
            if winner["host"] in self.hosts:
                self._host_idx = self.hosts.index(winner["host"])
            self._api_winner = winner["host"]
            self._api_winner_ts = time.time()
            return winner["data"]

        # 全失败: 动态发现新主机后二次竞速
        if self._update_live_host():
            winner2 = {}
            lock2 = threading.Lock()

            def _race2(host):
                if winner2.get("data"):
                    return
                data = self._try_host(host, api_path, timeout)
                if data:
                    with lock2:
                        if not winner2.get("data"):
                            winner2["data"] = data
                            winner2["host"] = host

            threads2 = [threading.Thread(target=_race2, args=(h,), daemon=True) for h in self.hosts]
            for t in threads2:
                t.start()
            deadline2 = time.time() + 12
            while time.time() < deadline2:
                with lock2:
                    if winner2.get("data"):
                        break
                time.sleep(0.2)
            if winner2.get("data"):
                self.baseHost = winner2["host"]
                if winner2["host"] in self.hosts:
                    self._host_idx = self.hosts.index(winner2["host"])
                self._api_winner = winner2["host"]
                self._api_winner_ts = time.time()
                return winner2["data"]
        return {}

    # ================= 本地代理 =================
    def _proxy_base(self):
        fn = getattr(self, "getProxyUrl", None)
        if callable(fn):
            try:
                u = fn(True)
                if u:
                    return str(u)
            except Exception:
                pass
        return "http://127.0.0.1:18080/proxy?do=py&key=%s" % self.PLATFORM_KEY

    def _proxy_img_url(self, url, referer=None):
        if not url:
            return ""
        base = self._proxy_base()
        sep = "&" if "?" in base else "?"
        u = base + sep + "type=img&u=" + quote(str(url), safe="")
        if referer:
            u += "&r=" + quote(referer, safe="")
        return u

    def _serve_img(self, url, referer=None):
        # 多候选主机回退: 主URL取图失败后, 依次试 static CDN + 各 API 主机的同一路径, 抗单点不可达
        cands = [url]
        try:
            p = urlparse(url).path
            if p:
                for base in [self.staticHost, self.baseHost] + list(getattr(self, "hosts", []) or []):
                    if not base:
                        continue
                    cand = base + p
                    if cand not in cands:
                        cands.append(cand)
                    if len(cands) >= 5:
                        break
        except Exception:
            pass
        last = [502, "text/plain", b"proxy fetch failed"]
        for u in cands:
            try:
                headers = {"User-Agent": self._ua}
                if referer:
                    headers["Referer"] = referer
                    headers["Origin"] = referer.rstrip("/")
                req = urllib.request.Request(u, headers=headers)
                with self.opener.open(req, timeout=15) as resp:
                    raw = resp.read()
                    ct = (resp.headers.get("Content-Type") or "image/jpeg").split(";")[0].strip()
                if raw[:4] == b"\x89PNG":
                    ct = "image/png"
                elif raw[:3] == b"GIF":
                    ct = "image/gif"
                elif raw[:2] == b"\xff\xd8":
                    ct = "image/jpeg"
                elif raw[:4] == b"RIFF":
                    ct = "image/webp"
                elif raw[:4] == b"\x00\x01\x00\x00":
                    ct = "image/avif"
                return [200, ct, raw]
            except Exception:
                continue
        return last

    def _format_poster(self, raw_url):
        """封面图: 相对路径优先拼已证明可达的 API 主机(baseHost, 竞速胜者), 绝对URL直用; 包本地代理URL
        baseHost 是刚响应过 API 的主机, 供图可达性最高; static CDN 作为 _serve_img 的回退候选"""
        if not raw_url:
            return ""
        pic = raw_url.strip()
        if pic.startswith("//"):
            pic = "https:" + pic
        elif pic.startswith("/"):
            pic = (self.baseHost or self.staticHost) + pic
        referer_url = (self.baseHost or self.staticHost) + "/"
        return self._proxy_img_url(pic, referer=referer_url)

    # ================= 标准接口 =================
    def homeContent(self, filter):
        classes = [
            {"type_name": "🔥 最近更新", "type_id": "api@@latest"},
            {"type_name": "📈 热门影片", "type_id": "api@@hot"},
            {"type_name": "✨ 新片上市", "type_id": "api@@new-releases"},
            {"type_name": "🔞 无码影片", "type_id": "api@@uncensored"},
            {"type_name": "🈵 有码影片", "type_id": "api@@censored"},
            {"type_name": "🔤 字幕专区", "type_id": "api@@subtitle"},
            {"type_name": "💎 4K 超高清", "type_id": "api@@4k"},
            {"type_name": "📂 类型大全", "type_id": "folder@@genres"},
            {"type_name": "📂 演员大全", "type_id": "folder@@stars"},
            {"type_name": "📂 片商大全", "type_id": "folder@@studios"},
            {"type_name": "📂 番号系列", "type_id": "folder@@codes"}
        ]
        if not classes:
            classes = [{"type_name": "GetAV·全部", "type_id": "api@@latest"}]

        video_filters = [
            {
                "key": "sortBy",
                "name": "排序",
                "value": [
                    {"n": "最新", "v": "latest"},
                    {"n": "最热", "v": "popular"},
                    {"n": "评分", "v": "rating"},
                    {"n": "时长", "v": "duration"}
                ]
            },
            {
                "key": "subtitles",
                "name": "字幕",
                "value": [
                    {"n": "全部", "v": ""},
                    {"n": "中文字幕", "v": "true"}
                ]
            },
            {
                "key": "resolution",
                "name": "画质",
                "value": [
                    {"n": "全部", "v": ""},
                    {"n": "4K超高清", "v": "4k"}
                ]
            }
        ]

        folder_sort_filters = [
            {
                "key": "sort",
                "name": "排序",
                "value": [
                    {"n": "最热", "v": "popular"},
                    {"n": "名称", "v": "name"},
                    {"n": "数量", "v": "movies"}
                ]
            }
        ]

        filters = {
            "api@@latest": video_filters,
            "api@@hot": video_filters,
            "api@@new-releases": video_filters,
            "api@@uncensored": video_filters,
            "api@@censored": video_filters,
            "api@@subtitle": video_filters,
            "api@@4k": video_filters,
            "folder@@genres": folder_sort_filters,
            "folder@@studios": folder_sort_filters,
            "folder@@codes": folder_sort_filters,
            "folder@@stars": [
                {
                    "key": "gender",
                    "name": "性别",
                    "value": [
                        {"n": "女优", "v": "2"},
                        {"n": "男优", "v": "1"}
                    ]
                },
                {
                    "key": "sort",
                    "name": "排序",
                    "value": [
                        {"n": "最热", "v": "popular"},
                        {"n": "最新", "v": "latest"},
                        {"n": "数量", "v": "movies"},
                        {"n": "名称", "v": "name"}
                    ]
                }
            ]
        }
        return {"class": classes, "filters": filters}

    def homeVideoContent(self):
        res = self._fetch_api("/api/movies?category=latest&sortBy=latest&limit=20&page=1&locale=zh")
        movies = (res.get("data") or {}).get("movies") or []
        v_list = []
        for m in movies:
            cid = str(m.get("id", "")).strip().lower()
            if not cid or cid.isdigit():
                continue
            dur = format_seconds(m.get("videoLength", 0))
            v_list.append({
                "vod_id": cid,
                "vod_name": m.get("title") or cid.upper(),
                "vod_pic": self._format_poster(m.get("localImg") or m.get("img")),
                "vod_remarks": "蝴蝶影视 | %s" % dur if dur else "蝴蝶影视",
                "style": {"type": "rect", "ratio": 1.42}
            })
        return {"list": v_list}

    def _movies_to_vods(self, movies, page, extra_note=None):
        v_list = []
        for m in movies:
            cid = str(m.get("id", "")).strip().lower()
            if not cid or cid.isdigit():
                continue
            dur = format_seconds(m.get("videoLength", 0))
            pic = self._format_poster(m.get("localImg") or m.get("img"))
            if not pic:
                pic = generate_color_card((m.get("title") or cid.upper())[:12])
            v_list.append({
                "vod_id": cid,
                "vod_name": m.get("title") or cid.upper(),
                "vod_pic": pic,
                "vod_remarks": "蝴蝶影视 | %s" % dur if dur else "蝴蝶影视",
                "style": {"type": "rect", "ratio": 1.42}
            })
        return v_list

    def categoryContent(self, tid, pg, filter, extend):
        page = int(pg) if str(pg).isdigit() else 1
        extend = extend or {}

        if str(tid).startswith("folder@@"):
            f_type = tid.replace("folder@@", "")

            if f_type == "stars":
                gender = extend.get("gender", "2")
                sort_type = extend.get("sort", "popular")

                query_parts = [
                    "page=%d" % page,
                    "limit=24",
                    "sort=%s" % sort_type,
                    "locale=zh"
                ]
                if gender:
                    query_parts.append("gender=%s" % gender)

                api_url = "/api/stars?" + "&".join(query_parts)
                res = self._fetch_api(api_url)
                data_obj = res.get("data") or {}
                stars = data_obj.get("stars") or (res.get("data") if isinstance(res.get("data"), list) else [])
                v_list = []
                for s in stars:
                    s_id = str(s.get("id", "")).strip()
                    base_name = s.get("name") or s.get("originalName") or s.get("nameJp") or ""
                    if not base_name:
                        continue
                    count = s.get("movieCount") or s.get("movie_count") or ""
                    display_name = "%s (%s部)" % (base_name, count) if count else base_name
                    remarks = "蝴蝶影视 | %s部" % count if count else "蝴蝶影视"

                    raw_avatar = s.get("localAvatar") or s.get("avatar") or s.get("localImg") or s.get("img")
                    avatar = self._format_poster(raw_avatar) if raw_avatar else generate_color_card(base_name)

                    v_list.append({
                        "vod_id": "subfolder@@star@@%s@@sortBy=popular@@subtitles=@@resolution=@@name=%s" % (s_id, quote(base_name)),
                        "vod_name": display_name,
                        "vod_pic": avatar,
                        "vod_remarks": remarks,
                        "vod_tag": "folder",
                        "style": {"type": "rect", "ratio": 1.78}
                    })
                total_pages = (res.get("data") or {}).get("pagination", {}).get("totalPages", page + 1 if len(v_list) >= 24 else page)
                return {
                    "page": page,
                    "pagecount": total_pages,
                    "limit": len(v_list),
                    "total": 5487,
                    "list": v_list
                }

            elif f_type == "genres":
                sort_type = extend.get("sort", "popular")
                api_url = "/api/genres?limit=100&sort=%s&locale=zh-CN" % sort_type
                res = self._fetch_api(api_url)
                items = (res.get("data") or {}).get("genres") or []
                v_list = []
                for g in items:
                    g_id = str(g.get("id", ""))
                    name = g.get("name") or g.get("originalName", "")
                    count = g.get("movieCount", "")
                    remarks = "蝴蝶影视 | %s部" % count if count else "蝴蝶影视"
                    v_list.append({
                        "vod_id": "subfolder@@genre@@%s@@sortBy=latest@@subtitles=@@resolution=@@name=%s" % (g_id, quote(name)),
                        "vod_name": name,
                        "vod_pic": generate_color_card(name),
                        "vod_remarks": remarks,
                        "vod_tag": "folder",
                        "style": {"type": "rect", "ratio": 1.78}
                    })
                return {"page": 1, "pagecount": 1, "limit": len(v_list), "total": len(v_list), "list": v_list}

            elif f_type == "studios":
                sort_type = extend.get("sort", "popular")
                api_url = "/api/studios?limit=100&sort=%s&locale=zh-CN" % sort_type
                res = self._fetch_api(api_url)
                studios = (res.get("data") or {}).get("studios") or []
                v_list = []
                for st in studios:
                    st_id = str(st.get("id", ""))
                    name = st.get("name", "")
                    count = st.get("movieCount") or st.get("movie_count") or ""
                    remarks = "蝴蝶影视 | %s部" % count if count else "蝴蝶影视"
                    v_list.append({
                        "vod_id": "subfolder@@studio@@%s@@sortBy=latest@@subtitles=@@resolution=@@name=%s" % (st_id, quote(name)),
                        "vod_name": name,
                        "vod_pic": generate_color_card(name),
                        "vod_remarks": remarks,
                        "vod_tag": "folder",
                        "style": {"type": "rect", "ratio": 1.78}
                    })
                return {"page": 1, "pagecount": 1, "limit": len(v_list), "total": len(v_list), "list": v_list}

            elif f_type == "codes":
                sort_type = extend.get("sort", "popular")
                api_url = "/api/codes?limit=100&sort=%s&locale=zh-CN" % sort_type
                res = self._fetch_api(api_url)
                codes = (res.get("data") or {}).get("codes") or []
                v_list = []
                for cd in codes:
                    cd_code = str(cd.get("code") or cd.get("name", "")).strip().upper()
                    count = cd.get("movieCount") or cd.get("movie_count") or ""
                    remarks = "蝴蝶影视 | %s部" % count if count else "蝴蝶影视"
                    v_list.append({
                        "vod_id": "subfolder@@code@@%s@@sortBy=latest@@subtitles=@@resolution=@@name=%s" % (cd_code, quote(cd_code)),
                        "vod_name": cd_code,
                        "vod_pic": generate_color_card(cd_code),
                        "vod_remarks": remarks,
                        "vod_tag": "folder",
                        "style": {"type": "rect", "ratio": 1.78}
                    })
                return {"page": 1, "pagecount": 1, "limit": len(v_list), "total": len(v_list), "list": v_list}

        if str(tid).startswith("subfolder@@"):
            parts = str(tid).split("@@")
            sub_type = parts[1]
            target_id = parts[2]

            p_dict = {
                "sortBy": "popular" if sub_type == "star" else "latest",
                "subtitles": "",
                "resolution": "",
                "name": target_id
            }
            for p in parts[3:]:
                if "=" in p:
                    k, v = p.split("=", 1)
                    p_dict[k] = unquote(v)

            curr_sort = p_dict["sortBy"]
            curr_sub = p_dict["subtitles"]
            curr_res = p_dict["resolution"]
            sub_name = p_dict["name"]

            api_params = [
                "page=%d" % page,
                "limit=20",
                "locale=zh",
                "sortBy=%s" % curr_sort
            ]
            if curr_sub == "true":
                api_params.append("subtitles=true")
            if curr_res == "4k":
                api_params.append("resolution=4k")

            if sub_type == "star":
                api_params.append("starId=%s" % target_id)
            elif sub_type == "genre":
                api_params.append("genreId=%s" % target_id)
            elif sub_type == "studio":
                api_params.append("studioId=%s" % target_id)
            elif sub_type == "code":
                api_params.append("code=%s" % quote(target_id))

            api_url = "/api/movies?" + "&".join(api_params)
            res = self._fetch_api(api_url)
            data_obj = res.get("data") or {}
            movies = data_obj.get("movies") or []

            v_list = []

            if page == 1:
                sort_next_map = {
                    "popular": ("latest", "最热", "最新"),
                    "latest": ("duration", "最新", "时长"),
                    "duration": ("popular", "时长", "最热")
                }
                next_sort, cur_s_n, next_s_n = sort_next_map.get(curr_sort, ("popular", curr_sort, "最热"))
                sort_tid = "subfolder@@%s@@%s@@sortBy=%s@@subtitles=%s@@resolution=%s@@name=%s" % (
                    sub_type, target_id, next_sort, curr_sub, curr_res, quote(sub_name)
                )
                v_list.append({
                    "vod_id": sort_tid,
                    "vod_name": "🔀 排序: %s (点击切换)" % cur_s_n,
                    "vod_pic": generate_color_card("排序:%s" % cur_s_n, is_ctrl=True),
                    "vod_remarks": "切至 %s" % next_s_n,
                    "vod_tag": "folder",
                    "style": {"type": "rect", "ratio": 1.42}
                })

                next_sub = "" if curr_sub == "true" else "true"
                cur_sub_n = "中文字幕" if curr_sub == "true" else "全部版本"
                next_sub_n = "全部版本" if curr_sub == "true" else "中文字幕"
                sub_tid = "subfolder@@%s@@%s@@sortBy=%s@@subtitles=%s@@resolution=%s@@name=%s" % (
                    sub_type, target_id, curr_sort, next_sub, curr_res, quote(sub_name)
                )
                v_list.append({
                    "vod_id": sub_tid,
                    "vod_name": "🔤 字幕: %s" % cur_sub_n,
                    "vod_pic": generate_color_card("%s" % cur_sub_n, is_ctrl=True),
                    "vod_remarks": "切至 %s" % next_sub_n,
                    "vod_tag": "folder",
                    "style": {"type": "rect", "ratio": 1.42}
                })

                next_res = "" if curr_res == "4k" else "4k"
                cur_res_n = "4K超清" if curr_res == "4k" else "全部画质"
                next_res_n = "全部画质" if curr_res == "4k" else "4K超清"
                res_tid = "subfolder@@%s@@%s@@sortBy=%s@@subtitles=%s@@resolution=%s@@name=%s" % (
                    sub_type, target_id, curr_sort, curr_sub, next_res, quote(sub_name)
                )
                v_list.append({
                    "vod_id": res_tid,
                    "vod_name": "💎 画质: %s" % cur_res_n,
                    "vod_pic": generate_color_card("%s" % cur_res_n, is_ctrl=True),
                    "vod_remarks": "切至 %s" % next_res_n,
                    "vod_tag": "folder",
                    "style": {"type": "rect", "ratio": 1.42}
                })

            for m in movies:
                v_list.extend(self._movies_to_vods([m], page))

            total_pages = (data_obj.get("pagination") or {}).get("totalPages", page + 1 if len(movies) >= 20 else page)
            return {
                "page": page,
                "pagecount": total_pages,
                "limit": len(v_list),
                "total": 9999,
                "list": v_list
            }

        params = [
            "page=%d" % page,
            "limit=20",
            "locale=zh"
        ]

        sort_val = extend.get("sortBy", "latest")
        params.append("sortBy=%s" % sort_val)

        if extend.get("subtitles") == "true":
            params.append("subtitles=true")
        if extend.get("resolution") == "4k":
            params.append("resolution=4k")

        query_tail = "&".join(params)
        cat = tid.replace("api@@", "") if str(tid).startswith("api@@") else "latest"
        api_query = "/api/movies?category=%s&%s" % (cat, query_tail)

        res = self._fetch_api(api_query)
        data_obj = res.get("data") or {}
        movies = data_obj.get("movies") or []
        v_list = self._movies_to_vods(movies, page)

        total_pages = (data_obj.get("pagination") or {}).get("totalPages", page + 1 if len(v_list) >= 20 else page)
        return {
            "page": page,
            "pagecount": total_pages,
            "limit": len(v_list),
            "total": 9999,
            "list": v_list
        }

    def detailContent(self, ids):
        raw_id = ids[0] if isinstance(ids, (list, tuple)) else str(ids)

        if str(raw_id).startswith("subfolder@@"):
            return self.categoryContent(raw_id, 1, None, None)

        code = str(raw_id).strip().lower()
        res = self._fetch_api("/api/movies/%s" % code)
        data = res.get("data") or {}

        title = data.get("title", code.upper())
        poster = self._format_poster(data.get("localImg") or data.get("img"))

        actors_list = data.get("stars") or []
        actor_names = [clean_html_text(a.get("name", "")) for a in actors_list if a.get("name")]
        actor_str = ", ".join(actor_names) if actor_names else self.brandActor

        genres_list = data.get("genres") or []
        genre_names = [clean_html_text(g.get("name", "")) for g in genres_list if g.get("name")]
        type_str = " / ".join(genre_names) if genre_names else "情色"

        dur_str = format_seconds(data.get("videoLength", 0))
        remarks = "蝴蝶影视 | %s" % dur_str if dur_str else "蝴蝶影视"

        desc = data.get("description") or title
        full_content = (
            "【🔥 官方交流群: %s】\n"
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            "番号: %s\n"
            "片名: %s\n"
            "时长: %s\n"
            "发行: %s\n"
            "简介: %s"
        ) % (self.tgGroup, code.upper(), title, dur_str, str(data.get("date", ""))[:10], desc)

        video_sources = data.get("videoSources") or []
        label_map = {
            "raw_1080p": "正片 1080P", "raw_720p": "高清 720P",
            "raw_480p": "标清 480P", "raw_240p": "流畅 240P",
            "uc_1080p": "无码 1080P", "uc_720p": "无码 720P",
            "uc_480p": "无码 480P", "uc_240p": "无码 240P"
        }
        q_rank = {"1080p": 4, "720p": 3, "480p": 2, "240p": 1}

        def _rank(v):
            t = str(v.get("type", ""))
            for k in ("uc_", "raw_"):
                if t.startswith(k):
                    return q_rank.get(t[3:], 0)
            return 0

        play_lines = []
        for vs in sorted(video_sources, key=_rank, reverse=True):
            s_url = vs.get("url", "")
            if s_url:
                t_label = label_map.get(vs.get("type", ""), vs.get("type", "") or "默认线路")
                play_lines.append("%s$%s" % (t_label, s_url))

        if not play_lines:
            if data.get("localM3u8Path4k"):
                play_lines.append("超清 4K$%s" % data["localM3u8Path4k"])
            if data.get("localM3u8Path"):
                play_lines.append("高清 1080P$%s" % data["localM3u8Path"])
            if data.get("localM3u8PathUc"):
                play_lines.append("无码专线$%s" % data["localM3u8PathUc"])

        preview_url = data.get("previewVideoUrl")
        if preview_url:
            full_preview = self.staticHost + preview_url if not preview_url.startswith("http") else preview_url
            play_lines.append("精彩预告$%s" % full_preview)

        play_url_str = "#".join(play_lines) if play_lines else "暂无可用线路$https://dummyimage.com/1x1/000/000.png"

        vod_detail = {
            "vod_id": code,
            "vod_name": title,
            "vod_pic": poster,
            "type_name": type_str,
            "vod_year": str(data.get("date", ""))[:4],
            "vod_area": "日本",
            "vod_remarks": remarks,
            "vod_actor": actor_str,
            "vod_director": self.brandDirector,
            "vod_content": full_content.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;"),
            "vod_play_from": "蝴蝶影视专线",
            "vod_play_url": play_url_str
        }

        return {"list": [vod_detail]}

    def playerContent(self, flag, id, vipFlags):
        play_url = str(id).strip()

        # 为无扩展名的直链注入伪 .m3u8 扩展名, 强制激活 AVPlayer 原生硬解调度
        if ".m3u8" not in play_url.lower():
            sep = "&" if "?" in play_url else "?"
            play_url = play_url + sep + "format=.m3u8"

        referer = (self.baseHost or self.staticHost) + "/"
        return {
            "parse": 0,
            "jx": 0,
            "url": play_url,
            "header": {
                "User-Agent": self._ua,
                "Referer": referer,
                "Origin": (self.baseHost or self.staticHost)
            }
        }

    def searchContent(self, key, quick, pg="1"):
        page = int(pg) if str(pg).isdigit() else 1
        kw = quote(key.strip())
        api_url = "/api/movies?q=%s&sortBy=latest&limit=20&page=%d&locale=zh" % (kw, page)

        res = self._fetch_api(api_url)
        data_obj = res.get("data") or {}
        movies = data_obj.get("movies") or []
        v_list = self._movies_to_vods(movies, page)

        total_pages = (data_obj.get("pagination") or {}).get("totalPages", page + 1 if len(v_list) >= 20 else page)
        return {
            "page": page,
            "pagecount": total_pages,
            "limit": len(v_list),
            "total": 9999,
            "list": v_list
        }

    def action(self, action):
        return {"msg": "ok"}

    def liveContent(self):
        return ""

    def localProxy(self, params):
        p = {}
        if isinstance(params, dict):
            p = params
        elif isinstance(params, str):
            s = params.strip()
            if s.startswith("{"):
                try:
                    p = json.loads(s)
                except Exception:
                    p = {}
            elif "=" in s:
                try:
                    qs = urllib.parse.parse_qs(s.lstrip("?"))
                    p = {k: v[0] for k, v in qs.items()}
                except Exception:
                    p = {}
        t = str(p.get("type") or "")
        u = unquote(str(p.get("u") or p.get("url") or ""))
        r = unquote(str(p.get("r") or "")) or None
        if t == "img" and u:
            return self._serve_img(u, referer=r)
        return [404, "text/plain", b""]

    def destroy(self):
        self.options = {}
        self._api_winner = None
        try:
            self.cj.clear()
        except Exception:
            pass
