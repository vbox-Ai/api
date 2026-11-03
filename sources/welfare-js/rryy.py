#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""2048（rryy）— vbox 自包含适配器

由 muse_avbox.py 的 RryyAdapter 抽取生成，单文件无外部依赖（客户端只下载本文件）。
协议：纯 HTML + 门禁 cookie

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


# ============================================================ vbox 运行时适配
# 客户端 base.spider 只给 requests 打了「代理 + verify=False」补丁，裸 urllib 不走。
# 而 iOS CPython 无系统 CA 证书包 —— urllib 的 HTTPS 会全部 SSLError，
# 现象就是「分类能显示（本地静态），点进去没有数据（联网失败）」。
# 这里显式构造：不验证证书的 SSL 上下文 + 客户端注入的代理 + 自定义域名。
try:
    import ssl as _ssl
    _SSL_CTX = _ssl.create_default_context()
    _SSL_CTX.check_hostname = False
    _SSL_CTX.verify_mode = _ssl.CERT_NONE
except Exception:
    _SSL_CTX = None


def _vbox_cfg(sp, name, default=None):
    v = getattr(sp, name, None)
    if v is None:
        v = globals().get(name)
    return default if v is None else v


def _vbox_proxy(sp):
    if not _vbox_cfg(sp, '_vbox_proxy_enabled', False):
        return {}
    u = _vbox_cfg(sp, '_vbox_proxy_url', '') or ''
    return {'http': u, 'https': u} if u else {}


def _vbox_host(sp, default):
    hs = _vbox_cfg(sp, '_vbox_effective_hosts', None)
    if isinstance(hs, list) and hs:
        try:
            return str(hs[0]).rstrip('/')
        except Exception:
            pass
    return default


def _vbox_opener(sp):
    handlers = [urllib.request.ProxyHandler(_vbox_proxy(sp))]
    if _SSL_CTX is not None:
        handlers.append(urllib.request.HTTPSHandler(context=_SSL_CTX))
    try:
        handlers.append(urllib.request.HTTPCookieProcessor(http.cookiejar.CookieJar()))
    except Exception:
        pass
    return urllib.request.build_opener(*handlers)


_LOG = logging.getLogger("{key}")
if not _LOG.handlers:
    _LOG.addHandler(logging.NullHandler())


UA_IOS = ('Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) '
          'AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Mobile/15E148 Safari/604.1')
UA_DART = "Dart/3.12 (dart:io)"

