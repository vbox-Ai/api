# -*- coding: utf-8 -*-
"""kpsp 标签索引：拉全量 6628 个标签，建立 name→id 映射，导出常用分类"""
import json
import os

from _kpsp_probe2 import OUT, call, decrypt

WANT = ["网黄", "探花", "传媒", "吃瓜", "直播", "乱伦", "自拍",
        "偷拍", "私拍", "换脸", "泄密", "三级", "动漫", "欧美",
        "国产", "热门", "推荐", "精品", "无码", "中文字幕", "萝莉",
        "御姐", "少妇", "学生", "制服", "口交", "自慰", "群交", "3P"]

name2id = {}
id2item = {}
page = 1
total = None
while True:
    st, body = call("api/vod/tag", {"page": page, "per_page": 500})
    try:
        w = json.loads(body.decode("utf-8"))
        d = json.loads(decrypt(w["x-data"])[0].decode("utf-8")).get("data") or {}
    except Exception as e:
        print("page %d 失败 %s" % (page, e))
        break
    items = d.get("items") or []
    meta = {k: v for k, v in d.items() if k != "items"}
    total = meta.get("total")
    for it in items:
        nm = it.get("name")
        tid = it.get("id")
        if nm and tid is not None:
            id2item[tid] = it
            name2id.setdefault(nm, tid)
    print("page %-3d 累计 %d / %s" % (page, len(id2item), total))
    if not items or (meta.get("page") or 1) >= (meta.get("pages") or 1):
        break
    page += 1

print("\n标签总数:", len(id2item))
print("\n=== 常用分类 id ===")
hits = {}
for w in WANT:
    if w in name2id:
        hits[w] = name2id[w]
        print("  %-8s -> %-6s  %s" % (w, name2id[w], id2item[name2id[w]].get("remarks") or ""))
    else:
        print("  %-8s -> 未找到" % w)

out = {
    "total": len(id2item),
    "common": hits,
    "all": {str(k): {"name": v.get("name"), "sort": v.get("sort")}
            for k, v in sorted(id2item.items(), key=lambda x: -(x[1].get("sort") or 0))[:300]},
}
p = os.path.join(OUT, "kpsp_tag_index.json")
with open(p, "w", encoding="utf-8") as f:
    json.dump(out, f, ensure_ascii=False, indent=1)
print("\n已存:", p)
print("\n=== sort 最高 30 个（做默认分类用）===")
top = sorted(id2item.items(), key=lambda x: -(x[1].get("sort") or 0))[:30]
print([(k, v.get("name")) for k, v in top])
