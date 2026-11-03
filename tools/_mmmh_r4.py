# -*- coding: utf-8 -*-
"""mmmh 第四轮：实测 API 接口（找 token 与响应格式）"""
import json
import urllib.error
import urllib.request

OP = urllib.request.build_opener(urllib.request.ProxyHandler({}))
UA = "okhttp/3.14.9"
BASE = "https://sdhvb.meme06.live"

TOKENS = ["", "ae52f7ffd2dd66ba5743bb180188b991", "b2dc730bf54441f18492061ce80659b3"]


def fetch(url, hdrs=None):
    h = {"User-Agent": UA, "Accept": "application/json, */*"}
    if hdrs:
        h.update(hdrs)
    try:
        with OP.open(urllib.request.Request(url, headers=h), timeout=20) as r:
            return r.status, dict(r.headers), r.read()
    except urllib.error.HTTPError as e:
        return e.code, dict(e.headers) if e.headers else {}, e.read()
    except Exception as e:
        return 0, {}, str(e).encode()


PATHS = [
    "/v1/animat/category",
    "/v1/animat/category/list",
    "/v1/fiction/category",
]

print("=== 无鉴权尝试 ===")
for p in PATHS:
    st, hd, b = fetch(BASE + p)
    keys = {k.lower(): v for k, v in hd.items()}
    print("\n[%s] -> %s %d bytes  ctype=%s  x-resp-len=%s" %
          (p, st, len(b), keys.get("content-type"), keys.get("x-response-length")))
    print("   head:", b[:220].decode("utf-8", "replace").replace("\n", " "))

print("\n\n=== 带 Bearer token 尝试 ===")
for tok in TOKENS[:2]:
    if not tok:
        continue
    for p in PATHS[:1]:
        hdrs = {"Authorization": "Bearer " + tok}
        st, hd, b = fetch(BASE + p, hdrs)
        keys = {k.lower(): v for k, v in hd.items()}
        print("[%s tok=%s] -> %s %d  x-resp-len=%s" %
              (p, tok[:8], st, len(b), keys.get("x-response-length")))
        print("   head:", b[:180].decode("utf-8", "replace").replace("\n", " "))
