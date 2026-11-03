import re, io
p = "tools/_qysq_r12_sim.py"
s = open(p, encoding="utf-8").read()
old = r'm = re.search(r"\[(fp|x\d+|SP|THR)(?:, #(-?0x[0-9a-f]+))?\]", code)'
new = r'm = re.search(r"\[(fp|x\d+|SP|THR)(?:, #(-?(?:0x[0-9a-f]+|\d+)))?\]", code)'
assert old in s
s = s.replace(old, new)
s = s.replace("offi = int(off, 16) if off else 0", "offi = int(off, 0) if off else 0")
open(p, "w", encoding="utf-8", newline="\n").write(s)
print("patched")
