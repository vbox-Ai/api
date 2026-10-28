# -*- coding: utf-8 -*-
"""
漫蛙漫画（暮色 mw 平台）— vbox 福利区 Python 蜘蛛
================================================================
来源：暮色 plist 导出 flutter.mw = https://manwaqr.cc/
链路（纯 HTML 明文，无需解密，实测通过）：
  首页     GET /                        → 漫画列表 + 分类标签
  分类     GET /booklist?tag={tag}      → 分类漫画列表
  详情     GET /book/{id}               → 章节列表 /chapter/{chapterId}
  章节     GET /chapter/{id}            → 正文图 data-r-src=".../upload3/book/id/{bookId}/{chapterId}/xxx.webp"
  搜索     GET /search/?keyword={k}     → 搜索结果

HTML 关键结构（实测）：
  漫画卡片: <a href="/book/545872" title="成为我的作品吧"> ... <img data-home-src="...cover_1.webp">
  分类导航: <a href="/booklist?tag=悬疑">
  章节列表: <a href="/chapter/31512927" title="EP1 你怎么有反应">
  章节正文: <img data-r-src=".../upload3/book/id/545872/31512927/xxx_zb.webp">

vbox 适配：
  - 继承 base.spider.Spider，用 self.fetch（自动 SSL 绕过/域名注入/代理）
  - 漫画图片用 manga:// 协议返回，vbox WelfareResultMapper 自动解析
"""
import sys
import json
import re

sys.path.append('..')
try:
    from base.spider import Spider as _Spider
except Exception:
    class _Spider(object):
        def fetch(self, url, **kw):
            import urllib.request
            return urllib.request.urlopen(url).read().decode('utf-8', 'replace')

HOST = "https://manwaqr.cc"
IMG_HOST = "https://mwfimsvfast40.cc"


def _abs(url, host=HOST):
    if url.startswith("http"):
        return url
    return host + url


class Spider(_Spider):
    def __init__(self):
        super(Spider, self).__init__()
        self.host = HOST
        self.img_host = IMG_HOST

    def getName(self):
        return "漫蛙漫画"

    def getDependence(self):
        return []

    def init(self, extend=""):
        try:
            ext = json.loads(extend) if extend else {}
            if ext.get("host"):
                self.host = str(ext["host"]).rstrip("/")
        except Exception:
            pass

    def isVideoFormat(self, url):
        return False

    # ---------- 解析工具 ----------
    def _cards(self, html):
        """解析漫画卡片：<a href="/book/{id}" title="{name}"> ... <img data-{home-src|original|src}="{cover}">"""
        out = []
        pat = re.compile(
            r'<a href="(/book/\d+)"[^>]*title="([^"]+)"[^>]*>(.*?)</a>',
            re.S
        )
        seen = set()
        for m in pat.finditer(html):
            path, name, inner = m.group(1), m.group(2).strip(), m.group(3)
            if path in seen:
                continue
            seen.add(path)
            c = re.search(r'data-(?:home-src|original|src)="([^"]+)"', inner)
            cover = c.group(1) if c else ""
            if not cover or "/upload" not in cover:
                continue
            out.append({
                "vod_id": path,
                "vod_name": name,
                "vod_pic": cover,
            })
        return out

    # ---------- vbox 接口 ----------
    def homeContent(self, filter):
        try:
            html = self.fetch(self.host + "/").text
        except Exception:
            html = ""
        # 分类标签：/booklist?tag=xxx
        tags = list(dict.fromkeys(re.findall(r'href="/booklist\?tag=([^"]+)"', html)))
        classes = [{"type_id": t, "type_name": t} for t in tags[:30]]
        result = {"class": classes, "list": self._cards(html)}
        if filter:
            result["filters"] = {t: [] for t in tags[:30]}
        return result

    def homeVideoContent(self):
        try:
            html = self.fetch(self.host + "/").text
            return {"list": self._cards(html)}
        except Exception:
            return {"list": []}

    def categoryContent(self, tid, pg, filter, extend):
        page = int(pg or 1)
        url = "%s/booklist?tag=%s&page=%d" % (self.host, tid, page)
        try:
            html = self.fetch(url).text
            cards = self._cards(html)
        except Exception:
            cards = []
        return {"list": cards, "page": page, "pagecount": page + 1,
                "limit": len(cards), "total": 9999}

    def detailContent(self, ids):
        vid = ids[0] if ids else ""
        url = _abs(vid)
        name = ""
        pic = ""
        play_url = ""
        try:
            html = self.fetch(url).text
            t = re.search(r'<title>([^<]+)', html)
            if t:
                name = t.group(1).replace("-漫蛙漫画", "").strip()
            c = re.search(r'data-(?:home-src|original|src)="(https://[^"]+cover[^"]+)"', html)
            if c:
                pic = c.group(1)
            # 章节列表（去重保序）
            chs = list(dict.fromkeys(re.findall(r'<a href="(/chapter/\d+)"[^>]*title="([^"]+)"', html)))
            if chs:
                play_url = "#".join("%s$%s" % (n, _abs(u)) for u, n in chs)
        except Exception:
            pass
        if not play_url:
            return {"list": []}
        return {"list": [{
            "vod_id": vid,
            "vod_name": name or vid,
            "vod_pic": pic,
            "vod_play_from": "漫蛙",
            "vod_play_url": play_url,
        }]}

    def searchContent(self, key, quick, pg="1"):
        url = "%s/search/?keyword=%s&page=%s" % (self.host, key, pg or "1")
        try:
            html = self.fetch(url).text
            cards = self._cards(html)
        except Exception:
            cards = []
        return {"list": cards, "page": int(pg or 1),
                "pagecount": int(pg or 1) + 1, "limit": len(cards), "total": len(cards)}

    def playerContent(self, flag, id, vipFlags):
        """解析章节页正文图，返回 manga:// 协议"""
        url = _abs(id)
        try:
            html = self.fetch(url).text
            # 正文图特征：data-r-src=".../upload3/book/id/{bookId}/{chapterId}/xxx.webp"
            imgs = [u for u in re.findall(r'data-r-src="(https://[^"]+)"', html)
                    if "/upload3/book/id/" in u and "/ads/" not in u]
            if not imgs:
                imgs = list(dict.fromkeys(
                    re.findall(r'(https://[^"\'\s]+/upload3/book/id/[^"\'\s]+\.(?:webp|jpg|jpeg|png))', html)
                ))
            if imgs:
                return {"parse": 0, "url": "manga://" + "&&".join(imgs)}
        except Exception:
            pass
        return {"parse": 0, "url": ""}
