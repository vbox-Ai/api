# -*- coding: utf-8 -*-
"""zlt（糟老头）第一轮：按 ZltInterceptor::onRequest 还原签名与加密

asm：module/zlt/network/interceptor.dart @0x8e20a0（size 0x6ec）
逐段读出的流程（三段分支 GET/POST/POST-form 逻辑一致）：

    map = SplayTreeMap（按 key 排序）
        app="3"  brand="Xiaomi"  Connection="close"  encryptpic="1"
        model="MI 14"  platform="1"  requestUUID="78a6c296-2aea-8d78-38da-3176e9cfdcd2"
        token=<SpUtil "token_zlt">  t=<时间戳>  version="2.5.2.6"  k="hyfr6iyPZMZfJFEc"
    map["s"] = Hex(Hash(jsonEncode(map)))          ← k 参与签名
    map.remove("k")
    d = base64( AES(jsonEncode(map), key="xPxo2S5uGPhKHx5g" (16B),
                                     iv ="0a1b2c3d4e5f6789" (16B)) )
    请求 = {d: …}（GET 拼 query，POST 走 form；Content-Type: application/x-www-form-urlencoded）

上一版情报把 401「驾照无效」当成缺一个神秘凭证 —— 其实就是上面的 `token`（splash token id=6）。
"""
import base64
import hashlib
import json
import time
import urllib.error
import urllib.parse
import urllib.request

from Crypto.Cipher import AES

BASE = "https://apjk85sd.q2ngx58.com"
KEY = b"xPxo2S5uGPhKHx5g"
IV = b"0a1b2c3d4e5f6789"
K = "hyfr6iyPZMZfJFEc"
TOKEN = ("LzF2SHp6NldrVmVBaHFobmVMVys3Q3l3S096MG95bUNhdDFpKyhMZFlKMVpUckRqdWl4cTJvc2E4ZXVL"
         "L1dSZDIwbG1QcHBiYkJOMHJoSWthK01iOFhKbmMwR3RWZisyc3E0dXBwOGxleXdFMk9tQUVIVGJrOG03"
         "T3lMQVMyd0dkYlBacnJCME1ma2JPaHZ5VVBZYk55TzFXS3dvTUJsenlUSGZkRTlpSmpiUkhFelFXT3hI"
         "SHhaaDlTQnN2RlFB")
UA = "okhttp/3.14.9"
OP = urllib.request.build_opener(urllib.request.ProxyHandler({}))


def build(extra=None, ts_unit="s", hash_name="md5"):
    mp = {
        "app": "3", "brand": "Xiaomi", "Connection": "close", "encryptpic": "1",
        "model": "MI 14", "platform": "1",
        "requestUUID": "78a6c296-2aea-8d78-38da-3176e9cfdcd2",
        "token": TOKEN,
        "version": "2.5.2.6",
        "k": K,
    }
    ts = int(time.time() * 1000) if ts_unit == "ms" else int(time.time())
    mp["t"] = str(ts)
    if extra:
        for k2, v2 in extra.items():
            mp[str(k2)] = str(v2)
    ordered = {k2: mp[k2] for k2 in sorted(mp.keys())}          # SplayTreeMap 语义
    raw = json.dumps(ordered, ensure_ascii=False, separators=(",", ":"))
    hf = {"md5": hashlib.md5, "sha1": hashlib.sha1, "sha256": hashlib.sha256}[hash_name]
    mp["s"] = hf(raw.encode()).hexdigest()
    ordered_s = {k2: mp[k2] for k2 in sorted(mp.keys())}
    del ordered_s["k"]
    body = json.dumps(ordered_s, ensure_ascii=False, separators=(",", ":")).encode()
    enc = AES.new(KEY, AES.MODE_CBC, IV).encrypt(body + b"\0" * (-len(body) % 16))
    return base64.b64encode(enc).decode(), ordered_s, raw


def call(path, extra=None, method="GET", **kw):
    d, plain_map, raw = build(extra, **kw)
    url = BASE + "/" + path.lstrip("/")
    if method == "GET":
        req = urllib.request.Request(url + "?d=" + urllib.parse.quote(d),
                                     headers={"User-Agent": UA})
    else:
        form = urllib.parse.urlencode({"d": d}).encode()
        req = urllib.request.Request(url, data=form, method="POST",
                                     headers={"User-Agent": UA,
                                              "Content-Type": "application/x-www-form-urlencoded"})
    try:
        with OP.open(req, timeout=15) as r:
            return r.status, r.read()[:400]
    except urllib.error.HTTPError as e:
        try:
            return e.code, e.read()[:400]
        except Exception:
            return e.code, b""
    except Exception as e:
        return 0, str(e)[:80].encode()


if __name__ == "__main__":
    print("== 打印一份签名与加密后的 map（自查用）==")
    d, pm, raw = build({"page": 1})
    print("sign-raw:", raw[:220])
    print("plain  :", json.dumps(pm, ensure_ascii=False)[:220])
    print("d      :", d[:80], "...")

    print("\n%-28s %-6s %-10s %s" % ("路径", "方法", "参数", "HTTP/响应"))
    print("-" * 100)
    for path in ("api/tags/navicate", "api/index_items/more", "api/query/tags_and_attr"):
        for method in ("GET", "POST"):
            for ts_unit in ("s", "ms"):
                st, body = call(path, None, method, ts_unit=ts_unit)
                s = body.decode("utf-8", "replace")
                print("%-28s %-6s %-10s %s %s" % (path, method, ts_unit, st, s[:110]))
                if st == 200 and '"code":401' not in s and "驾照" not in s:
                    print("   ★ 看起来通过鉴权")
