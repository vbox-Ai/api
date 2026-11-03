# -*- coding: utf-8 -*-
"""aijav / mdtv 共用签名链实测

签名  encode_sign = MD5( sorted("k=v" join "&") + "&NRkw0g3iJLDvw5tJ5PuVt5276z0SOuyL" )
请求  AES key="RWf23muavYNWSdef"(16) , 字段 post-data
响应  AES key="0XxdjmI55ZjjqQLO3nI7gGqrBP0Vz9jS"(32) , IV="RWf23muavY"+suffix
"""
import base64
import hashlib
import json
import time
import urllib.error
import urllib.request

from Crypto.Cipher import AES
from Crypto.Util.Padding import pad, unpad

SIGN_SECRET = "&NRkw0g3iJLDvw5tJ5PuVt5276z0SOuyL"
REQ_KEY = b"RWf23muavYNWSdef"                 # 16 -> AES-128
REQ_IV_CAND = [
    ("respk16", b"0XxdjmI55ZjjqQLO"[:16]),
    ("zerokey16", b"\x00" * 16),
    ("suffixpad", (b"NWSdef" + b"\x00" * 10)[:16]),
    ("reqkey", REQ_KEY),
]
RESP_KEY = b"0XxdjmI55ZjjqQLO3nI7gGqrBP0Vz9jS"   # 32 -> AES-256
RESP_IV_HEAD = b"RWf23muavY"
UA = "okhttp/3.14.9"


def sign_of(mp):
    kv = "&".join("%s=%s" % (k, mp[k]) for k in sorted(mp.keys()))
    return hashlib.md5((kv + SIGN_SECRET).encode("utf-8")).hexdigest()


def dec_resp(body):
    j = json.loads(body.decode("utf-8", "replace"))
    if "data" not in j:
        return j
    d = j["data"]
    suf = str(j.get("suffix") or "")
    raw = base64.b64decode(d + "=" * ((4 - len(d) % 4) % 4))
    iv = (RESP_IV_HEAD + suf.encode())[:16]
    p = AES.new(RESP_KEY, AES.MODE_CBC, iv).decrypt(raw)
    try:
        p = unpad(p, 16)
    except Exception:
        pass
    try:
        return json.loads(p.decode("utf-8", "replace"))
    except Exception:
        return {"_plain": p[:300].decode("utf-8", "replace")}


def try_call(base, path, biz, iv_name, iv):
    ts = str(int(time.time()))
    plain = json.dumps(biz, ensure_ascii=False, separators=(",", ":")).encode()
    post_data = base64.b64encode(AES.new(REQ_KEY, AES.MODE_CBC, iv).encrypt(pad(plain, 16))).decode()
    mp = {"post-data": post_data, "timestamp": ts}
    mp["encode_sign"] = sign_of(mp)
    body = json.dumps(mp, ensure_ascii=False).encode()
    req = urllib.request.Request(base.rstrip("/") + path, data=body, headers={
        "User-Agent": UA, "Content-Type": "application/json", "Accept": "application/json"},
        method="POST")
    op = urllib.request.build_opener(urllib.request.ProxyHandler({}))
    try:
        with op.open(req, timeout=20) as r:
            return r.status, dec_resp(r.read())
    except urllib.error.HTTPError as e:
        try:
            return e.code, dec_resp(e.read())
        except Exception:
            return e.code, {"_err": "decode fail"}
    except Exception as e:
        return 0, {"_err": "%s: %s" % (type(e).__name__, e)}


TARGETS = [
    ("aijav", "https://newavapi.9xyrp3kg4b86.com", ["/video/lists", "/tag/lists", "/actor/lists"]),
    ("mdtv", "https://spi.d5c4a712.com", ["/video/list", "/video/channel", "/video/tags"]),
]
BIZ = [{"page": 1, "limit": 20}, {"page": 1, "pageSize": 20}, {"page": 1}]

for name, base, paths in TARGETS:
    print("\n" + "=" * 76)
    print(name, base)
    hit = False
    for path in paths:
        for biz in BIZ:
            for ivn, iv in REQ_IV_CAND:
                st, j = try_call(base, path, biz, ivn, iv)
                code = j.get("code")
                msg = str(j.get("msg") or j.get("message") or "")[:26]
                has = bool(j.get("data")) or bool(j.get("list"))
                flag = "★" if (code in (0, 200) or has) else " "
                print(" %s %-16s %-26s %-12s -> %s code=%s msg=%s data=%s" %
                      (flag, path, json.dumps(biz, separators=(",", ":")), ivn, st, code, msg, has))
                if flag == "★":
                    print("     样本:", json.dumps(j, ensure_ascii=False)[:400])
                    hit = True
                    break
            if hit:
                break
        if hit:
            break
    if not hit:
        print("  （本轮未命中）")
