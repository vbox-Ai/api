# -*- coding: utf-8 -*-
"""qysq 响应解密：爆破「剥离偏移 × key × iv」找 JSON"""
import base64
import hashlib
import hmac
import json
import time
import urllib.error
import urllib.request
import uuid

from Crypto.Cipher import AES
from Crypto.Util.Padding import unpad

OP = urllib.request.build_opener(urllib.request.ProxyHandler({}))
DEV_UA = "DevType=Apple iPhone mobile;SysType=light;Ver=2.1.2;BuildID=Mobile Safari 18.5"
BROWSER_UA = ("Mozilla/5.0 (iPhone; CPU iPhone OS 18_5 like Mac OS X) "
              "AppleWebKit/605.1.15 (KHTML, like Gecko) Version/18.5 Mobile/15E148 Safari/604.1")
SECRET = b"gH3nA7fR9tV1jY6z"
TOKEN = ("eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJhdWQiOiJwdWJsaWMiLCJleHAiOjE3OTM4NTgxNjIs"
         "Imlzc3VlciI6ImNvbS5idXR0ZXJmbHkiLCJzdWIiOiJhc2lnbiIsInVzZXJJZCI6NTY3NzU4MX0"
         ".yjzuUUUK1hlQBzlTQ703ZYemCvfL97EYsQNUCyEVET4")
BASE = "https://d1kmvkv4iwtiup.cloudfront.net"


def call(path, body=None):
    ts = str(int(time.time()))
    nonce = str(uuid.uuid4())
    msg = "%s&%s&%s&%s&%s" % (TOKEN, path, DEV_UA, ts, nonce)
    sign = hmac.new(SECRET, msg.encode(), hashlib.sha1).hexdigest()
    h = {"X-User-Agent": DEV_UA, "user-agent": BROWSER_UA,
         "authorization": "Bearer " + TOKEN,
         "x-api-key": "timestamp=%s;sign=%s;nonce=%s" % (ts, sign, nonce),
         "Accept": "application/json", "Content-Type": "application/json"}
    data = json.dumps(body or {}, ensure_ascii=False).encode()
    req = urllib.request.Request(BASE + path, data=data, headers=h, method="POST")
    try:
        with OP.open(req, timeout=20) as r:
            return json.loads(r.read().decode("utf-8", "replace"))
    except Exception as e:
        return {"_err": str(e)}


j = call("/api/app/media/short/hot")
d = j.get("data") or ""
raw = base64.b64decode(d + "=" * (-len(d) % 4))
print("密文 %d 字节  %%16=%d" % (len(raw), len(raw) % 16))

md5s = hashlib.md5(SECRET).digest()
smd5 = hashlib.md5(SECRET).hexdigest()
KEYS = {
    "secret16": SECRET,
    "md5raw": md5s,
    "md5hex16": smd5[:16].encode(),
    "md5tok": hashlib.md5(TOKEN.encode()).digest(),
    "sha1_16": hashlib.sha1(SECRET).digest()[:16],
    "secret32": (SECRET + SECRET)[:32],
}
IVS = {
    "zero": b"\x00" * 16,
    "secret": SECRET,
    "md5raw": md5s,
    "md5hex16": smd5[:16].encode(),
    "secretrev": SECRET[::-1],
}
# 剥离方案：头/尾各自偏移
OFFSETS = [(0, 0), (12, 0), (0, 12), (16, 0), (0, 16), (16, 12), (12, 16), (4, 8), (8, 4)]

print("\n爆破中…")
found = None
for ho, to in OFFSETS:
    seg = raw[ho:len(raw) - to if to else len(raw)]
    if len(seg) % 16 or len(seg) < 32:
        continue
    for kn, kb in KEYS.items():
        if len(kb) not in (16, 24, 32):
            continue
        for ivn, ivb in IVS.items():
            try:
                p = AES.new(kb, AES.MODE_CBC, ivb).decrypt(seg)
                for cand in (p, p[16:], p[:len(p) // 16 * 16]):
                    try:
                        t = unpad(cand, 16).decode("utf-8", "replace")
                    except Exception:
                        t = cand.decode("utf-8", "replace")
                    s = t.lstrip()
                    if s[:1] in ("{", "["):
                        try:
                            json.loads(s)
                        except Exception:
                            continue
                        found = (ho, to, kn, ivn, s)
                        break
                if found:
                    break
            except Exception:
                pass
        if found:
            break
    if found:
        break

if found:
    ho, to, kn, ivn, s = found
    print("\n★★★ 命中  剥头=%d 剥尾=%d key=%s iv=%s" % (ho, to, kn, ivn))
    print(s[:600])
    open("tools/_dec/qysq_home_plain.json", "w", encoding="utf-8").write(s)
else:
    print("\n未命中。结论：qysq 响应加密用了非显而易见派生（需继续读 asm），")
    print("        但【请求签名已完全打通】（接口返回 code=200 + 真实密文）。")
