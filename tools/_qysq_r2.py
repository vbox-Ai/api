# -*- coding: utf-8 -*-
"""qysq 妻友社区：按还原的 HMAC-SHA1 签名实测"""
import hashlib
import hmac
import json
import time
import urllib.error
import urllib.parse
import urllib.request
import uuid

OP = urllib.request.build_opener(urllib.request.ProxyHandler({}))
DEV_UA = "DevType=Apple iPhone mobile;SysType=light;Ver=2.1.2;BuildID=Mobile Safari 18.5"
BROWSER_UA = ("Mozilla/5.0 (iPhone; CPU iPhone OS 18_5 like Mac OS X) "
              "AppleWebKit/605.1.15 (KHTML, like Gecko) Version/18.5 Mobile/15E148 Safari/604.1")
SECRET = b"gH3nA7fR9tV1jY6z"
TOKEN = ("eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJhdWQiOiJwdWJsaWMiLCJleHAiOjE3OTM4NTgxNjIs"
         "Imlzc3VlciI6ImNvbS5idXR0ZXJmbHkiLCJzdWIiOiJhc2lnbiIsInVzZXJJZCI6NTY3NzU4MX0"
         ".yjzuUUUK1hlQBzlTQ703ZYemCvfL97EYsQNUCyEVET4")
BASE = "https://d1kmvkv4iwtiup.cloudfront.net"


def gen_sign(path):
    ts = str(int(time.time()))          # utc 秒
    nonce = str(uuid.uuid4())
    msg = "%s&%s&%s&%s&%s" % (TOKEN, path, DEV_UA, ts, nonce)
    sign = hmac.new(SECRET, msg.encode("utf-8"), hashlib.sha1).hexdigest()
    return "timestamp=%s;sign=%s;nonce=%s" % (ts, sign, nonce)


def call(path, body=None, method=None):
    xkey = gen_sign(path)
    h = {
        "X-User-Agent": DEV_UA,
        "user-agent": BROWSER_UA,
        "authorization": "Bearer " + TOKEN,
        "x-api-key": xkey,
        "Accept": "application/json",
        "Content-Type": "application/json",
    }
    data = None
    if body is not None:
        data = json.dumps(body, ensure_ascii=False).encode("utf-8")
    req = urllib.request.Request(BASE + path, data=data, headers=h,
                                 method=method or ("POST" if data else "GET"))
    try:
        with OP.open(req, timeout=15) as r:
            return r.status, r.read()
    except urllib.error.HTTPError as e:
        return e.code, e.read()
    except Exception as e:
        return 0, str(e).encode()


PATHS = ["/api/app/media/home", "/api/app/ping/config", "/api/app/media/short/hot",
         "/api/app/live/home"]

print("=== 按签名请求（POST + 空体）===")
for p in PATHS:
    st, b = call(p, {})
    print("\n[%-32s] -> %s %d" % (p, st, len(b)))
    print("   ", b[:260].decode("utf-8", "replace").replace("\n", " "))

print("\n\n=== GET 试 ===")
for p in PATHS[:2]:
    st, b = call(p, None, "GET")
    print("  %-32s -> %s %s" % (p, st, b[:150].decode("utf-8", "replace").replace("\n", " ")))
