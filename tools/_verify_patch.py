# -*- coding: utf-8 -*-
"""验证 muse_avbox.py 修改后的行为：HOSTS 表完整性、HostResolver 功能、适配器注册。"""
import importlib.util
import os
import sys

sys.stdout.reconfigure(encoding="utf-8")
REPO = r"C:\Users\Administrator\Downloads\vboxapp\_remote_api"
P = os.path.join(REPO, "sources", "welfare-js", "muse_avbox.py")

spec = importlib.util.spec_from_file_location("muse_avbox", P)
m = importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)

print("=== PLATFORM_HOSTS ===")
print("条数:", len(m.PLATFORM_HOSTS))

print("\n=== MEDIA_HOSTS ===")
print("条数:", len(m.MEDIA_HOSTS))

print("\n=== 配置端点 ===")
print("FL2_HOST_API :", m.FL2_HOST_API)
print("MMMH_HOST_TXT:", m.MMMH_HOST_TXT)

print("\n=== CATALOG 平台数 ===")
print("CATALOG:", len(m.CATALOG))
print("ADAPTERS:", list(m.ADAPTERS.keys()))

print("\n=== HostResolver ===")
r = m.host_resolver()
print("hdb.candidates :", r.candidates("hdb"))
print("one.candidates :", r.candidates("one"))
print("hgsp.primary   :", r.primary("hgsp"))
print("join 测试      :", r.join("https://api55.nmrgqb.com/", "/home/defaultchannels"))

# 覆盖率检查：CATALOG 里每个 key 是否都有 host
missing = []
for item in m.CATALOG:
    k = item["key"]
    if k not in m.PLATFORM_HOSTS and k not in ("mw", "live"):
        missing.append(k)
print("\n=== CATALOG 中缺 PLATFORM_HOSTS 的 key ===")
print(missing if missing else "无（全部覆盖）")

# CATALOG 有但 splash 没有的，按脚本标注
print("\n=== 平台 → host 速查 ===")
for item in m.CATALOG:
    k = item["key"]
    h = m.PLATFORM_HOSTS.get(k, "<缺失>")
    print("  %-10s %-16s %s" % (k, item["name"], h))
