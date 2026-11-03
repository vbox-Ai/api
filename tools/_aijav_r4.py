# -*- coding: utf-8 -*-
"""aijav 第四轮：暴力枚举取流路径

已确认：
  · 路由不存在 → {"code":999,"msg":"网络异常，请稍候再试"}
  · 路由存在但业务不对 → 业务码（3001 视频不存在 / 1 成功）
所以「code != 999」就是路由存在的信号。用这个判据扫候选路径。
参数统一带 {vid: 15477}（video/info 实证的键名）+ {id: 15477} 双发。
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


def dec_resp(raw_body):
    try:
        j = json.loads(raw_body.decode("utf-8", "replace"))
    except Exception:
        return {"_raw": raw_body[:120].decode("utf-8", "replace")}
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


def call(path, biz):
    mp = dict(biz)
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
        with OP.open(req, timeout=12) as r:
            return dec_resp(r.read())
    except urllib.error.HTTPError as e:
        try:
            return dec_resp(e.read())
        except Exception:
            return {"_http": e.code}
    except Exception as e:
        return {"_err": str(e)[:40]}


SEG2 = ["play", "plays", "playurl", "play_url", "getplay", "getPlayUrl", "url", "urls",
        "m3u8", "source", "sources", "src", "stream", "video", "detail", "info",
        "get", "one", "view", "unlock", "buy", "purchase", "order", "point", "points",
        "related", "recommend", "reviews", "comments", "collect", "like", "download"]
PREFIX = ["video", "player", "media", "play", "vod", "app/video"]

print("%-26s %-8s %s" % ("路径", "code", "摘要"))
print("-" * 100)
found = []
for pre in PREFIX:
    for seg in SEG2:
        path = "%s/%s" % (pre, seg)
        j = call(path, {"vid": VID})
        code = j.get("code")
        if code == 999:
            continue
        s = json.dumps(j, ensure_ascii=False)
        print("%-26s %-8s %s" % (path, code, s[:120]))
        found.append((path, code, s[:400]))

print("\n非 999 的路径共 %d 个" % len(found))
open("tools/_dec/aijav_route_scan.json", "w", encoding="utf-8").write(
    json.dumps(found, ensure_ascii=False, indent=1))
