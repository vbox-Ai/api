# -*- coding: utf-8 -*-
"""通用冒烟：验证自包含适配器是否有 分类 / 列表 / 详情 / 播放 四项能力

用法：python tools/_smoke_standalone.py hdb mmav rryy one
"""
import importlib.util
import json
import os
import sys
import traceback

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
WJ = os.path.join(ROOT, "sources", "welfare-js")


def load(key):
    p = os.path.join(WJ, key + ".py")
    spec = importlib.util.spec_from_file_location("sp_" + key, p)
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


def probe(key, deep=True):
    r = {"key": key, "class": 0, "list": 0, "detail": 0, "play": 0,
         "err": "", "sample": "", "play_url": ""}
    try:
        m = load(key)
        sp = m.Spider()
        sp.init("")

        # 1 分类
        h = sp.homeContent(True)
        cls = h.get("class") or []
        r["class"] = len(cls)
        if not cls:
            r["err"] = "无分类"
            return r

        # 2 列表（取第一个分类）
        tid = cls[0]["type_id"]
        got = None
        for c in cls[:3]:
            cr = sp.categoryContent(c["type_id"], "1", True, {})
            if cr.get("list"):
                got = cr["list"]
                tid = c["type_id"]
                break
        r["list"] = len(got or [])
        if not got:
            r["err"] = "列表空"
            return r
        r["sample"] = json.dumps(got[0], ensure_ascii=False)[:220]

        if not deep:
            return r

        # 3 详情
        vid = got[0].get("vod_id")
        d = sp.detailContent([vid])
        dl = d.get("list") or []
        r["detail"] = len(dl)
        if dl:
            pu = dl[0].get("vod_play_url") or ""
            r["play_url"] = pu[:160]

        # 4 播放
        if pu:
            first = pu.split("#")[0]
            pid = first.split("$", 1)[1] if "$" in first else first
            pc = sp.playerContent("", pid, "")
            if pc.get("url"):
                r["play"] = 1
                if not r["play_url"]:
                    r["play_url"] = str(pc["url"])[:160]
        return r
    except Exception as e:
        r["err"] = "%s: %s" % (type(e).__name__, e)
        r["tb"] = traceback.format_exc()[-400:]
        return r


if __name__ == "__main__":
    keys = sys.argv[1:] or ["hdb", "mmav", "rryy", "one"]
    print("%-6s %-6s %-6s %-7s %-5s %s" % ("key", "分类", "列表", "详情", "播放", "备注"))
    print("-" * 92)
    rows = []
    for k in keys:
        r = probe(k)
        okc = "✓" if r["class"] else "-"
        okl = "✓" if r["list"] else "-"
        okd = "✓" if r["detail"] else "-"
        okp = "✓" if r["play"] else "-"
        print("%-6s %-6s %-6s %-7s %-5s %s" %
              (k, "%s%d" % (okc, r["class"]), "%s%d" % (okl, r["list"]),
               "%s%d" % (okd, r["detail"]), okp, r["err"][:34]))
        rows.append(r)
    print("-" * 92)
    for r in rows:
        if r.get("sample"):
            print("\n[%s] 样本: %s" % (r["key"], r["sample"]))
        if r.get("play_url"):
            print("[%s] 播放: %s" % (r["key"], r["play_url"]))
        if r.get("tb"):
            print("[%s] 异常尾部:\n%s" % (r["key"], r["tb"]))
    with open(os.path.join(HERE, "_dec", "standalone_smoke.json"), "w", encoding="utf-8") as f:
        json.dump(rows, f, ensure_ascii=False, indent=1)
