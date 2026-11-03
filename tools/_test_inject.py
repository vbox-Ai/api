# -*- coding: utf-8 -*-
"""模拟客户端注入（代理 + 自定义域名），验证适配器能否正确消费

客户端 PythonSpiderEngine 会往 spider 实例/globals 注入：
    _vbox_effective_hosts   List[str]  用户自定义域名 + defaultHosts
    _vbox_proxy_enabled     Bool
    _vbox_proxy_url         String
    _vbox_platform_key      String
    _vbox_ssl_bypass        Bool
"""
import importlib.util
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
WJ = os.path.join(ROOT, "sources", "welfare-js")

PROXY = "http://127.0.0.1:7890"

CASES = [
    # rryy 域名被 DNS 污染，必须靠代理；用它验证代理注入
    ("rryy", {"_vbox_proxy_enabled": True, "_vbox_proxy_url": PROXY}),
    # hdb 直连可用，验证「无代理」路径不被误伤
    ("hdb", {"_vbox_proxy_enabled": False}),
    # hsck 验证域名注入生效（注入同一 host 应无副作用）
    ("hsck", {"_vbox_effective_hosts": ["https://hsck3.u0u0.cc"]}),
    # mw 漫画
    ("mw", {"_vbox_proxy_enabled": False}),
]


def load(key):
    p = os.path.join(WJ, key + ".py")
    spec = importlib.util.spec_from_file_location("inj_" + key, p)
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


print("%-6s %-34s %-6s %-6s %-6s %s" % ("key", "注入", "分类", "列表", "播放", "备注"))
print("-" * 96)
for key, inj in CASES:
    try:
        m = load(key)
        sp = m.Spider()
        sp.init("")
        # —— 模拟客户端注入
        for k, v in inj.items():
            setattr(sp, k, v)

        cls = (sp.homeContent(True).get("class") or [])
        n_l, n_p, note = 0, 0, ""
        for c in cls[:4]:
            r = sp.categoryContent(c["type_id"], "1", True, {})
            if r.get("list"):
                n_l = len(r["list"])
                d = sp.detailContent([r["list"][0]["vod_id"]])
                dl = d.get("list") or []
                if dl and dl[0].get("vod_play_url"):
                    first = dl[0]["vod_play_url"].split("#")[0]
                    cid = first.split("$")[-1]
                    pc = sp.playerContent("", cid, "")
                    n_p = 1 if pc.get("url") else 0
                break
        if not n_l:
            note = "列表空（检查代理/域名是否被正确应用）"
        print("%-6s %-34s %-6d %-6d %-6d %s" %
              (key, json.dumps(inj, ensure_ascii=False)[:34], len(cls), n_l, n_p, note))
    except Exception as e:
        print("%-6s %-34s %-6s %-6s %-6s 异常: %s" %
              (key, json.dumps(inj, ensure_ascii=False)[:34], "-", "-", "-",
               "%s: %s" % (type(e).__name__, str(e)[:40])))
