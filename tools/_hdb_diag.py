# -*- coding: utf-8 -*-
"""hdb 诊断：区分「限流」「域名失效」「参数问题」。
注意 HdbAdapter 用 self.host（小写）+ DOMAINS 列表轮换。"""
import importlib.util
import os
import sys
import time

sys.stdout.reconfigure(encoding="utf-8")
REPO = r"C:\Users\Administrator\Downloads\vboxapp\_remote_api"
P = os.path.join(REPO, "sources", "welfare-js", "muse_avbox.py")

spec = importlib.util.spec_from_file_location("muse_avbox", P)
m = importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)

sp = m.Spider()


def main():
    a = m.HdbAdapter(sp)
    print("默认 host:", a.host)
    print("DOMAINS:", a.DOMAINS)
    print("crypto 可用:", getattr(a, "_has_crypto", None))

    # 找它实际发请求的方法
    meth = None
    for name in ("_post", "_call", "_request", "post"):
        if hasattr(a, name):
            meth = getattr(a, name)
            print("请求方法:", name)
            break
    if meth is None:
        print("未找到请求方法，列出自定义方法：")
        print([x for x in dir(a) if not x.startswith("__")])
        return

    print("\n--- 逐个域名试探 dailyList ---")
    for host in a.DOMAINS:
        a.host = host
        try:
            t0 = time.time()
            try:
                r = meth("pwa/v2_0/dailyList",
                         {"page": 1, "length": 20, "country": -2,
                          "censorship_type": 0})
            except TypeError:
                r = meth("pwa/v2_0/dailyList")
            dt = time.time() - t0
            code = r.get("code") if isinstance(r, dict) else "?"
            n = 0
            if isinstance(r, dict):
                d = r.get("data")
                if isinstance(d, list):
                    n = len(d)
                elif isinstance(d, dict):
                    n = len(d.get("list") or [])
            print("  %-28s %5.1fs code=%-4s items=%d" % (host, dt, code, n))
        except Exception as e:
            print("  %-28s 异常: %s" % (host, str(e)[:80]))
        time.sleep(3)


if __name__ == "__main__":
    main()
