# -*- coding: utf-8 -*-
"""mmav 端到端验证：分类 → 列表 → 详情 → 播放直链可播。"""
import importlib.util
import os
import subprocess
import sys
import traceback

sys.stdout.reconfigure(encoding="utf-8")
REPO = r"C:\Users\Administrator\Downloads\vboxapp\_remote_api"
P = os.path.join(REPO, "sources", "welfare-js", "muse_avbox.py")

spec = importlib.util.spec_from_file_location("muse_avbox", P)
m = importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)

CURL = r"C:\Windows\System32\curl.exe"


def head(url):
    cmd = [CURL, "-s", "-o", "NUL", "-w", "%{http_code}|%{content_type}|%{size_download}",
           "--max-time", "20", "-k", "-H", "User-Agent: okhttp/4.9.0", url]
    r = subprocess.run(cmd, capture_output=True, timeout=35)
    return r.stdout.decode("utf-8", "replace").strip()


def main():
    sp = m.Spider()
    a = m.MmavAdapter(sp)

    print("=== 配置域名 ===")
    print("  封面:", a._img_base())
    print("  播放:", a._video_base())
    print()

    print("=== 分类 ===")
    cats = a.categories()
    print("  一级分类 %d 个" % len(cats))

    print("\n=== 列表 ===")
    items = a.list("mmav_7", 1)
    print("  %d 条" % len(items))
    if not items:
        return
    it = items[0]
    print("  ", it["vod_id"], str(it["vod_name"])[:30])
    print("  封面:", it["vod_pic"][:80])
    print("  封面可达:", head(it["vod_pic"]))

    print("\n=== 详情 ===")
    print("  ", a.detail(it["vod_id"]))

    print("\n=== 播放 ===")
    p = a.play(it["vod_id"])
    print("  url:", p["url"][:110], "...")
    print("  可达:", head(p["url"]))

    print("\n=== 翻页 ===")
    for pg in (1, 2, 3):
        print("  page %d: %d 条" % (pg, len(a.list("mmav_7", pg))))

    print("\n=== 其它分类 ===")
    for cid in ("9", "12", "3", "4"):
        try:
            n = len(a.list("mmav_" + cid, 1))
            print("  cid=%-3s %d 条" % (cid, n))
        except Exception as e:
            print("  cid=%-3s 异常 %s" % (cid, str(e)[:50]))


if __name__ == "__main__":
    try:
        main()
    except Exception:
        traceback.print_exc()