PLATFORM_HOSTS = {
    # ---------------- 视频类 ----------------
    "one": "https://api.3459381.com",                 # ✓（splash 未下发，沿用）
    "hdb": "https://api.b7f3192.com",                 # ✓ 黄豆瓣
    "rryy": "https://yy.swgongshui.com",              # ⚑ 2048
    "hgsp": "https://api55.nmrgqb.com",               # ✓ 黄瓜视频（已确认真实 host）
    "hxsp": "https://hxapi.ruueyek.com",              # ✓ 红杏视频（token exp=2043）
    "zlt": "https://apjk85sd.q2ngx58.com",            # ✓ 糟老头
    "lxs": "https://api.hichatapi.info",              # ⚑ 撸先生
    "djr": "https://tokyohot-api-bo92ps.mtqztc.com",  # ✗ DNS 无记录，已下线
    "91av": "https://api3.lmqtqhiho.cc",              # ✓ 91AV
    "aijav": "https://newavapi.9xyrp3kg4b86.com",     # ✓ AiJav
    "mdtv": "https://spi.d5c4a712.com",               # ✓ 麻豆TV
    "mmav": "https://bvbvbvssu.a63qv1sy.com",         # ✓ 猫咪AV（根路径 403 属正常）
    "kpsp": "https://sm-api.wieuc.com",               # ✓ 看片视频
    "insav": "https://snen24.com",                    # ⚑ INSAV
    "txvlog": "https://api.0yhxyky2v099lb9.com",      # ✓ 糖心（splash 未下发，沿用）
    "km": "https://icef4vn.xyz",                      # ✓ 快猫
    "91pron": "https://we.killcovid2020.com",         # ✓ 91Pron
    "javdb": "https://jdforrepam.com",                # ✓ JavDb
    "missav": "https://missav.ws",                    # ⚑ MissAV
    "qysq": "https://d1kmvkv4iwtiup.cloudfront.net",  # ✓ 妻友社区
    "hsck": "https://hsck3.u0u0.cc",                  # ✓ 黄色仓库（418 反爬挑战）
    "hjsq": "http://23.225.145.74",                   # ✓ 海角社区
    "lclf": "https://lclf.lol",                       # ⚑ 绿茶楼凤
    # ---------------- 漫画/小说类 ----------------
    "akmh": "https://www.18akmanhua.com",             # ⚑ 爱看漫画
    "jmtt": "https://jdforrepam.com",                 # ✓ 禁漫天堂（splash 未下发，沿用）
    "mw": "https://manwaqr.cc",                       # ✓ 漫蛙
    "mmmh": "https://public.mino02.live",             # ✓ 迷妹漫画（配置另见 MMMH_HOST_TXT）
    "hhlz": "https://snen24.com",                     # ✓ 嘿嘿连载（splash 未下发，沿用）
    # ---------------- 其他 ----------------
    "fl2": "https://prja.website",                    # ✓ fulao2（配置另见 FL2_HOST_API）
    "4hu": "https://h96h69.com",                      # ✗ DNS 有记录但 TCP 不通
    "51cg": "https://h96h69.com",                     # ✗ 同上（splash 未下发）
    "cgw": "https://h96h69.com",                      # ✗ 同上（splash 未下发）
    "live": "http://api.hclyz.com:81",                # ✓ 直播盒子
}
MEDIA_HOSTS = {
    "hdb_img": "https://gjwspicacrlvz.gdpcdz.com",       # ✓ 黄豆瓣图片
    "insav_img": "https://yik.yanyunhome.com",           # ✓
    "kpsp_media": "https://hm-img.hdstfb.com",           # ✓
    "one_img": "https://q3vp74ws02jp.gdliren123.com",    # ✓
    "one_video": "https://z4bey8.bx7qxb.com",            # ✓
    "4hu_api": "https://portal.instruno.com",            # ✓
    "4hu_video": "https://m3u8.73cdn.com",               # ✓
    "jpys_img": "https://img.ypfbj.com",                 # ⚑
    "asgj": "https://qiyouimage.arpuum.cn",              # ✓
    "live1": "https://17s.bj-steel.com.cn",              # ✓
    "live2": "http://api.hclyz.com:81",                  # ✓
}

class BaseAdapter(object):
    """一个资源平台 = 一个适配器。子类实现 categories/list/detail/play。"""

    content_type = "video"   # video / comic / live

    def __init__(self, spider):
        self.sp = spider

    def categories(self):
        """返回 [{"type_id": ..., "type_name": ...}]，即 L2 平台内分类。"""
        return []

    def list(self, tid, page):
        """返回 vbox 列表项 [vod...]。"""
        return []

    def detail(self, vid):
        return {}

    def play(self, vid):
        return None


class HostResolver(object):
    """按平台 key 解析可用域名。

    背景：暮色的域名会轮换，splash 下发的 PLATFORM_HOSTS 是「当前值」，
    但网络环境不同（直连 / 代理 / 被墙）时未必可用。
    本类提供：
      1) 候选池：主域名 + 备选域名（同平台多域名时）
      2) 记忆：本次进程内哪个域名成功过，后续优先复用
      3) 归一化：去掉末尾斜杠，避免拼接出 `//path`
    """

    # 同平台的备选域名（已从 splash 与 plist 交叉确认）
    ALTERNATES = {
        "hdb": ["https://api.b3d530f.com", "https://api.6b18726.com", "https://api.7d87e17.com"],
        "one": ["https://api.61c76a0.com", "https://api.87735d5.com", "https://api.c6dd5cc.com"],
        "rryy": ["https://yy.swgongshui.com"],
        "hgsp": ["https://api55.nmrgqb.com"],
    }

    def __init__(self):
        self._ok = {}   # key -> 已验证可用的域名

    def candidates(self, key, extra=None):
        """返回该平台的候选域名列表（已归一化、去重）。"""
        out = []
        if key in self._ok:
            out.append(self._ok[key])
        base = PLATFORM_HOSTS.get(str(key))
        if base:
            out.append(base)
        for alt in self.ALTERNATES.get(str(key), []):
            out.append(alt)
        for u in (extra or []):
            out.append(u)
        seen, res = set(), []
        for u in out:
            if not u:
                continue
            n = str(u).rstrip("/")
            if n and n not in seen:
                seen.add(n)
                res.append(n)
        return res

    def mark_ok(self, key, host):
        if host:
            self._ok[str(key)] = str(host).rstrip("/")

    def primary(self, key):
        """取首选域名（不探测）。"""
        c = self.candidates(key)
        return c[0] if c else ""

    def join(self, host, path):
        """安全拼接：host 去尾斜杠，path 去头斜杠。"""
        return str(host).rstrip("/") + "/" + str(path).lstrip("/")


