# -*- coding: utf-8 -*-
"""wsSecret 修正版：哈希输入为 salt + uri.path + expire。

反汇编再读（call site）：
  // 0x5afaf8: mov x2, x0        → x2 = host+path（URL）
  // 0x5afafc: r1 = "D7hGKHnW..." → r1 = salt
  // 0x5afb04: wsSecret()          → wsSecret(salt, url)

函数内：
  Uri::parse(url)               ← 解析的是 URL
  expire = now + 7200
  md5( salt + uri.path + expire )
  → url?wsSecret=<md5>&wsTime=<expire>&ip=<randomIp>
"""
import hashlib
import random
import subprocess
import sys
import time
import urllib.parse

sys.path.insert(0, r"C:\Users\Administrator\Downloads\vboxapp\_remote_api\tools")
from _mmav_dec import fetch_decoded  # noqa: E402

sys.stdout.reconfigure(encoding="utf-8")

CURL = r"C:\Windows\System32\curl.exe"
PROXY = "http://127.0.0.1:7890"
SALT = "D7hGKHnWThaECaQ3ji4XyAF3MfYKJ53M"

HOSTS = [
    "https://cf-worker-r2.mtzionhub.com",
    "https://wzzqlm.erbaiwulaoge.com",
    "https://m3m.1vkx.cn",
    "https://bvbvbvssu.a63qv1sy.com",
]


def rand_ip():
    return "%d.%d.%d.%d" % (random.randint(1, 254), random.randint(0, 255),
                            random.randint(0, 255), random.randint(1, 254))


def sign(url, key=SALT, ip_mode="random"):
    expire = int(time.time()) + 7200
    path = urllib.parse.urlparse(url).path
    secret = hashlib.md5(("%s%s%d" % (key, path, expire)).encode()).hexdigest()
    ip = "0.0.0.0" if ip_mode == "zero" else rand_ip()
    return "%s?wsSecret=%s&wsTime=%d&ip=%s" % (url, secret, expire, ip)


def probe(url, proxy=False, timeout=15):
    cmd = [CURL, "-s", "-o", "NUL", "-w", "%{http_code}|%{content_type}|%{size_download}",
           "--max-time", str(timeout), "-k", "-H", "User-Agent: okhttp/4.9.0"]
    if proxy:
        cmd += ["--proxy", PROXY]
    cmd += [url]
    r = subprocess.run(cmd, capture_output=True, timeout=timeout + 10)
    return r.stdout.decode("utf-8", "replace").strip()


if __name__ == "__main__":
    res = fetch_decoded("data/mediaVideo/list-7-1-50.js")
    vurl = (res.get("list") or {}).get("data")[0]["video_url"]
    print("video_url:", vurl)
    print()

    for h in HOSTS:
        full = h + vurl
        print("=== %s ===" % h)
        print("  签名(随机IP) 直连: %s" % probe(sign(full), proxy=False))
        print("  签名(随机IP) 代理: %s" % probe(sign(full), proxy=True))
        print("  签名(0.0.0.0) 直连: %s" % probe(sign(full, ip_mode="zero"), proxy=False))
        print()
