import re
data = open(r"C:\Users\Administrator\Downloads\DPK\_apk\libdir\libapp.so","rb").read()
for needle in (b"video_id_", b"m3u8", b"/hls/"):
    idxs = [m.start() for m in re.finditer(re.escape(needle), data)]
    print("\n===", needle, "hits", len(idxs))
    for i in idxs[:14]:
        s = max(0,i-70); e=min(len(data), i+70)
        print(" ", i, repr(data[s:e]))
