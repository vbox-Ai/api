#!/usr/bin/python
# coding=utf-8
"""
AcFan TVBox Spider — vbox 适配版
站点: acf.f76typd0.work

vbox 适配：
1. requests.Session → 继承基类 self.fetch
2. playerContent header → dict 格式
3. 继承 base.spider.Spider

注意：图片使用站点自己的 media-proxy（/media-proxy?url=），不使用 localProxy
"""
import sys, re, json
from urllib.parse import quote, unquote

sys.path.append('..')
try:
    from base.spider import Spider as _B
except Exception:
    class _B:
        pass
try:
    import requests
except ImportError:
    requests = None

HOST = "https://acf.f76typd0.work"
UA = "Mozilla/5.0 (Linux; Android 12; SM-G9750 Build/SP1A.210812.016; wv) AppleWebKit/537.36 (KHTML, like Gecko) Version/4.0 Chrome/89.0.4389.72 MQQBrowser/6.2 TBS/046279 Mobile Safari/537.36"

CAT_PATH = {
    "guochan": "GC/2075051039321464834",
    "rifan": "3/2072212947517390849",
    "pao": "ITEM_LI9_TWI_N6Y/2072654840359600130",
    "motion": "MOTION_ANIME/2072654931050029058",
    "dcg": "2/2072212891277045761",
    "twofived": "2_5D/2072655042194890753",
    "twod": "2D/2072655119809298434",
    "aigen": "AI/2072655204107608066",
    "mmd": "MMD/2072655243595792385",
    "cosplay": "COSPLAY/2075576278568513538",
}

CLASS_LIST = [
    {"type_name": "国产动漫", "type_id": "guochan"},
    {"type_name": "里番", "type_id": "rifan"},
    {"type_name": "泡面番", "type_id": "pao"},
    {"type_name": "Motion Anime", "type_id": "motion"},
    {"type_name": "3DCG", "type_id": "dcg"},
    {"type_name": "2.5D", "type_id": "twofived"},
    {"type_name": "2D动画", "type_id": "twod"},
    {"type_name": "AI生成", "type_id": "aigen"},
    {"type_name": "MMD", "type_id": "mmd"},
    {"type_name": "Cosplay", "type_id": "cosplay"},
]

DEFAULT_PIC = HOST + "/images/default-cover.svg"


