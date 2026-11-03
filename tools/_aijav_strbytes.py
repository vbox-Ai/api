import re
p = r"C:\Users\Administrator\Downloads\DPK\_apk\libdir\libapp.so"
data = open(p, "rb").read()
for needle in (b"NRkw0g3i", b"0XxdjmI55", b"RWf23muavY", b"NWSdef"):
    idxs = [m.start() for m in re.finditer(re.escape(needle), data)]
    print("\n--", needle, "hits", len(idxs), idxs[:6])
    for i in idxs[:3]:
        s = max(0, i-45); e = min(len(data), i+70)
        print("  off", i, repr(data[s:e]))
