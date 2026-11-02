# -*- coding: utf-8 -*-
"""hjsq 第五轮：图片混淆格式爆破 + m3u8 AES key 验证"""
import base64
import binascii
import itertools
import json
import os
import re
import urllib.request

OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "_dec")
OP = urllib.request.build_opener(urllib.request.ProxyHandler({}))
UA = {"User-Agent": "okhttp/3.14.9", "Referer": "http://23.225.145.74/"}
MAGICS = {
    b"\xff\xd8\xff": "JPEG",
    b"\x89PNG": "PNG",
    b"GIF8": "GIF",
    b"RIFF": "WEBP",
    b"BM": "BMP",
}

raw = open(os.path.join(OUT, "hjsq_img_sample.txt"), "rb").read()
txt = raw.decode("latin-1")
rep = {"len_text": len(txt), "head": txt[:40]}

# ---------- 1. 字符集统计
charset = sorted(set(txt))
rep["charset"] = "".join(charset)
rep["charset_size"] = len(charset)
STD = set("ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789+/")
cur = set(charset)
rep["extra"] = "".join(sorted(cur - STD))
rep["missing"] = "".join(sorted(STD - cur))


def try_decode(s, mapping, strip_prefix):
    s2 = s[strip_prefix:] if strip_prefix else s
    for k, v in mapping.items():
        s2 = s2.replace(k, v)
    s2 = re.sub(r"[^A-Za-z0-9+/=]", "", s2)
    s2 += "=" * ((4 - len(s2) % 4) % 4)
    try:
        d = base64.b64decode(s2, validate=False)
    except Exception as e:
        return None, str(e)
    return d, None


results = []
for star_to, hash_to in itertools.product(["+", "/"], ["+", "/"]):
    if star_to == hash_to:
        continue
    mp = {"*": star_to, "#": hash_to}
    for sp in (0, 3, 4):
        d, err = try_decode(txt, mp, sp)
        if d is None:
            continue
        magic = None
        for m, name in MAGICS.items():
            if d.startswith(m):
                magic = name
                break
        results.append({
            "map": "star->%s hash->%s" % (star_to, hash_to),
            "strip": sp,
            "declen": len(d),
            "magic": magic,
            "head_hex": binascii.hexlify(d[:16]).decode(),
        })
rep["attempts"] = results

# ---------- 2. 若得 JPEG，落盘
best = next((r for r in results if r["magic"]), None)
rep["best"] = best
if best:
    star_to, hash_to = (best["map"].split("star->")[1].split(" hash->")[0],
                        best["map"].split("hash->")[1])
    d, _ = try_decode(txt, {"*": star_to, "#": hash_to}, best["strip"])
    p = os.path.join(OUT, "hjsq_img_decoded.jpg")
    with open(p, "wb") as f:
        f.write(d)
    rep["saved"] = p
    rep["tail_hex"] = binascii.hexlify(d[-8:]).decode()

# ---------- 3. m3u8 AES key
base = "https://0ts10.hj260302818.top/hjstore/video/20261101/b5cfbcae693d2b39d547397a4ae82bb9/"
try:
    rq = urllib.request.Request(base + "enc_14386723.key", headers=UA)
    with OP.open(rq, timeout=25) as r:
        kb = r.read()
    rep["aes_key"] = {"status": r.status, "len": len(kb),
                      "hex": binascii.hexlify(kb).decode()[:64]}
except Exception as e:
    rep["aes_key"] = {"err": "%s: %s" % (type(e).__name__, e)}

with open(os.path.join(OUT, "hjsq_probe5_report.json"), "w", encoding="utf-8") as f:
    json.dump(rep, f, ensure_ascii=False, indent=1)
print(json.dumps(rep, ensure_ascii=False, indent=1)[:3500])
