# -*- coding: utf-8 -*-
"""mmmh 迷妹漫画：解 host_pwa.txt 配置（拿真实 API host）"""
import base64
import binascii
import json
import urllib.error
import urllib.request

from Crypto.Cipher import AES
from Crypto.Util.Padding import unpad

OP = urllib.request.build_opener(urllib.request.ProxyHandler({}))
UA = "okhttp/3.14.9"
URL = "https://public.mino02.live/host_pwa.txt"

# 从 asm 抽到的候选密钥/常量
KEY_HEX = "ae52f7ffd2dd66ba5743bb180188b991"      # 32 hex -> 16 字节
KEY_ASCII = b"ae52f7ffd2dd66ba5743bb180188b991"    # 32 字节 -> AES-256
CAND_IV = [("zero", b"\x00" * 16),
           ("key16", bytes.fromhex(KEY_HEX)),
           ("ascii16", KEY_ASCII[:16])]


def fetch():
    req = urllib.request.Request(URL, headers={"User-Agent": UA})
    try:
        with OP.open(req, timeout=25) as r:
            return r.status, dict(r.headers), r.read()
    except urllib.error.HTTPError as e:
        return e.code, dict(e.headers) if e.headers else {}, e.read()
    except Exception as e:
        return 0, {}, str(e).encode()


st, hd, raw = fetch()
print("host_pwa.txt -> %s  %d bytes" % (st, len(raw)))
keys = {k.lower(): v for k, v in hd.items()}
print("  x-response-length =", keys.get("x-response-length"))
print("  ctype =", keys.get("content-type"))
txt = raw.decode("utf-8", "replace").strip()
print("  内容头:", txt[:120])
print("  长度:", len(txt))

# 尝试 base64 解码
b = None
for name, fn in (("b64", lambda s: base64.b64decode(s + "=" * ((4 - len(s) % 4) % 4))),
                 ("b64url", lambda s: base64.urlsafe_b64decode(
                     s.replace("-", "+").replace("_", "/") + "=" * ((4 - len(s) % 4) % 4))),
                 ("hex", binascii.unhexlify)):
    try:
        b = fn(txt)
        print("  %s 解码 -> %d 字节  head=%s" % (name, len(b), binascii.hexlify(b[:12]).decode()))
        break
    except Exception:
        continue

if b:
    print("\n=== 试 AES 解密 ===")
    done = False
    for kname, key in (("hex16", bytes.fromhex(KEY_HEX)), ("ascii32", KEY_ASCII),
                       ("ascii16", KEY_ASCII[:16])):
        for ivn, iv in CAND_IV:
            if len(b) % 16:
                continue
            try:
                p = AES.new(key, AES.MODE_CBC, iv).decrypt(b)
                try:
                    p = unpad(p, 16)
                except Exception:
                    pass
                printable = sum(1 for c in p[:64] if 9 <= c < 127) / max(1, len(p[:64]))
                if printable > 0.85:
                    print("  ★ key=%s iv=%s -> %s" % (kname, ivn, p[:300]))
                    done = True
                    break
            except Exception:
                continue
        if done:
            break
    if not done:
        # 尝试 gzip / zlib / 明文
        import gzip
        import zlib
        for name, fn in (("gzip", lambda x: gzip.decompress(x)),
                         ("zlib", lambda x: zlib.decompress(x)),
                         ("raw", lambda x: x)):
            try:
                d = fn(b)
                print("  作为 %s -> %s" % (name, d[:200]))
            except Exception:
                pass
        print("  未命中已知 AES 组合")
else:
    print("  无法解码")
