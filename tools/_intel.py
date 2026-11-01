# -*- coding: utf-8 -*-
"""把解密出的 splash/home 整理成平台情报总表：host / token / 模块 / tabs。"""
import json
import os
import sys

sys.stdout.reconfigure(encoding="utf-8")
DEC = os.path.join(os.path.dirname(os.path.abspath(__file__)), "_dec")
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "_platform_intel.md")


def load(name):
    p = os.path.join(DEC, name)
    if not os.path.exists(p):
        return None
    return json.load(open(p, encoding="utf-8"))


def main():
    sp = load("box_api_splash.json")
    hm = load("box_api_home_versionCode=101.json")
    lines = ["# 暮色 1.0.1 平台情报总表（从 6868 splash/home 明文解密）", ""]

    data = (sp or {}).get("data", {})
    print("splash.data keys:", list(data.keys()))
    lines.append("## splash.data 结构")
    for k, v in data.items():
        if isinstance(v, list):
            lines.append("- `%s`: list[%d]" % (k, len(v)))
        elif isinstance(v, dict):
            lines.append("- `%s`: dict(%d)" % (k, len(v)))
        else:
            lines.append("- `%s`: %r" % (k, str(v)[:60]))

    hosts = data.get("host") or []
    lines += ["", "## host 全集（%d）" % len(hosts), "", "| id | name | host |", "|---|---|---|"]
    for h in hosts:
        lines.append("| %s | `%s` | %s |" % (h.get("id"), h.get("name"), h.get("host")))
    print("\nhost 数:", len(hosts))

    # token / 其他键
    for key in ("token", "tokens", "config", "domain", "cdn"):
        if key in data and data[key]:
            lines += ["", "## %s" % key]
            v = data[key]
            if isinstance(v, list):
                for it in v:
                    lines.append("- %s" % json.dumps(it, ensure_ascii=False))
            else:
                lines.append("```json")
                lines.append(json.dumps(v, ensure_ascii=False, indent=1)[:3000])
                lines.append("```")

    # home 模块
    if hm:
        hd = hm.get("data", {})
        print("home.data keys:", list(hd.keys()))
        lines += ["", "## home.data 结构"]
        for k, v in hd.items():
            if isinstance(v, list):
                lines.append("- `%s`: list[%d]" % (k, len(v)))
            elif isinstance(v, dict):
                lines.append("- `%s`: dict(%d)" % (k, len(v)))
            else:
                lines.append("- `%s`: %r" % (k, str(v)[:60]))
        mods = hd.get("module") or hd.get("modules") or []
        if isinstance(mods, list):
            lines += ["", "## 模块列表（%d）" % len(mods), "",
                      "| moduleId | name | router | type | icon |", "|---|---|---|---|---|"]
            for m in mods:
                if not isinstance(m, dict):
                    continue
                lines.append("| %s | %s | %s | %s | %s |" % (
                    m.get("moduleId"), m.get("moduleName"), m.get("router"),
                    m.get("type"), str(m.get("icon", ""))[:50]))
        tabs = hd.get("tabs")
        if tabs:
            lines += ["", "## tabs"]
            lines.append("```json")
            lines.append(json.dumps(tabs, ensure_ascii=False, indent=1)[:3000])
            lines.append("```")

    open(OUT, "w", encoding="utf-8").write("\n".join(lines))
    print("\n写出:", OUT)


if __name__ == "__main__":
    main()
