p = "tools/_qysq_r12_sim.py"
s = open(p, encoding="utf-8").read()
s = s.replace('src = src.bytes if offi == 7 else len(getattr(src, "bytes", []) or [])',
              'src = (getattr(src, "bytes", None) if offi == 7 else len(getattr(src, "bytes", []) or []))')
open(p, "w", encoding="utf-8", newline="\n").write(s)
print("ok")