_HOST_RESOLVER = None


def host_resolver():
    """全局单例，跨 Adapter 共享探测结果。"""
    global _HOST_RESOLVER
    if _HOST_RESOLVER is None:
        _HOST_RESOLVER = HostResolver()
    return _HOST_RESOLVER


# ============================================================ AES 工具（纯 Python，兼容 vbox 运行时）
def _aes_cbc(key, iv, data, encrypt):
    """AES-128-CBC。优先 Crypto，其次 cryptography，最后 pyaes（vbox 内置）。"""
    try:
        from Crypto.Cipher import AES as _A
        c = _A.new(key, _A.MODE_CBC, iv)
        return c.encrypt(data) if encrypt else c.decrypt(data)
    except Exception:
        pass
    try:
        from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
        c = Cipher(algorithms.AES(key), modes.CBC(iv))
        d = c.encryptor() if encrypt else c.decryptor()
        return d.update(data) + d.finalize()
    except Exception:
        pass
    try:
        import pyaes
        if encrypt:
            m = pyaes.AESModeOfOperationCBC(key, iv=iv)
            pad = 16 - len(data) % 16
            data = data + bytes([pad]) * pad
            out = b""
            for i in range(0, len(data), 16):
                out += m.encrypt(data[i:i + 16])
            return out
        else:
            m = pyaes.AESModeOfOperationCBC(key, iv=iv)
            return m.decrypt(data)
    except Exception:
        raise RuntimeError("no AES backend (Crypto/cryptography/pyaes)")


def _pkcs7(data):
    n = 16 - len(data) % 16
    return data + bytes([n]) * n


def _unpkcs7(data):
    if not data:
        return data
    n = data[-1]
    if 1 <= n <= 16 and data[-n:] == bytes([n]) * n:
        return data[:-n]
    return data


