# -*- coding: utf-8 -*-
"""确定性提取业务密钥（不做模糊启发式）。
只认三种形态：
  A. 含 # ! @ $ % ^ 且无空格、非符号名 —— 业务口令
  B. 恰好 16 位 [A-Za-z0-9] —— AES-128 key
  C. 恰好 32 位 [0-9a-fA-F] —— MD5/AppKey
并与旧 _keys_extracted.json 交叉标注。"""
import json
import os
import re
import sys

sys.stdout.reconfigure(encoding="utf-8")
TOOLS = os.path.dirname(os.path.abspath(__file__))
SO = r"C:\Users\Administrator\Downloads\DPK\_apk\libdir\libapp.so"
OLD = r"C:\Users\Administrator\Downloads\暮色逆向\_keys_extracted.json"
OUT = os.path.join(TOOLS, "_secrets_final.json")

PWD_RE = re.compile(r'^[A-Za-z0-9_\-]*(?:[#!@$%^])[A-Za-z0-9_\-!@#$%^&*]*$')
K16_RE = re.compile(r'^[A-Za-z0-9]{16}$')
K32_RE = re.compile(r'^[0-9a-fA-F]{32}$')


def strings(data, minlen=8, maxlen=100):
    out, cur = [], bytearray()
    for b in data:
        if 32 <= b < 127:
            cur.append(b)
        else:
            if len(cur) >= minlen:
                out.append(cur.decode("ascii"))
            cur = bytearray()
    if len(cur) >= minlen:
        out.append(cur.decode("ascii"))
    return [s for s in out if len(s) <= maxlen and " " not in s]


def main():
    data = open(SO, "rb").read()
    uniq = []
    for s in strings(data):
        if s not in uniq:
            uniq.append(s)
    print("候选池:", len(uniq))

    pwd, k16, k32 = [], [], []
    for s in uniq:
        if PWD_RE.match(s) and not s.startswith("_") and not re.search(r"@\d{3,}$", s) \
                and "/" not in s and len(s) <= 64:
            pwd.append(s)
        elif K16_RE.match(s):
            k16.append(s)
        elif K32_RE.match(s):
            k32.append(s)

    old = json.load(open(OLD, encoding="utf-8"))
    known = set()
    for v in old.values():
        if isinstance(v, dict):
            for k in ("key16", "hex32"):
                known.update(v.get(k, []) or [])

    for title, arr in (("A. 业务口令 (#!@$%^)", pwd), ("B. 16 位 AES key", k16), ("C. 32 位 hex", k32)):
        print("\n===== %s  共 %d =====" % (title, len(arr)))
        for s in arr:
            tag = "  <旧表已有>" if s in known else ""
            print("  %r%s" % (s, tag))

    json.dump({"pwd": pwd, "k16": k16, "k32": k32},
              open(OUT, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print("\n写出", OUT)


if __name__ == "__main__":
    main()
