# -*- coding: utf-8 -*-
"""kpsp 实测 v2：x-data 在响应体 JSON 里，按 Fernet 结构手工解

CryptoUtil::ksSpDecrypt (0x8f2484)
  hex = urlsafe_b64decode(x-data).hex()
  hex[0:18]       = version(1B) + timestamp(8B)   ← 丢弃
  hex[18:50]      = IV (16B)
  hex[50:len-64]  = ciphertext
  hex[len-64:]    = HMAC-SHA256 (32B)             ← 校验被跳过
  AES-128-CBC(key=7af630c7e06ccecfa70d5a085f189c06)
"""
import base64
import binascii
import json
import os
import urllib.error
import urllib.parse
import urllib.request

from Crypto.Cipher import AES
from Crypto.Util.Padding import unpad

BASE = "https://sm-api.wieuc.com"
KEY_HEX = "7af630c7e06ccecfa70d5a085f189c06"
OP = urllib.request.build_opener(urllib.request.ProxyHandler({}))
UA = {"User-Agent": "okhttp/3.14.9", "Accept": "application/json"}
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "_dec")
os.makedirs(OUT, exist_ok=True)


def b64url_to_hex(s):
    s = s.replace("-", "+").replace("_", "/").strip()
    s += "=" * ((4 - len(s) % 4) % 4)
    return binascii.hexlify(base64.b64decode(s, validate=False)).decode()


def decrypt(xdata):
    h = b64url_to_hex(xdata)
    if len(h) < 50 + 64:
        raise ValueError("hex 太短: %d" % len(h))
    ver_t = h[0:18]
    iv = bytes.fromhex(h[18:50])
    ct = bytes.fromhex(h[50:len(h) - 64])
    mac = h[len(h) - 64:]
    key = bytes.fromhex(KEY_HEX)
    raw = AES.new(key, AES.MODE_CBC, iv).decrypt(ct)
    try:
        raw = unpad(raw, 16)
    except Exception:
        pass
    return raw, {"ver_ts": ver_t, "iv": h[18:50], "ct_len": len(ct), "mac": mac[:16]}


def call(path, qp=None):
    url = BASE + "/" + path.lstrip("/")
    if qp:
        url += "?" + urllib.parse.urlencode(qp)
    req = urllib.request.Request(url, headers=UA)
    try:
        with OP.open(req, timeout=20) as r:
            return r.status, r.read()
    except urllib.error.HTTPError as e:
        return e.code, e.read()
    except Exception as e:
        return 0, ("%s: %s" % (type(e).__name__, e)).encode()


def fetch_dec(path, qp=None, tag=""):
    st, body = call(path, qp)
    print("\n[%s %s] -> %s %d bytes" % (path, qp or "", st, len(body)))
    try:
        wrap = json.loads(body.decode("utf-8", "replace"))
    except Exception:
        print("  非 JSON:", body[:160])
        return None
    if not isinstance(wrap, dict):
        print("  非 dict:", str(wrap)[:160])
        return None
    xd = wrap.get("x-data") or wrap.get("xData") or wrap.get("data")
    if not isinstance(xd, str):
        print("  无 x-data，键:", list(wrap.keys())[:8])
        print("  ", json.dumps(wrap, ensure_ascii=False)[:300])
        return None
    try:
        plain, meta = decrypt(xd)
    except Exception as e:
        print("  ✗ 解密失败:", type(e).__name__, e)
        return None
    print("  ★ 解密成功 %d 字节  meta=%s" % (len(plain), meta["ct_len"]))
    print("  明文头:", plain[:180])
    try:
        j = json.loads(plain.decode("utf-8"))
    except Exception as e:
        print("  非 JSON:", e)
        return None
    fn = os.path.join(OUT, "kpsp_%s.json" % (tag or "sample"))
    with open(fn, "w", encoding="utf-8") as f:
        json.dump(j, f, ensure_ascii=False, indent=1)
    print("  已存:", os.path.basename(fn))
    probe_structure(j)
    return j


def probe_structure(j):
    if not isinstance(j, dict):
        print("  顶层非 dict:", type(j).__name__, str(j)[:200])
        return
    print("  顶层键:", list(j.keys())[:12])
    for k, v in j.items():
        if isinstance(v, dict):
            print("  %s(键): %s" % (k, list(v.keys())[:12]))
            for k2, v2 in v.items():
                if isinstance(v2, list) and v2 and isinstance(v2[0], dict):
                    print("    %s.%s[0] keys: %s" % (k, k2, list(v2[0].keys())[:16]))
                    print("    样本:", json.dumps(v2[0], ensure_ascii=False)[:700])
        elif isinstance(v, list) and v and isinstance(v[0], dict):
            print("  %s[0] keys: %s" % (k, list(v[0].keys())[:16]))
            print("    样本:", json.dumps(v[0], ensure_ascii=False)[:700])


if __name__ == "__main__":
    fetch_dec("api/vod/video", {"page": 1, "per_page": 20, "site_id": 1}, "list_s1")
