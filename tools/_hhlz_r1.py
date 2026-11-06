# -*- coding: utf-8 -*-
"""hhlz（嘿嘿连载）协议验证 —— 证据来自抓包 + asm

抓包：`归档/2026-10-29-052251/64`
    POST https://rrs0a03ak.pye57rf.com/comic/list
    body: {"appId":"1","debug":"1","osType":"3","product":"1","ver":"6.0.1",
           "marketChannel":"LDY","sign":"d01ef895544ab4f2a1f4d38d66edb283",
           "sysVer":"13","proxyChannel":"LDY","packageName":"com.t55f8907c5…",
           "time":1793222660,"phoneModel":"NX729J","udid":"00867d34-…",
           "cat":"","page_num":1}

asm：`module/hhlz/network/interceptor.dart`
    onRequest  @0x8de210 —— 上面这些字段逐个 `[]=`，**sign 是硬编码常量**
                            （0x8de318 "d01ef895544ab4f2a1f4d38d66edb283"）
    onResponse @0x8f1548 —— AES(key="D2o4XyQeIFobJ4tS", iv="sciCuBC7orQtDhTO") 解 → jsonDecode

本轮：按此重放，确认 sign 常量仍有效、响应能解出明文 JSON。
"""
import gzip
import json
import time
import urllib.error
import urllib.request
import uuid

from Crypto.Cipher import AES
from Crypto.Util.Padding import unpad

KEY = b"D2o4XyQeIFobJ4tS"
IV = b"sciCuBC7orQtDhTO"
SIGN = "d01ef895544ab4f2a1f4d38d66edb283"
PKG = "com.t55f8907c5.z222ec9ed4.vcd6814de920260901"
HOST = "https://rrs0a03ak.pye57rf.com"
OP = urllib.request.build_opener(urllib.request.ProxyHandler({}))


def body(cat="", page=1):
    return {
        "appId": "1", "debug": "1", "osType": "3", "product": "1", "ver": "6.0.1",
        "marketChannel": "LDY", "sign": SIGN, "sysVer": "13", "proxyChannel": "LDY",
        "packageName": PKG, "time": int(time.time()), "phoneModel": "NX729J",
        "udid": str(uuid.uuid4()), "cat": cat, "page_num": page,
    }


def post(path, payload):
    req = urllib.request.Request(
        HOST + path, data=json.dumps(payload, ensure_ascii=False).encode(), method="POST",
        headers={"Content-Type": "application/json", "User-Agent": "Dart/3.12 (dart:io)",
                 "Accept-Encoding": "gzip"})
    try:
        with OP.open(req, timeout=25) as r:
            raw = r.read()
            if (r.headers.get("Content-Encoding") or "").lower() == "gzip" or raw[:2] == b"\x1f\x8b":
                try:
                    raw = gzip.decompress(raw)
                except Exception:
                    pass
            return r.status, raw
    except urllib.error.HTTPError as e:
        raw = e.read()
        return e.code, raw
    except Exception as e:
        return 0, str(e)[:80].encode()


def dec(raw):
    if raw[:1] in (b"{", b"["):
        return raw.decode("utf-8", "replace")
    # 服务端可能先 base64 再加密，也可能直接密文；两种都试
    import base64
    outs = []
    for blob in (raw,):
        for txt in (blob,):
            try:
                outs.append(AES.new(KEY, AES.MODE_CBC, IV).decrypt(txt))
            except Exception:
                pass
            try:
                outs.append(AES.new(KEY, AES.MODE_CBC, IV).decrypt(
                    base64.b64decode(txt + b"=" * (-len(txt) % 4))))
            except Exception:
                pass
    for pt in outs:
        try:
            pt = unpad(pt, 16)
        except Exception:
            pass
        s = pt.decode("utf-8", "replace")
        if s.lstrip()[:1] in ("{", "["):
            return s
    return "解密失败: " + raw[:80].hex()


if __name__ == "__main__":
    for path, payload in (("/comic/list", body("", 1)),
                          ("/cartoon/info", {"comic_id": "1"})
                          ):
        st, raw = post(path, payload)
        print("\n%-14s HTTP %-4s raw=%dB" % (path, st, len(raw)))
        txt = dec(raw)
        print(txt[:600])
        if txt.lstrip()[:1] in ("{", "["):
            open("tools/_dec/hhlz_%s.json" % path.strip("/").replace("/", "_"),
                 "w", encoding="utf-8").write(txt)
            print("→ 已存")
