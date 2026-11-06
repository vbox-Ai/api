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
import base64
import datetime
import hashlib
import logging
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

# 模块级日志器（token 过期等运行期告警用）
_LOG = logging.getLogger("muse_avbox")
if not _LOG.handlers:
    _LOG.addHandler(logging.NullHandler())

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
#
# 数据来源：真机 6868 主后端 /box/api/splash 解密明文（2026-11-02，共 38 条 host）
#           资产见 tools/_dec/box_api_splash.json
# 可达性标注（2026-11-02 实测：29 直连 / 7 仅代理 / 2 真不可达）
#   ✓  直连    国内网络直接可达
#   ⚑  代理    被墙，走代理可达（客户端侧无障碍）
#   ✗  失效    DNS 无记录或服务已下线
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
    "hhlz": "https://rrs0a03ak.pye57rf.com",          # ✓ 嘿嘿连载（抓包实测，splash 未下发）
    # ---------------- 其他 ----------------
    "fl2": "https://prja.website",                    # ✓ fulao2（配置另见 FL2_HOST_API）
    "4hu": "https://h96h69.com",                      # ✗ DNS 有记录但 TCP 不通
    "51cg": "https://h96h69.com",                     # ✗ 同上（splash 未下发）
    "cgw": "https://h96h69.com",                      # ✗ 同上（splash 未下发）
    "live": "http://api.hclyz.com:81",                # ✓ 直播盒子
}

# ---------------------------------------------------------------------------
# 配置下发型端点：返回"域名配置"，不是 API 根，不能直接拼接口路径
# ---------------------------------------------------------------------------
FL2_HOST_API = "https://prja.website/v1/host"                # fulao2 host 配置
MMMH_HOST_TXT = "https://public.mino02.live/host_pwa.txt"    # 迷妹漫画 host 配置

# ---------------------------------------------------------------------------
# 媒体 / 资源域名（图片、m3u8、ts 切片）
# splash 下发但旧脚本未收录；播放直链与封面拼接需用到
# ---------------------------------------------------------------------------
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


# ---------------------------------------------------------------- host 自适应
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


