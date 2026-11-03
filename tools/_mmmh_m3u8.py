# -*- coding: utf-8 -*-
"""mmmh 验证：按 mmMhAnim 模板拼 m3u8（带 host/chain/encrypt/token）"""
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
TOKEN = ("eyJ1c2VyX2lkIjozMDQ1OTg4NjEsImxhc3Rsb2dpbiI6MTc2Mjg3MTA1MH0"
         ".a568a4b03a8d6c08c14494d85c40a9f1"
         ".7c6579106b5199d2177be390fc8c608b73bfc0cf63a2d853da78afab")
KEY = b"ae52f7ffd2dd66ba5743bb180188b991"
# 配置里的 stream chain
STREAM_CHAIN = "miOBGgHNWhpt2"
COMIC_CHAIN = "miXFCHEoSXJ.M"


def api(path, qp=None):
    url = BASE + path + (("?" + urllib.parse.urlencode(qp)) if qp else "")
    h = {"User-Agent": UA, "Accept": "application/json, */*",
         "Authorization": "Bearer " + TOKEN}
    try:
        with OP.open(urllib.request.Request(url, headers=h), timeout=20) as r:
            st, hd, body = r.status, dict(r.headers), r.read()
    except urllib.error.HTTPError as e:
        st, hd, body = e.code, dict(e.headers) if e.headers else {}, e.read()
    except Exception:
        return {}
    keys = {k.lower(): v for k, v in hd.items()}
    xlen = keys.get("x-response-length")
    if not xlen:
        return {}
    txt = body.decode("utf-8", "replace").strip()
    try:
        raw = base64.b64decode(txt + "=" * ((4 - len(txt) % 4) % 4))
        iv = hashlib.md5(str(xlen).encode()).hexdigest()[8:24].encode()
        p = AES.new(KEY, AES.MODE_CBC, iv).decrypt(raw)
        try:
            p = unpad(p, 16)
        except Exception:
            pass
        s = p.decode("utf-8", "replace")
        i = min([x for x in (s.find("{"), s.find("[")) if x >= 0] or [0])
        return json.JSONDecoder().raw_decode(s[i:])[0]
    except Exception:
        return {}


def get(url, hdrs=None):
    h = {"User-Agent": UA}
    if hdrs:
        h.update(hdrs)
    try:
        with OP.open(urllib.request.Request(url, headers=h), timeout=20) as r:
            return r.status, dict(r.headers), r.read(300)
    except urllib.error.HTTPError as e:
        return e.code, dict(e.headers) if e.headers else {}, e.read(150)
    except Exception as e:
        return 0, {}, str(e).encode()


j = api("/v1/animat/category/list", {"category_id": 7, "type": 1, "page": 1})
items = ((j.get("success") or {}).get("data") or [])[:3]
print("列表 %d 项" % len(items))

for it in items:
    ak = it.get("avkey")
    if not ak:
        continue
    # 按 asm 模板拼
    url = ("%s/v1/animat/pwa/media/720/%s.m3u8?host=%s&chain=%s&encrypt=true&token=%s"
           % (BASE, ak, TOKEN, STREAM_CHAIN, TOKEN))
    st, hd, b = get(url)
    ct = hd.get("Content-Type") or ""
    ok = b[:7] == b"#EXTM3U"
    print("\n%-14s -> %s %s" % (ak, st, ct))
    print("   head:", b[:120].decode("utf-8", "replace").replace("\n", " | "))
    if ok:
        print("   ★★★ m3u8 命中！")
    # 对比：直接旧路径
    st2, _, b2 = get("%s/v1/animat/media/720/%s.m3u8" % (BASE, ak),
                     {"Authorization": "Bearer " + TOKEN})
    print("   旧路径 -> %s %s" % (st2, b2[:60].decode("utf-8", "replace").replace("\n", " ")))
