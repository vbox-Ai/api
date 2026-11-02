# -*- coding: utf-8 -*-
"""4hu（4虎）客户端 —— 加密全部破解，域名自动跟随。

协议（avbox/module/hu4/network/interceptor.dart 反汇编）：
  业务响应：base64(- _ → + /) → AES-256-CBC
            key = "22946bc50fd63164b79df55070a85a92"  (32 字符 → 32 字节，不是 hex)
            iv  = "kaixin1234567890"
  CDN 反爬：ap-d 块 = base64 密文，XOR 解密
            key[i] = int(data_k_hex[2i:2i+2],16) ^ 0xA5

域名池：h96h69.com → 872k5e.com / k2hy98.com → xa49d8.com（持续轮换，需跟随 302）

用法：
  python tools/4hu_client.py                 # 探测当前可用域名
  python tools/4hu_client.py <path>          # 取指定路径（自动解密）
"""
import base64
import json
import re
import subprocess
import sys
import time

from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes

sys.stdout.reconfigure(encoding="utf-8")

CURL = r"C:\Windows\System32\curl.exe"
PROXY = "http://127.0.0.1:7890"
UA = ("Mozilla/5.0 (iPhone; CPU iPhone OS 18_5 like Mac OS X) "
      "AppleWebKit/605.1.15 (KHTML, like Gecko) Version/18.5 Mobile/15E148 Safari/604.1")

SEEDS = ["https://h96h69.com", "https://872k5e.com", "https://k2hy98.com"]

AES_KEY = b"22946bc50fd63164b79df55070a85a92"
AES_IV = b"kaixin1234567890"

# 缓存：可用域名 + 已发现的域名池
_pool = {"hosts": [], "checked_at": 0}


# ---------------------------------------------------------------- 传输
def _curl(url, timeout=20, follow=True, cookie=None):
    cmd = [CURL, "-s", "-S", "--max-time", str(timeout), "-k",
           "-H", "User-Agent: " + UA]
    if cookie:
        cmd += ["-H", "Cookie: " + cookie]
    if follow:
        cmd += ["-L"]
    cmd += [url, "-w", "\n__S__%{http_code}\n__U__%{url_effective}"]
    try:
        r = subprocess.run(cmd, capture_output=True, timeout=timeout + 15)
        out = r.stdout.decode("utf-8", "replace")
    except Exception as e:
        return "ERR", "", ""
    code = eff = ""
    body = out
    if "__U__" in body:
        body, _, eff = body.rpartition("__U__")
        eff = eff.strip()
    if "__S__" in body:
        body, _, code = body.rpartition("__S__")
    return code.strip(), body.strip(), eff


# ---------------------------------------------------------------- 域名跟随
def resolve_host(force=False):
    """跟随 302 找到当前真正可用的域名。"""
    if not force and _pool["hosts"] and time.time() - _pool["checked_at"] < 300:
        return _pool["hosts"][0]
    found = []
    for seed in SEEDS:
        code, body, eff = _curl(seed + "/", timeout=15)
        if eff:
            m = re.match(r"(https?://[^/]+)", eff)
            if m and m.group(1) not in found:
                found.append(m.group(1))
        if code == "200" and body:
            m = re.match(r"(https?://[^/]+)", seed)
            if m and m.group(1) not in found:
                found.append(m.group(1))
    _pool["hosts"] = found
    _pool["checked_at"] = time.time()
    return found[0] if found else SEEDS[0]


# ---------------------------------------------------------------- 解密
def aes_decrypt(data_b64):
    """业务响应：base64(- _ → + /) → AES-256-CBC → JSON"""
    s = str(data_b64).replace("-", "+").replace("_", "/")
    s += "=" * (-len(s) % 4)
    raw = base64.b64decode(s)
    if not raw or len(raw) % 16:
        return None
    d = Cipher(algorithms.AES(AES_KEY), modes.CBC(AES_IV)).decryptor()
    pt = d.update(raw) + d.finalize()
    n = pt[-1] if pt else 0
    if 1 <= n <= 16:
        pt = pt[:-n]
    return pt.decode("utf-8", "replace")


def xor_decrypt(blob_b64, key_hex):
    """CDN 反爬 ap-d 块：key[i] = hex 字节 ^ 0xA5，再逐字节 XOR"""
    s = blob_b64.replace("-", "+").replace("_", "/")
    s += "=" * (-len(s) % 4)
    data = base64.b64decode(s)
    key = bytes(((int(key_hex[i:i + 2], 16) ^ 0xA5) & 0xFF)
                for i in range(0, len(key_hex) - 1, 2))
    if not key:
        return data
    return bytes(b ^ key[i % len(key)] for i, b in enumerate(data))


def unwrap_challenge(html):
    """若响应是 ap-d 挑战页，解出真实内容。返回 (是否挑战, 文本)。"""
    if 'id="ap-d"' not in html:
        return False, html
    m = re.search(r'id="ap-d"[^>]*data-k="([^"]*)"[^>]*>([\s\S]*?)</script>', html)
    if not m:
        m = re.search(r'data-k="([^"]*)"[^>]*>([\s\S]*?)</script>', html)
    if not m:
        return True, ""
    key, blob = m.group(1), m.group(2).strip()
    try:
        raw = xor_decrypt(blob, key)
    except Exception:
        return True, ""
    for cand in (raw, raw[::-1]):
        for enc in ("utf-8", "gbk", "latin-1"):
            try:
                t = cand.decode(enc)
            except Exception:
                continue
            if t.lstrip()[:1] in ("<", "{", "["):
                return True, t
    return True, raw.decode("utf-8", "replace")


# ---------------------------------------------------------------- 高层接口
def fetch_path(path, host=None):
    """取一个路径，自动处理 302 与挑战页。返回 (kind, 内容)。"""
    h = host or resolve_host()
    code, body, eff = _curl(h.rstrip("/") + path)
    if eff:
        m = re.match(r"(https?://[^/]+)", eff)
        if m:
            h = m.group(1)
    if not body:
        return "empty", ""
    if 'id="ap-d"' in body:
        _, txt = unwrap_challenge(body)
        return "challenge-decrypted", txt
    if body.lstrip().startswith("{"):
        try:
            obj = json.loads(body)
            if isinstance(obj, dict) and obj.get("status") == 1 and obj.get("data"):
                dec = aes_decrypt(obj["data"])
                if dec:
                    return "aes", dec
            return "json", body
        except Exception:
            return "json", body
    return "raw", body


def search(keyword, page=1, classid=0, host=None):
    """搜索接口（免挑战）。返回解密后的 dict 或 None。"""
    import urllib.parse
    q = urllib.parse.quote(str(keyword))
    path = "/api/v2/search?keyword=%s&page=%s&classid=%s" % (q, page, classid)
    kind, txt = fetch_path(path, host)
    if kind == "aes":
        try:
            return json.loads(txt)
        except Exception:
            return None
    return None


if __name__ == "__main__":
    if len(sys.argv) > 1:
        kind, txt = fetch_path(sys.argv[1])
        print("kind:", kind, " len:", len(txt))
        print(txt[:1500])
    else:
        print("=== 域名池探测 ===")
        for s in SEEDS:
            code, body, eff = _curl(s + "/", timeout=15)
            print("  %-28s -> %-4s  %s" % (s, code, eff))
        h = resolve_host(force=True)
        print("\n当前可用:", h)
        print("\n=== 搜索测试 ===")
        for kw in ("test", "abc"):
            r = search(kw, host=h)
            print("  %-8s -> %s" % (kw, json.dumps(r, ensure_ascii=False)[:160] if r else "None"))
