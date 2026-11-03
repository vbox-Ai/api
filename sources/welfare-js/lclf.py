#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""绿茶楼凤（lclf）— vbox 自包含适配器

协议来源：libapp.so blutter 反汇编（package:avbox/module/lclf/*）
────────────────────────────────────────────────────────────
鉴权：无。仅需 UA。
信封：{"code":200,"msg":"操作成功","data":…}

接口（全部 POST）
    api/post/feed    列表   body = JSON {"pageNo":N,"pageSize":M[,"cid":市代码]}
    api/post/top     推荐   无参
    api/post/detail  详情   ⚠ 参数走 **query string**：?postId=xxx，body 为空
                             （用 JSON body 传 postId 会 400）

资源
    图片  BASE + picture 中的每一项（逗号分隔多图）→ 200 image/jpeg
    内容  图文型（楼凤资料），无视频流；播放用多图当剧集

坑
    1) feed 必须 Content-Type: application/json，用 form 会 415
    2) detail 参数在 query 不在 body（反汇编显示其用 qp 而非 data）
    3) 无视频：vod_play_url 输出多图，客户端按图浏览
"""

import base64
import gzip
import json
import os
import re
import ssl
import sys
import time
import urllib.error
import urllib.parse
import urllib.request

try:
    from base.spider import Spider as SpiderBase
except ImportError:
    class SpiderBase(object):
        def getCache(self, key):
            return None

        def setCache(self, key, value):
            return "fail"

        def delCache(self, key):
            return "fail"


BASE_DEFAULT = "https://lclf.lol"
UA = "okhttp/3.14.9"

# 分类：(type_id, 名称, 附加参数)
CATEGORIES = [
    ("top", "推荐"),
    ("new", "最新"),
]


class LclfCore(object):
    def __init__(self, spider):
        self.sp = spider
        self.base = BASE_DEFAULT

    # ---------------- 网络 ----------------
    def _open(self, req, timeout=18):
        try:
            return urllib.request.urlopen(req, timeout=timeout)
        except Exception:
            op = urllib.request.build_opener(urllib.request.ProxyHandler({}))
            return op.open(req, timeout=timeout)

    def _req(self, path, body=None, qp=None, timeout=18):
        url = self.base.rstrip("/") + "/" + path.lstrip("/")
        if qp:
            url += "?" + urllib.parse.urlencode(qp)
        h = {"User-Agent": UA, "Accept": "application/json, text/plain, */*",
             "Content-Type": "application/json"}
        data = None
        if body is not None:
            data = json.dumps(body, ensure_ascii=False).encode("utf-8")
        elif qp is not None:
            data = b""     # detail 走 qp，需 POST 但空 body
        req = urllib.request.Request(url, data=data, headers=h, method="POST")
        try:
            with self._open(req, timeout) as r:
                raw = r.read()
        except urllib.error.HTTPError as e:
            raw = e.read()
        except Exception:
            return {}
        try:
            return json.loads(raw.decode("utf-8", "replace"))
        except Exception:
            return {}

    # ---------------- 映射 ----------------
    def _pic(self, pic_field, idx=0):
        if not pic_field:
            return ""
        parts = [p.strip() for p in str(pic_field).split(",") if p.strip()]
        if not parts:
            return ""
        p = parts[idx] if idx < len(parts) else parts[0]
        if p.startswith("http"):
            return p
        return self.base.rstrip("/") + "/" + p.lstrip("/")

    def _pics(self, pic_field):
        if not pic_field:
            return []
        out = []
        for p in str(pic_field).split(","):
            p = p.strip()
            if not p:
                continue
            out.append(p if p.startswith("http") else
                       self.base.rstrip("/") + "/" + p.lstrip("/"))
        return out

    def _item(self, it):
        remarks = []
        if it.get("price"):
            remarks.append("消费%s" % it.get("price"))
        if it.get("nightPrice"):
            remarks.append("包夜%s" % it.get("nightPrice"))
        if it.get("age"):
            remarks.append(str(it.get("age")))
        if it.get("beauty"):
            remarks.append(str(it.get("beauty")))
        if int(it.get("top") or 0) == 1:
            remarks.insert(0, "置顶")
        return {
            "vod_id": str(it.get("id")),
            "vod_name": (it.get("title") or "").strip() or "无标题",
            "vod_pic": self._pic(it.get("picture")),
            "vod_remarks": " · ".join(remarks),
            "style": {"type": "rect", "ratio": 0.75},
        }

    # ---------------- 能力 ----------------
    def categories(self):
        return [{"type_id": t, "type_name": n} for t, n in CATEGORIES]

    def list(self, tid, page):
        if str(tid) == "top":
            j = self._req("api/post/top")
            data = j.get("data") or []
            if not isinstance(data, list):
                data = []
            return [self._item(it) for it in data[:60] if it.get("id")]
        body = {"pageNo": int(page), "pageSize": 20}
        # tid 形如 city_310113 → 按市过滤
        if str(tid).startswith("city_"):
            cid = str(tid)[5:]
            if cid.isdigit():
                body["cid"] = int(cid)
        j = self._req("api/post/feed", body=body)
        data = j.get("data") or {}
        items = data.get("list") or []
        return [self._item(it) for it in items if it.get("id")]

    def detail(self, vid):
        j = self._req("api/post/detail", qp={"postId": vid})
        d = j.get("data") or {}
        if not isinstance(d, dict) or not d:
            return {}
        title = (d.get("title") or "").strip() or ("楼凤 #%s" % vid)

        meta = []
        if d.get("price"):
            meta.append("消费：%s" % d.get("price"))
        if d.get("nightPrice"):
            meta.append("包夜：%s" % d.get("nightPrice"))
        if d.get("age"):
            meta.append("年龄：%s" % d.get("age"))
        if d.get("beauty"):
            meta.append("颜值：%s" % d.get("beauty"))
        if d.get("address"):
            meta.append("地址：%s" % d.get("address"))
        if d.get("viewCount"):
            meta.append("浏览：%s" % d.get("viewCount"))
        if d.get("createdAt"):
            meta.append("发布：%s" % d.get("createdAt"))

        body = []
        if d.get("servers"):
            body.append("服务项目：" + str(d.get("servers")))
        if d.get("intro"):
            body.append(str(d.get("intro")))
        for label, k in (("QQ", "qq"), ("TG", "tg"), ("微信", "wx"),
                         ("电话", "phone"), ("与你", "yn")):
            if d.get(k):
                body.append("%s：%s" % (label, d.get(k)))

        desc = "\n".join(meta)
        if body:
            desc += "\n" + "─" * 18 + "\n" + "\n".join(body)
        desc = desc.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")

        pics = self._pics(d.get("picture"))
        play = "#".join(["图%d$%s" % (i, u) for i, u in enumerate(pics[:30], 1)])

        return {
            "vod_id": str(vid),
            "vod_name": title,
            "vod_pic": pics[0] if pics else "",
            "vod_content": desc,
            "vod_play_url": play,
            "images": pics,
        }

    def play(self, vid):
        # 图文型：单张图片直接返回
        if str(vid).startswith("http"):
            return {"parse": 0, "url": str(vid),
                    "header": {"User-Agent": UA, "Referer": self.base + "/"}}
        return None


