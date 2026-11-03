# -*- coding: utf-8 -*-
"""基线追加 mmmh"""
import io
import os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
P = os.path.join(ROOT, "tools", "_gen_platform_table.py")
s = io.open(P, encoding="utf-8").read()
line = '    "mw":   {"class": 4,   "list": 38, "detail": 1, "play": 1},'
if '"mmmh"' not in s:
    assert line in s, "找不到 mw 基线行"
    s = s.replace(line, line + '\n    "mmmh": {"class": 25,  "list": 18, "detail": 1, "play": 0},', 1)
    io.open(P, "w", encoding="utf-8", newline="\n").write(s)
    print("已加 mmmh 基线（play=0：m3u8 服务端 500）")
else:
    print("已存在")
