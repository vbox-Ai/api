# -*- coding: utf-8 -*-
"""mdtv 按 asm 实际参数测：video/listcache + {list_row, type, page}"""
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
SIGN_SECRET = "&NRkw0g3iJLDvw5tJ5PuVt5276z0SOuyL"
REQ_KEY = b"-p9B[~PnPsJGDZMX"
RESP_KEY = b"Vq234zBeSdGgYXzVTEfnnjjdmaTkk7A4"
RESP_IV_HEAD = b"-p9B[~PnPs"


def sign_of(mp):
    kv = "&".join("%s=%s" % (k, mp[k]) for k in sorted(mp.keys()))
    return hashlib.md5((kv + SIGN_SECRET).encode("utf-8")).hexdigest()


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
    p = AES.new(RESP_KEY, AES.MODE_CBC, iv).decrypt(raw)
    try:
        p = unpad(p, 16)
    except Exception:
        pass
    t = p.decode("utf-8", "replace")
    try:
        return json.loads(t)
    except Exception:
        return {"_plain": t[:200]}


def call(path, biz, req_iv=REQ_KEY):
    ts = str(int(time.time()))
    plain = json.dumps(biz, ensure_ascii=False, separators=(",", ":")).encode()
    post = base64.b64encode(
        AES.new(REQ_KEY, AES.MODE_CBC, req_iv).encrypt(pad(plain, 16))).decode()
    mp = {"post-data": post, "timestamp": ts}
    mp["encode_sign"] = sign_of(mp)
    req = urllib.request.Request(BASE + path,
                                 data=json.dumps(mp, ensure_ascii=False).encode(),
                                 headers={"User-Agent": UA,
                                          "Content-Type": "application/json",
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
        return 0, {"_err": str(e)[:60]}


BIZ = [
    {"list_row": 120, "type": 4, "page": 1},
    {"list_row": 120, "type": 4, "page": 1, "channel_id": 0},
    {"list_row": 20, "type": 4, "page": 1},
    {"list_row": 120, "type": 4, "page": 1, "key": ""},
    {"list_row": 120, "type": 1, "page": 1},
]
for path in ("/video/listcache", "/video/list", "/video/channel"):
    for biz in BIZ:
        st, j = call(path, biz)
        s = json.dumps(j, ensure_ascii=False)
        ok = isinstance(j, dict) and j.get("code") in (0, 200) and j.get("data")
        print("%-18s %-46s -> %s %s%s" % (
            path, json.dumps(biz, separators=(",", ":"))[:46], st, s[:80],
            "  ★★★" if ok else ""))
        if ok:
            print("\n===== 成功 =====")
            print(json.dumps(j, ensure_ascii=False, indent=1)[:1500])
            open("tools/_dec/mdtv_ok.json", "w", encoding="utf-8").write(
                json.dumps(j, ensure_ascii=False, indent=1))
            raise SystemExit(0)
