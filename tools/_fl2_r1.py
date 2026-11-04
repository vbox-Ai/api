# -*- coding: utf-8 -*-
"""fl2（fulao2）第一轮：按 Fl2Interceptor::onRequest 还原信封

asm：module/fl2/network/interceptor.dart @0x8d76e8（size 0x7c8）

    KEY    = base64Decode("euZN1Gg3JIwWOEWhmE7C4l5dSSRU34fyuPMXjtuoqVs=")   → 32B（AES-256）
    IV     = _randomIv()  16 随机字节
    map    = 业务参数
             + timestamp（秒）
             + path（请求路径，如 "/v1/menu/xxx"）
    POST 特例 register/token：
             device_id    = <Uuid>
             key          = sha256("jav" + device_id + "jav")     ← _hashKey
             utm_medium   = ""
             model        = <manufacturer> + <model>
             universal_id = base64(device_id)                      ← _universalId
             platform     = "Android"
    payload = base64(IV) + "." + base64( AES-256-CBC( jsonEncode(map), KEY, IV ) )
    GET  → ?payload=…
    POST → Content-Type: application/x-www-form-urlencoded，body=payload=…

头：User-Agent: "Fulao2/Android 2.40; " + model
    Authorization: "Bearer " + token_fl2
    X-Info: eyJjcGFnZSI6ImxhdW5jaCIsInBsYXRmb3JtIjoyLCJwcGFnZSI6IiIsInZlcnNpb24iOiIyLjQwIn0=
    Uuid: <SpUtil "Uuid">
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

KEY = base64.b64decode("euZN1Gg3JIwWOEWhmE7C4l5dSSRU34fyuPMXjtuoqVs=")
XINFO = ("eyJjcGFnZSI6ImxhdW5jaCIsInBsYXRmb3JtIjoyLCJwcGFnZSI6IiIsInZlcnNpb24iOiIy"
         "LjQwIn0=")
UA_BASE = "Fulao2/Android 2.40; "
OP = urllib.request.build_opener(urllib.request.ProxyHandler({}))

HOSTS = ["https://prja.website"]


def hash_key(dev):
    return hashlib.sha256(("jav" + dev + "jav").encode()).hexdigest()


def universal_id(dev):
    return base64.b64encode(dev.encode()).decode()


def envelope(mp):
    iv = bytes(uuid.uuid4().bytes[:16])
    body = json.dumps(mp, ensure_ascii=False, separators=(",", ":")).encode()
    ct = AES.new(KEY, AES.MODE_CBC, iv).encrypt(pad(body, 16))
    return base64.b64encode(iv).decode() + "." + base64.b64encode(ct).decode()


def call(host, path, params=None, data=None, method="GET", token="", dev=""):
    ts = int(time.time())
    mp = {}
    if params:
        mp.update({str(k): str(v) for k, v in params.items()})
    if data:
        mp.update({str(k): (v if not isinstance(v, (int, float)) else v) for k, v in data.items()})
    if "register/token" in path:
        d = dev or str(uuid.uuid4())
        mp.update({
            "device_id": d,
            "key": hash_key(d),
            "utm_medium": "",
            "model": "Xiaomi MI 14",
            "universal_id": universal_id(d),
            "platform": "Android",
        })
    mp["path"] = path
    mp["timestamp"] = ts
    payload = envelope(mp)

    headers = {
        "User-Agent": UA_BASE + "Xiaomi MI 14",
        "X-Info": XINFO,
        "Accept": "application/json",
    }
    if token:
        headers["Authorization"] = "Bearer " + token
    if dev:
        headers["Uuid"] = dev

    url = host + path
    if method == "GET":
        # path 拼在 url 上，其余参数并进 query
        if params:
            url += ("&" if "?" in url else "?") + urllib.parse.urlencode(
                {k: v for k, v in params.items()})
        url += ("&" if "?" in url else "?") + "payload=" + urllib.parse.quote(payload)
        req = urllib.request.Request(url, headers=headers)
    else:
        body = urllib.parse.urlencode({"payload": payload}).encode()
        headers["Content-Type"] = "application/x-www-form-urlencoded"
        req = urllib.request.Request(url, data=body, method="POST", headers=headers)
    try:
        with OP.open(req, timeout=20) as r:
            return r.status, r.read()
    except urllib.error.HTTPError as e:
        try:
            return e.code, e.read()
        except Exception:
            return e.code, b""
    except Exception as e:
        return 0, str(e)[:80].encode()


if __name__ == "__main__":
    dev = str(uuid.uuid4())
    print("[device]", dev)
    for host in HOSTS:
        for method, path in (("GET", "/v1/host"), ("GET", "/v1/menu/navicate"),
                             ("POST", "/v1/register/token")):
            st, body = call(host, path, method=method, dev=dev)
            txt = body.decode("utf-8", "replace")
            print("\n%-6s %-26s HTTP %-4s %s" % (method, path, st, txt[:200].replace("\n", " ")))
            if st == 200 and txt.lstrip()[:1] in ("{", "["):
                open("tools/_dec/fl2_%s.json" % path.strip("/").replace("/", "_"),
                     "w", encoding="utf-8").write(txt)
