#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
淫花宫 - vbox 远程源适配版
站点: https://breplc.yhg5.help/yhg/
结构: 苹果CMS macCMS 模板站
适配: 继承 SpiderBase + super().init(extend) + localProxy三元组 + 封面走本地代理
"""
import sys
sys.path.append('..')
import re
import json
import urllib.request
import urllib.parse

try:
    from base.spider import Spider as SpiderBase
except ImportError:
    class SpiderBase(object):
        def __init__(self):
            self._vbox_effective_hosts = []
        def getCache(self, key): return None
        def setCache(self, key, value): return "fail"
        def delCache(self, key): return "fail"


class Spider(SpiderBase):
    PLATFORM_KEY = "yinhua_py"

    def __init__(self):
        try:
            super(Spider, self).__init__()
        except Exception:
            pass
        self.siteUrl = "https://breplc.yhg5.help"
        self.HOST = self.siteUrl
        self.ua = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"

    def init(self, extend=""):
        try:
            super().init(extend)
        except AttributeError:
            pass
        return True

    def getName(self):
        return "淫花宫"

    def isVideoFormat(self, url):
        low = (url or "").lower()
        return any(k in low for k in (".m3u8", ".mp4", ".flv", ".mkv", ".ts"))

    def manualVideoCheck(self):
        return False

    def destroy(self):
        pass

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
        if url.startswith("//"):
            url = "https:" + url
        elif url.startswith("/"):
            url = self.HOST + url
        base = self._proxy_base()
        sep = "&" if "?" in base else "?"
        u = base + sep + "type=img&u=" + urllib.parse.quote(str(url), safe="")
        if referer:
            u += "&r=" + urllib.parse.quote(referer, safe="")
        return u

    def _serve_img(self, url, referer=None):
        try:
            headers = {"User-Agent": self.ua}
            if referer:
                headers["Referer"] = referer
            req = urllib.request.Request(url, headers=headers)
            with urllib.request.urlopen(req, timeout=15) as resp:
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

    def _fetch(self, url):
        req = urllib.request.Request(url, headers={"User-Agent": self.ua})
        try:
            resp = urllib.request.urlopen(req, timeout=15)
            return resp.read().decode("utf-8", errors="replace")
        except Exception:
            return ""

    def _fix_img(self, img):
        """封面相对/绝对路径规范化 + 本地代理包装"""
        img = str(img or "").strip()
        if not img or img.startswith("data:"):
            return ""
        if img.startswith("//"):
            img = "https:" + img
        elif img.startswith("/"):
            img = self.HOST + img
        return self._proxy_img_url(img, referer=self.HOST + "/")

    def _parse_cards(self, html, limit=0):
        """解析 macCMS 卡片: /{vid}.html 链接 + 图片"""
        videos = []
        seen = set()
        link_items = re.findall(
            r'<a[^>]*href="(?:\./)?(\d+)\.html"[^>]*title="([^"]*)"',
            html, re.S
        )
        img_items = re.findall(
            r'<img[^>]*(?:data-original|src)="([^"]+)"',
            html, re.S
        )
        for i, (vid, title) in enumerate(link_items[:limit] if limit else link_items):
            if vid in seen:
                continue
            seen.add(vid)
            img = self._fix_img(img_items[i]) if i < len(img_items) else ""
            videos.append({
                "vod_id": vid,
                "vod_name": title,
                "vod_pic": img,
                "vod_remarks": ""
            })
        return videos

    def homeContent(self, filter):
        classes = [
            {"type_name": "熟母少妇", "type_id": "20"},
            {"type_name": "网红直播", "type_id": "21"},
            {"type_name": "自拍偷拍", "type_id": "22"},
            {"type_name": "强奸乱伦", "type_id": "23"},
            {"type_name": "高清国产", "type_id": "24"},
            {"type_name": "韩国专区", "type_id": "25"},
            {"type_name": "日本有码", "type_id": "26"},
            {"type_name": "日本无码", "type_id": "27"},
            {"type_name": "欧美情色", "type_id": "28"},
            {"type_name": "动漫卡通", "type_id": "29"},
            {"type_name": "三级伦理", "type_id": "30"},
        ]
        if not classes:
            classes = [{"type_name": "淫花宫·全部", "type_id": "24"}]
        result = {"class": classes, "filters": {}}

        # 首页推荐 (带时间预算保护, 失败不影响分类返回)
        try:
            html = self._fetch(self.siteUrl + "/cn/home/web/")
            result["list"] = self._parse_cards(html, limit=20)
        except Exception:
            result["list"] = []
        return result

    def homeVideoContent(self):
        return {"list": []}

    def categoryContent(self, tid, pg, filter, extend):
        page = int(pg) if pg else 1
        url = f"{self.siteUrl}/vodtype/{tid}.html"
        if page > 1:
            url = f"{self.siteUrl}/vodtype/{tid}/page/{page}.html"

        html = self._fetch(url)
        videos = self._parse_cards(html)

        result = {
            "list": videos,
            "page": page,
            "pagecount": 100,
            "limit": 30,
            "total": 3000
        }
        return result

    def detailContent(self, ids):
        vid = ids[0]
        url = f"{self.siteUrl}/{vid}.html"
        html = self._fetch(url)

        title = re.search(r"<title>([^<]*)</title>", html)
        title = title.group(1).split("_")[0] if title else ""

        pic = ""
        pm = re.search(r'<img[^>]+(?:data-original|src)="([^"]+\.(?:jpg|jpeg|png|webp))"', html, re.I)
        if pm:
            pic = self._fix_img(pm.group(1))

        m3u8 = re.search(r"['\"]([^'\"]*\.m3u8[^'\"]*)['\"]", html)
        m3u8_url = m3u8.group(1).replace('\\/', '/') if m3u8 else ""

        list_data = [{
            "vod_id": vid,
            "vod_name": title,
            "vod_pic": pic,
            "vod_year": "",
            "vod_area": "",
            "vod_remarks": "",
            "vod_content": "",
            "vod_play_from": "直链",
            "vod_play_url": m3u8_url,
        }]
        return {"list": list_data}

    def searchContent(self, key, quick, pg=1):
        url = f"{self.siteUrl}/s/{urllib.parse.quote(key)}.html"
        html = self._fetch(url)

        videos = []
        seen = set()
        items = re.findall(
            r'<a[^>]*href="(?:\./)?(\d+)\.html"[^>]*title="([^"]*)"',
            html, re.S
        )
        img_items = re.findall(
            r'<img[^>]*(?:data-original|src)="([^"]+)"',
            html, re.S
        )
        for i, (vid, title) in enumerate(items):
            if vid in seen:
                continue
            seen.add(vid)
            img = self._fix_img(img_items[i]) if i < len(img_items) else ""
            videos.append({
                "vod_id": vid,
                "vod_name": title,
                "vod_pic": img,
                "vod_remarks": ""
            })

        result = {
            "list": videos,
            "page": 1,
            "pagecount": 1,
            "limit": 30,
            "total": len(videos)
        }
        return result

    def playerContent(self, flag, id, vipFlags):
        return {
            "parse": 0,
            "jx": 0,
            "url": id,
            "header": {
                "User-Agent": self.ua,
                "Referer": self.siteUrl + "/"
            }
        }

    def localProxy(self, param):
        p = {}
        if isinstance(param, dict):
            p = param
        elif isinstance(param, str):
            s = param.strip()
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
        u = urllib.parse.unquote(str(p.get("u") or p.get("url") or ""))
        r = urllib.parse.unquote(str(p.get("r") or "")) or None
        if t == "img" and u:
            return self._serve_img(u, referer=r)
        return [404, "text/plain", b""]

    def setProxy(self, proxy):
        pass

    def getProxy(self):
        return None

    def getDependence(self):
        return ""
