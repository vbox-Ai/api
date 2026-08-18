# -*- coding: utf-8 -*-
"""
黄豆短剧 vbox Python Spider — 纯 Python AES 适配版 (v2)
站点: https://xqjzvcvt.top

v2 改动（基于 huangdou.py v1）：
1. pycryptodome/cryptography AES → 纯 Python AES-256-CBC（零第三方依赖，复用 fulao2.py AES 实现）
2. 域名注入 _vbox_effective_hosts
3. 补全 homeVideoContent 方法
4. urllib3 警告抑制 + session.verify=False
5. isVideoFormat / manualVideoCheck
6. HTTP→HTTPS 转换（iOS ATS 合规）
"""
import gzip
import hashlib
import hmac
import json
import os
import sys
import time
import uuid
import urllib.parse

import requests

try:
    import urllib3
    urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
except Exception:
    pass

sys.path.append('..')
try:
    from base.spider import Spider as BaseSpider
except Exception:
    class BaseSpider:
        pass

# ============================================================
# 纯 Python AES 实现（支持 AES-128/256 CBC）— 复用自 fulao2.py
# ============================================================
_sbox = [
    99,124,119,123,242,107,111,197,48,1,103,43,254,215,171,118,202,130,201,125,250,89,71,240,173,212,162,175,156,164,114,192,
    183,253,147,38,54,63,247,204,52,165,229,241,113,216,49,21,4,199,35,195,24,150,5,154,7,18,128,226,235,39,178,117,
    9,131,44,26,27,110,90,160,82,59,214,179,41,227,47,132,83,209,0,237,32,252,177,91,106,203,190,57,74,76,88,207,
    208,239,170,251,67,77,51,133,69,249,2,127,80,60,159,168,81,163,64,143,146,157,56,245,188,182,218,33,16,255,243,210,
    205,12,19,236,95,151,68,23,196,167,126,61,100,93,25,115,96,129,79,220,34,42,144,136,70,238,184,20,222,94,11,219,
    224,50,58,10,73,6,36,92,194,211,172,98,145,149,228,121,231,200,55,109,141,213,78,169,108,86,244,234,101,122,174,8,
    186,120,37,46,28,166,180,198,232,221,116,31,75,189,139,138,112,62,181,102,72,3,246,14,97,53,87,185,134,193,29,158,
    225,248,152,17,105,217,142,148,155,30,135,233,206,85,40,223,140,161,137,13,191,230,66,104,65,153,45,15,176,84,187,22]
_inv_sbox = [
    82,9,106,213,48,54,165,56,191,64,163,158,129,243,215,251,124,227,57,130,155,47,255,135,52,142,67,68,196,222,233,203,
    84,123,148,50,166,194,35,61,238,76,149,11,66,250,195,78,8,46,161,102,40,217,36,178,118,91,162,73,109,139,209,37,
    114,248,246,100,134,104,152,22,212,164,92,204,93,101,182,146,108,112,72,80,253,237,185,218,94,21,70,87,167,141,157,132,
    144,216,171,0,140,188,211,10,247,228,88,5,184,179,69,6,208,44,30,143,202,63,15,2,193,175,189,3,1,19,138,107,
    58,145,17,65,79,103,220,234,151,242,207,206,240,180,230,115,150,172,116,34,231,173,53,133,226,249,55,232,28,117,223,110,
    71,241,26,113,29,41,197,137,111,183,98,14,170,24,190,27,252,86,62,75,198,210,121,32,154,219,192,254,120,205,90,244,
    31,221,168,51,136,7,199,49,177,18,16,89,39,128,236,95,96,81,127,169,25,181,74,13,45,229,122,159,147,201,156,239,
    160,224,59,77,174,42,245,176,200,235,187,60,131,83,153,97,23,43,4,126,186,119,214,38,225,105,20,99,85,33,12,125]
_rcon = [0,1,2,4,8,16,32,64,128,27,54,108,212,137,51]

def _gmul(a, b):
    p = 0
    for _ in range(8):
        if b & 1: p ^= a
        hi = a & 0x80; a = ((a << 1) & 0xff) ^ (0x1b if hi else 0); b //= 2
    return p

def _subw(w): return [_sbox[x] for x in w]
def _rotw(w): return w[1:] + w[:1]

