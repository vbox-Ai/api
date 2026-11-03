# -*- coding: utf-8 -*-
"""mmmh 迷妹漫画：接口探测 + 加密响应分析"""
import base64
import binascii
import json
import urllib.error
import urllib.parse
import urllib.request

BASE = "https://public.mino02.live"
OP = urllib.request.build_opener(urllib.request.ProxyHandler({}))
UA = "okhttp/3.14.9"


def call(path, qp=None, hdrs=None):
    url = BASE + path
    if qp:
        url += "?" + urllib.parse.urlencode(qp)
    h = {"User-Agent": UA, "Accept": "*/*"}
    if hdrs:
        h.update(hdrs)
    req = urllib.request.Request(url, headers=h)
    try:
        with OP.open(req, timeout=20) as r:
            return r.status, dict(r.headers), r.read()
    except urllib.error.HTTPError as e:
        return e.code, dict(e.headers) if e.headers else {}, e.read()
    except Exception as e:
        return 0, {}, ("%s: %s" % (type(e).__name__, e)).encode()


PATHS = [
    "/v1/animat/category",
    "/v1/animat/category/list",
    "/v1/fiction/category",
    "/v1/fiction/category/list",
    "/v1/search/animat?keyword=test",
    "/v1/animat/category/list?cat_id=1&page=1",
]

print("=" * 76)
for p in PATHS:
    st, hd, body = call(p)
    keys = {k.lower(): v for k, v in hd.items()}
    print("\n[%s] -> %s  %d bytes" % (p, st, len(body)))
    print("   ctype=%s  x-resp-len=%s" % (keys.get("content-type"), keys.get("x-response-length")))
    print("   body[:160]:", body[:160].decode("utf-8", "replace"))
    # 尝试 base64 解码看熵
    try:
        s = body.decode("utf-8", "replace").strip()
        raw = base64.b64decode(s + "=" * ((4 - len(s) % 4) % 4))
        print("   b64 解码 %d 字节  head=%s" % (len(raw), binascii.hexlify(raw[:12]).decode()))
        # 是否 gzip
        if raw[:2] == b"\x1f\x8b":
            import gzip
            print("   是 gzip:", gzip.decompress(raw)[:120])
    except Exception as e:
        print("   b64 解码失败:", type(e).__name__)

print("\n" + "=" * 76)
print("试试带 token / 设备头")
for hdrs in ({"Authorization": "Bearer "},
             {"Authorization": "Bearer ae52f7ffd2dd66ba5743bb180188b991"},
             {"X-Requested-With": "XMLHttpRequest"},
             {"token": "ae52f7ffd2dd66ba5743bb180188b991"}):
    st, h2, b2 = call("/v1/animat/category", None, hdrs)
    print("  %-52s -> %s %d  %s" % (json.dumps(hdrs, ensure_ascii=False)[:52],
                                    st, len(b2), b2[:60].decode("utf-8", "replace")))
