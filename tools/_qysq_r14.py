# -*- coding: utf-8 -*-
"""qysq 第十四轮：基于 r13 的硬结论（摘要族是 sha384/sha512，不是 sha256）重建两段 KDF

r13 的判据很硬：把 asGjCrypto 的 341 条指令喂给状态机后，
  · sha256 → 3 处 sublist 越界（(8,48) / (8,48) / (12,40) 打在 32B 摘要上）
  · sha384 → 0 处越界
  · sha512 → 0 处越界
Dart 里越界必抛 RangeError，App 又确实能跑 ⇒ **摘要族只可能是 sha384/512**。
（池里那个 `_Sha256` 标签是误导，白啃了 12 轮。）

本轮按「两段 sha384/512 KDF」重建，切片边界直接用 asm 里出现过的那些：
  0,8,12,16,24,28,40,48,56,64
搜索空间压到几万组，命中判据是 AES 解出来的东西能严格 json.loads。
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
BOUNDS = (0, 8, 12, 16, 24, 28, 40, 48, 56, 64)


def fetch():
    path = "api/app/ping/config"
    ts = int(time.time())
    nonce = str(uuid.uuid4())
    msg = "%s&/%s&%s&%s&%s" % (TOKEN, path, DEV_UA, ts, nonce)
    sign = hmac.new(SECRET.encode(), msg.encode(), hashlib.sha1).hexdigest()
    req = urllib.request.Request(
        BASE + "/" + path,
        headers={"X-User-Agent": DEV_UA, "user-agent": BR_UA,
                 "authorization": "Bearer " + TOKEN,
                 "x-api-key": "timestamp=%s;sign=%s;nonce=%s" % (ts, sign, nonce)})
    with OP.open(req, timeout=25) as r:
        return json.loads(r.read().decode("utf-8", "replace"))


def ok(pt):
    try:
        txt = pt.decode("utf-8")
    except Exception:
        return None
    if txt.lstrip()[:1] not in ("{", "["):
        return None
    try:
        json.loads(txt)
        return txt
    except Exception:
        return None


def main():
    j = fetch()
    D = base64.b64decode(j["data"] + "=" * (-len(j["data"]) % 4))
    print("[sample] code=%s bytes=%d %%16=%d" % (j.get("code"), len(D), len(D) % 16))
    X = P + D[:24]

    for hn, hf in (("sha384", hashlib.sha384), ("sha512", hashlib.sha512)):
        H1 = hf(X).digest()
        # 第一段切片（asm 边界）
        k1s = {"H1[%d:%d]" % (a, b): H1[a:b] for a, b in itertools.combinations(BOUNDS, 2)
               if b <= len(H1)}
        # 第二段：把 K1 拼到 X / D 前面再哈希
        h2s = {}
        for kn, K1 in k1s.items():
            h2s["sha(%s+X)" % kn] = hf(K1 + X).digest()
            h2s["sha(%s+D24)" % kn] = hf(K1 + D[:24]).digest()
            h2s["sha(D24+%s)" % kn] = hf(D[:24] + K1).digest()
        mats = {"H1": H1}
        mats.update(h2s)

        keys, ivs = {}, {"zero": b"\0" * 16}
        for mn, M in mats.items():
            for a, b in itertools.combinations(BOUNDS, 2):
                if b <= len(M) and (b - a) in (16, 24, 32):
                    keys["%s[%d:%d]" % (mn, a, b)] = M[a:b]
                if b <= len(M) and (b - a) == 16:
                    ivs["%s[%d:%d]" % (mn, a, b)] = M[a:b]
        ct = D[12:]
        print("[%s] keys=%d ivs=%d ct=%d" % (hn, len(keys), len(ivs), len(ct)))
        for (kn, k), (vn, iv) in itertools.product(keys.items(), ivs.items()):
            pt = AES.new(k, AES.MODE_CBC, iv).decrypt(ct)
            txt = ok(pt)
            if txt:
                print("\n★ 命中 %s  key=%s  iv=%s" % (hn, kn, vn))
                print(txt[:300])
                open("tools/_dec/qysq_plain.json", "w", encoding="utf-8").write(txt)
                return
    print("\n两族仍未命中")


main()
