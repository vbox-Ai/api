# -*- coding: utf-8 -*-
"""精确替换 _vbox_proxy 里的 dict 字面量行"""
import io
import os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
P = os.path.join(ROOT, "tools", "_gen_standalone.py")
lines = io.open(P, encoding="utf-8").read().split("\n")

target_old = "return {'http': u, 'https': u} if u else {{}}"
target_new = "return {{'http': u, 'https': u}} if u else {{}}"

n = 0
for i, ln in enumerate(lines):
    if "'http': u" in ln:
        lines[i] = "    " + target_new
        n += 1
        print("  %d: %s" % (i + 1, lines[i].strip()))

io.open(P, "w", encoding="utf-8", newline="\n").write("\n".join(lines))
print("替换 %d 行" % n)
