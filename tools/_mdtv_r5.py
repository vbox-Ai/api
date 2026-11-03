# -*- coding: utf-8 -*-
"""mdtv 修正版：key=AES256(Vq234z...), iv=-p9B..., secret=mdtv 专有"""
import base64
import hashlib
import json
import time
import urllib.error
import urllib.request

from Crypto.Cipher import AES
from Crypto.Util.Padding import pad, unpad

OP = urllib.request.build_opener(urllib.request.ProxyHandler({}))
UA = ("Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) "
      "AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Mobile/15E148 Safari/604.1")
BASE = "https://spi.d5c4a712.com"

REQ_KEY = b"Vq234zBeSdGgYXzVTEfnnjjdmaTkk7A4"      # 32 -> AES-256
REQ_IV = b"-p9B[~PnPsJGDZMX"                        # 16
SECRETS = [
    "&m}q%ea6:LDcmS\\?aK)CeF287bPvd99@E,9Up^",      # 保留反斜杠
    "&m}q%ea6:LDcmS?aK)CeF287bPvd99@E,9Up^",        # 去反斜杠
]
RESP_KEY = REQ_KEY
RESP_IV_HEAD = b"-p9B[~PnPs"


def dec_resp(body):
    j = json.loads(body.decode("utf-8", "replace"))
    if "data" not in j:
        return j
    d = j["data"]
    suf = str(j.get("suffix") or "")
    raw = base64.b64decode(d + "=" * (-len(d) % 4))
    iv = (RESP_IV_HEAD + suf.encode()).ljust(16, b"\x00")[:16]
    if len(raw) % 16:
        return {"_err": "len %d" % len(raw)}
    for kb in (RESP_KEY, b"-p9B[~PnPsJGDZMX"):
        try:
            p = AES.new(kb, AES.MODE_CBC, iv).decrypt(raw)
            try:
                p = unpad(p, 16)
            except Exception:
                pass
            t = p.decode("utf-8", "replace")
            if t.lstrip()[:1] in ("{", "["):
                return json.loads(t)
        except Exception:
            continue
    return {"_raw": raw[:40].hex()}


def call(path, biz, secret):
    mp = dict(biz)
    kv = "&".join("%s=%s" % (k, mp[k]) for k in sorted(mp.keys()))
    mp["encode_sign"] = hashlib.md5((kv + secret).encode("utf-8")).hexdigest()
    ts = str(int(time.time()))
    plain = json.dumps(mp, ensure_ascii=False, separators=(",", ":")).encode()
    post = base64.b64encode(
        AES.new(REQ_KEY, AES.MODE_CBC, REQ_IV).encrypt(pad(plain, 16))).decode()
    body = json.dumps({"post-data": post, "timestamp": ts}).encode()
    req = urllib.request.Request(BASE + path, data=body, headers={
        "User-Agent": UA, "Content-Type": "application/json",
        "Accept": "application/json"}, method="POST")
    try:
        with OP.open(req, timeout=15) as r:
            return r.status, dec_resp(r.read())
    except urllib.error.HTTPError as e:
        try:
            return e.code, dec_resp(e.read())
        except Exception:
            return e.code, {"_err": "decode"}
    except Exception as e:
        return 0, {"_err": str(e)[:50]}


BIZ = [{"list_row": 120, "type": 4, "page": 1},
       {"list_row": 20, "type": 4, "page": 1},
       {"page": 1}]
for si, secret in enumerate(SECRETS):
    print("=" * 76)
    print("secret[%d] = %r" % (si, secret))
    for path in ("/video/list", "/video/listcache", "/video/channel"):
        for biz in BIZ:
            st, j = call(path, biz, secret)
            s = json.dumps(j, ensure_ascii=False)
            ok = isinstance(j, dict) and j.get("code") in (0, 200) and j.get("data")
            print("  %-18s %-40s -> %s %s%s" % (
                path, json.dumps(biz, separators=(",", ":"))[:40], st, s[:70],
                "  ★★★" if ok else ""))
            if ok:
                print("\n===== 成功 =====")
                print(json.dumps(j, ensure_ascii=False, indent=1)[:1200])
                open("tools/_dec/mdtv_ok.json", "w", encoding="utf-8").write(
                    json.dumps(j, ensure_ascii=False, indent=1))
                raise SystemExit(0)
