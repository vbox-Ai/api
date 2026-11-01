# -*- coding: utf-8 -*-
"""抽取 blutter 反汇编里的字符串池字面量（按出现顺序）。"""
import re
import sys
import os

ASM = r"C:\Users\Administrator\Downloads\DPK\_apk\blutter_out\asm"


def dump(path):
    s = open(path, encoding="utf-8").read()
    pat = re.compile(r'; \[pp\+[0-9a-f]+\] "(.*)"$')
    seen = []
    for line in s.split("\n"):
        m = pat.search(line.rstrip())
        if m:
            v = m.group(1)
            if v not in seen:
                seen.append(v)
    return seen


if __name__ == "__main__":
    target = sys.argv[1] if len(sys.argv) > 1 else "avbox/module/hgsp/network/service.dart"
    p = os.path.join(ASM, target.replace("/", os.sep))
    for v in dump(p):
        print(repr(v))
