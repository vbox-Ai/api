# -*- coding: utf-8 -*-
"""mmmh 第七轮：按 asm 还原的算法解响应（IV = MD5(X-Response-Length) 的某种切片）"""
import base64
import binascii
import hashlib
import json
import urllib.error
import urllib.request

from Crypto.Cipher import AES
from Crypto.Util.Padding import unpad

OP = urllib.request.build_opener(urllib.request.ProxyHandler({}))
UA = "okhttp/3.14.9"
BASE = "https://sdhvb.meme06.live"
TOKEN = ("eyJ1c2VyX2lkIjozMDQ1OTg4NjEsImxhc3Rsb2dpbiI6MTc2Mjg3MTA1MH0"
         ".a568a4b03a8d6c08c14494d85c40a9f1"
         ".7c6579106b5199d2177be390fc8c608b73bfc0cf63a2d853da78afab")
KEY = b"ae52f7ffd2dd66ba5743bb180188b991"      # 32 字节 -> AES-256


def fetch(url):
    h = {"User-Agent": UA, "Accept": "application/json, */*",
         "Authorization": "Bearer " + TOKEN}
    try:
        with OP.open(urllib.request.Request(url, headers=h), timeout=20) as r:
            return r.status, dict(r.headers), r.read()
    except urllib.error.HTTPError as e:
        return e.code, dict(e.headers) if e.headers else {}, e.read()
    except Exception as e:
        return 0, {}, str(e).encode()


st, hd, body = fetch(BASE + "/v1/animat/category")
keys = {k.lower(): v for k, v in hd.items()}
xlen = keys.get("x-response-length")
print("status=%s  body=%d  X-Response-Length=%r" % (st, len(body), xlen))

txt = body.decode("utf-8", "replace").strip()
raw = base64.b64decode(txt + "=" * ((4 - len(txt) % 4) % 4))
print("密文 %d 字节  (%%16=%d)" % (len(raw), len(raw) % 16))

md5hex = hashlib.md5(str(xlen).encode()).hexdigest()
print("MD5(X-Response-Length) =", md5hex, "len=%d" % len(md5hex))

# IV 候选：各种切片 / 派生
cands = {
    "md5hex[8:24]": md5hex[8:24],
    "md5hex[0:16]": md5hex[0:16],
    "md5hex[16:32]": md5hex[16:32],
    "md5hex[8:48]pad": (md5hex[8:48] + "0" * 48)[:16],
    "md5raw[:16]": hashlib.md5(str(xlen).encode()).digest()[:16],
    "xlen前16": str(xlen)[:16],
    "xlen.md5双写": hashlib.md5((str(xlen) + md5hex).encode()).hexdigest()[:16],
    "md5hex+md5hex[8:24]": (md5hex + md5hex)[8:24],
}
print("\n试 IV 候选：")
hit = None
for name, ivs in cands.items():
    ivb = ivs.encode() if isinstance(ivs, str) else ivs
    if len(ivb) != 16:
        print("  %-22s 长度 %d 跳过" % (name, len(ivb)))
        continue
    try:
        p = AES.new(KEY, AES.MODE_CBC, ivb).decrypt(raw)
        try:
            p = unpad(p, 16)
        except Exception:
            pass
        s = p.decode("utf-8", "replace")
        ok = s.lstrip()[:1] in ("{", "[")
        print("  %-22s iv=%-16s -> %s %s" %
              (name, ivs, "★JSON" if ok else "乱码", s[:70].replace("\n", " ")))
        if ok and hit is None:
            hit = (name, ivs, s)
    except Exception as e:
        print("  %-22s ERR %s" % (name, e))

if hit:
    name, ivs, s = hit
    print("\n★★★ 命中 IV = %s (%s)" % (ivs, name))
    i = s.find("{")
    if i < 0:
        i = s.find("[")
    obj, end = json.JSONDecoder().raw_decode(s[i:])
    with open("tools/_dec/mmmh_category_plain.json", "w", encoding="utf-8") as f:
        json.dump(obj, f, ensure_ascii=False, indent=1)
    print(json.dumps(obj, ensure_ascii=False, indent=1)[:1400])
