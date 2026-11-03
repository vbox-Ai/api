# -*- coding: utf-8 -*-
"""mmmh 图片：带 host/chain/Authorization 头请求"""
import urllib.error
import urllib.request

OP = urllib.request.build_opener(urllib.request.ProxyHandler({}))
UA = "okhttp/3.14.9"
IMG = "https://image.meme06.live"
COVER = "/imgs/cover/e4/fc322606ea.jpg"
CHAIN = "miXFCHEoSXJ.M"
TOKEN = ("eyJ1c2VyX2lkIjozMDQ1OTg4NjEsImxhc3Rsb2dpbiI6MTc2Mjg3MTA1MH0"
         ".a568a4b03a8d6c08c14494d85c40a9f1"
         ".7c6579106b5199d2177be390fc8c608b73bfc0cf63a2d853da78afab")


def fetch(url, hdrs):
    h = {"User-Agent": UA}
    h.update(hdrs)
    try:
        with OP.open(urllib.request.Request(url, headers=h), timeout=20) as r:
            return r.status, dict(r.headers), r.read()
    except urllib.error.HTTPError as e:
        return e.code, dict(e.headers) if e.headers else {}, e.read()
    except Exception as e:
        return 0, {}, str(e).encode()


def judge(b):
    if not b:
        return "空"
    if b[:3] == b"\xff\xd8\xff":
        return "★JPEG"
    if b[:4] == b"\x89PNG":
        return "★PNG"
    if b[:2] == b"\x1f\x8b":
        return "gzip"
    return "其它 magic=" + b[:4].hex()


url = IMG + COVER
VARIANTS = [
    ("裸", {}),
    ("chain 头", {"chain": CHAIN}),
    ("host+chain 头", {"host": IMG, "chain": CHAIN}),
    ("host+chain+Auth", {"host": IMG, "chain": CHAIN,
                         "Authorization": "Bearer " + TOKEN}),
    ("chain+Auth", {"chain": CHAIN, "Authorization": "Bearer " + TOKEN}),
    ("host+chain+Auth+Ref", {"host": IMG, "chain": CHAIN,
                             "Authorization": "Bearer " + TOKEN,
                             "Referer": "https://meme06.live/"}),
]

print("%-24s %-6s %-9s %s" % ("变体", "状态", "字节", "判定"))
print("-" * 74)
for name, hdrs in VARIANTS:
    st, h, b = fetch(url, hdrs)
    print("%-24s %-6s %-9d %s" % (name, st, len(b), judge(b)))
    if b[:3] == b"\xff\xd8\xff" or b[:4] == b"\x89PNG":
        with open("tools/_dec/mmmh_cover_ok.jpg", "wb") as f:
            f.write(b)
        print("   ★ 已存 tools/_dec/mmmh_cover_ok.jpg")
        print("   命中的头:", hdrs)
        break
