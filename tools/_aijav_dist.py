import json
j = json.load(open("tools/_dec/aijav_probe.json", encoding="utf-8"))
items = j["home"]["data"]["data"]
from collections import Counter
print("private:", Counter(x.get("private") for x in items))
print("is_purchase:", Counter(x.get("is_purchase") for x in items))
print("video_point:", Counter(x.get("video_point") for x in items))
print("is_new:", Counter(x.get("is_new") for x in items))
for x in items[:6]:
    print(x["id"], "private=%s purchase=%s point=%s new=%s" % (x.get("private"), x.get("is_purchase"), x.get("video_point"), x.get("is_new")))
