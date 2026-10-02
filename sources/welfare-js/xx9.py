# -*- coding: utf-8 -*-
"""
xx9 - vbox 远程源适配版
网关: pl5kjl.jas49cht5sqrwet.xyz 等 (AES-128-ECB 加密 JSON, time%10 选钥)
播放线路: 国线1-4 + 海线1 (域名映射 vodFullPlayUrl)
适配: 继承 SpiderBase + super().init(extend) + localProxy三元组
     + 3网关并发竞速(首个成功网关缓存10分钟) + 纯Python AES 兜底
     + 封面走本地代理
"""
import sys
sys.path.append('..')
import json
import time
import base64
import threading
import ssl
import urllib.request
import urllib.parse
import urllib.error
from urllib.parse import quote, unquote

_SSL_CTX = ssl.create_default_context()
_SSL_CTX.check_hostname = False
_SSL_CTX.verify_mode = ssl.CERT_NONE

try:
    from Crypto.Cipher import AES as FastAES
except Exception:
    try:
        from Cryptodome.Cipher import AES as FastAES
    except Exception:
        FastAES = None


# ================= 纯 Python AES-128 ECB (pycryptodome 缺失时兜底) =================
_SBOX = [
    0x63,0x7c,0x77,0x7b,0xf2,0x6b,0x6f,0xc5,0x30,0x01,0x67,0x2b,0xfe,0xd7,0xab,0x76,
    0xca,0x82,0xc9,0x7d,0xfa,0x59,0x47,0xf0,0xad,0xd4,0xa2,0xaf,0x9c,0xa4,0x72,0xc0,
    0xb7,0xfd,0x93,0x26,0x36,0x3f,0xf7,0xcc,0x34,0xa5,0xe5,0xf1,0x71,0xd8,0x31,0x15,
    0x04,0xc7,0x23,0xc3,0x18,0x96,0x05,0x9a,0x07,0x12,0x80,0xe2,0xeb,0x27,0xb2,0x75,
    0x09,0x83,0x2c,0x1a,0x1b,0x6e,0x5a,0xa0,0x52,0x3b,0xd6,0xb3,0x29,0xe3,0x2f,0x84,
    0x53,0xd1,0x00,0xed,0x20,0xfc,0xb1,0x5b,0x6a,0xcb,0xbe,0x39,0x4a,0x4c,0x58,0xcf,
    0xd0,0xef,0xaa,0xfb,0x43,0x4d,0x33,0x85,0x45,0xf9,0x02,0x7f,0x50,0x3c,0x9f,0xa8,
    0x51,0xa3,0x40,0x8f,0x92,0x9d,0x38,0xf5,0xbc,0xb6,0xda,0x21,0x10,0xff,0xf3,0xd2,
    0xcd,0x0c,0x13,0xec,0x5f,0x97,0x44,0x17,0xc4,0xa7,0x7e,0x3d,0x64,0x5d,0x19,0x73,
    0x60,0x81,0x4f,0xdc,0x22,0x2a,0x90,0x88,0x46,0xee,0xb8,0x14,0xde,0x5e,0x0b,0xdb,
    0xe0,0x32,0x3a,0x0a,0x49,0x06,0x24,0x5c,0xc2,0xd3,0xac,0x62,0x91,0x95,0xe4,0x79,
    0xe7,0xc8,0x37,0x6d,0x8d,0xd5,0x4e,0xa9,0x6c,0x56,0xf4,0xea,0x65,0x7a,0xae,0x08,
    0xba,0x78,0x25,0x2e,0x1c,0xa6,0xb4,0xc6,0xe8,0xdd,0x74,0x1f,0x4b,0xbd,0x8b,0x8a,
    0x70,0x3e,0xb5,0x66,0x48,0x03,0xf6,0x0e,0x61,0x35,0x57,0xb9,0x86,0xc1,0x1d,0x9e,
    0xe1,0xf8,0x98,0x11,0x69,0xd9,0x8e,0x94,0x9b,0x1e,0x87,0xe9,0xce,0x55,0x28,0xdf,
    0x8c,0xa1,0x89,0x0d,0xbf,0xe6,0x42,0x68,0x41,0x99,0x2d,0x0f,0xb0,0x54,0xbb,0x16,
]
_INV_SBOX = [0]*256
for _i, _v in enumerate(_SBOX):
    _INV_SBOX[_v] = _i
