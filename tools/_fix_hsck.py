# -*- coding: utf-8 -*-
"""加固 hsck：418 不依赖异常 + 内置域名优先、注入域名回退"""
import io
import os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
P = os.path.join(ROOT, "sources", "welfare-js", "hsck.py")
s = io.open(P, encoding="utf-8").read()

NEW_METHODS = '''    def get_html(self, path, timeout=None):
        """取页面。站点恒返 418，body 仍有效 —— 绝不按 status 判失败。"""
        if path.startswith("http"):
            urls = [path]
        else:
            urls = [self.base.rstrip("/") + "/" + path.lstrip("/")]
            for alt in getattr(self, "_alt_hosts", None) or []:
                a = str(alt).rstrip("/")
                if a and a != self.base.rstrip("/"):
                    urls.append(a + "/" + path.lstrip("/"))
        for url in urls:
            body = self._get_once(url, timeout)
            if body:
                return body
        return ""

    def _get_once(self, url, timeout=None):
        req = urllib.request.Request(url, headers={
            "User-Agent": UA,
            "Accept": "text/html,application/xhtml+xml,*/*",
            "Accept-Language": "zh-CN,zh;q=0.9",
            "Referer": self.base + "/",
        })
        raw = None
        try:
            with self._open(req, timeout) as r:
                raw = r.read()
        except Exception as e:
            rd = getattr(e, "read", None)
            if callable(rd):
                try:
                    raw = rd()
                except Exception:
                    raw = None
        if not raw:
            return ""
        if raw[:2] == b"\\x1f\\x8b":
            try:
                raw = gzip.decompress(raw)
            except Exception:
                pass
        return raw.decode("utf-8", "replace")

'''

start = s.index("    def get_html(self, path, timeout=None):")
end = s.index("    # ---------------- 解析 ----------------")
s = s[:start] + NEW_METHODS + s[end:]

# init 里：注入域名作为回退，不覆盖内置域名
old_inj = '''        # 客户端注入的自定义域名优先于脚本内置默认值
        try:
            _inj = _vbox_host(self, "")
            if _inj:
                for _attr in ("base", "host"):
                    if hasattr(self, _inj if False else _attr):
                        setattr(self, _attr, _inj)
                _core = getattr(self, "_core", None)
                if _core is not None:
                    for _attr in ("base", "host"):
                        if hasattr(_core, _attr):
                            setattr(_core, _attr, _inj)
        except Exception:
            pass'''
new_inj = '''        # 客户端注入域名：仅作回退候选，不覆盖内置域名（防注入错域导致全挂）
        try:
            _inj = _vbox_host(self, "")
            if _inj and self._core is not None:
                self._core._alt_hosts = [_inj]
        except Exception:
            pass'''
if old_inj in s:
    s = s.replace(old_inj, new_inj)
    print("init 注入逻辑已改为回退")
else:
    print("init 注入块未匹配（可能已被改过），跳过")

io.open(P, "w", encoding="utf-8", newline="\n").write(s)
try:
    compile(s, P, "exec")
    print("hsck 语法 OK")
except SyntaxError as e:
    print("语法错 line %s: %s" % (e.lineno, e.msg))
