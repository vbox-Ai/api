# -*- coding: utf-8 -*-
"""mdtv 麻豆TV：用已破的 aijav 同款算法解响应"""
import base64
import binascii
import json
import urllib.error
import urllib.request

from Crypto.Cipher import AES
from Crypto.Util.Padding import unpad

OP = urllib.request.build_opener(urllib.request.ProxyHandler({}))
UA = ("Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) "
      "AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Mobile/15E148 Safari/604.1")
BASE = "https://spi.d5c4a712.com"

RESP_KEY = b"0XxdjmI55ZjjqQLO3nI7gGqrBP0Vz9jS"   # AES-256（aijav 已验）
IV_HEAD = b"RWf23muavY"                          # + suffix(6) = 16


def get(path):
    try:
        with OP.open(urllib.request.Request(BASE + path, headers={
                "User-Agent": UA, "Accept": "application/json"}), timeout=15) as r:
            return r.status, r.read()
    except urllib.error.HTTPError as e:
        return e.code, e.read()
    except Exception as e:
        return 0, str(e).encode()


def dec(body):
    j = json.loads(body.decode("utf-8", "replace"))
    if "data" not in j:
        return j, "无 data 字段"
    d = j["data"]
    suf = str(j.get("suffix") or "")
    raw = base64.b64decode(d + "=" * (-len(d) % 4))
    iv = (IV_HEAD + suf.encode())[:16]
    if len(raw) % 16:
        return None, "密文 %d 字节非 16 倍数" % len(raw)
    p = AES.new(RESP_KEY, AES.MODE_CBC, iv).decrypt(raw)
    try:
        p = unpad(p, 16)
    except Exception:
        pass
    return p.decode("utf-8", "replace"), None


for path in ("/video/list", "/video/channel", "/video/tags"):
    st, b = get(path)
    txt, err = dec(b)
    print("=" * 74)
    print("[%s] -> %s %d bytes" % (path, st, len(b)))
    if err:
        print("   ", err)
        print("   原始:", b[:150])
        continue
    s = txt.lstrip()
    print("   解密成功 %d 字符" % len(txt))
    print("   ", txt[:500].replace("\n", " "))
    if s[:1] in ("{", "["):
        try:
            j = json.loads(s)
            print("   JSON keys:", list(j.keys())[:10] if isinstance(j, dict) else "list")
            if isinstance(j, dict):
                for k, v in j.items():
                    if isinstance(v, list) and v and isinstance(v[0], dict):
                        print("   %s[0]: %s" % (k, json.dumps(v[0], ensure_ascii=False)[:300]))
                        break
        except Exception as e:
            print("   非 JSON:", e)
