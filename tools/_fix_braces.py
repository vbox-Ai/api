# -*- coding: utf-8 -*-
"""修 _gen_standalone.py 里 vbox 适配块的空 dict 字面量：{} -> {{}} （避免 .format 报错）"""
import io
import os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
P = os.path.join(ROOT, "tools", "_gen_standalone.py")
lines = io.open(P, encoding="utf-8").read().split("\n")

fixed = 0
in_block = False
for i, ln in enumerate(lines):
    if "vbox 运行时适配" in ln:
        in_block = True
    if in_block and ln.startswith("def build("):
        in_block = False
    if in_block and "return {}" in ln and "{{}}" not in ln:
        lines[i] = ln.replace("return {}", "return {{}}")
        fixed += 1
    elif in_block and "else {}" in ln and "{{}}" not in ln:
        lines[i] = ln.replace("else {}", "else {{}}")
        fixed += 1

io.open(P, "w", encoding="utf-8", newline="\n").write("\n".join(lines))
print("已修 %d 处空 dict" % fixed)

# 复核
s = io.open(P, encoding="utf-8").read()
for i, ln in enumerate(s.split("\n"), 1):
    if 118 <= i <= 150 and ("return {" in ln or "else {" in ln):
        print("  %d: %s" % (i, ln.strip()))
