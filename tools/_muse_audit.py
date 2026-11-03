# -*- coding: utf-8 -*-
"""暮色聚合 31 平台 × 平铺/适配 状态总审计"""
import json
import os
import re

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = os.path.join(ROOT, "sources")
ASM = r"C:\Users\Administrator\Downloads\DPK\_apk\blutter_out\asm\avbox\module"

# --- CATALOG
muse = open(os.path.join(SRC, "welfare-js", "muse_avbox.py"), encoding="utf-8").read()
i = muse.index("CATALOG = [")
j = muse.index("\n]", i)
cat_seg = muse[i:j]
catalog = re.findall(
    r'\{"id":\s*(\d+),\s*"key":\s*"([^"]+)",\s*"name":\s*"([^"]+)",\s*"type":\s*\d+,\s*"collect":\s*\d+,\s*"tabs":\s*(\[[^\]]*\])\}',
    cat_seg)

# --- ADAPTERS
ad_seg = muse[muse.index("ADAPTERS = {"):]
ad_seg = ad_seg[:ad_seg.index("}") + 1]
adapters = re.findall(r'"([^"]+)":\s*(\w+)', ad_seg)

# --- PLATFORM_HOSTS
ph_seg = muse[muse.index("PLATFORM_HOSTS = {"):]
ph_seg = ph_seg[:ph_seg.index("\n}") + 2]
hosts = dict(re.findall(r'"([^"]+)":\s*"([^"]+)"', ph_seg))

# --- 已注册的平台条目
wp = json.load(open(os.path.join(SRC, "welfare_platforms.json"), encoding="utf-8"))
plats = wp["platforms"]
reg = {}
for e in plats:
    api = str(e.get("api") or "")
    key = str(e.get("platformKey") or "")
    reg[key] = {"name": e.get("name"), "api": api,
                "service": e.get("serviceType"), "sort": e.get("sortOrder")}

# --- 反汇编模块可用性
asm_mods = set(os.listdir(ASM)) if os.path.isdir(ASM) else set()

# --- 已有独立脚本
wj = os.path.join(SRC, "welfare-js")
files = set(os.listdir(wj))

rows = []
print("%-8s %-10s %-5s %-6s %-8s %-7s %-6s %s" %
      ("key", "name", "tabs", "ADPT", "HOST", "ASM", "注册", "独立脚本"))
print("-" * 100)
for cid, key, name, tabs in catalog:
    has_ad = "✓" if key in dict(adapters) else "-"
    has_host = "✓" if key in hosts else "-"
    has_asm = "✓" if key in asm_mods else "-"
    # 是否已独立注册（platformKey 形如 xxx_py 且 api 指向该 key 的独立文件）
    reg_hit = [k for k, v in reg.items() if k == key + "_py"]
    standalone = [f for f in files if f in (key + ".py", "musep_" + key + ".py")]
    stand_self = key + ".py" in files       # 自包含
    stand_thin = "musep_" + key + ".py" in files  # 薄封装
    tag = "自包含" if stand_self else ("薄封装" if stand_thin else "无")
    rows.append({"id": int(cid), "key": key, "name": name, "tabs": tabs,
                 "adapter": key in dict(adapters), "host": hosts.get(key),
                 "asm": key in asm_mods, "registered": bool(reg_hit),
                 "script": tag})
    print("%-8s %-10s %-5s %-6s %-8s %-7s %-6s %s" %
          (key, name, tabs[:5], has_ad,
           (hosts.get(key) or "-")[:26], has_asm,
           "✓" if reg_hit else "-", tag))

print()
print("CATALOG 平台数 :", len(catalog))
print("ADAPTERS 已实现:", list(dict(adapters).keys()))
print("已独立注册     :", [r["key"] for r in rows if r["registered"]])
print("有自包含脚本   :", [r["key"] for r in rows if r["script"] == "自包含"])
print("仅薄封装(违反自包含约束):", [r["key"] for r in rows if r["script"] == "薄封装"])
print("完全无脚本     :", [r["key"] for r in rows if r["script"] == "无"])
print()
print("→ 待平铺（未独立注册）:", len([r for r in rows if not r["registered"]]), "个")

out = os.path.join(ROOT, "tools", "_dec", "muse_audit.json")
os.makedirs(os.path.dirname(out), exist_ok=True)
json.dump({"catalog": rows, "adapters": dict(adapters), "hosts": hosts},
          open(out, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
print("已存:", out)
