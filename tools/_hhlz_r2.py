# -*- coding: utf-8 -*-
"""hhlz 第二轮：解 data 字段 + 摸清四个接口

响应结构：
    {"code":0,"msg":"success","data":"<base64>","cimg":"1","capi":"1"}
    data = base64( AES-128-CBC(JSON, key="D2o4XyQeIFobJ4tS", iv="sciCuBC7orQtDhTO") )

所有请求都要带同一套"设备参数"（appId/debug/osType/product/ver/marketChannel/sign/
sysVer/proxyChannel/packageName/time/phoneModel/udid），sign 是**硬编码常量**。

接口（asm：comic_page / read_comic_page）：
    /comic/list     列表（cat 分类, page_num 页码）
    /cartoon/info   详情
    /comic/catalog  目录
    /comic/chapter  章节图
"""
import base64
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
UDID = "00867d34-62ad-3de6-b203-186d92fe0876"
OP = urllib.request.build_opener(urllib.request.ProxyHandler({}))


def base_params():
    return {
        "appId": "1", "debug": "1", "osType": "3", "product": "1", "ver": "6.0.1",
        "marketChannel": "LDY", "sign": SIGN, "sysVer": "13", "proxyChannel": "LDY",
        "packageName": PKG, "time": int(time.time()), "phoneModel": "NX729J", "udid": UDID,
    }


def dec_data(envelope):
    """{"code":0,...,"data":"<b64>"} → 明文 JSON 字符串"""
    if not isinstance(envelope, dict):
        return envelope
    d = envelope.get("data")
    if not isinstance(d, str) or not d:
        return envelope
    try:
        raw = base64.b64decode(d + "=" * (-len(d) % 4))
        pt = AES.new(KEY, AES.MODE_CBC, IV).decrypt(raw)
        try:
            pt = unpad(pt, 16)
        except Exception:
            pass
        s = pt.decode("utf-8", "replace")
        return json.loads(s)
    except Exception:
        return envelope


def post(path, extra=None):
    payload = base_params()
    if extra:
        payload.update(extra)
    req = urllib.request.Request(
        HOST + path, data=json.dumps(payload, ensure_ascii=False).encode(), method="POST",
        headers={"Content-Type": "application/json", "User-Agent": "Dart/3.12 (dart:io)",
                 "Accept-Encoding": "gzip"})
    try:
        with OP.open(req, timeout=25) as r:
            raw = r.read()
            if raw[:2] == b"\x1f\x8b":
                try:
                    raw = gzip.decompress(raw)
                except Exception:
                    pass
            env = json.loads(raw.decode("utf-8", "replace"))
            return r.status, env, dec_data(env)
    except urllib.error.HTTPError as e:
        raw = e.read()
        try:
            env = json.loads(raw.decode("utf-8", "replace"))
            return e.code, env, dec_data(env)
        except Exception:
            return e.code, {}, raw[:100].decode("utf-8", "replace")
    except Exception as e:
        return 0, {}, str(e)[:80]


if __name__ == "__main__":
    st, env, data = post("/comic/list", {"cat": "", "page_num": 1})
    print("[comic/list] HTTP %s code=%s" % (st, (env or {}).get("code")))
    print(json.dumps(data, ensure_ascii=False)[:800])
    open("tools/_dec/hhlz_list.json", "w", encoding="utf-8").write(
        json.dumps(data, ensure_ascii=False, indent=1))
