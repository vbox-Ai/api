#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""911爆料网 — vbox 适配版（并发域名探测 + 10分钟缓存）"""

import sys
import os
import re
import json
import base64
import time
import html as html_lib
import urllib.request
import urllib.parse
import http.cookiejar
import gzip
import zlib
import ssl
from concurrent.futures import ThreadPoolExecutor, as_completed

# requests 优先，urllib 兜底
try:
    import requests
except ImportError:
    requests = None

try:
    from base.spider import Spider as SpiderBase
except ImportError:
    class SpiderBase(object):
        def getCache(self, key): return None
        def setCache(self, key, value): return "fail"
        def delCache(self, key): return "fail"


# ============================================================
# 并发域名探测 + 10 分钟 TTL 缓存
# ============================================================
_DOMAIN_CACHE = {"domain": None, "timestamp": 0}
_CACHE_TTL = 600  # 10 分钟
_PROBE_TIMEOUT = 8


def _probe_domain(domain, path, headers, timeout=_PROBE_TIMEOUT):
    """探测单个域名 + 路径，返回 (text, domain) 或 None"""
    try:
        url = domain.rstrip('/') + '/' + path.lstrip('/')
        if requests is not None:
            rsp = requests.get(url, headers=headers, timeout=timeout, verify=False)
            if rsp.status_code == 200:
                return rsp.text, domain
        else:
            req = urllib.request.Request(url, headers=headers)
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                if resp.getcode() == 200:
                    raw = resp.read()
                    if raw.startswith(b"\x1f\x8b"):
                        raw = gzip.decompress(raw)
                    return raw.decode("utf-8", errors="ignore"), domain
    except Exception:
        pass
    return None


class _DomainProbeMixin:
    """并发域名探测混入：谁响应快就用谁，10 分钟缓存"""

    def _fetch_best(self, path, headers=None, timeout=_PROBE_TIMEOUT):
        """并发探测域名，返回 (text, best_domain)。先试缓存，过期后并发探测"""
        headers = headers or getattr(self, '_ua_headers', {})
        domains = getattr(self, '_probe_domains', [])
        if not domains:
            return "", ""

        now = time.time()

        # 1. 缓存未过期 → 先试缓存域名
        cached = _DOMAIN_CACHE["domain"]
        if cached and (now - _DOMAIN_CACHE["timestamp"]) < _CACHE_TTL:
            result = _probe_domain(cached, path, headers, timeout)
            if result:
                return result

        # 2. 缓存过期/失效 → 并发探测所有域名，先到先得
        with ThreadPoolExecutor(max_workers=len(domains)) as executor:
            futures = {
                executor.submit(_probe_domain, d, path, headers, timeout): d
                for d in domains
            }
            for future in as_completed(futures):
                result = future.result()
                if result:
                    _DOMAIN_CACHE["domain"] = result[1]
                    _DOMAIN_CACHE["timestamp"] = time.time()
                    return result

        # 3. 全部失败
        return "", domains[0] if domains else ""


