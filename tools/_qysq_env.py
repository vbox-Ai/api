import json, base64, hashlib, hmac, time, uuid, urllib.request
BASE="https://d1kmvkv4iwtiup.cloudfront.net"
SECRET="gH3nA7fR9tV1jY6z"
DEV_UA="DevType=Apple iPhone mobile;SysType=light;Ver=2.1.2;BuildID=Mobile Safari 18.5"
BR_UA="Mozilla/5.0 (iPhone; CPU iPhone OS 18_5 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/18.5 Mobile/15E148 Safari/604.1"
TOKEN="eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJhdWQiOiJwdWJsaWMiLCJleHAiOjE3OTM4NTgxNjIsImlzc3VlciI6ImNvbS5idXR0ZXJmbHkiLCJzdWIiOiJhc2lnbiIsInVzZXJJZCI6NTY3NzU4MX0.yjzuUUUK1hlQBzlTQ703ZYemCvfL97EYsQNUCyEVET4"
OP=urllib.request.build_opener(urllib.request.ProxyHandler({}))
def call(path, method="POST", body=b"{}"):
    ts=int(time.time()); nonce=str(uuid.uuid4())
    msg="%s&/%s&%s&%s&%s"%(TOKEN,path,DEV_UA,ts,nonce)
    sign=hmac.new(SECRET.encode(), msg.encode(), hashlib.sha1).hexdigest()
    h={"X-User-Agent":DEV_UA,"user-agent":BR_UA,"authorization":"Bearer "+TOKEN,
       "x-api-key":"timestamp=%s;sign=%s;nonce=%s"%(ts,sign,nonce),"Content-Type":"application/json"}
    req=urllib.request.Request(BASE+"/"+path, data=None if method=="GET" else body, method=method, headers=h)
    with OP.open(req, timeout=20) as r:
        return json.loads(r.read().decode("utf-8","replace"))
for p,m in (("api/app/media/home","POST"),("api/app/ping/config","GET"),("api/app/media/short/hot","POST")):
    try:
        j=call(p,m)
    except Exception as e:
        print(p,"ERR",str(e)[:60]); continue
    d=j.get("data")
    print("\n==",p,"code=",j.get("code"),"msg=",j.get("msg"),"tip=",j.get("tip"),"hash=",j.get("hash"))
    if isinstance(d,str):
        print("   data len=%d head=%s"%(len(d), d[:60]))
    else:
        print("   data 非密文:", json.dumps(d, ensure_ascii=False)[:200])
