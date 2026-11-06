# -*- coding: utf-8 -*-
"""抓包分析：one 平台签名（sign 头）离线还原尝试

样本来自 `归档/2026-10-29-052251/22`：
    POST https://api.3459381.com/v2.5/article/day
    headers: uuid / timestamp=1793222604 / platform=3 / token=<JWT> / sign=1bcff1382475e132e9b31eab76a022
    body:    "T2xWlkG7Owbiw1smMECUyMEMOCJ7v67mpB3DyuYx0nA="（44B base64，AES 密文）

目标：找出 sign 的算法（是否 md5、参与字段与顺序、是否带 secret）。
做法：把能想到的字段组合都拼一遍，比对 1bcff1382475e132e9b31eab76a022。
"""
import base64
import hashlib
import itertools
import json

SIGN = "1bcff1382475e132e9b31eab76a022"
PATH = "/v2.5/article/day"
TS = "1793222604"
PLATFORM = "3"
UUID = "9b1a29f0-cf81-11f1-92c4-114a8eafec4b"
BODY = "T2xWlkG7Owbiw1smMECUyMEMOCJ7v67mpB3DyuYx0nA="
TOKEN = ("eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9.eyJpc3MiOjUwODE5NTY0LCJpc192aXNpdG9yIjoxLCJ1dWlkIjoi"
         "OWIxYTI5ZjAtY2Y4MS0xMWYxLTkyYzQtMTE0YThlYWZlYzRiIiwibmlja25hbWUiOiJcdTUxYWNcdTZjZjNcd"
         "TYwMmFcdTllM2Q1MTU0MjcxIiwiaXAiOiI1Ni43MC4yLjI0NiIsImlhdCI6MTc5Mjg2ODkxMCwiZXhwIjoxNzkz"
         "NDc3MzEwLCJuYmYiOjE3OTI4Njg5MTAsInN1YiI6ImFwaS40M2I4NDc3LmNvbSIsImp0aSI6IjZkNTU1N2QyYT"
         "MyNzFhZDU4ZmMyZTUxN2MyODk5M2UwIn0.FY51Jq0ZXozjkDCOAPi2O1FW-IluL4TxSlLwtZguKPI")

FIELDS = {
    "path": PATH,
    "p": PATH.lstrip("/"),
    "ts": TS,
    "platform": PLATFORM,
    "uuid": UUID,
    "body": BODY,
    "token": TOKEN,
    "appId": "1",
    "ver": "2.5",
}
CAND_SECRETS = [
    "", "-", "&", "|", ".", ":", "_",
    "3459381", "api.3459381.com", "one", "avbox", "tvbox",
]

hits = []


def try_join(sep, keys, secret="", secret_pos="tail", prefix=""):
    vals = [FIELDS[k] for k in keys]
    s = sep.join(vals)
    if secret:
        s = (secret + s) if secret_pos == "head" else (s + secret)
    s = prefix + s
    for algo in ("md5", "sha1", "sha256"):
        h = hashlib.new(algo, s.encode()).hexdigest()
        if SIGN in h:
            hits.append((algo, sep, keys, secret, secret_pos, prefix, s[:80]))


# 1) 全排列长度 2..4 的字段子集（不含 secret）
keys_all = list(FIELDS)
for n in (2, 3, 4):
    for keys in itertools.permutations(keys_all, n):
        for sep in ("&", "|", "", "-", "_"):
            try_join(sep, keys)

# 2) 带 secret 的两三种常见位置
for keys in (("path", "ts"), ("path", "ts", "body"), ("ts", "path"), ("path", "body", "ts"),
             ("path", "ts", "uuid"), ("path", "ts", "platform")):
    for sec in CAND_SECRETS:
        for pos in ("tail", "head"):
            try_join("&", keys, sec, pos)
            try_join("|", keys, sec, pos)
            try_join("", keys, sec, pos)

print("命中：", len(hits))
for h in hits[:10]:
    print(h)

# 额外：直接 md5(body) / md5(path+body) 之类的手工组合
manual = {
    "md5(body)": BODY, "md5(path+body)": PATH + BODY, "md5(body+path)": BODY + PATH,
    "md5(ts+body)": TS + BODY, "md5(body+ts)": BODY + TS,
    "md5(path+ts+body)": PATH + TS + BODY,
    "md5(path+ts+body+token)": PATH + TS + BODY + TOKEN,
    "md5(token+path+ts)": TOKEN + PATH + TS,
}
for name, s in manual.items():
    if hashlib.md5(s.encode()).hexdigest() == SIGN:
        print("★ 人工命中:", name)
print("done")
