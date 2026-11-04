#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""黄豆瓣（hdb）— vbox 自包含适配器

由 muse_avbox.py 的 HdbAdapter 抽取生成，单文件无外部依赖（客户端只下载本文件）。
协议：RSA-2048 + AES-128-CBC 双向信封

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




# ============================================================ vbox 入口
class Spider(SpiderBase):
    MODULE = "hdb"
    NAME = "黄豆瓣"
    ADAPTER = HdbAdapter
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
        # 内置域名优先、注入域名仅回退（坑表 #15）
        # 之前是"注入即覆盖"：客户端下发的 defaultHosts 一旦过期，列表就全空（分类是静态的，所以表现成"有分类无数据"）
        try:
            inj = _vbox_host(self, "")
            if inj and not getattr(self.ADAPTER, "HOST", ""):
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
