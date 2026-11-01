# -*- coding: utf-8 -*-
"""连通性核验：对 splash 下发的 host 逐一探测，区分
  - 可直连（国内）
  - 需代理
  - 不可达（域名已死）
并识别哪些是「配置文件 URL」而非 API 根域名。"""
import concurrent.futures as cf
import json
import os
import subprocess
import sys

sys.stdout.reconfigure(encoding="utf-8")
REPO = r"C:\Users\Administrator\Downloads\vboxapp\_remote_api"
CURL = r"C:\Windows\System32\curl.exe"
PROXY = "http://127.0.0.1:7890"

# 已知是配置文件/媒体资源，不是 API 根域名
CONFIG_LIKE = {"fl2", "mmmh"}
MEDIA_LIKE = {"hdb_img", "insav_img", "kpsp_media", "one_img", "one_video",
              "4hu_video", "jpys_img", "asgj", "live1", "live2", "adsterra"}


def probe(name, host, use_proxy):
    cmd = [CURL, "-s", "-o", "NUL", "-w", "%{http_code}|%{time_total}",
           "--max-time", "12", "-A", "Mozilla/5.0", host]
    if use_proxy:
        cmd += ["--proxy", PROXY]
    try:
        p = subprocess.run(cmd, capture_output=True, timeout=20)
        out = p.stdout.decode("utf-8", "replace").strip()
        code, _, t = out.partition("|")
        return name, host, use_proxy, code, t
    except Exception as e:
        return name, host, use_proxy, "ERR", str(e)[:40]


def main():
    s = json.load(open(os.path.join(REPO, "tools", "_dec", "box_api_splash.json"), encoding="utf-8"))
    hosts = [(h["name"], h["host"]) for h in s["data"]["host"]]

    rows = []
    with cf.ThreadPoolExecutor(max_workers=10) as ex:
        futs = []
        for n, h in hosts:
            futs.append(ex.submit(probe, n, h, False))
        for f in cf.as_completed(futs):
            rows.append(f.result())

    direct_ok = {r[0] for r in rows if r[3] not in ("000", "ERR")}
    need = [(r[0], r[1]) for r in rows if r[0] not in direct_ok]

    rows2 = []
    if need:
        with cf.ThreadPoolExecutor(max_workers=10) as ex:
            futs = [ex.submit(probe, n, h, True) for n, h in need]
            for f in cf.as_completed(futs):
                rows2.append(f.result())

    status = {}
    for n, h, _px, code, t in rows:
        status[n] = ("直连", code)
    for n, h, _px, code, t in rows2:
        if code not in ("000", "ERR"):
            status[n] = ("需代理", code)
        else:
            status[n] = ("不可达", code)

    print("%-12s %-6s %-8s %s" % ("key", "状态", "HTTP", "类型"))
    print("-" * 90)
    for n, h in hosts:
        kind = "配置URL" if n in CONFIG_LIKE else ("媒体" if n in MEDIA_LIKE else "API")
        st, code = status.get(n, ("?", "?"))
        print("%-12s %-6s %-8s %-6s %s" % (n, st, code, kind, h))

    print()
    print("统计：直连 %d / 需代理 %d / 不可达 %d" % (
        sum(1 for v in status.values() if v[0] == "直连"),
        sum(1 for v in status.values() if v[0] == "需代理"),
        sum(1 for v in status.values() if v[0] == "不可达")))


if __name__ == "__main__":
    main()
