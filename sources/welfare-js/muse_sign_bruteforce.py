# -*- coding: utf-8 -*-
"""
暮色(avbox) 签名算法自适应爆破器 — 纯标准库
================================================================
用途：拿到一个「活」的后端域名后，一键穷举签名拼接顺序，自动定钥。
      配合 muse_avbox.py 使用；定钥后把命中的组合填进 extend.signMode。

背景（逆向 暮色 1.0.1 IPA 得到的证据）：
  · 鉴权四件套：X-Auth-Key / X-Auth-TimeStamp / X-Auth-Nonce / X-Auth-Sign
  · AppKey 常量：368480924a6c78e2e8681551a7cf4c21（编译期常量，字符串池里
    直接出现完整折叠串 "&X-Auth-Key=368480924a6c78e2e8681551a7cf4c21"）
  · 混淆函数名证据：_generateSign@1325267197 / _nonce@1725101045
    _calculateMac@1437296910（missav 模块）/ buildSignature / encode_sign
  · 哈希实现：package:crypto (md5/sha1/sha256/hmac) + pointycastle
  · 请求体信封：RSA 公钥 + package:encrypt（Encrypted.fromUtf8）

用法：
  python muse_sign_bruteforce.py <host> [--key KEY] [--path /api/v2/index_items]
"""
import sys, time, ssl, hashlib, hmac, base64, random, json
import urllib.request, urllib.error, urllib.parse

ctx = ssl.create_default_context(); ctx.check_hostname = False; ctx.verify_mode = ssl.CERT_NONE
UA = "Dart/3.9 (dart:io)"

KEY = "368480924a6c78e2e8681551a7cf4c21"
PATH = "/api/v2/index_items"

# 候选 secret（IPA 字符串池里扫到的疑似模块密钥，可覆盖性参与爆破）
CANDIDATE_SECRETS = [
    "",  # 关键：很多实现只用 AppKey，secret 为空
    "cuke@appSecret#Ten2020!0120",
    "Z7tSXMjByKCFzF5tyApk8cFpjQXD8zWdr",
    "0XxdjmI55ZjjqQLO3nI7gGqrBP0Vz9jS",
    "hyfr6iyPZMZfJFEcr",
    "F16wCJ3LmWY=",
    "k54Vcjbp6ByR6D83eIoxgw==",
]


def dg(name, data):
    return hashlib.new(name, data if isinstance(data, bytes) else data.encode())


def make_sign(mode, key, secret, ts, nonce, path):
    K, S, T, N, P = key, secret, ts, nonce, path
    pieces = {
        "K": K, "S": S, "T": T, "N": N, "P": P,
        "K_T_N": K + T + N,
        "K_N_T": K + N + T,
        "T_N_K": T + N + K,
        "N_T_K": N + T + K,
        "K_S_T_N": K + S + T + N,
        "S_K_T_N": S + K + T + N,
        "K_P_T_N": K + P + T + N,
        "P_K_T_N": P + K + T + N,
        "K_T_S_N": K + T + S + N,
        "K_P_N_T": K + P + N + T,
        "P_T_N_K": P + T + N + K,
        "T_N": T + N,
        "K_T": K + T,
        "K_N": K + N,
    }
    mode = mode.lower()
    def piece(tag):
        return pieces[tag.upper()]
    # md5 族
    if mode.startswith("md5:"):
        return hashlib.md5(piece(mode[4:]).encode()).hexdigest()
    if mode.startswith("sha1:"):
        return hashlib.sha1(piece(mode[5:]).encode()).hexdigest()
    if mode.startswith("sha256:"):
        return hashlib.sha256(piece(mode[7:]).encode()).hexdigest()
    # hmac 族（key = K 或 S）
    if mode.startswith("hmac_md5_k:"):
        return hmac.new(K.encode(), piece(mode[11:]).encode(), hashlib.md5).hexdigest()
    if mode.startswith("hmac_md5_s:"):
        return hmac.new(S.encode(), piece(mode[11:]).encode(), hashlib.md5).hexdigest()
    if mode.startswith("hmac_sha256_k:"):
        return hmac.new(K.encode(), piece(mode[14:]).encode(), hashlib.sha256).hexdigest()
    if mode.startswith("hmac_sha256_s:"):
        return hmac.new(S.encode(), piece(mode[14:]).encode(), hashlib.sha256).hexdigest()
    # base64 族
    if mode.startswith("b64_md5:"):
        return base64.b64encode(hashlib.md5(piece(mode[8:]).encode()).digest()).decode()
    raise ValueError("bad mode " + mode)


