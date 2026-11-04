# -*- coding: utf-8 -*-
"""fl2 第三轮：register/token 拿到密文了，本轮解它

关键突破（r2）：
  · payload 结构与 key 都对：`base64(iv) + "." + base64(ct)`
  · **map 里的 path 必须是不带前导斜杠的 "v1/register/token"**（带斜杠服务端就 "decrypt failure"）
  · 因此响应是一段 base64 密文（不是 JSON 信封）

本轮只做一件事：把响应密文解开。
可能的布局：ct / iv+ct / iv.ct / 无 IV（固定 IV=0 或 key[:16]）。
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
OP = urllib.request.build_opener(urllib.request.ProxyHandler({}))
HOST = "https://prja.website"
PATH_FIELD = "v1/register/token"


def envelope(mp):
    iv = uuid.uuid4().bytes[:16]
    body = json.dumps(mp, ensure_ascii=False, separators=(",", ":")).encode()
    ct = AES.new(KEY, AES.MODE_CBC, iv).encrypt(pad(body, 16))
    return base64.b64encode(iv).decode() + "." + base64.b64encode(ct).decode()


def register(dev):
    ts = int(time.time())
    mp = {
        "device_id": dev,
        "key": hashlib.sha256(("jav" + dev + "jav").encode()).hexdigest(),
        "utm_medium": "",
        "model": "Xiaomi MI 14",
        "universal_id": base64.b64encode(dev.encode()).decode(),
        "platform": "Android",
        "path": PATH_FIELD,
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
        return r.status, r.read()


def decrypt_blob(raw):
    txt = raw.decode("utf-8", "replace").strip()
    outs = []
    # 形式 1：iv.ct
    if "." in txt:
        a, b = txt.split(".", 1)
        try:
            iv = base64.b64decode(a + "=" * (-len(a) % 4))
            ct = base64.b64decode(b + "=" * (-len(b) % 4))
            if len(iv) == 16 and len(ct) % 16 == 0:
                outs.append(("iv.ct", iv, ct))
        except Exception:
            pass
    blob = None
    try:
        blob = base64.b64decode(txt + "=" * (-len(txt) % 4))
    except Exception:
        pass
    if blob:
        outs.append(("head16+ct", blob[:16], blob[16:]))
        outs.append(("zero+ct", b"\0" * 16, blob))
        outs.append(("tail16", blob[-16:], blob[:-16]))
        outs.append(("keypref", KEY[:16], blob))
    good = []
    for tag, iv, ct in outs:
        if not ct or len(ct) % 16 or len(iv) != 16:
            continue
        try:
            pt = AES.new(KEY, AES.MODE_CBC, iv).decrypt(ct)
        except Exception:
            continue
        try:
            pt = unpad(pt, 16)
        except Exception:
            pass
        s = pt.decode("utf-8", "replace")
        if s.lstrip()[:1] in ("{", "["):
            good.append((tag, s))
    return good


if __name__ == "__main__":
    dev = str(uuid.uuid4())
    print("[device]", dev)
    st, raw = register(dev)
    txt = raw.decode("utf-8", "replace")
    print("[register] HTTP %s  len=%d  head=%s" % (st, len(raw), txt[:90]))
    if txt.lstrip()[:1] == "{":
        print("  → 直接是 JSON：", txt[:300])
    for tag, s in decrypt_blob(raw):
        print("\n★ 解密命中 %s" % tag)
        print(s[:600])
        open("tools/_dec/fl2_token.json", "w", encoding="utf-8").write(s)
        break
    else:
        if txt.lstrip()[:1] != "{":
            print("\n未命中（样本已存 tools/_dec/fl2_reg_raw.txt）")
            open("tools/_dec/fl2_reg_raw.txt", "w", encoding="utf-8").write(txt)
