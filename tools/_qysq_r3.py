# -*- coding: utf-8 -*-
"""qysq 响应解密：先试 secret 作 AES key 的各种组合"""
import base64
import binascii
import hashlib
import hmac
import json
import time
import urllib.error
import urllib.request
import uuid

from Crypto.Cipher import AES
from Crypto.Util.Padding import unpad

OP = urllib.request.build_opener(urllib.request.ProxyHandler({}))
DEV_UA = "DevType=Apple iPhone mobile;SysType=light;Ver=2.1.2;BuildID=Mobile Safari 18.5"
BROWSER_UA = ("Mozilla/5.0 (iPhone; CPU iPhone OS 18_5 like Mac OS X) "
              "AppleWebKit/605.1.15 (KHTML, like Gecko) Version/18.5 Mobile/15E148 Safari/604.1")
SECRET = b"gH3nA7fR9tV1jY6z"
TOKEN = ("eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJhdWQiOiJwdWJsaWMiLCJleHAiOjE3OTM4NTgxNjIs"
         "Imlzc3VlciI6ImNvbS5idXR0ZXJmbHkiLCJzdWIiOiJhc2lnbiIsInVzZXJJZCI6NTY3NzU4MX0"
         ".yjzuUUUK1hlQBzlTQ703ZYemCvfL97EYsQNUCyEVET4")
BASE = "https://d1kmvkv4iwtiup.cloudfront.net"


def call(path, body=None, method=None):
    ts = str(int(time.time()))
    nonce = str(uuid.uuid4())
    msg = "%s&%s&%s&%s&%s" % (TOKEN, path, DEV_UA, ts, nonce)
    sign = hmac.new(SECRET, msg.encode(), hashlib.sha1).hexdigest()
    h = {"X-User-Agent": DEV_UA, "user-agent": BROWSER_UA,
         "authorization": "Bearer " + TOKEN,
         "x-api-key": "timestamp=%s;sign=%s;nonce=%s" % (ts, sign, nonce),
         "Accept": "application/json", "Content-Type": "application/json"}
    data = json.dumps(body, ensure_ascii=False).encode() if body is not None else None
    req = urllib.request.Request(BASE + path, data=data, headers=h,
                                 method=method or ("POST" if data else "GET"))
    try:
        with OP.open(req, timeout=15) as r:
            return r.status, r.read()
    except urllib.error.HTTPError as e:
        return e.code, e.read()
    except Exception as e:
        return 0, str(e).encode()


st, b = call("/api/app/media/short/hot", {})
j = json.loads(b.decode("utf-8", "replace"))
print("code:", j.get("code"), " keys:", list(j.keys()))
d = j.get("data") or ""
print("密文长度:", len(d))
raw = base64.b64decode(d + "=" * (-len(d) % 4))
print("解码 %d 字节  16%%=%d  head=%s" % (len(raw), len(raw) % 16,
                                          binascii.hexlify(raw[:12]).decode()))

# key 候选
md5s = hashlib.md5(SECRET).digest()
smd5 = hashlib.md5(SECRET).hexdigest()
sha1s = hashlib.sha1(SECRET).digest()
md5tok = hashlib.md5(TOKEN.encode()).digest()
KEYS = {
    "secret16": SECRET,
    "md5(secret)raw": md5s,
    "md5(secret)hex16": smd5[:16].encode(),
    "md5(token)raw": md5tok,
    "secret+md5hex16": (SECRET + smd5[:16].encode())[:16],
    "sha1(secret)[:16]": sha1s[:16],
    "secret*2_32": (SECRET + SECRET)[:32],
}
IVS = {
    "zero": b"\x00" * 16,
    "secret16": SECRET,
    "md5(secret)raw": md5s,
    "md5(secret)hex16": smd5[:16].encode(),
    "secretrev": SECRET[::-1],
}

if len(raw) % 16 == 0:
    hit = None
    for kn, kb in KEYS.items():
        for ivn, ivb in IVS.items():
            if len(kb) not in (16, 24, 32):
                continue
            try:
                p = AES.new(kb, AES.MODE_CBC, ivb).decrypt(raw)
                try:
                    p2 = unpad(p, 16)
                except Exception:
                    p2 = p
                t = p2.decode("utf-8", "replace")
                if t.lstrip()[:1] in ("{", "["):
                    print("\n★★★ 命中 key=%s iv=%s" % (kn, ivn))
                    print(t[:500])
                    hit = (kn, ivn, t)
                    break
            except Exception:
                pass
        if hit:
            break
    if not hit:
        print("\n未命中；再试 ECB 与前缀剥离")
        for kn, kb in KEYS.items():
            if len(kb) not in (16, 24, 32):
                continue
            try:
                p = AES.new(kb, AES.MODE_ECB).decrypt(raw)
                t = p.decode("utf-8", "replace")
                if t.lstrip()[:1] in ("{", "["):
                    print("  ECB 命中 key=%s -> %s" % (kn, t[:160]))
                    break
            except Exception:
                pass
else:
    print("长度非 16 倍数，可能需要先剥前缀")
