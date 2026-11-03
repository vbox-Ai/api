# -*- coding: utf-8 -*-
"""javdb 第三轮：详情/播放地址定位

列表项字段（v1/movies/latest）：id, number, title, cover_url/thumb_url, duration,
magnets_count, can_play, has_preview_video, preview_images, release_date …
→ 播放大概率在详情里由 can_play / preview 或第三方 player 提供。

本轮：拿 1 个 id，探 api/v1/movies/{id} 与 api/v4/movies/{id}，打印字段结构，
找出可播字段（m3u8/mp4/preview/magnet）。
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
            return r.status, json.loads(r.read().decode("utf-8", "replace"))
    except urllib.error.HTTPError as e:
        try:
            return e.code, json.loads(e.read().decode("utf-8", "replace"))
        except Exception:
            return e.code, {}
    except Exception as e:
        return 0, {"_err": str(e)[:60]}


def walk(o, p="", depth=0):
    """找所有含 http / .m3u8 / magnet 的字符串字段。"""
    if depth > 4:
        return
    if isinstance(o, dict):
        for k, v in o.items():
            walk(v, p + "." + k, depth + 1)
    elif isinstance(o, list):
        for i, v in enumerate(o[:3]):
            walk(v, p + "[%d]" % i, depth + 1)
    elif isinstance(o, str) and ("http" in o or "magnet" in o or ".m3u8" in o):
        print("   %-42s %s" % (p, o[:110]))


if __name__ == "__main__":
    st, j = call("api/v1/movies/latest", {"page": 1})
    ms = (j.get("data") or {}).get("movies") or []
    print("[latest] %d 条  can_play=true 的有 %d 条" % (
        len(ms), sum(1 for m in ms if m.get("can_play"))))
    ids = [m["id"] for m in ms[:3]]
    playable = [m["id"] for m in ms if m.get("can_play")][:2]
    print("[ids]", ids, "playable:", playable)

    cand = playable or ids
    for vid in cand:
        for path in ("api/v1/movies/%s" % vid, "api/v4/movies/%s" % vid):
            st, j = call(path)
            data = j.get("data")
            keys = list(data.keys())[:18] if isinstance(data, dict) else type(data).__name__
            print("\n%s → HTTP %s success=%s keys=%s" % (
                path, st, j.get("success"), keys))
            if isinstance(data, dict):
                walk(data)
                fn = "tools/_dec/javdb_detail_%s.json" % path.replace("/", "_")
                open(fn, "w", encoding="utf-8").write(
                    json.dumps(j, ensure_ascii=False, indent=1))
                print("   → 已存", fn)
