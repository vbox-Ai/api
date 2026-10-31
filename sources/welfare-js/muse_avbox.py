# -*- coding: utf-8 -*-
"""
暮色（com.look.avbox）资源平台 Spider — vbox 福利区适配版 v2
================================================================
架构（2026-10-31 重构，三级模型对齐暮色真实结构）：

  L1 平台目录   /box/api/home 的 data.module → 40 条，31 个带 router
                本文件内置快照 CATALOG（已解密存档），不再依赖 6868 网络
  L2 平台内分类 各平台在自己的域名上提供（见 ADAPTERS）
  L3 数据        同一平台域名的列表 / 详情 / 播放

部署方式：
  · 本文件是引擎，不直接注册为平台
  · 每个资源平台注册一个薄封装 muse_<key>.py，只设 MODULE="<key>"
  · 未设置 MODULE 时退化为「目录模式」，把 31 个平台当分类返回（兼容旧入口）

已适配平台（ADAPTERS）：
  rryy  2048 / 我为人人影院 —— 纯 HTML 明文：分类导航 + 列表 + 详情
  mw    漫蛙漫画            —— 独立蜘蛛 muse_mw.py（HTML 明文）
  live  直播盒子            —— 独立蜘蛛 muse_live_box.py（明文 gzip JSON）

未适配平台：homeContent 仍返回该平台的占位分类（内容类型），点进去为空列表，
           明确降级，不空转、不卡 UI。

证据来源：
  · 真机抓包 归档.zip（88 条，2026-10-28）：6868 只有 ping/splash/home/collect 四个接口
  · docs/muse_home_plain.json：/box/api/home 解密明文，40 条 module 完整字段
  · docs/暮色52平台接口侦察报告.md：各平台可达性与解析要点

extend 可注入：
  {"uuid": "...", "versionCode": "101", "timeout": 15, "host": "https://..."}
"""
import sys
import os
import json
import time
import re
import ssl
import html as _html
import urllib.parse
import urllib.request
import urllib.error
import http.cookiejar

sys.path.append('..')
try:
    from base.spider import Spider as _B
except Exception:
    class _B(object):
        pass

# ============================================================ 常量
UA_IOS = ('Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) '
          'AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Mobile/15E148 Safari/604.1')
UA_DART = "Dart/3.12 (dart:io)"

