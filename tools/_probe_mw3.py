# -*- coding: utf-8 -*-
"""mw：章节列表与阅读页结构"""
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


def get(path):
    url = path if path.startswith("http") else BASE + path
    try:
        with op.open(urllib.request.Request(url, headers={
                "User-Agent": UA, "Accept": "text/html,*/*",
                "Accept-Language": "zh-CN,zh;q=0.9", "Referer": BASE + "/"}),
                timeout=20) as r:
            return r.status, r.read()
    except urllib.error.HTTPError as e:
        return e.code, e.read()
    except Exception as e:
        return 0, str(e).encode()


st, b = get("/book/450159")
h = b.decode("utf-8", "replace")
print("详情 %s %d" % (st, len(b)))

print("\n=== detail-list-select 区域 ===")
i = h.find("detail-list-select")
if i > 0:
    seg = h[i:i + 2500].replace("\n", " ")
    print(seg[:1600])

print("\n=== 全部 href 模式统计 ===")
from collections import Counter
hrefs = re.findall(r'href="([^"]+)"', h)
pat = Counter()
for x in hrefs:
    p = re.sub(r"\d+", "N", x.split("?")[0])
    if p.startswith("/") and len(p) > 3:
        pat[p] += 1
for p, n in pat.most_common(14):
    print("  %-40s %d" % (p, n))

print("\n=== 尝试章节 URL 猜测 ===")
cands = []
mm = re.search(r'/book/450159/(\d+)', h)
if mm:
    cands.append("/book/450159/" + mm.group(1))
for c in ["/book/450159/1", "/book/450159/0", "/chapter/450159/1",
          "/read/450159/1", "/book/450159/chapter/1"]:
    cands.append(c)
for c in cands[:6]:
    s2, b2 = get(c)
    t2 = b2.decode("utf-8", "replace")
    imgs = re.findall(r'src="(https?://[^"]+\.(?:jpg|png|webp)[^"]*)"', t2)
    ok = "img-content" in t2
    print("  %-24s -> %-4s %7d bytes  img-content=%s 图片数=%d" %
          (c, s2, len(b2), ok, len(imgs)))
    if imgs:
        print("      样本:", imgs[:3])
    if ok:
        j = t2.find("img-content")
        print("      区域:", t2[max(0, j - 200):j + 600].replace("\n", " ")[:500])
        break
