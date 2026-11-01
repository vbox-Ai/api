# -*- coding: utf-8 -*-
"""端到端冒烟测试：加载 muse_avbox，实例化 Spider，验证目录模式与各接口不崩。"""
import importlib.util
import os
import sys
import traceback

sys.stdout.reconfigure(encoding="utf-8")
REPO = r"C:\Users\Administrator\Downloads\vboxapp\_remote_api"
P = os.path.join(REPO, "sources", "welfare-js", "muse_avbox.py")

spec = importlib.util.spec_from_file_location("muse_avbox", P)
m = importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)


def main():
    print("=== 1. 目录模式 homeContent ===")
    try:
        sp = m.Spider()          # MODULE="" → 目录模式
        res = sp.homeContent(False)
        cats = res.get("class") or []
        print("  分类数:", len(cats))
        for c in cats[:8]:
            sub = c.get("sub_categories") or []
            print("    %-14s %-12s sub=%d" % (c.get("type_id"), c.get("type_name"), len(sub)))
        if len(cats) > 8:
            print("    ... 共 %d 个" % len(cats))
    except Exception:
        print("  FAILED:")
        traceback.print_exc()

    print("\n=== 2. 各 Adapter 的 categories() 是否可调用 ===")
    for key, cls in m.ADAPTERS.items():
        try:
            a = cls(sp)
            c = a.categories()
            print("  %-6s -> %d 个分类" % (key, len(c)))
        except Exception as e:
            print("  %-6s -> 异常: %s" % (key, str(e)[:80]))

    print("\n=== 3. one token 有效期 ===")
    try:
        a = m.OneAdapter(sp)
        ok, left = a.token_status()
        print("  有效=%s  剩余=%s" % (ok, ("%.2f 小时" % (left / 3600.0)) if left else "未知"))
    except Exception as e:
        print("  异常:", e)

    print("\n=== 4. HostResolver 全平台 ===")
    r = m.host_resolver()
    for item in m.CATALOG:
        k = item["key"]
        cs = r.candidates(k)
        print("  %-10s %d 个候选  %s" % (k, len(cs), cs[0] if cs else "<无>"))


if __name__ == "__main__":
    main()
