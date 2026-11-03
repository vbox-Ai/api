# -*- coding: utf-8 -*-
"""mmmh 第二轮：用 main 里的 base64 常量作 AES-256 key/IV 解 host_pwa.txt"""
import base64
import binascii
import json
import urllib.error
import urllib.request

from Crypto.Cipher import AES
from Crypto.Util.Padding import unpad

OP = urllib.request.build_opener(urllib.request.ProxyHandler({}))
UA = "okhttp/3.14.9"

K_B64 = "h7lkUI0kb25Usb3qTFLefTf8b+8Hs2Y63sANNraUm/Q="
IV_B64 = "k54Vcjbp6ByR6D83eIoxgw=="

key = base64.b64decode(K_B64)
iv = base64.b64decode(IV_B64)
print("key = %d 字节  %s" % (len(key), key.hex()))
print("iv  = %d 字节  %s" % (len(iv), iv.hex()))


def fetch(url):
    try:
        with OP.open(urllib.request.Request(url, headers={"User-Agent": UA}), timeout=25) as r:
            return r.status, r.read()
    except urllib.error.HTTPError as e:
        return e.code, e.read()
    except Exception as e:
        return 0, str(e).encode()


st, raw = fetch("https://public.mino02.live/host_pwa.txt")
txt = raw.decode("utf-8", "replace").strip()
data = base64.b64decode(txt + "=" * ((4 - len(txt) % 4) % 4))
print("\nhost_pwa.txt -> %s  密文 %d 字节" % (st, len(data)))

p = AES.new(key, AES.MODE_CBC, iv).decrypt(data)
try:
    p = unpad(p, 16)
except Exception:
    pass
print("解密 %d 字节" % len(p))
print("hex head:", binascii.hexlify(p[:24]).decode())
try:
    s = p.decode("utf-8")
    print("★ UTF-8 明文:")
    print(s[:1200])
    with open("tools/_dec/mmmh_host_pwa.json", "w", encoding="utf-8") as f:
        f.write(s)
    print("\n已存 tools/_dec/mmmh_host_pwa.json")
except Exception as e:
    print("非 UTF-8:", e)
    print("原始:", p[:200])
