
# -*- coding: utf-8 -*-
# 茄子精品 Spider
# 站点: https://oxh.qzjp4.beer/qzjp/
# 真实结构: <li class="fed-list-item"> + <a class="fed-list-pics" data-original> + player_data.url

import re as _re
import urllib.parse as _urlparse

try:
    from base.spider import Spider as BaseSpider
except ImportError:
    class BaseSpider:
        def init(self, extend=""): pass
        def homeContent(self, filter): return {}
        def categoryContent(self, tid, pg, filter, extend): return {}
        def detailContent(self, ids): return {}
        def searchContent(self, key, quick, pg): return {}
        def playerContent(self, flag, id, vipFlags): return {}
        def localProxy(self, param): return [404, "text/plain", ""]
        def isVideoFormat(self, url): return False
        def manualVideoCheck(self): return False
        def getName(self): return ""

class Spider(BaseSpider):

    def init(self, extend=""):
        # iOS 注入的有效域名（用户自定义 + defaultHosts）优先于硬编码域名
        injected = globals().get('_vbox_effective_hosts')
        if injected and isinstance(injected, list) and len(injected) > 0:
            self.siteUrl = str(injected[0]).rstrip('/')
        else:
            self.siteUrl = "https://oxh.qzjp4.beer"
        self._ua = "Mozilla/5.0 (Linux; Android 13) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Mobile Safari/537.36"
        self.headers = {
            "User-Agent": self._ua,
            "Referer": self.siteUrl + "/",
        }

    def getDependence(self):
        return []

    def fetch(self, url, headers=None, **kw):
        """基类 fetch 兼容层，统一走 urllib，保证域名注入生效"""
        kw.pop('timeout', None)
        import urllib.request
        import ssl
        ctx = ssl._create_unverified_context()
        req = urllib.request.Request(url, headers=headers or self.headers)
        with urllib.request.urlopen(req, timeout=kw.get('timeout', 15), context=ctx) as resp:
            class _R:
                pass
            r = _R()
            r.status_code = resp.getcode()
            r.text = resp.read().decode("utf-8", errors="ignore")
            r.headers = dict(resp.headers)
            return r

    def _fetch_text(self, url, referer=None):
        h = {
            "User-Agent": self._ua,
            "Referer": referer or self.siteUrl + "/",
        }
        r = self.fetch(url, headers=h)
        return r.text if r else ""

    def homeContent(self, filter):
        result = {}
        class_parse = [
            {"type_name": "美女写真", "type_id": "20"},
            {"type_name": "国产精品", "type_id": "21"},
            {"type_name": "无码专区", "type_id": "22"},
            {"type_name": "中文字幕", "type_id": "23"},
            {"type_name": "强奸乱伦", "type_id": "24"},
            {"type_name": "人妻熟女", "type_id": "25"},
            {"type_name": "亚洲情色", "type_id": "26"},
            {"type_name": "制服丝袜", "type_id": "27"},
            {"type_name": "SM捆绑", "type_id": "28"},
            {"type_name": "自淫系列", "type_id": "29"},
            {"type_name": "三级伦理", "type_id": "30"},
        ]
        result["class"] = class_parse
        result["filters"] = {}
        result["list"] = []
        return result

    def categoryContent(self, tid, pg, filter, extend):
        result = {}
        page = int(pg or 1)
        if page > 1:
            url = f"{self.siteUrl}/cn/home/web/index.php/vod/type/id/{tid}-{page}.html"
        else:
            url = f"{self.siteUrl}/cn/home/web/index.php/vod/type/id/{tid}.html"
        html = self._fetch_text(url)

        # 真实结构: <li class="fed-list-item"><a class="fed-list-pics" href="..." data-original="..."><a class="fed-list-title" href="...">标题</a></li>
        items = _re.findall(
            r'<a[^>]*class="fed-list-pics[^"]*"[^>]*href="([^"]*)"[^>]*data-original="([^"]*)"[^>]*>.*?<a[^>]*class="fed-list-title[^"]*"[^>]*>([^<]*)</a>',
            html, _re.S
        )

        video_list = []
        for href, pic, title in items[:120]:
            m = _re.search(r'/id/(\d+)/', href)
            vid = m.group(1) if m else href
            # 封面图 CDN（pic.heiimg.com 等）实测无需 Referer，纯 URL 直连，不带 @Referer
            if pic and pic.startswith("//"):
                pic = "https:" + pic
            proxy_pic = pic if pic else ""
            video_list.append({
                "vod_id": vid,
                "vod_name": title,
                "vod_pic": proxy_pic,
                "vod_remarks": "",
            })
        result["list"] = video_list
        result["page"] = page
        result["pagecount"] = page + 1 if video_list else page
        result["limit"] = 120
        result["total"] = 12000
        return result

    def detailContent(self, ids):
        result = {}
        vid = str(ids[0] if isinstance(ids, (list, tuple)) else ids or "").strip()
        if not vid:
            return result
        url = f"{self.siteUrl}/cn/home/web/index.php/vod/play/id/{vid}/sid/1/nid/1.html"
        html = self._fetch_text(url)

        # 真实结构: player_data={"url":"https:\/\/xxx.m3u8"}
        # 优先从 player_data JSON 块提取 url，避免误匹配其它 "url":"" 空字段
        m3u8_url = ""
        pd_match = _re.search(r'player_data\s*=\s*(\{.*?\})\s*;', html, _re.S)
        if pd_match:
            pd_text = pd_match.group(1)
            # 反转义 JSON 字符串里的 \/
            pd_text = pd_text.replace("\\/", "/")
            u_match = _re.search(r'"url"\s*:\s*"(https?://[^"]+)"', pd_text)
            if u_match:
                m3u8_url = u_match.group(1)
        # 兜底：全页找 m3u8 直链
        if not m3u8_url:
            fb = _re.search(r'(https?://[^"\']+\.m3u8[^"\']*)', html)
            if fb:
                m3u8_url = fb.group(1).replace("\\/", "/")

        title_match = _re.search(r'<h1[^>]*>([^<]*)</h1>', html)
        title = title_match.group(1).strip() if title_match else vid

        pic_match = _re.search(r'<meta[^>]*property=["\']og:image["\'][^>]*content=["\']([^"\']+)["\']', html)
        pic = pic_match.group(1).strip() if pic_match else ""
        if pic and pic.startswith("//"):
            pic = "https:" + pic
        # 纯 URL，不带 @Referer
        proxy_pic = pic if pic else ""

        result["list"] = [{
            "vod_id": vid,
            "vod_name": title,
            "vod_pic": proxy_pic,
            "vod_remarks": "",
            "vod_year": "",
            "vod_area": "",
            "vod_letter": "",
            "vod_class": "",
            "vod_duration": "",
            "vod_content": "",
            "vod_play_from": "高清",
            "vod_play_url": m3u8_url,
        }]
        return result

    def searchContent(self, key, quick, pg="1"):
        result = {}
        result["list"] = []
        result["page"] = pg
        result["pagecount"] = 1
        result["limit"] = 20
        result["total"] = 0
        # 源站搜索接口: /cn/home/web/index.php/vod/search/wd/{key}.html
        try:
            import urllib.parse as _up
            page = int(pg or 1)
            search_url = f"{self.siteUrl}/cn/home/web/index.php/vod/search/wd/{_up.quote(str(key or ''))}"
            if page > 1:
                search_url += f"-{page}"
            search_url += ".html"
            html = self._fetch_text(search_url)
            items = _re.findall(
                r'<a[^>]*class="fed-list-pics[^"]*"[^>]*href="([^"]*)"[^>]*data-original="([^"]*)"[^>]*>.*?<a[^>]*class="fed-list-title[^"]*"[^>]*>([^<]*)</a>',
                html, _re.S
            )
            video_list = []
            for href, pic, title in items[:50]:
                m = _re.search(r'/id/(\d+)/', href)
                vid = m.group(1) if m else href
                if pic and pic.startswith("//"):
                    pic = "https:" + pic
                proxy_pic = pic if pic else ""
                video_list.append({
                    "vod_id": vid,
                    "vod_name": title,
                    "vod_pic": proxy_pic,
                    "vod_remarks": "搜索结果",
                })
            result["list"] = video_list
            result["pagecount"] = page + 1 if video_list else page
            result["limit"] = 50
            result["total"] = len(video_list)
        except Exception:
            pass
        return result

    def playerContent(self, flag, id, vipFlags):
        # m3u8 直链播放：CDN（v.heicdn.com / *.lbsl2026.com）实测无需 Referer，
        # 带本站 Referer 反而可能被部分 CDN 识别为异源请求而拒绝。
        # 返回空 header，让播放器用默认 User-Agent 直接请求。
        result = {}
        result["parse"] = 0
        result["jx"] = 0
        result["url"] = id
        result["header"] = {}
        return result

    def localProxy(self, param):
        return [404, "text/plain", ""]

    def isVideoFormat(self, url):
        return False

    def manualVideoCheck(self):
        return False

    def getName(self):
        return "茄子精品"
