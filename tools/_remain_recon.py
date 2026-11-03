# -*- coding: utf-8 -*-
"""剩余平台批量可攻性筛查：asm 接口路径 + host 实测"""
import json
import os
import re
import urllib.error
import urllib.request

ASM = r"C:\Users\Administrator\Downloads\DPK\_apk\blutter_out\asm\avbox\module"
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, "tools", "_dec")
os.makedirs(OUT, exist_ok=True)

# 尚未平铺的平台 + 已知 host
PLATS = {
    "aijav": "https://newavapi.9xyrp3kg4b86.com",
    "akmh": "https://www.18akmanhua.com",
    "cgw": "https://h96h69.com",
    "djr": "https://tokyohot-api-bo92ps.mtqztc.com",
    "fl2": "https://prja.website",
    "hgsp": "https://api55.nmrgqb.com",
    "hhlz": "https://snen24.com",
    "hxsp": "https://hxapi.ruueyek.com",
    "insav": "https://snen24.com",
    "javdb": "https://jdforrepam.com",
    "jmtt": "https://jdforrepam.com",
    "live": "http://api.hclyz.com:81",
    "lxs": "https://api.hichatapi.info",
    "mdtv": "https://spi.d5c4a712.com",
    "mmmh": "https://public.mino02.live",
    "mw": "https://manwaqr.cc",
    "qysq": "https://d1kmvkv4iwtiup.cloudfront.net",
    "txvlog": "https://api.0xyhxyky2v099lb9.com".replace("0xyhxy", "0yhxy"),
    "zlt": "https://apjk85sd.q2ngx58.com",
    "4hu": "https://h96h69.com",
    "51cg": "https://h96h69.com",
    "91av": "https://api3.lmqtqhiho.cc",
    "91pron": "https://we.killcovid2020.com",
}
OP = urllib.request.build_opener(urllib.request.ProxyHandler({}))
UA = "okhttp/3.14.9"


def paths_of(key):
    d = os.path.join(ASM, key)
    if not os.path.isdir(d):
        return None
    ps = set()
    for root, _, files in os.walk(d):
        for fn in files:
            if not fn.endswith(".dart"):
                continue
            t = open(os.path.join(root, fn), encoding="utf-8", errors="ignore").read()
            for m in re.finditer(r'r(?:16|\d)? = "([a-zA-Z0-9_\-/\.\?=&]{4,60})"', t):
                s = m.group(1)
                if "/" in s and not s.startswith(("package:", "lib:", "/module/")) \
                        and not s.endswith(".dart") and not s.endswith((".png", ".jpg", ".css", ".js")):
                    ps.add(s)
    return sorted(ps)[:20]


def probe(url):
    try:
        req = urllib.request.Request(url, headers={"User-Agent": UA,
                                                  "Accept": "application/json,text/html,*/*"})
        with OP.open(req, timeout=15) as r:
            b = r.read(200)
            return r.status, (r.headers.get("Content-Type") or "")[:26], b[:90]
    except urllib.error.HTTPError as e:
        try:
            b = e.read(120)
        except Exception:
            b = b""
        return e.code, (e.headers.get("Content-Type") or "")[:26] if e.headers else "", b
    except Exception as e:
        return 0, type(e).__name__, b""


rows = []
for key, host in PLATS.items():
    ps = paths_of(key)
    st, ct, head = probe(host)
    rows.append({"key": key, "host": host, "asm": ps is not None, "paths": ps or [],
                 "status": st, "ctype": ct,
                 "head": head.decode("utf-8", "replace").replace("\n", " ")[:70]})
    print("%-7s asm=%-5s host=%-42s %-4s %-24s %s" %
          (key, "有" if ps is not None else "无", host[:42], st, ct,
           (head.decode("utf-8", "replace").replace("\n", " ")[:40])))

json.dump(rows, open(os.path.join(OUT, "remain_recon.json"), "w", encoding="utf-8"),
          ensure_ascii=False, indent=1)

print("\n=== 有 asm 且 host 活着（优先攻）===")
for r in rows:
    if r["asm"] and r["status"] in (200, 403, 418, 404):
        print("  %-7s %s" % (r["key"], r["paths"][:8]))
print("\n=== host 不可达（先搁置）===")
print("  ", [r["key"] for r in rows if r["status"] == 0])
