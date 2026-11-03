# -*- coding: utf-8 -*-
"""mdtv：用自身常量（-p9B[~PnPs / Vq234z... / JGDZMX）爆破 key×iv 派生"""
import base64
import hashlib
import json
import urllib.error
import urllib.request

from Crypto.Cipher import AES
from Crypto.Util.Padding import unpad

OP = urllib.request.build_opener(urllib.request.ProxyHandler({}))
UA = ("Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) "
      "AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Mobile/15E148 Safari/604.1")
BASE = "https://spi.d5c4a712.com"

K_LONG = b"Vq234zBeSdGgYXzVTEfnnjjdmaTkk7A4"    # 32
K_SHORT = b"-p9B[~PnPsJGDZMX"                    # 16
IV_HEAD = b"-p9B[~PnPs"                          # 9
SUF_TAIL = b"JGDZMX"                             # 6


def get(path):
    try:
        with OP.open(urllib.request.Request(BASE + path, headers={
                "User-Agent": UA, "Accept": "application/json"}), timeout=15) as r:
            return json.loads(r.read().decode("utf-8", "replace"))
    except Exception:
        return {}


j = get("/video/list")
d = j.get("data") or ""
suf = str(j.get("suffix") or "")
raw = base64.b64decode(d + "=" * (-len(d) % 4))
print("密文 %d 字节 %%16=%d  suffix=%s" % (len(raw), len(raw) % 16, suf))
print("suffix hex len=%d" % len(suf))

sb = suf.encode()
KEYS = {"K_LONG32": K_LONG, "K_SHORT16": K_SHORT,
        "md5short": hashlib.md5(K_SHORT).digest(),
        "sha1short16": hashlib.sha1(K_SHORT).digest()[:16]}
# IV 候选（必须 16 字节）
IVS = {
    "head+suf": (IV_HEAD + sb)[:16],
    "suf+head": (sb + IV_HEAD)[:16],
    "head+suf_pad0": (IV_HEAD + sb).ljust(16, b"\x00"),
    "head+tail": (IV_HEAD + SUF_TAIL)[:16],
    "short16": K_SHORT,
    "long[:16]": K_LONG[:16],
    "zero": b"\x00" * 16,
    "suf_pad": sb.ljust(16, b"\x00"),
}
for nm, iv in IVS.items():
    if len(iv) != 16:
        IVS[nm] = iv.ljust(16, b"\x00")[:16]

if len(raw) % 16:
    # 剥尾/头对齐
    for cut in (12, 4, 16, 8):
        if (len(raw) - cut) % 16 == 0:
            raw = raw[:len(raw) - cut]
            print("剥尾 %d 字节后对齐" % cut)
            break

print("\n爆破：")
hit = None
for kn, kb in KEYS.items():
    if len(kb) not in (16, 24, 32):
        continue
    for ivn, iv in IVS.items():
        try:
            p = AES.new(kb, AES.MODE_CBC, iv).decrypt(raw)
            for cand in (p, p[16:]):
                try:
                    t = unpad(cand, 16).decode("utf-8", "replace")
                except Exception:
                    t = cand.decode("utf-8", "replace")
                if t.lstrip()[:1] in ("{", "["):
                    json.loads(t.lstrip())
                    hit = (kn, ivn, t)
                    break
            if hit:
                break
        except Exception:
            pass
    if hit:
        break

if hit:
    kn, ivn, t = hit
    print("★★★ 命中 key=%s iv=%s" % (kn, ivn))
    print(t[:600])
    open("tools/_dec/mdtv_list_plain.json", "w", encoding="utf-8").write(t)
else:
    print("未命中。mdtv 与 aijav 共用签名链，但响应密钥派生待细读 interceptor。")
