# -*- coding: utf-8 -*-
"""hjsq 海角社区 接口实测探测器

协议来源：libapp.so blutter 反汇编
  - baseUrl      : SpUtil["hjsq"]     -> http://23.225.145.74
  - X-User-Id    : 硬编码 171299991201  (HjSqInterceptor::onRequest)
  - X-User-Token : SpUtil["token_hjsq"] -> b2dc730bf54441f18492061ce80659b3
  - 信封         : {"errorCode":0,"message":"","data":...}
  - GET 取 data / POST 取 response

直连 IP，不走代理。
"""
import json
import sys
import urllib.error
import urllib.request

BASE = "http://23.225.145.74"
USER_ID = "171299991201"
TOKEN = "b2dc730bf54441f18492061ce80659b3"

# 显式禁用代理（本机有 mihomo 全局环境变量，会把 http 请求劫走）
OPENER = urllib.request.build_opener(urllib.request.ProxyHandler({}))

HDRS = {
    "X-User-Id": USER_ID,
    "X-User-Token": TOKEN,
    "User-Agent": "okhttp/3.14.9",
    "Accept": "application/json",
}


def call(path, method="GET", body=None, timeout=20):
    url = BASE.rstrip("/") + "/" + path.lstrip("/")
    data = None
    headers = dict(HDRS)
    if body is not None:
        data = json.dumps(body, ensure_ascii=False).encode("utf-8")
        headers["Content-Type"] = "application/json; charset=utf-8"
    req = urllib.request.Request(url, data=data, headers=headers, method=method)
    try:
        with OPENER.open(req, timeout=timeout) as r:
            raw = r.read()
            return r.status, raw
    except urllib.error.HTTPError as e:
        return e.code, e.read()
    except Exception as e:
        return 0, ("%s: %s" % (type(e).__name__, e)).encode()


def show(tag, path, method="GET", body=None, limit=1200):
    st, raw = call(path, method, body)
    print("=" * 78)
    print("[%s] %s %s -> %s  (%d bytes)" % (tag, method, path, st, len(raw)))
    if not raw:
        print("  <empty>")
        return None
    try:
        txt = raw.decode("utf-8", "replace")
    except Exception:
        txt = repr(raw[:200])
    try:
        j = json.loads(txt)
        print(json.dumps(j, ensure_ascii=False, indent=1)[:limit])
        return j
    except Exception:
        print(txt[:limit])
        return None


if __name__ == "__main__":
    print("### hjsq probe  base=%s" % BASE)
    show("A 首页帖子", "api2/topic/node/topics?page=1&nodeId=0&type=0")
    show("B 热帖", "api2/topic/hot/topics")
    show("C 新闻", "api2/topic/node/news")
    show("D 视频tab", "api2/topic/node/topics?page=1&nodeId=13&type=0")
    show("E 视频列表", "api2/video/node_list?pageIndex=1&type=&orderType=")
    show("F 搜索", "api2/topic/search?node_id=0&keyword=%E5%81%B7%E6%8B%8D")
    show("G 根路径", "")
