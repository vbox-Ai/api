# -*- coding: utf-8 -*-
"""aijav 第一轮：直接套 mdtv 结案的两条经验（补 suffix 头 + 常量回二进制取原始字节）

asm：module/aijav/network/interceptor.dart @0x8d544c（onRequest）/ @0x8efe30（onResponse）
    SecRET  = "&NRkw0g3iJLDvw5tJ5PuVt5276z0SOuyL"        libapp.so @500125
    KEY     = "0XxdjmI55ZjjqQLO3nI7gGqrBP0Vz9jS"  (32B)  libapp.so @322372
    REQ_IV  = "RWf23muavYNWSdef"                 (16B)  libapp.so @944669
    头      suffix: "NWSdef"                             libapp.so @572092
    响应 IV = "RWf23muavY" + 响应体 suffix               @0x8efe68

上一版文档把 REQ_KEY 记成 16B 的 "RWf23muavYNWSdef"（当成 AES-128）—— 错：
那是 IV，请求/响应同一把 32B key "0Xxdjm…"。

接口：video/lists（首页/视频/搜索）、tag/lists、actor/lists、publisher/lists
     首页 biz {page, limit:54, type:8}；视频页 {page, limit:40, <idKey>:<id>}
"""
import base64
import hashlib
import json
import time
import urllib.error
import urllib.request

from Crypto.Cipher import AES
from Crypto.Util.Padding import pad, unpad

BASE = "https://newavapi.9xyrp3kg4b86.com/"
KEY = b"0XxdjmI55ZjjqQLO3nI7gGqrBP0Vz9jS"
REQ_IV = b"RWf23muavYNWSdef"
SECRET = "&NRkw0g3iJLDvw5tJ5PuVt5276z0SOuyL"
RESP_IV_HEAD = "RWf23muavY"
SUFFIX = "NWSdef"
UA = "Dart/3.4 (dart:io)"
OP = urllib.request.build_opener(urllib.request.ProxyHandler({}))


def dec_resp(raw_body):
    j = json.loads(raw_body.decode("utf-8", "replace"))
    if not isinstance(j, dict) or "data" not in j:
        return j
    d = j.get("data")
    if not isinstance(d, str):
        return j
    suf = str(j.get("suffix") or "")
    raw = base64.b64decode(d + "=" * (-len(d) % 4))
    iv = (RESP_IV_HEAD + suf).ljust(16, "\0")[:16].encode()
    if len(raw) % 16:
        return {"_err": "len%%16=%d" % (len(raw) % 16), "_suffix": suf}
    p = AES.new(KEY, AES.MODE_CBC, iv).decrypt(raw)
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
    ct = AES.new(KEY, AES.MODE_CBC, REQ_IV).encrypt(pad(plain, 16))
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
        return {"_err": str(e)[:70]}


def brief(tag, j, n=1):
    s = json.dumps(j, ensure_ascii=False)
    print("\n### %-28s %s" % (tag, s[:300]))
    d = j.get("data")
    if isinstance(d, dict):
        lst = d.get("data") or d.get("list") or []
        print("    total=%s per_page=%s current=%s last=%s 条数=%s"
              % (d.get("total"), d.get("per_page"), d.get("current_page"),
                 d.get("last_page"), len(lst) if isinstance(lst, list) else "?"))
    return j


out = {}
print("=" * 100)
print("A. 列表接口（首页 / 分类 / 演员 / 片商）")
print("=" * 100)
out["home"] = brief("video/lists 首页", call("video/lists", {"page": 1, "limit": 54, "type": 8}))
out["search"] = brief("video/lists 搜索", call("video/lists", {"page": 1, "limit": 20, "keyword": "麻豆"}))
out["tag"] = brief("tag/lists", call("tag/lists", {"page": 1, "limit": 40}))
out["actor"] = brief("actor/lists", call("actor/lists", {"page": 1, "limit": 40}))
out["publisher"] = brief("publisher/lists", call("publisher/lists", {"page": 1, "limit": 40}))

# 取到 id 后跑三类动态过滤
def first_id(j):
    d = j.get("data")
    if isinstance(d, dict):
        for k in ("data", "list"):
            if isinstance(d.get(k), list) and d[k]:
                return d[k][0].get("id")
    if isinstance(d, list) and d:
        return d[0].get("id")
    return None


tid = first_id(out["tag"])
aid = first_id(out["actor"])
pid = first_id(out["publisher"])
print("\n" + "=" * 100)
print("B. 动态键过滤  tag_id=%s actor_id=%s publisher_id=%s" % (tid, aid, pid))
print("=" * 100)
if tid:
    out["by_tag"] = brief("video/lists tag_id=%s" % tid,
                          call("video/lists", {"page": 1, "limit": 40, "tag_id": tid}))
if aid:
    out["by_actor"] = brief("video/lists actor_id=%s" % aid,
                            call("video/lists", {"page": 1, "limit": 40, "actor_id": aid}))
if pid:
    out["by_publisher"] = brief("video/lists publisher_id=%s" % pid,
                                call("video/lists", {"page": 1, "limit": 40, "publisher_id": pid}))

# 首个视频完整字段
home = out["home"]
hd = home.get("data") if isinstance(home.get("data"), dict) else {}
items = hd.get("data") or hd.get("list") or []
if items:
    print("\n### 首条完整字段")
    print(json.dumps(items[0], ensure_ascii=False, indent=1)[:1500])

open("tools/_dec/aijav_probe.json", "w", encoding="utf-8").write(
    json.dumps(out, ensure_ascii=False, indent=1))
print("\n已写 tools/_dec/aijav_probe.json")
