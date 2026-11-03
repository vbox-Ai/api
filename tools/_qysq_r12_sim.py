# -*- coding: utf-8 -*-
"""qysq 第十二轮（修订）：asGjCrypto 指令级迷你解释器

上一版拿不到任何指令：blutter 同一地址会输出「伪代码行」与「真实指令行」两种，
需要按缩进区分（伪代码 `// 0xADDR:`，真实指令 `//     0xADDR:`），否则全被伪代码覆盖。

本版：
  · raw[addr]（真实指令）优先，pseudo[addr] 仅用于取 `;` 后的注释（池字符串等）
  · 初始把函数入参 r1 = base64 密文串
  · 分支全部忽略（两条路径语义等价，都是 memcpy）
  · 跑完打印各栈槽内容 + 关键调用 trace，并用样本验证 key/iv
"""
import base64
import hashlib
import hmac
import json
import re
import time
import urllib.request
import uuid

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
            addr = int(m.group(1), 16)
            if start <= addr < end:
                raw[addr] = m.group(2).strip()
            continue
        m = PSEUDO.match(line)
        if m:
            addr = int(m.group(1), 16)
            if start <= addr < end:
                pseudo.setdefault(addr, m.group(2).strip())
    out = []
    for addr in sorted(set(raw) | set(pseudo)):
        r = raw.get(addr, "")
        p = pseudo.get(addr, "")
        first = r.split()[0] if r.split() else ""
        text = r if first in MNEMS else (r or p)
        comment = ""
        if ";" in (r or p):
            comment = (r or p).split(";", 1)[1].strip()
        out.append((addr, text, comment))
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


D_BYTES = None


class Stub:
    def __init__(self):
        self.data = None

    def content(self):
        return list(self.data if self.data is not None else (D_BYTES or []))


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