# 平台目录快照（/box/api/home → data.module，已解密，2026-10-28 真机导出）
# key 取自 router 的 /module/<key> 尾段；tabs 是内容类型（视频/漫画），不是平台内分类
CATALOG = [
    {"id": 36, "key": "lclf", "name": "绿茶楼凤", "type": 0, "collect": 0, "tabs": []},
    {"id": 1, "key": "one", "name": "one", "type": 0, "collect": 1, "tabs": ["视频"]},
    {"id": 2, "key": "insav", "name": "INSAV", "type": 0, "collect": 1, "tabs": ["视频"]},
    {"id": 3, "key": "hhlz", "name": "嘿嘿连载", "type": 0, "collect": 1, "tabs": ["视频", "漫画"]},
    {"id": 4, "key": "aijav", "name": "AiJav", "type": 0, "collect": 1, "tabs": ["视频"]},
    {"id": 5, "key": "mdtv", "name": "麻豆TV", "type": 0, "collect": 1, "tabs": ["视频"]},
    {"id": 6, "key": "rryy", "name": "2048", "type": 0, "collect": 1, "tabs": ["视频"]},
    {"id": 7, "key": "91pron", "name": "91Pron", "type": 0, "collect": 1, "tabs": ["视频"]},
    {"id": 8, "key": "km", "name": "快猫", "type": 0, "collect": 1, "tabs": ["视频"]},
    {"id": 9, "key": "fl2", "name": "fulao2", "type": 0, "collect": 1, "tabs": ["视频"]},
    {"id": 10, "key": "jmtt", "name": "禁漫天堂", "type": 0, "collect": 1, "tabs": ["漫画"]},
    {"id": 11, "key": "akmh", "name": "爱看漫画", "type": 0, "collect": 1, "tabs": ["视频", "漫画"]},
    {"id": 12, "key": "mmav", "name": "猫咪AV", "type": 0, "collect": 1, "tabs": ["视频"]},
    {"id": 13, "key": "kpsp", "name": "看片视频", "type": 0, "collect": 1, "tabs": ["视频"]},
    {"id": 14, "key": "djr", "name": "东京热", "type": 0, "collect": 1, "tabs": ["视频"]},
    {"id": 15, "key": "hgsp", "name": "黄瓜视频", "type": 0, "collect": 1, "tabs": ["视频"]},
    {"id": 17, "key": "hxsp", "name": "红杏视频", "type": 0, "collect": 1, "tabs": ["视频"]},
    {"id": 18, "key": "javdb", "name": "JavDb", "type": 0, "collect": 0, "tabs": []},
    {"id": 19, "key": "zlt", "name": "糟老头", "type": 0, "collect": 1, "tabs": ["视频"]},
    {"id": 20, "key": "txvlog", "name": "糖心Vlog", "type": 0, "collect": 1, "tabs": ["视频"]},
    {"id": 22, "key": "mw", "name": "漫蛙", "type": 0, "collect": 1, "tabs": ["视频"]},
    {"id": 23, "key": "mmmh", "name": "迷妹漫画", "type": 0, "collect": 1, "tabs": ["视频", "漫画"]},
    {"id": 24, "key": "51cg", "name": "51吃瓜", "type": 0, "collect": 1, "tabs": ["视频"]},
    {"id": 25, "key": "91av", "name": "91AV", "type": 0, "collect": 1, "tabs": ["视频"]},
    {"id": 26, "key": "hdb", "name": "黄豆瓣", "type": 0, "collect": 1, "tabs": ["视频"]},
    {"id": 27, "key": "cgw", "name": "吃瓜网", "type": 0, "collect": 1, "tabs": ["视频"]},
    {"id": 28, "key": "qysq", "name": "妻友社区", "type": 0, "collect": 1, "tabs": ["视频"]},
    {"id": 29, "key": "4hu", "name": "4虎", "type": 0, "collect": 1, "tabs": ["视频"]},
    {"id": 30, "key": "hsck", "name": "黄色仓库", "type": 0, "collect": 1, "tabs": ["视频"]},
    {"id": 31, "key": "lxs", "name": "撸先生", "type": 0, "collect": 1, "tabs": ["视频"]},
    {"id": 35, "key": "live", "name": "直播盒子", "type": 0, "collect": 0, "tabs": []}
]

CATALOG_BY_KEY = {m["key"]: m for m in CATALOG}

# 平台 key → 后端主域名（用于占位/降级提示；数据请求走各 ADAPTER）
PLATFORM_HOSTS = {
    "one": "https://api.3459381.com",
    "insav": "https://snen24.com",
    "aijav": "https://newavapi.9xyrp3kg4b86.com",
    "mdtv": "https://spi.d5c4a712.com",
    "rryy": "https://yy.swgongshui.com",
    "91pron": "https://we.killcovid2020.com",
    "km": "https://icef4vn.xyz",
    "fl2": "https://prja.website",
    "jmtt": "https://jdforrepam.com",
    "akmh": "https://www.18akmanhua.com",
    "mmav": "https://bvbvbvssu.a63qv1sy.com",
    "kpsp": "https://sm-api.wieuc.com",
    "djr": "https://tokyohot-api-bo92ps.mtqztc.com",
    "hgsp": "https://api55.nmrgqb.com",
    "hxsp": "https://hxapi.ruueyek.com",
    "javdb": "https://jdforrepam.com",
    "zlt": "https://apjk85sd.q2ngx58.com",
    "txvlog": "https://api.0yhxyky2v099lb9.com",
    "mw": "https://manwaqr.cc",
    "mmmh": "https://public.mino02.live",
    "51cg": "https://h96h69.com",
    "91av": "https://api3.lmqtqhiho.cc",
    "hdb": "https://api.b7f3192.com",
    "cgw": "https://h96h69.com",
    "qysq": "https://d1kmvkv4iwtiup.cloudfront.net",
    "4hu": "https://h96h69.com",
    "hsck": "https://hsck3.u0u0.cc",
    "lxs": "https://api.hichatapi.info",
    "live": "http://api.hclyz.com:81",
    "lclf": "https://lclf.lol",
    "hhlz": "https://snen24.com",
}


# ============================================================ 适配器基类
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
        self._cats = seen
        return seen

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
        cats = {c["type_id"] for c in self.categories()}
        if tid not in cats:
            tid = "1"
        page = int(page or 1)
        # 分页实测（2026-10-31）：
        #   /home/{cid}.html?p={页}  → 分类正确且分页生效（24 张/页）
        #   /?cid={cid}&filter=news&p={页} → 忽略 cid，只按偏移翻全站，分类场景不可用
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


