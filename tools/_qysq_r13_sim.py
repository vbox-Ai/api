# -*- coding: utf-8 -*-
"""qysq 第十三轮：解释器加「切片越界计数 + 哈希族可选 + 收尾真解密」

上一轮的结论：静态模拟跑通了，但 `sublist(8,48)` 在 32B 摘要上越界 —— 说明摘要族选错。
本轮把哈希族做成参数，判据很硬：

  · 正确配置下，**不该有任何一次 sublist 越界**（Dart 会抛 RangeError，App 就能跑了？）
  · 跑完直接用收集到的 Key / IV / ct = D[12:] 做 AES 解密，能 json.loads 才算真命中

三种族各跑一遍：sha256 / sha384 / sha512。
"""
import base64
import hashlib
import hmac
import json
import re
import sys
import time
import urllib.request
import uuid

from Crypto.Cipher import AES

ASM = r"C:\Users\Administrator\Downloads\DPK\_apk\blutter_out\asm\avbox\util\crypto_util.dart"
START, END = 0x7237f0, 0x723d44
BASE = "https://d1kmvkv4iwtiup.cloudfront.net"
SECRET = "gH3nA7fR9tV1jY6z"
DEV_UA = "DevType=Apple iPhone mobile;SysType=light;Ver=2.1.2;BuildID=Mobile Safari 18.5"
BR_UA = ("Mozilla/5.0 (iPhone; CPU iPhone OS 18_5 like Mac OS X) AppleWebKit/605.1.15 "
         "(KHTML, like Gecko) Version/18.5 Mobile/15E148 Safari/604.1")
TOKEN = ("eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJhdWQiOiJwdWJsaWMiLCJleHAiOjE3OTM4NTgxNjIs"
         "Imlzc3VlciI6ImNvbS5idXR0ZXJmbHkiLCJzdWIiOiJhc2lnbiIsInVzZXJJZCI6NTY3NzU4MX0."
         "yjzuUUUK1hlQBzlTQ703ZYemCvfL97EYsQNUCyEVET4")
OP = urllib.request.build_opener(urllib.request.ProxyHandler({}))

RAW = re.compile(r"^\s*//\s{3,}(0x[0-9a-f]+):\s+(.*)$")
PSEUDO = re.compile(r"^\s*//\s(0x[0-9a-f]+):\s+(.*)$")
MNEMS = {"mov", "movz", "ldur", "stur", "ldr", "str", "add", "sub", "lsl", "sdiv",
         "bl", "blr", "cmp", "b", "tbz", "tbnz", "ret", "brk", "cbz", "cbnz",
         "stp", "ldp", "and", "movk", "sxtw", "lsr", "asr"}


def load_insns(path, start, end):
    raw, pseudo = {}, {}
    for line in open(path, encoding="utf-8"):
        m = RAW.match(line)
        if m:
            a = int(m.group(1), 16)
            if start <= a < end:
                raw[a] = m.group(2).strip()
            continue
        m = PSEUDO.match(line)
        if m:
            a = int(m.group(1), 16)
            if start <= a < end:
                pseudo.setdefault(a, m.group(2).strip())
    out = []
    for a in sorted(set(raw) | set(pseudo)):
        r, p = raw.get(a, ""), pseudo.get(a, "")
        first = r.split()[0] if r.split() else ""
        text = r if first in MNEMS else (r or p)
        comment = (r or p).split(";", 1)[1].strip() if ";" in (r or p) else ""
        out.append((a, text, comment))
    return out


class Bytes(list):
    pass


class Grow(list):
    pass


class Str(str):
    pass


class Obj:
    def __init__(self, kind, **kw):
        self.kind = kind
        self.__dict__.update(kw)


class Algo:
    def __init__(self, name):
        self.name = name


D_BYTES = []
KEYB = None
IVB = None
LASTSET = None
STUB_DATA = []


class Stub:
    def content(self):
        return list(D_BYTES)


