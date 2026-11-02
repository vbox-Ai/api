# -*- coding: utf-8 -*-
"""hjsq 第七轮：自定义 base64 字母表解码（含旋转/反向/替换变体爆破）"""
import base64
import binascii
import json
import os

OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "_dec")
txt = open(os.path.join(OUT, "hjsq_img_sample.txt"), "rb").read().decode("latin-1")

ALPH = "ABCD*EFGHIJKLMNOPQRSTUVWX#YZabcdefghijklmnopqrstuvwxyz1234567890"
assert len(ALPH) == 64 and len(set(ALPH)) == 64
STD = "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789+/"

MAGICS = {b"\xff\xd8\xff": "JPEG", b"\x89PNG": "PNG", b"GIF8": "GIF",
          b"RIFF": "WEBP", b"BM": "BMP"}


def decode_with(alph, data):
    """用给定 64 字符表做 base64 解码；表外字符视为填充丢弃"""
    idx = {c: i for i, c in enumerate(alph)}
    buf = 0
    bits = 0
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


def magic_of(b):
    for m, n in MAGICS.items():
        if b.startswith(m):
            return n
    return None


rep = {"alph": ALPH, "text_len": len(txt)}
payload = txt[3:] if txt.startswith("#FE") else txt
rep["payload_len"] = len(payload)
rep["len_mod4"] = len(payload) % 4

cands = []

# 1) 原表 / 反向表 / 每个旋转
for name, alph in (("asis", ALPH), ("rev", ALPH[::-1])):
    d = decode_with(alph, payload)
    cands.append({"name": name, "rot": 0, "len": len(d), "magic": magic_of(d),
                  "hex": binascii.hexlify(d[:12]).decode()})

for r in range(64):
    alph = ALPH[r:] + ALPH[:r]
    d = decode_with(alph, payload[:4096])
    if magic_of(d):
        cands.append({"name": "rot", "rot": r, "magic": magic_of(d),
                      "hex": binascii.hexlify(d[:12]).decode()})
        full = decode_with(alph, payload)
        p = os.path.join(OUT, "hjsq_img_rot%d.jpg" % r)
        open(p, "wb").write(full)
        cands[-1]["saved"] = p
        cands[-1]["full_len"] = len(full)

# 2) 简单替换 * -> + , # -> / 后走标准表
for a, b in (("*+", "#/"), ("*/", "#+"), ("#+", "*/")):
    s = payload.replace(a[0], a[1]).replace(b[0], b[1])
    try:
        d = base64.b64decode(s, validate=False)
        cands.append({"name": "subst_%s_%s" % (a, b), "len": len(d),
                      "magic": magic_of(d),
                      "hex": binascii.hexlify(d[:12]).decode()})
    except Exception as e:
        cands.append({"name": "subst_%s_%s" % (a, b), "err": str(e)})

rep["cands"] = cands
rep["hit"] = [c for c in cands if c.get("magic")]

# 3) 无魔数时看熵与可打印率
d0 = decode_with(ALPH, payload)
rep["asis_stats"] = {
    "len": len(d0),
    "printable_ratio": round(sum(1 for x in d0[:2000] if 32 <= x < 127) / 2000, 3),
    "head_hex": binascii.hexlify(d0[:32]).decode(),
    "head_latin1": d0[:80].decode("latin-1"),
}

# 4) 重复块定位（了解明文结构）
seg = "TzoRWjMYij4SVnIc"
rep["zeros_seg_count"] = payload.count(seg)
d_seg = decode_with(ALPH, seg)
rep["zeros_seg_dec_hex"] = binascii.hexlify(d_seg).decode()

with open(os.path.join(OUT, "hjsq_probe7_report.json"), "w", encoding="utf-8") as f:
    json.dump(rep, f, ensure_ascii=False, indent=1)
print(json.dumps(rep, ensure_ascii=False, indent=1)[:3500])
