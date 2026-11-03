# -*- coding: utf-8 -*-
"""mmmh 图片：试 chain 参数与各种派生"""
import base64
import hashlib
import urllib.error
import urllib.request

from Crypto.Cipher import AES
from Crypto.Util.Padding import unpad

OP = urllib.request.build_opener(urllib.request.ProxyHandler({}))
UA = "okhttp/3.14.9"
IMG = "https://image.meme06.live"
COVER = "/imgs/cover/e4/fc322606ea.jpg"
CHAIN = "miXFCHEoSXJ.M"
TOKEN = ("eyJ1c2VyX2lkIjozMDQ1OTg4NjEsImxhc3Rsb2dpbiI6MTc2Mjg3MTA1MH0"
         ".a568a4b03a8d6c08c14494d85c40a9f1"
         ".7c6579106b5199d2177be390fc8c608b73bfc0cf63a2d853da78afab")


def get(url, hdrs=None):
    h = {"User-Agent": UA}
    if hdrs:
        h.update(hdrs)
    try:
        with OP.open(urllib.request.Request(url, headers=h), timeout=20) as r:
            return r.status, dict(r.headers), r.read()
    except urllib.error.HTTPError as e:
        return e.code, dict(e.headers) if e.headers else {}, e.read()
    except Exception as e:
        return 0, {}, str(e).encode()


VARIANTS = [
    ("裸", IMG + COVER),
    ("?chain=", IMG + COVER + "?chain=" + CHAIN),
    ("&chain=", IMG + COVER + "&chain=" + CHAIN),
    ("?chain= 无点", IMG + COVER + "?chain=" + CHAIN.replace(".", "")),
    ("?chain=&token", IMG + COVER + "?chain=" + CHAIN + "&token=" + TOKEN),
]

for name, url in VARIANTS:
    st, hd, b = get(url)
    magic = b[:4].hex() if b else ""
    isjpg = b[:3] == b"\xff\xd8\xff"
    ispng = b[:4] == b"\x89PNG"
    print("%-14s -> %s %7d  magic=%-10s %s" % (
        name, st, len(b), magic,
        "★JPEG" if isjpg else ("★PNG" if ispng else ("加密/其它" if b else ""))))

# 拿一份密文做本地破解尝试
st, hd, data = get(IMG + COVER)
print("\n密文 %d 字节  16%%=%d" % (len(data), len(data) % 16))

if len(data) % 16 == 0:
    cands = {}
    ch = CHAIN
    cands["md5(chain)[:16]"] = hashlib.md5(ch.encode()).hexdigest()[:16].encode()
    cands["md5(chain)raw"] = hashlib.md5(ch.encode()).digest()
    cands["md5(chain+token)[:16]"] = hashlib.md5((ch + TOKEN).encode()).hexdigest()[:16].encode()
    cands["chain[:16]pad"] = (ch.encode() + b"\x00" * 16)[:16]
    cands["token前16"] = TOKEN[:16].encode()
    cands["respkey[:16]"] = b"ae52f7ffd2dd66ba"[:16]
    cands["respkey32"] = b"ae52f7ffd2dd66ba5743bb180188b991"
    ivs = {
        "zero": b"\x00" * 16,
        "md5chain[8:24]": hashlib.md5(ch.encode()).hexdigest()[8:24].encode(),
        "chain[:16]pad": (ch.encode() + b"\x00" * 16)[:16],
    }
    hit = 0
    for kn, kb in cands.items():
        for ivn, ivb in ivs.items():
            if len(kb) not in (16, 24, 32):
                continue
            try:
                p = AES.new(kb, AES.MODE_CBC, ivb).decrypt(data[:len(data) // 16 * 16])
                if p[:3] == b"\xff\xd8\xff" or p[:4] == b"\x89PNG":
                    print("  ★★ 命中 key=%s iv=%s" % (kn, ivn))
                    hit += 1
            except Exception:
                pass
    if not hit:
        print("  本地 AES 组合未命中（需继续逆向 MmMhAnimImg 的密钥派生）")
