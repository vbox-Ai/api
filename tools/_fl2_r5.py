# -*- coding: utf-8 -*-
"""fl2 第五轮：拿到 token 后跑业务接口

信封已通（r4）：payload = b64(iv) + "." + b64(AES(json))，path 字段不带前导斜杠；
响应 = AES-256-CBC，key=utf8("db6f7f9e5d7a770e0e3497a7d7a077f5")，iv=utf8(md5(X-VTag)[8:24])。

本轮枚举业务路径（v1/menu/*、v2/menu/type、v2/vertical/list/*、v2/search/*、v1/actors），
用解密后的 status.code 判断是否命中。
"""
import base64
import hashlib
import json
import time
import urllib.error
import urllib.parse
import urllib.request
import uuid

from Crypto.Cipher import AES
from Crypto.Util.Padding import pad, unpad

REQ_KEY = base64.b64decode("euZN1Gg3JIwWOEWhmE7C4l5dSSRU34fyuPMXjtuoqVs=")
RESP_KEY = b"db6f7f9e5d7a770e0e3497a7d7a077f5"
XINFO = ("eyJjcGFnZSI6ImxhdW5jaCIsInBsYXRmb3JtIjoyLCJwcGFnZSI6IiIsInZlcnNpb24iOiIy"
         "LjQwIn0=")
OP = urllib.request.build_opener(urllib.request.ProxyHandler({}))
HOST = "https://prja.website"


def envelope(mp):
    iv = uuid.uuid4().bytes[:16]
    body = json.dumps(mp, ensure_ascii=False, separators=(",", ":")).encode()
    ct = AES.new(REQ_KEY, AES.MODE_CBC, iv).encrypt(pad(body, 16))
    return base64.b64encode(iv).decode() + "." + base64.b64encode(ct).decode()


def dec_resp(raw, vtag):
    h = hashlib.md5((vtag or "").encode()).hexdigest()
    iv = h[8:24].encode()
    txt = raw.decode("utf-8", "replace").strip()
    if txt.lstrip()[:1] in ("{", "["):
        return txt
    try:
        pt = AES.new(RESP_KEY, AES.MODE_CBC, iv).decrypt(
            base64.b64decode(txt + "=" * (-len(txt) % 4)))
        try:
            pt = unpad(pt, 16)
        except Exception:
            pass
        return pt.decode("utf-8", "replace")
    except Exception as e:
        return "解密失败: %s" % e


def call(path_field, url_path=None, params=None, data=None, method="GET", token="", dev=""):
    ts = int(time.time())
    mp = {}
    if params:
        mp.update({str(k): v for k, v in params.items()})
    if data:
        mp.update({str(k): v for k, v in data.items()})
    mp["path"] = path_field
    mp["timestamp"] = ts
    payload = envelope(mp)
    headers = {"User-Agent": "Fulao2/Android 2.40; Xiaomi MI 14", "X-Info": XINFO,
               "Uuid": dev, "Accept": "application/json"}
    if token:
        headers["Authorization"] = "Bearer " + token
    url = HOST + (url_path or ("/" + path_field))
    if method == "GET":
        q = {}
        if params:
            q.update({k: v for k, v in params.items()})
        q["payload"] = payload
        url += ("&" if "?" in url else "?") + urllib.parse.urlencode(q)
        req = urllib.request.Request(url, headers=headers)
    else:
        headers["Content-Type"] = "application/x-www-form-urlencoded"
        req = urllib.request.Request(url, data=urllib.parse.urlencode({"payload": payload}).encode(),
                                     method="POST", headers=headers)
    try:
        with OP.open(req, timeout=20) as r:
            return r.status, dict(r.headers), r.read()
    except urllib.error.HTTPError as e:
        try:
            return e.code, dict(e.headers or {}), e.read()
        except Exception:
            return e.code, {}, b""
    except Exception as e:
        return 0, {}, str(e)[:60].encode()


def register(dev):
    st, hdrs, raw = call("v1/register/token", "/v1/register/token", method="POST", dev=dev,
                         data={"device_id": dev,
                               "key": hashlib.sha256(("jav" + dev + "jav").encode()).hexdigest(),
                               "utm_medium": "", "model": "Xiaomi MI 14",
                               "universal_id": base64.b64encode(dev.encode()).decode(),
                               "platform": "Android"})
    txt = dec_resp(raw, hdrs.get("X-VTag", ""))
    try:
        j = json.loads(txt)
        return j["response"]["token"]
    except Exception:
        print("[register 失败]", txt[:200])
        return ""


if __name__ == "__main__":
    dev = str(uuid.uuid4())
    tok = register(dev)
    print("[token]", tok[:40], "...", len(tok))
    cases = [
        ("v1/menu/navicate", "GET", None),
        ("v1/menu/nav", "GET", None),
        ("v2/menu/type", "GET", None),
        ("v1/user/info", "GET", None),
        ("v1/actors", "GET", {"page": 1}),
        ("v2/vertical/list/1", "GET", {"page": 1}),
        ("v2/search/keyword", "GET", {"keyword": "SSIS", "page": 1}),
        ("v2/search/", "GET", {"keyword": "SSIS", "page": 1}),
    ]
    for path, method, params in cases:
        st, hdrs, raw = call(path, None, params, None, method, tok, dev)
        txt = dec_resp(raw, hdrs.get("X-VTag", ""))
        flag = ""
        try:
            j = json.loads(txt)
            code = (j.get("status") or {}).get("code")
            flag = "  ★" if code == 200 else ""
        except Exception:
            code = "?"
        print("\n%-24s %-5s HTTP %-4s code=%-4s %s%s" % (
            path, method, st, code, txt[:140].replace("\n", " "), flag))
        if flag:
            open("tools/_dec/fl2_%s.json" % path.replace("/", "_"), "w",
                 encoding="utf-8").write(txt)
