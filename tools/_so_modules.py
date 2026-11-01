# -*- coding: utf-8 -*-
"""精确的模块归属：把 so 字符串池按 ['avbox/module/<key>/' ... ] 切段，
每个段内的字符串归属该模块。这样能排除全局共享噪声。

Dart AOT 的字符串池按"分配顺序"连续存放，同一模块的常量通常相邻。
"""
import json
import os
import re
import sys
from collections import OrderedDict

sys.stdout.reconfigure(encoding="utf-8")
TOOLS = os.path.dirname(os.path.abspath(__file__))
SO = r"C:\Users\Administrator\Downloads\DPK\_apk\libdir\libapp.so"
OUT = os.path.join(TOOLS, "_1101_module_map.json")

MOD_RE = re.compile(r'^[A-Za-z0-9_./]+\.dart$')
KEY_RE = re.compile(r'^[A-Za-z0-9_\-!#@$%^&*]{8,80}$')
URL_RE = re.compile(r'^https?://[^\s]{4,200}$')
HEX_RE = re.compile(r'^[0-9a-fA-F]{16,128}$')


def tokens(data):
    """顺序返回 so 中所有 >=6 字符的可打印串。"""
    out, cur = [], bytearray()
    for b in data:
        if 32 <= b < 127:
            cur.append(b)
        else:
            if len(cur) >= 6:
                out.append(cur.decode("ascii"))
            cur = bytearray()
    return out


def main():
    data = open(SO, "rb").read()
    toks = tokens(data)
    print("tokens:", len(toks))

    # 找模块边界：路径字符串 avbox/module/<key>/...
    bounds = []
    for i, t in enumerate(toks):
        m = re.search(r'avbox/module/([a-z0-9_]+)/', t)
        if m:
            bounds.append((i, m.group(1)))

    print("模块边界点:", len(bounds))
    if not bounds:
        return

    # 每个模块取它所有边界点之后 40 个 token 窗口内的内容
    mods = {}
    for idx, (pos, key) in enumerate(bounds):
        window = toks[pos:pos + 40]
        d = mods.setdefault(key, {"urls": set(), "keys": set(), "hex": set(), "paths": set()})
        for t in window:
            if URL_RE.match(t):
                d["urls"].add(t)
            elif HEX_RE.match(t):
                d["hex"].add(t)
            elif KEY_RE.match(t) and (re.search(r'[A-Z]', t) or re.search(r'[#!@$%^&*]', t)) \
                    and not t.endswith(".dart"):
                d["keys"].add(t)

    print("归入模块:", len(mods))
    out = {}
    for k in sorted(mods):
        v = mods[k]
        out[k] = {kk: sorted(vv) for kk, vv in v.items()}
        if v["keys"] or v["hex"]:
            print("\n== %s ==" % k)
            if v["urls"]:
                print("  URL:", sorted(v["urls"])[:3])
            if v["hex"]:
                print("  HEX:", sorted(v["hex"])[:5])
            if v["keys"]:
                print("  KEY:", sorted(v["keys"])[:8])

    json.dump(out, open(OUT, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print("\n写出", OUT)


if __name__ == "__main__":
    main()
