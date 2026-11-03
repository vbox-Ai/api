# -*- coding: utf-8 -*-
"""hsck 黄色仓库：418 门禁绕行 + HTML 结构解析"""
import http.cookiejar
import re
import urllib.error
import urllib.request

BASE = "https://hsck3.u0u0.cc"
UAS = {
    "okhttp": "okhttp/3.14.9",
    "iphone": ("Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) "
               "AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Mobile/15E148 Safari/604.1"),
    "pc": ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
           "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"),
}

jar = http.cookiejar.CookieJar()
op = urllib.request.build_opener(
    urllib.request.ProxyHandler({}),
    urllib.request.HTTPCookieProcessor(jar))


def get(url, ua_key="okhttp", extra=None):
    h = {"User-Agent": UAS[ua_key], "Accept": "text/html,application/xhtml+xml,*/*",
         "Accept-Language": "zh-CN,zh;q=0.9", "Referer": BASE + "/"}
    if extra:
        h.update(extra)
    req = urllib.request.Request(url, headers=h)
    try:
        with op.open(req, timeout=20) as r:
            return r.status, r.read()
    except urllib.error.HTTPError as e:
        return e.code, e.read()
    except Exception as e:
        return 0, ("%s: %s" % (type(e).__name__, e)).encode()


print("=" * 74)
print("1) 各 UA + cookie 重放")
for k in UAS:
    st, b = get(BASE + "/", k)
    print("  %-8s 第一次 -> %s  %d bytes  cookies=%d" %
          (k, st, len(b), len(jar)))
    st2, b2 = get(BASE + "/", k)
    print("  %-8s 第二次 -> %s  %d bytes  cookies=%d" %
          (k, st2, len(b2), len(jar)))
    if st == 200:
        break

st, body = get(BASE + "/", "iphone")
txt = body.decode("gb18030", "replace")
print("\n  cookie 列表:", [c.name + "=" + c.value[:16] for c in jar])
print("  页面标题:", (re.search(r"<title>(.*?)</title>", txt, re.S) or [None, ""])[1][:60])

print("\n" + "=" * 74)
print("2) 列表容器结构（stui-vodlist__box 附近）")
idx = txt.find("stui-vodlist__box")
if idx > 0:
    print(txt[max(0, idx - 300):idx + 700].replace("\n", " ")[:900])
else:
    print("  未找到 stui-vodlist__box；尝试其它标记")
    for mark in ("vodlist", "data-original", "mac-vod", "module-item", "/index.php/vod"):
        print("   %-18s 出现 %d 次" % (mark, txt.count(mark)))

print("\n" + "=" * 74)
print("3) 链接与图片样本")
links = re.findall(r'href="(/[^"]*?(?:vod|detail|id)[^"]*?)"', txt)[:8]
print("  链接:", links[:8])
imgs = re.findall(r'data-original="([^"]+)"', txt)[:6]
print("  图片:", imgs[:6])
titles = re.findall(r'title="([^"]{4,40})"', txt)[:8]
print("  标题:", titles[:8])

print("\n" + "=" * 74)
print("4) 常见苹果CMS路径探测")
for p in ["/index.php/vod/show/id/1.html", "/vodshow/1--------1---.html",
          "/index.php/vod/type/id/1.html", "/type/1.html", "/index.php/ajax/data"]:
    st, b = get(BASE + p, "iphone")
    print("  %-34s -> %-4s %d bytes" % (p, st, len(b)))
