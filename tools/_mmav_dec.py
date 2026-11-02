# -*- coding: utf-8 -*-
"""mmav 解密实现。

从 avbox/module/mmav/network/interceptor.dart 反汇编还原：

  IV  = response["suffix"] + "$0v@krH7V2"
  Key = "IdTJq0HklpuI6mu8iB%OO@!vd^4K&uXW"      (32 字符 → AES-256)
  plain = AES-CBC-decrypt( key, iv, base64decode(response["data"]) )
        → jsonDecode

注意：IV 是「响应里的 suffix 拼固定后缀」，动态的，不能用固定值。
"""
import base64
import hashlib
import json
import subprocess
import sys

from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes

sys.stdout.reconfigure(encoding="utf-8")

CURL = r"C:\Windows\System32\curl.exe"
HOST = "https://bvbvbvssu.a63qv1sy.com"
KEY = b"IdTJq0HklpuI6mu8iB%OO@!vd^4K&uXW"
IV_SUFFIX = "$0v@krH7V2"


def fetch(path, timeout=25):
    cmd = [CURL, "-s", "-S", "--max-time", str(timeout), "-k",
           "-H", "User-Agent: okhttp/4.9.0", HOST + "/" + path]
    r = subprocess.run(cmd, capture_output=True, timeout=timeout + 15)
    return r.stdout.decode("utf-8", "replace")


def decrypt(obj):
    """obj 为服务端返回的外层 JSON（含 data / suffix）"""
    data = obj.get("data")
    suffix = obj.get("suffix") or ""
    if not data:
        return None
    # IV = 固定常量 + suffix（顺序已实测确认，反写会解出乱码）
    iv = (IV_SUFFIX + suffix).encode("utf-8")
    if len(iv) != 16:
        return {"_err": "IV 长度不是 16: %d (suffix=%r)" % (len(iv), suffix)}
    try:
        raw = base64.b64decode(data + "=" * (-len(data) % 4))
    except Exception as e:
        return {"_err": "base64 失败: %s" % e}
    if len(raw) % 16:
        return {"_err": "密文长度非 16 倍数: %d" % len(raw)}
    try:
        d = Cipher(algorithms.AES(KEY), modes.CBC(iv)).decryptor()
        pt = d.update(raw) + d.finalize()
        n = pt[-1] if pt else 0
        if 1 <= n <= 16:
            pt = pt[:-n]
        return json.loads(pt.decode("utf-8", "replace"))
    except Exception as e:
        return {"_err": "解密失败: %s" % str(e)[:100]}


def fetch_decoded(path):
    txt = fetch(path)
    try:
        obj = json.loads(txt)
    except Exception:
        return {"_err": "外层非 JSON", "_raw": txt[:200]}
    if obj.get("code") != 0:
        return {"_err": "code=%s msg=%s" % (obj.get("code"), obj.get("msg")), "_outer": obj}
    return decrypt(obj)


if __name__ == "__main__":
    for p in ("data/category/base-1.js", "data/config/base-1.js"):
        print("=" * 70)
        print(p)
        txt = fetch(p)
        obj = json.loads(txt)
        print("  外层 suffix=%r" % obj.get("suffix"))
        print("  IV 将是:", repr(IV_SUFFIX + (obj.get("suffix") or "")))
        res = decrypt(obj)
        if isinstance(res, dict) and res.get("_err"):
            print("  失败:", res)
        else:
            s = json.dumps(res, ensure_ascii=False)
            print("  ✅ 解密成功  明文长度 %d" % len(s))
            print("  前 400:", s[:400])
        print()
