import json, importlib.util, sys
spec = importlib.util.spec_from_file_location("r3", "tools/_aijav_r3.py")
# 复用 r3 里的 call（避免重复粘贴）
src = open("tools/_aijav_r3.py", encoding="utf-8").read()
src = src.split('print("== 空参试探')[0]
ns = {}
exec(compile(src, "r3", "exec"), ns)
call = ns["call"]
j = json.load(open("tools/_dec/aijav_probe.json", encoding="utf-8"))
items = j["home"]["data"]["data"]
cand = [x for x in items if x.get("private") == 3][:3] + [x for x in items if x.get("private") == 2][:2]
for it in cand:
    r = call("video/info", {"vid": it["id"]})
    d = r.get("data") or {}
    keys = sorted(d.keys()) if isinstance(d, dict) else []
    print(it["id"], "private=%s" % it.get("private"), "code=%s" % r.get("code"),
          "有 m3u8_url=%s" % ("m3u8_url" in d), "点数=%s" % d.get("video_point"),
          "| keys 数=%d" % len(keys))
