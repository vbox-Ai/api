# -*- coding: utf-8 -*-
"""fl2 第二轮：用 register/token 的 "decrypt failure" 当判据，扫信封变体

服务端很明确：payload 结构对（能取到 payload），但解不开 → 加密层差异。
枚举四维：
  A. payload 组装：iv.ct / base64(iv+ct) / hex(iv+ct) / 仅 ct
  B. key：base64解码后的 32B / 原 base64 字符串 utf8 / sha256(32B) / 32B 前 16B(AES-128)
  C. path 字段："/v1/register/token" / "v1/register/token"
  D. timestamp：秒 / 毫秒
命中判据：响应里不再出现 "decrypt failure"。
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
from Crypto.Util.Padding import pad

RAW_KEY_B64 = "euZN1Gg3JIwWOEWhmE7C4l5dSSRU34fyuPMXjtuoqVs="
KEYB = base64.b64decode(RAW_KEY_B64)
XINFO = ("eyJjcGFnZSI6ImxhdW5jaCIsInBsYXRmb3JtIjoyLCJwcGFnZSI6IiIsInZlcnNpb24iOiIy"
         "LjQwIn0=")
OP = urllib.request.build_opener(urllib.request.ProxyHandler({}))
HOST = "https://prja.website"


def build_payload(mp, key, mode, ts_unit):
    iv = uuid.uuid4().bytes[:16]
    body = json.dumps(mp, ensure_ascii=False, separators=(",", ":")).encode()
    ct = AES.new(key, AES.MODE_CBC, iv).encrypt(pad(body, 16))
    if mode == "iv.ct":
        return base64.b64encode(iv).decode() + "." + base64.b64encode(ct).decode()
    if mode == "b64(iv+ct)":
        return base64.b64encode(iv + ct).decode()
    if mode == "hex(iv+ct)":
        return (iv + ct).hex()
    if mode == "ct":
        return base64.b64encode(ct).decode()
    raise ValueError(mode)


def try_register(key, mode, path_form, ts_unit, dev):
    ts = int(time.time() * 1000) if ts_unit == "ms" else int(time.time())
    mp = {
        "device_id": dev,
        "key": hashlib.sha256(("jav" + dev + "jav").encode()).hexdigest(),
        "utm_medium": "",
        "model": "Xiaomi MI 14",
        "universal_id": base64.b64encode(dev.encode()).decode(),
        "platform": "Android",
        "path": path_form,
        "timestamp": ts,
    }
    payload = build_payload(mp, key, mode, ts_unit)
    body = urllib.parse.urlencode({"payload": payload}).encode()
    req = urllib.request.Request(
        HOST + "/v1/register/token", data=body, method="POST",
        headers={"User-Agent": "Fulao2/Android 2.40; Xiaomi MI 14",
                 "X-Info": XINFO, "Uuid": dev,
                 "Content-Type": "application/x-www-form-urlencoded",
                 "Accept": "application/json"})
    try:
        with OP.open(req, timeout=15) as r:
            return r.status, r.read().decode("utf-8", "replace")
    except urllib.error.HTTPError as e:
        try:
            return e.code, e.read().decode("utf-8", "replace")
        except Exception:
            return e.code, ""
    except Exception as e:
        return 0, str(e)[:60]


if __name__ == "__main__":
    dev = str(uuid.uuid4())
    keys = {
        "b64decoded32": KEYB,
        "utf8_b64str": RAW_KEY_B64.encode(),
        "sha256": hashlib.sha256(KEYB).digest(),
        "aes128": KEYB[:16],
    }
    print("%-14s %-12s %-24s %-4s %s" % ("key", "payload", "path/ts", "HTTP", "响应"))
    print("-" * 108)
    hit = []
    for kn, key in keys.items():
        for mode in ("iv.ct", "b64(iv+ct)", "hex(iv+ct)", "ct"):
            for path_form in ("/v1/register/token", "v1/register/token"):
                for ts_unit in ("s", "ms"):
                    st, txt = try_register(key, mode, path_form, ts_unit, dev)
                    bad = "decrypt failure" in txt
                    print("%-14s %-12s %-24s %-4s %s%s" % (
                        kn, mode, "%s/%s" % (path_form[:14], ts_unit), st,
                        txt[:90].replace("\n", " "), "" if bad else "   ★"))
                    if not bad:
                        hit.append((kn, mode, path_form, ts_unit, txt[:400]))
    print("\n非 decrypt-failure 的组合 %d 个" % len(hit))
    for h in hit[:5]:
        print(h)
