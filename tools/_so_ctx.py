# -*- coding: utf-8 -*-
"""在 libapp.so 中定位 hxsp 相关常量上下文，特别是 "10" 与响应判定逻辑。"""
import os
import re
import sys

sys.stdout.reconfigure(encoding="utf-8")
SO = r"C:\Users\Administrator\Downloads\DPK\_apk\libdir\libapp.so"


def ctx(buf, needle, before=120, after=260, limit=6):
    n = needle.encode() if isinstance(needle, str) else needle
    out, start = [], 0
    while len(out) < limit:
        i = buf.find(n, start)
        if i < 0:
            break
        seg = buf[max(0, i - before):i + after]
        printable = "".join(chr(c) if 32 <= c < 127 else "." for c in seg)
        out.append((i, printable))
        start = i + 1
    return out


def main():
    buf = open(SO, "rb").read()
    for needle in sys.argv[1:] or ["Bearer_", "getPubConfig", "W$S3skNwm3zkHXqd"]:
        print("\n===== %r =====" % needle)
        for off, s in ctx(buf, needle):
            print("  0x%08x  %s" % (off, s))


if __name__ == "__main__":
    main()
