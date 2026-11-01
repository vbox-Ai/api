# -*- coding: utf-8 -*-
"""判定 "10" 的性质：是否与密文内容完全无关（= 固定回执）。

方法：同一结构，只改变密文中一个字节，观察响应是否恒定。
若恒定 -> 服务端根本没解我们的密文（格式/密钥/包装不对）
若变化 -> 部分解密成功
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
PATH = "appApi/getPubConfig"


def dumps(o):
    return json.dumps(o, ensure_ascii=False, separators=(",", ":"))


def make(extra=None):
    m = {
        "appVersion": "5.3", "client": "1", "tenant": "05", "phoneIp": "10.0.0.0",
        "matchid": "4310ced81499c24b", "m3": "1",
        "m2": "a4a099fc3c66bf328caa4ce4d5268c0b", "token": TOKEN,
        "timestamp": str(int(time.time() * 1000)), "nonce": str(_uuid.uuid4()),
    }
    if extra:
        m.update(extra)
    o = {k: m[k] for k in sorted(m)}
    o["sign"] = hashlib.md5((dumps(o) + SALT).encode()).hexdigest()
    return dumps(o)


def enc_bytes(plain):
    p = padding.PKCS7(128).padder()
    data = p.update(plain) + p.finalize()
    e = Cipher(algorithms.AES(KEY), modes.CBC(IV)).encryptor()
    return e.update(data) + e.finalize()


if __name__ == "__main__":
    raw = enc_bytes(make().encode())
    print("密文长度:", len(raw), " base64 长度:", len(base64.b64encode(raw)))

    results = []
    # 多次同一请求
    for i in range(2):
        st, resp = post(HOST + "/" + PATH, {"ct": base64.b64encode(raw).decode()}, AUTH)
        results.append((st, resp))
    print("同密文两次:", results)

    # 翻转最后一字节
    bad = bytearray(raw)
    bad[-1] ^= 0xFF
    st, resp = post(HOST + "/" + PATH, {"ct": base64.b64encode(bytes(bad)).decode()}, AUTH)
    print("翻转末字节:", (st, resp))

    # 完全不同长度
    for n in (16, 32, 64, 128, 256):
        fake = bytes(n)
        st, resp = post(HOST + "/" + PATH, {"ct": base64.b64encode(fake).decode()}, AUTH)
        print("全零密文 %3d 字节:" % n, (st, resp))

    # 明文形态：空 JSON
    raw2 = enc_bytes(b"{}")
    st, resp = post(HOST + "/" + PATH, {"ct": base64.b64encode(raw2).decode()}, AUTH)
    print("明文 {} :", (st, resp))
