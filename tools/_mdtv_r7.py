# -*- coding: utf-8 -*-
"""mdtv 第四轮：timestamp 改毫秒（asm 确认），并试 json 转义两种"""
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
REQ_KEY = b"Vq234zBeSdGgYXzVTEfnnjjdmaTkk7A4"
REQ_IV = b"-p9B[~PnPsJGDZMX"
SECRET = "&m}q%ea6:LDcmS\\?aK)CeF287bPvd99@E,9Up^"
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
    p = AES.new(REQ_KEY, AES.MODE_CBC, iv).decrypt(raw)
    try:
        p = unpad(p, 16)
    except Exception:
        pass
    t = p.decode("utf-8", "replace")
    try:
        return json.loads(t)
    except Exception:
        return {"_plain": t[:200]}


def call(path, biz, ms=True, ascii_mode=True, body_mode="post_only"):
    mp = dict(biz)
    ts = int(time.time() * 1000) if ms else int(time.time())
    mp["timestamp"] = ts
    joined = "&".join("%s=%s" % (k, mp[k]) for k in sorted(mp.keys()))
    mp["encode_sign"] = hashlib.md5((joined + SECRET).encode("utf-8")).hexdigest()

    plain = json.dumps(mp, ensure_ascii=ascii_mode,
                       separators=(",", ":")).encode("utf-8")
    post = base64.b64encode(
        AES.new(REQ_KEY, AES.MODE_CBC, REQ_IV).encrypt(pad(plain, 16))).decode()
    if body_mode == "post_only":
        out = {"post-data": post}
    elif body_mode == "post_ts":
        out = {"post-data": post, "timestamp": ts}
    else:
        out = {"post-data": post, "timestamp": ts, "encode_sign": mp["encode_sign"]}
    req = urllib.request.Request(BASE + path, data=json.dumps(out).encode(),
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
        return 0, {"_err": str(e)[:40]}


BIZ = {"page": 1, "list_row": 120, "type": 4, "channel": 1}

print("%-10s %-9s %-12s %-16s %s" % ("ts单位", "ascii", "body", "路径", "结果"))
print("-" * 100)
hit = None
for ms in (True, False):
    for am in (True, False):
        for bm in ("post_only", "post_ts", "post_both"):
            for path in ("/video/listcache", "/video/list"):
                st, j = call(path, BIZ, ms, am, bm)
                s = json.dumps(j, ensure_ascii=False)
                ok = isinstance(j, dict) and j.get("code") in (0, 200) and j.get("data")
                print("%-10s %-9s %-12s %-16s %s%s" % (
                    "毫秒" if ms else "秒", am, bm, path, s[:80],
                    "  ★★★" if ok else ""))
                if ok:
                    hit = (path, j)
                    break
            if hit:
                break
        if hit:
            break
    if hit:
        break

if hit:
    print("\n===== 成功 %s =====" % hit[0])
    print(json.dumps(hit[1], ensure_ascii=False, indent=1)[:1800])
    open("tools/_dec/mdtv_ok.json", "w", encoding="utf-8").write(
        json.dumps(hit[1], ensure_ascii=False, indent=1))
