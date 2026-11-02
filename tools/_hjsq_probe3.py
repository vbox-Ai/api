# -*- coding: utf-8 -*-
"""hjsq 第三轮：节点树 + 视频帖播放解析 + 图片直链验证"""
import json
import os

from _hjsq_probe import call

OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "_dec")
os.makedirs(OUT, exist_ok=True)


def save(name, obj):
    p = os.path.join(OUT, name)
    with open(p, "w", encoding="utf-8") as f:
        json.dump(obj, f, ensure_ascii=False, indent=1)
    return p


def getj(path, method="GET", body=None):
    st, raw = call(path, method, body)
    try:
        return st, json.loads(raw.decode("utf-8", "replace"))
    except Exception:
        return st, {"_raw": raw.decode("utf-8", "replace")[:300], "_status": st}


rep = {}

# ---------- 1. 节点树
st, j = getj("api2/topic/nodes")
save("hjsq_nodes.json", j)
d = j.get("data")
rep["nodes"] = {"status": st, "errorCode": j.get("errorCode"),
                "type": type(d).__name__,
                "len": len(d) if isinstance(d, (list, dict)) else None}
if isinstance(d, list) and d:
    rep["nodes"][""] = None
    rep["nodes"]["first"] = d[0]
    rep["nodes"]["count_top"] = len(d)
    # 统计子节点
    def walk(ns, depth=1, acc=None):
        if acc is None:
            acc = []
        for n in ns or []:
            kids = n.get("children") or n.get("child") or n.get("nodes") or []
            acc.append({"nodeId": n.get("nodeId"), "name": n.get("name"),
                        "parentId": n.get("parentId"), "depth": depth,
                        "kids": len(kids)})
            if kids:
                walk(kids, depth + 1, acc)
        return acc
    flat = walk(d)
    rep["nodes"]["flat_count"] = len(flat)
    rep["nodes"]["sample"] = flat[:40]
elif isinstance(d, dict):
    rep["nodes"]["keys"] = sorted(d.keys())[:20]

# ---------- 2. 找一个 hasVideo=true 的帖子
cands = []
for path in ["api2/topic/node/topics?page=1&nodeId=1001&type=0",
             "api2/topic/node/topics?page=1&type=1",
             "api2/topic/node/topics?page=1&nodeId=13&type=0",
             "api2/topic/hot/topics"]:
    st2, j2 = getj(path)
    for r in ((j2.get("data") or {}).get("results") or []):
        if r.get("hasVideo"):
            cands.append({"topicId": r.get("topicId"), "title": r.get("title"),
                          "nodeId": (r.get("node") or {}).get("nodeId"),
                          "money_type": r.get("money_type"), "src": path})
    if len(cands) >= 5:
        break
rep["video_topic_candidates"] = cands[:5]

# ---------- 3. 取视频帖详情 + 播放解析
if cands:
    tid = cands[0]["topicId"]
    st3, j3 = getj("api2/topic/%s" % tid)
    save("hjsq_video_topic_%s.json" % tid, j3)
    dd = j3.get("data") or {}
    rep["video_detail"] = {
        "topicId": tid, "errorCode": j3.get("errorCode"),
        "hasVideo": dd.get("hasVideo"), "money_type": dd.get("money_type"),
        "content": [{k: (v if not isinstance(v, str) or len(v) < 140 else v[:140])
                     for k, v in c.items()} for c in (dd.get("content") or [])][:6],
        "attachments": dd.get("attachments"),
        "doors": dd.get("doors"),
    }
    for a in (dd.get("attachments") or []):
        for rt in ("1", "2", "3"):
            body = {"id": a.get("id"), "resource_type": rt, "resource_id": tid}
            st4, j4 = getj("api2/attachment", "POST", body)
            key = "POST_att%s_rt%s" % (a.get("id"), rt)
            rep[key] = {"status": st4, "errorCode": j4.get("errorCode"),
                        "message": j4.get("message"),
                        "response": j4.get("response") or j4.get("data")}
            if j4.get("errorCode") == 0:
                save("hjsq_attachment_ok.json", j4)
                break

# ---------- 4. 图片直链验证（.jpg.txt 是否可直取）
import urllib.request
op = urllib.request.build_opener(urllib.request.ProxyHandler({}))
img = "https://pic.hj260302818.top/hjstore/images/20261102/3b8756537400d11c9d4c38e5034feb5a.jpg.txt"
rep["img_probe"] = {}
for u in (img, img[:-4]):
    try:
        rq = urllib.request.Request(u, headers={"User-Agent": "okhttp/3.14.9", "Referer": "http://23.225.145.74/"})
        with op.open(rq, timeout=20) as r:
            body = r.read(32)
            rep["img_probe"][u[-20:]] = {"status": r.status,
                                         "ctype": r.headers.get("Content-Type"),
                                         "head_hex": body[:8].hex()}
    except Exception as e:
        rep["img_probe"][u[-20:]] = {"err": "%s: %s" % (type(e).__name__, e)}

save("hjsq_probe3_report.json", rep)
print(json.dumps(rep, ensure_ascii=False, indent=1)[:6000])
