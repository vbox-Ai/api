# -*- coding: utf-8 -*-
"""线上问题诊断（用户 2026-11-04 反馈）

一次性体检：
  A. 封面图：取每个平台的 vod_pic，分别在「无 Referer」「带 Referer」「APP UA」下 GET，
     判断是不是 CDN 防盗链导致客户端不显示。
  B. 列表：模拟客户端注入（_vbox_effective_hosts=内置域名 / _vbox_proxy_enabled=False），
     看 mmav / hdb / hsck / km 的 categoryContent 是否真能出数据。
  C. 分类：homeContent 是否为空（客户端报「未能解析到分类」的判据）。
"""
import importlib.util
import json
import os
import urllib.error
import urllib.request

WJ = os.path.join("sources", "welfare-js")
UA_APP = "Dart/3.4 (dart:io)"
UA_BR = ("Mozilla/5.0 (iPhone; CPU iPhone OS 18_5 like Mac OS X) AppleWebKit/605.1.15 "
         "(KHTML, like Gecko) Version/18.5 Mobile/15E148 Safari/604.1")
OP = urllib.request.build_opener(urllib.request.ProxyHandler({}))


def load(key):
    p = os.path.join(WJ, key + ".py")
    spec = importlib.util.spec_from_file_location("diag_" + key, p)
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


def probe_img(url, referer=""):
    for tag, hdr in (("裸", {"User-Agent": UA_BR}),
                     ("带Referer", {"User-Agent": UA_BR, "Referer": referer} if referer else None),
                     ("APP UA", {"User-Agent": UA_APP})):
        if hdr is None:
            continue
        try:
            with OP.open(urllib.request.Request(url, headers=hdr), timeout=12) as r:
                n = len(r.read(4096))
                yield tag, r.status, r.headers.get("Content-Type", ""), n
        except urllib.error.HTTPError as e:
            yield tag, e.code, e.headers.get("Content-Type", "") if e.headers else "", 0
        except Exception as e:
            yield tag, 0, str(e)[:40], 0


def main():
    print("=" * 104)
    print("A. 封面图可达性（用户反馈：mdtv / javdb / hjsq / kpsp 封面不显示）")
    print("=" * 104)
    for key in ("mdtv", "javdb", "hjsq", "kpsp"):
        try:
            m = load(key)
            sp = m.Spider()
            sp.init("")
            h = sp.homeContent(True)
            cls = h.get("class") or []
            items = []
            for c in cls[:3]:
                cr = sp.categoryContent(c["type_id"], "1", True, {})
                if cr.get("list"):
                    items = cr["list"]
                    break
            pic = (items[0].get("vod_pic") if items else "") or ""
            print("\n[%s] class=%d list=%d" % (key, len(cls), len(items)))
            print("   pic = %s" % pic[:120])
            if not pic:
                continue
            for tag, st, ct, n in probe_img(pic, "https://" + key + ".com/"):
                print("    %-10s HTTP %-4s %-28s %dB" % (tag, st, ct, n))
        except Exception as e:
            print("[%s] 异常 %s" % (key, str(e)[:70]))

    print("\n" + "=" * 104)
    print("B/C. 列表与分类（用户反馈：mmav/hdb/hsck 有分类无数据；km 报未能解析到分类；rryy/one 无数据）")
    print("=" * 104)
    for key in ("mmav", "hdb", "hsck", "km", "rryy", "one"):
        try:
            m = load(key)
            sp = m.Spider()
            try:
                sp._vbox_proxy_enabled = False
                sp._vbox_effective_hosts = []
            except Exception:
                pass
            sp.init("")
            h = sp.homeContent(True)
            cls = h.get("class") or []
            names = [c.get("type_name") for c in cls[:5]]
            print("\n[%s] homeContent class=%d %s" % (key, len(cls), names))
            if not cls:
                continue
            for c in cls[:3]:
                cr = sp.categoryContent(c["type_id"], "1", True, {})
                lst = cr.get("list") or []
                print("   tid=%-14s 列表=%d  样本=%s" % (
                    c.get("type_id"), len(lst),
                    json.dumps(lst[0], ensure_ascii=False)[:100] if lst else "-"))
        except Exception as e:
            print("[%s] 异常 %s" % (key, str(e)[:80]))


main()
