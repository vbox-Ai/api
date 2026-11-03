# -*- coding: utf-8 -*-
"""javdb 第一轮：按 JavDbInterceptor::onRequest 还原 jdsignature

asm：module/javdb/network/interceptor.dart @0x8df080（size 0x1b0，只有 30 来条指令）
    ts    = micros/1000/1000          → **秒**
    first = md5( f"{ts}{SECRET}" )    ← SECRET 是 interceptor 的 field_7
    header: accept-language = "zh"
    header: jdsignature     = f"{ts}.lpw6vgqzsp.{first}"

SECRET 来自 service.dart @0x7b9fa8（构造时 StoreField r1->field_7）：
    71cf27bb3c0bcdf207b64abecddc970098c7421ee7203b9cdae54478478a199e7d5a6e1a57691123c1a931c057842fb73ba3b3c83bcd69c17ccf174081e3d8aa

接口：api/v1/movies/、api/v1/movies/tags、api/v2/tags、api/v2/search、api/v1/actors、api/v1/makers、api/v4/movies/
"""
import hashlib
import json
import time
import urllib.error
import urllib.parse
import urllib.request

BASE = "https://jdforrepam.com"
SECRET = ("71cf27bb3c0bcdf207b64abecddc970098c7421ee7203b9cdae54478478a199e7d5a6e1a57691123c1a931c0"
          "57842fb73ba3b3c83bcd69c17ccf174081e3d8aa")
UA = "Mozilla/5.0 (iPhone; CPU iPhone OS 18_5 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/18.5 Mobile/15E148 Safari/604.1"
OP = urllib.request.build_opener(urllib.request.ProxyHandler({}))


def sign():
    ts = int(time.time())
    first = hashlib.md5(("%s%s" % (ts, SECRET)).encode()).hexdigest()
    return ts, "%s.lpw6vgqzsp.%s" % (ts, first)


def call(path, params=None, ts_unit="s"):
    ts, sig = sign()
    if ts_unit == "ms":
        ts = int(time.time() * 1000)
        sig = "%s.lpw6vgqzsp.%s" % (ts, hashlib.md5(("%s%s" % (ts, SECRET)).encode()).hexdigest())
    url = BASE + "/" + path.lstrip("/")
    if params:
        url += "?" + urllib.parse.urlencode(params)
    req = urllib.request.Request(url, headers={
        "User-Agent": UA, "accept-language": "zh", "jdsignature": sig,
        "Accept": "application/json"})
    try:
        with OP.open(req, timeout=20) as r:
            return r.status, r.read()
    except urllib.error.HTTPError as e:
        try:
            return e.code, e.read()
        except Exception:
            return e.code, b""
    except Exception as e:
        return 0, str(e)[:80].encode()


if __name__ == "__main__":
    print("%-30s %-6s %-6s %s" % ("路径", "参数", "HTTP", "响应摘要"))
    print("-" * 110)
    cases = [
        ("api/v1/movies/tags", None),
        ("api/v2/tags", None),
        ("api/v1/actors", {"page": 1}),
        ("api/v1/makers", {"page": 1}),
        ("api/v1/movies/recent", {"page": 1}),
        ("api/v1/movies/hot", {"page": 1}),
        ("api/v4/movies/recent", {"page": 1}),
        ("api/v2/search", {"q": "SSIS", "page": 1}),
    ]
    for path, params in cases:
        for unit in ("s",):
            st, body = call(path, params, unit)
            txt = body.decode("utf-8", "replace")
            print("%-30s %-6s %-6s %s" % (
                path, unit, st, txt[:150].replace("\n", " ")))
            if st == 200 and txt.lstrip()[:1] in ("{", "["):
                open("tools/_dec/javdb_%s.json" % path.replace("/", "_"), "w",
                     encoding="utf-8").write(txt)
