# -*- coding: utf-8 -*-
"""最终结论验证：gzip 用真实 DEFLATE 解压，确认 6868 响应可完整解出。
用 zlib.decompressobj(wbits=-15) 让解码从 deflate 流继续，容忍头部/尾部异常。"""
import base64
import json
import os
import sys
import zlib

from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes

sys.stdout.reconfigure(encoding="utf-8")
KEY = b"8992d27bceae2962"
IV = b"62233532ac9029c6"
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "_dec")


def load_all():
    items = []
    for b, d, f in os.walk(r"C:\Users\Administrator\Downloads"):
        if "basic" not in f or "response_body" not in f:
            continue
        u = open(os.path.join(b, "basic"), encoding="utf-8", errors="replace").read().strip()
        if "6868" not in u:
            continue
        items.append((u, open(os.path.join(b, "response_body"), "rb").read(), b))
    return items


def dechunk(raw):
    out, i = b"", 0
    if b"\r\n" not in raw[:20]:
        return raw
    while i < len(raw):
        j = raw.find(b"\r\n", i)
        if j < 0:
            return out or raw
        try:
            size = int(raw[i:j].split(b";")[0], 16)
        except ValueError:
            return raw
        i = j + 2
        if size == 0:
            break
        out += raw[i:i + size]
        i += size + 2
    return out or raw


def cbc_dec(ct):
    prev, out = IV, b""
    for k in range(0, len(ct) - 15, 16):
        d = Cipher(algorithms.AES(KEY), modes.ECB()).decryptor()
        p = d.update(ct[k:k + 16]) + d.finalize()
        out += bytes(a ^ b for a, b in zip(p, prev))
        prev = ct[k:k + 16]
    return out


def gunzip_soft(b):
    if b[:2] != b"\x1f\x8b":
        return None
    # 跳过 10 字节头（fname 标志位可能更复杂，这里用 zlib 原始流）
    for skip in range(10, 16):
        try:
            z = zlib.decompressobj(-15)
            return z.decompress(b[skip:])
        except Exception:
            continue
    return None


def main():
    os.makedirs(OUT, exist_ok=True)
    for u, raw, b in load_all():
        body = dechunk(raw)
        t = "".join(body.decode("utf-8", "replace").strip().strip('"').split())
        if not t:
            continue
        ct = base64.b64decode(t + "=" * (-len(t) % 4))
        if len(ct) % 16:
            continue
        plain = cbc_dec(ct)
        g = gunzip_soft(plain)
        tag = "gz"
        if g is None:
            g = plain
            tag = "raw"
        try:
            txt = g.decode("utf-8")
        except Exception:
            print("SKIP(undecodable) %s" % u)
            continue
        txt = txt.strip()
        if not txt.startswith(("{", "[")):
            print("SKIP(nonjson) %s  head=%r" % (u, txt[:60]))
            continue
        name = u.split("6868/")[-1].replace("/", "_").replace("?", "_")
        fp = os.path.join(OUT, name + ".json")
        open(fp, "w", encoding="utf-8").write(txt)
        print("OK  %-44s %s  %d B -> %s" % (u, tag, len(txt), os.path.basename(fp)))


if __name__ == "__main__":
    main()
