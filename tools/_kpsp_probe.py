# -*- coding: utf-8 -*-
"""kpsp 看片视频 实测：业务解密 + 接口探测

算法还原自 CryptoUtil::ksSpDecrypt (0x8f2484) / _decode64ToHex (0x8df848)
  hex = urlsafe_b64decode(x-data).hex()
  iv  = hex[18:50]
  ct  = hex[50 : len-64]
  key = 7af630c7e06ccecfa70d5a085f189c06   (hex → 16 字节)
  plain = AES-128-CBC
"""
import base64
import binascii
import json
import os
import urllib.error
import urllib.request

try:
    from Crypto.Cipher import AES
    HAVE_PYC = True
except ImportError:
    HAVE_PYC = False

BASE = "https://sm-api.wieuc.com"
KEY_HEX = "7af630c7e06ccecfa70d5a085f189c06"
OP = urllib.request.build_opener(urllib.request.ProxyHandler({}))
UA = {"User-Agent": "okhttp/3.14.9", "Accept": "application/json"}
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "_dec")
os.makedirs(OUT, exist_ok=True)


def decode64_to_hex(s):
    s = s.replace("-", "+").replace("_", "/").strip()
    s += "=" * ((4 - len(s) % 4) % 4)
    b = base64.b64decode(s, validate=False)
    return binascii.hexlify(b).decode()


def ks_sp_decrypt(xdata):
    h = decode64_to_hex(xdata)
    iv = bytes.fromhex(h[18:50])
    ct = bytes.fromhex(h[50:len(h) - 64])
    key = bytes.fromhex(KEY_HEX)
    if HAVE_PYC:
        from Crypto.Cipher import AES as _A
        from Crypto.Util.Padding import unpad
        raw = _A.new(key, _A.MODE_CBC, iv).decrypt(ct)
        try:
            raw = unpad(raw, 16)
        except Exception:
            pass
    else:
        from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
        d = Cipher(algorithms.AES(key), modes.CBC(iv)).decryptor()
        raw = d.update(ct) + d.finalize()
        raw = raw.rstrip(b"\x00")
    return raw


def call(path, qp=None):
    url = BASE + "/" + path.lstrip("/")
    if qp:
        url += "?" + urllib.parse.urlencode(qp)
    req = urllib.request.Request(url, headers=UA)
    try:
        with OP.open(req, timeout=20) as r:
            return r.status, dict(r.headers), r.read()
    except urllib.error.HTTPError as e:
        return e.code, dict(e.headers), e.read()
    except Exception as e:
        return 0, {}, ("%s: %s" % (type(e).__name__, e)).encode()


import urllib.parse  # noqa: E402

print("pycryptodome =", HAVE_PYC)
print("=" * 74)

tests = [
    ("api/vod/video?page=1&per_page=20&site_id=1", None),
    ("api/vod/video", {"page": 1, "per_page": 20, "site_id": 1}),
    ("api/vod/video", {"page": 1, "per_page": 20}),
    ("api/vod/video", {"page": 1, "per_page": 20, "site_id": 1, "product_type": 1}),
]

for path, qp in tests:
    st, hd, body = call(path, qp)
    keys = {k.lower(): v for k, v in hd.items()}
    print("\n[%s %s] -> %s  %d bytes" % (path, qp or "", st, len(body)))
    print("  headers: ctype=%s  x-data=%s" % (
        keys.get("content-type", "-"),
        ("有(len=%d)" % len(keys["x-data"])) if "x-data" in keys else "无"))
    hx = keys.get("x-data")
    if not hx:
        print("  body head:", body[:200])
        continue
    try:
        plain = ks_sp_decrypt(hx)
        print("  ★ 解密成功 %d 字节" % len(plain))
        print("  明文头:", plain[:200])
        try:
            j = json.loads(plain.decode("utf-8"))
            fn = "kpsp_list_%s.json" % abs(hash(path + str(qp))) % 100000
            with open(os.path.join(OUT, fn), "w", encoding="utf-8") as f:
                json.dump(j, f, ensure_ascii=False, indent=1)
            print("  已存:", fn)
            if isinstance(j, dict):
                print("  顶层键:", list(j.keys())[:10])
                d = j.get("data") or j
                if isinstance(d, dict):
                    print("  data 键:", list(d.keys())[:10])
                    for kk in ("list", "data", "items", "videos", "rows"):
                        if isinstance(d.get(kk), list) and d[kk]:
                            print("  样本[%s][0]:" % kk,
                                  json.dumps(d[kk][0], ensure_ascii=False)[:600])
                            break
        except Exception as e:
            print("  非 JSON:", e)
    except Exception as e:
        print("  ✗ 解密失败:", type(e).__name__, e)
        print("  hex len =", len(decode64_to_hex(hx)))