# ============================================================ one / api.3459381.com
class OneAdapter(BaseAdapter):
    """one 平台 —— 请求/响应均 AES-128-CBC 加密。

    密钥（Blutter 反编译 OneInterceptor 实证）：
      Key = l*bv%Ziq000Biaog   IV = 8597506002939249
    签名（OneInterceptor::onRequest 反推）：
      sign = MD5( MD5("0.0.0.0.3." + timestamp + ".." + uuid) + "m4n2hjPeYWkD6tFpqKF^3HO^h24P@idT" )
    链路：
      分类  POST /v2.5/navigation/getDemandTagList   body 空
      列表  POST /v2.5/article/discovery             body 表单加密
      详情  POST /v2.5/article/detail                body id=xxx 加密
    响应：gzip(http) → 去引号 → base64 → AES 解密 → JSON
    """

    content_type = "video"
    HOST = "https://api.3459381.com"
    IMG_HOST = "https://q3vp74ws02jp.gdliren123.com"
    VIDEO_HOST = "https://z4bey8.bx7qxb.com"
    KEY = b"l*bv%Ziq000Biaog"
    IV = b"8597506002939249"
    SIGN_SALT = "m4n2hjPeYWkD6tFpqKF^3HO^h24P@idT"
    # 正式态 token（muse_endpoints.json tokens.one + 对应 uuid）
    # 注意：正式态 token exp=2026-11-02 07:00，过期后需刷新（后续补动态刷新机制）
    TOKEN = ("eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9.eyJpc3MiOjgwNTA0NzcsImlzX3Zpc2l0b3IiOjA"
             "sInV1aWQiOiJkYTIzYTMwMC1jZWJmLTExZjEtOWJlMC0yYjg0NDU2OWFmMzkiLCJuaWNrbmFtZSI"
             "6IjE1NioqKioqOTU2IiwiaXAiOiIzOC40Ni4xMC4yIiwiaWF0IjoxNzkyOTY1NjAwLCJleHAiOjE"
             "3OTM1NzQwMDAsIm5iZiI6MTc5Mjk2NTYwMCwic3ViIjoiYXBpLmVtMW9pZmQwLmNvbSIsImp0aSI"
             "6IjdmOGQzZWZjNWU3ZWM1NmFmM2M4Y2FmZDQ2YzExYTFmIn0.ynDjIcs74g7uRB84mnr98rU7trs"
             "InlK0pjXzCIr6xMI")
    UUID = "da23a300-cebf-11f1-9be0-2b844569af39"

    def __init__(self, spider):
        super(OneAdapter, self).__init__(spider)
        self.token = OneAdapter.TOKEN
        self.uuid = OneAdapter.UUID
        self._cats = None
        self._token_warned = False
        self._token_checked = False

    # ---------------- token 管理 ----------------
    # token 唯一来源 = 6868 /box/api/splash 下发（客户端内无登录/注册接口）。
    # 6868 splash 目前被服务端加固（返回"违规请求"），无法自动拉取。
    # 因此策略为：
    #   1) extend 注入优先（{"one_token": "...", "one_uuid": "..."}）
    #   2) 进程环境变量兜底（ONE_TOKEN / ONE_UUID）
    #   3) 都没有则用内置 TOKEN
    #   首次请求时用真实调用探活；失效则一次性告警，不反复骚扰日志。
    @classmethod
    def apply_token(cls, token, uuid=None):
        """外部注入 token。uuid 为空时自动从 JWT payload 提取。"""
        if not token:
            return False
        cls.TOKEN = str(token)
        if uuid:
            cls.UUID = str(uuid)
        else:
            pl = cls._payload(token)
            if pl and pl.get("uuid"):
                cls.UUID = pl["uuid"]
        return True

    @classmethod
    def _payload(cls, tok):
        try:
            parts = str(tok).split(".")
            if len(parts) < 2:
                return None
            seg = parts[1]
            seg += "=" * (-len(seg) % 4)
            return json.loads(base64.urlsafe_b64decode(seg))
        except Exception:
            return None

    @staticmethod
    def token_exp(tok):
        """从 JWT 取出 exp（秒级时间戳）。非 JWT 返回 None。"""
        pl = OneAdapter._payload(tok)
        return pl.get("exp") if pl else None

    def token_status(self):
        """返回 (是否未过期, 剩余秒数)。无 exp 视为未知但放行。"""
        exp = self.token_exp(self.token)
        if exp is None:
            return True, None
        left = int(exp) - int(time.time())
        return left > 0, left

    def _check_token(self):
        """首次调用时检查 token 剩余寿命，过短则写日志（不影响返回结构）。"""
        if self._token_warned:
            return
        self._token_warned = True
        ok, left = self.token_status()
        try:
            if not ok:
                _LOG.warning("one: token 已过期，需更新 OneAdapter.TOKEN")
            elif left is not None and left < 86400:
                _LOG.warning("one: token 将在 %.1f 小时后过期", left / 3600.0)
        except Exception:
            pass

    def _sign(self, ts, uuid):
        import hashlib
        inner = hashlib.md5(("0.0.0.0.3." + ts + ".." + uuid).encode()).hexdigest()
        return hashlib.md5((inner + OneAdapter.SIGN_SALT).encode()).hexdigest()

    def _call(self, path, form=""):
        self._check_token()
        self.ensure_token(probe_path=path)
        ts = str(int(time.time()))
        headers = {
            "User-Agent": UA_DART,
            "ip": "0.0.0.0",
            "uuid": self.uuid,
            "Content-Type": "application/x-www-form-urlencoded",
            "timestamp": ts,
            "platform": "3",
            "token": self.token,
            "sign": self._sign(ts, self.uuid),
            "user-key": "",
            "app-version": "2.6.4",
        }
        body = b""
        if form:
            ct = _aes_cbc(self.KEY, self.IV, _pkcs7(form.encode()), True)
            body = base64.b64encode(ct)
        raw = self.sp.fetch_bytes(self.HOST + path, headers=headers, data=body)
        if not raw:
            return None
        return self._dec(raw)

    def _dec(self, raw):
        try:
            p = raw.decode("utf-8", "replace").strip()
            # 服务端错误/明文直接返回 JSON
            if p[:1] in ("{", "["):
                return json.loads(p)
            if p[:1] == '"':
                p = json.loads(p)
            ct = base64.b64decode(p + "=" * (-len(p) % 4))
            pt = _unpkcs7(_aes_cbc(self.KEY, self.IV, ct, False))
            return json.loads(pt.decode("utf-8", "replace"))
        except Exception:
            return None

    # ---------------- token 探活 ----------------
    # 重要：one 接口必须带 `user-key` 头，即使是空值也必须发送。
    # urllib 会发送 "user-key: "（服务端接受），curl 会丢弃空值头（服务端 401）。
    def token_alive(self, probe_path="v2.5/navigation/getDemandTagList"):
        """用一次真实调用判断 token 是否仍可用。返回 True/False。"""
        try:
            self._probing = True
            try:
                r = self._call(probe_path)
            finally:
                self._probing = False
            if isinstance(r, dict):
                code = r.get("code")
                if code == 200:
                    return True
                if code == 401:
                    return False
            # 解密失败或结构异常，按不可用处理但不误报
            return bool(r)
        except Exception:
            self._probing = False
            return False

    def ensure_token(self, probe_path=None):
        """首次使用时执行一次探活；失效则明确告警，避免静默空数据。"""
        if self._token_checked or getattr(self, "_probing", False):
            return
        self._token_checked = True
        ok, left = self.token_status()
        if ok and self.token_alive(probe_path or "v2.5/navigation/getDemandTagList"):
            return
        _LOG.error(
            "one: token 不可用（本地判断 %s，剩余 %s）。"
            "请更新 OneAdapter.TOKEN 或在 extend 中传 one_token。",
            "未过期" if ok else "已过期",
            ("%.1f 小时" % (left / 3600.0)) if left is not None else "未知")

    def _abs(self, path, host):
        if not path:
            return ""
        if path.startswith("http"):
            return path
        return host + path

    def categories(self):
        if self._cats is not None:
            return self._cats
        d = self._call("//v2.5/navigation/getDemandTagList", "")
        cats = []
        if d and d.get("code") == 200:
            raw = [t for t in (d.get("data") or []) if isinstance(t, dict)]
            # one 上游 5 个 demand_tag 是扁平分类（id 1-5）：
            #   1=欧美 2=日本 3=国产 4=ONE直播 5=抽奖
            # 其中 1/2/3 是「视频」内容，4/5 是非视频栏目。
            # 这里把 1/2/3 归为一个「视频」一级分类 + 三个地区二级分类，
            # 4/5 各自保持独立一级分类 —— 真实反映内容结构，不造假。
            # 二级分类用 `sub_categories` 键（下划线风格），与客户端
            # VodCategory.fromJson 约定一致（客户端 scheme A）。
            video_subs = []
            for t in raw:
                tid = str(t.get("id"))
                title = t.get("title", "")
                if tid in ("1", "2", "3"):
                    video_subs.append({"type_id": tid, "type_name": title})
            if video_subs:
                cats.append({
                    "type_id": "video",
                    "type_name": "视频",
                    "sub_categories": video_subs,
                })
            for t in raw:
                tid = str(t.get("id"))
                title = t.get("title", "")
                if tid in ("4", "5"):
                    cats.append({"type_id": tid, "type_name": title})
        if not cats:
            cats = [{"type_id": "0", "type_name": "全部"}]
        self._cats = cats
        return cats

    def list(self, tid, page):
        page = int(page or 1)
        ym = time.strftime("%Y-%m")
        # 一级「视频」聚合分类 tid="video" → 请求全部视频（demand_tag_id=0）；
        # 二级分类 tid="1"/"2"/"3" 或独立分类 "4"/"5" → 请求对应 demand_tag_id。
        if str(tid) == "video":
            tag_id = "0"
        else:
            tag_id = str(tid or 0)
        form = ("demand_tag_id=%s&model_id=6&page=%d&published_at=%s&size=24&sort=published_at"
                % (tag_id, page, ym))
        d = self._call("//v2.5/article/discovery", form)
        out = []
        if d and d.get("code") == 200:
            for it in d.get("data") or []:
                if not isinstance(it, dict):
                    continue
                out.append({
                    "vod_id": str(it.get("id")),
                    "vod_name": it.get("title") or it.get("description") or it.get("actor") or str(it.get("id")),
                    "vod_pic": self._abs(it.get("thumb"), self.IMG_HOST),
                    "vod_remarks": it.get("length") or it.get("quality") or "",
                })
        return out

    def detail(self, vid):
        d = self._call("//v2.5/article/detail", "id=%s" % vid)
        if not d or d.get("code") != 200:
            return {}
        it = d.get("data") or {}
        pics = it.get("multiple_pic") or it.get("multi_pic_thumbnail") or []
        video = it.get("video_file") or it.get("video") or it.get("preview_video") or ""
        play_url = self._abs(video, self.VIDEO_HOST) if video else ""
        content = it.get("description") or it.get("title") or ""
        return {
            "vod_id": str(vid),
            "vod_name": it.get("title") or it.get("video_name") or str(vid),
            "vod_pic": self._abs(it.get("thumb"), self.IMG_HOST),
            "vod_content": content,
            "vod_play_url": play_url,
            "images": [self._abs(p, self.IMG_HOST) for p in pics if p],
        }

    def play(self, vid):
        d = self.detail(vid)
        url = d.get("vod_play_url") or ""
        if url:
            return {"parse": 0, "url": url, "header": {"User-Agent": UA_IOS}}
        imgs = d.get("images") or []
        if imgs:
            return {"parse": 0, "url": "manga://" + "&&".join(imgs)}
        return None


