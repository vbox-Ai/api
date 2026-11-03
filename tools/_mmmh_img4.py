# -*- coding: utf-8 -*-
"""mmmh 图片第三轮：comic tsurl 作图片服务 + chain 各种传法"""
import urllib.error
import urllib.request

OP = urllib.request.build_opener(urllib.request.ProxyHandler({}))
UA = "okhttp/3.14.9"
COVER = "/imgs/cover/e4/fc322606ea.jpg"
CHAIN = "miXFCHEoSXJ.M"
TOKEN = ("eyJ1c2VyX2lkIjozMDQ1OTg4NjEsImxhc3Rsb2dpbiI6MTc2Mjg3MTA1MH0"
         ".a568a4b03a8d6c08c14494d85c40a9f1"
         ".7c6579106b5199d2177be390fc8c608b73bfc0cf63a2d853da78afab")

TRIES = [
    ("comic host 裸", "https://comic.meme06.live" + COVER, {}),
    ("comic + chain 头", "https://comic.meme06.live" + COVER, {"chain": CHAIN}),
    ("comic + chain+auth", "https://comic.meme06.live" + COVER,
     {"chain": CHAIN, "Authorization": "Bearer " + TOKEN}),
    ("comic + host头", "https://comic.meme06.live" + COVER, {"host": "comic.meme06.live"}),
    ("image + ?chain&token", "https://image.meme06.live" + COVER + "?chain=" + CHAIN
     + "&token=" + TOKEN, {}),
    ("image + ?encrypt", "https://image.meme06.live" + COVER + "?encrypt=true&chain=" + CHAIN, {}),
    ("image + v1 前缀", "https://image.meme06.live/v1" + COVER, {}),
    ("api + imgs 路径", "https://sdhvb.meme06.live" + COVER,
     {"Authorization": "Bearer " + TOKEN}),
    ("api + imgs + chain", "https://sdhvb.meme06.live" + COVER,
     {"Authorization": "Bearer " + TOKEN, "chain": CHAIN}),
]


def fetch(url, hdrs):
    h = {"User-Agent": UA, "Accept": "image/*,*/*"}
    h.update(hdrs)
    try:
        with OP.open(urllib.request.Request(url, headers=h), timeout=20) as r:
            return r.status, r.read()
    except urllib.error.HTTPError as e:
        return e.code, e.read()
    except Exception as e:
        return 0, str(e).encode()


print("%-24s %-6s %-9s %s" % ("尝试", "状态", "字节", "判定"))
print("-" * 78)
for name, url, hdrs in TRIES:
    st, b = fetch(url, hdrs)
    if b[:3] == b"\xff\xd8\xff":
        j = "★JPEG"
    elif b[:4] == b"\x89PNG":
        j = "★PNG"
    else:
        j = "magic=" + (b[:4].hex() if b else "-")
    print("%-24s %-6s %-9d %s" % (name, st, len(b), j))
    if j.startswith("★"):
        with open("tools/_dec/mmmh_cover_ok.jpg", "wb") as f:
            f.write(b)
        print("   ★★★ 命中！%s" % name)
        break
else:
    print("\n全部未命中 —— 图片确为服务端加密存储，需客户端本地解密（MmMhChain 密钥派生），本轮未破。")
