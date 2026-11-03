# -*- coding: utf-8 -*-
"""移除重复平台（直播盒子 live_py，已由 muse_live_box_py 覆盖）"""
import json
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = os.path.join(ROOT, "sources")
WP = os.path.join(SRC, "welfare_platforms.json")
AS = os.path.join(SRC, "all_sources.json")

REMOVE = {"live_py"}


def load(p):
    with open(p, encoding="utf-8") as f:
        return json.load(f)


def dump(p, o):
    with open(p, "w", encoding="utf-8", newline="\n") as f:
        json.dump(o, f, ensure_ascii=False, indent=2)
        f.write("\n")


wp = load(WP)
asrc = load(AS)
asl = (asrc.get("welfarePlatforms") or {}).get("platforms") or []

for name, lst in (("welfare", wp["platforms"]), ("all_sources", asl)):
    before = len(lst)
    keep = [e for e in lst if e.get("platformKey") not in REMOVE]
    removed = [e.get("platformKey") for e in lst if e.get("platformKey") in REMOVE]
    lst[:] = keep
    print("%-12s %d -> %d  移除=%s" % (name, before, len(keep), removed))

dump(WP, wp)
dump(AS, asrc)
print("\n完成。当前平台数: welfare=%d all=%d" % (len(wp["platforms"]), len(asl)))