# ============================================================ hdb / 黄豆瓣
class HdbAdapter(BaseAdapter):
    """黄豆瓣（key=hdb）—— RSA-2048 + AES-128-CBC 双向加密信封。

    协议（逆向 libapp.so，实测通过）：
      请求  encrypt_data = base64(AES-128-CBC(业务JSON))
            encrypt_key  = base64(RSA(服务端公钥, {"key":b64,"iv":b64}))
      响应  encrypt_key  → RSA 客户端私钥解密 → AES key/iv
            encrypt_data → AES-128-CBC 解密 → JSON（可能 gzip）
    接口：pwa/v2_0/dailyList / filmDetails / searchV21List
    注意：国内直连可用，无需翻墙。
    """

    content_type = "video"

    DOMAINS = [
        "https://api.b7f3192.com/",
        "https://api.b3d530f.com/",
        "https://api.6b18726.com/",
        "https://api.7d87e17.com/",
    ]

    SERVER_PUB_PEM = """-----BEGIN PUBLIC KEY-----
MIIBIjANBgkqhkiG9w0BAQEFAAOCAQ8AMIIBCgKCAQEAtHXnr6i9DxHl1xEJoczX
QvOGUrROLWn89QedCY2JeljOOqj/CHa+rqnzyy9qylx8WUQE7BYFhtLi8erOgZ4X
ezbJLRfWoccSMHjAW0KkS9o2MXKdmrFWllRVw7uMEUXNWVTJU3u+YWZcUMxI6z93
B5MZqJoiOlneI8icw11thOEguo3wgPpJGDILrXIsCBdOepOyk3ajYHfnWnbm725E
28UNuegydULxIAtKs0MuOxoGHhKlEm5Cfn1WY5PMH169T+AD01lCVNjs2MUnDf26
iO+7vijvY0/Y93jnjT/n3MVmKfGM4ggOKHU3qKamPf5kwlZipJ6CQwR8JLotkxP+
kQIDAQAB
-----END PUBLIC KEY-----"""

    CLIENT_PRIV_PEM = """-----BEGIN PRIVATE KEY-----
MIIEvQIBADANBgkqhkiG9w0BAQEFAASCBKcwggSjAgEAAoIBAQDM3SKlwhVilftp
FodFBn4isxrSm9NxG/K3Ux6qQoH77vs7pJkGBr8Yhr1Wom2s2dpXzzXq17Iz0Hx1
wooDSKWlQO6Ask9uyw13lTcLYt3TCad3lIIea/BQf75LxTlGyLN0QD9kgY0U+aqh
nKxXrSiQ0frjtD11vF8h/KPZydkng7vAsAZAObonjxKoqzU+Nz4UzUdd42xV9kru
Q7eUlcz6Fphn6/+Zxc2WdCr/cgVShjShcbH8I4MUPHl16ZuJFs3DM0TgIpL6CD0k
LuzvuU/aVgl6eNrwyDq4NL811d+fRX2T6nfiO74TUXZ/3vlbrrrBl5Zy9x2ymP+o
L6WP7nYfAgMBAAECggEAOBt0astuCfMjyRNHdushTqWY+gd9cGQEJJtaMa1HZlV8
b0hUNKdSXQhCAOE5gnaj6xqwHKJ4huJZw/LE08Nowoq3B35ObPylspOmYLLyJ+Nj
/0coH+bWCWYDG0NnvXAoXfVep0sn9Y+vYNXFCbo9+vPXb9ekYYN21psX0QUMOVrI
b5tdJ1OY739bvydAotjkIcsQcThL04u1mF+6FNBms7pTiR6Sp+7ZvuDBV1wFZ6Oj
AIed9aIcSJQqSFVjxwgyHcT6RmzUFCvbVFyoHW/9cJ6Iqw17clQ4RlfXbh1vfhNr
FgTiBiMcPKW90ikkpVPYCLajELo2RMtUhIzZ+KULyQKBgQDp/AzPHk5/XW4WcLcz
CJRsHiRjbSadSH2sSB0r9lq/Ju5hHzOHzXZPXqhWf4A/okuYve33QXe3Eem4TJK3
MR+dyUcV99SDqdSRfubyQHQ9vBaR99+wXZA3yGvqnsQQAjROD7wnBkDJ6THi7ulQ
kS7ewdzpU6HffZtJnACQKzdmgwKBgQDgI6h3qTtla1IoyDDxDNZdmWTBIrBiqKtk
hxFUkiSydOF0jMtpdPkjK08r6fBrrof11z1oW+FwmrLmovYpRNb68sLruYWiVR+U
4Rz00kTQ1/nusdHaaFJRQk5yLbaitR198LhSCvWg43PKZKkOuCaVmtqy81t5z3mx
Ff3I0xQ/NQKBgFKP+qEWy5ILkK3gZfRfAahI1oQy3p4/FwE0jP6XNhwfC5w/mzo/
GJEXEIU9Bi7uAIjL8+z8L9bsPjEm69oyPjq57BhnU5iF05jnU2yFq76g4MHu2gJs
cVgNo26tSPdxH62vxa9reG8GlvDBZphkMkqt01qNhR/MPYAyyMwWQ70rAoGBALXA
VIDL6w0fjJzjUMR2y3FUzJ3MWkl2Sp0W5Ze1dip7msKe1Odr4gaBvQ54AevfuAJD
ClmQf+uGlmFtbb0jREx0BFmPs+xhqF1aedeQlhrft5y19txrUazw3pm5teqUgRi5
1U0589oF9sP9AhWcgDU6P/NyYRASjLRrh8KMX1OtAoGAPQpoII/1154GATbMWCUe
RNCawhUDpmPI4hPomc9dmY7AeaB5LbcweuQ5kyHGOtn5ZMQcc0BIWpNP5j8QuCzB
VIOZSYBhwQnf2mDvVFo2vQc5Zty1TSNLyTtzkhncuW7FQHoAynBp+pctvKRJkaq9
piQStzEEfes94FMWEOaBHDA=
-----END PRIVATE KEY-----"""

    COMMON = {
        "channelcode": "pwa_254_0714",
        "nettype": "wifi",
        "deviceid": "9471361b-b296-4aa4-b4ee-7ad9ee4b7de2",
        "model": "Win32",
        "platform": 6,
        "version": "2.5.4",
        "sysversion": ("5.0 (iPhone; CPU iPhone OS 18_5 like Mac OS X) "
                       "AppleWebKit/605.1.15 (KHTML, like Gecko) "
                       "Version/18.5 Mobile/15E148 Safari/604.1"),
    }

    UA = ("5.0 (iPhone; CPU iPhone OS 18_5 like Mac OS X) "
          "AppleWebKit/605.1.15 (KHTML, like Gecko) "
          "Version/18.5 Mobile/15E148 Safari/604.1")

    USER_TOKEN = ("eyJ1c2VyX3V1aWQiOiJlZTg5MTNkYi05ZDc2LTQyMDUtODA5MC1hNDM3MzU4"
                  "ZTIxYjMiLCJ1cGRhdGVkX2F0IjoxNzkyODQzNzQ1LCJ2aXNpdG9yIjowfQ==")

    IMG_HOST = "https://gjwspicacrlvz.gdpcdz.com"

    def __init__(self, spider):
        super(HdbAdapter, self).__init__(spider)
        self.host = HdbAdapter.DOMAINS[0]
        self.timeout = 25
        self._belong_map = {}  # vod_id -> belong(ltype)
        self._ctx = ssl.create_default_context()
        self._ctx.check_hostname = False
        self._ctx.verify_mode = ssl.CERT_NONE
        try:
            from cryptography.hazmat.primitives import serialization
            from cryptography.hazmat.primitives.asymmetric import padding as _rsa_pad
            from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
            self._server_pub = serialization.load_pem_public_key(
                HdbAdapter.SERVER_PUB_PEM.encode())
            self._client_priv = serialization.load_pem_private_key(
                HdbAdapter.CLIENT_PRIV_PEM.encode(), password=None)
            self._rsa_pad = _rsa_pad
            self._cipher = Cipher
            self._algorithms = algorithms
            self._modes = modes
            self._has_crypto = True
        except Exception:
            self._has_crypto = False

    def _rsa_encrypt(self, data):
        return self._server_pub.encrypt(data, self._rsa_pad.PKCS1v15())

    def _rsa_decrypt(self, data):
        return self._client_priv.decrypt(data, self._rsa_pad.PKCS1v15())

    def _aes_cbc(self, key, iv, data, encrypt=True):
        c = self._cipher(self._algorithms.AES(key), self._modes.CBC(iv))
        x = c.encryptor() if encrypt else c.decryptor()
        return x.update(data) + x.finalize()

    @staticmethod
    def _pkcs7_pad(data):
        n = 16 - (len(data) % 16)
        return data + bytes([n]) * n

    @staticmethod
    def _pkcs7_unpad(data):
        if not data:
            return data
        n = data[-1]
        if 1 <= n <= 16 and data[-n:] == bytes([n]) * n:
            return data[:-n]
        return data

    def _build_body(self, params):
        import os as _os
        key = _os.urandom(16)
        iv = _os.urandom(16)
        meta = json.dumps({
            "key": base64.b64encode(key).decode(),
            "iv": base64.b64encode(iv).decode(),
        }, separators=(",", ":")).encode("utf-8")
        encrypt_key = base64.b64encode(self._rsa_encrypt(meta)).decode()
        raw = json.dumps(params, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
        ct = self._aes_cbc(key, iv, self._pkcs7_pad(raw), encrypt=True)
        encrypt_data = base64.b64encode(ct).decode()
        return {"encrypt_data": encrypt_data, "encrypt_key": encrypt_key}

    def _decrypt_body(self, resp):
        ek = base64.b64decode(resp["encrypt_key"])
        ed = base64.b64decode(resp["encrypt_data"])
        meta = json.loads(self._rsa_decrypt(ek).decode("utf-8"))
        aes_key = base64.b64decode(meta["key"])
        iv = base64.b64decode(meta["iv"])
        pt = self._pkcs7_unpad(self._aes_cbc(aes_key, iv, ed, encrypt=False))
        if pt[:2] == b"\x1f\x8b":
            import gzip
            pt = gzip.decompress(pt)
        return json.loads(pt.decode("utf-8"))

    def _post(self, path, params):
        body = self._build_body(params)
        data = json.dumps(body, separators=(",", ":")).encode("utf-8")
        headers = {
            "User-Agent": HdbAdapter.UA,
            "Content-Type": "application/json",
            "Accept": "application/json",
        }
        opener = urllib.request.build_opener(
            urllib.request.HTTPSHandler(context=self._ctx))
        # 域名轮换：当前域名失败时切换下一个
        for domain in HdbAdapter.DOMAINS:
            url = domain.rstrip("/") + "/" + path.lstrip("/")
            for _ in range(2):
                try:
                    req = urllib.request.Request(url, data=data, headers=headers, method="POST")
                    with opener.open(req, timeout=self.timeout) as r:
                        raw = r.read()
                    resp = json.loads(raw.decode("utf-8"))
                    if not isinstance(resp, dict) or "encrypt_data" not in resp:
                        return resp
                    result = self._decrypt_body(resp)
                    if result is not None:
                        return result
                except urllib.error.HTTPError as e:
                    try:
                        resp = json.loads(e.read().decode("utf-8"))
                        if not isinstance(resp, dict) or "encrypt_data" not in resp:
                            return resp
                        result = self._decrypt_body(resp)
                        if result is not None:
                            return result
                    except Exception:
                        pass
                except Exception:
                    pass
        return None

    @staticmethod
    def _abs_img(path):
        if not path:
            return ""
        if path.startswith("http"):
            return path
        return HdbAdapter.IMG_HOST + path

    def categories(self):
        return [
            {
                "type_id": "video",
                "type_name": "视频",
                "sub_categories": [
                    {"type_id": "4", "type_name": "最新"},
                    {"type_id": "3", "type_name": "国产"},
                    {"type_id": "2", "type_name": "日本"},
                    {"type_id": "1", "type_name": "欧美"},
                ],
            }
        ]

    def _fetch_daily(self, date_str, page=1):
        """取指定日期的一页数据。date 为必填参数（缺省会返回 code=41000 参数错误）。"""
        params = dict(HdbAdapter.COMMON)
        params.update({
            "page": page,
            "length": 20,
            "country": -2,
            "censorship_type": 0,
            "date": date_str,
        })
        return self._post("pwa/v2_0/dailyList", params)

    @staticmethod
    def _items_of(resp):
        if not resp or not isinstance(resp, dict):
            return []
        data = resp.get("data", resp)
        if not isinstance(data, dict):
            return []
        items = data.get("list")
        return items if isinstance(items, list) else []

    def _latest_date(self):
        """当天无更新时，回溯最多 7 天，找最近有数据的一天。

        hdb 的 dailyList 按"更新时间"分组：今天还没更新时列表就是空的，
        但这不代表平台挂了。回溯保证客户端不会看到空白页。
        """
        today = datetime.date.today()
        for back in range(0, 8):
            d = (today - datetime.timedelta(days=back)).isoformat()
            if back == 0:
                hit = self._fetch_daily(d, 1)
                if self._items_of(hit):
                    return d, hit
                continue
            time.sleep(0.8)          # 服务端有限流，请求间隔别太密
            resp = self._fetch_daily(d, 1)
            if self._items_of(resp):
                return d, resp
        return today.isoformat(), None

    def list(self, tid, page):
        page = int(page or 1)
        today_str = time.strftime("%Y-%m-%d")

        if page <= 1:
            date_str, resp = self._latest_date()
            self._current_date = date_str
        else:
            # 翻页沿用上一次选定的日期，避免同日多次回溯
            date_str = getattr(self, "_current_date", today_str) or today_str
            resp = self._fetch_daily(date_str, page)

        out = []
        if not resp or not isinstance(resp, dict):
            return out
        data = resp.get("data", resp)
        items = self._items_of(resp)
        for it in items:
            if not isinstance(it, dict):
                continue
            vid = str(it.get("id", ""))
            belong = it.get("belong", 1)
            self._belong_map[vid] = belong
            out.append({
                "vod_id": vid,
                "vod_name": it.get("title") or vid,
                "vod_pic": self._abs_img(it.get("img_url") or ""),
                "vod_remarks": it.get("love_number") or "",
            })
        return out

    def detail(self, vid):
        belong = self._belong_map.get(str(vid), 1)
        params = dict(HdbAdapter.COMMON)
        params.update({
            "film_id": str(vid),
            "ltype": belong,
            "userToken": HdbAdapter.USER_TOKEN,
        })
        resp = self._post("pwa/v2_0/filmDetails", params)
        if not resp or not isinstance(resp, dict):
            return {}
        data = resp.get("data", resp)
        items = data if isinstance(data, list) else (data.get("list") if isinstance(data, dict) else None)
        item = items[0] if isinstance(items, list) and items else {}
        if not isinstance(item, dict):
            return {}
        return {
            "vod_id": str(vid),
            "vod_name": item.get("title") or str(vid),
            "vod_pic": self._abs_img(item.get("img_url") or ""),
            "vod_play_url": item.get("url") or "",
        }

    def play(self, vid):
        d = self.detail(vid)
        url = d.get("vod_play_url") or ""
        if url:
            return {"parse": 0, "url": url, "header": {"User-Agent": HdbAdapter.UA}}
        return None


# ============================================================ mmav / 猫咪AV
class MmavAdapter(BaseAdapter):
    """猫咪AV —— 静态 js 数据 + AES-256-CBC 动态 IV + wsSecret 播放鉴权。

    链路（2026-11-02 全链路实测打通）：
      配置  GET data/config/base-1.js   → static_host / image_domain / m3u8_host_encrypt
      分类  GET data/category/base-1.js → menus 树（10 个一级菜单，各 8 个子分类）
      列表  GET data/mediaVideo/list-{cid}-{page}-50.js → 视频列表（50/页）
      封面  image_domain + cover 路径 → 200 image/jpeg
      播放  m3u8_host_encrypt + video_url + wsSecret 签名 → 200 application/vnd.apple.mpegurl

    加密（avbox/module/mmav/network/interceptor.dart 反汇编还原）：
      key = "IdTJq0HklpuI6mu8iB%OO@!vd^4K&uXW"   (32 字节 → AES-256)
      iv  = "$0v@krH7V2" + response["suffix"]      (固定常量在前，动态 suffix 在后)
      data = base64 → AES-256-CBC 解密 → JSON

    播放鉴权（avbox/util/url_util.dart::mmAvVideo + str_util.dart::wsSecret）：
      expire = now + 7200
      wsSecret = md5( "D7hGKHnWThaECaQ3ji4XyAF3MfYKJ53M" + uri.path + expire )
      → url?wsSecret=xxx&wsTime=xxx&ip=xxx

    分页语义（实测纠正）：模板中间数字是「页码」不是偏移量。
      list-7-1-50 → 第1页(首条54433)；list-7-2-50 → 第2页(首条50526)
      误传偏移 51 会变成第 51 页并返回空。

    遗留：
      - data/list/base-* 是另一种 slug 型列表，当前返回空 cat_list（未使用）
      - 专题频道（channel=topic）走 /page/topic/{id}，未接入
    """

    content_type = "video"
    HOST = "https://bvbvbvssu.a63qv1sy.com"
    KEY = b"IdTJq0HklpuI6mu8iB%OO@!vd^4K&uXW"
    IV_PREFIX = "$0v@krH7V2"
    IMG_FALLBACK = "https://wzzqlm.erbaiwulaoge.com"
    VIDEO_FALLBACK = "https://cf-worker-r2.mtzionhub.com"
    WS_SALT = "D7hGKHnWThaECaQ3ji4XyAF3MfYKJ53M"

    def __init__(self, spider):
        super(MmavAdapter, self).__init__(spider)
        self._cfg = None
        self._cats = None
        self._cat_map = {}      # 分类 id -> 名称
        self._vid_map = {}      # vod_id -> {video_url, cover, category_id}
        self._have_crypto = True
        try:
            from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
            self._Cipher, self._algo, self._modes = Cipher, algorithms, modes
        except Exception:
            self._have_crypto = False

    # ---------------- 传输与解密 ----------------
    def _get(self, path):
        txt = self.sp.fetch_text(self.HOST + "/" + path,
                                 headers={"User-Agent": UA_IOS})
        if not txt or not txt.lstrip().startswith("{"):
            return None
        try:
            return json.loads(txt)
        except Exception:
            return None

    def _dec(self, obj):
        """解密响应：data + suffix → AES-256-CBC。"""
        if not obj or not self._have_crypto:
            return None
        data = obj.get("data")
        suffix = obj.get("suffix") or ""
        if not data:
            return None
        iv = (MmavAdapter.IV_PREFIX + suffix).encode("utf-8")
        if len(iv) != 16:
            return None
        try:
            raw = base64.b64decode(data + "=" * (-len(data) % 4))
            if len(raw) % 16:
                return None
            d = self._Cipher(self._algo.AES(MmavAdapter.KEY),
                             self._modes.CBC(iv)).decryptor()
            pt = d.update(raw) + d.finalize()
            n = pt[-1] if pt else 0
            if 1 <= n <= 16:
                pt = pt[:-n]
            return json.loads(pt.decode("utf-8", "replace"))
        except Exception:
            return None

    def _fetch_dec(self, path):
        obj = self._get(path)
        if not obj or obj.get("code") != 0:
            return None
        return self._dec(obj)

    # ---------------- 配置 / 分类 ----------------
    def _config(self):
        if self._cfg is None:
            self._cfg = self._fetch_dec("data/config/base-1.js") or {}
        return self._cfg

    def _img_base(self):
        """封面域名优先级（实测）：
           catsta.tingqian.top 不可达(000)，wzzqlm 与 m3m 可用。
           用 image_domain（服务端下发）优先，img_host 已失效作兜底。"""
        cfg = self._config()
        return ((cfg.get("image_domain") or cfg.get("mm_web_image_domain")
                 or cfg.get("image_url") or MmavAdapter.IMG_FALLBACK)).rstrip("/")

    def _video_base(self):
        """播放域名（客户端 SpUtil 的 MmAvVideo ← config.m3u8_host_encrypt）。
           实测只有 cf-worker-r2.mtzionhub.com 对 m3u8 返回 200，其余 403。"""
        cfg = self._config()
        return (cfg.get("m3u8_host_encrypt")
                or cfg.get("m3u8_host_encrypt1")
                or MmavAdapter.VIDEO_FALLBACK).rstrip("/")

    # ---------------- wsSecret 播放签名 ----------------
    # 反汇编还原（url_util.dart::mmAvVideo + str_util.dart::wsSecret）：
    #   mmAvVideo(path) = wsSecret(SALT, host + path)
    #   wsSecret(salt, url):
    #       expire = now_seconds + 7200
    #       secret = md5( salt + uri.path + expire )
    #       → url?wsSecret=<secret>&wsTime=<expire>&ip=<ip>
    @staticmethod
    def _ws_sign(url, salt=None, ttl=7200, ip="0.0.0.0"):
        salt = salt or MmavAdapter.WS_SALT
        try:
            expire = int(time.time()) + int(ttl)
            path = urllib.parse.urlparse(url).path
            secret = hashlib.md5(
                ("%s%s%d" % (salt, path, expire)).encode()).hexdigest()
            return "%s?wsSecret=%s&wsTime=%d&ip=%s" % (url, secret, expire, ip)
        except Exception:
            return url

    def categories(self):
        if self._cats is not None:
            return self._cats
        menus = self._fetch_dec("data/category/base-1.js")
        cats = []
        if isinstance(menus, dict):
            tree = menus.get("menus") or {}
            for gid, group in tree.items():
                if not isinstance(group, dict):
                    continue
                subs = []
                for it in group.get("data") or []:
                    if not isinstance(it, dict):
                        continue
                    sid = it.get("id")
                    sname = it.get("name") or it.get("jump_name")
                    if sid is None or not sname:
                        continue
                    subs.append({"type_id": str(sid), "type_name": str(sname)})
                    self._cat_map[str(sid)] = str(sname)
                if subs:
                    cats.append({
                        "type_id": str(gid),
                        "type_name": group.get("name") or ("分类" + str(gid)),
                        "sub_categories": subs,
                    })
        # 兜底：media_video 频道已知有数据的分类
        if not cats:
            cats = [{"type_id": str(i), "type_name": n} for i, n in
                    ((7, "国产传媒"), (9, "素人自拍"), (12, "日本AV"),
                     (2, "麻豆"), (3, "直播"), (4, "动漫"), (5, "网黄"), (6, "绳艺"))]
        self._cats = cats
        return cats

    def _norm_cid(self, tid):
        """目录模式传 tid 可能是 'mmav_7' 复合格式，或纯 id。"""
        t = str(tid)
        if "_" in t:
            parts = t.split("_", 1)
            if parts[0] == "mmav":
                return parts[1]
        return t

    def list(self, tid, page):
        cid = self._norm_cid(tid)
        page = max(1, int(page or 1))
        # 模板：data/mediaVideo/list-{cid}-{page}-50.js
        # 实测（2026-11-02）中间数字是「页码」不是偏移量：
        #   page=1 -> current_page=1 首条 54433
        #   page=2 -> current_page=2 首条 50526
        #   page=3 -> current_page=3 首条 47571
        #   若误传偏移(51/101)，会变成第 51/101 页并返回空
        obj = self._fetch_dec(
            "data/mediaVideo/list-%s-%d-50.js" % (cid, page))
        out = []
        if not obj:
            return out
        lst = obj.get("list") or {}
        items = lst.get("data") if isinstance(lst, dict) else None
        if not isinstance(items, list):
            return out
        base = self._img_base()
        for it in items:
            if not isinstance(it, dict):
                continue
            vid = it.get("id")
            if vid is None:
                continue
            cover = it.get("cover") or it.get("thumb") or ""
            pic = cover
            if cover and not cover.startswith("http"):
                pic = base + cover
            self._vid_map[str(vid)] = {
                "video_url": it.get("video_url") or "",
                "cover": cover,
                "title": it.get("title") or str(vid),
                "category_id": it.get("category_id"),
            }
            out.append({
                "vod_id": str(vid),
                "vod_name": it.get("title") or str(vid),
                "vod_pic": pic,
                "vod_remarks": str(it.get("resolution") or "") + " / " +
                              str(it.get("duration_seconds") or "") + "s",
            })
        return out

    def detail(self, vid):
        info = self._vid_map.get(str(vid))
        if info:
            base = self._img_base()
            pic = info["cover"]
            if pic and not pic.startswith("http"):
                pic = base + pic
            return {
                "vod_id": str(vid),
                "vod_name": info.get("title") or str(vid),
                "vod_pic": pic,
            }
        return {"vod_id": str(vid), "vod_name": str(vid)}

    def play(self, vid):
        """播放：video_url 是相对路径，需拼播放域名 + wsSecret 签名。

        实测（2026-11-02）：
          域名 cf-worker-r2.mtzionhub.com + 正确签名 → 200 application/vnd.apple.mpegurl
          该 m3u8 为 VOD 播放列表，内部分片 URL 已自带签名，播放器可直读。
        """
        info = self._vid_map.get(str(vid))
        if not info:
            return None
        rel = info.get("video_url") or ""
        if not rel:
            return None
        if rel.startswith("http"):
            full = rel
        else:
            full = self._video_base() + rel
        signed = self._ws_sign(full)
        return {
            "parse": 0,
            "url": signed,
            "header": {"User-Agent": UA_IOS},
        }


# ============================================================ 注册表
ADAPTERS = {
    "rryy": RryyAdapter,
    "one": OneAdapter,
    "hdb": HdbAdapter,
    "mmav": MmavAdapter,
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
        self._last_adapter = None  # 目录模式下记录最近一次 categoryContent 用到的 adapter

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

        # one token 注入（优先级：extend > 环境变量 > 内置常量）
        # 6868 splash 已加固，无法自动拉取，只能外部喂入。
        tok = ext.get("one_token") or os.environ.get("ONE_TOKEN")
        uid = ext.get("one_uuid") or os.environ.get("ONE_UUID")
        if tok:
            try:
                OneAdapter.apply_token(tok, uid)
            except Exception:
                pass

        # 其它平台 host 覆盖：extend 里形如 {"hosts": {"hgsp": "https://..."}}
        hosts = ext.get("hosts")
        if isinstance(hosts, dict):
            for k, v in hosts.items():
                if v:
                    PLATFORM_HOSTS[str(k)] = str(v).rstrip("/")
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
    def fetch_bytes(self, url, headers=None, data=None):
        """返回原始字节（POST 用 data 为 bytes；响应已自动 gzip 解压）。"""
        h = {"User-Agent": UA_IOS, "Accept": "*/*", "Accept-Encoding": "gzip"}
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

    def _adapter_for(self, key):
        """按平台 key 动态取 adapter（目录模式用）。

        目录模式（MODULE=""）下，客户端把 31 个平台当分类返回，
        点某个平台 → categoryContent(tid=平台key) → 需要按 key 路由到
        对应 Adapter（而非固定 MODULE）。未适配 key 返回 None。
        """
        cls = ADAPTERS.get(str(key))
        if cls is None:
            return None
        try:
            return cls(self)
        except Exception:
            return None

    # ---------------- vbox 方法 ----------------
    def homeContent(self, filter):
        adapter = self._get_adapter()
        if adapter is not None:
            classes = adapter.categories()
            if not classes:
                classes = [{"type_id": "1", "type_name": "全部"}]
            return {"class": classes, "list": []}

        # 目录模式：未设 MODULE 时把 31 个平台当一级分类返回，
        # 已适配平台（rryy/one）附加 sub_categories（二级分类），
        # type_id 用「平台key_分类id」复合格式保证全局唯一，便于
        # categoryContent 解析出平台 + 分类。
        # 注意：mw（漫蛙）/ live（直播盒子）已独立平铺，不在此列出。
        if not self.MODULE:
            # 独立平铺、不应出现在聚合目录里的 key
            excluded = {"mw", "live"}
            classes = []
            for m in CATALOG:
                key = m["key"]
                if key in excluded:
                    continue
                item = {"type_id": key, "type_name": m["name"]}
                cls = ADAPTERS.get(key)
                if cls is not None:
                    try:
                        tmp = cls(self)
                        subs = tmp.categories()
                        if subs:
                            item["sub_categories"] = [
                                {"type_id": "%s_%s" % (key, s["type_id"]),
                                 "type_name": s["type_name"]}
                                for s in subs
                            ]
                    except Exception:
                        pass
                classes.append(item)
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
        # 目录模式：MODULE 为空 → 客户端把「平台 key」或「平台key_分类id」当 tid 传入
        if adapter is None and not self.MODULE:
            tid = str(tid)
            # 复合格式 rryy_yuma → 平台 key=rryy，分类 id=yuma
            if "_" in tid:
                pkey, _, sub_id = tid.partition("_")
                adapter = self._adapter_for(pkey)
                if adapter is not None:
                    # 把真实分类 id 传给 adapter
                    tid = sub_id
            else:
                adapter = self._adapter_for(tid)
        if adapter is None:
            return empty
        # 记录最近 adapter，供目录模式下 detailContent/playerContent 复用
        self._last_adapter = adapter
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
        # 目录模式：复用最近一次 categoryContent 路由到的 adapter
        if adapter is None and not self.MODULE:
            adapter = self._last_adapter
        if adapter is None or not vid:
            return {"list": []}
        try:
            d = adapter.detail(vid) or {}
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
            "vod_play_from": self.getName(),
            "vod_play_url": play_url,
        }
        if d.get("images"):
            item["vod_play_url"] = "#".join(["%s$%s" % (name, u) for u in d["images"]]) or play_url
        return {"list": [item]}

    def playerContent(self, flag, id, vipFlags):
        adapter = self._get_adapter()
        # 目录模式：复用最近一次 categoryContent 路由到的 adapter
        if adapter is None and not self.MODULE:
            adapter = self._last_adapter
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
