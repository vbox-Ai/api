# -*- coding: utf-8 -*-
"""mmmh 第十轮：多 avkey 验证 m3u8 + 封面解密尝试"""
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
IMG = "https://image.meme06.live"
TOKEN = ("eyJ1c2VyX2lkIjozMDQ1OTg4NjEsImxhc3Rsb2dpbiI6MTc2Mjg3MTA1MH0"
         ".a568a4b03a8d6c08c14494d85c40a9f1"
         ".7c6579106b5199d2177be390fc8c608b73bfc0cf63a2d853da78afab")
KEY = b"ae52f7ffd2dd66ba5743bb180188b991"


def call(path, qp=None):
    url = BASE + path + (("?" + urllib.parse.urlencode(qp)) if qp else "")
    h = {"User-Agent": UA, "Accept": "application/json, */*",
         "Authorization": "Bearer " + TOKEN}
    try:
        with OP.open(urllib.request.Request(url, headers=h), timeout=20) as r:
            st, hd, body = r.status, dict(r.headers), r.read()
    except urllib.error.HTTPError as e:
        st, hd, body = e.code, dict(e.headers) if e.headers else {}, e.read()
    except Exception as e:
        return 0, {}, b"", None
    keys = {k.lower(): v for k, v in hd.items()}
    xlen = keys.get("x-response-length")
    if not xlen:
        return st, keys, body, None
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
        return st, keys, body, json.JSONDecoder().raw_decode(s[i:])[0]
    except Exception:
        return st, keys, body, None


st, keys, body, obj = call("/v1/animat/category/list",
                           {"category_id": 7, "type": 1, "page": 1})
items = ((obj or {}).get("success") or {}).get("data") or []
print("列表 %d 项" % len(items))

print("\n=== m3u8 多测试 ===")
for it in items[:4]:
    ak = it.get("avkey")
    media = it.get("media") or {}
    for q in ("720", "intro", "240"):
        rel = media.get(q)
        if not rel:
            continue
        h = {"User-Agent": UA, "Authorization": "Bearer " + TOKEN,
             "Referer": "https://meme06.live/"}
        try:
            with OP.open(urllib.request.Request(BASE + rel, headers=h), timeout=20) as r:
                b = r.read(160)
                print("  %-14s %-6s -> %s %s | %s" % (ak, q, r.status,
                      r.headers.get("Content-Type"), b[:80]))
        except urllib.error.HTTPError as e:
            print("  %-14s %-6s -> HTTP %s" % (ak, q, e.code))
        except Exception as e:
            print("  %-14s %-6s -> %s" % (ak, q, type(e).__name__))
        break

print("\n=== 封面解密尝试（encrypt=true + chain）===")
if items:
    cov = items[0].get("cover") or ""
    url = IMG + cov
    try:
        with OP.open(urllib.request.Request(url, headers={"User-Agent": UA}), timeout=20) as r:
            data = r.read()
        print("  封面 %s -> %d 字节 head=%s" % (cov, len(data), data[:8].hex()))
        chain = "miXFCHEoSXJ.M"
        print("  chain =", chain)
        # 试几种 chain 派生
        cands = {}
        b64ch = base64.b64encode(chain.encode()).decode()
        cands["chain16"] = chain.encode()[:16]
        cands["chain+pad"] = (chain.encode() + b"\x00" * 16)[:16]
        cands["md5chain"] = hashlib.md5(chain.encode()).hexdigest()[:16].encode()
        cands["b64chain16"] = b64ch[:16].encode()
        for ivname, ivb in (("zero", b"\x00" * 16),):
            for kn, kb in (("chain16", chain.encode()[:16]), ("md5k", hashlib.md5(chain.encode()).digest())):
                if len(data) % 16:
                    continue
                try:
                    p = AES.new(kb, AES.MODE_CBC, ivb).decrypt(data[:len(data) // 16 * 16])
                    if p[:3] == b"\xff\xd8\xff" or p[:4] == b"\x89PNG":
                        print("  ★ 图片解密命中 key=%s iv=%s" % (kn, ivname))
                except Exception:
                    pass
        print("  （未命中则图片加密需进一步逆向 MmMhAnimImg/MmMhChain）")
    except Exception as e:
        print("  封面取失败:", e)
