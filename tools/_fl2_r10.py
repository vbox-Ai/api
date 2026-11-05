# -*- coding: utf-8 -*-
"""fl2 第八轮：媒体 token

`/media/**.m3u8` 直取（不带 token）恒返 498「Token 格式錯誤」；
带 `?token=<register token>` 时返回的不是密文（之前 dec-fail）—— 但那是旧 URL（已 404）。

本轮：register → v1/video/info 拿**新鲜** video_urls → 试 3 种带 token 的取法：
  A. ?token=<tok>
  B. ?token=<tok> + Authorization: Bearer <tok>
  C. 只用 URL 自带 expire/hash（不带 token）—— 对照
判据：body 以 #EXTM3U 开头（明文）或能解出文本。
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
from Crypto.Util.Padding import pad, unpad

REQ_KEY = base64.b64decode("euZN1Gg3JIwWOEWhmE7C4l5dSSRU34fyuPMXjtuoqVs=")
RESP_KEY = b"db6f7f9e5d7a770e0e3497a7d7a077f5"
XINFO = ("eyJjcGFnZSI6ImxhdW5jaCIsInBsYXRmb3JtIjoyLCJwcGFnZSI6IiIsInZlcnNpb24iOiIy"
         "LjQwIn0=")
UA = "Fulao2/Android 2.40; Xiaomi MI 14"
OP = urllib.request.build_opener(urllib.request.ProxyHandler({}))
HOST = "https://prja.website"


def envelope(mp):
    iv = uuid.uuid4().bytes[:16]
    body = json.dumps(mp, ensure_ascii=False, separators=(",", ":")).encode()
    ct = AES.new(REQ_KEY, AES.MODE_CBC, iv).encrypt(pad(body, 16))
    return base64.b64encode(iv).decode() + "." + base64.b64encode(ct).decode()


def dec(raw, vtag):
    h = hashlib.md5((vtag or "").encode()).hexdigest()
    txt = raw.decode("utf-8", "replace").strip()
    if txt.lstrip()[:1] in ("{", "["):
        return txt
    try:
        pt = AES.new(RESP_KEY, AES.MODE_CBC, h[8:24].encode()).decrypt(
            base64.b64decode(txt + "=" * (-len(txt) % 4)))
        try:
            pt = unpad(pt, 16)
        except Exception:
            pass
        return pt.decode("utf-8", "replace")
    except Exception as e:
        return "dec-fail:%s" % e


def call(path, method="GET", params=None, token="", dev=""):
    mp = dict(params or {})
    mp["path"] = path
    mp["timestamp"] = int(time.time())
    payload = envelope(mp)
    headers = {"User-Agent": UA, "X-Info": XINFO, "Uuid": dev, "Accept": "application/json"}
    if token:
        headers["Authorization"] = "Bearer " + token
    url = HOST + "/" + path.lstrip("/")
    if method == "GET":
        q = dict(params or {})
        q["payload"] = payload
        url += "?" + urllib.parse.urlencode(q)
        req = urllib.request.Request(url, headers=headers)
    else:
        headers["Content-Type"] = "application/x-www-form-urlencoded"
        body = {"payload": payload}
        body.update({str(k): str(v) for k, v in (params or {}).items()})
        req = urllib.request.Request(url, data=urllib.parse.urlencode(body).encode(),
                                     method="POST", headers=headers)
    try:
        with OP.open(req, timeout=20) as r:
            return r.status, dict(r.headers), r.read()
    except urllib.error.HTTPError as e:
        try:
            return e.code, dict(e.headers or {}), e.read()
        except Exception:
            return e.code, {}, b""
    except Exception as e:
        return 0, {}, str(e)[:60].encode()


def register(dev):
    ts = int(time.time())
    mp = {"device_id": dev,
          "key": hashlib.sha256(("jav" + dev + "jav").encode()).hexdigest(),
          "utm_medium": "", "model": "Xiaomi MI 14",
          "universal_id": base64.b64encode(dev.encode()).decode(),
          "platform": "Android", "path": "v1/register/token", "timestamp": ts}
    body = urllib.parse.urlencode({"payload": envelope(mp)}).encode()
    req = urllib.request.Request(
        HOST + "/v1/register/token", data=body, method="POST",
        headers={"User-Agent": UA, "X-Info": XINFO, "Uuid": dev,
                 "Content-Type": "application/x-www-form-urlencoded"})
    with OP.open(req, timeout=20) as r:
        j = json.loads(dec(r.read(), r.headers.get("X-VTag", "")))
    return j["response"]["token"]


def fetch(url, headers):
    try:
        r = OP.open(urllib.request.Request(url, headers=headers), timeout=15)
        return r.status, dict(r.headers), r.read()
    except urllib.error.HTTPError as e:
        try:
            return e.code, dict(e.headers or {}), e.read()
        except Exception:
            return e.code, {}, b""
    except Exception as e:
        return 0, {}, str(e)[:60].encode()


if __name__ == "__main__":
    dev = str(uuid.uuid4())
    tok = register(dev)
    print("[token] %d chars" % len(tok))
    st, h, raw = call("v1/video/info/524937", "GET", None, tok, dev)
    d = json.loads(dec(raw, h.get("X-VTag", "")))["response"]
    urls = d.get("video_urls") or {}
    print("[video_urls]", json.dumps(urls, ensure_ascii=False))
    rel = urls.get("480") or urls.get("240") or ""
    full = HOST + rel
    q = dict(urllib.parse.parse_qsl(urllib.parse.urlparse(full).query))
    print("[query]", q)

    tests = [
        ("裸取", full, {"User-Agent": UA}),
        ("+token query", full + "&token=" + urllib.parse.quote(tok), {"User-Agent": UA}),
        ("+token query +Bearer", full + "&token=" + urllib.parse.quote(tok),
         {"User-Agent": UA, "Authorization": "Bearer " + tok}),
        ("+Bearer only", full, {"User-Agent": UA, "Authorization": "Bearer " + tok}),
    ]
    for name, u, hd in tests:
        st, hh, body = fetch(u, hd)
        head = body[:60]
        plain = body.startswith(b"#EXTM3U")
        print("\n%-22s HTTP %-4s len=%-6d extm3u=%s  head=%r" % (name, st, len(body), plain, head))
        if plain or (b"EXTM3U" in body[:200]):
            open("tools/_dec/fl2_playlist.m3u8", "wb").write(body)
            print("   ★ 拿到明文 m3u8，已存 tools/_dec/fl2_playlist.m3u8")
            print(body[:400].decode("utf-8", "replace"))
            break
        else:
            print("   decrypted:", dec(body, hh.get("X-VTag", ""))[:160].replace("\n", " "))
