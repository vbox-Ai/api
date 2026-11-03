# -*- coding: utf-8 -*-
"""qysq 第五轮：响应解密（asGjCrypto 结构还原 + 真实样本爆破）

asm：avbox/util/crypto_util.dart::asGjCrypto @0x7237f0（size 0x55c）
关键骨架（逐段读出）：

    P  = utf8("vEukA&w15z4VAD3kAY#fkL#rBnU!WDhN")     # 32B 固定盐
    D  = base64Decode(resp["data"])
    X  = P + D[0:24]                                   # 0x7239ac~0x7239dc：sublist(D,0,24) 拼到 P 后
    H1 = sha256(X)                                     # 0x723a34
    L2 = H1[0:16]                 → AES Key            # 0x723b34 sublist(0,16)
    L3 = H1[8:24]                 → IV                 # 0x723b5c sublist(8, 24)（blutter 的 0x30 是 Smi 编码即 24）
    ct = D[12:]                                        # 0x723cf0 Encrypted(D.sublist(12))
    plain = AES-CBC-decrypt(ct, Key(L2), IV(L3))       # 0x723d34

本脚本先用真实接口拿一份样本（签名链已 100% 还原），
再在「nonce 长度 × key 切片 × iv 切片」的小空间里核对上面这套解读，
命中即以 JSON 解析成功为准。
"""
import base64
import binascii
import hashlib
import hmac
import json
import time
import urllib.request
import uuid

from Crypto.Cipher import AES

BASE = "https://d1kmvkv4iwtiup.cloudfront.net"
SECRET = "gH3nA7fR9tV1jY6z"
DEV_UA = "DevType=Apple iPhone mobile;SysType=light;Ver=2.1.2;BuildID=Mobile Safari 18.5"
BR_UA = ("Mozilla/5.0 (iPhone; CPU iPhone OS 18_5 like Mac OS X) AppleWebKit/605.1.15 "
         "(KHTML, like Gecko) Version/18.5 Mobile/15E148 Safari/604.1")
P = b"vEukA&w15z4VAD3kAY#fkL#rBnU!WDhN"      # asGjCrypto 里的 32B 盐
OP = urllib.request.build_opener(urllib.request.ProxyHandler({}))

TOKEN = ("eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJhdWQiOiJwdWJsaWMiLCJleHAiOjE3OTM4NTgxNjIs"
         "Imlzc3VlciI6ImNvbS5idXR0ZXJmbHkiLCJzdWIiOiJhc2lnbiIsInVzZXJJZCI6NTY3NzU4MX0."
         "yjzuUUUK1hlQBzlTQ703ZYemCvfL97EYsQNUCyEVET4")


def signed_get(path):
    ts = int(time.time())
    nonce = str(uuid.uuid4())
    msg = "%s&/%s&%s&%s&%s" % (TOKEN, path.lstrip("/"), DEV_UA, ts, nonce)
    sign = hmac.new(SECRET.encode(), msg.encode(), hashlib.sha1).hexdigest()
    req = urllib.request.Request(
        BASE + "/" + path.lstrip("/"),
        headers={
            "X-User-Agent": DEV_UA,
            "user-agent": BR_UA,
            "authorization": "Bearer " + TOKEN,
            "x-api-key": "timestamp=%s;sign=%s;nonce=%s" % (ts, sign, nonce),
            "Accept": "application/json",
        })
    with OP.open(req, timeout=20) as r:
        return r.read()


def signed_post(path, body=None):
    ts = int(time.time())
    nonce = str(uuid.uuid4())
    msg = "%s&/%s&%s&%s&%s" % (TOKEN, path.lstrip("/"), DEV_UA, ts, nonce)
    sign = hmac.new(SECRET.encode(), msg.encode(), hashlib.sha1).hexdigest()
    data = json.dumps(body or {}).encode()
    req = urllib.request.Request(
        BASE + "/" + path.lstrip("/"), data=data, method="POST",
        headers={
            "X-User-Agent": DEV_UA,
            "user-agent": BR_UA,
            "authorization": "Bearer " + TOKEN,
            "x-api-key": "timestamp=%s;sign=%s;nonce=%s" % (ts, sign, nonce),
            "Content-Type": "application/json",
            "Accept": "application/json",
        })
    with OP.open(req, timeout=20) as r:
        return r.read()


def try_decrypt(D):
    """按 asm 解读逐档验证，返回 (标签, 明文)。"""
    P_ = P
    cands = []
    for nlen in (12, 16, 24):
        nonce = D[:nlen]
        H = hashlib.sha256(P_ + nonce).digest()
        keys = {
            "H[0:16]": H[0:16], "H[8:24]": H[8:24], "H[16:32]": H[16:32],
            "H[all]": H,
        }
        for kn, k in keys.items():
            for vn, iv in (("H[8:24]", H[8:24]), ("H[0:16]", H[0:16]),
                           ("H[16:32]", H[16:32]), ("zero", b"\0" * 16),
                           ("D0", D[:16]), ("P0", P_[:16])):
                if len(k) not in (16, 24, 32) or len(iv) != 16:
                    continue
                for cut in (nlen, 12, 16, 24):
                    ct = D[cut:]
                    if not ct or len(ct) % 16:
                        continue
                    try:
                        pt = AES.new(k, AES.MODE_CBC, iv).decrypt(ct)
                    except Exception:
                        continue
                    if pt[:1] in (b"{", b"[") or pt[:2] == b"\x1f\x8b":
                        cands.append(("nonce=%d key=%s iv=%s cut=%d" % (nlen, kn, vn, cut), pt))
                        return cands
    return cands


if __name__ == "__main__":
    raw = b""
    for path in ("api/app/media/home", "api/app/ping/config"):
        try:
            if "home" in path:
                raw = signed_post(path, {})
            else:
                raw = signed_get(path)
            print("[fetch] %-24s %d bytes" % (path, len(raw)))
            break
        except Exception as e:
            print("[fetch] %s 失败 %s" % (path, str(e)[:60]))

    if not raw:
        raise SystemExit("没拿到样本")

    try:
        j = json.loads(raw.decode("utf-8", "replace"))
    except Exception:
        print("响应不是 JSON：", raw[:200])
        raise SystemExit(1)

    print("[envelope] code=%s keys=%s" % (j.get("code"), list(j.keys())))
    d = j.get("data")
    if not isinstance(d, str):
        print("data 不是密文串：", json.dumps(j, ensure_ascii=False)[:400])
        raise SystemExit(0)

    open("tools/_dec/qysq_raw_sample.json", "w", encoding="utf-8").write(
        json.dumps({"code": j.get("code"), "data_head": d[:80], "len_b64": len(d)},
                   ensure_ascii=False, indent=1))

    D = base64.b64decode(d + "=" * (-len(d) % 4))
    print("[bytes] 密文 %d 字节   %%16=%d   D[0:24]=%s" % (len(D), len(D) % 16, D[:24].hex()))

    hits = try_decrypt(D)
    if hits:
        tag, pt = hits[0]
        print("\n★ 命中：%s" % tag)
        print(pt[:600].decode("utf-8", "replace"))
        open("tools/_dec/qysq_plain.json", "wb").write(pt)
    else:
        print("\n未命中 —— 需要继续核 nonce/切片；已保存样本供下一轮")
