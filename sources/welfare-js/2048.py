#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
2048成人短剧 (麻豆传媒) - vbox 远程源适配版
站点: https://mdcmai4.xyz (REST API + m3u8/image proxy 接口)
特性: 普通长视频全分类 + AI短剧专区(全集独立播放流精准选集)
适配: 继承 SpiderBase + super().init(extend) + localProxy三元组 + 封面走本地代理
"""
import sys
sys.path.append('..')
import json
import urllib.parse
import urllib.request
from typing import Dict, List, Any

try:
    import requests
    HAS_REQUESTS = True
except ImportError:
    HAS_REQUESTS = False

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
    PLATFORM_KEY = "2048_py"

    siteUrl = "https://mdcmai4.xyz"
    api_categories = "/api/v1/categories?type=video"
    api_videos = "/api/v1/videos"
    api_short_dramas = "/api/v1/short-dramas"
    api_short_drama_detail = "/api/v1/short-dramas/{id}?productId=1"
    api_search = "/api/v1/videos/search"
    api_m3u8_proxy = "/api/v1/m3u8/proxy?path="
    api_img_proxy = "/api/v1/image/proxy?path="

    SHORT_DRAMA_TID = "short_drama_ai"

    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
        "Referer": "https://mdcmai4.xyz/",
        "Origin": "https://mdcmai4.xyz",
        "Accept": "application/json, text/plain, */*",
    }

    def __init__(self):
        try:
            super(Spider, self).__init__()
        except Exception:
            pass

    def getName(self) -> str:
        return "麻豆传媒🔞TG群：@tvshare23"

    def init(self, extend: str = "") -> bool:
        try:
            super().init(extend)
        except AttributeError:
            pass
        return True

    def isVideoFormat(self, url: str) -> bool:
        low = (url or '').lower()
        return '.m3u8' in low or '.mp4' in low

    def manualVideoCheck(self) -> bool:
        return False

    def destroy(self):
        pass

    # ───── 本地代理 ─────
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
        u = base + sep + "type=img&u=" + urllib.parse.quote(str(url), safe="")
        if referer:
            u += "&r=" + urllib.parse.quote(referer, safe="")
        return u

    def _serve_img(self, url, referer=None):
        try:
            headers = dict(self.headers)
            if referer:
                headers["Referer"] = referer
            ct = "image/jpeg"
            if HAS_REQUESTS:
                resp = requests.get(url, headers=headers, timeout=15, verify=False)
                if resp.status_code != 200:
                    return [502, "text/plain", b"upstream %s" % resp.status_code]
                raw = resp.content
                ct = (resp.headers.get("Content-Type") or ct).split(";")[0].strip()
            else:
                req = urllib.request.Request(url, headers=headers)
                with urllib.request.urlopen(req, timeout=15) as r:
                    raw = r.read()
                    ct = (r.headers.get("Content-Type") or ct).split(";")[0].strip()
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

    # ───── 网络请求封装 ─────
    def _fetch_json(self, url: str) -> Dict[str, Any]:
        try:
            if HAS_REQUESTS:
                resp = requests.get(url, headers=self.headers, timeout=10, verify=False)
                if resp.status_code == 200:
                    return resp.json()
            else:
                req = urllib.request.Request(url, headers=self.headers)
                with urllib.request.urlopen(req, timeout=10) as response:
                    return json.loads(response.read().decode("utf-8"))
        except Exception:
            pass
        return {}

    # ───── URL 规范化组装 ─────
    def _format_cover(self, cover_path: str) -> str:
        """格式化封面图片地址 + 本地代理包装"""
        if not cover_path:
            return ""
        if cover_path.startswith("http"):
            return self._proxy_img_url(cover_path, referer=self.siteUrl + "/")
        if cover_path.startswith("/uploads/") or cover_path.startswith("/api/"):
            url = f"{self.siteUrl}{cover_path}"
            return self._proxy_img_url(url, referer=self.siteUrl + "/")
        encoded_path = urllib.parse.quote(cover_path, safe="")
        url = f"{self.siteUrl}{self.api_img_proxy}{encoded_path}"
        return self._proxy_img_url(url, referer=self.siteUrl + "/")

    def _format_play_url(self, video_path: str) -> str:
        if not video_path:
            return ""
        if video_path.startswith("http"):
            return video_path
        if video_path.startswith("/api/v1/m3u8/proxy"):
            return f"{self.siteUrl}{video_path}"
        encoded_path = urllib.parse.quote(video_path, safe="")
        return f"{self.siteUrl}{self.api_m3u8_proxy}{encoded_path}"

    def _format_duration(self, seconds: int) -> str:
        if not seconds:
            return ""
        m, s = divmod(int(seconds), 60)
        h, m = divmod(m, 60)
        if h > 0:
            return f"{h:02d}:{m:02d}:{s:02d}"
        return f"{m:02d}:{s:02d}"

    # ───── TVBox/vbox 核心接口 ─────
    def homeContent(self, filter: bool = False) -> Dict[str, Any]:
        classes = [
            {"type_id": self.SHORT_DRAMA_TID, "type_name": "🔥 AI短剧"}
        ]

        url = f"{self.siteUrl}{self.api_categories}"
        res = self._fetch_json(url)

        if res.get("code") == 200 and isinstance(res.get("data"), list):
            for cat in res["data"]:
                if cat.get("enabled", True):
                    classes.append({
                        "type_id": str(cat.get("id")),
                        "type_name": cat.get("name", "未知分类")
                    })

        if len(classes) == 1:
            classes.append({"type_id": "all", "type_name": "麻豆·全部"})

        return {"class": classes}

    def categoryContent(self, tid: str, pg: str, filter: bool, extend: Dict) -> Dict[str, Any]:
        page = int(pg) if pg else 1
        videos = []
        pagecount = page
        total = 0

        if str(tid) == self.SHORT_DRAMA_TID:
            url = f"{self.siteUrl}{self.api_short_dramas}?productId=1&sortBy=heat&page={page}&size=12"
            res = self._fetch_json(url)
            if res.get("code") == 200:
                data = res.get("data", {})
                pagecount = data.get("totalPages", page)
                total = data.get("total", 0)

                for item in data.get("items", []):
                    ep_cnt = item.get("episodeCount", 1)
                    rating = item.get("rating", 0.0)
                    videos.append({
                        "vod_id": f"drama@@{item.get('id')}@@{item.get('title', '')}@@{item.get('coverUrl', '')}",
                        "vod_name": item.get("title", ""),
                        "vod_pic": self._format_cover(item.get("coverUrl", "")),
                        "vod_remarks": f"评分:{rating} | 共{ep_cnt}集"
                    })
        else:
            url = f"{self.siteUrl}{self.api_videos}?page={page}&size=24&categoryId={tid}"
            res = self._fetch_json(url)
            if res.get("code") == 200:
                data = res.get("data", {})
                pagecount = data.get("totalPages", page)
                total = data.get("total", 0)

                for item in data.get("items", []):
                    v_url = item.get("videoUrl", "")
                    videos.append({
                        "vod_id": f"video@@{item.get('id')}@@{v_url}@@{item.get('title', '')}@@{item.get('coverUrl', '')}",
                        "vod_name": item.get("title", ""),
                        "vod_pic": self._format_cover(item.get("coverUrl", "")),
                        "vod_remarks": self._format_duration(item.get("durationSec", 0)) or item.get("categoryName", "")
                    })

        return {
            "list": videos,
            "page": page,
            "pagecount": pagecount,
            "limit": 12 if str(tid) == self.SHORT_DRAMA_TID else 24,
            "total": total
        }

    def detailContent(self, ids: List[str]) -> Dict[str, Any]:
        vod_id = ids[0]

        if "@@" in vod_id:
            parts = vod_id.split("@@")
            vtype = parts[0]

            if vtype == "drama":
                drama_id = parts[1]
                title = parts[2] if len(parts) > 2 else "短剧详情"
                cover = parts[3] if len(parts) > 3 else ""

                detail_url = f"{self.siteUrl}{self.api_short_drama_detail.format(id=drama_id)}"
                res = self._fetch_json(detail_url)

                episodes = []
                if res.get("code") == 200 and isinstance(res.get("data"), dict):
                    drama_data = res["data"]
                    title = drama_data.get("title", title)
                    cover = drama_data.get("coverUrl", cover)

                    for ep in drama_data.get("episodes", []):
                        ep_no = ep.get("episodeNo", 1)
                        ep_title = f"第{ep_no}集"
                        raw_vurl = ep.get("videoUrl", "")
                        if raw_vurl:
                            play_stream = self._format_play_url(raw_vurl)
                            episodes.append(f"{ep_title}${play_stream}")

                play_url_str = "#".join(episodes) if episodes else "暂无分集数据$error"
                from_name = "AI短剧专线"
            else:
                video_url = parts[2] if len(parts) > 2 else ""
                title = parts[3] if len(parts) > 3 else "视频详情"
                cover = parts[4] if len(parts) > 4 else ""
                play_stream = self._format_play_url(video_url)
                play_url_str = f"正片${play_stream}" if play_stream else "暂无播放地址$error"
                from_name = "专线播放"
        else:
            title = "在线播放"
            cover = ""
            from_name = "专线播放"
            play_url_str = "暂无播放地址$error"

        return {
            "list": [{
                "vod_id": vod_id,
                "vod_name": title,
                "vod_pic": self._format_cover(cover) if cover else "",
                "vod_play_from": from_name,
                "vod_play_url": play_url_str
            }]
        }

    def searchContent(self, key: str, quick: str, pg="1") -> Dict[str, Any]:
        page = int(pg) if pg else 1
        encoded_kw = urllib.parse.quote(key)
        url = f"{self.siteUrl}{self.api_search}?page={page}&size=24&q={encoded_kw}"
        res = self._fetch_json(url)

        videos = []
        if res.get("code") == 200:
            data = res.get("data", {})
            for item in data.get("items", []):
                v_url = item.get("videoUrl", "")
                videos.append({
                    "vod_id": f"video@@{item.get('id')}@@{v_url}@@{item.get('title', '')}@@{item.get('coverUrl', '')}",
                    "vod_name": item.get("title", ""),
                    "vod_pic": self._format_cover(item.get("coverUrl", "")),
                    "vod_remarks": self._format_duration(item.get("durationSec", 0)) or item.get("categoryName", "")
                })

        return {"list": videos}

    def playerContent(self, flag: str, id: str, vipFlags: str) -> Dict[str, Any]:
        return {
            "parse": 0,
            "playUrl": "",
            "url": id,
            "header": {
                "User-Agent": self.headers["User-Agent"],
                "Referer": "https://mdcmai4.xyz/",
                "Origin": "https://mdcmai4.xyz"
            }
        }

    def localProxy(self, param) -> List[Any]:
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
