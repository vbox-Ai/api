import io, re, sys
p = r"C:\Users\Administrator\Downloads\DPK\_apk\libdir\libapp.so"
data = open(p, "rb").read()
print("size", len(data))
for needle in (b"ea6:LDcmS", b"Vq234zBeSdGg", b"-p9B[~PnPs", b"encode_sign", b"list_row"):
    idxs = [m.start() for m in re.finditer(re.escape(needle), data)]
    print("\n--", needle, "hits", len(idxs), idxs[:6])
    for i in idxs[:3]:
        s = max(0, i - 40); e = min(len(data), i + 90)
        print("  off", i, repr(data[s:e]))
