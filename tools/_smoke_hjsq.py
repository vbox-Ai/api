# -*- coding: utf-8 -*-
"""hjsq 适配器冒烟测试：homeContent / categoryContent / detailContent /
   searchContent / playerContent / localProxy 全链路"""
import importlib.util
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, ROOT)

spec = importlib.util.spec_from_file_location(
    "hjsq", os.path.join(ROOT, "sources", "welfare-js", "hjsq.py"))
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)

sp = mod.Spider()
sp.init("")

out = {"steps": []}


def rec(label, ok, /, **kw):
    d = {"step": label, "ok": bool(ok)}
    d.update(kw)
    out["steps"].append(d)
    print(("  [OK] " if ok else "  [FAIL] ") + label)
    return d


print("=" * 70)
print("1) homeContent")
h = sp.homeContent(True)
classes = h.get("class") or []
rec("homeContent", len(classes) > 0,
    classes=len(classes), with_filters=len(h.get("filters") or {}))
print("   前 12 个分类:", [(c["type_id"], c["type_name"]) for c in classes[:12]])

print("2) categoryContent")
tests = [("hot", 1), ("news", 1), ("new", 1), ("cream", 1), ("original", 1)]
num_tid = next((c["type_id"] for c in classes
                if str(c["type_id"]).isdigit()), None)
if num_tid:
    tests.append((num_tid, 1))
    tests.append((num_tid, 2))

first_items = {}
for tid, pg in tests:
    r = sp.categoryContent(tid, pg, True, {})
    n = len(r.get("list") or [])
    total = r.get("total") or 0
    # 平台存在真实空节点（如 900 短视频专区 total=0），空但其 total 也是 0 时视为正常
    ok = n > 0 or (total == 0)
    rec("category tid=%s pg=%s" % (tid, pg), ok, n=n, total=total, pagecount=r.get("pagecount"))
    if r.get("list"):
        first_items.setdefault(tid, r["list"][0])

# 打印一条样本
if "hot" in first_items:
    print("   hot 首条:", json.dumps(first_items["hot"], ensure_ascii=False)[:300])

print("3) 分页一致性（hot pg1 vs pg2 首条应不同）")
a = sp.categoryContent("hot", 1, True, {})
b = sp.categoryContent("hot", 2, True, {})
ia = (a.get("list") or [{}])[0].get("vod_id")
ib = (b.get("list") or [{}])[0].get("vod_id")
rec("pagination hot", ia != ib, p1=ia, p2=ib)

print("4) detailContent")
# 找一个视频帖和一个图帖
vid_id, pic_id = None, None
for it in (a.get("list") or []):
    if it.get("vod_tag") == "video" and not vid_id:
        vid_id = it["vod_id"]
    if it.get("vod_tag") == "pic" and not pic_id:
        pic_id = it["vod_id"]
if not vid_id:
    for c in sp.categoryContent(num_tid or "hot", 1, True, {}).get("list") or []:
        if c.get("vod_tag") == "video":
            vid_id = c["vod_id"]
            break
if not pic_id:
    pic_id = (a.get("list") or [{}])[0].get("vod_id")

for label, tid in (("视频帖", vid_id), ("图帖", pic_id)):
    if not tid:
        continue
    d = sp.detailContent([tid])
    lst = d.get("list") or []
    ok = bool(lst)
    info = {}
    if ok:
        v = lst[0]
        info = {"name": (v.get("vod_name") or "")[:40],
                "has_play": bool(v.get("vod_play_url")),
                "play_head": (v.get("vod_play_url") or "")[:120],
                "content_len": len(v.get("vod_content") or ""),
                "pic_head": (v.get("vod_pic") or "")[:80]}
    rec("detail %s %s" % (label, tid), ok, **info)

print("5) searchContent")
s = sp.searchContent("自拍", False, "1")
rec("search", len(s.get("list") or []) > 0, n=len(s.get("list") or []))
if s.get("list"):
    print("   搜索首条:", (s["list"][0].get("vod_name") or "")[:60])

print("6) localProxy 图片解码")
import urllib.parse as up
# 从图帖详情里找一个 .txt 图片
txt_url = None
if pic_id:
    j = sp._get("api2/topic/%s" % pic_id)
    for att in ((j.get("data") or {}).get("attachments") or []):
        if (att.get("category") or "") == "images" and (att.get("remoteUrl") or "").endswith(".txt"):
            txt_url = att["remoteUrl"]
            break
if txt_url:
    code, ctype, body, hdr = sp.localProxy({"url": txt_url})
    magic = body[:4].hex() if body else ""
    rec("localProxy decode", code == 200 and body[:3] == b"\xff\xd8\xff",
        code=code, ctype=ctype, bytes=len(body), magic=magic)
else:
    rec("localProxy decode", False, note="未找到图片附件")

print("7) playerContent")
if vid_id:
    v = sp.detailContent([vid_id]).get("list") or [{}]
    pu = (v[0].get("vod_play_url") or "")
    url = pu.split("$", 1)[1].split("#")[0] if "$" in pu else ""
    p = sp.playerContent("", url, "")
    is_m3u8 = ".m3u8" in (p.get("url") or "")
    rec("playerContent", is_m3u8, parse=p.get("parse"), url_head=(p.get("url") or "")[:100])
    if is_m3u8:
        # 验证 HLS 可拉 + AES key 可取
        try:
            m = sp._fetch_bytes(p["url"]).decode("utf-8", "replace")
            keyline = [l for l in m.splitlines() if "EXT-X-KEY" in l]
            base = p["url"].rsplit("/", 1)[0] + "/"
            import re as _re
            ku = _re.search(r'URI="([^"]+)"', keyline[0]).group(1) if keyline else ""
            kb = sp._fetch_bytes(base + ku) if ku else b""
            rec("HLS+AES key", kb and len(kb) == 16,
                segs=len([l for l in m.splitlines() if l and not l.startswith("#")]),
                key_hex=kb.hex(), key_len=len(kb))
        except Exception as e:
            rec("HLS+AES key", False, err=str(e))

print("=" * 70)
okn = sum(1 for s in out["steps"] if s["ok"])
print("PASS %d / %d" % (okn, len(out["steps"])))

with open(os.path.join(HERE, "_dec", "hjsq_smoke.json"), "w", encoding="utf-8") as f:
    json.dump(out, f, ensure_ascii=False, indent=1)
