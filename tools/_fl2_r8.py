import importlib.util, json, uuid
src=open("tools/_fl2_r7.py",encoding="utf-8").read().split('if __name__')[0]
ns={}; exec(compile(src,"f7","exec"),ns)
call, register, dec = ns["call"], ns["register"], ns["dec"]
dev=str(uuid.uuid4()); tok=register(dev)
vid="524937"
cands=[("v1/videos/%s"%vid,{}),("v2/videos/%s"%vid,{}),("v1/video/info/%s"%vid,{}),
       ("v1/video/%s/detail"%vid,{}),("v2/vertical/%s/detail"%vid,{}),
       ("v1/video/detail",{"video_id":vid}),("v1/videos",{"video_id":vid}),
       ("v2/videos",{"video_id":vid})]
for p,params in cands:
    for m in ("GET","POST"):
        st,h,raw=call(p,m,params,tok,dev); txt=dec(raw,h.get("X-VTag",""))
        code=None; keys=""
        try:
            j=json.loads(txt); code=(j.get("status") or {}).get("code")
            rs=j.get("response"); keys=",".join(list(rs.keys())[:8]) if isinstance(rs,dict) else type(rs).__name__
        except Exception: pass
        print("%-26s %-4s %-4s code=%-5s %s" % (p,m,st,code, (keys or txt[:60]).replace("\n"," ")))
        if code==200:
            open("tools/_dec/fl2_detail_%s.json"%p.replace("/","_"),"w",encoding="utf-8").write(txt)
