#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
蝴蝶影视·小荷塘 - vbox 远程源适配版
站点: https://y5b1.tllp166.xyz (macCMS 风格)
适配: 继承 SpiderBase + super().init(extend) + localProxy三元组 + 封面走本地代理
"""
import sys
sys.path.append('..')
import os
import re
import json
import base64
import html as html_lib
import urllib.request
import urllib.parse
from urllib.parse import urlparse, quote, unquote
import http.cookiejar
import gzip
import zlib
import ssl

try:
    from base.spider import Spider as SpiderBase
except ImportError:
    class SpiderBase(object):
        def __init__(self):
            self._vbox_effective_hosts = []
        def getCache(self, key): return None
        def setCache(self, key, value): return "fail"
        def delCache(self, key): return "fail"


def format_remarks(brand="蝴蝶影视", meta=""):
    clean_meta = str(meta or "").strip()
    clean_meta = re.sub(r"[\r\n\t]+", " ", clean_meta).strip()
    if clean_meta:
        return "%s | %s" % (brand, clean_meta)
    return brand


class Spider(SpiderBase):
    PLATFORM_KEY = "xiaohetang_py"

    def __init__(self):
        try:
            super(Spider, self).__init__()
        except Exception:
            pass
        self.siteUrl = "https://y5b1.tllp166.xyz"
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
        try:
            super().init(extend)
        except AttributeError:
            pass
        if isinstance(extend, dict):
            self.options = extend
        elif extend:
            try:
                self.options = json.loads(extend)
            except Exception:
                self.options = {}
        return True

    def getName(self):
        return "蝴蝶影视·小荷塘"

    def isVideoFormat(self, url):
        if not url:
            return False
        low = url.lower()
        if any(bad in low for bad in ("preview.mp4", "sample.mp4", "trailer.mp4", "loading", "stat")):
            return False
        return any(k in low for k in (".m3u8", ".mp4", ".flv", ".mkv", ".avi", ".ts", ".mpd", "index.png"))

    def manualVideoCheck(self):
        return False

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
        try:
            headers = {"User-Agent": self._ua}
            if referer:
                headers["Referer"] = referer
            req = urllib.request.Request(url, headers=headers)
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
            return [200, ct, raw]
        except Exception:
            return [502, "text/plain", b"proxy fetch failed"]

    def _fetch(self, target_url, data=None, referer="", headers_custom=None):
        if not target_url:
            return {"code": 0, "text": "", "bytes": b"", "err": "", "final_url": ""}
        if target_url.startswith("//"):
            target_url = "https:" + target_url
        elif target_url.startswith("/"):
            target_url = self.siteUrl + target_url

        headers = {
            "User-Agent": self._ua,
            "Referer": referer if referer else (self.siteUrl + "/"),
            "Accept": "*/*",
            "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
            "Accept-Encoding": "gzip, deflate",
            "Connection": "keep-alive"
        }
        if headers_custom:
            headers.update(headers_custom)

        req_data = None
        if data is not None:
            if isinstance(data, dict):
                req_data = urllib.parse.urlencode(data).encode("utf-8")
                headers["Content-Type"] = "application/x-www-form-urlencoded; charset=UTF-8"
                headers["X-Requested-With"] = "XMLHttpRequest"
            elif isinstance(data, (bytes, str)):
                req_data = data.encode("utf-8") if isinstance(data, str) else data

        last_err = ""
        for attempt in range(2):
            try:
                req = urllib.request.Request(target_url, data=req_data, headers=headers)
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

                    shell_m = re.search(r'decodeURIComponent\s*\(\s*atob\s*\(\s*["\']([A-Za-z0-9+/=]+)["\']\s*\)\s*\)', text)
                    if shell_m:
                        try:
                            b64_str = shell_m.group(1)
                            decoded_raw = base64.b64decode(b64_str).decode("latin1")
                            unquoted_html = urllib.parse.unquote(decoded_raw)
                            try:
                                text = unquoted_html.encode("latin1").decode("utf-8")
                            except Exception:
                                text = unquoted_html
                        except Exception:
                            pass

                    return {"code": code, "text": text, "bytes": raw, "err": "", "final_url": final_url}
            except urllib.error.HTTPError as e:
                last_err = "HTTP %s" % e.code
                if e.code in (451, 403, 429) and attempt == 0:
                    continue
                err_raw = ""
                try:
                    err_raw = e.read().decode("utf-8", errors="ignore")
                except Exception:
                    pass
                return {"code": e.code, "text": err_raw, "bytes": b"", "err": str(e), "final_url": target_url}
            except Exception as e:
                last_err = str(e)
                if attempt == 0:
                    continue
                return {"code": -1, "text": "", "bytes": b"", "err": str(e), "final_url": target_url}

        return {"code": -1, "text": "", "bytes": b"", "err": last_err, "final_url": target_url}

    def homeContent(self, filter):
        classes = [
            {"type_name": "🇨🇳 国内视频", "type_id": "/index.php/vod/type/id/9.html"},
            {"type_name": "🌸 系列全集", "type_id": "/index.php/vod/type/id/1.html"},
            {"type_name": "🌐 国外精选", "type_id": "/index.php/vod/type/id/12.html"},
            {"type_name": "🔥 猎奇专区", "type_id": "/index.php/vod/type/id/15.html"},
            {"type_name": "🎀 次元萝莉", "type_id": "/index.php/vod/type/id/2.html"},
            {"type_name": "👄 欧美口舌", "type_id": "/index.php/vod/type/id/3.html"}
        ]
        if not classes:
            classes = [{"type_name": "小荷塘·全部", "type_id": "/index.php/vod/type/id/9.html"}]
        result = {"class": classes}
        if filter:
            filter_items = [
                {
                    "key": "by",
                    "name": "排序",
                    "init": "time",
                    "value": [
                        {"n": "最新发布", "v": "time"},
                        {"n": "本周最热", "v": "hits_week"},
                        {"n": "最赞影片", "v": "up"}
                    ]
                }
            ]
            result["filters"] = {c["type_id"]: filter_items for c in classes}
        return result

    def homeVideoContent(self):
        return {"list": []}

    def _extract_pic(self, block_content):
        """从卡片块中提取封面并转本地代理 URL"""
        pic = ""
        cand_pics = re.findall(r'["\'](https?://[^"\']+\.(?:jpg|jpeg|png|webp)[^"\']*)["\']', block_content, re.I)
        if not cand_pics:
            cand_pics = re.findall(r'["\'](/[^"\']+\.(?:jpg|jpeg|png|webp)[^"\']*)["\']', block_content, re.I)
        for cp in cand_pics:
            low_cp = cp.lower()
            if any(bad in low_cp for bad in ("loading.png", "load", "default", "logo", "touxiang", "favicon")):
                continue
            pic = cp
            break
        if not pic:
            for attr in ("data-original", "data-src", "data-bg", "data-cover", "data-thumb"):
                attr_m = re.search(r'%s=["\']([^"\']+)["\']' % attr, block_content, re.I)
                if attr_m and "loading" not in attr_m.group(1).lower():
                    pic = attr_m.group(1).strip()
                    break
        if not pic:
            bg_m = re.search(r'url\s*\(\s*["\']?([^"\'\)\s]+)["\']?\s*\)', block_content)
            if bg_m and "loading" not in bg_m.group(1).lower() and not bg_m.group(1).endswith((".svg", ".ico")):
                pic = bg_m.group(1).strip()
        if pic.startswith("//"):
            pic = "https:" + pic
        elif pic.startswith("/"):
            pic = self.siteUrl + pic
        return self._proxy_img_url(pic, referer=self.siteUrl + "/") if pic else ""

    def categoryContent(self, tid, pg, filter, extend):
        del filter
        slug = str(tid).strip()
        pg_num = int(pg) if str(pg).isdigit() else 1

        extend = extend if isinstance(extend, dict) else {}
        by_val = extend.get("by", "")

        target_path = slug
        if by_val:
            id_m = re.search(r'id/(\d+)', slug)
            type_id = id_m.group(1) if id_m else "9"
            if pg_num > 1:
                target_path = "/index.php/vod/show/by/%s/id/%s/page/%d.html" % (by_val, type_id, pg_num)
            else:
                target_path = "/index.php/vod/show/by/%s/id/%s.html" % (by_val, type_id)
        else:
            if pg_num > 1:
                target_path = re.sub(r'\.html$', '/page/%d.html' % pg_num, target_path)

        res = self._fetch(target_path)
        html_text = res.get("text", "")

        blocks = re.split(r'<a\s+[^>]*href=["\'](/index\.php/vod/play/id/\d+[^"\']*)["\']', html_text, flags=re.I)

        videos = []
        seen_ids = set()

        for i in range(1, len(blocks), 2):
            play_href = blocks[i].strip()
            block_content = blocks[i + 1] if i + 1 < len(blocks) else ""

            if play_href in seen_ids:
                continue

            title = ""
            title_m = re.search(r'class=["\']?[^"\'>]*(?:title|name|text)[^"\'>]*["\']?[^>]*>([\s\S]*?)<', block_content, re.I)
            if title_m:
                title = re.sub(r'<[^>]+>', '', title_m.group(1)).strip()
            if not title:
                title_alt = re.search(r'(?:title|alt)=["\']([^"\']+)["\']', block_content, re.I)
                if title_alt:
                    title = title_alt.group(1).strip()

            pic = self._extract_pic(block_content)

            meta_str = ""
            dur_m = re.search(r'(\d+:\d+|\d+集)', block_content)
            if dur_m:
                meta_str = dur_m.group(1).strip()

            remarks = format_remarks("蝴蝶影视", meta_str if meta_str else "超清")

            if not title:
                id_match = re.search(r'id/(\d+)', play_href)
                title = "精彩视频 %s" % (id_match.group(1) if id_match else "")

            seen_ids.add(play_href)
            videos.append({
                "vod_id": play_href,
                "vod_name": html_lib.unescape(title),
                "vod_pic": pic if pic else "https://dummyimage.com/600x338/1a1a1a/ffffff.png&text=No+Pic",
                "vod_remarks": remarks,
                "style": {"type": "rect", "ratio": 1.78}
            })

        return {
            "page": pg_num,
            "pagecount": pg_num + 1 if len(videos) >= 15 else 1,
            "limit": len(videos),
            "total": 9999 if len(videos) >= 15 else len(videos),
            "list": videos
        }

    def detailContent(self, ids):
        raw_id = ids[0] if isinstance(ids, (list, tuple)) else str(ids)
        detail_path = raw_id if raw_id.startswith("http") else self.siteUrl + raw_id

        res = self._fetch(detail_path)
        html_text = res.get("text", "")

        title_m = re.search(r'<title[^>]*>(.*?)</title>', html_text, re.I)
        raw_title = title_m.group(1).strip() if title_m else "精彩影视"
        clean_title = raw_title.split("-")[0].split("_")[0].strip()

        pic_m = re.search(r'<img[^>]+(?:data-original|src)=["\'](https?://[^"\']+\.(?:jpg|jpeg|png|webp))["\']', html_text, re.I)
        pic = ""
        if pic_m:
            pic = self._proxy_img_url(pic_m.group(1), referer=detail_path)

        desc_lines = [
            "【🔥 官方交流群: %s】" % self.tgGroup,
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━━",
            "• 影片名称: %s" % clean_title,
            "• 活跃节点: %s" % self.siteUrl,
            "• 播放模式: 蝴蝶影视专属动态极速硬解",
            "• 本接口已启用页面脱壳与动态鉴权防护。"
        ]
        escaped_desc = "\n".join(desc_lines).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")

        safe_title = clean_title.replace("$", "＄").replace("#", "＃")

        return {
            "list": [{
                "vod_id": raw_id,
                "vod_name": html_lib.unescape(clean_title),
                "vod_pic": pic,
                "vod_actor": self.brandActor,
                "vod_director": self.brandDirector,
                "vod_remarks": format_remarks("蝴蝶影视", "正片"),
                "vod_content": escaped_desc,
                "vod_play_from": "🦋蝴蝶极速专线",
                "vod_play_url": "%s$%s" % (safe_title, raw_id)
            }]
        }

    def playerContent(self, flag, id, vipFlags):
        raw_id = str(id).strip()
        play_url = raw_id if raw_id.startswith("http") else self.siteUrl + raw_id

        headers = {
            "User-Agent": self._ua,
            "Referer": self.siteUrl + "/"
        }

        return {
            "parse": 1,
            "jx": 0,
            "url": play_url,
            "header": headers
        }

    def searchContent(self, key, quick, pg="1"):
        pg_num = int(pg) if str(pg).isdigit() else 1
        search_path = "/index.php/vod/search/page/%d/wd/%s.html" % (pg_num, urllib.parse.quote(key))

        res = self._fetch(search_path)
        html_text = res.get("text", "")

        blocks = re.split(r'<a\s+[^>]*href=["\'](/index\.php/vod/play/id/\d+[^"\']*)["\']', html_text, flags=re.I)

        videos = []
        seen_ids = set()

        for i in range(1, len(blocks), 2):
            play_href = blocks[i].strip()
            block_content = blocks[i + 1] if i + 1 < len(blocks) else ""

            if play_href in seen_ids:
                continue

            title = ""
            title_m = re.search(r'class=["\']?[^"\'>]*(?:title|name|text)[^"\'>]*["\']?[^>]*>([\s\S]*?)<', block_content, re.I)
            if title_m:
                title = re.sub(r'<[^>]+>', '', title_m.group(1)).strip()
            if not title:
                title_alt = re.search(r'(?:title|alt)=["\']([^"\']+)["\']', block_content, re.I)
                if title_alt:
                    title = title_alt.group(1).strip()

            pic = self._extract_pic(block_content)

            remarks = format_remarks("蝴蝶影视", "搜索")

            if not title:
                id_match = re.search(r'id/(\d+)', play_href)
                title = "%s 相关视频 %s" % (key, id_match.group(1) if id_match else "")

            seen_ids.add(play_href)
            videos.append({
                "vod_id": play_href,
                "vod_name": html_lib.unescape(title),
                "vod_pic": pic if pic else "https://dummyimage.com/600x338/1a1a1a/ffffff.png&text=Search",
                "vod_remarks": remarks,
                "style": {"type": "rect", "ratio": 1.78}
            })

        return {
            "page": pg_num,
            "pagecount": pg_num + 1 if len(videos) >= 15 else 1,
            "limit": len(videos),
            "total": 9999 if len(videos) >= 15 else len(videos),
            "list": videos
        }

    def action(self, action):
        if action == "toast":
            return {"msg": "🦋 蝴蝶影视正在为您极速解析"}
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
        try:
            self.cj.clear()
        except Exception:
            pass
