# -*- coding: utf-8 -*-
"""qysq 第六轮：宽口径爆破 asGjCrypto 的切片（用真实样本 tools/_dec/qysq_raw_sample.json 的同一接口重取）

上一轮只试了 CBC + 少量切片组合未命中。本轮：
  · 盐 P = "vEukA&w15z4VAD3kAY#fkL#rBnU!WDhN"（libapp.so @521089 原始字节实证）
  · H1 = sha256(P + D[:cut])   cut ∈ {0,12,16,24,32,48}
  · H2 = sha256(H1[a:b] + D[:cut2]) / sha256(D[:cut2] + H1[a:b])
  · key ∈ H1/H2 的 16/32 字节切片，iv ∈ 同族 16 字节切片（含全零）
  · 模式 ∈ CBC/CFB/OFB/CTR（172B 不是 16 的倍数，本身提示可能非 CBC）
判据：明文以 { 或 [ 开头且能 json 解析。
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


def fetch(path="api/app/media/home"):
    ts = int(time.time())
    nonce = str(uuid.uuid4())
    msg = "%s&/%s&%s&%s&%s" % (TOKEN, path, DEV_UA, ts, nonce)
    sign = hmac.new(SECRET.encode(), msg.encode(), hashlib.sha1).hexdigest()
    req = urllib.request.Request(
        BASE + "/" + path, data=b"{}", method="POST",
        headers={"X-User-Agent": DEV_UA, "user-agent": BR_UA,
                 "authorization": "Bearer " + TOKEN,
                 "x-api-key": "timestamp=%s;sign=%s;nonce=%s" % (ts, sign, nonce),
                 "Content-Type": "application/json"})
    with OP.open(req, timeout=20) as r:
        return json.loads(r.read().decode("utf-8", "replace"))


def slices(b, sizes=(16, 32)):
    out = {}
    for n in sizes:
        for i in range(0, max(1, len(b) - n + 1)):
            out["%s[%d:%d]" % ("H", i, i + n)] = b[i:i + n]
    return out


def ok(pt):
    if not pt:
        return False
    if pt[:1] not in (b"{", b"["):
        return False
    try:
        json.loads(pt.decode("utf-8"))
        return True
    except Exception:
        return pt[:1] in (b"{", b"[")


MODES = {
    "CBC": lambda k, iv: AES.new(k, AES.MODE_CBC, iv),
    "CFB": lambda k, iv: AES.new(k, AES.MODE_CFB, iv, segment_size=128),
    "OFB": lambda k, iv: AES.new(k, AES.MODE_OFB, iv),
    "CTR": lambda k, iv: AES.new(k, AES.MODE_CTR, nonce=b"", initial_value=int.from_bytes(iv, "big")),
}


def main():
    j = fetch()
    d = j.get("data")
    print("[envelope] code=%s" % j.get("code"))
    if not isinstance(d, str):
        print(json.dumps(j, ensure_ascii=False)[:300])
        return
    D = base64.b64decode(d + "=" * (-len(d) % 4))
    print("[bytes] %d  B  %%16=%d  head=%s" % (len(D), len(D) % 16, D[:16].hex()))

    hits = 0
    for cut in (0, 12, 16, 24, 32, 48):
        X = P + D[:cut]
        H1 = hashlib.sha256(X).digest()
        fams = {"H1": H1}
        for a in (0, 8, 16):
            for cut2 in (cut, 12, 16, 24):
                fams["H2(%d,%d)" % (a, cut2)] = hashlib.sha256(H1[a:a + 16] + D[:cut2]).digest()
                fams["H3(%d,%d)" % (a, cut2)] = hashlib.sha256(D[:cut2] + H1[a:a + 16]).digest()
        for fam, H in fams.items():
            keys = slices(H)
            ivs = dict(slices(H))
            ivs["zero"] = b"\0" * 16
            for (kn, k), (vn, iv) in itertools.product(keys.items(), ivs.items()):
                if len(k) not in (16, 24, 32):
                    continue
                for skip in (0, 12, 16, cut):
                    ct = D[skip:]
                    if not ct:
                        continue
                    for mn, mk in MODES.items():
                        if mn == "CBC" and len(ct) % 16:
                            continue
                        try:
                            pt = mk(k, iv).decrypt(ct)
                        except Exception:
                            continue
                        if ok(pt):
                            print("\n★ 命中 cut=%d fam=%s key=%s iv=%s skip=%d mode=%s"
                                  % (cut, fam, kn, vn, skip, mn))
                            print(pt[:500].decode("utf-8", "replace"))
                            open("tools/_dec/qysq_plain.json", "wb").write(pt)
                            hits += 1
                            return
    if not hits:
        print("\n仍未命中；样本长度 %d，可继续枚举 H 家族与 skip" % len(D))


main()
