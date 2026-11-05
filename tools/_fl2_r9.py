import importlib.util, json, uuid, urllib.request
src=open("tools/_fl2_r7.py",encoding="utf-8").read().split('if __name__')[0]
ns={}; exec(compile(src,"f7","exec"),ns)
call, register, dec = ns["call"], ns["register"], ns["dec"]
HOST=ns["HOST"]
dev=str(uuid.uuid4()); tok=register(dev)
# 1) m3u8 直取
u = HOST + "/media/480/524937.m3u8?expire=1793893925&hash=1b700846a1f80ffa90c23f6973cb33aa"
op=urllib.request.build_opener(urllib.request.ProxyHandler({}))
try:
    with op.open(urllib.request.Request(u, headers={"User-Agent":"Fulao2/Android 2.40; Xiaomi MI 14"})) as r:
        b=r.read(300); print("[m3u8]", r.status, len(b), b[:120])
except Exception as e:
    print("[m3u8] err", e)
# 2) 搜索候选
for p,params in (("v1/search/SSIS",{"page":1}),("v2/search",{"keyword":"SSIS","page":1}),
                 ("v1/search",{"keyword":"SSIS"}),("v2/search/SSIS",{"page":1}),
                 ("v1/videos/search",{"keyword":"SSIS"})):
    st,h,raw=call(p,"GET",params,tok,dev); txt=dec(raw,h.get("X-VTag",""))
    code=None; keys=""
    try:
        j=json.loads(txt); code=(j.get("status") or {}).get("code")
        rs=j.get("response"); keys=",".join(list(rs.keys())[:6]) if isinstance(rs,dict) else type(rs).__name__
    except Exception: pass
    print("%-22s GET %-4s code=%-5s %s" % (p,st,code,(keys or txt[:70]).replace("\n"," ")))
