# -*- coding: utf-8 -*-
"""hdb date 参数探测：验证「当天无数据、往前推有数据」，
确定适配器应如何选取 date。"""
import datetime
import importlib.util
import json
import os
import sys
import time

sys.stdout.reconfigure(encoding="utf-8")
REPO = r"C:\Users\Administrator\Downloads\vboxapp\_remote_api"
P = os.path.join(REPO, "sources", "welfare-js", "muse_avbox.py")

spec = importlib.util.spec_from_file_location("muse_avbox", P)
m = importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)

sp = m.Spider()


def main():
    a = m.HdbAdapter(sp)
    today = datetime.date.today()

    for back in range(0, 8):
        d = (today - datetime.timedelta(days=back)).isoformat()
        params = {"page": 1, "length": 20, "country": -2,
                  "censorship_type": 0, "date": d}
        try:
            r = a._post("pwa/v2_0/dailyList", params)
            data = (r or {}).get("data") or {}
            n = len(data.get("list") or [])
            print("  %s  code=%-4s items=%-3d total=%s update_num=%s" % (
                d, (r or {}).get("code"), n,
                data.get("totalPage"), data.get("update_num")))
        except Exception as e:
            print("  %s  异常 %s" % (d, str(e)[:60]))
        time.sleep(2)


if __name__ == "__main__":
    main()
