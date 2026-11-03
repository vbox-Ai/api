# -*- coding: utf-8 -*-
"""mmmh 第八轮：列表 / 详情 / 阅读 接口打通"""
import base64
import hashlib
import json
import urllib.error
import urllib.parse
import urllib.request

from Crypto.Cipher import AES
from Crypto.Util.Padding import unpad

OP = urllib.request.build_opener(urllib.request.ProxyHandler({}))
UA = "okhttp/3.14.9"
BASE = "https://sdhvb.meme06.live"
TOKEN = ("eyJ1c2VyX2lkIjozMDQ5ODg2MSwibGFzdGxvZ2luIjoxNzYyODcxMDUwfQ"  # 占位，运行时覆盖
         )
TOKEN = ("eyJ1c2VyX2lkIjozMDQ1OTg4NjEsImxhc3Rsb2dpbiI6MTc2Mjg3MTA1MH0"
         ".a568a4b03a8d6c08c14494d85c40a9f1"
         ".7c6579106b5199d2177be390fc8c608b73bfc0cf63a2d853da78afab")
KEY = b"ae52f7ffd2dd66ba5743bb180188b991"


def call(path, qp=None):
    url = BASE + path
    if qp:
        url += "?" + urllib.parse.urlencode(qp)
    h = {"User-Agent": UA, "Accept": "application/json, */*",
         "Authorization": "Bearer " + TOKEN}
    try:
        with OP.open(urllib.request.Request(url, headers=h), timeout=20) as r:
            st, hd, body = r.status, dict(r.headers), r.read()
    except urllib.error.HTTPError as e:
        st, hd, body = e.code, dict(e.headers) if e.headers else {}, e.read()
    except Exception as e:
        return 0, {}, str(e).encode(), None

    keys = {k.lower(): v for k, v in hd.items()}
    xlen = keys.get("x-response-length")
    if not xlen:
        return st, keys, body, None          # 明文错误体
    txt = body.decode("utf-8", "replace").strip()
    try:
        raw = base64.b64decode(txt + "=" * ((4 - len(txt) % 4) % 4))
        iv = hashlib.md5(str(xlen).encode()).hexdigest()[8:24].encode()
        p = AES.new(KEY, AES.MODE_CBC, iv).decrypt(raw)
        try:
            p = unpad(p, 16)
        except Exception:
            pass
        s = p.decode("utf-8", "replace")
        i = min([x for x in (s.find("{"), s.find("[")) if x >= 0] or [0])
        obj, _ = json.JSONDecoder().raw_decode(s[i:])
        return st, keys, body, obj
    except Exception as e:
        return st, keys, body, {"_err": str(e)}


print("=" * 76)
print("1) 列表接口（找 type 取值）")
for t in ["animat", "comic", "anime", "1", "manga"]:
    st, keys, body, obj = call("/v1/animat/category/list",
                               {"category_id": 7, "type": t, "page": 1})
    n = 0
    if isinstance(obj, dict):
        d = obj.get("success") or obj
        if isinstance(d, dict):
            for v in d.values():
                if isinstance(v, list):
                    n = len(v)
                    break
    print("  type=%-8s -> %s  n=%d  %s" % (t, st, n,
          json.dumps(obj, ensure_ascii=False)[:120] if obj else body[:100]))

print("\n" + "=" * 76)
print("2) 取一个可用的列表结果")
ok_obj = None
for t in ["animat", "comic"]:
    st, keys, body, obj = call("/v1/animat/category/list",
                               {"category_id": 7, "type": t, "page": 1})
    if isinstance(obj, dict) and "error" not in obj:
        s = json.dumps(obj, ensure_ascii=False)
        if '"id"' in s or '"comic_id"' in s or '"book_id"' in s:
            ok_obj = (t, obj)
            print("  ★ type=%s 可用" % t)
            print(json.dumps(obj, ensure_ascii=False, indent=1)[:1500])
            with open("tools/_dec/mmmh_list_sample.json", "w", encoding="utf-8") as f:
                json.dump(obj, f, ensure_ascii=False, indent=1)
            break
if not ok_obj:
    print("  未拿到列表")
