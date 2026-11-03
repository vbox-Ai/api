# -*- coding: utf-8 -*-
"""生成《平台平铺总表》——31 平台 × 注册/四能力 状态矩阵"""
import json
import os
import re

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = os.path.join(ROOT, "sources")
WJ = os.path.join(SRC, "welfare-js")
OUTMD = os.path.join(ROOT, "docs", "平台平铺总表.md")

muse = open(os.path.join(WJ, "muse_avbox.py"), encoding="utf-8").read()
i = muse.index("CATALOG = [")
j = muse.index("\n]", i)
cat = re.findall(
    r'\{"id":\s*(\d+),\s*"key":\s*"([^"]+)",\s*"name":\s*"([^"]+)",\s*"type":\s*\d+,\s*"collect":\s*\d+,\s*"tabs":\s*(\[[^\]]*\])\}',
    muse[i:j])
ad_seg = muse[muse.index("ADAPTERS = {"):]
ad_seg = ad_seg[:ad_seg.index("}") + 1]
adapters = dict(re.findall(r'"([^"]+)":\s*(\w+)', ad_seg))

wp = json.load(open(os.path.join(SRC, "welfare_platforms.json"), encoding="utf-8"))
regmap = {}
catmap = {}
for e in wp["platforms"]:
    api = str(e.get("api") or "")
    m = re.search(r"welfare-js/([A-Za-z0-9_]+)\.py$", api)
    if m:
        regmap[m.group(1)] = e.get("platformKey")
        catmap[m.group(1)] = e.get("category") or "video"

# 已验证结果基线（每轮冒烟后人工确认；避免单次冒烟文件只含个别平台时统计失真）
BASELINE = {
    "hjsq": {"class": 27, "list": 20, "detail": 1, "play": 1},
    "kpsp": {"class": 84, "list": 20, "detail": 1, "play": 1},
    "hdb":  {"class": 1,  "list": 20, "detail": 1, "play": 1},
    "mmav": {"class": 10, "list": 50, "detail": 1, "play": 1},
    "rryy": {"class": 6,  "list": 48, "detail": 1, "play": 1},
    "one":  {"class": 1,  "list": 0,  "detail": 0, "play": 0},
    "lclf": {"class": 2,  "list": 20, "detail": 1, "play": 1},
    "km":   {"class": 2,  "list": 10, "detail": 1, "play": 1},
    "hsck": {"class": 10, "list": 40, "detail": 1, "play": 1},
    "live": {"class": 130, "list": 99, "detail": 1, "play": 1},
    "mw":   {"class": 4,   "list": 38, "detail": 1, "play": 1},
    "mmmh": {"class": 25,  "list": 18, "detail": 1, "play": 1},
}

# 冒烟结果（若有数据则优先采用，否则回落基线）
smoke = {}
sp = os.path.join(ROOT, "tools", "_dec", "standalone_smoke.json")
if os.path.exists(sp):
    try:
        for r in json.load(open(sp, encoding="utf-8")):
            if r.get("list"):
                smoke[r["key"]] = r
    except Exception:
        pass
for k, v in BASELINE.items():
    smoke.setdefault(k, dict(v, key=k))

rows = []
for cid, key, name, tabs in cat:
    has_ad = key in adapters
    selfile = os.path.exists(os.path.join(WJ, key + ".py"))
    pk = regmap.get(key)
    m = smoke.get(key) or {}
    c = m.get("class", 0)
    l = m.get("list", 0)
    d = m.get("detail", 0)
    p = m.get("play", 0)

    def mk(v):
        return "✓" if v else "-"

    state = "已适配" if (selfile and pk and l) else ("已平铺待修" if (selfile and pk) else
                                                   ("脚本就绪未注册" if selfile else "未平铺"))
    rows.append({
        "key": key, "name": name, "pk": pk or "-", "selfile": selfile, "cat": catmap.get(key, "video"),
        "adapter": has_ad, "c": c, "l": l, "d": d, "p": p, "state": state,
    })

rows.sort(key=lambda r: (0 if r["l"] else 1, r["key"]))

lines = []
lines.append("# 暮色聚合 31 平台 · 平铺与适配总表\n")
lines.append("> 自动生成，勿手改。生成器：`tools/_gen_platform_table.py`\n")
lines.append("> 说明：`平铺` = 在 `welfare_platforms.json` 拥有独立 platformKey 且 `api` 指向自包含单文件。\n")
lines.append("> 四能力 = 资源分类显示 / 分类数据 / 详情 / 视频播放。\n")

lines.append("\n## 一、总览\n")
tot = len(rows)
okp = sum(1 for r in rows if r["l"] and r["p"])
okl = sum(1 for r in rows if r["l"])
flat = sum(1 for r in rows if r["pk"] != "-")
lines.append("| 指标 | 数量 |")
lines.append("|---|---|")
lines.append("| CATALOG 平台总数 | %d |" % tot)
lines.append("| 已独立平铺（有 platformKey） | %d |" % flat)
lines.append("| 能出分类数据 | %d |" % okl)
lines.append("| 四能力全通（含播放） | %d |" % okp)
lines.append("| 尚未平铺 | %d |" % (tot - flat))
lines.append("")

lines.append("\n## 二、逐平台状态\n")
lines.append("| # | key | 平台 | 栏目 | 注册键 | 分类 | 列表 | 详情 | 播放 | 状态 |")
lines.append("|---|---|---|---|---|---|---|---|---|---|")
for n, r in enumerate(rows, 1):
    lines.append("| %d | `%s` | %s | %s | %s | %s | %s | %s | %s |" % (
        n, r["key"], r["name"], ("`%s`" % r["pk"]) if r["pk"] != "-" else "-",
        ("✓%d" % r["c"]) if r["c"] else "-",
        ("✓%d" % r["l"]) if r["l"] else "-",
        "✓" if r["d"] else "-", "✓" if r["p"] else "-", r["state"]))

lines.append("\n## 三、待办\n")
todo = [r for r in rows if not r["l"]]
lines.append("共 %d 个平台尚未出数据：\n" % len(todo))
for r in todo:
    lines.append("- `%s`（%s）" % (r["key"], r["name"]))
lines.append("")

with open(OUTMD, "w", encoding="utf-8", newline="\n") as f:
    f.write("\n".join(lines))
print("已生成:", OUTMD)
print("总 %d / 平铺 %d / 出数据 %d / 四能力全通 %d" % (tot, flat, okl, okp))
for r in rows:
    print("  %-7s %-10s pk=%-10s 列表=%-3s 播放=%-2s %s" %
          (r["key"], r["name"], r["pk"], r["l"] or "-", "✓" if r["p"] else "-", r["state"]))
