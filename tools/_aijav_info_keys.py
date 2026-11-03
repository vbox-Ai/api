import json
j = json.load(open("tools/_dec/aijav_info.json", encoding="utf-8"))
d = j["data"]
print("keys:", sorted(d.keys()))
for k, v in d.items():
    s = json.dumps(v, ensure_ascii=False)
    if any(t in k.lower() for t in ("url", "play", "video", "hls", "m3u8", "src", "path", "file")):
        print("\n%s = %s" % (k, s[:400]))
print("\n--- 所有含 http 的字符串值 ---")
def walk(o, p=""):
    if isinstance(o, dict):
        for k, v in o.items():
            walk(v, p + "." + k)
    elif isinstance(o, list):
        for i, v in enumerate(o[:3]):
            walk(v, p + "[%d]" % i)
    elif isinstance(o, str) and ("http" in o or ".m3u8" in o or ".mp4" in o):
        print(p, "=", o[:160])
walk(d)