class Spider(_DomainProbeMixin, SpiderBase):
    def __init__(self):
        super(Spider, self).__init__()
        # 官方备用域名池（含同根域与已验证镜像）
        self.domain_pool = [
            "https://barely.jysznvsj.cc",
            "https://abopf.jysznvsj.cc",
            "https://392d.3920279.cc",
            "https://aaqq5838.cqcsms.com",
            "https://blw66.com"
        ]
        self._probe_domains = self.domain_pool  # 供 _fetch_best 使用

        self.tgGroup = "https://t.me/tvshare23"
        self.brandActor = "🦋 TG群: @tvshare23"
        self.brandDirector = "🦋 蝴蝶影视"
        self._ua = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36"
        self.options = {}

        # 固化生产级 9 大主干分类
        self.category_map = [
            {"n": "今日大瓜", "v": "jrgb"},
            {"n": "AI短剧", "v": "aidj"},
            {"n": "优先投放区", "v": "shijiebei"},
            {"n": "每日大赛", "v": "mrds"},
            {"n": "海角社区", "v": "hjsq"},
            {"n": "午夜剧场", "v": "crfys"},
            {"n": "动漫天堂", "v": "dmhv"},
            {"n": "水果派解说", "v": "sgpjs"},
            {"n": "独家爆料", "v": "rmgb"}
        ]

        self._ua_headers = {
            "User-Agent": self._ua,
            "Referer": self.domain_pool[0] + "/",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
            "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
        }

        self.ctx = ssl.create_default_context()
        self.ctx.check_hostname = False
        self.ctx.verify_mode = ssl.CERT_NONE

        self.cj = http.cookiejar.CookieJar()
        self.opener = urllib.request.build_opener(
            urllib.request.HTTPCookieProcessor(self.cj),
            urllib.request.HTTPSHandler(context=self.ctx)
        )

    # ---------------- 基类接口 ----------------

    def getName(self):
        return "蝴蝶生产级蜘蛛·911爆料网(并发漂移版)"

    def getDependence(self):
        return ['requests']

    def isVideoFormat(self, url):
        low = (url or "").lower()
        return any(k in low for k in (".m3u8", ".mp4", ".flv", ".mkv", ".avi", ".ts", ".mpd"))

    def manualVideoCheck(self):
        return False

    def destroy(self):
        self.options = {}
        _DOMAIN_CACHE["domain"] = None
        _DOMAIN_CACHE["timestamp"] = 0

    # ---------------- init：域名注入 + super ----------------

    def init(self, extend=""):
        # 先走 base.spider，应用 _vbox_effective_hosts 域名注入
        try:
            super().init(extend)
        except Exception:
            pass

        cfg = json.loads(extend) if isinstance(extend, str) and extend else (extend or {})
        self.proxies = cfg.get("proxies") or {}
        self.options = cfg if isinstance(cfg, dict) else {}

        # 注入域名 >> extend host >> 默认域名池
        injected = getattr(self, '_vbox_effective_hosts', None) or []
        if injected and str(injected[0]).startswith('http'):
            self.siteUrl = str(injected[0]).rstrip('/')
            self._probe_domains = [self.siteUrl]
        else:
            cached_url = self.getCache("active_site_url")
            if cached_url and str(cached_url) not in ("fail", "None", ""):
                self.siteUrl = str(cached_url)
            else:
                self.siteUrl = self.domain_pool[0]
            self._probe_domains = self.domain_pool

        self.host = self.siteUrl  # 兼容基类属性
        self._ua_headers["Referer"] = self.siteUrl + "/"
        return True

    # ---------------- HTTP 请求 ----------------

    def _request_single(self, target_url):
        headers = dict(self._ua_headers)
        headers["Referer"] = self.siteUrl + "/"
        req = urllib.request.Request(target_url, headers=headers)
        with self.opener.open(req, timeout=10) as resp:
            code = resp.getcode()
            raw = resp.read()
            if raw.startswith(b"\x1f\x8b"):
                raw = gzip.decompress(raw)
            elif getattr(resp, "headers", {}).get("Content-Encoding") == "deflate":
                try:
                    raw = zlib.decompress(raw)
                except Exception:
                    raw = zlib.decompress(raw, -zlib.MAX_WBITS)
            try:
                text = raw.decode("utf-8")
            except Exception:
                text = raw.decode("latin1", errors="ignore")
            return code, text

    def _fetch(self, path_or_url):
        """并发探测域名并请求。返回 {"code": int, "text": str, "err": str}"""
        if not path_or_url:
            return {"code": 0, "text": "", "err": ""}

        # 绝对地址直接请求
        if path_or_url.startswith("http://") or path_or_url.startswith("https://"):
            try:
                code, text = self._request_single(path_or_url)
                return {"code": code, "text": text, "err": ""}
            except Exception as e:
                return {"code": -1, "text": "", "err": str(e)}

        clean_path = path_or_url if path_or_url.startswith("/") else ("/" + path_or_url)

        # 1. 优先用缓存域名
        cached = _DOMAIN_CACHE["domain"]
        if cached and (time.time() - _DOMAIN_CACHE["timestamp"]) < _CACHE_TTL:
            try:
                code, text = self._request_single(cached + clean_path)
                if code == 200:
                    return {"code": code, "text": text, "err": ""}
            except Exception:
                pass

        # 2. 缓存失效/被拦截 → 并发探测所有域名
        for cand in self._probe_domains:
            if cand == _DOMAIN_CACHE.get("domain"):
                continue
            try:
                code, text = self._request_single(cand + clean_path)
                if code == 200:
                    self.siteUrl = cand
                    self.setCache("active_site_url", cand)
                    _DOMAIN_CACHE["domain"] = cand
                    _DOMAIN_CACHE["timestamp"] = time.time()
                    return {"code": code, "text": text, "err": ""}
            except Exception:
                continue

        return {"code": -1, "text": "", "err": "所有备用域名均不可达"}

    def _post(self, target_url, data_dict):
        if target_url.startswith("/"):
            target_url = self.siteUrl + target_url
        body = urllib.parse.urlencode(data_dict).encode("utf-8")
        headers = dict(self._ua_headers)
        headers.update({
            "X-Requested-With": "XMLHttpRequest",
            "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8",
            "Accept": "application/json, text/javascript, */*; q=0.01",
            "Connection": "close"
        })
        try:
            req = urllib.request.Request(target_url, data=body, headers=headers)
            with self.opener.open(req, timeout=10) as resp:
                code = resp.getcode()
                raw = resp.read()
                if raw.startswith(b"\x1f\x8b"):
                    raw = gzip.decompress(raw)
                try:
                    text = raw.decode("utf-8")
                except Exception:
                    text = raw.decode("latin1", errors="ignore")
                return {"code": code, "text": text, "err": ""}
        except Exception as e:
            return {"code": -1, "text": "", "err": str(e)}

    def _decode_xor(self, enc_b64_str, key_str):
        try:
            raw = base64.b64decode(enc_b64_str)
            key = key_str.encode("utf-8")
            out = bytes([raw[i] ^ key[i % len(key)] for i in range(len(raw))])
            return out.decode("utf-8", errors="ignore")
        except Exception:
            return ""

    # ---------------- 首页 ----------------

    def homeContent(self, filter):
        classes = [{"type_name": c["n"], "type_id": c["v"]} for c in self.category_map]
        result = {"class": classes}
        if filter:
            result["filters"] = {}
        return result

    def homeVideoContent(self):
        return {"list": []}

    # ---------------- 分类列表 ----------------

    def categoryContent(self, tid, pg, filter, extend):
        del filter
        extend = extend if isinstance(extend, dict) else {}
        slug = str(tid).strip("/")
        page_num = int(pg) if str(pg).isdigit() else 1
        req_url = "/category/%s/%s/" % (slug, page_num) if page_num > 1 else "/category/%s/" % slug

        res = self._fetch(req_url)
        html_text = res.get("text", "")

        blocks = []
        if "<article" in html_text:
            raw_blocks = html_text.split("<article")[1:]
            for b in raw_blocks:
                cut_b = b.split("</article>")[0]
                if "post-list-ad" in cut_b or ("loadBannerDirect" in cut_b and "/archives/" not in cut_b):
                    continue
                blocks.append("<article" + cut_b)

        result_list = []
        current_cover = self._get_cover()

        for b in blocks:
            link_m = re.search(r'href=["\']([^"\']*/archives/\d+[^"\']*)["\']', b, re.I)
            if not link_m:
                continue
            target_href = link_m.group(1).strip()
            clean_vid = target_href.lstrip("/")

            title = ""
            h_title = re.search(r'<h[23][^>]*>(?:<a[^>]*>)?([^<]+)(?:</a>)?</h[23]>', b, re.I)
            if h_title:
                clean = h_title.group(1).strip()
                if "loadBanner" not in clean and len(clean) > 2:
                    title = clean
            if not title:
                t_m = re.search(r'title=["\']([^"\']+)["\']', b, re.I)
                if t_m and "loadBanner" not in t_m.group(1) and len(t_m.group(1).strip()) > 2:
                    title = t_m.group(1).strip()
            if not title or title.startswith("911爆料编辑部"):
                continue

            remarks = ""
            date_m = re.search(r'(\d{4}[-/]\d{1,2}[-/]\d{1,2})', b)
            if date_m:
                remarks = date_m.group(1).strip()

            result_list.append({
                "vod_id": target_href if target_href.startswith("http") else self.siteUrl + "/" + clean_vid,
                "vod_name": html_lib.unescape(title),
                "vod_pic": current_cover,
                "vod_remarks": remarks,
                "style": {"type": "rect", "ratio": 0.75}
            })

        return {
            "page": page_num,
            "pagecount": 999 if result_list else 1,
            "limit": 20,
            "total": 9999 if result_list else 0,
            "list": result_list
        }

    # ---------------- 详情页 ----------------

    def detailContent(self, ids):
        raw_id = ids[0] if isinstance(ids, (list, tuple)) else str(ids)
        clean_path = raw_id.replace("vod/", "")
        if not clean_path.startswith("/"):
            clean_path = "/" + clean_path

        # 如果 raw_id 是完整 URL，直接用
        if raw_id.startswith("http"):
            res = self._fetch(raw_id)
        else:
            res = self._fetch(clean_path)
        html_text = res.get("text", "")

        # 标题
        title = ""
        t_m = re.search(r'<h1[^>]*>([\s\S]*?)</h1>', html_text, re.I)
        if t_m:
            title = re.sub(r'<[^>]+>', '', t_m.group(1)).strip()
        if not title:
            og_t = re.search(r'<meta[^>]+property=["\']og:title["\'][^>]+content=["\']([^"\']+)["\']', html_text, re.I)
            if og_t:
                title = og_t.group(1).strip()

        # 简介
        content = "暂无简介"
        c_m = re.search(r'<div[^>]+class=["\'][^"\']*(?:post-content|entry-content)[^"\']*["\'][^>]*>([\s\S]*?)</div>', html_text, re.I)
        if c_m:
            raw_c = re.sub(r'<(?:script|style|div)[^>]*>[\s\S]*?</(?:script|style|div)>', '', c_m.group(1), flags=re.I)
            clean_c = re.sub(r'<[^>]+>', '', raw_c).strip()
            if clean_c:
                content = re.sub(r'\s+', ' ', clean_c)[:250]

        # 核心逆向：提取真实视频直链与专属剧照
        play_url = ""
        cover_pic = ""

        config_m = re.search(r'data-config=(["\'])([\s\S]*?)\1', html_text, re.I)
        if config_m:
            raw_cfg = html_lib.unescape(html_lib.unescape(config_m.group(2).strip()))
            try:
                cfg_obj = json.loads(raw_cfg)
                v_obj = cfg_obj.get("video", {})
                if isinstance(v_obj, dict):
                    play_url = v_obj.get("url", "")
                    cover_pic = v_obj.get("pic", "")
            except Exception:
                pass
            if not play_url:
                v_sec = re.search(r'"video"\s*:\s*\{([^}]+)\}', raw_cfg)
                if v_sec:
                    u_m = re.search(r'"url"\s*:\s*"([^"]+)"', v_sec.group(1))
                    if u_m:
                        play_url = u_m.group(1)
                    p_m = re.search(r'"pic"\s*:\s*"([^"]+)"', v_sec.group(1))
                    if p_m:
                        cover_pic = p_m.group(1)

        # 容灾匹配
        if not play_url:
            m3u8_candidates = re.findall(r'https?://[^\s"\'<>]+\.m3u8[^\s"\'<>]*', html_text, re.I)
            for cand in m3u8_candidates:
                cand_clean = html_lib.unescape(cand).replace(r"\/", "/")
                if "advert" not in cand_clean and ("auth_key" in cand_clean or "videos5" in cand_clean):
                    play_url = cand_clean
                    break
            if not play_url and m3u8_candidates:
                play_url = html_lib.unescape(m3u8_candidates[-1]).replace(r"\/", "/")

        if play_url:
            play_url = html_lib.unescape(play_url).replace(r"\/", "/").replace("&amp;", "&").strip()
        if cover_pic:
            cover_pic = html_lib.unescape(cover_pic).replace(r"\/", "/").strip()
        else:
            og_img = re.search(r'<meta[^>]+property=["\']og:image["\'][^>]+content=["\']([^"\']+)["\']', html_text, re.I)
            if og_img and "placeholder" not in og_img.group(1):
                cover_pic = og_img.group(1).strip()
            else:
                cover_pic = self._get_cover()

        brand_desc = (
            "【🔥 官方交流群: %s】\n"
            "【🌐 当前激活节点: %s】\n"
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            "%s"
        ) % (self.tgGroup, self.siteUrl, content)
        escaped_desc = brand_desc.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")

        vod_play_url = "正片直链$%s" % play_url if play_url else ""

        return {
            "list": [{
                "vod_id": raw_id,
                "vod_name": html_lib.unescape(title) if title else "精彩视频",
                "vod_pic": cover_pic,
                "vod_actor": self.brandActor,
                "vod_director": self.brandDirector,
                "vod_remarks": "高清正片",
                "vod_content": escaped_desc,
                "vod_play_from": "蝴蝶专线",
                "vod_play_url": vod_play_url
            }]
        }

    # ---------------- 播放器 ----------------

    def playerContent(self, flag, id, vipFlags):
        return {
            "parse": 0,
            "url": str(id).strip(),
            "header": {
                "User-Agent": self._ua,
                "Referer": self.siteUrl + "/"
            }
        }

    # ---------------- 搜索 ----------------

    def searchContent(self, key, quick, pg="1"):
        page_num = int(pg) if str(pg).isdigit() else 1
        query = urllib.parse.quote(str(key).strip())
        req_url = "/search/%s/%s/" % (query, page_num) if page_num > 1 else "/search/%s/" % query

        res = self._fetch(req_url)
        html_text = res.get("text", "")

        blocks = []
        if "<article" in html_text:
            raw_blocks = html_text.split("<article")[1:]
            for b in raw_blocks:
                cut_b = b.split("</article>")[0]
                if "post-list-ad" in cut_b or ("loadBannerDirect" in cut_b and "/archives/" not in cut_b):
                    continue
                blocks.append("<article" + cut_b)

        result_list = []
        current_cover = self._get_cover()

        for b in blocks:
            link_m = re.search(r'href=["\']([^"\']*/archives/\d+[^"\']*)["\']', b, re.I)
            if not link_m:
                continue
            target_href = link_m.group(1).strip()
            clean_vid = target_href.lstrip("/")

            title = ""
            h_title = re.search(r'<h[23][^>]*>(?:<a[^>]*>)?([^<]+)(?:</a>)?</h[23]>', b, re.I)
            if h_title:
                clean = h_title.group(1).strip()
                if "loadBanner" not in clean and len(clean) > 2:
                    title = clean
            if not title or title.startswith("911爆料编辑部"):
                continue

            remarks = ""
            date_m = re.search(r'(\d{4}[-/]\d{1,2}[-/]\d{1,2})', b)
            if date_m:
                remarks = date_m.group(1).strip()

            result_list.append({
                "vod_id": target_href if target_href.startswith("http") else self.siteUrl + "/" + clean_vid,
                "vod_name": html_lib.unescape(title),
                "vod_pic": current_cover,
                "vod_remarks": remarks,
                "style": {"type": "rect", "ratio": 0.75}
            })

        return {
            "page": page_num,
            "pagecount": 999 if result_list else 1,
            "limit": 20,
            "total": 9999 if result_list else 0,
            "list": result_list
        }

    # ---------------- 本地代理 ----------------

    def localProxy(self, param):
        return [200, "text/plain; charset=utf-8", b"ok", {}]

    def _get_cover(self):
        return self.siteUrl + "/usr/themes/Mirages/images/home-cover-placeholder-v2.png"

    def action(self, action):
        if action == "toast":
            return {"msg": "当前节点: %s" % self.siteUrl}
        return {"msg": "未配置 action"}

    def liveContent(self):
        return ""