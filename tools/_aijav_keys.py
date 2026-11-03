import json, itertools
# 直接看 aijav 列表项里所有键，找有没有播放相关字段
j = json.load(open("tools/_dec/aijav_probe.json", encoding="utf-8"))
it = j["home"]["data"]["data"][0]
print(sorted(it.keys()))
print("private=%s play=%s video_point=%s is_purchase=%s" % (it.get("private"), it.get("play"), it.get("video_point"), it.get("is_purchase")))
for k, v in it.items():
    if isinstance(v, str) and ("http" in v or "/" in v):
        print(k, "=", v)
