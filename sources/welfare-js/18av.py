# -*- coding: utf-8 -*-
"""
18av (密) - vbox 远程源适配版
源: 18av[密].js (TVBox JS 规则) → Python Spider 重写
站点: https://mjv012.com (18av 镜像, /zh/ 前缀)
分类: 中文字幕/有碼AV/無碼AV/素人AV/無碼破解/H動畫/國產自拍
详情页: video[data-src] 预览直链
适配: 继承 SpiderBase + super().init(extend) + localProxy三元组 + 封面走本地代理
"""
import sys
sys.path.append('..')
import re
import json
import html as html_lib
import urllib.request
import urllib.parse
from urllib.parse import quote, unquote

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
    PLATFORM_KEY = "18av_py"

    HOST = "https://mjv012.com"
    HOME_URL = "/zh/"
    UA = ("Mozilla/5.0 (iPhone; CPU iPhone OS 15_4_1 like Mac OS X) "
          "AppleWebKit/605.1.15 (KHTML, like Gecko) Version/15.4.1 Mobile/15E148 Safari/604.1")
    # ⚠️ PHPSESSID 会过期, 失效时服务器会重新颁发 (保留 YES_Eighteen 年龄声明)
    COOKIE = "YES_Eighteen=IamOverEighteenYearsOld;PHPSESSID=ti945stmtto483t5t6ur8nj0t1"

    # 分类名称与路径片段 (对应 JS 规则 class_name / class_url)
    CLASSES = [
        ("chinese_list", "中文字幕"),
        ("censored_list", "有碼AV"),
        ("uncensored_list", "無碼AV"),
        ("amateurjav_list", "素人AV"),
        ("reducing-mosaic_list", "無碼破解"),
        ("animation_list", "H動畫"),
        ("dt_list", "國產自拍"),
    ]

    def __init__(self):
        try:
            super(Spider, self).__init__()
        except Exception:
            pass
        self.headers = {
            "User-Agent": self.UA,
            "Accept": "*/*",
            "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
            "Cookie": self.COOKIE,
        }

    def init(self, extend=""):
        try:
            super().init(extend)
        except AttributeError:
            pass
        # 支持 extend 覆盖 host
        if isinstance(extend, dict):
            h = str(extend.get("host") or "").strip()
            if h.startswith("http"):
                self.HOST = h.rstrip("/")
        elif extend:
            h = str(extend).strip()
            if h.startswith("http"):
                self.HOST = h.rstrip("/")
        return True

    def getName(self):
        return "18av"

    def isVideoFormat(self, url):
        low = (url or "").lower()
        return any(k in low for k in (".m3u8", ".mp4", ".flv", ".mkv", ".webm"))

    def manualVideoCheck(self):
        return False

    def destroy(self):
        pass

    # ================= HTTP =================
    def _fetch(self, path, timeout=15):
        url = self.HOST + path if path.startswith("/") else path
        req = urllib.request.Request(url, headers=self.headers)
        try:
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                raw = resp.read()
                try:
                    return raw.decode("utf-8")
                except Exception:
                    return raw.decode("big5", errors="ignore")
        except Exception:
            return ""

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
            headers = dict(self.headers)
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

    # ================= 卡片解析 (.post) =================
    def _parse_posts(self, html_text):
        items = []
        seen = set()
        chunks = re.split(r'<div[^>]*class="post"', html_text or "")
        for ch in chunks[1:]:
            ch = ch[:4000]
            a = re.search(r'<h3>\s*<a[^>]*href="([^"]+)"[^>]*>(.*?)</a>', ch, re.S)
            if not a:
                a = re.search(r'<h3[^>]*>\s*<a[^>]*href="([^"]+)"[^>]*>(.*?)</a>', ch, re.S)
            if not a:
                continue
            href = a.group(1).strip()
            if href.startswith("//"):
                href = "https:" + href
            elif href.startswith("/"):
                href = self.HOST + href
            vid = unquote(href)
            if vid in seen:
                continue
            seen.add(vid)

            title = html_lib.unescape(re.sub(r'<[^>]+>', '', a.group(2))).strip()
            if not title:
                tm = re.search(r'<h3[^>]*title="([^"]+)"', ch)
                title = html_lib.unescape(tm.group(1)).strip() if tm else ""

            img = ""
            im = re.search(r'<img[^>]+(?:data-src|src)="([^"]+)"', ch, re.I)
            if im:
                img = im.group(1).strip()
                if img.startswith("//"):
                    img = "https:" + img
                elif img.startswith("/"):
                    img = self.HOST + img

            meta = ""
            mm = re.search(r'class="meta"[^>]*>(.*?)</', ch, re.S)
            if mm:
                meta = html_lib.unescape(re.sub(r'<[^>]+>', ' ', mm.group(1))).strip()

            items.append({
                "vod_id": vid,
                "vod_name": title or vid,
                "vod_pic": self._proxy_img_url(img, referer=self.HOST + self.HOME_URL) if img else "",
                "vod_remarks": meta[:40] if meta else "",
            })
        return items

    # ================= 标准接口 =================
    def homeContent(self, filter):
        classes = [{"type_id": slug, "type_name": name} for slug, name in self.CLASSES]
        if not classes:
            classes = [{"type_id": "chinese_list", "type_name": "18av·全部"}]
        result = {"class": classes}
        if filter:
            result["filters"] = {}
        return result

    def homeVideoContent(self):
        html_text = self._fetch(self.HOME_URL + "chinese_list/all/1.html")
        return {"list": self._parse_posts(html_text)[:24]}

    def categoryContent(self, tid, pg, filter, extend):
        page = int(pg) if str(pg).isdigit() else 1
        slug = str(tid).strip()
        # 校验 slug 在分类表内, 未知 slug 回落到第一个
        valid = [s for s, _ in self.CLASSES]
        if slug not in valid:
            slug = valid[0] if valid else "chinese_list"
        path = "/zh/%s/all/%d.html" % (slug, page)
        html_text = self._fetch(path)
        items = self._parse_posts(html_text)
        return {
            "list": items,
            "page": page,
            "pagecount": page + 1 if len(items) >= 20 else page,
            "limit": len(items),
            "total": 9999 if len(items) >= 20 else len(items),
        }

    def detailContent(self, ids):
        vid = ids[0] if isinstance(ids, (list, tuple)) else str(ids)
        url = vid if vid.startswith("http") else self.HOST + vid
        html_text = self._fetch(url, timeout=15)

        # 标题
        title_m = re.search(r'<title>([^<]+)</title>', html_text or "", re.S)
        title = html_lib.unescape(title_m.group(1)).strip() if title_m else ""

        # 封面
        pic_m = re.search(r'<meta[^>]+property="og:image"[^>]+content="([^"]+)"', html_text or "", re.I)
        pic = ""
        if pic_m:
            pic = pic_m.group(1).strip()
            if pic.startswith("//"):
                pic = "https:" + pic
            elif pic.startswith("/"):
                pic = self.HOST + pic

        # 描述
        desc_m = re.search(r'<meta[^>]+name="description"[^>]+content="([^"]+)"', html_text or "", re.I)
        desc = html_lib.unescape(desc_m.group(1)).strip() if desc_m else ""

        # 预览视频 video[data-src]
        play_urls = []
        play_froms = []
        for i, m in enumerate(re.finditer(r'<video[^>]+data-src="([^"]+)"', html_text or "")):
            src = m.group(1).strip()
            if src.startswith("//"):
                src = "https:" + src
            elif src.startswith("/"):
                src = self.HOST + src
            if src.startswith("http"):
                play_urls.append(src)
                play_froms.append("预览%d" % (i + 1))

        vod = {
            "vod_id": vid,
            "vod_name": title or vid,
            "vod_pic": self._proxy_img_url(pic, referer=url) if pic else "",
            "vod_remarks": "",
            "vod_content": desc,
            "vod_play_from": "$$$".join(play_froms) if play_froms else "",
            "vod_play_url": "$$$".join(play_urls) if play_urls else "",
        }
        return {"list": [vod]}

    def searchContent(self, key, quick, pg="1"):
        page = int(pg) if str(pg).isdigit() else 1
        kw = quote(str(key or "").strip())
        path = "/zh/fc_search/all/%s/%d.html" % (kw, page)
        html_text = self._fetch(path)
        items = self._parse_posts(html_text)
        return {
            "list": items,
            "page": page,
            "pagecount": page + 1 if len(items) >= 20 else page,
            "limit": len(items),
            "total": len(items),
        }

    def playerContent(self, flag, id, vipFlags):
        return {
            "parse": 0,
            "jx": 0,
            "url": id,
            "header": {
                "User-Agent": self.UA,
                "Referer": self.HOST + self.HOME_URL,
                "Cookie": self.COOKIE,
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
        u = unquote(str(p.get("u") or p.get("url") or ""))
        r = unquote(str(p.get("r") or "")) or None
        if t == "img" and u:
            return self._serve_img(u, referer=r)
        return [404, "text/plain", b""]
