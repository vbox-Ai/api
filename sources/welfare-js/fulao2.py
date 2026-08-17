# -*- coding: utf-8 -*-
"""
Fulao2 TVBox Spider — vbox 适配版
API: api-al.yuytyr.online

vbox 适配：
1. pycryptodome AES → 纯 Python AES-256/128-CBC/ECB
2. 内置 HTTP 服务器 → localProxy 模式
3. playerContent header → dict 格式
4. 继承 base.spider.Spider
"""
import sys, json, base64, gzip, threading, time, hashlib
from urllib.parse import quote, urljoin
from collections import OrderedDict

sys.path.append('..')
try:
    from base.spider import Spider as _B
except ImportError:
    class _B:
        pass
try:
    import requests
except ImportError:
    requests = None

# ============================================================
# 纯 Python AES 实现（支持 AES-128/256）
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
    """AES 单块加密"""
    rks, Nr = _expand_key(key)
    s = [[block[4 * c + r] for c in range(4)] for r in range(4)]
    _add_round_key(s, rks[0])
    for rnd in range(1, Nr):
        # SubBytes
        for r in range(4):
            for c in range(4): s[r][c] = _sbox[s[r][c]]
        # ShiftRows
        s[1] = s[1][1:] + s[1][:1]; s[2] = s[2][2:] + s[2][:2]; s[3] = s[3][3:] + s[3][:3]
        # MixColumns
        for c in range(4):
            a = [s[r][c] for r in range(4)]
            s[0][c] = _gmul(a[0], 2) ^ _gmul(a[1], 3) ^ a[2] ^ a[3]
            s[1][c] = a[0] ^ _gmul(a[1], 2) ^ _gmul(a[2], 3) ^ a[3]
            s[2][c] = a[0] ^ a[1] ^ _gmul(a[2], 2) ^ _gmul(a[3], 3)
            s[3][c] = _gmul(a[0], 3) ^ a[1] ^ a[2] ^ _gmul(a[3], 2)
        _add_round_key(s, rks[rnd])
    # Final round (no MixColumns)
    for r in range(4):
        for c in range(4): s[r][c] = _sbox[s[r][c]]
    s[1] = s[1][1:] + s[1][:1]; s[2] = s[2][2:] + s[2][:2]; s[3] = s[3][3:] + s[3][:3]
    _add_round_key(s, rks[Nr])
    return bytes(s[r][c] for c in range(4) for r in range(4))

def _aes_ecb_encrypt(plaintext, key):
    """AES-ECB 加密（用于 IV 派生）"""
    if len(plaintext) < 16:
        return plaintext
    block = plaintext[:16]
    return _aes_block_encrypt(block, key)

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

# ============================================================
# 配置
# ============================================================
API_DOMAIN = "https://api-al.yuytyr.online"
IMG_DOMAIN = "https://images.yxdesign.art"

REQ_KEY = base64.b64decode("euZN1Gg3JIwWOEWhmE7C4l5dSSRU34fyuPMXjtuoqVs=")
RESP_KEY = b"db6f7f9e5d7a770e0e3497a7d7a077f5"
IMG_KEY = base64.b64decode("svOEKGb5WD0ezmHE4FXCVQ==")
IMG_IV = base64.b64decode("4B7eYzHTevzHvgVZfWVNIg==")

UA_APP = "Fulao2/Android 2.40; Lenovo TB-J606F"
UA_CDN = "com.ilulutv.fulao2.main.MyApplication/2.40 (Linux;Android 11) ExoPlayerLib/2.11.1"
UA_IMG = "Dalvik/2.1.0 (Linux; U; Android 11; Lenovo TB-J606F Build/RKQ1.210303.002)"

TARGET_CATEGORIES = ["推荐", "H动画", "最新", "抢先看", "中字", "NTR", "火爆", "FC2", "91大神", "传媒"]

X_INFO_LAUNCH = "eyJjcGFnZSI6ImxhdW5jaCIsInBsYXRmb3JtIjoyLCJwcGFnZSI6IiIsInZlcnNpb24iOiIyLjQwIn0="
X_INFO_CENSOR = "eyJjcGFnZSI6ImNlbnNvciIsInBsYXRmb3JtIjoyLCJwcGFnZSI6ImxhdW5jaCIsInZlcnNpb24iOiIyLjQwIn0="
X_INFO_PLAY = "eyJjcGFnZSI6InBsYXkiLCJwbGF0Zm9ybSI6MiwicHBhZ2UiOiJjZW5zb3IiLCJ2ZXJzaW9uIjoiMi40MCJ9"

