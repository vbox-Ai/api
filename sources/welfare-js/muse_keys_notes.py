# -*- coding: utf-8 -*-
"""
暮色 6868 协议分析 + 存储键清单（只读工具，不做网络请求）
================================================================
结论（2026-10-29 抓包实证）：
  1) 鉴权 = time(13位毫秒) + uuid(32位hex, 每次请求随机, 不是设备号)
  2) /box/api/ping 免鉴权, 固定返回 32 字节 base64
  3) /collect/api/status 额外带 token 头（登录态, 154 字符, 多次请求复用）
  4) 响应体 = base64(AES 密文), 16 字节对齐, 确定性（同请求同密文）
  5) 服务端有来源校验：非手机网络一律返回 {"code":400,"msg":"违规请求"}
     —— 用真 token + 真 body 从 PC 重放同样被拒，说明按来源 IP 拦截

密钥不在二进制里：
  · 341,124 个 ASCII 子串（16/24/32）→ 全部失败
  · 7,995 个 base64 串（解码后 16/24/32）→ 全部失败
  · 3,045,688 个 4 字节对齐原始窗口 → 全部失败
  · 27,266 条 ASCII 串的 md5/sha256 派生 → 全部失败
  · AES-ECB/CBC/CTR/CFB/OFB/GCM + ChaCha20/ChaCha20-Poly1305 → 全部失败

真实密钥在设备本地存储（SharedPreferences 键名已从二进制取出）：
  encrypt_key            主加密密钥
  avkey                  备用/播放密钥
  m3u8_host_encrypt      m3u8 主机加密串
  token_box / token_av91 / token_hxsp / token_qysq / token_mmmh /
  token_one / token_one_visitor / token_fl2 / token_fl2_refresh /
  token_akmh / token_hjsq / token_rryy / token_djr / token_hdb /
  token_txvlog / token_zlt            ← 各平台独立登录令牌
  domain / domain_original / domain_novel / image_domain /
  domain_picture / domain_comic / domain_preview   ← 各资源域
  device_id / deviceid / devicefingerprint / devicetype /
  devicemodel / devicebrand / user_id / username / cdkey

读取方法（越狱机, Filza）：
  /var/mobile/Containers/Data/Application/<UUID>/Library/Preferences/com.look.avbox.plist

拿到 encrypt_key 后，用 decrypt.py 的 decrypt() 解任意响应体。
"""

STORAGE_KEYS = {
    "crypto": ["encrypt_key", "avkey", "m3u8_host_encrypt"],
    "platform_tokens": [
        "token_box", "token_av91", "token_hxsp", "token_qysq", "token_mmmh",
        "token_one", "token_one_visitor", "token_fl2", "token_fl2_refresh",
        "token_akmh", "token_hjsq", "token_rryy", "token_djr", "token_hdb",
        "token_txvlog", "token_zlt",
    ],
    "domains": [
        "domain", "domain_original", "domain_novel", "image_domain",
        "domain_picture", "domain_comic", "domain_preview",
    ],
    "device": [
        "device_id", "deviceid", "devicefingerprint", "devicetype",
        "devicemodel", "devicebrand", "user_id", "username", "cdkey",
    ],
}

KNOWN_ENDPOINTS = {
    "6868 明文通道": [
        "/box/api/ping",            # 免鉴权, 返回 32B base64
        "/box/api/splash",          # 需 time+uuid
        "/box/api/home?versionCode=101",  # 需 time+uuid, 返回加密包
        "/collect/api/status",      # POST, 需 time+uuid+token, body 加密
    ],
    "IPA 内其余路由": [
        "/app/ping/config", "/app/media/home", "/app/live/home",
        "/api/v2/index_items", "/api/v1/video", "/api/v2/query/result",
        "/api/videos/list_contents", "/api/contents/list_contents",
        "/api/community/list_construct",
    ],
}


def decrypt(b64_text, key, iv=None, mode="CBC"):
    """拿到 encrypt_key 后调用：解一条 base64 响应体"""
    import base64 as _b64
    from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes as _m
    s = b64_text.strip().strip('"')
    raw = _b64.b64decode(s + "=" * (-len(s) % 4))
    k = key if isinstance(key, bytes) else _b64.b64decode(key)
    v = iv or bytes(16)
    if isinstance(v, str):
        v = _b64.b64decode(v)
    if mode == "CBC":
        c = Cipher(algorithms.AES(k), _m.CBC(v))
    elif mode == "ECB":
        c = Cipher(algorithms.AES(k), _m.ECB())
    elif mode == "CTR":
        c = Cipher(algorithms.AES(k), _m.CTR(v))
    else:
        raise ValueError("mode: CBC/ECB/CTR")
    d = c.decryptor()
    return d.update(raw) + d.finalize()


if __name__ == "__main__":
    print("存储键（需从设备 plist 读取）：")
    for group, keys in STORAGE_KEYS.items():
        print(f"  [{group}]")
        for k in keys:
            print("    ", k)
    print("\n已知端点：")
    for group, eps in KNOWN_ENDPOINTS.items():
        print(f"  [{group}]")
        for e in eps:
            print("    ", e)
