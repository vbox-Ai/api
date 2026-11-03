# -*- coding: utf-8 -*-
"""mmmh 图片第二轮：换 host 值与域名"""
import urllib.error
import urllib.request

OP = urllib.request.build_opener(urllib.request.ProxyHandler({}))
UA = "okhttp/3.14.9"
COVER = "/imgs/cover/e4/fc322606ea.jpg"
CHAIN = "miXFCHEoSXJ.M"
TOKEN = ("eyJ1c2VyX2lkIjozMDQ1OTg4NjEsImxhc3Rsb2dpbiI6MTc2Mjg3MTA1MH0"
         ".a568a4b03a8d6c08c14494d85c40a9f1"
         ".7c6579106b5199d2177be390fc8c608b73bfc0cf63a2d853da78afab")
HOSTS = ["https://image.meme06.live", "image.meme06.live",
         "https://comic.meme06.live", "comic.meme06.live",
         "https://image1.dkmrii.cn", "https://img.meme06.live"]
URLS = ["https://image.meme06.live" + COVER,
        "https://comic.meme06.live" + COVER]


def fetch(url, hdrs):
    h = {"User-Agent": UA}
    h.update(hdrs)
    try:
        with OP.open(urllib.request.Request(url, headers=h), timeout=20) as r:
            return r.status, r.read()
    except urllib.error.HTTPError as e:
        return e.code, e.read()
    except Exception as e:
        return 0, str(e).encode()


def judge(b):
    if not b:
        return "空"
    if b[:3] == b"\xff\xd8\xff":
        return "★JPEG"
    if b[:4] == b"\x89PNG":
        return "★PNG"
    return "len=%d magic=%s" % (len(b), b[:4].hex())


print("%-34s %-30s %-6s %s" % ("图片URL", "host 头", "状态", "判定"))
print("-" * 100)
done = False
for url in URLS:
    for hv in HOSTS:
        for witha in (False, True):
            hdrs = {"host": hv, "chain": CHAIN}
            if witha:
                hdrs["Authorization"] = "Bearer " + TOKEN
            st, b = fetch(url, hdrs)
            j = judge(b)
            mark = " <<<" if j.startswith("★") else ""
            print("%-34s %-30s %-6s %s%s" % (url.replace("https://", ""), hv, st, j, mark))
            if j.startswith("★"):
                with open("tools/_dec/mmmh_cover_ok.jpg", "wb") as f:
                    f.write(b)
                print("   ★ 命中并已存：host=%s auth=%s" % (hv, witha))
                done = True
                break
        if done:
            break
    if done:
        break

if not done:
    # 看看 400 的响应体说了什么
    st, b = fetch(URLS[0], {"host": "https://image.meme06.live", "chain": CHAIN})
    print("\n400 响应体前 400：")
    print(b[:400].decode("utf-8", "replace"))
