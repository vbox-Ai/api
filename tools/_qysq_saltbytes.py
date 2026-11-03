import re
data = open(r"C:\Users\Administrator\Downloads\DPK\_apk\libdir\libapp.so","rb").read()
for needle in (b"vEukA&w15z4", b"gH3nA7fR9tV1jY6z", b"asGjCrypto"):
    idxs = [m.start() for m in re.finditer(re.escape(needle), data)]
    print("\n--", needle, len(idxs), idxs[:4])
    for i in idxs[:2]:
        s=max(0,i-60); e=min(len(data), i+80)
        print("  off", i, repr(data[s:e]))
