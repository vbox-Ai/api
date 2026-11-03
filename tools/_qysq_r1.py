# -*- coding: utf-8 -*-
"""qysq 妻友社区：接口探测"""
import json
import urllib.error
import urllib.parse
import urllib.request

OP = urllib.request.build_opener(urllib.request.ProxyHandler({}))
UA = ("Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) "
      "AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Mobile/15E148 Safari/604.1")
BASE = "https://d1kmvkv4iwtiup.cloudfront.net"
TOKEN = ("eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJhdWQiOiJwdWJsaWMiLCJleHAiOjE3OTM4NTgxNjIs"
         "Imlzc3VlciI6ImNvbS5idXR0ZXJmbHkiLCJzdWIiOiJhc2lnbiIsInVzZXJJZCI6NTY3NzU4MX0"
         ".yjzuUUUK1hlQBzlTQ703ZYemCvfL97EYsQNUCyEVET4")


def req(path, qp=None, hdrs=None):
    url = path if path.startswith("http") else BASE + path
    if qp:
        url += ("&" if "?" in url else "?") + urllib.parse.urlencode(qp)
    h = {"User-Agent": UA, "Accept": "application/json,text/html,*/*",
         "Accept-Language": "zh-CN,zh;q=0.9"}
    if hdrs:
        h.update(hdrs)
    try:
        with OP.open(urllib.request.Request(url, headers=h), timeout=15) as r:
            return r.status, dict(r.headers), r.read()
    except urllib.error.HTTPError as e:
        return e.code, dict(e.headers) if e.headers else {}, e.read()
    except Exception as e:
        return 0, {}, str(e).encode()


PATHS = [
    "/api/app/media/home",
    "/api/app/ping/config",
    "/api/app/media/short/hot",
    "/api/app/live/home",
    "/api/app/publish/contents",
    "/api/app/media/topic/details",
]

print("=== 无鉴权 ===")
for p in PATHS:
    st, hd, b = req(p)
    ct = (hd.get("Content-Type") or "")[:30]
    txt = b[:200].decode("utf-8", "replace").replace("\n", " ")
    print("\n[%-34s] -> %s %5d %s" % (p, st, len(b), ct))
    print("   ", txt[:180])

print("\n\n=== 带 token 头几种形式 ===")
for name, hdrs in (("Authorization Bearer", {"Authorization": "Bearer " + TOKEN}),
                   ("token", {"token": TOKEN}),
                   ("X-Token", {"X-Token": TOKEN})):
    st, hd, b = req("/api/app/media/home", None, hdrs)
    txt = b[:160].decode("utf-8", "replace").replace("\n", " ")
    print("  %-22s -> %s %d  %s" % (name, st, len(b), txt[:130]))
