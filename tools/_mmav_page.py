# -*- coding: utf-8 -*-
"""确认列表模板中间数字的语义：页码 vs 偏移量。"""
import sys

sys.path.insert(0, r"C:\Users\Administrator\Downloads\vboxapp\_remote_api\tools")
from _mmav_dec import fetch_decoded  # noqa: E402

sys.stdout.reconfigure(encoding="utf-8")


def ids(path):
    r = fetch_decoded(path)
    if not isinstance(r, dict) or r.get("_err"):
        return None, 0, None
    lst = r.get("list") or {}
    data = lst.get("data") or []
    first = data[0]["id"] if data else None
    return [d["id"] for d in data], lst.get("current_page"), first


if __name__ == "__main__":
    print("=== 按「页码」解释：list-7-{page}-50 ===")
    for pg in (1, 2, 3, 4):
        ids_list, cur, first = ids("data/mediaVideo/list-7-%d-50.js" % pg)
        print("  page=%-3d current_page=%-4s 条数=%-3s 首条id=%s" % (
            pg, cur, len(ids_list) if ids_list else 0, first))

    print("\n=== 按「偏移量」解释：list-7-{offset}-50 ===")
    for off in (1, 51, 101):
        ids_list, cur, first = ids("data/mediaVideo/list-7-%d-50.js" % off)
        print("  off=%-4d current_page=%-4s 条数=%-3s 首条id=%s" % (
            off, cur, len(ids_list) if ids_list else 0, first))