STREAM_HOSTS = [
    ("VIP高速3", "https://stream.yxdesign.art"),
    ("VIP高速1", "https://stream.lingqi.co"),
    ("VIP高速2", "https://stream-hua.hangbo.xyz"),
    ("海外线路", "https://stream.ass6.store"),
]
QUALITIES = [("480", "高清"), ("240", "标清")]

# ============================================================
# LRU 缓存
# ============================================================
class _LRUCache:
    def __init__(self, maxsize=200):
        self._maxsize = maxsize
        self._od = OrderedDict()
    def get(self, key, default=None):
        if key not in self._od: return default
        self._od.move_to_end(key); return self._od[key]
    def __setitem__(self, key, value):
        if key in self._od: self._od.move_to_end(key)
        self._od[key] = value
        if len(self._od) > self._maxsize: self._od.popitem(last=False)
    def __contains__(self, key): return key in self._od
    def clear(self): self._od.clear()

# ============================================================
# Spider
# ============================================================
class Spider(_B):

    def init(self, e=""):
        self.token = ""
        self.sess = requests.Session()
        self.sess.headers.update({
            "user-agent": UA_APP,
            "authorization": "Bearer ",
            "accept-encoding": "gzip",
            "x-info": X_INFO_LAUNCH,
        })
        self._m3u8_cache = _LRUCache(maxsize=300)
        self._img_cache = _LRUCache(maxsize=200)
        self._m3u8_lock = threading.Lock()
        self._get_token()

    def getName(self):
        return "Fulao2"

    def isVideoFormat(self, u):
        return True

    def manualVideoCheck(self):
        return False

    def destroy(self):
        self._m3u8_cache.clear()
        self._img_cache.clear()

    # ==================== 加解密 ====================

    def _encrypt_payload(self, path):
        payload = json.dumps({
            "path": path,
            "device_id": "aeffaaa7-166c-4545-8971-c669ff59f611",
            "utm_medium": "",
            "model": "LENOVOLenovo TB-J606F",
            "universal_id": "3027776cc331ee45",
            "platform": "Android",
            "key": "f7787644a1f6b8e41a580fdfb4501acb9c095dda346567fa82a15c68a55b4ce1",
            "timestamp": "1785928268",
        }, separators=(',', ':'))
        iv = base64.b64decode("B3nBQVSgjRuC09mgsdbgIg==")
        ct = _aes_cbc_encrypt_pure(payload.encode(), REQ_KEY, iv)
        return base64.b64encode(iv).decode() + "." + base64.b64encode(ct).decode()

    def _decrypt_resp(self, text):
        try:
            ct = base64.b64decode(text)
            iv_block = _aes_ecb_encrypt(ct[:16], RESP_KEY)
            marker = b'{"status":{"code'.ljust(16, b'\x00')
            iv = bytes(a ^ b for a, b in zip(iv_block, marker))
            raw = _aes_cbc_decrypt_pure(ct, RESP_KEY, iv)
            if raw[:2] == b'\x1f\x8b':
                raw = gzip.decompress(raw)
            return json.loads(raw.decode())
        except Exception as e:
            print("[Fulao2] decrypt_resp err: " + str(e))
            return None

    def _decrypt_m3u8(self, text):
        try:
            ct = base64.b64decode(text)
            iv_block = _aes_ecb_encrypt(ct[:16], RESP_KEY)
            marker = b'#EXTM3U\n#EXT-X-V'
            iv = bytes(a ^ b for a, b in zip(iv_block, marker))
            raw = _aes_cbc_decrypt_pure(ct, RESP_KEY, iv)
            if raw[:2] == b'\x1f\x8b':
                raw = gzip.decompress(raw)
            return raw.decode('utf-8', errors='ignore')
        except Exception as e:
            print("[Fulao2] decrypt_m3u8 err: " + str(e))
            return None

    def _decrypt_img(self, raw):
        """图片 AES-128-CBC 解密"""
        try:
            dec = _aes_cbc_decrypt_pure(raw, IMG_KEY, IMG_IV)
            if dec:
                return dec
        except Exception:
            pass
        return raw

    def _api(self, method, path, xinfo=None):
        enc = self._encrypt_payload(path)
        url = API_DOMAIN + "/" + path
        h = {}
        if xinfo:
            h["x-info"] = xinfo
        try:
            if method == "POST":
                h["content-type"] = "application/x-www-form-urlencoded"
                r = self.sess.post(url, data="payload=" + quote(enc), headers=h, timeout=15)
            else:
                r = self.sess.get(url + "?payload=" + quote(enc), headers=h, timeout=15)
            if r.status_code == 200:
                return self._decrypt_resp(r.text)
            return None
        except Exception as e:
            print("[Fulao2] api err " + path + " " + str(e))
            return None

    # ==================== Token ====================

    def _get_token(self):
        data = self._api("POST", "v1/register/token")
        if data and "response" in data:
            resp = data["response"]
            self.token = resp.get("token", resp.get("access_token", ""))
            self.sess.headers["authorization"] = "Bearer " + self.token

    # ==================== 代理 URL 构建 ====================

    def _build_proxy_url(self, ptype, key):
        try:
            if hasattr(self, 'getProxyUrl'):
                base = self.getProxyUrl()
                if '?' not in base:
                    base += '?do=py'
                return base + '&type=' + ptype + '&key=' + quote(key, safe='')
        except Exception:
            pass
        return key

    def _img_url(self, path):
        if not path:
            return ""
        if path.startswith("http"):
            full = path
        else:
            full = IMG_DOMAIN + ("" if path.startswith("/") else "/") + path
        return self._build_proxy_url("img", full)

    # ==================== m3u8 获取 ====================

    def _fetch_m3u8(self, vid, h_label, h_host, quality):
        cache_key = vid + "_" + h_label + "_" + quality
        with self._m3u8_lock:
            if cache_key in self._m3u8_cache:
                return cache_key

        url = (API_DOMAIN + "/v3/media/" + quality + "/" + vid
               + ".m3u8?&token=" + self.token + "&h=" + h_host)
        try:
            resp = self.sess.get(url, timeout=20, allow_redirects=True)
            if resp.status_code != 200:
                print("[Fulao2] fetch_m3u8 " + h_label + "-" + quality + " status=" + str(resp.status_code))
                return None
            text = self._decrypt_m3u8(resp.text)
            if not text:
                return None
            with self._m3u8_lock:
                self._m3u8_cache[cache_key] = text
            print("[Fulao2] fetch_m3u8 " + h_label + "-" + quality + " OK")
            return cache_key
        except Exception as e:
            print("[Fulao2] fetch_m3u8 " + h_label + "-" + quality + " " + str(e))
            return None

    def _play_url(self, cache_key):
        return self._build_proxy_url("m3u8", cache_key)

    # ==================== 首页分类 ====================

    def homeContent(self, filter=False):
        data = self._api("GET", "v2/menu/type")
        classes = []
        if data and "response" in data:
            seen = set()
            for group in ["pixeled", "unpixeled"]:
                for item in data["response"].get(group, []):
                    t = item.get("title", "")
                    if t in TARGET_CATEGORIES and t not in seen:
                        seen.add(t)
                        classes.append({"type_id": str(item["id"]), "type_name": t})
        return {"class": classes, "filters": {}}

    def homeVideoContent(self):
        return {"list": []}

    # ==================== 分类列表 ====================

    def categoryContent(self, tid, pg=1, filter=False, extend=None):
        data = self._api("GET", "v1/menu/" + str(tid) + "/layout", xinfo=X_INFO_CENSOR)
        videos = []
        if data and "response" in data:
            for layout in data["response"]:
                items = layout.get("data", [])
                if isinstance(items, dict):
                    items = [items]
                if not isinstance(items, list):
                    continue
                for v in items:
                    vid = v.get("video_id")
                    title = v.get("video_title", "")
                    if not vid or not title:
                        continue
                    raw_pic = v.get("cover") or v.get("thumb", "")
                    actor = v.get("actor", "")
                    if isinstance(actor, list):
                        actor = "、".join(actor)
                    videos.append({
                        "vod_id": str(vid),
                        "vod_name": title,
                        "vod_pic": self._img_url(raw_pic),
                        "vod_remarks": actor,
                    })
        return {"list": videos, "page": pg, "pagecount": 99, "limit": len(videos) or 20}

    # ==================== 视频详情 ====================

    def detailContent(self, ids):
        vid = str(ids[0])

        # 1. 元数据
        info = self._api("GET", "v1/video/info/" + vid, xinfo=X_INFO_PLAY)
        raw_pic = ""
        title = ""
        number = ""
        desc = ""
        actor = ""
        tags = ""
        if info and "response" in info:
            r = info["response"]
            raw_pic = r.get("cover_url") or r.get("cover") or r.get("thumb", "")
            title = r.get("video_title", "")
            number = r.get("video_number", "")
            desc = r.get("video_description", "")
            a = r.get("actor", [])
            actor = "、".join(a) if isinstance(a, list) else str(a)
            tg = r.get("video_tags", [])
            tags = " ".join(tg) if isinstance(tg, list) else str(tg)

        # 2. 同步获取默认线路
        default_label = STREAM_HOSTS[0][0]
        default_host = STREAM_HOSTS[0][1]
        default_key = self._fetch_m3u8(vid, default_label, default_host, "480")
        if not default_key:
            default_key = self._fetch_m3u8(vid, default_label, default_host, "240")
        if not default_key:
            print("[Fulao2] detail 默认线路失败 vid=" + vid)
            return {"list": []}

        # 3. 后台并发预热
        def prefetch_all():
            import concurrent.futures
            tasks = []
            for hl, hh in STREAM_HOSTS:
                for q, _ in QUALITIES:
                    ck = vid + "_" + hl + "_" + q
                    with self._m3u8_lock:
                        if ck not in self._m3u8_cache:
                            tasks.append((vid, hl, hh, q))
            if not tasks:
                return
            with concurrent.futures.ThreadPoolExecutor(max_workers=4) as ex:
                futs = [ex.submit(self._fetch_m3u8, *args) for args in tasks]
                concurrent.futures.wait(futs)

        threading.Thread(target=prefetch_all, daemon=True).start()

        # 4. 构造播放列表
        from_parts = []
        url_groups = []
        for h_label, h_host in STREAM_HOSTS:
            parts = []
            for quality, q_label in QUALITIES:
                ck = vid + "_" + h_label + "_" + quality
                parts.append(q_label + "$" + self._play_url(ck))
            from_parts.append(h_label)
            url_groups.append("$$$".join(parts))

        return {"list": [{
            "vod_id": vid,
            "vod_name": title,
            "vod_pic": self._img_url(raw_pic),
            "vod_remarks": number,
            "vod_content": desc or tags,
            "vod_actor": actor,
            "vod_play_from": "$$$".join(from_parts),
            "vod_play_url": ":::".join(url_groups),
        }]}

    # ==================== 播放 ====================

    def playerContent(self, flag, id, vipFlags=None):
        return {
            "parse": 0,
            "url": id,
            "header": {
                "User-Agent": UA_CDN,
                "Cookie": "jwt=token",
            },
        }

    def searchContent(self, key, quick=False, pg=1):
        return {"list": []}

    # ==================== localProxy ====================

    def _parse_proxy_params(self, param):
        if isinstance(param, dict):
            return param
        if isinstance(param, str):
            try:
                d = json.loads(param)
                if isinstance(d, dict):
                    return d
            except Exception:
                pass
            result = {}
            qs = param.split('?', 1)[1] if '?' in param else param
            for pair in qs.split('&'):
                if '=' in pair:
                    from urllib.parse import unquote
                    k, v = pair.split('=', 1)
                    result[k] = unquote(v)
            return result
        return {}

    def localProxy(self, param):
        try:
            p = self._parse_proxy_params(param)
            ptype = p.get("type", "")
            key = p.get("key", "")

            if ptype == "m3u8":
                return self._serve_m3u8(key)
            elif ptype == "img":
                return self._serve_img(key)
            elif ptype == "ts":
                return self._serve_ts(key)
            return [404, "text/plain", b""]
        except Exception as e:
            print("[Fulao2] localProxy err: " + str(e))
            return [404, "text/plain", b""]

    def _serve_m3u8(self, key):
        """从缓存中取 m3u8，重写 TS 分片地址为代理 URL"""
        content = self._m3u8_cache.get(key)
        if not content:
            return [404, "text/plain", b"m3u8 not found"]
        # 重写 TS 分片为代理 URL
        lines = []
        for line in content.split('\n'):
            stripped = line.strip()
            if not stripped:
                continue
            if stripped.startswith('#'):
                if '#EXT-X-KEY:' in stripped and 'URI=' in stripped:
                    # 重写 KEY URI
                    import re
                    m = re.search(r'URI="([^"]+)"', stripped)
                    if m:
                        key_url = m.group(1)
                        proxy_key_url = self._build_proxy_url("ts", key_url)
                        stripped = stripped.replace(m.group(1), proxy_key_url)
                lines.append(stripped)
            elif not stripped.startswith('http'):
                lines.append(stripped)
            else:
                lines.append(self._build_proxy_url("ts", stripped))
        content = '\n'.join(lines) + '\n'
        return [200, "application/vnd.apple.mpegurl", content.encode('utf-8')]

    def _serve_img(self, url):
        """下载并解密图片"""
        try:
            r = requests.get(url, headers={
                "User-Agent": UA_IMG,
                "Accept-Encoding": "gzip",
                "Connection": "Keep-Alive",
            }, timeout=10, allow_redirects=True)
            raw = r.content
            body = self._decrypt_img(raw)
            return [200, "image/jpeg", body]
        except Exception as e:
            print("[Fulao2] _serve_img err: " + str(e))
            return [404, "text/plain", b""]

    def _serve_ts(self, url):
        """代理 TS 分片"""
        try:
            r = requests.get(url, headers={
                "User-Agent": UA_CDN,
            }, timeout=10, allow_redirects=True)
            return [200, "video/mp2t", r.content]
        except Exception as e:
            print("[Fulao2] _serve_ts err: " + str(e))
            return [404, "text/plain", b""]