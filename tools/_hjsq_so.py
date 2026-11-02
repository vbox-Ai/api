# -*- coding: utf-8 -*-
"""在 libapp.so 里定位图片 .txt 混淆的解码痕迹"""
import os
import re

SO = r"C:\Users\Administrator\Downloads\DPK\_apk\libdir\libapp.so"
data = open(SO, "rb").read()
print("so size = %d" % len(data))

pats = [b"#FE", b".jpg.txt", b"hjstore", b"TzoRWjMY", b".txt", b"jpg.txt",
        b"imgUrl", b"remoteUrl", b"coverUrl"]
for p in pats:
    idx = 0
    hits = []
    while len(hits) < 6:
        i = data.find(p, idx)
        if i < 0:
            break
        hits.append(i)
        idx = i + 1
    print("[%-12s] %d  %s" % (p.decode("latin-1"), len(hits), hits))

# 找可疑的 64 字符字母表字面量（含 # 或 * 的长 ASCII 串）
print("\n--- 候选字母表/替换表字面量 ---")
found = 0
for m in re.finditer(rb"[A-Za-z0-9#*+/=$_\-]{50,90}", data):
    s = m.group(0)
    if b" " in s:
        continue
    ext = set(s) - set(b"ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789+/")
    if ext and (b"*" in s or b"#" in s) and len(set(s)) >= 55:
        print("off=%d len=%d distinct=%d  %s" % (m.start(), len(s), len(set(s)), s[:90].decode("latin-1")))
        found += 1
        if found >= 15:
            break
print("候选数 =", found)

# 找 "#FE" 变体：F/E 相关魔数
print("\n--- 魔数候选 ---")
for p in [b"FEyX", b"yXSn", b"#FEy", b"FE#", b"encrypt", b"decrypt", b"xor", b"Xor"]:
    print("%-10s %d" % (p.decode("latin-1"), data.count(p)))
