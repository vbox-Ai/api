# -*- coding: utf-8 -*-
"""真实网络冒烟：对已适配平台（one / hdb / rryy）实际请求一次，确认数据链路未被打断。"""
import importlib.util
import os
import sys
import traceback

sys.stdout.reconfigure(encoding="utf-8")
REPO = r"C:\Users\Administrator\Downloads\vboxapp\_remote_api"
P = os.path.join(REPO, "sources", "welfare-js", "muse_avbox.py")

spec = importlib.util.spec_from_file_location("muse_avbox", P)
m = importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)

sp = m.Spider()


def run(key, cls):
    print("=" * 60)
    print("[%s] %s" % (key, cls.__name__))
    try:
        a = cls(sp)
        cats = a.categories()
        print("  分类: %d 个" % len(cats))
        for c in cats[:3]:
            print("    ", c.get("type_id"), c.get("type_name"))
        if cats:
            tid = cats[0].get("type_id")
            items = a.list(tid, 1)
            print("  列表[%s]: %d 条" % (tid, len(items)))
            for it in items[:3]:
                print("    ", str(it.get("vod_name"))[:40], "|", str(it.get("vod_id")))
    except Exception:
        print("  FAILED:")
        traceback.print_exc()


if __name__ == "__main__":
    for key, cls in (("one", m.OneAdapter), ("hdb", m.HdbAdapter), ("rryy", m.RryyAdapter)):
        run(key, cls)
