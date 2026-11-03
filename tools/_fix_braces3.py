# -*- coding: utf-8 -*-
"""精确修复：还原 SPIDER_TPL 占位符，仅转义 HEADER_TPL 内 vbox 块的花括号"""
import io
import os
import re

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
P = os.path.join(ROOT, "tools", "_gen_standalone.py")
lines = io.open(P, encoding="utf-8").read().split("\n")

# 1) 定位模板边界
def find(pred, start=0):
    for i in range(start, len(lines)):
        if pred(lines[i]):
            return i
    return -1

i_hdr = find(lambda l: l.startswith("HEADER_TPL = "))
i_spr = find(lambda l: l.startswith("SPIDER_TPL = "))
print("HEADER_TPL @%d  SPIDER_TPL @%d" % (i_hdr + 1, i_spr + 1))

# 2) 还原 SPIDER_TPL 区间内被误转义的占位符
for i in range(i_spr, min(i_spr + 120, len(lines))):
    ln = lines[i]
    if "{{key}}" in ln or "{{name}}" in ln or "{{cls}}" in ln \
            or "{{init_seg}}" in ln or "{{fetchb}}" in ln or "{{fetcht}}" in ln:
        lines[i] = (ln.replace("{{key}}", "{key}")
                      .replace("{{name}}", "{name}")
                      .replace("{{cls}}", "{cls}")
                      .replace("{{init_seg}}", "{init_seg}")
                      .replace("{{fetchb}}", "{fetchb}")
                      .replace("{{fetcht}}", "{fetcht}"))
        print("  还原 %d: %s" % (i + 1, lines[i].strip()))

# 3) 在 HEADER_TPL 区间内，找到 vbox 块，只转义其中未转义的花括号
start = find(lambda l: "vbox 运行时适配" in l, i_hdr)
end = find(lambda l: l.startswith("SPIDER_TPL = "), i_hdr) if start > 0 else -1
print("vbox 块 %d-%d" % (start + 1, end))
fixed = 0
for i in range(start, end):
    ln = lines[i]
    if "{{" in ln or "}}" in ln:
        continue
    if "{" in ln or "}" in ln:
        lines[i] = ln.replace("{", "{{").replace("}", "}}")
        fixed += 1
        print("  转义 %d: %s" % (i + 1, lines[i].strip()))
print("转义 %d 行" % fixed)

io.open(P, "w", encoding="utf-8", newline="\n").write("\n".join(lines))
print("写回完成")
