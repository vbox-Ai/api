# -*- coding: utf-8 -*-
"""cgw 吃瓜网：接口探测（api.php/api/...）"""
import json
import urllib.error
import urllib.parse
import urllib.request

OP = urllib.request.build_opener(urllib.request.ProxyHandler({}))
UA = ("Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) "
      "AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Mobile/15E148 Safari/604.1")
BASE = "https://h96h69.com"


def req(path, qp=None, data=None, method=None, hdrs=None):
    url = path if path.startswith("http") else BASE + path
    if qp:
        url += ("&" if "?" in url else "?") + urllib.parse.urlencode(qp)
    h = {"User-Agent": UA, "Accept": "application/json,text/html,*/*",
         "Accept-Language": "zh-CN,zh;q=0.9", "Referer": BASE + "/"}
    if hdrs:
        h.update(hdrs)
    body = None
    if data is not None:
        body = urllib.parse.urlencode(data).encode()
        h.setdefault("Content-Type", "application/x-www-form-urlencoded")
    r = urllib.request.Request(url, data=body, headers=h,
                               method=method or ("POST" if body else "GET"))
    try:
        with OP.open(r, timeout=15) as resp:
            return resp.status, resp.url, dict(resp.headers), resp.read()
    except urllib.error.HTTPError as e:
        return e.code, url, dict(e.headers) if e.headers else {}, e.read()
    except Exception as e:
        return 0, url, {}, str(e).encode()


print("=== 1) 根路径 + 跳转 ===")
st, final, hd, b = req("/")
print("  / -> %s  最终URL=%s  %d bytes" % (st, final, len(b)))
print("  ctype:", hd.get("Content-Type"))
print("  head:", b[:200].decode("utf-8", "replace").replace("\n", " "))

print("\n=== 2) API 探测 ===")
APIS = [
    ("/api.php/api/videos/list_category", None),
    ("/api.php/api/videos/list_contents", {"page": 1, "category_id": 1}),
    ("/api.php/api/contents/list_category", None),
    ("/api.php/api/contents/list_contents", {"page": 1, "category_id": 1}),
    ("/api.php/api/videos/list_category", {"page": 1}),
]
for p, qp in APIS:
    st, final, hd, b = req(p, qp)
    ct = (hd.get("Content-Type") or "")[:30]
    txt = b[:200].decode("utf-8", "replace").replace("\n", " ")
    print("\n[%s%s] -> %s %d %s" % (p, ("?" + urllib.parse.urlencode(qp)) if qp else "", st, len(b), ct))
    print("   ", txt[:180])

print("\n=== 3) 常见 PHP 接口风格补充探测 ===")
for p, qp in [("/api.php", None),
              ("/api.php/api/index/init", None),
              ("/api.php/api/videos/index", None),
              ("/api.php/api/contents/index", None)]:
    st, final, hd, b = req(p, qp)
    print("  %-38s -> %-4s %d %s" % (p, st, len(b),
                                     b[:90].decode("utf-8", "replace").replace("\n", " ")))