class Spider(_B):
    headers = {
        "User-Agent": UA,
        "Referer": HOST + "/",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "zh-CN,zh;q=0.9"
    }

    def getName(self):
        return "AcFan"

    def init(self, extend=""):
        pass

    def isVideoFormat(self, url):
        if not url:
            return False
        return any(url.lower().endswith(ext) for ext in [".m3u8", ".mp4", ".avi", ".flv", ".mkv", ".ts"]) or "m3u8" in url.lower()

    def manualVideoCheck(self):
        return False

    def destroy(self):
        return "success"

    def action(self, action):
        pass

    # ============================================================
    # 辅助: 请求
    # ============================================================
    def fetch(self, url):
        for _ in range(3):
            try:
                r = self._B_fetch(url, headers=self.headers, timeout=10) if hasattr(self, '_B_fetch') else None
                if r is None:
                    import requests as _req
                    r = _req.get(url, headers=self.headers, timeout=10, verify=False)
                return r.text or ""
            except Exception:
                try:
                    import requests as _req
                    r = _req.get(url, headers=self.headers, timeout=10, verify=False)
                    return r.text or ""
                except Exception:
                    pass
        return ""

    def _abs_url(self, url):
        url = (url or "").strip().replace("\\/", "/")
        if not url:
            return ""
        if url.startswith("//"):
            return "https:" + url
        if url.startswith("http"):
            return url
        if url.startswith("/"):
            return HOST + url
        return url

    # 站点自己的 media-proxy（不使用 localProxy）
    def proxy_img(self, url):
        if not url or not url.startswith("http") or "127.0.0.1" in url or "/media-proxy" in url:
            return url
        return HOST + "/media-proxy?url=" + quote(url, safe="")

    @staticmethod
    def _match(text, pat):
        m = re.search(pat, text or "", re.I)
        return m.group(1) if m else ""

    @staticmethod
    def _clean(text):
        text = re.sub(r"<[^>]+>", " ", text or "")
        text = re.sub(r"\s+", " ", text)
        return text.strip()

    # ============================================================
    # 1. 首页
    # ============================================================
    def homeContent(self, filter):
        data = []
        try:
            html = self.fetch(HOST + "/")
            data = self.parseList(html)
        except Exception:
            pass
        return {"class": CLASS_LIST, "list": data}

    def homeVideoContent(self):
        try:
            html = self.fetch(HOST + "/")
            return {"list": self.parseList(html)[:24]}
        except Exception:
            return {"list": []}

    # ============================================================
    # 2. 分类列表
    # ============================================================
    def categoryContent(self, tid, pg, filter, extend):
        page = int(pg) if pg and str(pg).isdigit() else 1
        path = CAT_PATH.get(tid, "")
        if not path:
            return {"page": page, "pagecount": 1, "limit": 24, "total": 0, "list": []}
        if page > 1:
            url = HOST + "/category/" + path + "/page/" + str(page)
        else:
            url = HOST + "/category/" + path
        html = self.fetch(url)
        pages = [int(p) for p in re.findall(r"/category/[^\"']+/page/(\d+)", html)]
        pc = max(pages) if pages else 1
        data = self.parseList(html)
        return {"page": page, "pagecount": pc, "limit": 24, "total": pc * 24, "list": data}

    # ============================================================
    # 3. 详情页
    # ============================================================
    def detailContent(self, ids):
        sid = ids[0] if ids else ""
        ps = sid.split("@@@")
        vid = ps[0] if len(ps) > 0 else sid
        play = ps[1] if len(ps) > 1 else ""
        name = unquote(ps[2]) if len(ps) > 2 else vid
        pic = unquote(ps[3]) if len(ps) > 3 else ""
        if play:
            return {"list": [{
                "vod_id": sid, "vod_name": name, "vod_pic": self.proxy_img(pic),
                "vod_content": name, "vod_play_from": "AcFan",
                "vod_play_url": "播放$" + play
            }]}
        html = self.fetch(HOST + "/watch/" + vid)
        vod_name, vod_pic, vod_content, m3u8, cat_name = vid, "", "", "", ""
        for jm in re.finditer(r'<script[^>]*type="application/ld\+json"[^>]*>(.*?)</script>', html, re.S):
            try:
                data = json.loads(jm.group(1))
                if isinstance(data, list):
                    for item in data:
                        t = item.get("@type", "")
                        if t == "VideoObject":
                            vod_name = item.get("name", vod_name)
                            vod_content = item.get("description", "")
                            vod_pic = item.get("thumbnailUrl", "")
                            m3u8 = item.get("contentUrl", "")
                        elif t == "BreadcrumbList":
                            els = item.get("itemListElement", [])
                            if len(els) >= 2:
                                cat_name = els[1].get("name", "")
            except Exception:
                pass
        if not vod_pic:
            og = re.search(r'property="og:image"[^>]*content="([^"]*)"', html)
            vod_pic = og.group(1) if og else ""
        if vod_name == vid:
            tm = re.search(r"<title>(.*?)</title>", html)
            vod_name = tm.group(1).replace(" - AcFan", "").strip() if tm else vid
        tags = list(dict.fromkeys(re.findall(r'href="/search\?tag=([^"]*)"', html)))
        tag_text = " ".join(unquote(t) for t in tags)
        vod_content = (vod_content + "\n" + tag_text).strip() if vod_content else tag_text
        if cat_name:
            vod_content = "分类: " + cat_name + "\n" + vod_content
        play_url = ("播放$" + m3u8) if m3u8 else ""
        return {"list": [{
            "vod_id": sid, "vod_name": vod_name, "vod_pic": self.proxy_img(vod_pic),
            "vod_content": vod_content, "vod_play_from": "AcFan",
            "vod_play_url": play_url
        }]}

    # ============================================================
    # 4. 搜索
    # ============================================================
    def searchContent(self, key, quick, pg="1"):
        page = int(pg) if str(pg).isdigit() else 1
        wd = quote(key)
        html = self.fetch(HOST + "/search?q=" + wd + "&page=" + str(page))
        pages = [int(p) for p in re.findall(r"/search\?page=(\d+)", html)]
        pc = max(pages) if pages else 1
        return {"list": self.parseList(html), "page": page, "pagecount": pc, "limit": 24, "total": pc * 24}

    # ============================================================
    # 5. 播放接口
    # ============================================================
    def playerContent(self, flag, id, vipFlags):
        sid = id or ""
        ps = sid.split("@@@")
        url = ps[1] if len(ps) > 1 else sid
        if self.isVideoFormat(url):
            return {"parse": 0, "url": url, "header": self.headers}
        html = self.fetch(HOST + "/watch/" + ps[0])
        m3u8 = ""
        for jm in re.finditer(r'<script[^>]*type="application/ld\+json"[^>]*>(.*?)</script>', html, re.S):
            try:
                data = json.loads(jm.group(1))
                if isinstance(data, list):
                    for item in data:
                        if item.get("@type") == "VideoObject":
                            m3u8 = item.get("contentUrl", "")
                            break
            except Exception:
                pass
        if m3u8:
            return {"parse": 0, "url": m3u8, "header": self.headers}
        return {"parse": 1, "url": url, "header": self.headers}

    def localProxy(self, param):
        return [200, "text/plain", b""]

    # ============================================================
    # 辅助: 列表解析
    # ============================================================
    def parseList(self, html):
        res = []
        if not html:
            return res
        cover_map = self.getCoverMap(html)
        seen = set()
        for m in re.finditer(r'href="/watch/(CNT\d+)"', html):
            vid = m.group(1)
            if vid in seen:
                continue
            seen.add(vid)
            block = html[m.start():m.start() + 6000]
            name = self._match(block, r'<img[^>]*alt="([^"]*)"') or vid
            duration = self._match(block, r'>(\d{1,3}:\d{2}(?::\d{2})?)</span>') or ""
            pic = cover_map.get(vid, DEFAULT_PIC)
            sid = vid + "@@@" + "" + "@@@" + quote(name) + "@@@" + quote(pic)
            res.append({
                "vod_id": sid,
                "vod_name": self._clean(name),
                "vod_pic": self.proxy_img(pic),
                "vod_remarks": self._clean(duration) if duration else ""
            })
        if not res:
            res = self.parseListFromPush(html)
        return res

    def getCoverMap(self, html):
        m = {}
        if not html:
            return m
        try:
            for cm in re.finditer(r'coverUrl', html):
                pos = cm.end()
                rest = html[pos:pos + 200]
                um = re.search(r'https?://[^\s"\\]+', rest)
                if not um:
                    continue
                cover = um.group(0)
                back = html[max(0, cm.start() - 300):cm.start()]
                im = re.findall(r'CNT\d+', back)
                if not im:
                    continue
                vid = im[-1]
                if vid not in m:
                    m[vid] = cover
        except Exception:
            pass
        return m

    def parseListFromPush(self, html):
        res = []
        if not html:
            return res
        try:
            seen = set()
            for cm in re.finditer(r'coverUrl', html):
                pos = cm.end()
                rest = html[pos:pos + 200]
                um = re.search(r'https?://[^\s"\\]+', rest)
                if not um:
                    continue
                cover = um.group(0)
                back = html[max(0, cm.start() - 300):cm.start()]
                ids = re.findall(r'CNT\d+', back)
                if not ids:
                    continue
                vid = ids[-1]
                if vid in seen:
                    continue
                seen.add(vid)
                tm = re.search(r'title[^h]*([^\s"\\]{2,})', back)
                name = tm.group(1) if tm else vid
                sid = vid + "@@@" + "" + "@@@" + quote(name) + "@@@" + quote(cover)
                res.append({
                    "vod_id": sid,
                    "vod_name": self._clean(name),
                    "vod_pic": self.proxy_img(cover),
                    "vod_remarks": ""
                })
        except Exception:
            pass
        return res
