# -*- coding: utf-8 -*-
"""从 muse_avbox.py 抽取指定 Adapter，生成 vbox 自包含单平台适配器。

用法：python tools/_gen_standalone.py hdb mmav rryy one
产物：sources/welfare-js/<key>.py
"""
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MUSE = os.path.join(ROOT, "sources", "welfare-js", "muse_avbox.py")
OUTD = os.path.join(ROOT, "sources", "welfare-js")

SRC = open(MUSE, encoding="utf-8").read()


def between(start, end, frm=0):
    i = SRC.index(start, frm)
    j = SRC.index(end, i)
    return SRC[i:j]


def spider_init_seg():
    """精确取 muse Spider.__init__（避免误命中 HostResolver.__init__）。"""
    anchor = SRC.index("        super(Spider, self).__init__()")
    i = SRC.rindex("    def __init__(self):", 0, anchor)
    j = SRC.index("    # ---------------- 基类接口", i)
    return SRC[i:j]


# ---------- 公共片段
UA_SEG = between("UA_IOS = (", "# 平台目录快照")
PH_SEG = between("PLATFORM_HOSTS = {", "\n}\n") + "\n}\n"
MH_SEG = between("MEDIA_HOSTS = {", "\n}\n") + "\n}\n"
BASE_SEG = between("class BaseAdapter(object):", "# ---------------------------------------------------------------- host 自适应")
HOST_SEG = between("class HostResolver(object):", "# ============================================================ rryy")
AES_SEG = between("# ============================================================ AES 工具",
                  "# ============================================================ one /")
INIT_SEG = spider_init_seg()
FETCHB_SEG = between("    def fetch_bytes(self, url", "    def fetch_text(self, url")
FETCHT_SEG = between("    def fetch_text(self, url", "    # ---------------- 适配器 ----------------")

# ---------- 各 Adapter 段
ADAPTER_SEG = {
    "rryy": between("# ============================================================ rryy / 2048",
                    "# ============================================================ AES 工具"),
    "one": between("# ============================================================ one /",
                   "# ============================================================ hdb / 黄豆瓣"),
    "hdb": between("# ============================================================ hdb / 黄豆瓣",
                   "# ============================================================ mmav / 猫咪AV"),
    "mmav": between("# ============================================================ mmav / 猫咪AV",
                    "# ============================================================ 注册表"),
}
ADAPTER_CLS = {"rryy": "RryyAdapter", "one": "OneAdapter",
               "hdb": "HdbAdapter", "mmav": "MmavAdapter"}

META = {
    "rryy": ("2048", "视频", "纯 HTML + 门禁 cookie"),
    "one": ("one", "视频", "AES-128-CBC + MD5 签名"),
    "hdb": ("黄豆瓣", "视频", "RSA-2048 + AES-128-CBC 双向信封"),
    "mmav": ("猫咪AV", "视频", "AES-256-CBC 动态 IV + wsSecret 签名"),
}

HEADER_TPL = '''#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""{name}（{key}）— vbox 自包含适配器

由 muse_avbox.py 的 {cls} 抽取生成，单文件无外部依赖（客户端只下载本文件）。
协议：{proto}

约束：不改 vbox 客户端；所有网络请求走本文件内 urllib。
"""

import base64
import datetime
import gzip
import hashlib
import html as _html
import http.cookiejar
import json
import logging
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


_LOG = logging.getLogger("{key}")
if not _LOG.handlers:
    _LOG.addHandler(logging.NullHandler())


'''

