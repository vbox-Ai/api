# -*- coding: utf-8 -*-
"""fl2 第四轮：响应解密（onResponse @0x8f0d6c 已读出）

    vtag = resp.headers["X-VTag"]
    h    = MD5(vtag) 的 32 位十六进制串
    Key  = utf8("db6f7f9e5d7a770e0e3497a7d7a077f5")      ← 32B ASCII，AES-256
    IV   = utf8(h[8:24])                                ← 16 位十六进制字符，16 字节
    plain= AES-256-CBC-decrypt64(body); jsonDecode

（asm 里 `movz #0x30` + `substring(8, 0x30)` 的 0x30 是 Smi 编码，真实值 24，
  与「h 只有 32 字符、Dart substring 越界必抛」互证。）

本轮：register/token → 拿 X-VTag → 解出 token。
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


def register(dev):
    ts = int(time.time())
    mp = {
        "device_id": dev,
        "key": hashlib.sha256(("jav" + dev + "jav").encode()).hexdigest(),
        "utm_medium": "",
        "model": "Xiaomi MI 14",
        "universal_id": base64.b64encode(dev.encode()).decode(),
        "platform": "Android",
        "path": "v1/register/token",
        "timestamp": ts,
    }
    body = urllib.parse.urlencode({"payload": envelope(mp)}).encode()
    req = urllib.request.Request(
        HOST + "/v1/register/token", data=body, method="POST",
        headers={"User-Agent": "Fulao2/Android 2.40; Xiaomi MI 14",
                 "X-Info": XINFO, "Uuid": dev,
                 "Content-Type": "application/x-www-form-urlencoded",
                 "Accept": "application/json"})
    with OP.open(req, timeout=20) as r:
        return r.status, dict(r.headers), r.read()


if __name__ == "__main__":
    dev = str(uuid.uuid4())
    print("[device]", dev)
    st, hdrs, raw = register(dev)
    vtag = hdrs.get("X-VTag") or hdrs.get("x-vtag") or ""
    print("[register] HTTP %s  X-VTag=%r  body=%dB" % (st, vtag, len(raw)))
    print("[headers]", {k: v for k, v in hdrs.items() if k.lower().startswith("x-")})
    out = dec_resp(raw, vtag)
    print("\n[decrypted]\n%s" % out[:800])
    if out.lstrip()[:1] in ("{", "["):
        open("tools/_dec/fl2_token.json", "w", encoding="utf-8").write(out)
        print("\n★ 已存 tools/_dec/fl2_token.json")
