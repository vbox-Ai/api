# -*- coding: utf-8 -*-
"""抽取指定 dart 反汇编文件的字符串池字面量（按出现顺序）。"""
import os
import re
import sys

sys.stdout.reconfigure(encoding="utf-8")
ASM = r"C:\Users\Administrator\Downloads\DPK\_apk\blutter_out\asm"


def dump(rel):
    p = os.path.join(ASM, rel.replace("/", os.sep))
    if not os.path.exists(p):
        print("NOT FOUND", p)
        return
    pat = re.compile(r'; \[pp\+0x[0-9a-f]+\] "(.*)"$')
    for i, line in enumerate(open(p, encoding="utf-8"), 1):
        m = pat.search(line.rstrip())
        if m:
            print("%5d  %r" % (i, m.group(1)))


if __name__ == "__main__":
    for rel in sys.argv[1:]:
        print("=" * 30, rel)
        dump(rel)
