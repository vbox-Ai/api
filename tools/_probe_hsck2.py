# -*- coding: utf-8 -*-
"""hsck 第二轮：UTF-8 解码 + 分类导航 + 详情页 + 播放地址"""
import http.cookiejar
import re
import urllib.error
import urllib.request

BASE = "https://hsck3.u0u0.cc"
UA = ("Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) "
      "AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Mobile/15E148 Safari/604.1")

jar = http.cookiejar.CookieJar()
op = urllib.request.build_opener(urllib.request.ProxyHandler({}),
                                 urllib.request.HTTPCookieProcessor(jar))


def get(path, timeout=20):
    url = path if path.startswith("http") else BASE + path
    req = urllib.request.Request(url, headers={
        "User-Agent": UA, "Accept": "text/html,*/*",
        "Accept-Language": "zh-CN,zh;q=0.9", "Referer": BASE + "/"})
    try:
        with op.open(req, timeout=timeout) as r:
            return r.status, r.read()
    except urllib.error.HTTPError as e:
        return e.code, e.read()
    except Exception as e:
        return 0, str(e).encode()


st, body = get("/")
html = body.decode("utf-8", "replace")
print("首页 status=%s bytes=%d" % (st, len(body)))
print("标题:", (re.search(r"<title>(.*?)</title>", html, re.S) or [None, ""])[1][:60])

print("\n=== 分类导航 ===")
navs = re.findall(r'<a[^>]+href="([^"]+)"[^>]*>([^<]{2,12})</a>', html)
seen = set()
for href, name in navs:
    n = name.strip()
    if not n or n in seen:
        continue
    if any(x in href for x in ("/vodtype", "/type", "/list", "/index.php/vod", "/vodshow")):
        seen.add(n)
        print("  %-40s %s" % (href, n))
if not seen:
    # 退而求其次：所有带类型的链接
    for href, name in navs[:40]:
        if href.count("/") <= 3 and name.strip():
            print("  %-40s %s" % (href, name.strip()))

print("\n=== 列表项解析（取前 3 条）===")
items = re.findall(
    r'<a class="stui-vodlist__thumb[^"]*"\s+href="([^"]+)"[^>]*title="([^"]*)"[^>]*data-original="([^"]+)"',
    html)
if not items:
    items = re.findall(r'href="(/view/\?id=[^"]+)"[^>]*title="([^"]*)"[^>]*data-original="([^"]+)"', html)
print("  命中 %d 条" % len(items))
for href, title, pic in items[:3]:
    print("  %-28s %-30s %s" % (href, title[:28], pic[:60]))

print("\n=== 详情页 ===")
if items:
    href = items[0][0]
    st2, b2 = get(href)
    h2 = b2.decode("utf-8", "replace")
    print("  %s -> %s %d bytes" % (href, st2, len(b2)))
    print("  标题:", (re.search(r"<title>(.*?)</title>", h2, re.S) or [None, ""])[1][:60])
    m3u8 = re.findall(r'(https?://[^\s"\'<>]+?\.m3u8[^\s"\'<>]*)', h2)
    print("  m3u8:", m3u8[:3])
    player = re.findall(r'(?:var\s+player_[a-z]*\s*=|url:|src:)\s*[{"]?\s*["\']([^"\']{20,200})["\']', h2)
    print("  player 候选:", player[:4])
    print("  含关键字:", {k: h2.count(k) for k in ("m3u8", "player", "vod_play", "iframe", "encrypt")})
    # 打印详情页里含 m3u8/player 的片段
    for kw in ("m3u8", "vod_play"):
        i = h2.find(kw)
        if i > 0:
            print("  [%s] 上下文: %s" % (kw, h2[max(0, i - 200):i + 200].replace("\n", " ")[:380]))
            break
