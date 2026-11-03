p = "tools/_qysq_r12_sim.py"
s = open(p, encoding="utf-8").read()

# 1) Stub 默认回落到原始明文缓冲（AllocateUint8Array(len)+memcpy(D) == D）
s = s.replace('''class Stub:
    def __init__(self):
        self.data = None''', '''D_BYTES = None


class Stub:
    def __init__(self):
        self.data = None

    def content(self):
        return list(self.data if self.data is not None else (D_BYTES or []))''')

# 2) 各处把 Stub 变成可迭代
s = s.replace('''            elif "Hash::convert" in nm:
                alg = gr("x1")
                data = gr("x2") or []''', '''            elif "Hash::convert" in nm:
                alg = gr("x1")
                data = gr("x2") or []
                if isinstance(data, Stub):
                    data = data.content()''')
s = s.replace('''            elif "_ofEfficientLengthIterable" in nm:
                src = gr("x2")''', '''            elif "_ofEfficientLengthIterable" in nm:
                src = gr("x2")
                if isinstance(src, Stub):
                    src = src.content()''')
s = s.replace('''                src = gr("x1")
                if isinstance(src, Stub) and src.data is not None:
                    src = list(src.data)''', '''                src = gr("x1")
                if isinstance(src, Stub):
                    src = src.content()''')
s = s.replace('''                src = gr("x1")
                if isinstance(src, Stub) and src.data is not None:
                    src = src.content()''', '''                src = gr("x1")
                if isinstance(src, Stub):
                    src = src.content()''')

# 3) run() 里设置 D_BYTES
s = s.replace('''def run(sample_b64):
    insns = load_insns(ASM, START, END)''', '''def run(sample_b64):
    global D_BYTES
    D_BYTES = list(base64.b64decode(sample_b64 + "=" * (-len(sample_b64) % 4)))
    insns = load_insns(ASM, START, END)''')
open(p, "w", encoding="utf-8", newline="\n").write(s)
print("patched2")
