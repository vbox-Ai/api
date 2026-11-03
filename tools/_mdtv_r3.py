# -*- coding: utf-8 -*-
"""mdtv：完整请求（签名字段 post-data/encode_sign/timestamp + 正确参数）"""
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
REQ_KEY = b"-p9B[~PnPsJGDZMX"          # 16 -> AES-128
REQ_IV = b"-p9B[~PnPsJGDZMX"           # 先用同值
RESP_KEY = b"Vq234zBeSdGgYXzVTEfnnjjdmaTkk7A4"   # 32 -> AES-256
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


def call(path, biz, iv=None):
    iv = iv or REQ_IV
    ts = str(int(time.time()))
    plain = json.dumps(biz, ensure_ascii=False, separators=(",", ":")).encode()
    post_data = base64.b64encode(
        AES.new(REQ_KEY, AES.MODE_CBC, iv).encrypt(pad(plain, 16))).decode()
    mp = {"post-data": post_data, "timestamp": ts}
    mp["encode_sign"] = sign_of(mp)
    body = json.dumps(mp, ensure_ascii=False).encode()
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
        return 0, {"_err": str(e)[:60]}


IVS = [("reqkey", REQ_KEY), ("zero", b"\x00" * 16),
       ("resp[:16]", RESP_KEY[:16]), ("-p9B[~PnPs+pad", b"-p9B[~PnPs".ljust(16, b"\x00"))]
BIZ = [{"page": 1, "limit": 20}, {"page": 1, "pageSize": 20}, {"page": 1},
       {"channel_id": 1, "page": 1}, {"cid": 1, "page": 1}]

print("%-14s %-28s %-14s %-6s %s" % ("路径", "参数", "iv", "状态", "解密结果"))
print("-" * 104)
hit = None
for path in ("/video/list", "/video/channel", "/video/tags"):
    for biz in BIZ:
        for ivn, iv in IVS:
            st, j = call(path, biz, iv)
            s = json.dumps(j, ensure_ascii=False)[:70]
            ok = isinstance(j, dict) and j.get("code") in (0, 200) and j.get("data")
            print("%-14s %-28s %-14s %-6s %s%s" % (
                path, json.dumps(biz, separators=(",", ":"))[:28], ivn, st, s,
                "  ★" if ok else ""))
            if ok:
                hit = (path, biz, ivn, j)
                break
        if hit:
            break
    if hit:
        break

if hit:
    path, biz, ivn, j = hit
    print("\n★★★ 成功 %s  biz=%s  iv=%s" % (path, json.dumps(biz), ivn))
    print(json.dumps(j, ensure_ascii=False, indent=1)[:1200])
    open("tools/_dec/mdtv_ok.json", "w", encoding="utf-8").write(
        json.dumps(j, ensure_ascii=False, indent=1))
else:
    print("\n全部仍报参数/签名错误")
