# -*- coding: utf-8 -*-
"""kpsp 适配器冒烟测试"""
import importlib.util
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, ROOT)

spec = importlib.util.spec_from_file_location(
    "kpsp", os.path.join(ROOT, "sources", "welfare-js", "kpsp.py"))
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)

sp = mod.Spider()
sp.init("")

steps = []


def rec(label, ok, **kw):
    d = {"step": label, "ok": bool(ok)}
    d.update(kw)
    steps.append(d)
    print(("  [OK] " if ok else "  [FAIL] ") + label)


print("=" * 72)
print("1) homeContent")
h = sp.homeContent(True)
cls = h.get("class") or []
rec("homeContent", len(cls) > 15, classes=len(cls))
print("   前 10:", [(c["type_id"], c["type_name"]) for c in cls[:10]])

print("2) categoryContent")
for tid in ["all", "2194", "407", "300"]:
    r = sp.categoryContent(tid, "1", True, {})
    n = len(r.get("list") or [])
    rec("category tid=%s" % tid, n > 0, n=n, total=r.get("total"))
    if tid == "all" and r.get("list"):
        print("   样本:", json.dumps(r["list"][0], ensure_ascii=False)[:260])

print("3) 分页 / 标签隔离")
a = sp.categoryContent("all", "1", True, {})
b = sp.categoryContent("all", "2", True, {})
ia = (a.get("list") or [{}])[0].get("vod_id")
ib = (b.get("list") or [{}])[0].get("vod_id")
rec("pagination", ia != ib, p1=ia, p2=ib)
t1 = sp.categoryContent("407", "1", True, {})
ta = (t1.get("list") or [{}])[0].get("vod_id")
# 判据：total 或首条任一不同即证明 tag 过滤生效
# （407 首条恰好与全站首条同片，但 total 115048 → 1623 已明显收窄）
rec("tag isolation", (t1.get("total") != a.get("total")) or (ta != ia),
    tag407_first=ta, all_first=ia,
    tag_total=t1.get("total"), all_total=a.get("total"))

print("4) detailContent")
vid = ia
d = sp.detailContent([vid])
lst = d.get("list") or []
ok = bool(lst) and bool((lst[0] or {}).get("vod_play_url"))
info = {}
if lst:
    v = lst[0]
    info = {"name": (v.get("vod_name") or "")[:34],
            "play": (v.get("vod_play_url") or "")[:150],
            "pic": (v.get("vod_pic") or "")[:90],
            "content_len": len(v.get("vod_content") or "")}
rec("detail %s" % vid, ok, **info)

print("5) searchContent")
s = sp.searchContent("偷拍", False, "1")
rec("search", len(s.get("list") or []) > 0, n=len(s.get("list") or []),
    total=s.get("total"))

print("6) 播放链路")
if lst:
    pu = (lst[0].get("vod_play_url") or "").split("#")[0]
    url = pu.split("$", 1)[1] if "$" in pu else ""
    pc = sp.playerContent("", url, "")
    is_m3u8 = ".m3u8" in (pc.get("url") or "")
    rec("playerContent", is_m3u8, parse=pc.get("parse"), url=(pc.get("url") or "")[:110])
    if is_m3u8:
        try:
            import re as _re
            import urllib.request as _u
            op = _u.build_opener(_u.ProxyHandler({}))
            rq = _u.Request(pc["url"], headers={"User-Agent": mod.UA,
                                                "Referer": sp.media + "/"})
            with op.open(rq, timeout=25) as r:
                m = r.read().decode("utf-8", "replace")
            segs = [l for l in m.splitlines() if l and not l.startswith("#")]
            kline = [l for l in m.splitlines() if "EXT-X-KEY" in l]
            ku = _re.search(r'URI="([^"]+)"', kline[0]).group(1) if kline else ""
            base = pc["url"].rsplit("/", 1)[0] + "/"
            kb = b""
            if ku:
                rq2 = _u.Request(base + ku, headers={"User-Agent": mod.UA})
                with op.open(rq2, timeout=20) as r:
                    kb = r.read()
            rec("HLS+AES key", bool(kb) and len(kb) == 16,
                segs=len(segs), key_hex=kb.hex(), key_len=len(kb))
        except Exception as e:
            rec("HLS+AES key", False, err=str(e))

print("7) 封面可取")
try:
    import urllib.request as _u
    op = _u.build_opener(_u.ProxyHandler({}))
    pic = (lst[0].get("vod_pic") or "") if lst else ""
    if pic:
        rq = _u.Request(pic, headers={"User-Agent": mod.UA})
        with op.open(rq, timeout=20) as r:
            b = r.read(16)
            full = r.read(0)
        rec("cover fetch", True, status=r.status, magic=b[:4].hex(),
            ctype=r.headers.get("Content-Type"))
    else:
        rec("cover fetch", False, note="无封面")
except Exception as e:
    rec("cover fetch", False, err=str(e))

print("=" * 72)
okn = sum(1 for s in steps if s["ok"])
print("PASS %d / %d" % (okn, len(steps)))
with open(os.path.join(HERE, "_dec", "kpsp_smoke.json"), "w", encoding="utf-8") as f:
    json.dump({"steps": steps}, f, ensure_ascii=False, indent=1)
