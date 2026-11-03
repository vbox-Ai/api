# -*- coding: utf-8 -*-
"""mdtv 第六轮：拿到签名后跑通全部接口，固化字段结构

已被 r8 打通的两处修正：
  1) 请求头 `suffix: JGDZMX`（少了服务端解不开请求体 → 1002）
  2) 签名 secret 无反斜杠（libapp.so 偏移 367007 raw bytes 实证）→ 修正后 1001 消失

本轮目标：
  video/channel 分类、video/tags 标签、video/listcache 分页/分区/标签过滤、
  video/list 搜索、以及播放地址是否就是列表里的 video_url。
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
REQ_KEY = b"Vq234zBeSdGgYXzVTEfnnjjdmaTkk7A4"
REQ_IV = b"-p9B[~PnPsJGDZMX"
SECRET = "&m}q%ea6:LDcmS?aK)CeF287bPvd99@E,9Up^"
RESP_IV_HEAD = b"-p9B[~PnPs"
SUFFIX = "JGDZMX"
UA = "Dart/3.4 (dart:io)"
OP = urllib.request.build_opener(urllib.request.ProxyHandler({}))


def dec_resp(raw_body):
    j = json.loads(raw_body.decode("utf-8", "replace"))
    if not isinstance(j, dict) or "data" not in j:
        return j
    d = j["data"]
    suf = str(j.get("suffix") or "")
    raw = base64.b64decode(d + "=" * (-len(d) % 4))
    iv = (RESP_IV_HEAD + suf.encode()).ljust(16, b"\0")[:16]
    if len(raw) % 16:
        return {"_err": "len%%16=%d" % (len(raw) % 16)}
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


def call(path, biz=None):
    mp = dict(biz or {})
    mp["timestamp"] = int(time.time() * 1000)
    joined = "&".join("%s=%s" % (k, mp[k]) for k in sorted(mp.keys()))
    mp["encode_sign"] = hashlib.md5((joined + SECRET).encode()).hexdigest()
    plain = json.dumps(mp, ensure_ascii=False, separators=(",", ":")).encode()
    ct = AES.new(REQ_KEY, AES.MODE_CBC, REQ_IV).encrypt(pad(plain, 16))
    body = json.dumps({"post-data": base64.b64encode(ct).decode()}).encode()
    req = urllib.request.Request(
        BASE + path.lstrip("/"), data=body, method="POST",
        headers={"Content-Type": "application/json", "suffix": SUFFIX,
                 "User-Agent": UA})
    try:
        with OP.open(req, timeout=20) as r:
            return dec_resp(r.read())
    except urllib.error.HTTPError as e:
        try:
            return dec_resp(e.read())
        except Exception:
            return {"_http": e.code}
    except Exception as e:
        return {"_err": str(e)[:60]}


def peek(tag, j, depth=1):
    print("\n### %s" % tag)
    print(json.dumps(j, ensure_ascii=False)[:1200])


out = {}

# 1) 分类
ch = call("video/channel")
out["channel"] = ch
peek("video/channel", ch)

# 2) 标签
tg = call("video/tags")
out["tags"] = tg
peek("video/tags", tg)

# 3) 推荐列表第 1 / 2 页
p1 = call("video/listcache", {"page": 1, "list_row": 120, "type": 4})
out["list_p1"] = p1
d1 = p1.get("data") or {}
print("\n### listcache 推荐  page=1 → total=%s per_page=%s last_page=%s 条数=%d"
      % (d1.get("total"), d1.get("per_page"), d1.get("last_page"),
         len(d1.get("data") or [])))

p2 = call("video/listcache", {"page": 2, "list_row": 120, "type": 4})
d2 = p2.get("data") or {}
print("### listcache 推荐  page=2 → current=%s 条数=%d 首条 id=%s"
      % (d2.get("current_page"), len(d2.get("data") or []),
         (d2.get("data") or [{}])[0].get("id")))

# 4) 分区过滤
chans = []
cj = ch.get("data")
if isinstance(cj, list):
    chans = cj
elif isinstance(cj, dict) and isinstance(cj.get("data"), list):
    chans = cj["data"]
for c in (chans or [])[:3]:
    cid = c.get("id")
    r = call("video/listcache", {"page": 1, "list_row": 20, "type": 4, "channel": cid})
    dd = r.get("data") or {}
    print("### channel=%s(%s) → total=%s 条数=%d 首条=%s"
          % (cid, c.get("name"), dd.get("total"), len(dd.get("data") or []),
             ((dd.get("data") or [{}])[0]).get("title", "")[:26]))

# 5) 标签过滤
tags = []
tj = tg.get("data")
if isinstance(tj, list):
    tags = tj
elif isinstance(tj, dict) and isinstance(tj.get("data"), list):
    tags = tj["data"]
for t in (tags or [])[:3]:
    tid = t.get("id")
    r = call("video/listcache", {"page": 1, "list_row": 20, "type": 4, "tags": tid})
    dd = r.get("data") or {}
    print("### tags=%s(%s) → total=%s 条数=%d"
          % (tid, t.get("name"), dd.get("total"), len(dd.get("data") or [])))

# 6) 搜索
s = call("video/list", {"page": 1, "list_row": 20, "keyword": "麻豆"})
sd = s.get("data") or {}
print("\n### video/list 搜索 麻豆 → code=%s total=%s 条数=%d 首条=%s"
      % (s.get("code"), sd.get("total"), len(sd.get("data") or []),
         ((sd.get("data") or [{}])[0]).get("title", "")[:30]))

# 7) 播放地址来源确认
first = (d1.get("data") or [{}])[0]
print("\n### 首条完整字段")
print(json.dumps(first, ensure_ascii=False, indent=1)[:1200])

open("tools/_dec/mdtv_probe.json", "w", encoding="utf-8").write(
    json.dumps(out, ensure_ascii=False, indent=1))
print("\n已写 tools/_dec/mdtv_probe.json")
