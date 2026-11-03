# -*- coding: utf-8 -*-
"""修 hdb/mmav/rryy/one 的 __init__ opener：改成 _vbox_opener(self)

问题：生成器替换未生效（模板里是多行写法），产物仍是裸 build_opener，
导致 iOS/需代理环境下 HTTPS 全部失败 → 有分类无数据。
"""
import io
import os
import re

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
WJ = os.path.join(ROOT, "sources", "welfare-js")
GEN = os.path.join(ROOT, "tools", "_gen_standalone.py")

OLD_MULTI = ("        self._jar = http.cookiejar.CookieJar()\n"
             "        self._opener = urllib.request.build_opener(\n"
             "            urllib.request.HTTPCookieProcessor(self._jar))")
NEW_MULTI = ("        self._jar = http.cookiejar.CookieJar()\n"
             "        self._opener = _vbox_opener(self)")

# 1) 修生成器：在 build() 里对 init_seg 做替换，保证以后重生成也正确
s = io.open(GEN, encoding="utf-8").read()
if "init_seg = INIT_SEG" not in s and "init_seg=INIT_SEG" in s:
    # 在 build() 里注入替换逻辑
    anchor = "    body += SPIDER_TPL.format(key=key, name=name, cls=cls,"
    if anchor in s:
        inject = ('    # 强制把裸 build_opener 换成带 SSL/代理 的 _vbox_opener\n'
                  '    _init_seg = INIT_SEG\n'
                  '    if "self._opener = urllib.request.build_opener(" in _init_seg:\n'
                  '        _init_seg = re.sub(\n'
                  '            r"self\\._opener = urllib\\.request\\.build_opener\\([^)]*\\)",\n'
                  '            "self._opener = _vbox_opener(self)", _init_seg, count=1)\n'
                  '        _init_seg = _init_seg.replace(\n'
                  '            "urllib.request.HTTPCookieProcessor(self._jar))", "")\n'
                  '    INIT_PATCHED = _init_seg\n')
        s = s.replace(anchor, inject + anchor, 1)
        # SPIDER_TPL.format 用 INIT_PATCHED
        s = s.replace("init_seg=INIT_SEG", "init_seg=INIT_PATCHED")
        io.open(GEN, "w", encoding="utf-8", newline="\n").write(s)
        print("生成器已加 INIT_PATCHED 逻辑")
    else:
        print("生成器锚点未找到，跳过生成器修改")
else:
    print("生成器已是修补状态或结构不同")

# 2) 批量修已生成的 4 个产物
files = ["hdb", "mmav", "rryy", "one"]
for f in files:
    p = os.path.join(WJ, f + ".py")
    src = io.open(p, encoding="utf-8").read()
    orig = src
    if OLD_MULTI in src:
        src = src.replace(OLD_MULTI, NEW_MULTI, 1)
    else:
        # 宽松正则：匹配 build_opener(...) 跨行
        src = re.sub(r"self\._opener = urllib\.request\.build_opener\(\s*"
                     r"urllib\.request\.HTTPCookieProcessor\(self\._jar\)\)",
                     "self._opener = _vbox_opener(self)", src, count=1)
    if src != orig:
        io.open(p, "w", encoding="utf-8", newline="\n").write(src)
        try:
            compile(src, p, "exec")
            print("%-6s 已修 _opener  OK" % f)
        except SyntaxError as e:
            print("%-6s 语法错 line %s" % (f, e.lineno))
    else:
        print("%-6s 未匹配到旧写法（检查）" % f)

# 3) 复核
print("\n复核：")
for f in files:
    p = os.path.join(WJ, f + ".py")
    src = io.open(p, encoding="utf-8").read()
    has_vbox = "_opener = _vbox_opener(self)" in src
    has_raw = "build_opener(\n            urllib.request.HTTPCookieProcessor" in src
    print("  %-6s _vbox_opener=%s  残留裸 opener=%s" % (f, has_vbox, has_raw))
