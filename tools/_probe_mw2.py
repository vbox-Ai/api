# -*- coding: utf-8 -*-
"""mw 漫蛙：列表项/详情/阅读页 结构精确提取"""
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
    try:
        with op.open(urllib.request.Request(url, headers={
                "User-Agent": UA, "Accept": "text/html,*/*",
                "Accept-Language": "zh-CN,zh;q=0.9", "Referer": BASE + "/"}),
                timeout=timeout) as r:
            return r.status, r.read()
    except urllib.error.HTTPError as e:
        return e.code, e.read()
    except Exception as e:
        return 0, str(e).encode()


st, b = get("/booklist")
h = b.decode("utf-8", "replace")
print("booklist %s %d bytes" % (st, len(b)))

print("\n=== 首个 /book/ 链接的 DOM 上下文 ===")
m = re.search(r'<a[^>]*href="/book/\d+"', h)
if m:
    s = max(0, m.start() - 400)
    print(h[s:m.start() + 900].replace("\n", " ")[:1200])

print("\n=== 用正则试提取列表项 ===")
pats = [
    r'<a[^>]+href="(/book/\d+)"[^>]*>\s*<img[^>]+(?:data-original|src)="([^"]+)"[^>]*>',
    r'<a[^>]+href="(/book/\d+)"[^>]*title="([^"]*)"',
    r'href="(/book/\d+)"[^>]*>\s*<div[^>]*class="[^"]*cover[^"]*"',
]
for i, p in enumerate(pats):
    got = re.findall(p, h)[:5]
    print("  模式%d -> %d 条 %s" % (i, len(got), got[:3]))

print("\n=== 分页参数试探 ===")
for q in ["?page=2", "?page=2&gender=-1", "?gender=2&page=1"]:
    st2, b2 = get("/booklist" + q)
    h2 = b2.decode("utf-8", "replace")
    ids = list(dict.fromkeys(re.findall(r'href="/book/(\d+)"', h2)))[:4]
    print("  %-22s -> %s %d bytes  前4个id=%s" % (q, st2, len(b2), ids))

print("\n=== 详情页 ===")
st3, b3 = get("/book/450159")
h3 = b3.decode("utf-8", "replace")
print("  /book/450159 -> %s %d bytes" % (st3, len(b3)))
print("  标题:", (re.search(r"<title>(.*?)</title>", h3, re.S) or [None, ""])[1][:60])
for sel in ("detail-main-info-title", "detail-main-cover", "detail-desc", "detail-list-select"):
    i = h3.find(sel)
    print("   %-24s %s" % (sel, ("位置 %d" % i) if i > 0 else "未出现"))
# 章节链接
chaps = re.findall(r'href="(/book/\d+/\d+[^"]*)"', h3)[:6]
print("  章节链接:", chaps)
print("  其它链接:", list(dict.fromkeys(re.findall(r'href="(/[a-z]+/[^"]*)"', h3)))[:10])
