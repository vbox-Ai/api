# -*- coding: utf-8 -*-
"""zlt 糟老头 + mdtv 麻豆TV：快速可攻性探测"""
import json
import urllib.error
import urllib.parse
import urllib.request

OP = urllib.request.build_opener(urllib.request.ProxyHandler({}))
UA = ("Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) "
      "AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Mobile/15E148 Safari/604.1")

TARGETS = {
    "zlt": ("https://apjk85sd.q2ngx58.com",
            ["/api/v2/index_items", "/api/tags/navicate", "/api/v2/query/",
             "/api/query/tags_and_attr", "/api/girls/list/1"]),
    "mdtv": ("https://spi.d5c4a712.com",
             ["/video/list", "/video/channel", "/video/tags"]),
}


def get(base, path, qp=None, hdrs=None):
    url = base + path
    if qp:
        url += "?" + urllib.parse.urlencode(qp)
    h = {"User-Agent": UA, "Accept": "application/json,*/*"}
    if hdrs:
        h.update(hdrs)
    try:
        with OP.open(urllib.request.Request(url, headers=h), timeout=15) as r:
            return r.status, dict(r.headers), r.read()
    except urllib.error.HTTPError as e:
        return e.code, dict(e.headers) if e.headers else {}, e.read()
    except Exception as e:
        return 0, {}, str(e).encode()


for name, (base, paths) in TARGETS.items():
    print("=" * 78)
    print(name, base)
    for p in paths:
        st, hd, b = get(base, p)
        ct = (hd.get("Content-Type") or "")[:26]
        txt = b[:180].decode("utf-8", "replace").replace("\n", " ")
        print("  %-32s -> %-4s %6d %-26s %s" % (p, st, len(b), ct, txt[:110]))
        # 若是 JSON，看结构
        s = b.strip()
        if s[:1] in (b"{", b"["):
            try:
                j = json.loads(b.decode("utf-8", "replace"))
                if isinstance(j, dict):
                    print("      JSON keys:", list(j.keys())[:10])
                    for k, v in j.items():
                        if isinstance(v, list) and v and isinstance(v[0], dict):
                            print("      %s[0] keys: %s" % (k, list(v[0].keys())[:12]))
                            break
                        if isinstance(v, dict):
                            print("      %s keys: %s" % (k, list(v.keys())[:10]))
            except Exception:
                pass
    print()
