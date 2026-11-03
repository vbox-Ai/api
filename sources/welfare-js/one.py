#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""one（one）— vbox 自包含适配器

由 muse_avbox.py 的 OneAdapter 抽取生成，单文件无外部依赖（客户端只下载本文件）。
协议：AES-128-CBC + MD5 签名

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




# ============================================================ vbox 入口
class Spider(SpiderBase):
    MODULE = "one"
    NAME = "one"
    ADAPTER = OneAdapter
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
        tok = ext.get("one_token") or os.environ.get("ONE_TOKEN")
        uid = ext.get("one_uuid") or os.environ.get("ONE_UUID")
        if tok:
            try:
                OneAdapter.apply_token(tok, uid)
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
