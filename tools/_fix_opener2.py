# -*- coding: utf-8 -*-
"""让 _vbox_opener 每次请求时构建（保证读到最新注入的代理/域名），并复用实例 cookie jar"""
import io
import os
import re

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
WJ = os.path.join(ROOT, "sources", "welfare-js")
GEN = os.path.join(ROOT, "tools", "_gen_standalone.py")

# 新版 _vbox_opener：复用 sp._jar（保持 cookie 会话），每次调用都读最新注入
NEW_FN = '''def _vbox_opener(sp=None):
    """带 SSL 放行 + 客户端代理 的 opener（每次构建，保证读到最新注入）。"""
    handlers = [urllib.request.ProxyHandler(_vbox_proxy(sp))]
    if _SSL_CTX is not None:
        handlers.append(urllib.request.HTTPSHandler(context=_SSL_CTX))
    jar = getattr(sp, "_jar", None)
    if jar is not None:
        try:
            handlers.append(urllib.request.HTTPCookieProcessor(jar))
        except Exception:
            pass
    return urllib.request.build_opener(*handlers)'''

OLD_FN_RE = re.compile(
    r"def _vbox_opener\(sp=None\):\n(?:.*?\n)*?    return urllib\.request\.build_opener\(\*handlers\)")

TARGETS = ["hdb", "mmav", "rryy", "one"]
for f in TARGETS:
    p = os.path.join(WJ, f + ".py")
    s = io.open(p, encoding="utf-8").read()
    orig = s
    # 1) 替换 _vbox_opener 定义
    s = OLD_FN_RE.sub(NEW_FN, s, count=1)
    # 2) 每次请求构建 opener（不再用固定的 self._opener）
    s = s.replace("with self._opener.open(req, timeout=self.timeout) as r:",
                  "with _vbox_opener(self).open(req, timeout=self.timeout) as r:")
    s = s.replace("self._opener.open(req, timeout=", "_vbox_opener(self).open(req, timeout=")
    if s != orig:
        io.open(p, "w", encoding="utf-8", newline="\n").write(s)
        try:
            compile(s, p, "exec")
            ok = "OK"
        except SyntaxError as e:
            ok = "SYNTAX ERR %s" % e.lineno
        n_calls = s.count("_vbox_opener(self).open(")
        print("%-6s 修补 %s  请求点数=%d" % (f, ok, n_calls))
    else:
        print("%-6s 无变化" % f)

# 3) 生成器同步（模板里的 _vbox_opener 也换新版，避免下次重生成回退）
s = io.open(GEN, encoding="utf-8").read()
if "保证读到最新注入" not in s:
    s = OLD_FN_RE.sub(NEW_FN.replace("{", "{{").replace("}", "}}"), s, count=1)
    # 生成器里 fetch 段用 self._opener.open，也替换
    s = s.replace("with self._opener.open(req, timeout=self.timeout) as r:",
                  "with _vbox_opener(self).open(req, timeout=self.timeout) as r:")
    io.open(GEN, "w", encoding="utf-8", newline="\n").write(s)
    print("生成器已同步")
else:
    print("生成器已是新版")

# 复核
print("\n复核产物：")
for f in TARGETS:
    s = io.open(os.path.join(WJ, f + ".py"), encoding="utf-8").read()
    print("  %-6s _vbox_opener(self).open=%d  裸 self._opener.open=%d" % (
        f, s.count("_vbox_opener(self).open("), s.count("self._opener.open(")))
