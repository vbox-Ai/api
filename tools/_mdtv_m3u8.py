import urllib.request
u = "https://m3md.n6uem8.xyz/doudou/ms/fc50e00c43936ae2383644a57__1306860/hls/1/index.m3u8"
op = urllib.request.build_opener(urllib.request.ProxyHandler({}))
for ua in ("Dart/3.4 (dart:io)", "Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Mobile/15E148 Safari/604.1"):
    try:
        r = op.open(urllib.request.Request(u, headers={"User-Agent": ua}), timeout=15)
        b = r.read()
        print(ua[:20], r.status, len(b))
        print(b[:400].decode("utf-8", "replace"))
    except Exception as e:
        print(ua[:20], "ERR", e)
