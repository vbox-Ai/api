# -*- coding: utf-8 -*-
"""fl2 第六轮：把列表/搜索/详情/播放路径定下来

已知：register/token ✅、v2/menu/type ✅（pixeled 1/4/16/18/8/15…，unpixeled 3/5/7/19/14/11…）、
      v1/actors ✅。路径字面量：v1/menu/  v1/actor/  v2/search/  v2/vertical/list/

本轮对这些路径分别试 GET / POST（服务端对 GET 返 405 的说明它要 POST），
打印解密后的 status.code 与顶层 key，命中即落盘。
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


def dec(raw, vtag):
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
        return "dec-fail:%s" % e


def call(path_field, method="GET", params=None, token="", dev="", url_path=None):
    mp = {}
    if params:
        mp.update({str(k): v for k, v in params.items()})
    mp["path"] = path_field
    mp["timestamp"] = int(time.time())
    payload = envelope(mp)
    headers = {"User-Agent": "Fulao2/Android 2.40; Xiaomi MI 14", "X-Info": XINFO,
               "Uuid": dev, "Accept": "application/json"}
    if token:
        headers["Authorization"] = "Bearer " + token
    url = HOST + "/" + (url_path or path_field).lstrip("/")
    if method == "GET":
        q = dict(params or {})
        q["payload"] = payload
        url += "?" + urllib.parse.urlencode(q)
        req = urllib.request.Request(url, headers=headers)
    else:
        headers["Content-Type"] = "application/x-www-form-urlencoded"
        body = {"payload": payload}
        if params:
            body.update({str(k): str(v) for k, v in params.items()})
        req = urllib.request.Request(url, data=urllib.parse.urlencode(body).encode(),
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


def reg(dev):
    st, hdrs, raw = call("v1/register/token", "POST", dev=dev, url_path="/v1/register/token")
    # register 需要额外字段：直接用 r4 的做法补 body
    return None


def register(dev):
    ts = int(time.time())
    mp = {
        "device_id": dev,
        "key": hashlib.sha256(("jav" + dev + "jav").encode()).hexdigest(),
        "utm_medium": "", "model": "Xiaomi MI 14",
        "universal_id": base64.b64encode(dev.encode()).decode(),
        "platform": "Android",
        "path": "v1/register/token", "timestamp": ts,
    }
    body = urllib.parse.urlencode({"payload": envelope(mp)}).encode()
    req = urllib.request.Request(
        HOST + "/v1/register/token", data=body, method="POST",
        headers={"User-Agent": "Fulao2/Android 2.40; Xiaomi MI 14", "X-Info": XINFO,
                 "Uuid": dev, "Content-Type": "application/x-www-form-urlencoded"})
    with OP.open(req, timeout=20) as r:
        j = json.loads(dec(r.read(), r.headers.get("X-VTag", "")))
    return j["response"]["token"]


if __name__ == "__main__":
    dev = str(uuid.uuid4())
    tok = register(dev)
    print("[token] len=%d" % len(tok))

    cases = [
        ("v1/menu/1", {"page": 1}),
        ("v1/menu/4", {"page": 1}),
        ("v1/menu/1", {"page": 1, "id": 1}),
        ("v2/search/SSIS", {"page": 1}),
        ("v2/search/", {"keyword": "SSIS", "page": 1}),
        ("v2/vertical/list/1", {"page": 1}),
        ("v1/actor/19206", {"page": 1}),
    ]
    for path, params in cases:
        for method in ("POST", "GET"):
            st, hdrs, raw = call(path, method, params, tok, dev)
            txt = dec(raw, hdrs.get("X-VTag", ""))
            code = None
            keys = ""
            try:
                j = json.loads(txt)
                code = (j.get("status") or {}).get("code")
                rs = j.get("response")
                keys = ",".join(list(rs.keys())[:8]) if isinstance(rs, dict) else type(rs).__name__
            except Exception:
                pass
            ok = code == 200
            print("%-22s %-5s HTTP %-4s code=%-5s keys=%-40s %s" % (
                path, method, st, code, keys, "★" if ok else txt[:60].replace("\n", " ")))
            if ok and keys:
                fn = "tools/_dec/fl2_%s_%s.json" % (path.replace("/", "_"), method.lower())
                open(fn, "w", encoding="utf-8").write(txt)
