# -*- coding: utf-8 -*-
"""aijav 第二轮：找播放地址接口

aijav 列表项里**没有**媒体直链（只有 thumb/preview、play=播放数、private/video_point 购买标记），
客户端 Video VO 也只存 id/title/thumb —— 说明播放必须走一个"取流"接口。
asm 里只出现 4 个路径（video/lists、tag/lists、actor/lists、publisher/lists），
所以取流路径可能是拼接串。这里按语义枚举候选，逐个看错误码。
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
PUB = 44
ACTOR = 2440


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


print("%-22s %-40s %s" % ("路径", "biz", "结果"))
print("-" * 104)

CANDIDATES = [
    ("video/detail", {"id": VID}),
    ("video/info", {"id": VID}),
    ("video/one", {"id": VID}),
    ("video/view", {"id": VID}),
    ("video/play", {"id": VID}),
    ("video/plays", {"id": VID}),
    ("video/url", {"id": VID}),
    ("video/player", {"id": VID}),
    ("video/detail", {"video_id": VID}),
    ("video/play", {"video_id": VID}),
    ("video/lists", {"page": 1, "limit": 1, "id": VID}),
    ("publisher/detail", {"id": PUB}),
    ("actor/detail", {"id": ACTOR}),
]
for path, biz in CANDIDATES:
    j = call(path, biz)
    s = json.dumps(j, ensure_ascii=False)
    code = j.get("code")
    hit = isinstance(j, dict) and j.get("data") not in (None, {}, [], "") and code in (0, 1, 200)
    print("%-22s %-40s code=%-5s %s%s" % (path, json.dumps(biz), code, s[:110],
                                          "   ★" if hit else ""))
    if hit:
        open("tools/_dec/aijav_detail.json", "w", encoding="utf-8").write(
            json.dumps(j, ensure_ascii=False, indent=1))
