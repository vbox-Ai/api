# -*- coding: utf-8 -*-
"""批量协议提取：对多个平台，从 blutter asm 抽接口路径/常量，并实测 host 可达性"""
import json
import os
import re
import urllib.error
import urllib.request

ASM = r"C:\Users\Administrator\Downloads\DPK\_apk\blutter_out\asm\avbox\module"
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, "tools", "_dec")
os.makedirs(OUT, exist_ok=True)

PLATS = {
    "lclf": "https://lclf.lol",
    "km": "https://icef4vn.xyz",
    "hsck": "https://hsck3.u0u0.cc",
    "mmmh": "https://public.mino02.live",
    "hhlz": "https://snen24.com",
    "javdb": "https://jdforrepam.com",
    "aijav": "https://newavapi.9xyrp3kg4b86.com",
    "insav": "https://snen24.com",
    "mdtv": "https://spi.d5c4a712.com",
    "zlt": "https://apjk85sd.q2ngx58.com",
    "txvlog": "https://api.0yhxyky2v099lb9.com",
    "qysq": "https://d1kmvkv4iwtiup.cloudfront.net",
    "fl2": "https://prja.website",
    "akmh": "https://www.18akmanhua.com",
    "jmtt": "https://jdforrepam.com",
    "lxs": "https://api.hichatapi.info",
}

# 疑似接口路径的模式
PATH_RE = re.compile(r'^[a-zA-Z0-9_\-/\.]{3,80}$')
SKIP_EXT = (".dart", ".g.dart")


def extract(key):
    d = os.path.join(ASM, key)
    if not os.path.isdir(d):
        return {"mod": False, "paths": [], "consts": [], "files": 0}
    paths, consts, nfiles = set(), set(), 0
    for root, _, files in os.walk(d):
        for fn in files:
            if not fn.endswith(".dart"):
                continue
            nfiles += 1
            txt = open(os.path.join(root, fn), encoding="utf-8", errors="ignore").read()
            for m in re.finditer(r'r\d+ = "([^"\\]{2,90})"', txt):
                s = m.group(1)
                if s.endswith(SKIP_EXT):
                    continue
                if "/" in s and PATH_RE.match(s) and not s.startswith("package:") \
                        and not s.startswith("lib:"):
                    paths.add(s)
                elif 3 <= len(s) <= 60 and re.search(r"[a-zA-Z]", s) \
                        and not re.match(r"^(loading|qp|data|code|msg|message|icon|name)$", s):
                    consts.add(s)
    return {"mod": True, "files": nfiles,
            "paths": sorted(paths)[:40],
            "consts": sorted(consts)[:40]}


def probe(url, timeout=15):
    op = urllib.request.build_opener(urllib.request.ProxyHandler({}))
    out = {}
    for tag, hdrs in (("ua_okhttp", {"User-Agent": "okhttp/3.14.9"}),
                      ("ua_ios", {"User-Agent": "Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) "
                                               "AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Mobile/15E148"})):
        try:
            req = urllib.request.Request(url, headers=hdrs)
            with op.open(req, timeout=timeout) as r:
                b = r.read(400)
                out[tag] = {"status": r.status,
                            "ctype": (r.headers.get("Content-Type") or "")[:40],
                            "head": b[:120].decode("utf-8", "replace").replace("\n", " ")[:110]}
        except urllib.error.HTTPError as e:
            out[tag] = {"status": e.code,
                        "ctype": (e.headers.get("Content-Type") or "")[:40] if e.headers else "",
                        "head": e.read(200).decode("utf-8", "replace").replace("\n", " ")[:110]}
        except Exception as e:
            out[tag] = {"status": 0, "err": "%s" % type(e).__name__}
    return out


rep = {}
for k, host in PLATS.items():
    print("=" * 78)
    e = extract(k)
    print("[%s] asm=%s files=%d paths=%d consts=%d" %
          (k, "有" if e["mod"] else "无", e["files"], len(e["paths"]), len(e["consts"])))
    if e["paths"]:
        print("   路径:", e["paths"][:14])
    if e["consts"]:
        print("   常量:", e["consts"][:16])
    pr = probe(host)
    for tag, info in pr.items():
        print("   %-10s -> %s %s %s" % (tag, info.get("status"),
                                        info.get("ctype", ""), info.get("head", info.get("err", ""))[:70]))
    rep[k] = {"asm": e, "host": host, "probe": pr}

with open(os.path.join(OUT, "batch_recon.json"), "w", encoding="utf-8") as f:
    json.dump(rep, f, ensure_ascii=False, indent=1)
print("\n已存 batch_recon.json")
