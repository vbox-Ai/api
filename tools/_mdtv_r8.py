# -*- coding: utf-8 -*-
"""mdtv 第五轮：补上 asm 里发现的两处关键报文细节

从 blutter 反汇编 `module/mdtv/network/interceptor.dart::onRequest` 逐条读出：

  1. 请求头必须带 `suffix: JGDZMX`（0x8d5e74 `headers["suffix"]="JGDZMX"`）
     以及 `Content-Type: application/json`（0x8d5ea4）。
     缺 suffix → 服务端无法还原 IV（IV = "-p9B[~PnPs" + suffix）→ 解不开请求体
     → 业务层拿到空参 → {"code":1002,"msg":"参数错误"}。
     这正好解释了「响应能解密、请求恒 1002」的全部现象。

  2. 列表页 biz 只有三个键（home_page.dart::loadData，数组长度 12 = 3 对）：
         {"page": <页>, "list_row": 120, "type": 4}
     channel 只是 VideoPage（分区页）额外追加的第 4 个键。

其余保持上一轮已确认的算法：
  签名 MD5( sorted(k=v 用 & 连接) + "&m}q%ea6:LDcmS\\?aK)CeF287bPvd99@E,9Up^" )
  请求 AES-256-CBC(key=Vq234z…, iv=-p9B[~PnPsJGDZMX) → base64 → {"post-data": …}
  响应 {"suffix":"<6hex>","data":"<b64>"}，iv = "-p9B[~PnPs"+suffix
"""
import base64
import hashlib
import json
import time
import urllib.error
import urllib.request

from Crypto.Cipher import AES
from Crypto.Util.Padding import pad, unpad

BASE = "https://spi.d5c4a712.com/"
REQ_KEY = b"Vq234zBeSdGgYXzVTEfnnjjdmaTkk7A4"   # AES-256
REQ_IV = b"-p9B[~PnPsJGDZMX"                    # 16B
# ⚠ blutter 的 asm 注释把 `?` 打印成了 `\?`，libapp.so 偏移 367007 处
#   原始字节是 `&m}q%ea6:LDcmS?aK)CeF287bPvd99@E,9Up^`（36 字符，**无反斜杠**）。
#   上一轮带反斜杠 → 服务端解不开请求体时不影响，一旦请求体能解开就报 1001。
SECRET = "&m}q%ea6:LDcmS?aK)CeF287bPvd99@E,9Up^"
RESP_IV_HEAD = b"-p9B[~PnPs"
SUFFIX = "JGDZMX"
UA = "Dart/3.4 (dart:io)"

OP_DIRECT = urllib.request.build_opener(urllib.request.ProxyHandler({}))
OP_PROXY = urllib.request.build_opener(
    urllib.request.ProxyHandler({"http": "http://127.0.0.1:7890",
                                 "https": "http://127.0.0.1:7890"}))


def dec_resp(raw_body):
    """响应解密：{"suffix","data"} → 明文 dict。"""
    j = json.loads(raw_body.decode("utf-8", "replace"))
    if not isinstance(j, dict) or "data" not in j:
        return j
    d = j["data"]
    suf = str(j.get("suffix") or "")
    raw = base64.b64decode(d + "=" * (-len(d) % 4))
    iv = (RESP_IV_HEAD + suf.encode()).ljust(16, b"\0")[:16]
    if len(raw) % 16:
        return {"_err": "len %%16=%d" % (len(raw) % 16), "_raw": j}
    p = AES.new(REQ_KEY, AES.MODE_CBC, iv).decrypt(raw)
    try:
        p = unpad(p, 16)
    except Exception:
        pass
    t = p.decode("utf-8", "replace")
    try:
        return json.loads(t)
    except Exception:
        return {"_plain": t[:300]}


def build_post(biz):
    """按 interceptor.onRequest 的字节级顺序构造 post-data。"""
    mp = dict(biz)                              # 保持插入顺序：业务键在前
    mp["timestamp"] = int(time.time() * 1000)   # _getCurrentMicros()/1000 → 毫秒
    joined = "&".join("%s=%s" % (k, mp[k]) for k in sorted(mp.keys()))  # encodeComponent(key)=key
    mp["encode_sign"] = hashlib.md5((joined + SECRET).encode()).hexdigest()
    plain = json.dumps(mp, ensure_ascii=False, separators=(",", ":")).encode()
    ct = AES.new(REQ_KEY, AES.MODE_CBC, REQ_IV).encrypt(pad(plain, 16))
    return base64.b64encode(ct).decode(), mp


def call(path, biz, op=OP_DIRECT, extra_headers=None, timeout=15):
    post, mp = build_post(biz)
    hdrs = {"Content-Type": "application/json", "suffix": SUFFIX, "User-Agent": UA}
    if extra_headers:
        hdrs.update(extra_headers)
    req = urllib.request.Request(
        BASE + path.lstrip("/"),
        data=json.dumps({"post-data": post}).encode(),
        headers=hdrs, method="POST")
    try:
        with op.open(req, timeout=timeout) as r:
            return r.status, dec_resp(r.read()), mp
    except urllib.error.HTTPError as e:
        try:
            return e.code, dec_resp(e.read()), mp
        except Exception:
            return e.code, {"_err": "decode"}, mp
    except Exception as e:
        return 0, {"_err": str(e)[:60]}, mp


def show(tag, res):
    st, j, mp = res
    s = json.dumps(j, ensure_ascii=False)
    head = "%-34s HTTP %-4s %s" % (tag, st, s[:150])
    ok = isinstance(j, dict) and j.get("code") in (0, 200) and j.get("data")
    print(head + ("   ★★★ HIT" if ok else ""))
    return ok


if __name__ == "__main__":
    print("=" * 108)
    print("A. 首页推荐列表（3 键 biz，带 suffix 头）")
    print("=" * 108)
    hit = None
    for op_name, op in (("直连", OP_DIRECT), ("代理", OP_PROXY)):
        ok = show("listcache page=1 3键 [%s]" % op_name,
                  call("video/listcache", {"page": 1, "list_row": 120, "type": 4}, op))
        if ok:
            hit = ("video/listcache", {"page": 1, "list_row": 120, "type": 4}, op)
            break

    print()
    print("=" * 108)
    print("B. 分类 / 标签（无参 biz）")
    print("=" * 108)
    if not hit:
        for path in ("video/channel", "video/tags"):
            if show(path, call(path, {})):
                hit = (path, {}, OP_DIRECT)
                break

    print()
    print("=" * 108)
    print("C. 分区列表（4 键 biz，channel 0..6）")
    print("=" * 108)
    if not hit:
        for ch in range(0, 7):
            if show("listcache channel=%d" % ch,
                    call("video/listcache",
                         {"page": 1, "list_row": 120, "type": 4, "channel": ch})):
                hit = ("video/listcache",
                       {"page": 1, "list_row": 120, "type": 4, "channel": ch}, OP_DIRECT)
                break

    print()
    if hit:
        path, biz, op = hit
        print("===== 命中 %s · biz=%s =====" % (path, json.dumps(biz)))
        st, j, mp = call(path, biz, op)
        print("发送明文 map:", json.dumps(mp, ensure_ascii=False))
        print(json.dumps(j, ensure_ascii=False, indent=1)[:2500])
        open("tools/_dec/mdtv_ok.json", "w", encoding="utf-8").write(
            json.dumps(j, ensure_ascii=False, indent=1))
    else:
        print("仍未命中 —— 下一步：核对 interceptor 的 AESMode 是否 AESMode.cbc（Instance_AESMode@a81bc1）")
