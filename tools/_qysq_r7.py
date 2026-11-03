# -*- coding: utf-8 -*-
"""qysq 第七轮：宽口径扫描 + 打分排序（不再"首个像 { 就收"）

上一轮的教训：`pt[:1] == b"{"` 会命中随机噪声。本轮改成分数制：
  score = 可打印字符占比 + 出现 "code"/"data"/"msg" 加分 + JSON 严格解析一次性加分
取分数最高的前 8 个打印，人工判断是否收敛。
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


def score(pt):
    if not pt:
        return -1
    printable = sum(1 for b in pt[:256] if 9 <= b <= 13 or 32 <= b < 127)
    s = printable / min(len(pt), 256)
    try:
        txt = pt.decode("utf-8")
        if txt.lstrip()[:1] in ("{", "["):
            json.loads(txt)
            return 100
        if txt.lstrip()[:1] in ("{", "["):
            s += 5
        for kw in ("code", "data", "msg", "list", "total"):
            if '"%s"' % kw in txt:
                s += 2
    except Exception:
        if pt[:2] in (b"\x1f\x8b", b"x\x9c"):
            s += 4
    return s


def main():
    j = fetch()
    d = j.get("data")
    D = base64.b64decode(d + "=" * (-len(d) % 4))
    print("[bytes] %d  %%16=%d" % (len(D), len(D) % 16))

    results = []
    prefixes = {
        "P": P,
        "D12": D[:12],
        "D16": D[:16],
        "D24": D[:24],
        "D32": D[:32],
    }
    hashes = {}
    for name, body in prefixes.items():
        for order, data in (("PD", P + body), ("DP", body + P)):
            hashes["sha256(%s%s)" % (order, name)] = hashlib.sha256(data).digest()
            hashes["md5(%s%s)" % (order, name)] = hashlib.md5(data).digest()
            hashes["sha512(%s%s)" % (order, name)] = hashlib.sha512(data).digest()
    # 二次派生
    base_items = list(hashes.items())
    for name, H in base_items:
        for a in (0, 8, 16):
            hashes["%s^sha256(H[%d:%d]+D12)" % (name, a, a + 16)] = \
                hashlib.sha256(H[a:a + 16] + D[:12]).digest()
            hashes["%s^sha256(H[%d:%d]+D24)" % (name, a, a + 16)] = \
                hashlib.sha256(H[a:a + 16] + D[:24]).digest()

    modes = {
        "CBC": lambda k, iv: AES.new(k, AES.MODE_CBC, iv),
        "CFB": lambda k, iv: AES.new(k, AES.MODE_CFB, iv, segment_size=128),
        "OFB": lambda k, iv: AES.new(k, AES.MODE_OFB, iv),
        "ECB": lambda k, iv: AES.new(k, AES.MODE_ECB),
    }

    for hname, H in hashes.items():
        keyc = {}
        for n in (16, 24, 32):
            for i in range(0, max(1, len(H) - n + 1)):
                keyc["%s[%d:%d]" % (hname, i, i + n)] = H[i:i + n]
        ivc = {"zero": b"\0" * 16}
        for i in range(0, max(1, len(H) - 15)):
            ivc["%s[%d:%d]" % (hname, i, i + 16)] = H[i:i + 16]
        for skip in (0, 12, 16, 24):
            ct = D[skip:]
            if len(ct) < 32:
                continue
            for kn, k in keyc.items():
                for vn, iv in ivc.items():
                    for mn, mk in modes.items():
                        if mn in ("CBC", "ECB") and len(ct) % 16:
                            continue
                        try:
                            pt = mk(k, iv).decrypt(ct)
                        except Exception:
                            continue
                        sc = score(pt)
                        if sc >= 6:
                            results.append((sc, "%s | skip=%d | key=%s | iv=%s | %s"
                                            % (mn, skip, kn, vn, hname), pt))

    results.sort(key=lambda x: -x[0])
    print("\n候选（按分数）:")
    for sc, tag, pt in results[:8]:
        print("\n[%.1f] %s" % (sc, tag))
        print("   ", pt[:220].decode("utf-8", "replace").replace("\n", " "))

    if results and results[0][0] >= 50:
        open("tools/_dec/qysq_plain.json", "wb").write(results[0][2])
        print("\n★ 已保存 tools/_dec/qysq_plain.json")
    else:
        print("\n无高分候选 —— 需要回到 asm 逐指令核 0x723a70~0x723c60 的切片边界")


main()
