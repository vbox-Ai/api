# -*- coding: utf-8 -*-
"""one 平台 token 刷新 / 校验工具。

用法：
  python tools/one_token_tool.py check                 # 检查当前内置 token 状态
  python tools/one_token_tool.py verify <token>        # 验证某个 token 是否可用
  python tools/one_token_tool.py patch <token>         # 写入 muse_avbox.py 的 OneAdapter.TOKEN

背景：
  1) one 客户端内无登录/注册接口，token 唯一来源是 6868 splash 下发
  2) 6868 splash 已被服务端加固（"违规请求"），无法自动拉取
  3) 因此只能人工获取 token 后喂入

  token 获取途径（任选）：
    a) 真机抓包：iOS FLEX / Android HttpCanary 抓一次 App 启动
    b) 已登录设备的 plist：flutter.token_one
    c) 已解密的 splash 资产：tools/_dec/box_api_splash.json → token_one
"""
import base64
import hashlib
import json
import os
import re
import sys
import time
import urllib.request

sys.stdout.reconfigure(encoding="utf-8")

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SCRIPT = os.path.join(REPO, "sources", "welfare-js", "muse_avbox.py")
SPLASH = os.path.join(REPO, "tools", "_dec", "box_api_splash.json")

KEY = b"l*bv%Ziq000Biaog"
IV = b"8597506002939249"
SALT = "m4n2hjPeYWkD6tFpqKF^3HO^h24P@idT"
UA = "Dart/3.12 (dart:io)"
HOST = "https://api.3459381.com"
PROBE = "v2.5/navigation/getDemandTagList"


def payload_of(tok):
    try:
        parts = str(tok).split(".")
        if len(parts) < 2:
            return None
        seg = parts[1] + "=" * (-len(parts[1]) % 4)
        return json.loads(base64.urlsafe_b64decode(seg))
    except Exception:
        return None


def make_sign(ts, uuid):
    inner = hashlib.md5(("0.0.0.0.3." + ts + ".." + uuid).encode()).hexdigest()
    return hashlib.md5((inner + SALT).encode()).hexdigest()


def call_raw(token, uuid, timeout=30):
    """发一次探活请求，返回 (status, raw_bytes)。

    注意：必须带 user-key 空值头 —— urllib 会发送 "user-key: "，
    服务端据此视为"参数已提供"。curl 会丢弃空值头导致 401。
    """
    ts = str(int(time.time()))
    h = {
        "User-Agent": UA, "ip": "0.0.0.0", "uuid": uuid,
        "Content-Type": "application/x-www-form-urlencoded",
        "timestamp": ts, "platform": "3", "token": token,
        "sign": make_sign(ts, uuid), "user-key": "", "app-version": "2.6.4",
    }
    req = urllib.request.Request(HOST + "//" + PROBE, data=b"", headers=h, method="POST")
    op = urllib.request.build_opener(
        urllib.request.ProxyHandler({"http": "http://127.0.0.1:7890",
                                     "https": "http://127.0.0.1:7890"}))
    with op.open(req, timeout=timeout) as r:
        return r.status, r.read()


def decrypt(raw):
    from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
    p = raw.decode("utf-8", "replace").strip()
    if p[:1] in ("{", "["):
        return json.loads(p)
    if p[:1] == '"':
        p = json.loads(p)
    ct = base64.b64decode(p + "=" * (-len(p) % 4))
    d = Cipher(algorithms.AES(KEY), modes.CBC(IV)).decryptor()
    pt = d.update(ct) + d.finalize()
    n = pt[-1] if pt else 0
    if 1 <= n <= 16:
        pt = pt[:-n]
    return json.loads(pt.decode("utf-8", "replace"))


