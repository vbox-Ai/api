# -*- coding: utf-8 -*-
"""mmmh 适配器：改用 mmMhAnim 模板生成 m3u8（播放已实测 200）"""
import io
import os
import re

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
P = os.path.join(ROOT, "sources", "welfare-js", "mmmh.py")
s = io.open(P, encoding="utf-8").read()

# 1) ensure_config 里补存 stream chain
old_cfg = '''        comic = cfg.get("comic") or []
        self.comic_chain = (comic[0].get("chain") if comic else "") or ""'''
new_cfg = '''        comic = cfg.get("comic") or []
        self.comic_chain = (comic[0].get("chain") if comic else "") or ""
        stream = cfg.get("stream") or []
        self.stream_chain = (stream[0].get("chain") if stream else "") or ""
        self.stream_ts = (stream[0].get("tsurl") if stream else "") or ""'''
assert old_cfg in s
s = s.replace(old_cfg, new_cfg)

# 2) __init__ 补字段
s = s.replace("        self.comic_chain = \"\"\n",
              "        self.comic_chain = \"\"\n        self.stream_chain = \"\"\n        self.stream_ts = \"\"\n")

# 3) detail 里的播放 URL 改成 mmMhAnim 模板
old_play = '''        base = self.ensure_config()
        media = it.get("media") or {}
        plays = []
        for label, q in (("正片 720", "720"), ("标清 240", "240"), ("预览", "intro")):
            rel = media.get(q)
            if rel:
                url = rel if rel.startswith("http") else base + rel
                plays.append("%s$%s" % (label, url))'''
new_play = '''        base = self.ensure_config()
        avkey = it.get("avkey") or ""
        plays = []
        # 按 UrlUtil::mmMhAnim 的模板拼（缺 host/chain/encrypt/token 会 500）
        if avkey:
            for label, q in (("正片 720", "720"), ("标清 240", "240"),
                             ("预览", "intro")):
                url = ("%s/v1/animat/pwa/media/%s/%s.m3u8"
                       "?host=%s&chain=%s&encrypt=true&token=%s"
                       % (base, q, avkey, self.token,
                          self.stream_chain, self.token))
                plays.append("%s$%s" % (label, url))'''
assert old_play in s
s = s.replace(old_play, new_play)

# 4) playerContent 的 header 保留 token（m3u8 已自带，但分片/密钥请求可能需要）
io.open(P, "w", encoding="utf-8", newline="\n").write(s)
try:
    compile(s, P, "exec")
    print("mmmh.py 已更新播放模板  OK")
except SyntaxError as e:
    print("语法错 line %s: %s" % (e.lineno, e.msg))