def fetch():
    path = "api/app/media/home"
    ts = int(time.time())
    nonce = str(uuid.uuid4())
    msg = "%s&/%s&%s&%s&%s" % (TOKEN, path, DEV_UA, ts, nonce)
    sign = hmac.new(SECRET.encode(), msg.encode(), hashlib.sha1).hexdigest()
    req = urllib.request.Request(
        BASE + "/" + path, data=b"{}", method="POST",
        headers={"X-User-Agent": DEV_UA, "user-agent": BR_UA,
                 "authorization": "Bearer " + TOKEN,
                 "x-api-key": "timestamp=%s;sign=%s;nonce=%s" % (ts, sign, nonce),
                 "Content-Type": "application/json"})
    with OP.open(req, timeout=20) as r:
        return json.loads(r.read().decode("utf-8", "replace"))


def simulate(sample_b64, algo_name):
    global D_BYTES
    D_BYTES = list(base64.b64decode(sample_b64 + "=" * (-len(sample_b64) % 4)))
    insns = load_insns(ASM, START, END)
    regs = {1: Str(sample_b64)}
    slots, stack, clamps = {}, [], []
    key = iv = ct = None

    def gr(n):
        if n in ("NULL", "xzr", "wzr"):
            return None
        try:
            return regs.get(int(n.lstrip("w").lstrip("x")))
        except Exception:
            return None

    def sr(n, v):
        try:
            regs[int(n.lstrip("w").lstrip("x"))] = v
        except Exception:
            pass

    def coerce(v):
        if isinstance(v, Stub):
            return v.content()
        if isinstance(v, Obj):
            return list(getattr(v, "bytes", None) or [])
        return v

    for addr, text, comment in insns:
        code = text.split(";")[0].strip()
        tok = code.replace(",", " ").split()
        if not tok:
            continue
        mn = tok[0]

        if mn == "mov":
            sr(tok[1], gr(tok[2]))
            continue
        if mn == "movz":
            sr(tok[1], int(tok[2].lstrip("#"), 0))
            continue
        if mn in ("ldur", "stur", "ldr", "str"):
            m = re.search(r"\[(fp|x\d+|SP|THR)(?:, #(-?(?:0x[0-9a-f]+|\d+)))?\]", code)
            if not m:
                continue
            base, off = m.group(1), m.group(2)
            offi = int(off, 0) if off else 0
            if base == "fp" and off:
                if mn in ("stur", "str"):
                    slots[offi] = gr(tok[1])
                else:
                    sr(tok[1], slots.get(offi))
            elif base.startswith("x"):
                dstobj = regs.get(int(base[1:]))
                if mn in ("stur", "str") and isinstance(dstobj, Obj):
                    dstobj.bytes = coerce(gr(tok[1]))
                    continue
                src = dstobj
                if isinstance(src, Stub):
                    src = src.content()
                if isinstance(src, Obj):
                    src = getattr(src, "bytes", None) if offi == 7 else len(getattr(src, "bytes", []) or [])
                elif isinstance(src, (list, bytes)):
                    src = len(src) if offi != 7 else Bytes(list(src))
                sr(tok[1], src)
            elif base == "SP":
                if mn in ("stur", "str"):
                    stack.append(gr(tok[1]))
                else:
                    sr(tok[1], stack.pop() if stack else None)
            continue
        if mn in ("add", "sub", "lsl", "sdiv", "lsr", "and"):
            if len(tok) >= 3 and tok[2] == "PP":
                ms = re.search(r'"((?:[^"\\]|\\.)*)"', comment)
                if ms:
                    sr(tok[1], Str(ms.group(1)))
                continue
            a = gr(tok[2])
            b = gr(tok[3]) if len(tok) > 3 else None
            if b is None and len(tok) > 3 and tok[3].startswith("#"):
                b = int(tok[3].lstrip("#"), 0)
            if isinstance(a, int) and isinstance(b, int):
                v = {"add": a + b, "sub": a - b, "lsl": a << b, "lsr": a >> b,
                     "and": a & b, "sdiv": (a // b if b else 0)}[mn]
                sr(tok[1], v)
            continue
        if mn == "bl":
            nm = comment
            if "Utf8Encoder::convert" in nm:
                regs[0] = Bytes(str(gr("x2")).encode())
            elif "::base64Decode" in nm:
                s = str(gr("x1"))
                regs[0] = Bytes(base64.b64decode(s + "=" * (-len(s) % 4)))
            elif "sublist" in nm:
                src = coerce(gr("x1"))
                st = gr("x2") or 0
                en = stack.pop() if stack else None
                if isinstance(src, list):
                    real_en = en if isinstance(en, int) else len(src)
                    if real_en > len(src):
                        clamps.append((addr, st, real_en, len(src)))
                    regs[0] = Bytes(list(src)[st:real_en])
                else:
                    regs[0] = Bytes()
            elif "addAll" in nm:
                dst, add = gr("x1"), coerce(gr("x2"))
                if isinstance(dst, list) and isinstance(add, list):
                    dst.extend(add)
            elif "_ofEfficientLengthIterable" in nm:
                regs[0] = Grow(list(coerce(gr("x2")) or []))
            elif "Hash::convert" in nm:
                data = coerce(gr("x2")) or []
                hf = {"sha256": hashlib.sha256, "sha384": hashlib.sha384,
                      "sha512": hashlib.sha512}[algo_name]
                regs[0] = Obj("Digest", bytes=Bytes(hf(bytes(list(data))).digest()))
            elif "fromList" in nm and "Uint8List" in nm:
                src = coerce(gr("x2"))
                if not isinstance(src, list):
                    src = coerce(gr("x1"))
                regs[0] = Bytes(list(src or []))
            elif "AllocateUint8Array" in nm:
                regs[0] = Stub()
            elif "_slowSetRange" in nm:
                global LASTSET
                dst, src = regs.get(0), coerce(gr("x5"))
                if not isinstance(src, list):
                    src = coerce(slots.get(-0x38)) or coerce(slots.get(-0x18))
                if isinstance(src, list):
                    LASTSET = list(src)
                    regs[0] = Bytes(list(src))
            elif "AllocateKeyStub" in nm:
                regs[0] = Obj("Key")
                print("   [dbg] Allocate Key @0x%x" % addr)
            elif "AllocateIVStub" in nm:
                regs[0] = Obj("IV")
            elif "AllocateEncryptedStub" in nm:
                regs[0] = Obj("Encrypted")
                print("   [dbg] Allocate Encrypted @0x%x" % addr)
            elif "Encrypter::decrypt" in nm:
                enc = gr("x2")
                ivv = gr("x3") or (stack.pop() if stack else None)
                ct = getattr(enc, "bytes", None)
                ivb = getattr(ivv, "bytes", None) or IVB
                try:
                    kb = bytes(list(KEYB or []))
                    ivb2 = bytes(list(ivb or []))[:16]
                    ctb = bytes(list(ct or []))
                    if len(kb) in (16, 24, 32) and len(ivb2) == 16 and ctb and len(ctb) % 16 == 0:
                        pt = AES.new(kb, AES.MODE_CBC, ivb2).decrypt(ctb)
                        try:
                            from Crypto.Util.Padding import unpad
                            pt = unpad(pt, 16)
                        except Exception:
                            pass
                        txt = pt.decode("utf-8", "replace")
                        print("   [AES] key=%dB iv=%dB ct=%dB -> %r" % (
                            len(kb), len(ivb2), len(ctb), txt[:120]))
                        try:
                            json.loads(txt)
                            print("   ★★★ 命中！key=%s iv=%s" % (kb.hex(), ivb2.hex()))
                            open("tools/_dec/qysq_plain.json", "w", encoding="utf-8").write(txt)
                        except Exception:
                            pass
                    else:
                        print("   [AES] 长度不合法 key=%s iv=%s ct=%s" % (
                            len(kb), len(ivb2), len(ctb)))
                except Exception as e:
                    print("   [AES] err", e)
            continue
        if "StoreField" in code:
            m = re.search(r"r(\d+)->field_([0-9a-f]+) = r(\d+)", code)
            if m:
                dst, src = regs.get(int(m.group(1))), coerce(regs.get(int(m.group(3))))
                if isinstance(dst, Obj):
                    dst.bytes = src
                    if dst.kind == "Key":
                        key = list(src) if isinstance(src, list) else None

    print("[%s] clamps=%d %s" % (algo_name, len(clamps), clamps[:4]))
    return clamps


def yield_result(k, iv, ct):
    def ln(v):
        if isinstance(v, Obj):
            v = getattr(v, "bytes", None)
        return len(v) if isinstance(v, (list, bytes)) else None
    print("   [decrypt] key=%s iv=%s ct=%s" % (ln(k), ln(iv), ln(ct)))


if __name__ == "__main__":
    j = fetch()
    print("[envelope] code=%s" % j.get("code"))
    for algo in ("sha256", "sha384", "sha512"):
        simulate(j["data"], algo)
