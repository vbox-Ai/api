# -*- coding: utf-8 -*-
"""mw 漫画适配器完整链路冒烟"""
import importlib.util
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
spec = importlib.util.spec_from_file_location(
    "mw", os.path.join(ROOT, "sources", "welfare-js", "mw.py"))
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)

sp = mod.Spider()
sp.init("")

steps = []


def rec(label, ok, **kw):
    d = {"step": label, "ok": bool(ok)}
    d.update(kw)
    steps.append(d)
    print(("  [OK] " if ok else "  [FAIL] ") + label + ("  " + json.dumps(kw, ensure_ascii=False)[:170] if kw else ""))


print("=" * 72)
h = sp.homeContent(True)
cls = h.get("class") or []
rec("homeContent", len(cls) > 0, classes=len(cls),
    names=[c["type_name"] for c in cls[:6]])

got = None
for c in cls[:4]:
    r = sp.categoryContent(c["type_id"], "1", True, {})
    if r.get("list"):
        got = (c, r)
        break
rec("categoryContent", bool(got),
    tid=got[0]["type_id"] if got else None,
    n=len(got[1]["list"]) if got else 0)

if got:
    items = got[1]["list"]
    rec("cover real", bool(items) and "/upload" in (items[0].get("vod_pic") or ""),
        pic=(items[0].get("vod_pic") or "")[:80])

    # 分页
    r2 = sp.categoryContent(got[0]["type_id"], "2", True, {})
    rec("pagination", bool(r2.get("list")) and r2["list"][0]["vod_id"] != items[0]["vod_id"],
        p2_first=r2["list"][0]["vod_id"] if r2.get("list") else None)

    vid = items[0]["vod_id"]
    d = sp.detailContent([vid])
    dl = d.get("list") or []
    ok = bool(dl) and bool(dl[0].get("vod_play_url"))
    rec("detailContent", ok,
        name=(dl[0].get("vod_name") or "")[:24] if dl else None,
        chapters=len((dl[0].get("vod_play_url") or "").split("#")) if dl else 0)

    if ok:
        pu = dl[0]["vod_play_url"]
        first = pu.split("#")[0]
        # 章节格式: "标题$cid"
        cid = first.split("$")[-1]
        p = sp.playerContent("", cid, "")
        url = p.get("url") or ""
        n_img = url.count("&&") + 1 if url.startswith("manga://") else 0
        rec("playerContent(manga://)", url.startswith("manga://") and n_img > 0,
            cid=cid, images=n_img, head=url[:100])

        # 图片真可下载
        if n_img:
            first_img = url[len("manga://"):].split("&&")[0]
            try:
                import urllib.request as _u
                op = _u.build_opener(_u.ProxyHandler({}))
                rq = _u.Request(first_img, headers={"User-Agent": mod.UA,
                                                    "Referer": sp._c().host + "/"})
                with op.open(rq, timeout=20) as r:
                    b = r.read(64)
                rec("image fetch", True, status=r.status,
                    ctype=r.headers.get("Content-Type"), magic=b[:4].hex())
            except Exception as e:
                rec("image fetch", False, err=str(e)[:80])

# 搜索
try:
    s = sp.searchContent("海梦", False, "1")
    rec("searchContent", len(s.get("list") or []) > 0, n=len(s.get("list") or []))
except Exception as e:
    rec("searchContent", False, err=str(e)[:60])

print("=" * 72)
okn = sum(1 for s in steps if s["ok"])
print("PASS %d / %d" % (okn, len(steps)))
with open(os.path.join(HERE, "_dec", "mw_smoke.json"), "w", encoding="utf-8") as f:
    json.dump({"steps": steps}, f, ensure_ascii=False, indent=1)
