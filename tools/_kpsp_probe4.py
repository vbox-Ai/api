# -*- coding: utf-8 -*-
"""kpsp 实测 v4：详情字段 / 导航端点 / per_page 上限 / 标签差异"""
import json
import os

from _kpsp_probe2 import BASE, OUT, call, decrypt
from _kpsp_probe2 import fetch_dec

print("1) 详情 api/vod/video/{id}")
j = fetch_dec("api/vod/video/242253", None, "detail")

print("\n2) 导航端点候选")
for p in ["api/vod/nav", "api/nav", "api/vod/tag", "api/vod/tags",
          "api/vod/category", "api/vod/site", "api/vod/product"]:
    st, body = call(p)
    note = ""
    try:
        w = json.loads(body.decode("utf-8", "replace"))
        xd = w.get("x-data") if isinstance(w, dict) else None
        if xd:
            pl, _ = decrypt(xd)
            note = "★解密 " + pl[:160].decode("utf-8", "replace")
        else:
            note = str(w)[:120]
    except Exception:
        note = body[:100].decode("utf-8", "replace")
    print("  %-22s -> %s  %s" % (p, st, note))

print("\n3) per_page 上限")
for n in (20, 50, 100, 200):
    st, body = call("api/vod/video", {"page": 1, "per_page": n, "site_id": 1})
    try:
        w = json.loads(body.decode("utf-8", "replace"))
        d = json.loads(decrypt(w["x-data"])[0].decode("utf-8")).get("data") or {}
        print("  per_page=%-4d 返回=%d  pages=%s" % (n, len(d.get("items") or []), d.get("pages")))
    except Exception as e:
        print("  per_page=%-4d 失败 %s" % (n, e))

print("\n4) 各标签是否真的有差异")
tags = ["网黄", "探花", "传媒", "吃瓜", "直播", "乱伦", "自拍",
        "偷拍", "私拍", "换脸", "泄密", "三级", "动漫", "欧美"]
sig = {}
for t in tags:
    st, body = call("api/vod/video", {"page": 1, "per_page": 3, "site_id": 1, "tag": t})
    try:
        w = json.loads(body.decode("utf-8", "replace"))
        d = json.loads(decrypt(w["x-data"])[0].decode("utf-8")).get("data") or {}
        items = d.get("items") or []
        first = items[0]["id"] if items else None
        sig[t] = (d.get("total"), first)
        print("  %-4s total=%-8s first=%s" % (t, d.get("total"), first))
    except Exception as e:
        print("  %-4s 失败 %s" % (t, e))
print("\n  不同首条数:", len({v[1] for v in sig.values()}),
      " 不同 total 数:", len({v[0] for v in sig.values()}))
