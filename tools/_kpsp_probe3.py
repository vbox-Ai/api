# -*- coding: utf-8 -*-
"""kpsp 实测 v3：媒体域名 / 搜索 / 标签 / 详情 / site_id 范围"""
import json
import os
import urllib.error
import urllib.parse
import urllib.request

from _kpsp_probe2 import BASE, OUT, call, decrypt, fetch_dec

OP = urllib.request.build_opener(urllib.request.ProxyHandler({}))
UA = "okhttp/3.14.9"

HOSTS = ["https://hm-img.hdstfb.com", BASE, "https://sm-api.wieuc.com",
         "https://hm-video.hdstfb.com", "https://hm.hdstfb.com"]

print("=" * 74)
print("1) 媒体域名探测（pic / play_url 拼哪个 host）")
j = json.load(open(os.path.join(OUT, "kpsp_list_s1.json"), encoding="utf-8"))
it = (j.get("data") or {}).get("items") or [{}]
it = it[0]
pic = it.get("pic") or ""
play = it.get("play_url") or ""
pre = it.get("preview_url") or ""
pplay = it.get("preview_play_url") or ""
print("  pic       =", pic)
print("  play_url  =", play)
print("  preview   =", pre)


def head(url, timeout=15):
    try:
        req = urllib.request.Request(url, headers={"User-Agent": UA, "Referer": BASE + "/"})
        with OP.open(req, timeout=timeout) as r:
            b = r.read(64)
            return r.status, r.headers.get("Content-Type"), len(b), b[:16]
    except urllib.error.HTTPError as e:
        return e.code, None, 0, b""
    except Exception as e:
        return 0, type(e).__name__, 0, str(e)[:60].encode()


for h in HOSTS:
    u = h.rstrip("/") + pic
    st, ct, n, head_b = head(u)
    print("  pic  %-32s -> %s %s" % (h, st, ct))
for h in HOSTS[:3]:
    u = h.rstrip("/") + play
    st, ct, n, head_b = head(u)
    print("  play %-32s -> %s %s" % (h, st, ct))
    if st == 200:
        try:
            rq = urllib.request.Request(u, headers={"User-Agent": UA, "Referer": BASE + "/"})
            with OP.open(rq, timeout=20) as r:
                m = r.read().decode("utf-8", "replace")
            print("       m3u8 头:", m[:220].replace("\n", " | "))
            segs = [l for l in m.splitlines() if l and not l.startswith("#")]
            keys = [l for l in m.splitlines() if "EXT-X-KEY" in l]
            print("       分片=%d  key行=%s" % (len(segs), keys[:1]))
        except Exception as e:
            print("       m3u8 读取失败:", e)

print("\n" + "=" * 74)
print("2) 搜索 search/vod")
fetch_dec("search/vod", {"search": "偷拍", "page": 1, "per_page": 20, "site_id": 1}, "search")

print("\n" + "=" * 74)
print("3) 标签过滤 tag=")
fetch_dec("api/vod/video", {"page": 1, "per_page": 5, "site_id": 1, "tag": "偷拍"}, "tag")

print("\n" + "=" * 74)
print("4) 详情端点候选")
for p in ["api/vod/video/%s" % (it.get("id")),
          "api/vod/detail?id=%s" % (it.get("id")),
          "api/vod/video/detail?id=%s" % (it.get("id")),
          "api/vod/info?id=%s" % (it.get("id"))]:
    st, body = call(p)
    ok = False
    try:
        w = json.loads(body.decode("utf-8", "replace"))
        xd = w.get("x-data") if isinstance(w, dict) else None
        if xd:
            pl, _ = decrypt(xd)
            print("  [%s] -> %s  ★解密 %d 字节: %s" % (p, st, len(pl), pl[:120]))
            ok = True
    except Exception:
        pass
    if not ok:
        print("  [%s] -> %s  %s" % (p, st, body[:100]))

print("\n" + "=" * 74)
print("5) site_id 范围")
for sid in range(1, 7):
    st, body = call("api/vod/video", {"page": 1, "per_page": 3, "site_id": sid})
    try:
        w = json.loads(body.decode("utf-8", "replace"))
        xd = w.get("x-data")
        pl, _ = decrypt(xd)
        d = json.loads(pl.decode("utf-8")).get("data") or {}
        print("  site_id=%d total=%s pages=%s n=%d" % (
            sid, d.get("total"), d.get("pages"), len(d.get("items") or [])))
    except Exception as e:
        print("  site_id=%d 失败 %s" % (sid, e))
