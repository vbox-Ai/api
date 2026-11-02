# -*- coding: utf-8 -*-
"""扫描 blutter 反汇编各平台 interceptor，按鉴权复杂度排序，挑下一个目标"""
import os
import re

ASM = r"C:\Users\Administrator\Downloads\DPK\_apk\blutter_out\asm\avbox\module"

# 已交付/已放弃的不看
SKIP = {"hjsq", "hdb", "mmav", "rryy", "one", "hxsp", "hgsp", "4hu", "hu4",
        "qysq", "51cg", "cgw", "djr", "missav", "akmh", "av91", "sp91",
        "cg51", "ltb", "pron91", "box", "live", "fl2"}

SIG_HINTS = ["sign", "Sign", "signature", "md5", "MD5", "sha", "SHA", "HMAC",
             "hmac", "encrypt", "Encrypt", "AES", "aes", "RSA", "nonce",
             "Nonce", "timestamp", "TimeStamp", "key", "secret", "Secret"]

rows = []
if not os.path.isdir(ASM):
    print("asm 目录不存在: %s" % ASM)
    raise SystemExit(1)

for mod in sorted(os.listdir(ASM)):
    if mod in SKIP:
        continue
    d = os.path.join(ASM, mod)
    if not os.path.isdir(d):
        continue
    # 找 interceptor / service
    targets = []
    for root, _, files in os.walk(d):
        for fn in files:
            if fn in ("interceptor.dart", "service.dart", "http.dart", "api.dart"):
                targets.append(os.path.join(root, fn))
    if not targets:
        continue

    strs = []
    raw = ""
    for t in targets:
        txt = open(t, encoding="utf-8", errors="ignore").read()
        raw += txt
        # 提取引号字符串常量
        strs += re.findall(r'r\d+ = "([^"]{1,80})"', txt)
        strs += re.findall(r'\[pp\+[^\]]*\] "([^"]{1,80})"', txt)

    uniq = []
    for s in strs:
        if s not in uniq:
            uniq.append(s)

    low = raw.lower()
    hints = sum(low.count(h.lower()) for h in
               ["sign", "md5", "sha1", "sha256", "hmac", "nonce", "timestamp", "secret"])

    # 判断是否有明显签名链
    has_hmac = any(k in low for k in ("hmac", "md5(", "sha1", "sha256"))
    rows.append({
        "mod": mod,
        "files": len(targets),
        "hint_score": hints,
        "has_digest": has_hmac,
        "strings": uniq[:14],
    })

rows.sort(key=lambda r: (r["has_digest"], r["hint_score"], -len(r["strings"])))
print("候选 %d 个（按鉴权复杂度升序）\n" % len(rows))
for r in rows[:16]:
    print("=" * 70)
    print("%-10s files=%d  hint=%d  摘要签名=%s" %
          (r["mod"], r["files"], r["hint_score"], "是" if r["has_digest"] else "否"))
    print("  常量:", " | ".join(r["strings"][:14])[:400])