# ============================================================ 注册表
ADAPTERS = {
    "rryy": RryyAdapter,
}


class Spider(_B):
    MODULE = ""

    def __init__(self):
        super(Spider, self).__init__()
        self.uuid = ""
        self.version_code = "101"
        self.timeout = 15
        self.ctx = ssl.create_default_context()
        self.ctx.check_hostname = False
        self.ctx.verify_mode = ssl.CERT_NONE
        self._jar = http.cookiejar.CookieJar()
        self._opener = urllib.request.build_opener(
            urllib.request.HTTPCookieProcessor(self._jar))
        self._adapter = None

    # ---------------- 基类接口 ----------------
    def getName(self):
        meta = CATALOG_BY_KEY.get(self.MODULE)
        if meta:
            return meta["name"]
        return "暮色聚合" if not self.MODULE else self.MODULE

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
        if host and self.MODULE in ADAPTERS:
            try:
                ADAPTERS[self.MODULE].HOST = str(host).rstrip("/")
            except Exception:
                pass
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

    # ---------------- 网络 ----------------
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
            with self._opener.open(req, timeout=self.timeout) as r:
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

    # ---------------- 适配器 ----------------
    def _get_adapter(self):
        if self._adapter is None:
            cls = ADAPTERS.get(self.MODULE)
            self._adapter = cls(self) if cls else None
        return self._adapter

    # ---------------- vbox 方法 ----------------
    def homeContent(self, filter):
        adapter = self._get_adapter()
        if adapter is not None:
            classes = adapter.categories()
            if not classes:
                classes = [{"type_id": "1", "type_name": "全部"}]
            return {"class": classes, "list": []}

        # 目录模式：未设 MODULE 时把 31 个平台当分类（兼容旧入口）
        if not self.MODULE:
            classes = [{"type_id": m["key"], "type_name": m["name"]} for m in CATALOG]
            return {"class": classes, "list": []}

        # 未适配平台：用内容类型做占位分类，明确降级
        meta = CATALOG_BY_KEY.get(self.MODULE) or {}
        tabs = meta.get("tabs") or []
        if not tabs:
            tabs = ["漫画"] if meta.get("key") in ("mw", "akmh", "jmtt", "mmmh") else ["视频"]
        classes = [{"type_id": "_%d" % i, "type_name": t} for i, t in enumerate(tabs)]
        return {"class": classes, "list": []}

    def homeVideoContent(self):
        return {"list": []}

    def categoryContent(self, tid, pg, filter, extend):
        page = int(pg or 1)
        empty = {"list": [], "page": page, "pagecount": page + 1, "limit": 0, "total": 0}
        adapter = self._get_adapter()
        if adapter is None:
            return empty
        try:
            items = adapter.list(tid, page)
        except Exception:
            items = []
        return {
            "list": items,
            "page": page,
            "pagecount": page + 1 if items else page,
            "limit": len(items),
            "total": 9999 if items else 0,
        }

    def searchContent(self, key, quick, pg="1"):
        page = int(pg or 1)
        return {"list": [], "page": page, "pagecount": page, "limit": 0, "total": 0}

    def detailContent(self, array):
        vid = str(array[0]) if array else ""
        adapter = self._get_adapter()
        if adapter is None or not vid:
            return {"list": []}
        try:
            d = adapter.detail(vid) or {}
        except Exception:
            d = {}
        if not d:
            return {"list": []}
        name = d.get("vod_name") or vid
        return {"list": [{
            "vod_id": vid,
            "vod_name": name,
            "vod_pic": d.get("vod_pic", ""),
            "vod_content": d.get("vod_content", ""),
            "vod_play_from": self.getName(),
            "vod_play_url": "%s$%s" % (name, vid),
        }]}

    def playerContent(self, flag, id, vipFlags):
        adapter = self._get_adapter()
        if adapter is not None and str(id) and not str(id).startswith("http"):
            try:
                r = adapter.play(str(id))
            except Exception:
                r = None
            if isinstance(r, dict) and r.get("url"):
                return r
        url = str(id)
        if url.startswith("http"):
            return {"parse": 0, "url": url, "header": {"User-Agent": UA_IOS}}
        return {"parse": 1, "url": url, "header": {"User-Agent": UA_IOS}, "jx": 1}
