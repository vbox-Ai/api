# -*- coding: utf-8 -*-
"""mw 漫蛙：HTML 结构实测"""
import http.cookiejar
import re
import urllib.error
import urllib.request

BASE = "https://manwaqr.cc"
UA = ("Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) "
      "AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Mobile/15E148 Safari/604.1")

jar = http.cookiejar.CookieJar()
op = urllib.request.build_opener(urllib.request.ProxyHandler({}),
                                 urllib.request.HTTPCookieProcessor(jar))


def get(path, timeout=20):
    url = path if path.startswith("http") else BASE + path
    req = urllib.request.Request(url, headers={
        "User-Agent": UA,
        "Accept": "text/html,application/xhtml+xml,*/*",
        "Accept-Language": "zh-CN,zh;q=0.9",
        "Referer": BASE + "/",
    })
    try:
        with op.open(req, timeout=timeout) as r:
            return r.status, r.read()
    except urllib.error.HTTPError as e:
        return e.code, e.read()
    except Exception as e:
        return 0, str(e).encode()


st, body = get("/")
print("首页 %s  %d bytes" % (st, len(body)))
html = body.decode("utf-8", "replace")
print("标题:", (re.search(r"<title>(.*?)</title>", html, re.S) or [None, ""])[1][:60])
print("cookie:", [c.name for c in jar])

print("\n=== 列表项结构 manga-list-2-cover ===")
i = html.find("manga-list-2-cover")
if i > 0:
    print(html[max(0, i - 200):i + 900].replace("\n", " ")[:1000])
else:
    print("  未找到；含关键字计数:", {k: html.count(k) for k in
                                ("manga-list", "book-list", "cover", "data-original", "/book/")})

print("\n=== /booklist ===")
st2, b2 = get("/booklist")
h2 = b2.decode("utf-8", "replace")
print("  %s %d bytes" % (st2, len(b2)))
print("  标题:", (re.search(r"<title>(.*?)</title>", h2, re.S) or [None, ""])[1][:60])
for mark in ("manga-list-2-cover", "book-list-cover", "data-original", "class=\"list"):
    print("   %-22s 出现 %d" % (mark, h2.count(mark)))
i = h2.find("manga-list-2-cover")
if i > 0:
    print("  片段:", h2[max(0, i - 150):i + 700].replace("\n", " ")[:850])

print("\n=== 链接样式 ===")
print("  /book/ 链接:", re.findall(r'href="([^"]*/book/[^"]*)"', h2)[:6])
print("  detail 链接:", re.findall(r'href="([^"]*detail[^"]*)"', h2)[:4])
print("\n=== 分类导航 ===")
print("  ", re.findall(r'href="([^"]*(?:booklist|list)[^"]*)"[^>]*>([^<]{2,10})<', h2)[:10])
