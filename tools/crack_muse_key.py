# -*- coding: utf-8 -*-
"""
crack_muse_key.py — 暮色(avbox) AES 密钥一键提取
=================================================

原理（2026-10-30 Blutter 反编译实证）：
  暮色客户端把 AES Key/IV 以「切罗基字母(Cherokee, U+13A0~U+13FF) UTF-16LE」
  形式硬编码在 Dart AOT 快照(libapp.so / App)里，运行时经 StringExtension.s()
  逐码元 XOR 0x1395 还原为 16 位 hex 字符串：
      "ᎭᎬᎬ..."  --XOR 0x1395-->  "8992d27bceae2962"  (Key)
  解密链：base64 → AES-128-CBC → gzip → JSON

用法：
  python crack_muse_key.py <暮色.apk | libapp.so | App>
  python crack_muse_key.py <路径> --out key.json

特性：
  1. 直接字节级模式匹配，不需要 Blutter / 不需要编译环境，秒级完成
  2. 自动探测 XOR 掩码：即使暮色换掩码(不再 0x1395)也能暴力 0x0000~0xFFFF 找回
  3. APK 输入自动解包取 lib/arm64-v8a/libapp.so

适用版本：暮色 iOS 1.0.1 / 安卓 1.0.1（后续版本若未改混淆方式同样适用）
"""
import sys
import os
import json
import zipfile
import tempfile
import io

CHEROKEE_LO, CHEROKEE_HI = 0x13A0, 0x13FF
KEY_LEN = 16
HEX_CHARS = set("0123456789abcdef")
DEFAULT_MASK = 0x1395


def scan_cherokee_runs(data: bytes):
    """扫描二进制中的 UTF-16LE 切罗基连续串。
    返回 [(start_offset, [code_units]), ...]，仅保留长度 >= 8 的串。"""
    runs = []
    n = len(data)
    i = 0
    # Dart TwoByteString 对象内容通常 8 字节对齐，但为鲁棒性逐字节步进
    while i + 1 < n:
        cu = data[i] | (data[i + 1] << 8)
        if CHEROKEE_LO <= cu <= CHEROKEE_HI:
            start = i
            units = []
            while i + 1 < n:
                cu2 = data[i] | (data[i + 1] << 8)
                if not (CHEROKEE_LO <= cu2 <= CHEROKEE_HI):
                    break
                units.append(cu2)
                i += 2
            if len(units) >= 8:
                runs.append((start, units))
        else:
            i += 1
    return runs


def try_decode(units, mask):
    """按掩码解码，返回 (plaintext, is_hex16)"""
    dec = "".join(chr(u ^ mask) for u in units)
    ok = len(dec) == KEY_LEN and all(c in HEX_CHARS for c in dec)
    return dec, ok


def crack(data: bytes):
    """主提取逻辑。返回结果列表"""
    findings = []
    seen = set()
    for off, units in scan_cherokee_runs(data):
        # 只处理 run 长度 16（独立 Key/IV 常量）与 32（Key+IV 连体），
        # 跳过其他长度（如 32+ 的 MD5 盐等长串切窗噪声）
        if len(units) == KEY_LEN:
            windows = [(off, 0, units)]
        elif len(units) == 2 * KEY_LEN:
            windows = [(off, 0, units[:KEY_LEN]), (off, 1, units[KEY_LEN:])]
        else:
            continue
        for base, widx, win in windows:
            woff = base + widx * KEY_LEN * 2
            # ① 先试已知掩码 0x1395
            dec, ok = try_decode(win, DEFAULT_MASK)
            if ok:
                if dec not in seen:
                    seen.add(dec)
                    findings.append({"offset": woff, "mask": hex(DEFAULT_MASK),
                                     "value": dec, "run_len": len(units), "how": "known-mask"})
                continue
            # ② 已知掩码失败 → 暴力探测任意掩码（只接受能解出 16-hex 的）
            for mask in range(0x10000):
                dec, ok = try_decode(win, mask)
                if ok:
                    if dec not in seen:
                        seen.add(dec)
                        findings.append({"offset": woff, "mask": hex(mask),
                                         "value": dec, "run_len": len(units), "how": "brute-mask"})
                    break
    findings.sort(key=lambda f: f["offset"])
    return findings