def build_modes():
    concat = ["K_T_N", "K_N_T", "T_N_K", "N_T_K", "K_S_T_N", "S_K_T_N",
              "K_P_T_N", "P_K_T_N", "K_T_S_N", "K_P_N_T", "P_T_N_K",
              "T_N", "K_T", "K_N"]
    modes = []
    for c in concat:
        modes.append("md5:" + c)
        modes.append("sha1:" + c)
        modes.append("sha256:" + c)
    for c in ["K_T_N", "K_S_T_N", "K_P_T_N", "T_N_K"]:
        modes.append("hmac_md5_k:" + c)
        modes.append("hmac_md5_s:" + c)
        modes.append("hmac_sha256_k:" + c)
        modes.append("hmac_sha256_s:" + c)
    for c in ["K_T_N", "K_S_T_N"]:
        modes.append("b64_md5:" + c)
    return modes


def probe(host, path, key, secret, mode, ts, nonce):
    sign = make_sign(mode, key, secret, ts, nonce, path)
    qs = urllib.parse.urlencode({
        "X-Auth-Key": key,
        "X-Auth-TimeStamp": ts,
        "X-Auth-Nonce": nonce,
        "X-Auth-Sign": sign,
    })
    url = host + path + "?" + qs
    req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=8, context=ctx) as r:
            body = r.read(400).decode("utf-8", "replace")
            return r.status, body
    except urllib.error.HTTPError as e:
        return e.code, e.read(400).decode("utf-8", "replace")
    except Exception as e:
        return "ERR", str(e)[:80]


def main():
    host = sys.argv[1] if len(sys.argv) > 1 else "https://api.3459381.com"
    key = KEY
    path = PATH
    if "--key" in sys.argv:
        key = sys.argv[sys.argv.index("--key") + 1]
    if "--path" in sys.argv:
        path = sys.argv[sys.argv.index("--path") + 1]

    modes = build_modes()
    print("host=%s path=%s key=%s" % (host, path, key))
    print("total combos:", len(modes) * len(CANDIDATE_SECRETS))

    ts = str(int(time.time()))
    nonce = "%016x" % random.getrandbits(64)

    hits = []
    for secret in CANDIDATE_SECRETS:
        for mode in modes:
            st, body = probe(host, path, key, secret, mode, ts, nonce)
            ok = False
            if st == 200:
                try:
                    obj = json.loads(body)
                    ok = obj.get("code") in (0, 200) or "data" in obj
                except Exception:
                    ok = "Wrong path" not in body and "系统繁忙" not in body
            if ok:
                print("HIT  secret=%r mode=%s status=%s body=%s" % (secret, mode, st, body[:140]))
                hits.append((secret, mode, body))
            elif st not in (404, 500, 403) and st != "ERR":
                # 非标准状态，值得记录
                print("note secret=%r mode=%s status=%s body=%s" % (secret, mode, st, body[:120]))

    if hits:
        print("\n=== RESULT ===")
        for s, m, b in hits:
            print("signMode=%r secret=%r" % (m, s))
    else:
        print("\n未命中：后端域名可能已失效（返回统一 500 兜底），需先拿到活域名或真机抓包。")
        print("提示：尝试 /api/v1/system/domain 或 /api/<hash>/r 获取动态域名后重跑本脚本。")


if __name__ == "__main__":
    main()