class Spider(SpiderBase):
    MODULE = "lclf"
    NAME = "绿茶楼凤"

    def __init__(self):
        super(Spider, self).__init__()
        self.timeout = 18
        self._core = None

    def getName(self):
        return self.NAME

    def getDependence(self):
        return []

    def init(self, extend=""):
        ext = {}
        if extend:
            try:
                ext = json.loads(extend) if isinstance(extend, str) else dict(extend)
            except Exception:
                ext = {}
        self._core = LclfCore(self)
        if ext.get("host"):
            self._core.base = str(ext["host"]).rstrip("/")
        try:
            self.timeout = int(ext.get("timeout") or 18)
        except Exception:
            self.timeout = 18
        return None

    def isVideoFormat(self, url):
        low = (url or "").lower()
        return any(k in low for k in (".m3u8", ".mp4", ".flv", ".mkv", ".ts"))

    def manualVideoCheck(self):
        return False

    def destroy(self):
        pass

    def action(self, action):
        return {"msg": self.NAME}

    def liveContent(self):
        return ""

    def _c(self):
        if self._core is None:
            self._core = LclfCore(self)
        return self._core

    # ---------------- vbox 接口 ----------------
    def homeContent(self, filter):
        cls = self._c().categories()
        return {"class": cls or [{"type_id": "new", "type_name": "最新"}], "list": []}

    def homeVideoContent(self):
        try:
            items = self._c().list("top", 1)
            return {"list": items}
        except Exception:
            return {"list": []}

    def categoryContent(self, tid, pg, filter, extend):
        try:
            page = int(pg or 1)
        except Exception:
            page = 1
        try:
            r = self._c().list(str(tid), page)
        except Exception:
            r = [], 
        items = r[0] if isinstance(r, tuple) else r
        return {
            "list": items or [],
            "page": page,
            "pagecount": page + 1 if items else page,
            "limit": len(items or []),
            "total": 9999 if items else 0,
        }

    def detailContent(self, ids):
        vid = str(ids[0]) if ids else ""
        if not vid:
            return {"list": []}
        try:
            d = self._c().detail(vid)
        except Exception:
            d = {}
        if not d:
            return {"list": []}
        item = {
            "vod_id": vid,
            "vod_name": d.get("vod_name") or vid,
            "vod_pic": d.get("vod_pic", ""),
            "vod_content": d.get("vod_content", ""),
            "vod_play_from": self.NAME,
            "vod_play_url": d.get("vod_play_url", ""),
        }
        return {"list": [item]}

    def playerContent(self, flag, id, vipFlags):
        url = str(id)
        if url.startswith("http"):
            return {"parse": 0, "url": url,
                    "header": {"User-Agent": UA, "Referer": BASE_DEFAULT + "/"}}
        return {"parse": 1, "url": url, "header": {"User-Agent": UA}, "jx": 1}

    def searchContent(self, key, quick, pg="1"):
        return {"list": [], "page": 1, "pagecount": 1, "limit": 0, "total": 0}

    def localProxy(self, param):
        return [404, "text/plain; charset=utf-8", b"", {}]
