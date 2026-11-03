# -*- coding: utf-8 -*-
"""qysq 第九轮：把「盐 P 直接当 key/iv」这一族也扫掉（前几轮只扫了哈希派生）

覆盖：
  key ∈ { P[0:16], P[16:32], P(32B), hash*(P), hash*(P+D), hash*(D+P), hash*(D[:12]+P) 的 16/24/32 切片 }
  iv  ∈ { zero, P[0:16], D[0:16], D[12:28], 同族哈希切片 }
  skip ∈ { 0, 12, 16, 24 }，模式 ∈ CBC/CFB/OFB/CTR
判据：严格 JSON 解析（不再用"像 {"就收）。
"""
import base64
import hashlib
import hmac
import itertools
import json
import time
import urllib.request
import uuid

from Crypto.Cipher import AES

BASE = "https://d1kmvkv4iwtiup.cloudfront.net"
SECRET = "gH3nA7fR9tV1jY6z"
DEV_UA = "DevType=Apple iPhone mobile;SysType=light;Ver=2.1.2;BuildID=Mobile Safari 18.5"
BR_UA = ("Mozilla/5.0 (iPhone; CPU iPhone OS 18_5 like Mac OS X) AppleWebKit/605.1.15 "
         "(KHTML, like Gecko) Version/18.5 Mobile/15E148 Safari/604.1")
P = b"vEukA&w15z4VAD3kAY#fkL#rBnU!WDhN"
OP = urllib.request.build_opener(urllib.request.ProxyHandler({}))
TOKEN = ("eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJhdWQiOiJwdWJsaWMiLCJleHAiOjE3OTM4NTgxNjIs"
         "Imlzc3VlciI6ImNvbS5idXR0ZXJmbHkiLCJzdWIiOiJhc2lnbiIsInVzZXJJZCI6NTY3NzU4MX0."
         "yjzuUUUK1hlQBzlTQ703ZYemCvfL97EYsQNUCyEVET4")


def fetch(path="api/app/media/home", body=b"{}"):
    ts = int(time.time())
    nonce = str(uuid.uuid4())
    msg = "%s&/%s&%s&%s&%s" % (TOKEN, path, DEV_UA, ts, nonce)
    sign = hmac.new(SECRET.encode(), msg.encode(), hashlib.sha1).hexdigest()
    req = urllib.request.Request(
        BASE + "/" + path, data=body, method="POST",
        headers={"X-User-Agent": DEV_UA, "user-agent": BR_UA,
                 "authorization": "Bearer " + TOKEN,
                 "x-api-key": "timestamp=%s;sign=%s;nonce=%s" % (ts, sign, nonce),
                 "Content-Type": "application/json"})
    with OP.open(req, timeout=20) as r:
        return json.loads(r.read().decode("utf-8", "replace"))


def main():
    j = fetch()
    D = base64.b64decode(j["data"] + "=" * (-len(j["data"]) % 4))
    print("[sample] bytes=%d %%16=%d" % (len(D), len(D) % 16))

    mats = {
        "P": P,
        "sha256(P)": hashlib.sha256(P).digest(),
        "sha384(P)": hashlib.sha384(P).digest(),
        "sha512(P)": hashlib.sha512(P).digest(),
        "md5(P)": hashlib.md5(P).digest(),
    }
    for cut in (12, 16, 24):
        for tag, body in (("P+D", P + D[:cut]), ("D+P", D[:cut] + P)):
            for hn, hf in (("sha256", hashlib.sha256), ("sha384", hashlib.sha384),
                           ("sha512", hashlib.sha512), ("md5", hashlib.md5)):
                mats["%s(%s%d)" % (hn, tag, cut)] = hf(body).digest()

    keys, ivs = {}, {"zero": b"\0" * 16, "P0": P[:16], "D0": D[:16], "D12": D[12:28]}
    for mn, M in mats.items():
        for n in (16, 24, 32):
            if len(M) >= n:
                keys["%s[:%d]" % (mn, n)] = M[:n]
                keys["%s[-%d:]" % (mn, n)] = M[-n:]
                for i in range(0, len(M) - n + 1):
                    keys["%s[%d:%d]" % (mn, i, i + n)] = M[i:i + n]
        if len(M) >= 16:
            for i in range(0, len(M) - 15):
                ivs["%s[%d:%d]" % (mn, i, i + 16)] = M[i:i + 16]

    print("[space] keys=%d ivs=%d" % (len(keys), len(ivs)))
    hits = 0
    for skip in (0, 12, 16, 24):
        ct = D[skip:]
        if len(ct) < 32:
            continue
        for (kn, k), (vn, iv) in itertools.product(keys.items(), ivs.items()):
            for mn in ("CBC", "CFB", "OFB"):
                if mn == "CBC" and len(ct) % 16:
                    continue
                try:
                    if mn == "CBC":
                        pt = AES.new(k, AES.MODE_CBC, iv).decrypt(ct)
                    elif mn == "CFB":
                        pt = AES.new(k, AES.MODE_CFB, iv, segment_size=128).decrypt(ct)
                    else:
                        pt = AES.new(k, AES.MODE_OFB, iv).decrypt(ct)
                except Exception:
                    continue
                txt = None
                try:
                    txt = pt.decode("utf-8")
                except Exception:
                    continue
                if txt.lstrip()[:1] in ("{", "["):
                    try:
                        json.loads(txt)
                    except Exception:
                        continue
                    print("\n★ 命中 skip=%d mode=%s key=%s iv=%s" % (skip, mn, kn, vn))
                    print(txt[:400])
                    open("tools/_dec/qysq_plain.json", "w", encoding="utf-8").write(txt)
                    hits += 1
                    return
    print("\n仍未命中（keys=%d ivs=%d 全扫完）" % (len(keys), len(ivs)))


main()
