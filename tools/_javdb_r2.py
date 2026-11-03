# -*- coding: utf-8 -*-
"""javdb 第二轮：签名已通，本轮只做「参数取值/子路径」发现

已知（r1 实测）：
  api/v2/search?q=&page=  → success:1，返回 movies（签名 100% 正确）
  api/v1/movies/tags      → 缺 filter_by
  api/v2/tags             → 缺 type
  api/v1/actors|makers    → 缺 type
  api/v1/movies/recent|hot → 404；api/v4/movies/recent → ResourceNotFound

本轮枚举这些取值，命中即落盘。判据：success==1 且 data 非空。
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
UA = ("Mozilla/5.0 (iPhone; CPU iPhone OS 18_5 like Mac OS X) AppleWebKit/605.1.15 "
      "(KHTML, like Gecko) Version/18.5 Mobile/15E148 Safari/604.1")
OP = urllib.request.build_opener(urllib.request.ProxyHandler({}))


def call(path, params=None):
    ts = int(time.time())
    sig = "%s.lpw6vgqzsp.%s" % (ts, hashlib.md5(("%s%s" % (ts, SECRET)).encode()).hexdigest())
    url = BASE + "/" + path.lstrip("/")
    if params:
        url += "?" + urllib.parse.urlencode(params)
    req = urllib.request.Request(url, headers={
        "User-Agent": UA, "accept-language": "zh", "jdsignature": sig,
        "Accept": "application/json"})
    try:
        with OP.open(req, timeout=15) as r:
            return r.status, r.read()
    except urllib.error.HTTPError as e:
        try:
            return e.code, e.read()
        except Exception:
            return e.code, b""
    except Exception as e:
        return 0, str(e)[:60].encode()


def probe(path, params=None, tag=""):
    st, body = call(path, params)
    txt = body.decode("utf-8", "replace")
    try:
        j = json.loads(txt)
    except Exception:
        j = None
    ok = bool(j) and (j.get("success") == 1) and j.get("data")
    print("%-58s %-4s %s %s" % (
        "%s %s" % (path, json.dumps(params, ensure_ascii=False) if params else ""),
        st, "★" if ok else " ", txt[:110].replace("\n", " ")))
    if ok:
        fn = "tools/_dec/javdb_%s.json" % (tag or path.replace("/", "_"))
        open(fn, "w", encoding="utf-8").write(
            json.dumps(j, ensure_ascii=False, indent=1))
        print("      → 已存 %s" % fn)
    return ok


if __name__ == "__main__":
    print("== A. v1/movies/tags 的 filter_by ==")
    for v in ("tag", "tags", "actor", "maker", "series", "director", "code",
              "category", "genre", "all", "movie"):
        if probe("api/v1/movies/tags", {"filter_by": v}, "movie_tags_" + v):
            break

    print("\n== B. v2/tags 的 type ==")
    for v in ("movies", "actors", "makers", "series", "directors", "codes",
              "tags", "movie", "actor", "maker"):
        if probe("api/v2/tags", {"type": v}, "tags_" + v):
            break

    print("\n== C. actors / makers 的 type ==")
    for v in ("all", "popular", "new", "hot"):
        if probe("api/v1/actors", {"type": v, "page": 1}, "actors_" + v):
            break
    for v in ("all", "popular", "new", "hot"):
        if probe("api/v1/makers", {"type": v, "page": 1}, "makers_" + v):
            break

    print("\n== D. 列表子路径 ==")
    for sub in ("new", "latest", "recent", "hot", "popular", "top", "all",
                "movie", "movies", "release"):
        for pre in ("api/v1/movies", "api/v4/movies"):
            if probe("%s/%s" % (pre, sub), {"page": 1}, "list_%s_%s" % (pre.replace("/", "_"), sub)):
                break
