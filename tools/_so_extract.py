# -*- coding: utf-8 -*-
"""从 libapp.so（Flutter AOT）全量提取平台情报。

原理：Dart AOT 快照的字符串池是明文 UTF-8，按平台模块路径切段，
把每个 avbox/module/<key>/ 下的所有字符串归类，再按语义分组：
  密钥类 / URL 类 / 路径类 / 字段类 / 头名类
"""
import os
import re
import sys
from collections import OrderedDict

sys.stdout.reconfigure(encoding="utf-8")
SO = r"C:\Users\Administrator\Downloads\DPK\_apk\libdir\libapp.so"
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "_so_strings.txt")

# 只保留"像情报"的字符串
URL_RE = re.compile(r'https?://[^\s"\'<>\\]{4,200}')
PATH_RE = re.compile(r'^(?:[a-zA-Z_][\w\-]*/)+[\w\-.?=&%{}]*$')
HEX16 = re.compile(r'^[0-9a-fA-F]{16}$')
HEX32 = re.compile(r'^[0-9a-fA-F]{32,128}$')
B64 = re.compile(r'^[A-Za-z0-9+/=]{20,}$')


def extract_strings(data, minlen=4, maxlen=400):
    out = []
    cur = bytearray()
    for b in data:
        if 32 <= b < 127:
            cur.append(b)
        else:
            if len(cur) >= minlen:
                out.append(cur.decode("ascii"))
            cur = bytearray()
    if len(cur) >= minlen:
        out.append(cur.decode("ascii"))
    return [s for s in out if len(s) <= maxlen]


def main():
    data = open(SO, "rb").read()
    print("so size", len(data))
    strs = extract_strings(data)
    print("raw ascii strings", len(strs))
    uniq = list(OrderedDict.fromkeys(strs))
    print("unique", len(uniq))

    keys = {}
    for s in uniq:
        m = re.search(r'avbox/module/([a-z0-9_]+)/', s)
        if m:
            keys.setdefault(m.group(1), set()).add(s)
    print("发现模块数:", len(keys))
    print("模块:", sorted(keys.keys()))

    # 全局情报（不属于任何模块）
    glob = {
        "url": set(), "hex": set(), "path": set(), "b64": set(),
    }
    for s in uniq:
        if URL_RE.search(s):
            glob["url"].update(URL_RE.findall(s))
        if HEX16.match(s) or HEX32.match(s):
            glob["hex"].add(s)
        if "avbox/module/" in s:
            continue
        if PATH_RE.match(s) and ("/" in s) and len(s) < 120:
            glob["path"].add(s)
        if B64.match(s) and len(s) >= 32:
            glob["b64"].add(s)

    with open(OUT, "w", encoding="utf-8") as w:
        w.write("# libapp.so 字符串情报\n\n")
        w.write("## 全局 URL（%d）\n" % len(glob["url"]))
        for u in sorted(glob["url"]):
            w.write("- %s\n" % u)
        w.write("\n## 全局 hex 密钥（%d）\n" % len(glob["hex"]))
        for h in sorted(glob["hex"]):
            w.write("- `%s`\n" % h)
        w.write("\n## 全局路径（%d）\n" % len(glob["path"]))
        for p in sorted(glob["path"]):
            w.write("- %s\n" % p)

        w.write("\n\n# 按模块分组\n")
        for k in sorted(keys.keys()):
            w.write("\n## %s\n" % k)
            for s in sorted(keys[k]):
                w.write("- %s\n" % s)
    print("写出", OUT)
    print("全局 url", len(glob["url"]), "hex", len(glob["hex"]), "path", len(glob["path"]))


if __name__ == "__main__":
    main()
