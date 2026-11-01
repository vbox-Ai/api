# -*- coding: utf-8 -*-
"""全量提取所有抓包会话：basic(URL) + request_headers + 响应体前若干字节，
输出到一个汇总文件，便于检索 hgsp 等平台。"""
import os
import sys

sys.stdout.reconfigure(encoding="utf-8")
ROOT = r"C:\Users\Administrator\Downloads\暮色逆向"
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "_cap_dump.txt")


def readf(p, limit=3000):
    if not os.path.exists(p):
        return ""
    try:
        with open(p, "rb") as f:
            b = f.read(limit)
        return b.decode("utf-8", "replace")
    except Exception:
        return ""


def main():
    rows = []
    for base, dnames, _f in os.walk(ROOT):
        subs = [d for d in dnames if d.isdigit()]
        if len(subs) < 2:
            continue
        for sub in sorted(subs, key=lambda x: int(x)):
            d = os.path.join(base, sub)
            basic = readf(os.path.join(d, "basic"), 400).strip()
            if not basic:
                continue
            rows.append((base, sub, basic, d))
    print("会话请求总数:", len(rows))
    with open(OUT, "w", encoding="utf-8") as w:
        for base, sub, basic, d in rows:
            w.write("\n" + "=" * 100 + "\n")
            w.write("### %s / #%s\n" % (os.path.basename(base), sub))
            w.write("URL: %s\n" % basic)
            hdr = readf(os.path.join(d, "request_headers"), 4000)
            if hdr:
                w.write("--- REQ HEADERS ---\n" + hdr + "\n")
            rh = readf(os.path.join(d, "response_headers"), 1500)
            if rh:
                w.write("--- RESP HEADERS ---\n" + rh + "\n")
            rb = os.path.join(d, "response_body")
            if os.path.exists(rb):
                sz = os.path.getsize(rb)
                w.write("--- RESP BODY (%d B) head ---\n" % sz)
                w.write(readf(rb, 600) + "\n")
    print("写出:", OUT)
    # 打印主机分布
    from collections import Counter
    hosts = Counter()
    for _b, _s, basic, _d in rows:
        try:
            h = basic.split("//", 1)[1].split("/", 1)[0]
        except Exception:
            h = basic
        hosts[h] += 1
    print("\n主机分布:")
    for h, c in hosts.most_common(60):
        print("  %-45s %d" % (h, c))


if __name__ == "__main__":
    main()
