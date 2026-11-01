# -*- coding: utf-8 -*-
"""hxsp 签名链 v3 —— 修正字段清单。

从反汇编精确提取的固定字段（注意大小写！）：

  appVersion = "5.3"
  client     = "1"
  tenant     = "05"
  phoneIp    = "0.0.0.0"   (随后被覆盖为 "10.0.0.0")
  matchid    = "4310ced81499c24b"    ← 全小写
  m3         = "1"
  m2         = "a4a099fc3c66bf328caa4ce4d5268c0b"
  token      = token_hxsp（去掉 Bearer_ 前缀后？）
  timestamp  = 13 位毫秒
  nonce      = uuid

  然后 addAll(业务参数 map)
  → SplayTreeMap 排序 → jsonEncode
  → sign = MD5(json + "b7flnSQP98989988fMEQXhhG")
  → ct = base64(AES-128-CBC(key="W$S3skNwm3zkHXqd", iv="ZV8^Vg!aSyk!uRNh", json(map)))
"""
import base64
import hashlib
import json
import sys
import time
import uuid as _uuid

from cryptography.hazmat.primitives import padding
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes

sys.path.insert(0, r"C:\Users\Administrator\Downloads\vboxapp\_remote_api\tools")
from _hxsp_http import post  # noqa: E402

sys.stdout.reconfigure(encoding="utf-8")

HOST = "https://hxapi.ruueyek.com"
TOKEN = ("eyJhbGciOiJIUzUxMiJ9.eyJzdWIiOiIyMDIzMTIwNjQ2NzQ5NzE5IiwiZXhwIjoyMzA2NjY0Nzc1LCJpYXQiOjE3MDE4NjQ3NzUsIm1hdGNoSWQiOiI1NTIxZTVhMTcwNTk0OGY0In0"
         ".UP5S-7Kyxr1DVjBSxO0fIvPAjOUqfRbdz_dOo-8MuXZ4cfcGIShrBMn-OS_0988Nw2QdiUGkg31U9jSCG0v3bw")
KEY = b"W$S3skNwm3zkHXqd"
IV = b"ZV8^Vg!aSyk!uRNh"
SALT = "b7flnSQP98989988fMEQXhhG"
AUTH = {"Authorization": "Bearer_" + TOKEN}


def dumps(o):
    return json.dumps(o, ensure_ascii=False, separators=(",", ":"))


def build_map(token_value="", extra=None):
    m = {
        "appVersion": "5.3",
        "client": "1",
        "tenant": "05",
        "phoneIp": "10.0.0.0",
        "matchid": "4310ced81499c24b",
        "m3": "1",
        "m2": "a4a099fc3c66bf328caa4ce4d5268c0b",
        "token": token_value,
        "timestamp": str(int(time.time() * 1000)),
        "nonce": str(_uuid.uuid4()),
    }
    if extra is not None:
        m.update(extra)
    return m


def sign_map(m):
    o = {k: m[k] for k in sorted(m)}
    o["sign"] = hashlib.md5((dumps(o) + SALT).encode()).hexdigest()
    return o


def enc(o):
    p = padding.PKCS7(128).padder()
    data = p.update(dumps(o).encode()) + p.finalize()
    e = Cipher(algorithms.AES(KEY), modes.CBC(IV)).encryptor()
    return base64.b64encode(e.update(data) + e.finalize()).decode()


def dec(text):
    t = str(text).strip().strip('"')
    if not t:
        return "<empty>"
    try:
        raw = base64.b64decode(t + "=" * (-len(t) % 4))
    except Exception:
        return t
    if not raw or len(raw) % 16:
        return "<len=%d>" % len(raw)
    try:
        d = Cipher(algorithms.AES(KEY), modes.CBC(IV)).decryptor()
        out = d.update(raw) + d.finalize()
        n = out[-1]
        if 1 <= n <= 16:
            out = out[:-n]
        return out.decode("utf-8", "replace")
    except Exception as e:
        return "<dec:%s>" % e


def probe(path, token_value="", extra=None, no_sign=False, tag=""):
    m = build_map(token_value, extra)
    o = {k: m[k] for k in sorted(m)} if no_sign else sign_map(m)
    ct = enc(o)
    st, resp = post(HOST + "/" + path, {"ct": ct}, AUTH)
    out = dec(resp)
    print("[%-38s] %-4s %s" % (tag or path, st, out[:220]))
    return out


if __name__ == "__main__":
    print("=== token 字段三种取值 ===")
    probe("appApi/getPubConfig", token_value="", tag="token=''")
    probe("appApi/getPubConfig", token_value=TOKEN, tag="token=JWT")
    probe("appApi/getPubConfig", no_sign=True, tag="无 sign")

    print("\n=== 加上业务参数 ===")
    probe("appApi/index/competitiveProductList",
          extra={"oprationType": "1", "pageIndex": 1, "pageSize": 20},
          tag="competitiveProductList")
    probe("appApi/subscribe/masterChannel",
          extra={"pageIndex": 1, "pageSize": 20}, tag="masterChannel")

    print("\n=== 先试探 ct 是否已能被解密 ===")
    probe("appApi/getPubConfig", tag="getPubConfig 基线")
