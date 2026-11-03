# -*- coding: utf-8 -*-
"""qysq 第八轮：换哈希族（sha384/sha512 让 asm 里的 48/40/28/20 这些切片边界全部合法）

推理依据（asGjCrypto @0x7237f0 的 sublist 边界）：
    D[0:24] / H[8:48] / H[0:16] / H[8:48] / H[12:40] / H[28:] / H[0:8] / D[12:]
    这些数字在 32 字节摘要上不合法（8:48 越界），在 **48 字节（sha384）或 64 字节（sha512）** 上全部合法。
    上一轮只用了 sha256，所以必然 0 命中。

本轮：哈希族 × 顺序 × cut × 切片 × 模式（含流模式，因为样本长度对不齐 16）全扫，
用「明文可打印率 + JSON 结构」打分，取最高分打印。
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
HASHES = {"sha256": hashlib.sha256, "sha384": hashlib.sha384, "sha512": hashlib.sha512}


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


def score(pt):
    if not pt:
        return -1.0
    head = pt[:200]
    printable = sum(1 for b in head if 9 <= b <= 13 or 32 <= b < 127 or b >= 0xC0)
    s = printable / len(head)
    try:
        txt = pt.decode("utf-8")
        if txt.lstrip()[:1] in ("{", "["):
            json.loads(txt)
            return 100.0
        for kw in ('"code"', '"msg"', '"data"'):
            if kw in txt:
                s += 1.0
    except Exception:
        pass
    return s


def main():
    j = fetch()
    D = base64.b64decode(j["data"] + "=" * (-len(j["data"]) % 4))
    print("[sample] code=%s  bytes=%d  %%16=%d" % (j.get("code"), len(D), len(D) % 16))

    results = []
    for hname, hfn in HASHES.items():
        for cut in (0, 12, 16, 24, 32):
            for order, data in (("P+D", P + D[:cut]), ("D+P", D[:cut] + P)):
                H = hfn(data).digest()
                keys = {}
                for n in (16, 24, 32):
                    for i in range(0, len(H) - n + 1):
                        keys["[%d:%d]" % (i, i + n)] = H[i:i + n]
                ivs = {"zero": b"\0" * 16}
                for i in range(0, len(H) - 15):
                    ivs["[%d:%d]" % (i, i + 16)] = H[i:i + 16]
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
                            s = score(pt)
                            if s >= 0.9:
                                results.append((s, "%s %s cut=%d skip=%d key=H%s iv=H%s"
                                                % (hname, order, cut, skip, kn, vn), pt))

    results.sort(key=lambda x: -x[0])
    print("候选数: %d" % len(results))
    for s, tag, pt in results[:6]:
        print("\n[%.2f] %s" % (s, tag))
        print("   ", pt[:200].decode("utf-8", "replace").replace("\n", " "))
    if results and results[0][0] >= 50:
        open("tools/_dec/qysq_plain.json", "wb").write(results[0][2])
        print("\n★ 已保存 tools/_dec/qysq_plain.json")


main()
