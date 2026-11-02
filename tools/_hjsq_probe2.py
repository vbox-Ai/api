# -*- coding: utf-8 -*-
"""hjsq 第二轮：详情 / 播放解析 / 视频列表 / 节点树 探测，结果落盘 UTF-8"""
import json
import os
import sys

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
        return st, {"_raw": raw.decode("utf-8", "replace")[:400], "_status": st}


report = {}

# --- 1. 详情：从搜索拿到的 topicId 2305227
st, j = getj("api2/topic/2305227")
report["detail_2305227"] = {"status": st, "errorCode": j.get("errorCode"),
                            "top_keys": sorted((j.get("data") or {}).keys()) if isinstance(j.get("data"), dict) else None}
save("hjsq_topic_detail.json", j)

d = j.get("data") or {}
atts = d.get("attachments") or []
report["detail.attachments_count"] = len(atts)
if atts:
    a0 = atts[0]
    report["detail.attachment0"] = a0
    # 记录所有附件的关键字段
    report["detail.attachment_fields"] = [
        {"id": a.get("id"), "category": a.get("category"),
         "remoteUrl": (a.get("remoteUrl") or "")[:120],
         "coverUrl": (a.get("coverUrl") or "")[:120]} for a in atts[:5]
    ]
report["detail.hasVideo"] = d.get("hasVideo")
report["detail.content_types"] = [c.get("type") for c in (d.get("content") or [])][:20]
report["detail.doors"] = d.get("doors")

# --- 2. 播放解析 POST api2/attachment
if atts:
    aid = atts[0].get("id")
    for rt in ("1", "2", "0"):
        body = {"id": aid, "resource_type": rt, "resource_id": d.get("topicId")}
        st2, j2 = getj("api2/attachment", "POST", body)
        report["attachment_POST_rt%s" % rt] = {"status": st2,
                                               "errorCode": j2.get("errorCode"),
                                               "message": j2.get("message"),
                                               "response": j2.get("response") or j2.get("data")}
        if j2.get("errorCode") == 0:
            save("hjsq_attachment_ok.json", j2)
            break

# --- 3. 视频列表参数变体
variants = [
    "api2/video/node_list?pageIndex=1&type=0&orderType=0",
    "api2/video/node_list?pageIndex=1&type=1&orderType=0",
    "api2/video/node_list?pageIndex=1&type=0&orderType=1",
    "api2/video/node_list?pageIndex=1&type=2&orderType=2",
    "api2/video/node_list?pageIndex=0&type=1&orderType=1",
]
report["video_node_list"] = {}
for v in variants:
    st3, j3 = getj(v)
    report["video_node_list"][v.split("?")[1]] = {
        "status": st3, "errorCode": j3.get("errorCode"),
        "message": j3.get("message"),
        "n": (len(j3["data"]) if isinstance(j3.get("data"), list)
              else (len((j3.get("data") or {}).get("results") or []) if isinstance(j3.get("data"), dict) else None)),
    }

# --- 4. 节点树候选端点
cands = [
    "api2/topic/node/list", "api2/node/list", "api2/topic/nodes",
    "api2/node/nodeList", "api2/topic/node/all", "api2/topic/node/info",
    "api2/topic/node/parent", "api2/forum/node_list",
]
report["node_list_candidates"] = {}
for c in cands:
    st4, j4 = getj(c)
    report["node_list_candidates"][c] = {
        "status": st4, "errorCode": j4.get("errorCode"),
        "message": (j4.get("message") or "")[:60],
        "has_data": j4.get("data") is not None,
    }

# --- 5. 分页上限 / 其它 type 值
for t in ("1", "3", "7"):
    st5, j5 = getj("api2/topic/node/topics?page=1&type=%s" % t)
    dd = j5.get("data") or {}
    report["topic_type_%s" % t] = {"errorCode": j5.get("errorCode"),
                                   "page": dd.get("page"),
                                   "n": len(dd.get("results") or [])}

save("hjsq_probe2_report.json", report)
print(json.dumps(report, ensure_ascii=False, indent=1))
