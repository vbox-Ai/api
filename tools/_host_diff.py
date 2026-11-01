# -*- coding: utf-8 -*-
"""比对：解密出的 splash host 表  vs  脚本内硬编码的 HOSTS 表。"""
import json
import os
import re
import sys

sys.stdout.reconfigure(encoding="utf-8")
REPO = r"C:\Users\Administrator\Downloads\vboxapp\_remote_api"
SPLASH = os.path.join(REPO, "tools", "_dec", "box_api_splash.json")
SCRIPT = os.path.join(REPO, "sources", "welfare-js", "muse_avbox.py")


def load_live():
    s = json.load(open(SPLASH, encoding="utf-8"))
    return {h["name"]: h["host"].rstrip("/") for h in s["data"]["host"]}


def load_script_hosts():
    src = open(SCRIPT, encoding="utf-8").read()
    m = re.search(r"HOSTS\s*=\s*\{(.*?)\n\}", src, re.S)
    if not m:
        return {}
    out = {}
    for mm in re.finditer(r'"([A-Za-z0-9_]+)"\s*:\s*"([^"]+)"', m.group(1)):
        out[mm.group(1)] = mm.group(2).rstrip("/")
    return out


def main():
    live = load_live()
    cur = load_script_hosts()
    print("splash host 条数: %d" % len(live))
    print("脚本 HOSTS 条数: %d" % len(cur))
    print()

    diff, missing, same = [], [], []
    for k, v in sorted(live.items()):
        if k in cur:
            if cur[k] != v:
                diff.append((k, cur[k], v))
            else:
                same.append(k)
        else:
            missing.append((k, v))

    print("=== 不一致（必须修复）: %d ===" % len(diff))
    for k, a, b in diff:
        print("  %-12s 脚本: %-48s splash: %s" % (k, a, b))

    print()
    print("=== 脚本缺失（建议补）: %d ===" % len(missing))
    for k, v in missing:
        print("  %-12s %s" % (k, v))

    print()
    print("=== 一致: %d ===" % len(same))
    print("  " + ", ".join(same))

    extra = [k for k in cur if k not in live]
    if extra:
        print()
        print("=== 脚本有、splash 没有（可能已下线）: %d ===" % len(extra))
        for k in sorted(extra):
            print("  %-12s %s" % (k, cur[k]))


if __name__ == "__main__":
    main()