# ============================================================ rryy / 2048
class RryyAdapter(BaseAdapter):
    """2048（我为人人影院）—— 纯 HTML 明文。

    链路（2026-10-31 实测）：
      门禁  GET /home/enter.html?to=%2F  → 种 cookie enter_site_ok
      首页  GET /home/1.html             → 导航 11 个分类 + 48 张卡
      分类  GET /home/{catId}.html       → 该分类列表
      详情  GET /play/{id}.html          → 标题 / 封面（播放需 VIP，取不到直链）
    """

    content_type = "video"
    HOST = "https://yy.swgongshui.com"

    def __init__(self, spider):
        super(RryyAdapter, self).__init__(spider)
        self._entered = False
        self._cats = None

    def _enter(self):
        if self._entered:
            return
        self.sp.fetch_text(self.HOST + "/home/enter.html?to=%2F")
        self._entered = True

    def _page(self, path):
        self._enter()
        return self.sp.fetch_text(self.HOST + path)

    def categories(self):
        if self._cats is not None:
            return self._cats
        html = self._page("/home/1.html")
        pat = re.compile(r'href="/home/(\d+)\.html"[^>]*>\s*<span[^>]*>([^<]{1,20})</span>', re.S)
        seen = []
        for cid, name in pat.findall(html):
            item = {"type_id": cid, "type_name": _html.unescape(name).strip()}
            if item not in seen:
                seen.append(item)
        # 把 11 个扁平分类重组成「带二级分类」的结构：
        #   有码   → [日本有码, 中文有码]
        #   无码   → [中文无码, 日本无码, 欧美无码]
        #   地区   → [国产强片, 日韩强片, 欧美强片]
        #   独立   → 三级强片 / 包罗万象 / VR专区
        # 二级分类用 `sub_categories` 键（下划线风格），与客户端
        # VodCategory.fromJson 约定一致（scheme A）。
        flat = {c["type_id"]: c for c in seen}
        groups = [
            ("yuma",  "有码", ["6", "10"]),
            ("wuma",  "无码", ["7", "8", "9"]),
            ("diqu",  "地区", ["1", "4", "13"]),
        ]
        cats = []
        used = set()
        for gid, gname, members in groups:
            subs = []
            for mid in members:
                if mid in flat:
                    subs.append({"type_id": mid, "type_name": flat[mid]["type_name"]})
                    used.add(mid)
            if subs:
                cats.append({
                    "type_id": gid,
                    "type_name": gname,
                    "sub_categories": subs,
                })
        # 剩余分类作为独立一级分类
        for c in seen:
            if c["type_id"] not in used:
                cats.append(c)
        self._cats = cats
        return cats

    @staticmethod
    def _cards(html):
        out, seen = [], set()
        pat = re.compile(r'href="/play/(\d+)\.html"', re.S)
        positions = [(m.start(), m.group(1)) for m in pat.finditer(html)]
        for idx, (pos, vid) in enumerate(positions):
            if vid in seen:
                continue
            seen.add(vid)
            end = positions[idx + 1][0] if idx + 1 < len(positions) else min(len(html), pos + 4000)
            block = html[pos:end]
            alt = re.search(r'alt="([^"]*)"', block)
            src = re.search(r'(?:data-src|src)="(https?://[^"]+\.(?:jpg|jpeg|png|webp|gif)[^"]*)"', block)
            name = _html.unescape(alt.group(1)).replace("\x00", "").strip() if alt else vid
            if not name or len(name) < 2:
                name = vid
            out.append({
                "vod_id": vid,
                "vod_name": name,
                "vod_pic": (src.group(1).replace("//vod_pic", "/vod_pic") if src else ""),
            })
        return out

    def list(self, tid, page):
        page = int(page or 1)
        # 聚合分类（yuma/wuma/diqu）→ 合并各子分类的第一页数据；
        # 独立分类 → 请求对应 /home/{cid}.html?p={页}
        tid = str(tid)
        group_subs = {
            "yuma": ["6", "10"],
            "wuma": ["7", "8", "9"],
            "diqu": ["1", "4", "13"],
        }
        if tid in group_subs:
            merged = []
            seen_ids = set()
            for sub_id in group_subs[tid]:
                html = self._page("/home/%s.html?p=%d" % (sub_id, page))
                if not html or len(html) < 5000:
                    continue
                for card in self._cards(html):
                    if card["vod_id"] not in seen_ids:
                        seen_ids.add(card["vod_id"])
                        merged.append(card)
            return merged
        # 独立分类
        cats = {c["type_id"] for c in self.categories()}
        if tid not in cats:
            tid = "1"
        html = self._page("/home/%s.html?p=%d" % (tid, page))
        if not html or len(html) < 5000:
            return []
        return self._cards(html)

    def detail(self, vid):
        html = self._page("/play/%s.html" % urllib.parse.quote(str(vid)))
        if not html:
            return {}
        t = re.search(r"<title>([^<]*)</title>", html)
        name = _html.unescape(t.group(1)).replace("\x00", "").strip() if t else ""
        name = re.sub(r"\s*-\s*我为人人影院\s*$", "", name).strip()
        pic = re.search(r'(?:data-src|src)="(https?://[^"]+(?:vod_pic|cover)[^"]*)"', html)
        vip = "会员" in html
        return {
            "vod_id": str(vid),
            "vod_name": name or str(vid),
            "vod_pic": (pic.group(1).replace("//vod_pic", "/vod_pic") if pic else ""),
            "vod_content": "该片源播放需站点 VIP（列表与详情可用）" if vip else "",
            "vip_only": vip,
        }

    def play(self, vid):
        # 站点播放器由 JS 注入，取不到直链；交给播放器嗅探详情页
        return {"parse": 1, "url": self.HOST + "/play/%s.html" % urllib.parse.quote(str(vid))}




