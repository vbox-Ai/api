# -*- coding: utf-8 -*-
"""彻底转义 _gen_standalone.py 的 HEADER_TPL 中 vbox 适配块内的所有花括号"""
import io
import os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
P = os.path.join(ROOT, "tools", "_gen_standalone.py")
src = io.open(P, encoding="utf-8").read()
lines = src.split("\n")

start = next(i for i, l in enumerate(lines) if "vbox 运行时适配" in l)
end = next(i for i, l in enumerate(lines) if i > start and l.startswith("def build("))

fixed = 0
for i in range(start, end):
    ln = lines[i]
    if "{{" in ln or "}}" in ln:
        continue                      # 已转义
    if "{" in ln or "}" in ln:
        new = ln.replace("{", "{{").replace("}", "}}")
        lines[i] = new
        fixed += 1
        print("  %d: %s" % (i + 1, new.strip()))

io.open(P, "w", encoding="utf-8", newline="\n").write("\n".join(lines))
print("已转义 %d 行（块范围 %d-%d）" % (fixed, start + 1, end))