SPIDER_TPL = '''

# ============================================================ vbox 入口
class Spider(SpiderBase):
    MODULE = "{key}"
    NAME = "{name}"
    ADAPTER = {cls}
{init_seg}
    # ---------------- 基类接口 ----------------
    def getName(self):
        return self.NAME

    def getDependence(self):
        return []

    def init(self, extend=""):
        ext = {{}}
        if extend:
            try:
                ext = json.loads(extend) if isinstance(extend, str) else dict(extend)
            except Exception:
                ext = {{}}
        if ext.get("uuid"):
            self.uuid = str(ext["uuid"]).strip()
        if ext.get("versionCode"):
            self.version_code = str(ext["versionCode"])
        if ext.get("timeout"):
            try:
                self.timeout = int(ext["timeout"])
            except Exception:
                pass
        host = ext.get("host")
        if host:
            try:
                self.ADAPTER.HOST = str(host).rstrip("/")
            except Exception:
                pass
        self._adapter = None
        return None

    def isVideoFormat(self, url):
        low = (url or "").lower()
        return any(k in low for k in (".m3u8", ".mp4", ".flv", ".mkv", ".ts", ".mpd"))

    def manualVideoCheck(self):
        return False

    def destroy(self):
        pass

    def action(self, action):
        pass
{fetchb}{fetcht}
    def _get_adapter(self):
        if self._adapter is None:
            self._adapter = self.ADAPTER(self)
        return self._adapter

    # ---------------- vbox 方法 ----------------
    def homeContent(self, filter):
        classes = self._get_adapter().categories()
        if not classes:
            classes = [{{"type_id": "1", "type_name": "全部"}}]
        return {{"class": classes, "list": []}}

    def homeVideoContent(self):
        return {{"list": []}}

    def categoryContent(self, tid, pg, filter, extend):
        try:
            page = int(pg or 1)
        except Exception:
            page = 1
        try:
            items = self._get_adapter().list(str(tid), page)
        except Exception:
            items = []
        return {{
            "list": items or [],
            "page": page,
            "pagecount": page + 1 if items else page,
            "limit": len(items or []),
            "total": 9999 if items else 0,
        }}

    def detailContent(self, array):
        vid = str(array[0]) if array else ""
        if not vid:
            return {{"list": []}}
        try:
            d = self._get_adapter().detail(vid) or {{}}
        except Exception:
            d = {{}}
        if not d:
            return {{"list": []}}
        name = d.get("vod_name") or vid
        play_url = d.get("vod_play_url") or "%s$%s" % (name, vid)
        item = {{
            "vod_id": vid,
            "vod_name": name,
            "vod_pic": d.get("vod_pic", ""),
            "vod_content": d.get("vod_content", ""),
            "vod_play_from": self.NAME,
            "vod_play_url": play_url,
        }}
        if d.get("images"):
            item["vod_play_url"] = "#".join(
                ["%s$%s" % (name, u) for u in d["images"]]) or play_url
        return {{"list": [item]}}

    def playerContent(self, flag, id, vipFlags):
        url = str(id)
        if url and not url.startswith("http"):
            try:
                r = self._get_adapter().play(url)
            except Exception:
                r = None
            if isinstance(r, dict) and r.get("url"):
                return r
        if url.startswith("http"):
            return {{"parse": 0, "url": url, "header": {{"User-Agent": UA_IOS}}}}
        return {{"parse": 1, "url": url, "header": {{"User-Agent": UA_IOS}}, "jx": 1}}

    def searchContent(self, key, quick, pg="1"):
        try:
            page = int(pg or 1)
        except Exception:
            page = 1
        ad = self._get_adapter()
        fn = getattr(ad, "search", None)
        if fn is None:
            return {{"list": [], "page": page, "pagecount": page, "limit": 0, "total": 0}}
        try:
            items = fn(str(key), page) or []
        except Exception:
            items = []
        return {{
            "list": items,
            "page": page,
            "pagecount": page + 1 if items else page,
            "limit": len(items),
            "total": 9999 if items else 0,
        }}

    def localProxy(self, param):
        return [404, "text/plain; charset=utf-8", b"", {{}}]
'''


def build(key):
    name, _ctype, proto = META[key]
    cls = ADAPTER_CLS[key]
    body = HEADER_TPL.format(name=name, key=key, cls=cls, proto=proto)
    body += UA_SEG
    body += PH_SEG
    body += MH_SEG
    body += "\n"
    body += BASE_SEG
    body += HOST_SEG
    body += AES_SEG
    body += ADAPTER_SEG[key]
    body += SPIDER_TPL.format(key=key, name=name, cls=cls,
                              init_seg=INIT_SEG, fetchb=FETCHB_SEG, fetcht=FETCHT_SEG)
    # one 平台需要 token 注入钩子
    if key == "one":
        body = body.replace(
            "        self._adapter = None\n        return None",
            "        tok = ext.get(\"one_token\") or os.environ.get(\"ONE_TOKEN\")\n"
            "        uid = ext.get(\"one_uuid\") or os.environ.get(\"ONE_UUID\")\n"
            "        if tok:\n"
            "            try:\n"
            "                OneAdapter.apply_token(tok, uid)\n"
            "            except Exception:\n"
            "                pass\n"
            "        self._adapter = None\n        return None")
    out = os.path.join(OUTD, key + ".py")
    with open(out, "w", encoding="utf-8", newline="\n") as f:
        f.write(body)
    # 语法检查
    try:
        compile(body, out, "exec")
        ok = "OK"
    except SyntaxError as e:
        ok = "SYNTAX ERROR line %s: %s" % (e.lineno, e.msg)
    print("%-6s -> %-8s %6d 行  %s" % (key, os.path.basename(out), body.count("\n"), ok))
    return out


if __name__ == "__main__":
    keys = sys.argv[1:] or ["hdb", "mmav", "rryy", "one"]
    for k in keys:
        if k not in ADAPTER_SEG:
            print("跳过未知 key:", k)
            continue
        build(k)
