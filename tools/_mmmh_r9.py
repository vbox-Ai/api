# -*- coding: utf-8 -*-
"""mmmh 第九轮：确认 comic/fiction 接口 + 验证 m3u8/封面可播可取"""
import base64
import hashlib
import json
import urllib.error
import urllib.parse
import urllib.request

from Crypto.Cipher import AES
from Crypto.Util.Padding import unpad

OP = urllib.request.build_opener(urllib.request.ProxyHandler({}))
UA = "okhttp/3.14.9"
BASE = "https://sdhvb.meme06.live"
IMG_HOST = "https://image.meme06.live"
TOKEN = ("eyJ1c2VyX2lkIjozMDQ1OTg4NjEsImxhc3Rsb2dpbiI6MTc2Mjg3MTA1MH0"
         ".a568a4b03a8d6c08c14494d85c40a9f1"
         ".7c6579106b5199d2177be390fc8c608b73bfc0cf63a2d853da78afab")
KEY = b"ae52f7ffd2dd66ba5743bb180188b991"


def call(path, qp=None, raw_req=False):
    url = BASE + path
    if qp:
        url += "?" + urllib.parse.urlencode(qp)
    h = {"User-Agent": UA, "Accept": "application/json, */*",
         "Authorization": "Bearer " + TOKEN}
    try:
        with OP.open(urllib.request.Request(url, headers=h), timeout=20) as r:
            st, hd, body = r.status, dict(r.headers), r.read()
    except urllib.error.HTTPError as e:
        st, hd, body = e.code, dict(e.headers) if e.headers else {}, e.read()
    except Exception as e:
        return 0, {}, str(e).encode(), None
    keys = {k.lower(): v for k, v in hd.items()}
    xlen = keys.get("x-response-length")
    if not xlen:
        return st, keys, body, None
    txt = body.decode("utf-8", "replace").strip()
    if not txt or txt[0] in "{[":
        try:
            return st, keys, body, json.loads(txt)
        except Exception:
            return st, keys, body, None
    try:
        rawb = base64.b64decode(txt + "=" * ((4 - len(txt) % 4) % 4))
        iv = hashlib.md5(str(xlen).encode()).hexdigest()[8:24].encode()
        p = AES.new(KEY, AES.MODE_CBC, iv).decrypt(rawb)
        try:
            p = unpad(p, 16)
        except Exception:
            pass
        s = p.decode("utf-8", "replace")
        i = min([x for x in (s.find("{"), s.find("[")) if x >= 0] or [0])
        obj, _ = json.JSONDecoder().raw_decode(s[i:])
        return st, keys, body, obj
    except Exception as e:
        return st, keys, body, {"_err": str(e)}


print("=== 探 comic / fiction 接口 ===")
for p, qp in [
    ("/v1/fiction/category", None),
    ("/v1/fiction/category/list", {"category_id": 1, "page": 1}),
    ("/v1/comic/category", None),
    ("/v1/comic/category/list", {"category_id": 1, "type": 1, "page": 1}),
    ("/v1/combine/animat/internal/", {"id": 44191}),
    ("/v1/combine/animat/internal/LDM184-003", None),
]:
    st, keys, body, obj = call(p, qp)
    s = json.dumps(obj, ensure_ascii=False)[:150] if obj else body[:110].decode("utf-8", "replace")
    print("  %-40s -> %-4s %s" % (p + (("?" + urllib.parse.urlencode(qp)) if qp else ""), st, s))

print("\n=== 验证 m3u8 与封面 ===")
st, keys, body, obj = call("/v1/animat/category/list",
                           {"category_id": 7, "type": 1, "page": 1})
item = ((obj or {}).get("success") or {}).get("data") or []
if item:
    it = item[0]
    avkey = it.get("avkey")
    media = it.get("media") or {}
    m3u8 = media.get("720") or media.get("intro")
    print("  avkey =", avkey)
    print("  media =", json.dumps(media, ensure_ascii=False))
    for name, url in (("m3u8", BASE + m3u8 if m3u8 else ""),
                      ("封面", IMG_HOST + (it.get("cover") or ""))):
        if not url:
            continue
        try:
            with OP.open(urllib.request.Request(url, headers={"User-Agent": UA}), timeout=20) as r:
                b = r.read(300)
                print("  %-4s %s -> %s %s %s" % (name, url[:70], r.status,
                                                 r.headers.get("Content-Type"), b[:80]))
        except urllib.error.HTTPError as e:
            print("  %-4s %s -> HTTP %s" % (name, url[:70], e.code))
        except Exception as e:
            print("  %-4s %s -> %s" % (name, url[:70], type(e).__name__))