def _expand_key(k):
    Nk = len(k) // 4; Nr = Nk + 6
    w = [list(k[i:i+4]) for i in range(0, len(k), 4)]
    for i in range(Nk, 4 * (Nr + 1)):
        t = w[i - 1][:]
        if i % Nk == 0:
            t = _subw(_rotw(t)); t[0] ^= _rcon[i // Nk]
        elif Nk > 6 and i % Nk == 4:
            t = _subw(t)
        w.append([w[i - Nk][j] ^ t[j] for j in range(4)])
    return [sum(w[4*r:4*r+4], []) for r in range(Nr + 1)], Nr

def _add_round_key(s, rk):
    for c in range(4):
        for r in range(4): s[r][c] ^= rk[4 * c + r]

def _inv_shift_rows(s):
    s[1] = s[1][-1:] + s[1][:-1]; s[2] = s[2][-2:] + s[2][:-2]; s[3] = s[3][-3:] + s[3][:-3]

def _inv_sub_bytes(s):
    for r in range(4):
        for c in range(4): s[r][c] = _inv_sbox[s[r][c]]

def _inv_mix_columns(s):
    for c in range(4):
        a = [s[r][c] for r in range(4)]
        s[0][c] = _gmul(a[0], 14) ^ _gmul(a[1], 11) ^ _gmul(a[2], 13) ^ _gmul(a[3], 9)
        s[1][c] = _gmul(a[0], 9) ^ _gmul(a[1], 14) ^ _gmul(a[2], 11) ^ _gmul(a[3], 13)
        s[2][c] = _gmul(a[0], 13) ^ _gmul(a[1], 9) ^ _gmul(a[2], 14) ^ _gmul(a[3], 11)
        s[3][c] = _gmul(a[0], 11) ^ _gmul(a[1], 13) ^ _gmul(a[2], 9) ^ _gmul(a[3], 14)

def _aes_block_decrypt(block, key):
    rks, Nr = _expand_key(key)
    s = [[block[4 * c + r] for c in range(4)] for r in range(4)]
    _add_round_key(s, rks[Nr])
    for rnd in range(Nr - 1, 0, -1):
        _inv_shift_rows(s); _inv_sub_bytes(s); _add_round_key(s, rks[rnd]); _inv_mix_columns(s)
    _inv_shift_rows(s); _inv_sub_bytes(s); _add_round_key(s, rks[0])
    return bytes(s[r][c] for c in range(4) for r in range(4))

def _aes_block_encrypt(block, key):
    rks, Nr = _expand_key(key)
    s = [[block[4 * c + r] for c in range(4)] for r in range(4)]
    _add_round_key(s, rks[0])
    for rnd in range(1, Nr):
        for r in range(4):
            for c in range(4): s[r][c] = _sbox[s[r][c]]
        s[1] = s[1][1:] + s[1][:1]; s[2] = s[2][2:] + s[2][:2]; s[3] = s[3][3:] + s[3][:3]
        for c in range(4):
            a = [s[r][c] for r in range(4)]
            s[0][c] = _gmul(a[0], 2) ^ _gmul(a[1], 3) ^ a[2] ^ a[3]
            s[1][c] = a[0] ^ _gmul(a[1], 2) ^ _gmul(a[2], 3) ^ a[3]
            s[2][c] = a[0] ^ a[1] ^ _gmul(a[2], 2) ^ _gmul(a[3], 3)
            s[3][c] = _gmul(a[0], 3) ^ a[1] ^ a[2] ^ _gmul(a[3], 2)
        _add_round_key(s, rks[rnd])
    for r in range(4):
        for c in range(4): s[r][c] = _sbox[s[r][c]]
    s[1] = s[1][1:] + s[1][:1]; s[2] = s[2][2:] + s[2][:2]; s[3] = s[3][3:] + s[3][:3]
    _add_round_key(s, rks[Nr])
    return bytes(s[r][c] for c in range(4) for r in range(4))

def _aes_cbc_decrypt_pure(ct, key, iv):
    """AES-CBC 解密 + PKCS7 unpad"""
    out = b''; prev = iv
    for i in range(0, len(ct), 16):
        block = ct[i:i+16]
        if len(block) < 16:
            break
        dec = _aes_block_decrypt(block, key)
        out += bytes(a ^ b for a, b in zip(dec, prev))
        prev = block
    if out:
        pad = out[-1]
        if 1 <= pad <= 16 and out.endswith(bytes([pad]) * pad):
            out = out[:-pad]
    return out

def _aes_cbc_encrypt_pure(pt, key, iv):
    """AES-CBC 加密 + PKCS7 pad"""
    pad_len = 16 - (len(pt) % 16)
    pt = pt + bytes([pad_len]) * pad_len
    out = b''; prev = iv
    for i in range(0, len(pt), 16):
        block = pt[i:i+16]
        xored = bytes(a ^ b for a, b in zip(block, prev))
        enc = _aes_block_encrypt(xored, key)
        out += enc; prev = enc
    return out


class Spider(BaseSpider):

    def __init__(self):
        self.proxy = "https://api.uumnet.com/tvbox/api/proxyrequest.php?url="
        self.host = "https://xqjzvcvt.top"
        self.api = self.host + "/api"
        self.name = "黄豆短剧"
        self.platform_key = "7961beb44246e3012ce228d6b5ced05a"
        self.version = "2.0.0"
        self.device_type = "web"
        self.session_id = uuid.uuid4().hex
        self.device_id = self.session_id
        self.token = ""
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                          "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Accept": "*/*",
            "Origin": self.host,
            "Referer": self.host + "/home",
            "Content-Type": "application/octet-stream"
        }
        self.session = requests.Session()
        self.session.headers.update(self.headers)
        self.session.verify = False
        self.class_cache = None
        self.filter_cache = {}

    def init(self, extend=""):
        # 域名注入
        try:
            effective_hosts = globals().get('_vbox_effective_hosts', [])
            if effective_hosts and len(effective_hosts) > 0:
                self.host = effective_hosts[0].rstrip('/')
                print('[黄豆v2] 使用注入域名: ' + self.host)
        except Exception as e:
            print('[黄豆v2] 读取注入域名失败: ' + str(e))

        # extend 配置覆盖
        if extend:
            try:
                cfg = json.loads(extend)
                self.name = cfg.get("name", self.name)
                base_url = cfg.get("site") or cfg.get("base_url")
                if base_url:
                    self.host = base_url.rstrip("/")
                self.token = cfg.get("token", self.token)
            except Exception:
                pass

        self.api = self.host + "/api"
        self.headers["Origin"] = self.host
        self.headers["Referer"] = self.host + "/home"
        self.session.headers.update(self.headers)

    def getName(self):
        return self.name

    def isVideoFormat(self, url):
        return False

    def manualVideoCheck(self):
        return False

    def homeContent(self, filter):
        data = self._api("/drama/list", {"page": "1", "page_size": "18"})
        classes = self._classes()
        return {
            "class": classes,
            "filters": self._filters(classes),
            "list": [self._vod(x) for x in self._list(data)],
            "parse": 0,
            "jx": 0
        }

    def homeVideoContent(self):
        return {"list": []}

    def categoryContent(self, tid, pg, filter, extend):
        extend = extend or {}
        if tid == "yuandou":
            data = self._api("/drama/navBlock", {"code": "yuandou", "tab": "recommend", "page": str(pg)})
            items = self._nav_items(data)
        else:
            req = {"page": str(pg), "page_size": "18"}
            if tid and tid not in ("all", "recommend"):
                tabs = self._nav_filter(tid)
                idx = self._int(extend.get("sub"), 0)
                sub = tabs[idx] if tabs and 0 <= idx < len(tabs) else {}
                flt = sub.get("filter", {}) if isinstance(sub, dict) else {}
                req["cat_id"] = flt.get("cat_id", "")
                if flt.get("tag_id"):
                    req["tag_id"] = flt.get("tag_id", "")
                req["order"] = flt.get("order", "") or extend.get("order", "")
            elif extend.get("order"):
                req["order"] = extend.get("order")
            if extend.get("update_status"):
                req["update_status"] = extend.get("update_status")
            data = self._api("/drama/list", req)
            items = self._list(data)
        return {
            "page": int(pg),
            "pagecount": int(pg) if len(items) < 18 else int(pg) + 1,
            "limit": 18,
            "total": 99999,
            "list": [self._vod(x) for x in items],
            "parse": 0,
            "jx": 0
        }

    def detailContent(self, ids):
        vid = str(ids[0]).replace("rp_", "")
        obj = self._api("/drama/detail", {"id": vid})
        data = obj.get("data", obj) if isinstance(obj, dict) else {}
        if not isinstance(data, dict):
            return {"list": [], "parse": 0, "jx": 0}
        data = self._unlock(data)
        vod_id = self._sid(data.get("id") or data.get("drama_id") or vid)
        name = data.get("name") or data.get("title") or data.get("t") or vod_id
        eps = data.get("episodes") if isinstance(data.get("episodes"), list) else []
        count = self._int(data.get("episode_count") or data.get("free_episodes"), len(eps) or 1)
        play = []
        if eps:
            for i, ep in enumerate(eps, 1):
                seq = ep.get("seq") or ep.get("episode") or ep.get("ep") or i
                play.append("%s$%s|%s" % (ep.get("name") or ep.get("title") or "第%s集" % seq, vod_id, seq))
        else:
            play = ["第%s集$%s|%s" % (i, vod_id, i) for i in range(1, count + 1)]
        desc = data.get("description") or data.get("summary") or data.get("intro") or name
        vod = {
            "vod_id": vod_id,
            "vod_name": name,
            "vod_pic": self._pic(data),
            "type_name": data.get("category") or data.get("type") or "",
            "vod_year": "",
            "vod_area": "",
            "vod_remarks": data.get("update_label") or "全%s集" % count,
            "vod_actor": "",
            "vod_director": "",
            "vod_content": desc,
            "vod_play_from": self.name,
            "vod_play_url": "#".join(play)
        }
        return {"list": [vod], "parse": 0, "jx": 0}

    def searchContent(self, key, quick, pg="1"):
        data = self._api("/drama/list", {"page": str(pg), "page_size": "18", "keywords": str(key)})
        items = self._list(data)
        return {
            "page": int(pg),
            "pagecount": int(pg) if len(items) < 18 else int(pg) + 1,
            "limit": 18,
            "total": 99999,
            "list": [self._vod(x) for x in items],
            "parse": 0,
            "jx": 0
        }

    def playerContent(self, flag, id, vipFlags):
        vid, seq = self._split(id)
        obj = self._api("/drama/play", {"id": vid, "seq": str(seq)}, True)
        data = obj.get("data", {}) if isinstance(obj, dict) else {}
        url = data.get("m3u8") or data.get("url")
        if not url:
            url = self._hls(vid, seq)
        play_header = {
            "User-Agent": self.headers["User-Agent"],
            "Referer": self.host + "/home",
            "Origin": self.host,
            "Accept": "*/*"
        }
        # HTTP→HTTPS 转换（iOS ATS 合规）
        if url.startswith("http://"):
            url = "https://" + url[7:]
        # URL 编码后走 HTTPS 代理，避免 iOS ATS 拦截
        encoded_url = urllib.parse.quote(url, safe='')
        return {
            "parse": 0,
            "playUrl": "",
            "url": self.proxy + encoded_url,
            "jx": 0,
            "header": play_header,
            "headers": play_header
        }

    # ==================== 加密 API ====================

    def _api(self, path, data=None, silent=False):
        path = "/" + path.lstrip("/")
        rid = str(uuid.uuid4())
        key = self._key(rid)
        iv = os.urandom(16)
        raw = json.dumps({
            "token": self.token or "",
            "deviceId": self.device_id,
            "data": data or {}
        }, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
        body = iv + _aes_cbc_encrypt_pure(gzip.compress(raw), key, iv)
        ts = int(time.time())
        sign = hashlib.sha256(
            ("Dart|%s|%s|%s|%s" % (self.session_id, rid, ts, path)).encode("utf-8")
        ).hexdigest() + "-" + str(ts)
        h = dict(self.headers)
        h.update({
            "version": self.version,
            "deviceType": self.device_type,
            "time": str(ts),
            "sign": sign,
            "requestId": rid,
            "sessionId": self.session_id,
            "deviceBrand": "",
            "deviceModel": "",
            "systemName": "",
            "systemVersion": ""
        })
        try:
            r = self.session.post(self.api + path, data=body, headers=h, timeout=20, verify=False)
            r.raise_for_status()
            return self._decode(r.content, rid)
        except Exception as e:
            if not silent:
                print("[黄豆v2] API error %s: %s" % (path, e))
            return {}

    def _key(self, rid):
        return hmac.new(
            self.platform_key.encode("utf-8"),
            bytes.fromhex(str(rid).replace("-", "")),
            hashlib.sha256
        ).digest()

    def _decode(self, blob, rid):
        if not blob or len(blob) < 32 or (len(blob) - 16) % 16 != 0:
            try:
                return json.loads(blob.decode("utf-8"))
            except Exception:
                return {}
        plain = _aes_cbc_decrypt_pure(blob[16:], self._key(rid), blob[:16])
        if plain[:2] == b"\x1f\x8b":
            plain = gzip.decompress(plain)
        return json.loads(plain.decode("utf-8"))

    # ==================== 数据处理 ====================

    def _classes(self):
        if self.class_cache:
            return self.class_cache
        arr = [{"type_id": "all", "type_name": "全部短剧"}]
        data = self._api("/drama/navList", {})
        for item in self._list(data.get("data", data) if isinstance(data, dict) else data):
            tid = str(item.get("code") or item.get("id") or item.get("cat_id") or "")
            name = item.get("name") or item.get("title") or tid
            if tid and name:
                arr.append({"type_id": tid, "type_name": name})
        self.class_cache = arr
        return arr

    def _filters(self, classes):
        common = [
            {"key": "order", "name": "排序", "value": [
                {"n": "默认", "v": ""},
                {"n": "最新", "v": "new"},
                {"n": "最热", "v": "hot"},
            ]},
            {"key": "update_status", "name": "状态", "value": [
                {"n": "全部", "v": ""},
                {"n": "连载", "v": "0"},
                {"n": "完结", "v": "1"},
            ]}
        ]
        fs = {}
        for c in classes:
            tid = c["type_id"]
            tabs = self._nav_filter(tid) if tid not in ("all", "yuandou") else []
            fs[tid] = ([{
                "key": "sub", "name": "子分类",
                "value": [{"n": t.get("name", "默认"), "v": str(i)} for i, t in enumerate(tabs)]
            }] if tabs else []) + common
        return fs

    def _nav_filter(self, code):
        if code not in self.filter_cache:
            data = self._api("/drama/navFilter", {"code": str(code)})
            self.filter_cache[code] = self._list(data.get("data", data) if isinstance(data, dict) else data)
        return self.filter_cache.get(code, [])

    def _list(self, data):
        if isinstance(data, list):
            return data
        if not isinstance(data, dict):
            return []
        if isinstance(data.get("list"), list):
            return data["list"]
        if isinstance(data.get("items"), list):
            return data["items"]
        if isinstance(data.get("data"), list):
            return data["data"]
        if isinstance(data.get("data"), dict):
            return self._list(data["data"])
        return []

    def _nav_items(self, data):
        blocks = self._list(data.get("data", data) if isinstance(data, dict) else data)
        items = []
        for b in blocks:
            if isinstance(b, dict) and isinstance(b.get("items"), list):
                items += b.get("items")
            elif isinstance(b, dict) and (b.get("id") or b.get("drama_id")):
                items.append(b)
        return items

    def _vod(self, item):
        item = item or {}
        vid = self._sid(item.get("id") or item.get("drama_id") or "")
        remarks = item.get("update_label") or item.get("corner") or ""
        if not remarks:
            ep_count = item.get("episode_count")
            if ep_count:
                remarks = "全%s集" % ep_count
        return {
            "vod_id": vid,
            "vod_name": item.get("name") or item.get("title") or item.get("t") or vid,
            "vod_pic": self._pic(item),
            "vod_remarks": remarks
        }

    def _pic(self, item):
        return (
            item.get("img_x") or item.get("img") or item.get("img_y") or
            item.get("cover") or item.get("pic") or ""
        )

    def _unlock(self, d):
        eps = d.get("episodes")
        if isinstance(eps, list):
            for ep in eps:
                if isinstance(ep, dict):
                    ep["is_buy"] = True
                    ep["type"] = "free"
                    ep["price"] = 0
                    ep["methods"] = []
        d.update({
            "pay_type": "free",
            "money": 0,
            "episode_price": 0,
            "points_price": 0,
            "can_vip_watch": True,
            "is_buy_whole": True,
            "vip_episodes": [],
            "coin_episodes": [],
            "points_episodes": []
        })
        return d

    def _sid(self, x):
        return str(x or "").replace("rp_", "")

    def _split(self, x):
        p = str(x).split("|", 1)
        return self._sid(p[0]), p[1] if len(p) > 1 and p[1] else "1"

    def _hls(self, vid, seq):
        return "%s/api/drama/hls/%s/%s/play.m3u8?line=free" % (self.host, self._sid(vid), seq)

    def _int(self, x, d=0):
        try:
            return int(x)
        except Exception:
            return d