_RCON = [0x00,0x01,0x02,0x04,0x08,0x10,0x20,0x40,0x80,0x1b,0x36]


def _xtime(a):
    return ((a << 1) ^ 0x1b) & 0xff if a & 0x80 else a << 1


class PureAES128:
    """纯 Python AES-128 ECB (加/解密), 与 pycryptodome 结果一致 (FIPS-197)"""

    def __init__(self, key):
        if len(key) != 16:
            raise ValueError("PureAES128 仅支持 16 字节密钥")
        w = [list(key[4*i:4*i+4]) for i in range(4)]
        for i in range(4, 44):
            temp = list(w[i-1])
            if i % 4 == 0:
                temp = temp[1:] + temp[:1]
                temp = [_SBOX[b] for b in temp]
                temp[0] ^= _RCON[i//4]
            w.append([a ^ b for a, b in zip(w[i-4], temp)])
        self.round_keys = [w[i*4:(i+1)*4] for i in range(11)]

    def _add_round_key(self, s, rnd):
        k = self.round_keys[rnd]
        for r in range(4):
            for c in range(4):
                s[r + 4*c] ^= k[c][r]

    def encrypt_block(self, blk):
        s = list(blk)
        self._add_round_key(s, 0)
        for rnd in range(1, 10):
            for i in range(16):
                s[i] = _SBOX[s[i]]
            s = self._shift_rows(s)
            s = self._mix(s)
            self._add_round_key(s, rnd)
        for i in range(16):
            s[i] = _SBOX[s[i]]
        s = self._shift_rows(s)
        self._add_round_key(s, 10)
        return bytes(s)

    def _shift_rows(self, s):
        out = [0]*16
        for r in range(4):
            for c in range(4):
                out[r + 4*c] = s[r + 4*((c + r) % 4)]
        return out

    def _mix(self, s):
        out = [0]*16
        for c in range(4):
            a0, a1, a2, a3 = s[4*c], s[4*c+1], s[4*c+2], s[4*c+3]
            out[4*c]   = _xtime(a0) ^ (_xtime(a1) ^ a1) ^ a2 ^ a3
            out[4*c+1] = a0 ^ _xtime(a1) ^ (_xtime(a2) ^ a2) ^ a3
            out[4*c+2] = a0 ^ a1 ^ _xtime(a2) ^ (_xtime(a3) ^ a3)
            out[4*c+3] = (_xtime(a0) ^ a0) ^ a1 ^ a2 ^ _xtime(a3)
        return out

    def decrypt_block(self, blk):
        s = list(blk)
        self._add_round_key(s, 10)
        for rnd in range(9, 0, -1):
            s = self._inv_shift_rows(s)
            for i in range(16):
                s[i] = _INV_SBOX[s[i]]
            self._add_round_key(s, rnd)
            s = self._inv_mix(s)
        s = self._inv_shift_rows(s)
        for i in range(16):
            s[i] = _INV_SBOX[s[i]]
        self._add_round_key(s, 0)
        return bytes(s)

    def _inv_shift_rows(self, s):
        out = [0]*16
        for r in range(4):
            for c in range(4):
                out[r + 4*c] = s[r + 4*((c - r) % 4)]
        return out

    def _inv_mix(self, s):
        def gmul(a, b):
            res = 0
            while b:
                if b & 1:
                    res ^= a
                a = _xtime(a)
                b >>= 1
            return res
        out = [0]*16
        for c in range(4):
            a0, a1, a2, a3 = s[4*c], s[4*c+1], s[4*c+2], s[4*c+3]
            out[4*c]   = gmul(a0,0x0e) ^ gmul(a1,0x0b) ^ gmul(a2,0x0d) ^ gmul(a3,0x09)
            out[4*c+1] = gmul(a0,0x09) ^ gmul(a1,0x0e) ^ gmul(a2,0x0b) ^ gmul(a3,0x0d)
            out[4*c+2] = gmul(a0,0x0d) ^ gmul(a1,0x09) ^ gmul(a2,0x0e) ^ gmul(a3,0x0b)
            out[4*c+3] = gmul(a0,0x0b) ^ gmul(a1,0x0d) ^ gmul(a2,0x09) ^ gmul(a3,0x0e)
        return out

    def ecb_encrypt(self, data):
        out = bytearray()
        for i in range(0, len(data), 16):
            out.extend(self.encrypt_block(data[i:i+16]))
        return bytes(out)

    def ecb_decrypt(self, data):
        out = bytearray()
        for i in range(0, len(data), 16):
            out.extend(self.decrypt_block(data[i:i+16]))
        return bytes(out)


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

    PLATFORM_KEY = "xx9_py"
    GW_TTL = 600  # 竞速胜者网关缓存 10 分钟

    # ---- 站点常量 ----
    GATEWAY_POOL = [
        "https://pl5kjl.jas49cht5sqrwet.xyz/fast-endecode/main/request",
        "https://pl5kjl.m93abv5upsv4s8f.xyz/fast-endecode/main/request",
        "https://api.y7hvaad8g.xyz/fast-endecode/main/request",
    ]

    # time%10 -> AES key（index 2 稳定可用，固定使用）
    KEYS = {
        0: "G7i3OPcfNhBnAYpc",
        1: "84UZNK33cSVylz6Y",
        2: "jeSWRcTwHyAKwJDB",
        3: "i1hvJx9vuRt5zEBS",
        4: "1Yy1KOa75R7cnmkg",
        6: "T0RVp7KIPamrtQ33",
        8: "ugvseZc5Kkj8ecmV",
        9: "G7i3OPcfNhBnAYpc",
    }
    REM = 2  # 固定使用 time%10==2 对应的密钥

    ADS_CODE = "DFH"

    # 播放线路（vuex.app.allConfig.h5_play_line）
    PLAY_LINES = [
        ("国线1", "https://rr.rxjhwl.com"),
        ("国线2", "https://ww.wealwelloa.com"),
        ("国线3", "https://cc.cloudworki.com"),
        ("国线4", "https://gg.gmdalian.com"),
        ("海线1", "https://allmusiclub.almusiclub.com"),
    ]

    PIC_BASE = "https://qv1tx2.shoupingxz.com"

    UA = ("Mozilla/5.0 (Linux; Android 11; Pixel 5) AppleWebKit/537.36 "
          "(KHTML, like Gecko) Chrome/120.0.0.0 Mobile Safari/537.36")

    # 专题分类（id -> title），作为 categoryContent 的分类来源
    THEMES = [
        ("27", "国产精选"), ("9", "主播剧情"), ("26", "业余素人"),
        ("47", "第一视角"), ("7", "欧美精选"), ("35", "日韩精选"),
        ("41", "粉嫩处女"), ("66", "偷窥偷拍监控"), ("50", "网爆偷拍泄密"),
        ("39", "AV精选"), ("40", "职业探花"), ("55", "网红裸舞"),
        ("59", "抖音风合集"), ("36", "动漫精选"), ("67", "街拍街射"),
        ("42", "明星AI换脸"), ("15", "经典老片"), ("16", "成人综艺"),
        ("24", "恐怖科幻伦理"), ("19", "官方推荐"),
    ]

    def __init__(self):
        try:
            super(Spider, self).__init__()
        except Exception:
            pass
        self._jwt = None
        self._jwt_ts = 0
        self._access = None
        self._access_ts = 0
        # 网关竞速缓存
        self._gw_winner = None
        self._gw_winner_ts = 0.0
        self._gw_lock = threading.Lock()

    def init(self, extend=""):
        try:
            super().init(extend)
        except AttributeError:
            pass
        self._jwt = None
        self._jwt_ts = 0
        self._access = None
        self._access_ts = 0

    def _rnd(self, n):
        import random
        cs = "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789"
        return "".join(random.choice(cs) for _ in range(n))

    def getName(self):
        return "xx9"

    def isVideoFormat(self, url):
        low = (url or "").lower()
        return ".m3u8" in low or ".mp4" in low

    def manualVideoCheck(self):
        return False

    def destroy(self):
        return

    # ================= 加密辅助 =================
    def _pad(self, b):
        n = 16 - (len(b) % 16)
        return b + bytes([n]) * n

    def _unpad(self, b):
        if not b:
            return b
        return b[:-b[-1]]

    def _enc(self, obj, key):
        raw = json.dumps(obj, ensure_ascii=False, separators=(',', ':')).encode('utf-8')
        if FastAES is not None:
            c = FastAES.new(key.encode('utf-8'), FastAES.MODE_ECB)
            return base64.b64encode(c.encrypt(self._pad(raw))).decode()
        c = PureAES128(key.encode('utf-8'))
        return base64.b64encode(c.ecb_encrypt(self._pad(raw))).decode()

    def _dec(self, b64, key):
        kb = key.encode('utf-8')
        if FastAES is not None:
            c = FastAES.new(kb, FastAES.MODE_ECB)
            raw = self._unpad(c.decrypt(base64.b64decode(b64)))
        else:
            c = PureAES128(kb)
            raw = self._unpad(c.ecb_decrypt(base64.b64decode(b64)))
        return raw.decode('utf-8')

    def _mktime(self):
        t = int(time.time() * 1000)
        return t - (t % 10) + self.REM

    # ================= 网关并发竞速 =================
    def _post_gw(self, gw, payload, headers):
        """POST JSON 到网关, 返回响应 text; 失败返回 None"""
        try:
            body = json.dumps(payload).encode('utf-8')
            h = dict(headers)
            h["Content-Type"] = "application/json"
            req = urllib.request.Request(gw, data=body, headers=h)
            with urllib.request.urlopen(req, timeout=10, context=_SSL_CTX) as resp:
                return resp.read().decode('utf-8', 'ignore')
        except Exception:
            return None

    def _get_gateway(self):
        """多网关并发竞速: 首个成功响应的网关缓存 10 分钟"""
        now = time.time()
        if self._gw_winner and (now - self._gw_winner_ts) < self.GW_TTL:
            return self._gw_winner
        winner = {}
        lock = threading.Lock()

        def _probe(gw):
            if winner.get("gw"):
                return
            ok = False
            try:
                # 轻量探测: GET 网关根, 200 即视为存活
                req = urllib.request.Request(gw, headers={"User-Agent": self.UA})
                with urllib.request.urlopen(req, timeout=8, context=_SSL_CTX) as resp:
                    ok = resp.getcode() in (200, 405, 500)  # 405/500 也说明网关存活
            except urllib.error.HTTPError:
                ok = True  # HTTP 错误也说明可达
            except Exception:
                ok = False
            if ok:
                with lock:
                    if not winner.get("gw"):
                        winner["gw"] = gw

        threads = [threading.Thread(target=_probe, args=(g,), daemon=True) for g in self.GATEWAY_POOL]
        for t in threads:
            t.start()
        deadline = time.time() + 10
        while time.time() < deadline:
            with lock:
                if winner.get("gw"):
                    break
            time.sleep(0.2)

        gw = winner.get("gw") or self.GATEWAY_POOL[0]
        self._gw_winner = gw
        self._gw_winner_ts = time.time()
        return gw

    # ================= 网关请求 =================
    def _call(self, uri, method, params=None, body=None, use_jwt=True, use_access=False, _retry=True):
        key = self.KEYS[self.REM]
        t = self._mktime()
        plain = {"method": method, "uri": uri}
        if body is not None:
            plain["body"] = body
        else:
            plain["params"] = params if params is not None else {}
        payload = {"data": self._enc(plain, key), "time": t}
        headers = {
            "User-Agent": self.UA,
            "Origin": "https://xx9.com",
            "Referer": "https://xx9.com/",
        }
        if use_jwt:
            jwt = self._get_jwt()
            if jwt:
                headers["jwtToken"] = jwt
        if use_access:
            acc = self._get_access()
            if acc:
                headers["accessToken"] = acc

        gw = self._get_gateway()
        text = self._post_gw(gw, payload, headers)
        if text is None:
            # 胜者网关失败, 失效后重新竞速一次
            self._gw_winner = None
            gw = self._get_gateway()
            text = self._post_gw(gw, payload, headers)
        if not text:
            return {}
        try:
            j = json.loads(text)
        except Exception:
            return {}
        # 响应可能是明文, 也可能是 {data:<密文>, time:..} 加密包
        if isinstance(j, dict) and isinstance(j.get("data"), str) and j.get("data") and ("time" in j):
            try:
                j = json.loads(self._dec(j["data"], key))
            except Exception:
                return j
        # accessToken 为空(1032)/过期(1019) -> 刷新后重试一次
        if use_access and _retry and isinstance(j, dict):
            code = str(j.get("code") or "")
            if code in ("1032", "1019"):
                self._access = None
                self._access_ts = 0
                return self._call(uri, method, params=params, body=body,
                                  use_jwt=use_jwt, use_access=use_access, _retry=False)
        return j

    def _get_jwt(self):
        now = time.time()
        if self._jwt and (now - self._jwt_ts) < 3600:
            return self._jwt
        try:
            r = self._call("app/jwt-token", 1, params={"adsCode": self.ADS_CODE}, use_jwt=False)
            jwt = r.get("result") if isinstance(r, dict) else None
            if jwt:
                self._jwt = jwt
                self._jwt_ts = now
        except Exception:
            pass
        return self._jwt

    def _get_access(self):
        now = time.time()
        # accessToken 缓存 30 分钟
        if self._access and (now - self._access_ts) < 1800:
            return self._access
        try:
            body = {
                "osType": "h5",
                "sign": self._rnd(32),
                "machineCode": "chrome",
                "version": "xx9.com",
            }
            r = self._call("user/register/free", 2, body=body, use_jwt=True, use_access=False)
            res = r.get("result") if isinstance(r, dict) else None
            acc = res.get("accessToken") if isinstance(res, dict) else None
            if acc:
                self._access = acc
                self._access_ts = now
        except Exception:
            pass
        return self._access

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
            headers = {"User-Agent": self.UA}
            if referer:
                headers["Referer"] = referer
                headers["Origin"] = referer.rstrip("/")
            req = urllib.request.Request(url, headers=headers)
            with urllib.request.urlopen(req, timeout=15, context=_SSL_CTX) as resp:
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

    # ================= 工具 =================
    def _pic(self, p):
        if not p:
            return ""
        if p.startswith("http"):
            return self._proxy_img_url(p, referer="https://xx9.com/")
        return self._proxy_img_url(self.PIC_BASE + p, referer="https://xx9.com/")

    def _vod_list_item(self, it):
        vid = it.get("id") or it.get("vodId")
        title = it.get("title") or ""
        pic = self._pic(it.get("vodPic") or it.get("gif") or "")
        dur = it.get("vodDuration")
        remark = ""
        if isinstance(dur, int) and dur > 0:
            m, s = divmod(dur, 60)
            remark = "%d:%02d" % (m, s)
        tags = it.get("tags")
        if not remark and isinstance(tags, list) and tags:
            remark = " ".join(tags[:3])
        return {
            "vod_id": str(vid),
            "vod_name": title,
            "vod_pic": pic,
            "vod_remarks": remark,
        }

    def _search(self, params):
        r = self._call("cms/vod/search", 2, params=params)
        data = r.get("data") if isinstance(r, dict) else None
        items = []
        if isinstance(data, list):
            items = data
        elif isinstance(data, dict):
            items = data.get("list") or data.get("records") or []
        total = r.get("total") if isinstance(r, dict) else 0
        return items, (total or 0)

    # ================= 首页 =================
    def homeContent(self, filter):
        classes = [{"type_id": tid, "type_name": name} for tid, name in self.THEMES]
        if not classes:
            classes = [{"type_id": "27", "type_name": "xx9·全部"}]
        filters = {}
        sort_filter = {
            "key": "sort",
            "name": "排序",
            "value": [
                {"n": "最新", "v": "1"},
                {"n": "最热", "v": "2"},
            ],
        }
        for tid, _ in self.THEMES:
            filters[tid] = [sort_filter]
        result = {
            "class": classes,
            "filters": filters,
        }
        return result

    def homeVideoContent(self):
        items, _ = self._search({
            "themeIds": self.THEMES[0][0],
            "page": 1, "pageSize": 30,
            "explore": False, "sortType": 1,
        })
        return {"list": [self._vod_list_item(it) for it in items]}

    # ================= 分类 =================
    def categoryContent(self, tid, pg, filter, extend):
        try:
            page = int(pg)
        except Exception:
            page = 1
        sort_type = 1
        if isinstance(extend, dict):
            sv = extend.get("sort")
            if sv:
                try:
                    sort_type = int(sv)
                except Exception:
                    sort_type = 1
        page_size = 30
        items, total = self._search({
            "themeIds": str(tid),
            "page": page, "pageSize": page_size,
            "explore": False, "sortType": sort_type,
        })
        vod = [self._vod_list_item(it) for it in items]
        pagecount = 9999
        if total:
            pagecount = (int(total) + page_size - 1) // page_size
        return {
            "list": vod,
            "page": page,
            "pagecount": pagecount,
            "limit": page_size,
            "total": int(total) if total else len(vod),
        }

    # ================= 详情 =================
    def detailContent(self, ids):
        vid = ids[0]
        r = self._call("cms/vod/detail/%s" % vid, 1, params={"needCdnAuth": True}, use_access=True)
        res = r.get("result") if isinstance(r, dict) else None
        if isinstance(res, dict):
            vod = res.get("vod", res)
        else:
            vod = res if isinstance(res, dict) else {}
        if not vod:
            return {"list": []}

        title = vod.get("title") or ""
        pic = self._pic(vod.get("vodPic") or "")
        intro = vod.get("vodIntro") or ""
        tags = vod.get("tags")
        if isinstance(tags, list):
            tag_str = ",".join(str(x) for x in tags)
        else:
            tag_str = ""
        dur = vod.get("vodDuration")
        remark = ""
        if isinstance(dur, int) and dur > 0:
            m, s = divmod(dur, 60)
            remark = "时长 %d:%02d" % (m, s)

        full = vod.get("vodFullPlayUrl")
        n_parts = len(full) if isinstance(full, list) and full else 1

        # 每条线路一个 from, 剧集用 # 分隔, 播放 id 编码为 "vid|addrIndex"
        froms = []
        urls = []
        for name, _domain in self.PLAY_LINES:
            eps = []
            if n_parts <= 1:
                eps.append("正片$%s|0" % vid)
            else:
                for i in range(n_parts):
                    eps.append("P%d$%s|%d" % (i + 1, vid, i))
            froms.append(name)
            urls.append("#".join(eps))

        vod_obj = {
            "vod_id": str(vid),
            "vod_name": title,
            "vod_pic": pic,
            "vod_remarks": remark,
            "vod_content": intro or tag_str,
            "vod_tag": tag_str,
            "vod_play_from": "$$$".join(froms),
            "vod_play_url": "$$$".join(urls),
        }
        return {"list": [vod_obj]}

    # ================= 搜索 =================
    def searchContent(self, key, quick, pg="1"):
        try:
            page = int(pg)
        except Exception:
            page = 1
        items, _ = self._search({
            "title": key,
            "page": page, "pageSize": 30,
            "explore": False, "sortType": 1,
        })
        return {"list": [self._vod_list_item(it) for it in items]}

    # ================= 播放 =================
    def playerContent(self, flag, id, vipFlags):
        # id 形如 "vid|addrIndex"; flag 为线路名, 用于选择域名
        vid = id
        idx = 0
        if "|" in str(id):
            vid, sidx = str(id).split("|", 1)
            try:
                idx = int(sidx)
            except Exception:
                idx = 0

        domain = None
        for name, dom in self.PLAY_LINES:
            if name == flag:
                domain = dom
                break
        if not domain:
            domain = self.PLAY_LINES[0][1]

        play_url = ""
        try:
            r = self._call("cms/vod/detail/%s" % vid, 1, params={"needCdnAuth": True}, use_access=True)
            res = r.get("result") if isinstance(r, dict) else None
            vod = res.get("vod", res) if isinstance(res, dict) else {}
            full = vod.get("vodFullPlayUrl")
            addr = None
            if isinstance(full, list) and full:
                if idx >= len(full):
                    idx = 0
                addr = full[idx].get("addr")
            if not addr:
                addr = vod.get("preview")
            if addr:
                play_url = domain + addr
        except Exception:
            play_url = ""

        return {
            "parse": 0,
            "playUrl": "",
            "url": play_url,
            "header": {
                "User-Agent": self.UA,
                "Referer": "https://xx9.com/",
            },
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