def verify(token):
    pl = payload_of(token)
    if not pl:
        print("  [X] 不是合法 JWT")
        return False
    uuid = pl.get("uuid") or ""
    exp = pl.get("exp")
    now = int(time.time())
    if exp:
        left = exp - now
        print("  exp=%s  剩余 %.2f 小时  %s" % (
            exp, left / 3600.0, "已过期" if left <= 0 else "有效期内"))
    print("  iss=%s  visitor=%s  uuid=%s" % (pl.get("iss"), pl.get("is_visitor"), uuid))
    try:
        st, raw = call_raw(token, uuid)
        obj = decrypt(raw)
        code = obj.get("code")
        print("  HTTP %s  code=%s  msg=%s" % (st, code, obj.get("message")))
        if code == 200:
            n = len(obj.get("data") or [])
            print("  [OK] token 可用，返回 %d 条分类" % n)
            return True
        print("  [X] token 不可用")
        return False
    except Exception as e:
        print("  [X] 验证失败: %s" % str(e)[:120])
        return False


def current_token():
    """从 muse_avbox.py 里读出内置 TOKEN。"""
    src = open(SCRIPT, encoding="utf-8").read()
    m = re.search(r'TOKEN\s*=\s*\(([^)]*)\)', src, re.S)
    if not m:
        return None
    raw = re.sub(r'"\s*\n\s*"', "", m.group(1)).strip().strip('"')
    return raw


def patch(token):
    """把新 token 写入 OneAdapter.TOKEN，并按 JWT 自动更新 UUID。"""
    pl = payload_of(token)
    if not pl or not pl.get("uuid"):
        print("[X] token 无效，无法提取 uuid")
        return False
    src = open(SCRIPT, encoding="utf-8").read()

    # 按 76 字符折叠，保持代码风格
    chunks = [token[i:i + 76] for i in range(0, len(token), 76)]
    if len(chunks) == 1:
        new_block = 'TOKEN = "%s"' % chunks[0]
    else:
        parts = ['"%s"' % chunks[0]]
        for c in chunks[1:-1]:
            parts.append('"%s"' % c)
        parts.append('"%s")' % chunks[-1])
        joined = ("\n             ".join(parts))
        new_block = "TOKEN = (" + joined

    src2, n = re.subn(r'TOKEN\s*=\s*\([^)]*\)', new_block, src, count=1, flags=re.S)
    if n != 1:
        src2, n = re.subn(r'TOKEN\s*=\s*"[^"]*"', new_block, src, count=1)
    if n != 1:
        print("[X] 未找到 TOKEN 定义，未修改")
        return False

    src2, m2 = re.subn(r'UUID\s*=\s*"[0-9a-fA-F\-]{36}"',
                       'UUID = "%s"' % pl["uuid"], src2, count=1)
    if m2 != 1:
        print("[!] UUID 未更新（可能定义格式不同）")

    open(SCRIPT, "w", encoding="utf-8").write(src2)
    print("[OK] 已写入 muse_avbox.py")
    print("     新 exp=%s  剩余 %.2f 小时" % (
        pl.get("exp"), (pl["exp"] - time.time()) / 3600.0 if pl.get("exp") else -1))
    return True


def main():
    cmd = sys.argv[1] if len(sys.argv) > 1 else "check"

    if cmd == "check":
        tok = current_token()
        if not tok:
            print("未找到内置 token")
            return 1
        print("当前内置 token（前 30 位）:", tok[:30])
        return 0 if verify(tok) else 2

    if cmd == "verify" and len(sys.argv) > 2:
        return 0 if verify(sys.argv[2]) else 2

    if cmd == "patch" and len(sys.argv) > 2:
        if not verify(sys.argv[2]):
            print("\n验证未通过，拒绝写入。加 --force 可强制写入。")
            if "--force" not in sys.argv:
                return 2
        return 0 if patch(sys.argv[2]) else 1

    if cmd == "from-splash":
        if not os.path.exists(SPLASH):
            print("找不到", SPLASH)
            return 1
        s = json.load(open(SPLASH, encoding="utf-8"))
        tok = None
        for t in s["data"]["token"]:
            if t["name"] == "token_one":
                tok = t["token"]
        if not tok:
            print("splash 里没有 token_one")
            return 1
        print("从 splash 资产取到 token_one，验证中...")
        if verify(tok):
            return 0 if patch(tok) else 1
        print("该 token 已失效，需从真机重新获取")
        return 2

    print(__doc__)
    return 1


if __name__ == "__main__":
    sys.exit(main())
