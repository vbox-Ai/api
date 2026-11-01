# -*- coding: utf-8 -*-
"""打印 hdb 的完整错误响应，定位 41000 的含义。"""
import importlib.util
import json
import os
import sys

sys.stdout.reconfigure(encoding="utf-8")
REPO = r"C:\Users\Administrator\Downloads\vboxapp\_remote_api"
P = os.path.join(REPO, "sources", "welfare-js", "muse_avbox.py")

spec = importlib.util.spec_from_file_location("muse_avbox", P)
m = importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)

sp = m.Spider()


def main():
    a = m.HdbAdapter(sp)

    cases = [
        ("dailyList 原参数", "pwa/v2_0/dailyList",
         {"page": 1, "length": 20, "country": -2, "censorship_type": 0}),
        ("dailyList 加 date", "pwa/v2_0/dailyList",
         {"page": 1, "length": 20, "country": -2, "censorship_type": 0,
          "date": __import__("datetime").date.today().isoformat()}),
        ("dailyList 空参", "pwa/v2_0/dailyList", {}),
        ("searchV21List", "pwa/v2_0/searchV21List",
         {"type": 4, "word": "test", "classification_id": ""}),
    ]
    for tag, path, params in cases:
        try:
            r = a._post(path, params)
            print("=== %s ===" % tag)
            print("  ", json.dumps(r, ensure_ascii=False)[:500] if r else "<None>")
        except Exception as e:
            print("=== %s === 异常: %s" % (tag, str(e)[:100]))
        print()


if __name__ == "__main__":
    main()
