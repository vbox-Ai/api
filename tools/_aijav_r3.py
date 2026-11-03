# -*- coding: utf-8 -*-
"""aijav 第三轮：video/info 是真实接口（返回业务码 3001 而非 999 网络异常），
枚举它的参数名 —— 先空参看服务端是否自己报出必填字段名。
"""
import base64
import hashlib
import json
import time
import urllib.error
import urllib.request

from Crypto.Cipher import AES
from Crypto.Util.Padding import pad, unpad

BASE = "https://newavapi.9xyrp3kg4b86.com/"
KEY = b"0XxdjmI55ZjjqQLO3nI7gGqrBP0Vz9jS"
REQ_IV = b"RWf23muavYNWSdef"
SECRET = "&NRkw0g3iJLDvw5tJ5PuVt5276z0SOuyL"
RESP_IV_HEAD = "RWf23muavY"
SUFFIX = "NWSdef"
UA = "Dart/3.4 (dart:io)"
OP = urllib.request.build_opener(urllib.request.ProxyHandler({}))
VID = 15477
MASH = "CAWD-568"


def dec_resp(raw_body):
    j = json.loads(raw_body.decode("utf-8", "replace"))
    if not isinstance(j, dict) or not isinstance(j.get("data"), str):
        return j
    d, suf = j["data"], str(j.get("suffix") or "")
    raw = base64.b64decode(d + "=" * (-len(d) % 4))
    iv = (RESP_IV_HEAD + suf).ljust(16, "\0")[:16].encode()
    if len(raw) % 16:
        return {"_err": "mod16=%d" % (len(raw) % 16)}
    p = AES.new(KEY, AES.MODE_CBC, iv).decrypt(raw)
    try:
        p = unpad(p, 16)
    except Exception:
        pass
    t = p.decode("utf-8", "replace")
    try:
        return json.loads(t)
    except Exception:
        return {"_plain": t[:200]}


def call(path, biz=None):
    mp = dict(biz or {})
    mp["timestamp"] = int(time.time() * 1000)
    joined = "&".join("%s=%s" % (k, mp[k]) for k in sorted(mp.keys()))
    mp["encode_sign"] = hashlib.md5((joined + SECRET).encode()).hexdigest()
    plain = json.dumps(mp, ensure_ascii=False, separators=(",", ":")).encode()
    ct = AES.new(KEY, AES.MODE_CBC, REQ_IV).encrypt(pad(plain, 16))
    body = json.dumps({"post-data": base64.b64encode(ct).decode()}).encode()
    req = urllib.request.Request(
        BASE + path.lstrip("/"), data=body, method="POST",
        headers={"Content-Type": "application/json", "suffix": SUFFIX,
                 "User-Agent": UA})
    try:
        with OP.open(req, timeout=15) as r:
            return dec_resp(r.read())
    except urllib.error.HTTPError as e:
        try:
            return dec_resp(e.read())
        except Exception:
            return {"_http": e.code}
    except Exception as e:
        return {"_err": str(e)[:50]}


print("== 空参试探（看服务端是否报必填字段名）==")
print(json.dumps(call("video/info", {}), ensure_ascii=False)[:300])

print("\n%-34s %-8s %s" % ("biz", "code", "msg/摘要"))
print("-" * 96)
TRIES = [
    {"id": VID}, {"video_id": VID}, {"vid": VID}, {"ids": VID},
    {"code": MASH}, {"mash": MASH}, {"number": MASH},
    {"code": VID}, {"id": str(VID)},
    {"id": VID, "code": MASH},
]
for biz in TRIES:
    j = call("video/info", biz)
    s = json.dumps(j, ensure_ascii=False)
    code = j.get("code")
    print("%-34s %-8s %s" % (json.dumps(biz), code, s[:130]))
    if code in (0, 1, 200) and j.get("data"):
        print("\n★ 命中 video/info")
        print(json.dumps(j, ensure_ascii=False, indent=1)[:2000])
        open("tools/_dec/aijav_info.json", "w", encoding="utf-8").write(
            json.dumps(j, ensure_ascii=False, indent=1))
        break
