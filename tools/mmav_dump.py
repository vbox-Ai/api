# -*- coding: utf-8 -*-
"""把 mmav 解密后的明文固化为仓库资产（tools/_dec/mmav_*.json）。

产物：
  mmav_config.json      配置（域名分工、开关、客服链接等 60+ 字段）
  mmav_category.json    分类树（10 个一级菜单 × 8 子分类）
  mmav_list_sample.json 列表样本（第 1 页 50 条完整字段）
"""
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _mmav_dec import fetch_decoded  # noqa: E402

sys.stdout.reconfigure(encoding="utf-8")

OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "_dec")


def dump(name, obj):
    p = os.path.join(OUT, name)
    with open(p, "w", encoding="utf-8") as f:
        json.dump(obj, f, ensure_ascii=False, indent=1)
    n = os.path.getsize(p)
    print("  OK %-24s %6d B" % (name, n))
    return p


def main():
    os.makedirs(OUT, exist_ok=True)
    print("=== 抓取并解密 ===")

    cfg = fetch_decoded("data/config/base-1.js")
    if isinstance(cfg, dict) and not cfg.get("_err"):
        dump("mmav_config.json", cfg)
    else:
        print("  FAIL config:", str(cfg)[:80])

    cat = fetch_decoded("data/category/base-1.js")
    if isinstance(cat, dict) and not cat.get("_err"):
        dump("mmav_category.json", cat)
    else:
        print("  FAIL category:", str(cat)[:80])

    lst = fetch_decoded("data/mediaVideo/list-7-1-50.js")
    if isinstance(lst, dict) and not lst.get("_err"):
        dump("mmav_list_sample.json", lst)
    else:
        print("  FAIL list:", str(lst)[:80])

    print("\n=== 产物清单 ===")
    for f in sorted(os.listdir(OUT)):
        p = os.path.join(OUT, f)
        print("  %-40s %7d B" % (f, os.path.getsize(p)))


if __name__ == "__main__":
    main()
