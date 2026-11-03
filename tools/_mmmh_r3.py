# -*- coding: utf-8 -*-
"""mmmh 第三轮：解析配置 + 实测 API 接口"""
import base64
import json
import re
import urllib.error
import urllib.parse
import urllib.request

from Crypto.Cipher import AES
from Crypto.Util.Padding import unpad

OP = urllib.request.build_opener(urllib.request.ProxyHandler({}))
UA = "okhttp/3.14.9"
K = base64.b64decode("h7lkUI0kb25Usb3qTFLefTf8b+8Hs2Y63sANNraUm/Q=")
IV = base64.b64decode("k54Vcjbp6ByR6D83eIoxgw==")


def fetch(url, hdrs=None, timeout=20):
    h = {"User-Agent": UA, "Accept": "application/json, */*"}
    if hdrs:
        h.update(hdrs)
    try:
        with OP.open(urllib.request.Request(url, headers=h), timeout=timeout) as r:
            return r.status, dict(r.headers), r.read()
    except urllib.error.HTTPError as e:
        return e.code, dict(e.headers) if e.headers else {}, e.read()
    except Exception as e:
        return 0, {}, str(e).encode()


def load_cfg():
    txt = open("tools/_dec/mmmh_host_pwa.json", encoding="utf-8").read().strip()
    # 去掉 32 位校验前缀
    i = txt.find("{")
    if i > 0:
        print("跳过前缀:", txt[:i])
    return json.loads(txt[i:])


cfg = load_cfg()
print("配置键:", list(cfg.keys()))
api = cfg.get("api") or []
print("\nAPI hosts:")
for a in api:
    print("  ", a.get("url"), "default=" + str(a.get("default")), "status=" + str(a.get("status")))
comic = cfg.get("comic") or []
print("\nComic endpoints:")
for c in comic:
    print("  url=%s" % c.get("url"))
    print("    chain=%s  tsurl=%s  encrypt=%s  name=%s" % (
        c.get("chain"), c.get("tsurl"), c.get("encrypt"), c.get("name")))

base = None
for a in api:
    if a.get("default") and a.get("status") == 1:
        base = a["url"]
        break
base = base or (api[0]["url"] if api else None)
print("\n选定 base:", base)

print("\n" + "=" * 74)
print("实测接口")
paths = [
    "/v1/animat/category",
    "/v1/animat/category/list",
    "/v1/fiction/category",
    "/v1/fiction/category/list",
    "/v1/animat/category/list?category_id=1&page=1",
]
for p in paths:
    st, hd, body = fetch(base + p)
    keys = {k.lower(): v for k, v in hd.items()}
    print("\n[%s] -> %s  %d bytes" % (p, st, len(body)))
    print("   ctype=%s  x-resp-len=%s" % (keys.get("content-type"), keys.get("x-response-length")))
    head = body[:200].decode("utf-8", "replace")
    print("   head:", head.replace("\n", " ")[:180])
