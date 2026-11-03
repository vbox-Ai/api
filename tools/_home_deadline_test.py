# -*- coding: utf-8 -*-
"""验证 mdtv / aijav 首页「未能解析到分类」修复

客户端约束（lib/platform/spider/python_bridge_engine.dart）：
    PythonBridgeEngine.timeout = 20s  ← homeContent 的总预算
    welfare_spider_main_page.dart：result.categories.isEmpty → 「未能解析到分类，请检查域名或网络」

三种场景各跑一遍，判据：class 必须非空，且耗时远小于 20s。
    1) 正常网络
    2) 断网（opener 直接抛异常）
    3) 慢网（每次请求 sleep 10s → 必须被 QUICK_TIMEOUT=3s 截断并回退快照）
"""
import importlib.util
import json
import os
import time


def load(key):
    p = os.path.join("sources", "welfare-js", key + ".py")
    spec = importlib.util.spec_from_file_location("home_" + key, p)
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


def run(key, mode):
    m = load(key)
    if mode == "dead":
        class _Dead:
            def open(self, *a, **k):
                raise OSError("network down")
        m._vbox_opener = lambda sp=None: _Dead()
    elif mode == "slow":
        class _Slow:
            def open(self, *a, **k):
                t = k.get("timeout") or 20
                time.sleep(min(float(t), 10))
                raise OSError("timeout")
        m._vbox_opener = lambda sp=None: _Slow()
        m.QUICK_TIMEOUT = 1.5           # 慢网场景把快速预算压到 1.5s，便于观察

    sp = m.Spider()
    sp.init("")
    t0 = time.time()
    h = sp.homeContent(True)
    dt = time.time() - t0
    cls = h.get("class") or []
    print("%-6s %-6s class=%-3d 耗时=%5.2fs  首项=%s" % (
        key, mode, len(cls),
        dt, json.dumps(cls[:1], ensure_ascii=False)))
    return len(cls) > 0 and dt < 8


if __name__ == "__main__":
    ok = True
    for k in ("mdtv", "aijav"):
        for md in ("normal", "dead", "slow"):
            ok = run(k, md) and ok
    print("\n全部通过" if ok else "\n有场景失败")
