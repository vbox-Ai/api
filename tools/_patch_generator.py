# -*- coding: utf-8 -*-
"""给 _gen_standalone.py 打 vbox 运行时适配补丁（SSL/代理/域名注入）"""
import io
import os
import re

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
P = os.path.join(ROOT, "tools", "_gen_standalone.py")
s = io.open(P, encoding="utf-8").read()

INJECT = '''
# ============================================================ vbox 运行时适配
# 客户端 base.spider 只给 requests 打了「代理 + verify=False」补丁，裸 urllib 不走。
# 而 iOS CPython 无系统 CA 证书包 —— urllib 的 HTTPS 会全部 SSLError，
# 现象就是「分类能显示（本地静态），点进去没有数据（联网失败）」。
# 这里显式构造：不验证证书的 SSL 上下文 + 客户端注入的代理 + 自定义域名。
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


def _vbox_proxy(sp):
    if not _vbox_cfg(sp, '_vbox_proxy_enabled', False):
        return {}
    u = _vbox_cfg(sp, '_vbox_proxy_url', '') or ''
    return {'http': u, 'https': u} if u else {}


def _vbox_host(sp, default):
    hs = _vbox_cfg(sp, '_vbox_effective_hosts', None)
    if isinstance(hs, list) and hs:
        try:
            return str(hs[0]).rstrip('/')
        except Exception:
            pass
    return default


def _vbox_opener(sp):
    handlers = [urllib.request.ProxyHandler(_vbox_proxy(sp))]
    if _SSL_CTX is not None:
        handlers.append(urllib.request.HTTPSHandler(context=_SSL_CTX))
    try:
        handlers.append(urllib.request.HTTPCookieProcessor(http.cookiejar.CookieJar()))
    except Exception:
        pass
    return urllib.request.build_opener(*handlers)

'''

ANCHOR = '_LOG = logging.getLogger('
if "_vbox_opener" in s:
    print("已打过补丁，跳过")
else:
    i = s.index(ANCHOR)
    s = s[:i] + INJECT.lstrip("\n") + "\n" + s[i:]
    print("已插入 vbox 运行时适配块")

    # __init__ 里的 opener 换成 _vbox_opener(self)
    old = ("        self._jar = http.cookiejar.CookieJar()\n"
           "        self._opener = urllib.request.build_opener(\n"
           "            urllib.request.HTTPCookieProcessor(self._jar))")
    if old in s:
        s = s.replace(old, "        self._jar = http.cookiejar.CookieJar()\n"
                          "        self._opener = _vbox_opener(self)")
        print("已改 __init__ opener")
    else:
        # 模板里可能是单行写法，宽松替换
        s2 = re.sub(r"self\._opener = urllib\.request\.build_opener\([^)]*\)",
                    "self._opener = _vbox_opener(self)", s, count=1)
        if s2 != s:
            s = s2
            print("已（正则）改 __init__ opener")

    # init() 支持客户端注入域名
    old2 = ('        host = ext.get("host")\n'
            '        if host:\n'
            '            try:\n'
            '                self.ADAPTER.HOST = str(host).rstrip("/")\n'
            '            except Exception:\n'
            '                pass')
    if old2 in s:
        s = s.replace(old2, old2 + '\n'
            '        # 客户端注入的自定义域名优先于脚本内置默认值\n'
            '        try:\n'
            '            inj = _vbox_host(self, "")\n'
            '            if inj:\n'
            '                self.ADAPTER.HOST = inj\n'
            '        except Exception:\n'
            '            pass')
        print("已改 init 域名注入")

    io.open(P, "w", encoding="utf-8", newline="\n").write(s)
    print("写回完成")
