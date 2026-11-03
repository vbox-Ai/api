# -*- coding: utf-8 -*-
"""qysq 第十轮：按 asm 的两段式 KDF 精确建模（H2 的输入含「密文前缀/半段/整段」）

asGjCrypto 结构（0x723a34 / 0x723ac0 两处 Sha256）：
    H1 = sha256(P + D[0:24])
    K1 = H1[8:24]
    H2 = sha256(K1 + D[a:b])        a∈{0,12,24, 半段}, b∈{半段, 整段}
    key = ?  iv = ?  ct = D[12:]

本轮把 (a,b) 的候选取自 asm 里出现过的边界（0/12/24/len/2/len），
key/iv 在 H1、H2 的所有 16 字节窗口里组合，模式 CBC/CFB。
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


def fetch(path="api/app/ping/config", method="GET"):
    ts = int(time.time())
    nonce = str(uuid.uuid4())
    msg = "%s&/%s&%s&%s&%s" % (TOKEN, path, DEV_UA, ts, nonce)
    sign = hmac.new(SECRET.encode(), msg.encode(), hashlib.sha1).hexdigest()
    req = urllib.request.Request(
        BASE + "/" + path, data=None if method == "GET" else b"{}", method=method,
        headers={"X-User-Agent": DEV_UA, "user-agent": BR_UA,
                 "authorization": "Bearer " + TOKEN,
                 "x-api-key": "timestamp=%s;sign=%s;nonce=%s" % (ts, sign, nonce),
                 "Content-Type": "application/json"})
    with OP.open(req, timeout=25) as r:
        return json.loads(r.read().decode("utf-8", "replace"))


def main():
    j = fetch()
    D = base64.b64decode(j["data"] + "=" * (-len(j["data"]) % 4))
    n = len(D)
    print("[sample] code=%s bytes=%d %%16=%d" % (j.get("code"), n, n % 16))

    H1 = hashlib.sha256(P + D[:24]).digest()
    K1 = H1[8:24]
    bounds = sorted({0, 12, 16, 24, n // 2, n // 2 * 2, n})
    found = 0
    for a, b in itertools.product(bounds, bounds):
        if a >= b or b > n:
            continue
        for hname, H2 in (("H2(K1+D[%d:%d])" % (a, b), hashlib.sha256(K1 + D[a:b]).digest()),
                          ("H2(D[%d:%d]+K1)" % (a, b), hashlib.sha256(D[a:b] + K1).digest())):
            mats = [("H1", H1), (hname, H2)]
            keys, ivs = {}, {}
            for mn, M in mats:
                for i in range(0, len(M) - 15):
                    ivs["%s[%d:]" % (mn, i)] = M[i:i + 16]
                    keys["%s[%d:%d]" % (mn, i, i + 16)] = M[i:i + 16]
                keys["%s" % mn] = M            # 32B → AES-256
            ivs["zero"] = b"\0" * 16
            for skip in (0, 12, 16, 24):
                ct = D[skip:]
                if len(ct) < 32:
                    continue
                for (kn, k), (vn, iv) in itertools.product(keys.items(), ivs.items()):
                    for mn2 in ("CBC", "CFB"):
                        if mn2 == "CBC" and len(ct) % 16:
                            continue
                        try:
                            if mn2 == "CBC":
                                pt = AES.new(k, AES.MODE_CBC, iv).decrypt(ct)
                            else:
                                pt = AES.new(k, AES.MODE_CFB, iv, segment_size=128).decrypt(ct)
                        except Exception:
                            continue
                        try:
                            txt = pt.decode("utf-8")
                        except Exception:
                            continue
                        if txt.lstrip()[:1] not in ("{", "["):
                            continue
                        try:
                            json.loads(txt)
                        except Exception:
                            continue
                        print("\n★ 命中 %s skip=%d mode=%s key=%s iv=%s" % (hname, skip, mn2, kn, vn))
                        print(txt[:400])
                        open("tools/_dec/qysq_plain.json", "w", encoding="utf-8").write(txt)
                        found += 1
                        return
    print("\n未命中（边界组合 %d 个已扫完）" % (len(bounds) ** 2))


main()
