# -*- coding: utf-8 -*-
import json
import os

ROOT = r"C:\Users\Administrator\Downloads\vboxapp\_remote_api\sources"
for f, path in [("welfare_platforms.json", ["platforms"]),
                ("all_sources.json", ["welfarePlatforms", "platforms"])]:
    d = json.load(open(os.path.join(ROOT, f), encoding="utf-8"))
    x = d
    for k in path:
        x = x[k]
    hit = [e for e in x if e.get("platformKey") == "hjsq_py"]
    print("%-24s 条目=%d  hjsq_py=%d" % (f, len(x), len(hit)))
    if hit:
        print("   api=%s  sortOrder=%s  name=%s" % (
            hit[0]["api"], hit[0]["sortOrder"], hit[0]["name"]))
