# -*- coding: utf-8 -*-
"""cgw：复用 4hu 的 ap-d XOR 解挑战，看能否拿到真实 API 数据"""
import json
import os
import sys
import urllib.error
import urllib.parse
import urllib.request

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__))))
from importlib.util import module_from_spec, spec_from_file_location

_spec = spec_from_file_location(
    "h4c", os.path.join(os.path.dirname(os.path.abspath(__file__)), "4hu_client.py"))
h4c = module_from_spec(_spec)
_spec.loader.exec_module(h4c)

OP = urllib.request.build_opener(urllib.request.ProxyHandler({}))
UA = ("Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) "
      "AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Mobile/15E148 Safari/604.1")


def raw_get(url, hdrs=None, timeout=15):
    h = {"User-Agent": UA, "Accept": "application/json,text/html,*/*",
         "Accept-Language": "zh-CN,zh;q=0.9"}
    if hdrs:
        h.update(hdrs)
    try:
        with OP.open(urllib.request.Request(url, headers=h), timeout=timeout) as r:
            return r.status, r.url, dict(r.headers), r.read()
    except urllib.error.HTTPError as e:
        return e.code, url, dict(e.headers) if e.headers else {}, e.read()
    except Exception as e:
        return 0, url, {}, str(e).encode()


print("=" * 74)
print("1) 解 ap-d 挑战")
st, final, hd, body = raw_get("https://h96h69.com/api.php/api/contents/list_category")
html = body.decode("utf-8", "replace")
print("  请求 -> %s  最终=%s  %d bytes" % (st, final, len(body)))
is_ch, txt = h4c.unwrap_challenge(html)
print("  是否挑战页:", is_ch, " 解出长度:", len(txt))
print("  解密内容前 600:")
print(txt[:600])

# 看是否含跳转/域名/cookie 线索
import re
urls = re.findall(r'(?:https?://[^\s"\'<>]+|/[a-zA-Z0-9_\-/\.]{3,60})', txt)
print("\n  内含 URL 线索:", list(dict.fromkeys(urls))[:12])
for kw in ("cookie", "document.cookie", "location", "href", "host", "domain"):
    if kw in txt.lower():
        i = txt.lower().find(kw)
        print("  [%s] %s" % (kw, txt[max(0, i - 60):i + 120].replace("\n", " ")))

print("\n" + "=" * 74)
print("2) 解密后若是 JS，尝试按其中的 cookie 重试")
cookies = re.findall(r'([A-Za-z0-9_]+)=([A-Za-z0-9%_\-\.]{4,})', txt)
print("  cookie 候选:", cookies[:6])
if cookies:
    ck = "; ".join("%s=%s" % (k, v) for k, v in cookies[:4])
    st2, final2, hd2, b2 = raw_get(
        "https://h96h69.com/api.php/api/contents/list_category",
        {"Cookie": ck, "Referer": final})
    t2 = b2.decode("utf-8", "replace")
    print("  带 cookie 重试 -> %s %d bytes  挑战页=%s" % (st2, len(b2), 'id="ap-d"' in t2))
    if 'id="ap-d"' not in t2:
        print("  body:", t2[:400])
    else:
        _, t3 = h4c.unwrap_challenge(t2)
        print("  二次解密:", t3[:300])
