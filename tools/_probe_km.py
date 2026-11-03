# -*- coding: utf-8 -*-
"""km 快猫：完整加密链实测（请求加密 + sig + 响应解密）"""
import binascii
import hashlib
import json
import urllib.error
import urllib.parse
import urllib.request

from Crypto.Cipher import AES
from Crypto.Util.Padding import pad, unpad

BASE = "https://icef4vn.xyz"
KEY = b"625202f9149maomi"   # 16 字节
IV = b"5efd3f6060emaomi"    # 16 字节
PASS = "maomi_pass_xyz"
OP = urllib.request.build_opener(urllib.request.ProxyHandler({}))
UA = "okhttp/3.14.9"


def aes_enc(plain_bytes):
    return AES.new(KEY, AES.MODE_CBC, IV).encrypt(pad(plain_bytes, 16))


def aes_dec(raw):
    p = AES.new(KEY, AES.MODE_CBC, IV).decrypt(raw)
    try:
        p = unpad(p, 16)
    except Exception:
        pass
    return p


def enc_payload(obj):
    data_hex = binascii.hexlify(aes_enc(json.dumps(obj, ensure_ascii=False,
                                                   separators=(",", ":")).encode())).decode()
    sig = hashlib.md5(("data=" + data_hex + PASS).encode()).hexdigest()
    return data_hex, sig


def post(path, obj):
    data_hex, sig = enc_payload(obj)
    body = urllib.parse.urlencode({"data": data_hex, "sig": sig}).encode()
    req = urllib.request.Request(
        BASE + path, data=body,
        headers={"User-Agent": UA, "Content-Type": "application/x-www-form-urlencoded"},
        method="POST")
    try:
        with OP.open(req, timeout=20) as r:
            return r.status, r.read()
    except urllib.error.HTTPError as e:
        return e.code, e.read()
    except Exception as e:
        return 0, ("%s: %s" % (type(e).__name__, e)).encode()


def dec_resp(raw):
    txt = raw.decode("utf-8", "replace").strip()
    if not txt:
        return {}
    # 可能是 hex 也可能是 base64
    for conv in ("hex", "b64"):
        try:
            if conv == "hex":
                b = binascii.unhexlify(txt)
            else:
                import base64
                b = base64.b64decode(txt + "=" * ((4 - len(txt) % 4) % 4))
            p = aes_dec(b)
            return json.loads(p.decode("utf-8", "replace").rstrip("\x00"))
        except Exception:
            continue
    return {"_raw": txt[:300]}


print("=" * 74)
for path in ["/api/videos/", "/api/videos/listAll", "/api/videos/listHot"]:
    for obj in ({"method": "listAll", "page": 1, "limit": 20},
                {"method": "listHot", "page": 1, "limit": 20},
                {"method": "list", "page": 1, "limit": 20},
                {"page": 1, "limit": 20, "methodName": "listAll"},
                {"page": 1, "limit": 20}):
        st, raw = post(path, obj)
        j = dec_resp(raw)
        ok = "code" in j and j.get("code") == 200
        print("%-22s %-42s -> %s %s" % (path, json.dumps(obj, ensure_ascii=False)[:42],
                                        st, json.dumps(j, ensure_ascii=False)[:150]))
        if ok:
            print("  ★★★ 命中")
            with open("tools/_dec/km_hit.json", "w", encoding="utf-8") as f:
                json.dump({"req": obj, "resp": j}, f, ensure_ascii=False, indent=1)
            raise SystemExit(0)
