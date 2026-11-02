# -*- coding: utf-8 -*-
"""mmav 播放直链拼接验证。

video_url = /common/msdl//xxx/hls/1/index.m3u8 （相对路径）
候选前缀（config 里的媒体域名）：
  image_domain = https://wzzqlm.erbaiwulaoge.com
  m3u8_host_encrypt = https://cf-worker-r2.mtzionhub.com
  static_host = https://dxj4su.e36cxt7p.com/public/1
  topic_playdomain = https://m3m.1vkx.cn/
"""
import subprocess
import sys

sys.path.insert(0, r"C:\Users\Administrator\Downloads\vboxapp\_remote_api\tools")
from _mmav_dec import fetch_decoded  # noqa: E402

sys.stdout.reconfigure(encoding="utf-8")

CURL = r"C:\Windows\System32\curl.exe"
PROXY = "http://127.0.0.1:7890"

CANDIDATES = [
    "https://wzzqlm.erbaiwulaoge.com",
    "https://cf-worker-r2.mtzionhub.com",
    "https://dxj4su.e36cxt7p.com/public/1",
    "https://m3m.1vkx.cn",
    "https://bvbvbvssu.a63qv1sy.com",
]


def probe(url, proxy=False, timeout=15):
    cmd = [CURL, "-s", "-o", "NUL", "-w", "%{http_code}|%{content_type}",
           "--max-time", str(timeout), "-k",
           "-H", "User-Agent: okhttp/4.9.0", url]
    if proxy:
        cmd += ["--proxy", PROXY]
    r = subprocess.run(cmd, capture_output=True, timeout=timeout + 10)
    return r.stdout.decode("utf-8", "replace").strip()


if __name__ == "__main__":
    res = fetch_decoded("data/mediaVideo/list-7-1-50.js")
    data = (res.get("list") or {}).get("data") or []
    if not data:
        print("无数据")
        sys.exit(1)
    vurl = data[0]["video_url"]
    cover = data[0]["cover"]
    print("video_url:", vurl)
    print("cover:", cover)
    print()

    print("=== m3u8 各域名前缀 ===")
    for base in CANDIDATES:
        url = base + vurl
        print("  %-48s -> %s" % (base, probe(url)))

    print("\n=== 封面各域名前缀 ===")
    for base in CANDIDATES:
        url = base + cover
        print("  %-48s -> %s" % (base, probe(url)))
