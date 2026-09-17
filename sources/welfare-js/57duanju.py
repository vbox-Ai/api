#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# 57短剧/57吃瓜 vbox 适配版 (V4.2 域名池并发探测)
# 基于蜂蜜影视 FongMi V4.1，vbox 适配改动：
#   1. 双固定域名 → 域名池并发探测（ThreadPoolExecutor，谁先成功用谁，10 分钟缓存）
#   2. 反诈劫持页识别（国家反诈中心/联合提醒 特征）→ 视为失败并踢出缓存
#   3. 统一路由：全部分类走域名池（cg 站即全功能站，实测 aichengduanju/hot 也在 cg 站）
#   4. 补 getDependence()；parse 返回值统一字符串 '0'
#   5. 零外部依赖（纯 urllib 标准库）

import sys
import os
import re
import json
import time
import base64
import html as html_lib
import urllib.request
import urllib.parse
from urllib.parse import urlparse, quote, unquote
import http.cookiejar
import gzip
import zlib
import ssl
from concurrent.futures import ThreadPoolExecutor, as_completed

try:
    from base.spider import Spider as SpiderBase
except ImportError:
    class SpiderBase(object):
        def getCache(self, key): return None
        def setCache(self, key, value): return "fail"
        def delCache(self, key): return "fail"

# 域名池：实测存活域名放前面（冷启动提速），被劫持的放后面兜底
DOMAINS = [
    "https://57cg1.com",
    "https://57cg2.com",
    "https://57cg5.com",
    "https://57cg6.com",
    "https://d2tu7000ico5j0.cloudfront.net",
    "https://57cg4.com",
    "https://57cg3.com",
    "https://57duanju.org",
]

# 反诈劫持页特征（命中即视为域名死亡）
HIJACK_MARKERS = ("国家反诈中心", "联合提醒", "反诈中心")

# 域名探测缓存 TTL（秒）
SITE_CACHE_TTL = 600

# 模块级域名缓存（跨实例共享）
_domain_cache = {"base": None, "ts": 0}


