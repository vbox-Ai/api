# -*- coding: utf-8 -*-
"""hjsq 第八轮：自定义 base64 -> data URI -> 真实图片"""
import base64
import binascii
import json
import os

OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "_dec")
txt = open(os.path.join(OUT, "hjsq_img_sample.txt"), "rb").read().decode("latin-1")
ALPH = "ABCD*EFGHIJKLMNOPQRSTUVWX#YZabcdefghijklmnopqrstuvwxyz1234567890"
MAGICS = {b"\xff\xd8\xff": "JPEG", b"\x89PNG": "PNG", b"GIF8": "GIF",
          b"RIFF": "WEBP", b"BM": "BMP"}


def decode_with(alph, data):
    idx = {c: i for i, c in enumerate(alph)}
    buf = bits = 0
    out = bytearray()
    for ch in data:
        v = idx.get(ch)
        if v is None:
            continue
        buf = (buf << 6) | v
        bits += 6
        if bits >= 8:
            bits -= 8
            out.append((buf >> bits) & 0xFF)
    return bytes(out)


rep = {}
inner = decode_with(ALPH, txt).decode("latin-1")
rep["inner_len"] = len(inner)
rep["inner_head"] = inner[:60]
rep["inner_tail"] = inner[-20:]

if inner.startswith("data:"):
    head, _, b64part = inner.partition(",")
    rep["mime"] = head
    rep["b64_len"] = len(b64part)
    raw = base64.b64decode(b64part + "=" * ((4 - len(b64part) % 4) % 4), validate=False)
    rep["img_len"] = len(raw)
    rep["img_hex"] = binascii.hexlify(raw[:16]).decode()
    rep["img_magic"] = next((n for m, n in MAGICS.items() if raw.startswith(m)), None)
    if rep["img_magic"]:
        ext = {"JPEG": "jpg", "PNG": "png", "GIF": "gif", "WEBP": "webp", "BMP": "bmp"}[rep["img_magic"]]
        p = os.path.join(OUT, "hjsq_img_decoded.%s" % ext)
        open(p, "wb").write(raw)
        rep["saved"] = p
        rep["saved_size"] = os.path.getsize(p)
else:
    rep["note"] = "非 data URI，输出前 200 字符"
    rep["inner_200"] = inner[:200]

print(json.dumps(rep, ensure_ascii=False, indent=1)[:2500])
with open(os.path.join(OUT, "hjsq_probe8_report.json"), "w", encoding="utf-8") as f:
    json.dump(rep, f, ensure_ascii=False, indent=1)
