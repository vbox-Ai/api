# -*- coding: utf-8 -*-
"""hxsp 请求客户端 —— 用 curl 子进程发请求，规避 Python OpenSSL 与该 CDN 的 TLS 握手不兼容。

背景：Python urllib 对 hxapi.ruueyek.com（CNAME → .gccdn.net，14.0.47.29 / 138.113.152.120）
      报 `SSL: UNEXPECTED_EOF_WHILE_READING`；curl(schannel) 正常。
      服务端已确认进入业务层：空 body 返回 {"code":1,"message":"参数缺失"}。
"""
import json
import os
import subprocess
import sys
import tempfile

sys.stdout.reconfigure(encoding="utf-8")

CURL = r"C:\Windows\System32\curl.exe"
PROXY = "http://127.0.0.1:7890"


def post(url, payload, headers=None, timeout=30, use_proxy=True):
    """用 curl 发 POST，返回 (status, body_text)。"""
    fd, path = tempfile.mkstemp(suffix=".json")
    os.close(fd)
    try:
        with open(path, "w", encoding="utf-8") as f:
            json.dump(payload, f, ensure_ascii=False)

        cmd = [CURL, "-s", "-S", "--max-time", str(timeout),
               "-X", "POST", url,
               "-H", "Content-Type: application/json",
               "-H", "Accept: application/json",
               "-H", "User-Agent: okhttp/4.9.0",
               "--data-binary", "@" + path,
               "-w", "\n__STATUS__%{http_code}"]
        for k, v in (headers or {}).items():
            cmd += ["-H", "%s: %s" % (k, v)]
        if use_proxy:
            cmd += ["--proxy", PROXY]

        p = subprocess.run(cmd, capture_output=True, timeout=timeout + 10)
        out = p.stdout.decode("utf-8", "replace")
        err = p.stderr.decode("utf-8", "replace").strip()
        if "__STATUS__" in out:
            body, _, status = out.rpartition("__STATUS__")
            return status.strip(), body.strip()
        return "ERR", (err or out)[:400]
    finally:
        try:
            os.unlink(path)
        except OSError:
            pass


def get(url, headers=None, timeout=30, use_proxy=True):
    cmd = [CURL, "-s", "-S", "--max-time", str(timeout), url,
           "-w", "\n__STATUS__%{http_code}"]
    for k, v in (headers or {}).items():
        cmd += ["-H", "%s: %s" % (k, v)]
    if use_proxy:
        cmd += ["--proxy", PROXY]
    try:
        p = subprocess.run(cmd, capture_output=True, timeout=timeout + 10)
        out = p.stdout.decode("utf-8", "replace")
        if "__STATUS__" in out:
            body, _, status = out.rpartition("__STATUS__")
            return status.strip(), body.strip()
        return "ERR", p.stderr.decode("utf-8", "replace")[:400]
    except Exception as e:
        return "ERR", str(e)[:300]


if __name__ == "__main__":
    print("GET  / ->", get("https://hxapi.ruueyek.com/"))
    print("POST /appApi/getPubConfig ->", post("https://hxapi.ruueyek.com/appApi/getPubConfig", {}))
