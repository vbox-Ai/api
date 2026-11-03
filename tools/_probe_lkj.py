# -*- coding: utf-8 -*-
"""lclf / km / javdb 接口实测"""
import json
import os
import urllib.error
import urllib.parse
import urllib.request

OP = urllib.request.build_opener(urllib.request.ProxyHandler({}))
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "_dec")
os.makedirs(OUT, exist_ok=True)
UA = "okhttp/3.14.9"


def call(url, qp=None, data=None, hdrs=None, timeout=18):
    if qp:
        url += ("&" if "?" in url else "?") + urllib.parse.urlencode(qp)
    h = {"User-Agent": UA, "Accept": "application/json, text/plain, */*"}
    if hdrs:
        h.update(hdrs)
    body = None
    if data is not None:
        if isinstance(data, dict):
            body = urllib.parse.urlencode(data).encode()
            h.setdefault("Content-Type", "application/x-www-form-urlencoded")
        else:
            body = data
    req = urllib.request.Request(url, data=body, headers=h,
                                 method="POST" if body is not None else "GET")
    try:
        with OP.open(req, timeout=timeout) as r:
            return r.status, r.headers.get("Content-Type"), r.read()
    except urllib.error.HTTPError as e:
        return e.code, (e.headers.get("Content-Type") if e.headers else ""), e.read()
    except Exception as e:
        return 0, None, ("%s: %s" % (type(e).__name__, e)).encode()


def show(tag, url, qp=None, data=None, hdrs=None, limit=700):
    st, ct, body = call(url, qp, data, hdrs)
    print("\n" + "=" * 76)
    print("[%s] %s%s -> %s %s %d bytes" %
          (tag, url, ("?" + urllib.parse.urlencode(qp)) if qp else "", st, ct, len(body)))
    txt = body.decode("utf-8", "replace")
    print(txt[:limit].replace("\n", " ")[:limit])
    return st, txt


print("#" * 76)
print("# lclf 绿茶楼凤  https://lclf.lol")
print("#" * 76)
for qp in [{"pageNo": 1, "pageSize": 20}, {"pageNo": 1, "pageSize": 20, "city": ""}]:
    show("feed", "https://lclf.lol/api/post/feed", qp)
show("top", "https://lclf.lol/api/post/top")
show("feed别名", "https://lclf.lol/api/post/feed?pageNo=1&pageSize=5")

print("\n" + "#" * 76)
print("# km 快猫  https://icef4vn.xyz")
print("#" * 76)
show("videos", "https://icef4vn.xyz/api/videos/", {"page": 1, "limit": 20})
show("videos2", "https://icef4vn.xyz/api/videos/listAll", {"page": 1})
show("detail", "https://icef4vn.xyz/api/videos/detail", {"id": 1})

print("\n" + "#" * 76)
print("# javdb  https://jdforrepam.com")
print("#" * 76)
for p in ["api/v1/movies/latest", "api/v1/movies/hot", "api/v2/search?q=test",
          "api/v1/movies", "api/v4/movies/latest"]:
    show("javdb", "https://jdforrepam.com/" + p, {"page": 1})