def run(sample_b64):
    global D_BYTES
    D_BYTES = list(base64.b64decode(sample_b64 + "=" * (-len(sample_b64) % 4)))
    insns = load_insns(ASM, START, END)
    print("[asm] %d 条" % len(insns))
    regs = {1: Str(sample_b64)}
    slots, stack, trace = {}, [], []

    def gr(name):
        if name in ("NULL", "xzr", "wzr"):
            return None
        n = name.lstrip("w").lstrip("x")
        try:
            return regs.get(int(n))
        except Exception:
            return None

    def sr(name, v):
        n = name.lstrip("w").lstrip("x")
        try:
            regs[int(n)] = v
        except Exception:
            pass

    for addr, text, comment in insns:
        code = text.split(";")[0].strip()
        tok = code.replace(",", " ").split()
        if not tok:
            continue
        mn = tok[0]

        if "LoadField" in code:
            m = re.search(r"r(\d+) = r(\d+)->field_([0-9a-f]+)", code)
            if m:
                src = regs.get(int(m.group(2)))
                if isinstance(src, (list, bytes)):
                    sr("x" + m.group(1), len(src))
                elif isinstance(src, Obj) and hasattr(src, "bytes"):
                    sr("x" + m.group(1), src.bytes)
            continue
        if "StoreField" in code:
            m = re.search(r"r(\d+)->field_([0-9a-f]+) = r(\d+)", code)
            if m:
                dst, src = regs.get(int(m.group(1))), regs.get(int(m.group(3)))
                if isinstance(dst, Obj):
                    dst.bytes = src
            continue

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
                # 对象字段：field_7 = bytes，其余视为长度
                src = regs.get(int(base[1:]))
                if isinstance(src, Stub) and src.data is not None:
                    src = src.data
                if isinstance(src, Obj):
                    src = (getattr(src, "bytes", None) if offi == 7 else len(getattr(src, "bytes", []) or []))
                elif isinstance(src, (list, bytes)):
                    src = len(src) if offi != 7 else Bytes(list(src))
                sr(tok[1], src)
            elif base == "SP" and mn in ("stur", "str"):
                stack.append(gr(tok[1]))
            elif base == "SP" and mn in ("ldur", "ldr"):
                sr(tok[1], stack.pop() if stack else None)
            continue
        if mn in ("add", "sub", "lsl", "sdiv", "lsr", "and"):
            if len(tok) >= 3 and tok[2] == "PP":
                ms = re.search(r'"((?:[^"\\]|\\.)*)"', comment)
                if ms:
                    sr(tok[1], Str(ms.group(1)))
                continue
            a = gr(tok[2])
            b = None
            if len(tok) > 3:
                b = gr(tok[3])
                if b is None and tok[3].startswith("#"):
                    b = int(tok[3].lstrip("#"), 0)
            if isinstance(a, int) and isinstance(b, int):
                if mn == "add":
                    v = a + b
                elif mn == "sub":
                    v = a - b
                elif mn == "lsl":
                    v = a << b
                elif mn == "lsr":
                    v = a >> b
                elif mn == "and":
                    v = a & b
                else:
                    v = a // b if b else 0
                sr(tok[1], v)
            continue
        if mn == "bl":
            nm = comment
            if "Utf8Encoder::convert" in nm:
                regs[0] = Bytes(str(gr("x2")).encode())
                trace.append(("utf8", len(regs[0])))
            elif "::base64Decode" in nm:
                s = str(gr("x1"))
                regs[0] = Bytes(base64.b64decode(s + "=" * (-len(s) % 4)))
                trace.append(("b64", len(regs[0])))
            elif "sublist" in nm:
                src = gr("x1")
                if isinstance(src, Stub):
                    src = src.content()
                if isinstance(src, Obj) and hasattr(src, "bytes"):
                    src = list(src.bytes)
                st = gr("x2") or 0
                en = stack.pop() if stack else None
                try:
                    regs[0] = Bytes(list(src)[st:en]) if isinstance(src, list) else None
                except Exception:
                    regs[0] = None
                trace.append(("sublist", st, en, len(regs[0]) if regs[0] is not None else None,
                              len(src) if isinstance(src, list) else type(src).__name__))
            elif "addAll" in nm:
                dst, add = gr("x1"), gr("x2")
                if isinstance(add, Obj) and hasattr(add, "bytes"):
                    add = list(add.bytes)
                if isinstance(dst, list) and isinstance(add, list):
                    dst.extend(list(add))
                trace.append(("addAll", len(dst) if isinstance(dst, list) else None))
            elif "_ofEfficientLengthIterable" in nm:
                src = gr("x2")
                if isinstance(src, Stub):
                    src = src.content()
                if isinstance(src, Obj) and hasattr(src, "bytes"):
                    src = list(src.bytes)
                regs[0] = Grow(list(src or []))
                trace.append(("grow", len(regs[0])))
            elif "Hash::convert" in nm:
                alg = gr("x1")
                data = gr("x2") or []
                if isinstance(data, Stub):
                    data = data.content()
                if isinstance(data, Obj) and hasattr(data, "bytes"):
                    data = list(data.bytes)
                an = getattr(alg, "name", "sha256")
                hf = {"sha256": hashlib.sha256, "sha384": hashlib.sha384,
                      "sha512": hashlib.sha512, "md5": hashlib.md5,
                      "sha1": hashlib.sha1}.get(str(an), hashlib.sha256)
                regs[0] = Obj("Digest", bytes=Bytes(hf(bytes(list(data))).digest()))
                trace.append(("hash", an, len(regs[0].bytes)))
            elif "fromList" in nm and "Uint8List" in nm:
                src = gr("x2")
                print("    [dbg fromList] x1=%r x2=%r" % (type(gr("x1")).__name__, type(src).__name__))
                if isinstance(src, Obj) and hasattr(src, "bytes"):
                    src = list(src.bytes)
                if not isinstance(src, list):
                    src = gr("x1")
                    if isinstance(src, Obj):
                        src = list(getattr(src, "bytes", []))
                regs[0] = Bytes(list(src or []))
                trace.append(("fromList", len(regs[0])))
            elif "AllocateUint8Array" in nm:
                regs[0] = Stub()
            elif "_slowSetRange" in nm:
                dst = regs.get(0)
                src = gr("x5") or slots.get(-0x18)
                if isinstance(dst, Stub) and isinstance(src, list):
                    dst.data = Bytes(list(src))
                    regs[0] = dst.data
                    trace.append(("slowset", len(dst.data)))
            elif "AllocateKeyStub" in nm:
                regs[0] = Obj("Key")
            elif "AllocateIVStub" in nm:
                regs[0] = Obj("IV")
            elif "AllocateEncryptedStub" in nm:
                regs[0] = Obj("Encrypted")
            continue
        # 其余（分支/栈帧/ret）忽略

    print("\n[slots]")
    for k in sorted(slots, reverse=True):
        v = slots[k]
        if isinstance(v, list) and v:
            print("  [fp-0x%02X] len=%-6d %s" % (-k, len(v), bytes(list(v))[:28].hex()))
        elif isinstance(v, Obj):
            print("  [fp-0x%02X] %s %s" % (-k, v.kind,
                                            getattr(v, "bytes", b"")[:28].hex() if hasattr(v, "bytes") else ""))
    print("\n[trace]")
    for t in trace:
        print("  ", t)


if __name__ == "__main__":
    j = fetch()
    print("[envelope] code=%s" % j.get("code"))
    run(j["data"])
