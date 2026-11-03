# -*- coding: utf-8 -*-
"""剩余 21 平台：最新可达性 + asm 接口重扫（含多候选域）"""
import json
import os
import re
import socket
import urllib.error
import urllib.request

ASM = r"C:\Users\Administrator\Downloads\DPK\_apk\blutter_out\asm\avbox\module"
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, "tools", "_dec")
os.makedirs(OUT, exist_ok=True)
OP = urllib.request.build_opener(urllib.request.ProxyHandler({}))
UA_IOS = ("Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) "
          "AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Mobile/15E148 Safari/604.1")

# 剩余平台（排除 live：用户已要求移除）
PLATS = {
    "aijav": ["https://newavapi.9xyrp3kg4b86.com"],
    "akmh": ["https://www.18akmanhua.com"],
    "cgw": ["https://h96h69.com"],
    "djr": ["https://tokyohot-api-bo92ps.mtqztc.com"],
    "fl2": ["https://prja.website"],
    "hgsp": ["https://api55.nmrgqb.com"],
    "hhlz": ["https://snen24.com"],
    "hxsp": ["https://hxapi.ruueyek.com"],
    "insav": ["https://snen24.com"],
    "javdb": ["https://jdforrepam.com"],
    "jmtt": ["https://jdforrepam.com"],
    "lxs": ["https://api.hichatapi.info"],
    "mdtv": ["https://spi.d5c4a712.com"],
    "qysq": ["https://d1kmvkv4iwtiup.cloudfront.net"],
    "txvlog": ["https://api.0yhxyky2v099lb9.com"],
    "zlt": ["https://apjk85sd.q2ngx58.com"],
    "4hu": ["https://h96h69.com"],
    "51cg": ["https://h96h69.com"],
    "91av": ["https://api3.lmqtqhiho.cc"],
    "91pron": ["https://we.killcovid2020.com"],
}


def dns(host):
    h = re.sub(r"^https?://", "", host).split("/")[0].split(":")[0]
    try:
        ip = socket.gethostbyname(h)
        return ip
    except Exception:
        return ""


def probe(url):
    try:
        req = urllib.request.Request(url, headers={
            "User-Agent": UA_IOS, "Accept": "application/json,text/html,*/*"})
        with OP.open(req, timeout=12) as r:
            b = r.read(200)
            return r.status, (r.headers.get("Content-Type") or "")[:24], b[:60]
    except urllib.error.HTTPError as e:
        try:
            b = e.read(120)
        except Exception:
            b = b""
        return e.code, (e.headers.get("Content-Type") or "")[:24] if e.headers else "", b
    except Exception as e:
        return 0, type(e).__name__, b""


def asm_paths(key):
    d = os.path.join(ASM, key)
    if not os.path.isdir(d):
        return None
    ps = set()
    for root, _, files in os.walk(d):
        for fn in files:
            if not fn.endswith(".dart"):
                continue
            t = open(os.path.join(root, fn), encoding="utf-8", errors="ignore").read()
            for m in re.finditer(r'r(?:16|\d)? = "([a-zA-Z0-9_\-/\.\?=&]{4,70})"', t):
                s = m.group(1)
                if "/" in s and not s.startswith(("package:", "lib:", "/module/")) \
                        and not s.endswith((".dart", ".png", ".jpg", ".css", ".js", ".svg")):
                    ps.add(s)
    return sorted(ps)[:16]


rows = []
print("%-7s %-15s %-42s %-5s %-18s %s" % ("key", "DNS", "host", "状态", "ctype", "asm"))
print("-" * 118)
for key, hosts in PLATS.items():
    host = hosts[0]
    ip = dns(host)
    st, ct, head = probe(host)
    ps = asm_paths(key)
    rows.append({"key": key, "host": host, "ip": ip, "status": st, "ctype": ct,
                 "head": head.decode("utf-8", "replace").replace("\n", " ")[:50],
                 "asm": ps is not None, "paths": ps or []})
    print("%-7s %-15s %-42s %-5s %-18s %s" % (
        key, ip or "无解析", host[:42], st, ct,
        ("有 %d" % len(ps)) if ps else "无"))

json.dump(rows, open(os.path.join(OUT, "remain21.json"), "w", encoding="utf-8"),
          ensure_ascii=False, indent=1)

print("\n=== 汇总 ===")
alive = [r for r in rows if r["status"] in (200, 201, 400, 401, 403, 404, 418, 500)]
dead = [r for r in rows if r["status"] == 0]
print("可达 %d: %s" % (len(alive), [r["key"] for r in alive]))
print("不可达 %d: %s" % (len(dead), [r["key"] for r in dead]))
print("\n有 asm 且可达（优先攻）:")
for r in rows:
    if r["asm"] and r["status"] != 0:
        print("  %-7s %s" % (r["key"], r["paths"][:8]))
