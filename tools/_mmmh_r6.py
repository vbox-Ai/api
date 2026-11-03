# -*- coding: utf-8 -*-
"""mmmh 第六轮：解密响应 + 拿分类 + 调列表接口"""
import base64
import binascii
import json
import urllib.error
import urllib.parse
import urllib.request

from Crypto.Cipher import AES
from Crypto.Util.Padding import unpad

OP = urllib.request.build_opener(urllib.request.ProxyHandler({}))
UA = "okhttp/3.14.9"
BASE = "https://sdhvb.meme06.live"
TOKEN = ("eyJ1c2VyX2lkIjozMDQ1OTg4NjEsImxhc3Rsb2dpbiI6MTc2Mjg3MTA1MH0"
         ".a568a4b03a8d6c08c14494d85c40a9f1"
         ".7c6579106b5199d2177be390fc8c608b73bfc0cf63a2d853da78afab")
K = base64.b64decode("h7lkUI0kb25Usb3qTFLefTf8b+8Hs2Y63sANNraUm/Q=")
IV = base64.b64decode("k54Vcjbp6ByR6D83eIoxgw==")


def fetch(url, hdrs=None, data=None, method=None):
    h = {"User-Agent": UA, "Accept": "application/json, */*",
         "Authorization": "Bearer " + TOKEN}
    if hdrs:
        h.update(hdrs)
    req = urllib.request.Request(url, data=data, headers=h,
                                 method=method or ("POST" if data else "GET"))
    try:
        with OP.open(req, timeout=20) as r:
            return r.status, dict(r.headers), r.read()
    except urllib.error.HTTPError as e:
        return e.code, dict(e.headers) if e.headers else {}, e.read()
    except Exception as e:
        return 0, {}, str(e).encode()


def dec(body, hdr=None):
    """响应解密：base64 → AES-256-CBC"""
    txt = body.decode("utf-8", "replace").strip()
    try:
        raw = base64.b64decode(txt + "=" * ((4 - len(txt) % 4) % 4))
    except Exception:
        return None, "非 base64"
    if len(raw) % 16:
        return None, "长度非 16 倍数: %d" % len(raw)
    p = AES.new(K, AES.MODE_CBC, IV).decrypt(raw)
    try:
        p = unpad(p, 16)
    except Exception:
        pass
    return p, None


st, hd, b = fetch(BASE + "/v1/animat/category")
print("[category] -> %s  %d bytes" % (st, len(b)))
print("  X-Response-Length:", hd.get("X-Response-Length"))
p, err = dec(b)
if p is None:
    print("  解密失败:", err)
    raise SystemExit(1)
print("  解密 %d 字节" % len(p))
print("  hex head:", binascii.hexlify(p[:16]).decode())

s = p.decode("utf-8", "replace")
i = s.find("{")
if i < 0:
    i = s.find("[")
try:
    obj, end = json.JSONDecoder().raw_decode(s[i:])
    print("  JSON 解析成功，结束于 %d / %d" % (i + end, len(s)))
except Exception as e:
    print("  JSON 失败:", e)
    print("  前 300:", s[:300])
    raise SystemExit(1)

with open("tools/_dec/mmmh_animat_category.json", "w", encoding="utf-8") as f:
    json.dump(obj, f, ensure_ascii=False, indent=1)
print(json.dumps(obj, ensure_ascii=False, indent=1)[:1500])
print("\n已存 tools/_dec/mmmh_animat_category.json")

# 提取 category_id
ids = []


def walk(o):
    if isinstance(o, dict):
        cid = o.get("id") or o.get("category_id")
        if cid is not None and (o.get("name") or o.get("title")):
            ids.append((cid, o.get("name") or o.get("title")))
        for v in o.values():
            walk(v)
    elif isinstance(o, list):
        for v in o:
            walk(v)


walk(obj)
print("\n候选 category: %s" % ids[:12])
