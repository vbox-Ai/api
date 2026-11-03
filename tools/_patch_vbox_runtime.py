# -*- coding: utf-8 -*-
"""批量给手写适配器注入 vbox 运行时适配（SSL 放行 / 代理 / 自定义域名）

问题背景：客户端 base.spider 只给 requests 打补丁（verify=False + proxies），
裸 urllib 完全不生效；iOS CPython 无 CA 证书 → 所有 HTTPS 必失败 →
「分类能显示、列表全空」。
"""
import io
import os
import re

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
WJ = os.path.join(ROOT, "sources", "welfare-js")
FILES = ["lclf", "km", "hsck", "kpsp", "hjsq", "mw", "live"]

BLOCK = '''# ============================================================ vbox 运行时适配
# 客户端 base.spider 只给 requests 打了「代理 + verify=False」补丁，裸 urllib 不走；
# 而 iOS CPython 无系统 CA 证书包 —— urllib 的 HTTPS 会全部 SSLError。
# 现象即「分类能显示（本地静态），点进去没有数据（联网失败）」。
try:
    import ssl as _ssl
    _SSL_CTX = _ssl.create_default_context()
    _SSL_CTX.check_hostname = False
    _SSL_CTX.verify_mode = _ssl.CERT_NONE
except Exception:
    _SSL_CTX = None


def _vbox_cfg(sp, name, default=None):
    v = getattr(sp, name, None)
    if v is None:
        v = globals().get(name)
    return default if v is None else v


def _vbox_proxy(sp=None):
    if sp is not None and not _vbox_cfg(sp, "_vbox_proxy_enabled", False):
        return {}
    if sp is None and not globals().get("_vbox_proxy_enabled", False):
        return {}
    u = (getattr(sp, "_vbox_proxy_url", None) if sp is not None else None) \\
        or globals().get("_vbox_proxy_url", "") or ""
    return {"http": u, "https": u} if u else {}


def _vbox_host(sp, default=""):
    hs = _vbox_cfg(sp, "_vbox_effective_hosts", None)
    if isinstance(hs, list) and hs:
        try:
            return str(hs[0]).rstrip("/")
        except Exception:
            pass
    return default


def _vbox_opener(sp=None):
    """带 SSL 放行 + 客户端代理 的 opener。"""
    handlers = [urllib.request.ProxyHandler(_vbox_proxy(sp))]
    if _SSL_CTX is not None:
        handlers.append(urllib.request.HTTPSHandler(context=_SSL_CTX))
    return urllib.request.build_opener(*handlers)


'''

NEW_OPEN = '''    def _open(self, req, timeout=None):
        t = timeout if timeout is not None else getattr(self, "timeout", 20)
        return _vbox_opener(getattr(self, "sp", None)).open(req, timeout=t)
'''

HOST_INJECT = '''        # 客户端注入的自定义域名优先于脚本内置默认值
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
            pass
'''

for f in FILES:
    p = os.path.join(WJ, f + ".py")
    s = io.open(p, encoding="utf-8").read()
    orig = s
    notes = []

    # 1) 插入 vbox 块（放在 UA = 之前，若已有则跳过）
    if "_vbox_opener" not in s:
        m = re.search(r"^(UA\s*=\s*)", s, re.M)
        if m:
            s = s[:m.start()] + BLOCK + s[m.start():]
        else:
            m = re.search(r"^(HOST_DEFAULT|BASE_DEFAULT|BASE)\s*=", s, re.M)
            s = (s[:m.start()] + BLOCK + s[m.start():]) if m else (BLOCK + s)
        notes.append("插入适配块")

    # 2) 重写 _open
    pat = re.compile(r"    def _open\(self[^)]*\):\n(?:.*?\n)*?(?=    def |\nclass |\ndef |\Z)", re.S)
    if "_vbox_opener(getattr(self" not in s and pat.search(s):
        s = pat.sub(NEW_OPEN + "\n", s, count=1)
        notes.append("重写 _open")

    # 3) init 末尾注入域名
    if "_inj = _vbox_host(self" not in s:
        m = re.search(r"(    def init\(self, extend=\"\"\):.*?)(\n        return None)", s, re.S)
        if m:
            s = s[:m.end(1)] + "\n" + HOST_INJECT + s[m.end(1):]
            notes.append("init 注入域名")

    if s != orig:
        io.open(p, "w", encoding="utf-8", newline="\n").write(s)
        try:
            compile(s, p, "exec")
            st = "OK"
        except SyntaxError as e:
            st = "SYNTAX ERR line %s" % e.lineno
        print("%-6s %-30s %s" % (f, "/".join(notes), st))
    else:
        print("%-6s 无变化" % f)
