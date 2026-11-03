# -*- coding: utf-8 -*-
"""mmmh 第一轮：host_pwa.txt 全结构分析 + asm 解密链定位"""
import base64
import binascii
import re
import urllib.error
import urllib.request

OP = urllib.request.build_opener(urllib.request.ProxyHandler({}))
UA = "okhttp/3.14.9"
URL = "https://public.mino02.live/host_pwa.txt"

req = urllib.request.Request(URL, headers={"User-Agent": UA})
try:
    with OP.open(req, timeout=25) as r:
        raw = r.read()
        hd = dict(r.headers)
except Exception as e:
    print("fetch err", e)
    raise SystemExit(1)

txt = raw.decode("utf-8", "replace").strip()
print("长度 = %d 字符" % len(txt))
print("首 80:", txt[:80])
print("尾 80:", txt[-80:])
print("是否含非法 base64 字符:", bool(re.search(r"[^A-Za-z0-9+/=]", txt)))
print("换行数:", txt.count("\n"), " 逗号:", txt.count(","), " 冒号:", txt.count(":"))

# 解码
for name, fn in (
    ("b64", lambda s: base64.b64decode(s + "=" * ((4 - len(s) % 4) % 4))),
    ("b64url", lambda s: base64.urlsafe_b64decode(
        s.replace("-", "+").replace("_", "/") + "=" * ((4 - len(s) % 4) % 4))),
):
    try:
        b = fn(txt)
        print("\n%s 解码 -> %d 字节" % (name, len(b)))
        print("  head hex:", binascii.hexlify(b[:32]).decode())
        print("  长度 %% 16 =", len(b) % 16)
        # 熵估算
        from collections import Counter
        c = Counter(b)
        import math
        ent = -sum((v / len(b)) * math.log2(v / len(b)) for v in c.values())
        print("  香农熵 = %.3f bit/byte (随机≈8)" % ent)
        break
    except Exception as e:
        print("%s 失败: %s" % (name, e))

# 看 asm 里谁调 _decode64ToHex / 配置解析
print("\n=== asm: mmmh 里与配置/解密相关的符号 ===")
import os
ASM = r"C:\Users\Administrator\Downloads\DPK\_apk\blutter_out\asm\avbox\module\mmmh"
hits = {}
for root, _, files in os.walk(ASM):
    for fn in files:
        if not fn.endswith(".dart"):
            continue
        p = os.path.join(root, fn)
        t = open(p, encoding="utf-8", errors="ignore").read()
        for kw in ("host_pwa", "MmMhChain", "CryptoUtil", "ksSp", "Decrypt", "decrypt",
                   "base64", "AES", "chain"):
            n = t.count(kw)
            if n:
                hits.setdefault(kw, []).append((fn, n))
for kw, lst in sorted(hits.items()):
    print("  %-12s %s" % (kw, lst[:4]))