def load_target(path: str):
    """APK → 解包取 libapp.so；其他按原始二进制读"""
    with open(path, "rb") as f:
        head = f.read(4)
    if head[:2] == b"PK" and path.lower().endswith(".apk"):
        print("[*] 检测到 APK，解包提取 lib/arm64-v8a/libapp.so ...")
        with zipfile.ZipFile(path) as z:
            names = [n for n in z.namelist()
                     if n.endswith("libapp.so") or n.endswith("App")]
            if not names:
                raise SystemExit("[!] APK 内未找到 libapp.so / App")
            target = sorted(names, key=lambda n: (0 if "arm64" in n else 1, n))[0]
            print("[*] 使用: %s" % target)
            with z.open(target) as f:
                buf = f.read()
        return buf, target
    buf = open(path, "rb").read()
    return buf, os.path.basename(path)


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)
    path = sys.argv[1]
    out_path = None
    if "--out" in sys.argv:
        out_path = sys.argv[sys.argv.index("--out") + 1]

    print("[*] 目标: %s" % path)
    data, name = load_target(path)
    print("[*] 二进制大小: %.1f MB" % (len(data) / 1048576.0))

    findings = crack(data)
    if not findings:
        print("[!] 未找到切罗基混淆密钥 —— 暮色可能换了混淆方式，"
              "需回退 Blutter 全量反编译（见 docs/暮色逆向全流程方法.md 第 5 节）")
        sys.exit(2)

    print("[+] 命中 %d 个候选：" % len(findings))
    for f in findings:
        print("    offset=0x%08X  mask=%s  how=%s  value=%s"
              % (f["offset"], f["mask"], f["how"], f["value"]))

    keys = [f["value"] for f in findings]
    # Key/IV 自动判定：只取「独立 16 长常量」(run_len==16) 的候选，
    # run32 切片（通常是 MD5 盐等长串）标为参考
    primaries = [f["value"] for f in findings if f.get("run_len") == KEY_LEN]
    result = {
        "app": "muse(avbox)",
        "binary": name,
        "count": len(findings),
        "findings": findings,
        "cipher": "AES-128-CBC / base64 → decrypt → gzip → JSON",
    }
    if len(primaries) == 2:
        # 暮色 1.0.1 实证布局：对象池中 IV 常量在 Key 之前（offset 小者为 IV）。
        # 新版本若解密验证不符，交换二者即可。
        result["aes_iv"] = primaries[0]
        result["aes_key"] = primaries[1]
        result["note"] = "Key/IV 按 1.0.1 对象池布局推断(offset 小者=IV)；如解密验证不符请交换"
    print()
    print("=" * 52)
    print("  候选密钥(按 offset 升序):")
    for f in findings:
        tag = " <== 独立常量" if f.get("run_len") == KEY_LEN else "      (来自%d长串,参考)" % f.get("run_len", 0)
        print("    %s%s" % (f["value"], tag))
    if result.get("aes_key"):
        print("  判定: AES_KEY=%s  AES_IV=%s" % (result["aes_key"], result["aes_iv"]))
        print("  数据流: base64 → AES-128-CBC → gzip → JSON")
    else:
        print("  [!] 独立常量候选数 != 2，无法自动判定 Key/IV，请用真实密文逐一验证")
    print("=" * 52)

    if out_path:
        with io.open(out_path, "w", encoding="utf-8") as f:
            json.dump(result, f, ensure_ascii=False, indent=2)
        print("[*] 已写入 %s" % out_path)


if __name__ == "__main__":
    main()
