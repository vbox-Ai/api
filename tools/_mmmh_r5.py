# -*- coding: utf-8 -*-
"""mmmh 第五轮：用真实 token_mmmh 打通接口"""
import json
import urllib.error
import urllib.request

OP = urllib.request.build_opener(urllib.request.ProxyHandler({}))
UA = "okhttp/3.14.9"
BASE = "https://sdhvb.meme06.live"
TOKEN = ("eyJ1c2VyX2lkIjozMDQ1OTg4NjEsImxhc3Rsb2dpbiI6MTc2Mjg3MTA1MH0"
         ".a568a4b03a8d6c08c14494d85c40a9f1"
         ".7c6579106b5199d2177be390fc8c608b73bfc0cf63a2d853da78afab")


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


VARIANTS = [
    ("Bearer 头", {"Authorization": "Bearer " + TOKEN}),
    ("token 头", {"token": TOKEN}),
    ("裸 Authorization", {"Authorization": TOKEN}),
]

PATHS = ["/v1/animat/category", "/v1/animat/category/list", "/v1/fiction/category"]

best = None
for name, hdrs in VARIANTS:
    print("\n=== %s ===" % name)
    for p in PATHS:
        st, hd, b = fetch(BASE + p, hdrs)
        keys = {k.lower(): v for k, v in hd.items()}
        txt = b[:150].decode("utf-8", "replace").replace("\n", " ")
        print("  [%-26s] -> %s %5d  x-resp-len=%-6s %s" %
              (p, st, len(b), keys.get("x-response-length"), txt[:110]))
        if st == 200 and b[:1] in (b"{", b"["):
            best = (p, hdrs, b)
            break
    if best:
        break

if best:
    p, hdrs, b = best
    print("\n★ 命中 %s" % p)
    try:
        j = json.loads(b.decode("utf-8", "replace"))
        print(json.dumps(j, ensure_ascii=False, indent=1)[:1200])
        with open("tools/_dec/mmmh_category.json", "w", encoding="utf-8") as f:
            json.dump(j, f, ensure_ascii=False, indent=1)
        print("\n已存 tools/_dec/mmmh_category.json")
    except Exception as e:
        print("非 JSON:", e, b[:300])
else:
    print("\n未命中，试带 MmMhChain / X-Response-Length 组合")
    for hdrs in ({"Authorization": "Bearer " + TOKEN, "MmMhChain": "miXFCHEoSXJ.M"},
                 {"Authorization": "Bearer " + TOKEN, "X-Response-Length": "0"},
                 {"Authorization": "Bearer " + TOKEN, "Content-Type": "application/json"}):
        st, hd, b = fetch(BASE + "/v1/animat/category", hdrs)
        print("  %-52s -> %s %s" % (json.dumps(hdrs, ensure_ascii=False)[:52], st,
                                    b[:110].decode("utf-8", "replace").replace("\n", " ")))
