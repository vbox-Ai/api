# -*- coding: utf-8 -*-
"""hxsp（红杏视频）协议实现 —— 签名链完整还原，服务端可达。

状态：请求可构造并到达服务端业务层，但服务端对任意非空 ct 返回固定 "10"。
      详见 docs/hxsp攻坚报告.md

关键约束：
  · Python OpenSSL 与该 CDN 握手不兼容 → 必须用 curl 子进程发请求
  · 响应解密与请求加密用同一对 key/iv

用法：
  python tools/hxsp_client.py            # 自检：构造并发送一次请求
  python tools/hxsp_client.py <path>     # 指定接口
"""
import base64
import hashlib
import json
import os
import subprocess
import sys
import tempfile
import time
import uuid as _uuid

from cryptography.hazmat.primitives import padding
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes

sys.stdout.reconfigure(encoding="utf-8")

# ---------------------------------------------------------------- 常量
HOST = "https://hxapi.ruueyek.com"
HOST_ORIGIN = "http://172.247.132.138"       # 反汇编硬编码的源站，同一后端

TOKEN = ("eyJhbGciOiJIUzUxMiJ9.eyJzdWIiOiIyMDIzMTIwNjQ2NzQ5NzE5IiwiZXhwIjoyMzA2NjY0Nzc1LCJpYXQiOjE3MDE4NjQ3NzUsIm1hdGNoSWQiOiI1NTIxZTVhMTcwNTk0OGY0In0"
         ".UP5S-7Kyxr1DVjBSxO0fIvPAjOUqfRbdz_dOo-8MuXZ4cfcGIShrBMn-OS_0988Nw2QdiUGkg31U9jSCG0v3bw")

KEY = b"W$S3skNwm3zkHXqd"
IV = b"ZV8^Vg!aSyk!uRNh"
SALT = "b7flnSQP98989988fMEQXhhG"
MATCH_ID = "4310ced81499c24b"
M2 = "a4a099fc3c66bf328caa4ce4d5268c0b"
NONCE_FIXED = "9f2032f4-ed31-42f3-84f4-0a2ceee60854"

CURL = r"C:\Windows\System32\curl.exe"
PROXY = "http://127.0.0.1:7890"

# 接口（反汇编全量提取）
API = {
    "pubConfig":        "appApi/getPubConfig",
    "competProduct":    "appApi/index/competitiveProductList",
    "labelClassify":    "appApi/label/getLabelClassify",
    "labelList":        "appApi/label/getLabelListWithClassifyId",
    "labelProduct":     "appApi/label/getLabelProducList",
    "masterChannel":    "appApi/subscribe/masterChannel",
    "channelList":      "appApi/channel/getCartoonChannelList",
    "channelProduct":   "appApi/channel/getCartoonProductList",
    "shortVideo":       "appApi/index/shortVideo",
    "screeningList":    "appApi/index/screeningSearchList",
    "videoDetail":      "appApi/detail/getVideoDetail",
    "actorPage":        "appApi/actor/filterActorPage",
    "actorProduct":     "appApi/getActorProductList",
    "searchLong":       "appApi/difference/search/searchLongVideoPage",
    "searchShort":      "appApi/difference/search/searchShortVideoPage",
}


def _dumps(o):
    return json.dumps(o, ensure_ascii=False, separators=(",", ":"))


def build_map(biz=None, token=None):
    """构造参数字典并补 sign。biz 为业务参数，会合并进固定头。"""
    m = {
        "appVersion": "5.3",
        "client": "1",
        "tenant": "05",
        "phoneIp": "10.0.0.0",
        "matchid": MATCH_ID,
        "m3": "1",
        "m2": M2,
        "token": token if token is not None else TOKEN,
        "timestamp": str(int(time.time() * 1000)),
        "nonce": str(_uuid.uuid4()),
    }
    if biz:
        m.update(biz)
    ordered = {k: m[k] for k in sorted(m)}
    ordered["sign"] = hashlib.md5((_dumps(ordered) + SALT).encode()).hexdigest()
    return ordered


def encrypt(obj):
    p = padding.PKCS7(128).padder()
    data = p.update(_dumps(obj).encode()) + p.finalize()
    e = Cipher(algorithms.AES(KEY), modes.CBC(IV)).encryptor()
    return base64.b64encode(e.update(data) + e.finalize()).decode()


def decrypt(text):
    t = str(text).strip().strip('"')
    if not t:
        return None
    try:
        raw = base64.b64decode(t + "=" * (-len(t) % 4))
    except Exception:
        return None
    if not raw or len(raw) % 16:
        return None
    try:
        d = Cipher(algorithms.AES(KEY), modes.CBC(IV)).decryptor()
        out = d.update(raw) + d.finalize()
        n = out[-1]
        if 1 <= n <= 16:
            out = out[:-n]
        return out.decode("utf-8", "replace")
    except Exception:
        return None


def post_raw(host, path, payload, timeout=30, proxy=PROXY):
    """用 curl 发 POST（Python urllib 与本 CDN TLS 不兼容）。返回 (status, body)。"""
    cmd = [CURL, "-s", "-S", "--max-time", str(timeout),
           "-X", "POST", host.rstrip("/") + "/" + path.lstrip("/"),
           "-H", "Content-Type: application/json",
           "-H", "Accept: application/json",
           "-H", "User-Agent: okhttp/4.9.0",
           "-H", "Authorization: Bearer_" + TOKEN]
    if proxy:
        cmd += ["--proxy", proxy]
    fd, p = tempfile.mkstemp()
    os.close(fd)
    with open(p, "wb") as f:
        f.write(payload.encode("utf-8"))
    cmd += ["--data-binary", "@" + p, "-w", "\n__S__%{http_code}"]
    try:
        r = subprocess.run(cmd, capture_output=True, timeout=timeout + 15)
        out = r.stdout.decode("utf-8", "replace")
        if "__S__" in out:
            b, _, s = out.rpartition("__S__")
            return s.strip(), b.strip()
        return "ERR", r.stderr.decode("utf-8", "replace")[:200]
    finally:
        try:
            os.unlink(p)
        except OSError:
            pass


def call(path, biz=None, token=None, host=None):
    """标准调用：构造 -> 加密 -> 发送 -> 尝试解密。返回 dict 或原始文本。"""
    ct = encrypt(build_map(biz, token))
    status, body = post_raw(host or HOST, path, _dumps({"ct": ct}))
    plain = decrypt(body)
    if plain:
        try:
            return json.loads(plain)
        except Exception:
            return {"_raw": plain, "_status": status}
    return {"_raw": body, "_status": status}


if __name__ == "__main__":
    path = sys.argv[1] if len(sys.argv) > 1 else API["pubConfig"]
    print("接口:", path)

    obj = build_map({"oprationType": "1", "pageIndex": 1, "pageSize": 20})
    ct = encrypt(obj)
    print("明文长度:", len(_dumps(obj)), " ct 长度:", len(ct))
    print("往返自检:", decrypt(ct) == _dumps(obj))

    status, body = post_raw(HOST, path, _dumps({"ct": ct}))
    print("\nHTTP %s  响应: %r" % (status, body[:200]))
    plain = decrypt(body)
    print("解密结果:", plain[:300] if plain else "<不是 AES 密文>")
