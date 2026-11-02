# -*- coding: utf-8 -*-
"""hjsq 第四轮：m3u8 可用性 + 图片 .txt 加密格式分析"""
import binascii
import json
import os
import urllib.request

OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "_dec")
os.makedirs(OUT, exist_ok=True)
OP = urllib.request.build_opener(urllib.request.ProxyHandler({}))
UA = {"User-Agent": "okhttp/3.14.9", "Referer": "http://23.225.145.74/"}


def fetch(u, n=None):
    rq = urllib.request.Request(u, headers=UA)
    with OP.open(rq, timeout=25) as r:
        return r.status, dict(r.headers), (r.read(n) if n else r.read())


rep = {}

M3U8 = "https://0ts10.hj260302818.top/hjstore/video/20261101/b5cfbcae693d2b39d547397a4ae82bb9/571842_i_preview.m3u8"
IMG = "https://pic.hj260302818.top/hjstore/images/20261102/3b8756537400d11c9d4c38e5034feb5a.jpg.txt"

# ---------- 1. m3u8
try:
    st, hd, body = fetch(M3U8)
    txt = body.decode("utf-8", "replace")
    rep["m3u8"] = {"status": st, "ctype": hd.get("Content-Type"),
                   "len": len(body), "head": txt[:800]}
    segs = [l.strip() for l in txt.splitlines() if l.strip() and not l.startswith("#")]
    rep["m3u8"]["segs"] = len(segs)
    if segs:
        base = M3U8.rsplit("/", 1)[0] + "/"
        su = segs[0] if segs[0].startswith("http") else base + segs[0]
        st2, hd2, b2 = fetch(su, 64)
        rep["m3u8"]["seg0_url"] = su
        rep["m3u8"]["seg0"] = {"status": st2, "ctype": hd2.get("Content-Type"),
                               "len_sample": len(b2),
                               "hex": binascii.hexlify(b2[:16]).decode()}
except Exception as e:
    rep["m3u8"] = {"err": "%s: %s" % (type(e).__name__, e)}

# ---------- 2. 图片 .txt
try:
    st, hd, body = fetch(IMG)
    rep["img"] = {"status": st, "ctype": hd.get("Content-Type"), "len": len(body)}
    head = body[:400]
    rep["img"]["head_ascii"] = head.decode("latin-1")
    rep["img"]["head_hex"] = binascii.hexlify(head[:64]).decode()
    with open(os.path.join(OUT, "hjsq_img_sample.txt"), "wb") as f:
        f.write(body)
    # 结构试探：找分隔符 / 换行 / 冒号
    rep["img"]["newlines"] = body.count(b"\n")
    rep["img"]["colons"] = body.count(b":")
    rep["img"]["pipes"] = body.count(b"|")
    # 尝试 base64 段
    import re
    m = re.search(rb"[A-Za-z0-9+/=]{80,}", body)
    if m:
        s = m.group(0)
        rep["img"]["b64_candidate_len"] = len(s)
        try:
            dec = __import__("base64").b64decode(s[:len(s) // 4 * 4])
            rep["img"]["b64_dec_hex"] = binascii.hexlify(dec[:16]).decode()
            rep["img"]["b64_dec_magic"] = dec[:4].hex()
        except Exception as e:
            rep["img"]["b64_err"] = str(e)
except Exception as e:
    rep["img"] = {"err": "%s: %s" % (type(e).__name__, e)}

with open(os.path.join(OUT, "hjsq_probe4_report.json"), "w", encoding="utf-8") as f:
    json.dump(rep, f, ensure_ascii=False, indent=1)
print(json.dumps(rep, ensure_ascii=False, indent=1)[:4000])
