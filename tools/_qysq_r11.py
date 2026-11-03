# -*- coding: utf-8 -*-
"""qysq 第十一轮：补上「明文不是 JSON 而是压缩流」这一分支

前 10 轮的命中判据只看「明文像 JSON」，而 Dart 侧 `asGjCrypto` 返回后直接 `jsonDecode`，
说明最终明文确实是 JSON —— 但**中间层可能先压缩再加密**（zlib/gzip/brotli），
那样用正确 key/iv 解出来的就是压缩流（首字节 0x78/0x1f/…），会被"可打印率"判据直接丢掉。
本轮判据改为：解出后依次尝试 zlib / gzip / raw-deflate / brotli / 严格 JSON。
"""
import base64
import hashlib
import hmac
import itertools
import json
import time
import urllib.request
import uuid
import zlib

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


def unwrap(pt):
    """尝试把 pt 还原成 JSON 文本；成功返回文本，否则 None。"""
    if not pt:
        return None
    for fn in (lambda b: zlib.decompress(b),
               lambda b: zlib.decompress(b, -15),
               lambda b: zlib.decompress(b, 16 + 15)):
        try:
            t = fn(pt)
            s = t.decode("utf-8")
            if s.lstrip()[:1] in ("{", "["):
                json.loads(s)
                return s
        except Exception:
            pass
    try:
        s = pt.decode("utf-8")
        if s.lstrip()[:1] in ("{", "["):
            json.loads(s)
            return s
    except Exception:
        pass
    return None


def main():
    j = fetch()
    d = j["data"]
    D = base64.b64decode(d + "=" * (-len(d) % 4))
    print("[sample] code=%s bytes=%d %%16=%d" % (j.get("code"), len(D), len(D) % 16))

    mats = {"P": P}
    for cut in (0, 12, 16, 24, 32):
        for tag, body in (("P+D", P + D[:cut]), ("D+P", D[:cut] + P)):
            for hn, hf in (("s256", hashlib.sha256), ("s384", hashlib.sha384),
                           ("s512", hashlib.sha512), ("md5", hashlib.md5),
                           ("s1", hashlib.sha1)):
                mats["%s(%s%d)" % (hn, tag, cut)] = hf(body).digest()

    keys, ivs = {}, {"zero": b"\0" * 16, "D0": D[:16], "D12": D[12:28]}
    for mn, M in mats.items():
        for n in (16, 24, 32):
            if len(M) >= n:
                for i in range(0, len(M) - n + 1):
                    keys["%s[%d:%d]" % (mn, i, i + n)] = M[i:i + n]
        for i in range(0, max(1, len(M) - 15)):
            ivs["%s[%d:%d]" % (mn, i, i + 16)] = M[i:i + 16]

    print("[space] keys=%d ivs=%d" % (len(keys), len(ivs)))
    for skip in (12, 0, 16):
        ct = D[skip:]
        if len(ct) < 32 or len(ct) % 16:
            continue
        for (kn, k), (vn, iv) in itertools.product(keys.items(), ivs.items()):
            pt = AES.new(k, AES.MODE_CBC, iv).decrypt(ct)
            s = unwrap(pt)
            if s:
                print("\n★ 命中 skip=%d key=%s iv=%s" % (skip, kn, vn))
                print(s[:400])
                open("tools/_dec/qysq_plain.json", "w", encoding="utf-8").write(s)
                return
    print("\n未命中（含压缩分支）")


main()