# ============================================================ vbox 入口
class Spider(SpiderBase):
    MODULE = "rryy"
    NAME = "2048"
    ADAPTER = RryyAdapter
    def __init__(self):
        super(Spider, self).__init__()
        self.uuid = ""
        self.version_code = "101"
        self.timeout = 15
        self.ctx = ssl.create_default_context()
        self.ctx.check_hostname = False
        self.ctx.verify_mode = ssl.CERT_NONE
        self._jar = http.cookiejar.CookieJar()
        self._opener = _vbox_opener(self)
        self._adapter = None
        self._last_adapter = None  # 目录模式下记录最近一次 categoryContent 用到的 adapter


    # ---------------- 基类接口 ----------------
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
        # 客户端注入的自定义域名优先于脚本内置默认值
        try:
            inj = _vbox_host(self, "")
            if inj:
                self.ADAPTER.HOST = inj
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
    def fetch_bytes(self, url, headers=None, data=None):
        """返回原始字节（POST 用 data 为 bytes；响应已自动 gzip 解压）。"""
        h = {"User-Agent": UA_IOS, "Accept": "*/*", "Accept-Encoding": "gzip"}
        if headers:
            h.update(headers)
        req = urllib.request.Request(url, data=data, headers=h,
                                     method="POST" if data is not None else "GET")
        try:
            with _vbox_opener(self).open(req, timeout=self.timeout) as r:
                raw = r.read()
                enc = (r.headers.get("Content-Encoding") or "").lower()
                if "gzip" in enc:
                    import gzip
                    try:
                        raw = gzip.decompress(raw)
                    except Exception:
                        pass
                return raw
        except urllib.error.HTTPError as e:
            raw = e.read()
            try:
                import gzip
                if raw[:2] == b"\x1f\x8b":
                    return gzip.decompress(raw)
            except Exception:
                pass
            return raw
        except Exception:
            return b""

    def fetch_text(self, url, headers=None, data=None):
        h = {
            "User-Agent": UA_IOS,
            "Accept": "text/html,application/xhtml+xml,application/json,*/*",
            "Accept-Language": "zh-CN,zh;q=0.9",
        }
        if headers:
            h.update(headers)
        req = urllib.request.Request(url, data=data, headers=h,
                                     method="POST" if data is not None else "GET")
        try:
            with _vbox_opener(self).open(req, timeout=self.timeout) as r:
                raw = r.read()
                enc = (r.headers.get("Content-Encoding") or "").lower()
                if "gzip" in enc:
                    import gzip
                    try:
                        raw = gzip.decompress(raw)
                    except Exception:
                        pass
                for code in ("utf-8", "gbk", "gb18030", "latin-1"):
                    try:
                        return raw.decode(code)
                    except Exception:
                        continue
                return raw.decode("utf-8", "replace")
        except urllib.error.HTTPError as e:
            try:
                return e.read().decode("utf-8", "replace")
            except Exception:
                return ""
        except Exception:
            return ""


    def _get_adapter(self):
        if self._adapter is None:
            self._adapter = self.ADAPTER(self)
        return self._adapter

    # ---------------- vbox 方法 ----------------
    def homeContent(self, filter):
        classes = self._get_adapter().categories()
        if not classes:
            classes = [{"type_id": "1", "type_name": "全部"}]
        return {"class": classes, "list": []}

    def homeVideoContent(self):
        return {"list": []}

    def categoryContent(self, tid, pg, filter, extend):
        try:
            page = int(pg or 1)
        except Exception:
            page = 1
        try:
            items = self._get_adapter().list(str(tid), page)
        except Exception:
            items = []
        return {
            "list": items or [],
            "page": page,
            "pagecount": page + 1 if items else page,
            "limit": len(items or []),
            "total": 9999 if items else 0,
        }

    def detailContent(self, array):
        vid = str(array[0]) if array else ""
        if not vid:
            return {"list": []}
        try:
            d = self._get_adapter().detail(vid) or {}
        except Exception:
            d = {}
        if not d:
            return {"list": []}
        name = d.get("vod_name") or vid
        play_url = d.get("vod_play_url") or "%s$%s" % (name, vid)
        item = {
            "vod_id": vid,
            "vod_name": name,
            "vod_pic": d.get("vod_pic", ""),
            "vod_content": d.get("vod_content", ""),
            "vod_play_from": self.NAME,
            "vod_play_url": play_url,
        }
        if d.get("images"):
            item["vod_play_url"] = "#".join(
                ["%s$%s" % (name, u) for u in d["images"]]) or play_url
        return {"list": [item]}

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
            return {"parse": 0, "url": url, "header": {"User-Agent": UA_IOS}}
        return {"parse": 1, "url": url, "header": {"User-Agent": UA_IOS}, "jx": 1}

    def searchContent(self, key, quick, pg="1"):
        try:
            page = int(pg or 1)
        except Exception:
            page = 1
        ad = self._get_adapter()
        fn = getattr(ad, "search", None)
        if fn is None:
            return {"list": [], "page": page, "pagecount": page, "limit": 0, "total": 0}
        try:
            items = fn(str(key), page) or []
        except Exception:
            items = []
        return {
            "list": items,
            "page": page,
            "pagecount": page + 1 if items else page,
            "limit": len(items),
            "total": 9999 if items else 0,
        }

    def localProxy(self, param):
        return [404, "text/plain; charset=utf-8", b"", {}]
