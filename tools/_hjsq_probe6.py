# -*- coding: utf-8 -*-
"""hjsq 第六轮：图片按周期位移密码求解（残基约束法）"""
import base64
import binascii
import json
import os

OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "_dec")
txt = open(os.path.join(OUT, "hjsq_img_sample.txt"), "rb").read().decode("latin-1")

B64 = set("ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789+/")
rep = {}

# 去掉 3 字符魔数头
for hdr in (3, 4, 0):
    body = txt[hdr:]
    # 试周期 16 / 8 / 12 / 32
    for period in (16, 8, 12, 32, 24):
        # 每个残基的字符集
        S = [set() for _ in range(period)]
        for i, ch in enumerate(body):
            S[i % period].add(ch)
        # 求每个残基的候选位移（加法：p = c - k）
        cand = []
        for r in range(period):
            ok = []
            for k in range(0, 128):
                if all(chr((ord(c) - k) % 128) in B64 for c in S[r]):
                    ok.append(k)
            cand.append(ok)
        zero = [r for r in range(period) if not cand[r]]
        rep["hdr%d_p%d" % (hdr, period)] = {
            "residues_without_shift": len(zero),
            "cand_counts": [len(c) for c in cand],
            "first_residue_cands": cand[0][:20],
            "unique_all": all(len(c) == 1 for c in cand),
        }

# 详细展开最可疑的一组：hdr=3, period=16
body = txt[3:]
period = 16
S = [set() for _ in range(period)]
for i, ch in enumerate(body):
    S[i % period].add(ch)
detail = {"period": 16, "hdr": 3, "per_residue": []}
for r in range(period):
    ok = []
    for k in range(0, 128):
        if all(chr((ord(c) - k) % 128) in B64 for c in S[r]):
            ok.append(k)
    detail["per_residue"].append({
        "r": r, "distinct": len(S[r]),
        "cands": ok[:12], "n_cands": len(ok),
        "sample_chars": "".join(sorted(S[r]))[:20],
    })
rep["detail_p16"] = detail

# 若每残基唯一，直接解密
keys = []
for r in range(period):
    ok = [k for k in range(0, 128)
          if all(chr((ord(c) - k) % 128) in B64 for c in S[r])]
    if len(ok) != 1:
        keys = None
        break
    keys.append(ok[0])

rep["derived_key"] = keys
if keys:
    out = "".join(chr((ord(ch) - keys[i % period]) % 128) for i, ch in enumerate(body))
    rep["b64_head"] = out[:80]
    s = out.rstrip("=")
    s += "=" * ((4 - len(s) % 4) % 4)
    try:
        dec = base64.b64decode(s, validate=False)
        rep["dec_len"] = len(dec)
        rep["dec_hex"] = binascii.hexlify(dec[:16]).decode()
        p = os.path.join(OUT, "hjsq_img_final.jpg")
        open(p, "wb").write(dec)
        rep["saved"] = p
    except Exception as e:
        rep["b64_err"] = str(e)

with open(os.path.join(OUT, "hjsq_probe6_report.json"), "w", encoding="utf-8") as f:
    json.dump(rep, f, ensure_ascii=False, indent=1)
print(json.dumps(rep, ensure_ascii=False, indent=1)[:4000])
