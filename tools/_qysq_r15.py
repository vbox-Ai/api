# -*- coding: utf-8 -*-
"""qysq 第十五轮：按「Smi 混合」假设，用解释器实测到的真实摘要值拼 key/iv

r13 跑出的真实链条（sha256 族，样本 D 全量已就位）：
    X  = 盐(32B) + D[0:24]                       = 56B   ← sublist(D,0,24) 中 24 是真实值
    H1 = sha256(X)                               = 3814d7fc…
    K1 = H1[8:24]（asm 里印成 8:48 → 48 是 Smi，真实 24）
    L2 = K1 + X（asm 印成 0:112 → 112 是 Smi，真实 56 = 整个 X）
    H2 = sha256(L2)
    H3 = sha256(K1)
    key = H2[0:16] + H3[8:24]（asm 印成 8:48 / 24:32，按 Smi 折算）
    iv  = H3[0:8] + H2[12:20]（asm 印成 0:16 / 12:40）

本轮把这套「按 Smi 折算后的切片」穷举一遍，用 AES 真解 + 严格 JSON 判据收口。
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
        t = pt.decode("utf-8")
    except Exception:
        return None
    if t.lstrip()[:1] in ("{", "["):
        try:
            json.loads(t)
            return t
        except Exception:
            return None
    return None


def main():
    j = fetch()
    D = base64.b64decode(j["data"] + "=" * (-len(j["data"]) % 4))
    ct = D[12:]
    print("[sample] code=%s D=%d ct=%d" % (j.get("code"), len(D), len(ct)))
    X = P + D[:24]

    H1 = hashlib.sha256(X).digest()
    K1s = {"H1[8:24]": H1[8:24], "H1[8:32]": H1[8:32],
           "H1[0:16]": H1[0:16], "H1[16:32]": H1[16:32]}
    variants = {}
    for kn, K1 in K1s.items():
        for order, L2 in (("%s+X" % kn, K1 + X), ("X+%s" % kn, X + K1)):
            H2 = hashlib.sha256(L2).digest()
            H3 = hashlib.sha256(K1).digest()
            variants[order] = (H2, H3, H1)

    found = 0
    for name, (H2, H3, H1_) in variants.items():
        keys = {}
        for a, b in itertools.combinations(range(0, 33, 4), 2):
            if b <= 32 and (b - a) in (16, 24, 32):
                keys["H2[%d:%d]" % (a, b)] = H2[a:b]
                keys["H3[%d:%d]" % (a, b)] = H3[a:b]
                keys["H1[%d:%d]" % (a, b)] = H1_[a:b]
        # 两段拼接的 key（16+16 / 16+16+... ）
        for a, b in ((0, 16), (8, 24), (16, 32)):
            for c, d in ((0, 16), (8, 24), (16, 32)):
                keys["H2[%d:%d]+H3[%d:%d]" % (a, b, c, d)] = H2[a:b] + H3[c:d]
        ivs = {"zero": b"\0" * 16}
        for a in range(0, 17, 4):
            if a + 16 <= 32:
                ivs["H2[%d:]" % a] = H2[a:a + 16]
                ivs["H3[%d:]" % a] = H3[a:a + 16]
                ivs["H1[%d:]" % a] = H1_[a:a + 16]
        for a, b in ((0, 8), (8, 16), (12, 20)):
            for c, d in ((0, 8), (8, 16), (16, 24)):
                if (b - a) + (d - c) == 16:
                    ivs["H3[%d:%d]+H2[%d:%d]" % (a, b, c, d)] = H3[a:b] + H2[c:d]
                    ivs["H2[%d:%d]+H3[%d:%d]" % (a, b, c, d)] = H2[a:b] + H3[c:d]

        print("[%s] keys=%d ivs=%d" % (name, len(keys), len(ivs)))
        for (kn, k), (vn, iv) in itertools.product(keys.items(), ivs.items()):
            if len(k) not in (16, 24, 32) or len(iv) != 16:
                continue
            txt = ok(AES.new(k, AES.MODE_CBC, iv).decrypt(ct))
            if txt:
                print("\n★ 命中  variant=%s key=%s iv=%s" % (name, kn, vn))
                print(txt[:300])
                open("tools/_dec/qysq_plain.json", "w", encoding="utf-8").write(txt)
                found += 1
                return
    if not found:
        print("\n未命中")


main()