class Spider(SpiderBase):
    def __init__(self):
        super(Spider, self).__init__()
        self.siteUrl = DOMAINS[0]
        self.cgUrl = DOMAINS[0]
        self.imgReferer = DOMAINS[0] + "/"
        self.tgGroup = "https://t.me/tvshare23"
        self.brandActor = "🦋 TG群: @tvshare23"
        self.brandDirector = "🦋 蝴蝶影视"
        self._ua = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36"
        self.options = {}

        self.ctx = ssl.create_default_context()
        self.ctx.check_hostname = False
        self.ctx.verify_mode = ssl.CERT_NONE

        self.cj = http.cookiejar.CookieJar()
        self.opener = urllib.request.build_opener(
            urllib.request.HTTPCookieProcessor(self.cj),
            urllib.request.HTTPSHandler(context=self.ctx)
        )

    def init(self, extend=""):
        if isinstance(extend, dict):
            self.options = extend
        elif extend:
            try:
                self.options = json.loads(extend)
            except Exception:
                self.options = {}
        return True

    def getName(self):
        return "57短剧"

    def getDependence(self):
        return []

    def isVideoFormat(self, url):
        low = (url or "").lower()
        return any(k in low for k in (".m3u8", ".mp4", ".flv", ".mkv", ".ts"))

    def manualVideoCheck(self):
        return False

    # ============================================================
    # 域名池：并发探测 + 10 分钟缓存 + 劫持页识别
    # ============================================================
    @staticmethod
    def _is_hijack(text):
        if not text:
            return False
        return any(m in text for m in HIJACK_MARKERS)

    def _probe_domain(self, domain):
        """探测单个域名，成功返回 domain，失败/劫持返回 None"""
        try:
            req = urllib.request.Request(domain + "/", headers={"User-Agent": self._ua})
            with self.opener.open(req, timeout=6) as resp:
                if resp.getcode() != 200:
                    return None
                raw = resp.read(65536)
                if raw.startswith(b"\x1f\x8b"):
                    raw = gzip.decompress(raw)
                text = raw.decode("utf-8", errors="ignore")
                if self._is_hijack(text):
                    return None
                if "<title>" in text and "57" in text:
                    return domain
                return None
        except Exception:
            return None

    def _get_base(self, force_refresh=False):
        """返回当前最快可用域名，10 分钟内走缓存"""
        global _domain_cache
        now = time.time()
        if not force_refresh and _domain_cache["base"] \
                and (now - _domain_cache["ts"]) < SITE_CACHE_TTL:
            return _domain_cache["base"]

        # 并发探测全部域名，谁先成功用谁
        with ThreadPoolExecutor(max_workers=len(DOMAINS)) as pool:
            futures = {pool.submit(self._probe_domain, d): d for d in DOMAINS}
            for fut in as_completed(futures):
                result = fut.result()
                if result:
                    _domain_cache["base"] = result
                    _domain_cache["ts"] = now
                    return result

        # 全部失败：保留旧缓存兜底（可能只是网络抖动）
        if _domain_cache["base"]:
            _domain_cache["ts"] = now - SITE_CACHE_TTL + 60  # 1 分钟后重试
            return _domain_cache["base"]
        return DOMAINS[0]

    def _invalidate_base(self):
        global _domain_cache
        _domain_cache["base"] = None
        _domain_cache["ts"] = 0

    # ============================================================
    # 网络层：重试 + gzip + 劫持识别
    # ============================================================
    def _fetch(self, target_url, referer=""):
        if not target_url:
            return {"code": 0, "text": "", "bytes": b"", "err": "", "final_url": ""}
        if target_url.startswith("//"):
            target_url = "https:" + target_url
        elif target_url.startswith("/"):
            target_url = self._get_base() + target_url

        headers = {
            "User-Agent": self._ua,
            "Referer": referer if referer else self._get_base() + "/",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
            "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
            "Accept-Encoding": "gzip, deflate",
            "Connection": "keep-alive"
        }

        for attempt in range(2):
            try:
                req = urllib.request.Request(target_url, headers=headers)
                with self.opener.open(req, timeout=12) as resp:
                    code = resp.getcode()
                    final_url = resp.geturl()
                    raw = resp.read()
                    enc = getattr(resp, "headers", {}).get("Content-Encoding", "")
                    if raw.startswith(b"\x1f\x8b") or enc == "gzip":
                        raw = gzip.decompress(raw)
                    elif enc == "deflate":
                        try:
                            raw = zlib.decompress(raw)
                        except Exception:
                            raw = zlib.decompress(raw, -zlib.MAX_WBITS)
                    try:
                        text = raw.decode("utf-8")
                    except Exception:
                        text = raw.decode("latin1", errors="ignore")

                    # 劫持页识别：踢出缓存，本次请求判失败
                    if code == 200 and self._is_hijack(text):
                        self._invalidate_base()
                        return {"code": 451, "text": "", "bytes": b"",
                                "err": "hijacked", "final_url": final_url}

                    return {"code": code, "text": text, "bytes": raw, "err": "", "final_url": final_url}
            except Exception as e:
                if attempt == 0:
                    continue
                return {"code": -1, "text": "", "bytes": b"", "err": str(e), "final_url": target_url}

        return {"code": -1, "text": "", "bytes": b"", "err": "timeout", "final_url": target_url}

    def _fetch_with_failover(self, path, referer=""):
        """请求失败/劫持时：踢出缓存重新探测域名，再试一次"""
        res = self._fetch(path, referer=referer)
        if res.get("code") == 200 and res.get("text"):
            return res
        self._invalidate_base()
        return self._fetch(path, referer=referer)

    def _wrap_pic(self, pic_url):
        if not pic_url:
            return ""
        if pic_url.startswith("//"):
            pic_url = "https:" + pic_url
        elif pic_url.startswith("/"):
            pic_url = self._get_base() + pic_url

        if "s.chigua.media" in pic_url and "@" not in pic_url:
            return "%s@Referer=%s@User-Agent=%s" % (pic_url, self._get_base() + "/", quote(self._ua))
        return pic_url

    def homeContent(self, filter):
        classes = [
            {"type_name": "成人AI短剧", "type_id": "cat_aichengduanju"},
            {"type_name": "热门精选", "type_id": "cat_hot"},
            {"type_name": "今日吃瓜", "type_id": "cat_jrcg"},
            {"type_name": "每日大赛", "type_id": "cat_mrds"},
            {"type_name": "网红黑料", "type_id": "cat_wanghong"},
            {"type_name": "网黄合集", "type_id": "cat_video"},
            {"type_name": "出轨劈腿", "type_id": "cat_cheating"},
            {"type_name": "直播擦边", "type_id": "cat_live"},
            {"type_name": "社会事件", "type_id": "cat_society"},
            {"type_name": "明星八卦", "type_id": "cat_star"},
            {"type_name": "全部短剧", "type_id": "cat_all"}
        ]

        result = {"class": classes}

        if filter:
            sort_filter = [
                {
                    "key": "sort",
                    "name": "排序",
                    "value": [
                        {"n": "最新发布", "v": ""},
                        {"n": "全站最热", "v": "hot"},
                        {"n": "飙升热榜", "v": "trending"}
                    ]
                }
            ]
            filters_dict = {}
            for item in classes:
                filters_dict[item["type_id"]] = sort_filter
            result["filters"] = filters_dict

        return result

    def homeVideoContent(self):
        res = self.categoryContent("cat_aichengduanju", 1, False, {})
        return {"list": res.get("list", [])[:12]}

    def _parse_card_list(self, html_text):
        vod_list = []
        seen_ids = set()

        pattern_events = r'<a[^>]+href=["\'](?:https?://[^/]+)?/events/(\d+)/?["\'][^>]*>([\s\S]*?)</a>'
        matches = re.findall(pattern_events, html_text)

        if not matches:
            pattern_all = r'<a[^>]+href=["\'](?:https?://[^/]+)?/(?:events/)?(\d+)/?["\'][^>]*>([\s\S]*?)</a>'
            matches = re.findall(pattern_all, html_text)

        for event_id, inner in matches:
            if event_id in seen_ids or len(event_id) < 2:
                continue
            seen_ids.add(event_id)

            m_t = re.search(r'<h[23][^>]*>([\s\S]*?)</h[23]>', inner)
            if m_t:
                name = re.sub(r'<[^>]+>', '', m_t.group(1)).strip()
            else:
                raw_txt = re.sub(r'<[^>]+>', ' ', inner).strip()
                name = raw_txt[:40] if raw_txt else ("短剧/热点 %s" % event_id)

            pic = ""
            img_matches = re.findall(r'<img[^>]+src=["\']([^"\']+)["\']', inner)
            for src_cand in img_matches:
                if not src_cand.endswith(".svg") and "logo" not in src_cand:
                    pic = src_cand.strip()
                    break

            final_pic = self._wrap_pic(pic)

            vod_list.append({
                "vod_id": event_id,
                "vod_name": name,
                "vod_pic": final_pic,
                "vod_remarks": "蝴蝶影视",
                "style": {"type": "rect", "ratio": 1.78}
            })

        return vod_list

    def categoryContent(self, tid, pg, filter, extend):
        del filter
        page = int(pg) if pg else 1
        raw_slug = str(tid).strip("/")

        # 去除命名保护前缀
        slug = raw_slug.replace("cat_", "")
        sort_val = extend.get("sort") if isinstance(extend, dict) else ""

        # 统一路由：全部分类走域名池
        if slug == "all":
            target_url = "/page/%d/" % page if page > 1 else "/"
        else:
            target_url = "/%s/%d/" % (slug, page) if page > 1 else "/%s/" % slug

        if sort_val:
            target_url += ("&sort=%s" if "?" in target_url else "?sort=%s") % sort_val

        res = self._fetch_with_failover(target_url)
        html_text = res.get("text", "")
        vod_list = self._parse_card_list(html_text)

        return {
            "page": page,
            "pagecount": page + 1 if len(vod_list) >= 10 else page,
            "limit": len(vod_list),
            "total": 9999,
            "list": vod_list
        }

    def detailContent(self, ids):
        raw_id = ids[0] if isinstance(ids, (list, tuple)) else str(ids)
        event_id = raw_id.strip("/")

        target_url = "/events/%s/" % event_id
        res = self._fetch_with_failover(target_url)
        detail_html = res.get("text", "")

        title = "AI短剧/热点 %s" % event_id
        cover = ""
        desc = "暂无详细介绍"

        m_title = re.search(r'<h1[^>]*>([\s\S]*?)</h1>', detail_html)
        if m_title:
            title = re.sub(r'<[^>]+>', '', m_title.group(1)).strip()

        m_desc = re.search(r'<meta[^>]+name=["\']description["\'][^>]+content=["\']([^"\']*)["\']', detail_html)
        if m_desc:
            desc = m_desc.group(1).strip()

        episodes = []

        # 1. 扫描所有 <video> 标签 (优先 data-hls-src，其次 src)
        v_blocks = re.findall(r'<video([^>]+)>', detail_html)
        for idx, attr in enumerate(v_blocks):
            m_hls = re.search(r'data-hls-src=["\']([^"\']+)["\']', attr)
            m_src = re.search(r'src=["\']([^"\']+)["\']', attr)
            stream_url = m_hls.group(1).strip() if m_hls else (m_src.group(1).strip() if m_src else "")

            if not cover:
                m_post = re.search(r'poster=["\']([^"\']+)["\']', attr)
                if m_post:
                    cover = m_post.group(1).strip()

            if stream_url:
                ep_name = "片段 %02d" % (len(episodes) + 1)
                episodes.append("%s$%s" % (ep_name, stream_url))

        # 2. 从 JSON-LD 或正则匹配全局 VideoObject
        if not episodes:
            m_schema = re.findall(r'<script\s+type=["\']application/ld\+json["\']>([\s\S]*?)</script>', detail_html)
            for s in m_schema:
                if '"VideoObject"' in s:
                    try:
                        data = json.loads(s)
                        v_list = data.get("video", [])
                        if isinstance(v_list, dict):
                            v_list = [v_list]
                        for idx, v_item in enumerate(v_list):
                            c_url = v_item.get("contentUrl", "")
                            if c_url:
                                ep_name = "第 %02d 集" % (len(episodes) + 1)
                                episodes.append("%s$%s" % (ep_name, c_url))
                                if not cover:
                                    cover = v_item.get("thumbnailUrl", "")
                    except Exception:
                        pass

        # 3. 正则兜底提取页面直链流
        if not episodes:
            all_media = re.findall(r'["\'](https?://[^"\'\s]+\.(?:m3u8|mp4)[^"\'\s]*)["\']', detail_html)
            seen_streams = set()
            for m_url in all_media:
                if m_url in seen_streams:
                    continue
                seen_streams.add(m_url)
                ep_name = "播放 %02d" % (len(episodes) + 1)
                episodes.append("%s$%s" % (ep_name, m_url))

        if not cover:
            m_pic = re.search(r'<meta property=["\']og:image["\'] content=["\']([^"\']+)["\']', detail_html)
            if m_pic:
                cover = m_pic.group(1).strip()

        full_desc = (
            "【🔥 官方交流群: %s】\n"
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            "本贴为您解析到【%d】个现场视频片段，点击下方片段即可起播！\n\n%s"
        ) % (self.tgGroup, len(episodes), desc)

        play_url = "#".join(episodes) if episodes else ("无可用视频流$http://127.0.0.1")

        return {
            "list": [{
                "vod_id": event_id,
                "vod_name": title,
                "vod_pic": self._wrap_pic(cover),
                "vod_actor": self.brandActor,
                "vod_director": self.brandDirector,
                "vod_remarks": "共 %d 个片段" % len(episodes) if len(episodes) > 1 else "蝴蝶影视",
                "vod_content": full_desc,
                "vod_play_from": "57吃瓜在线",
                "vod_play_url": play_url
            }]
        }

    def playerContent(self, flag, id, vipFlags):
        raw_url = str(id).strip()
        headers = {
            "User-Agent": self._ua,
            "Referer": self._get_base() + "/",
            "Origin": self._get_base().rstrip("/")
        }

        return {
            "parse": "0",
            "playUrl": "",
            "url": raw_url,
            "header": headers
        }

    def searchContent(self, key, quick, pg="1"):
        del quick
        page = int(pg) if pg else 1
        search_path = "/search/?q=%s" % quote(key)
        if page > 1:
            search_path += "&page=%d" % page

        res = self._fetch_with_failover(search_path)
        html_text = res.get("text", "")
        vod_list = self._parse_card_list(html_text)

        return {
            "page": page,
            "pagecount": page + 1 if len(vod_list) >= 10 else page,
            "limit": len(vod_list),
            "total": 9999,
            "list": vod_list
        }

    def action(self, action):
        return {"msg": "ok"}

    def liveContent(self):
        return ""

    def localProxy(self, params):
        url = params.get("url", "")
        if not url:
            return [404, "text/plain; charset=utf-8", "Missing url parameter"]
        res = self._fetch(url, referer=self._get_base() + "/")
        return [res.get("code", 200), "image/jpeg", res.get("bytes", b"")]

    def destroy(self):
        self.options = {}
