# -*- coding: utf-8 -*-
"""注册 mmmh（漫画类）"""
import io
import os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
P = os.path.join(ROOT, "tools", "_register_platforms.py")
s = io.open(P, encoding="utf-8").read()

ENTRY = '''    "mmmh": ("迷妹漫画", "books.vertical.fill", 661,
             "三层结构：① host_pwa.txt 配置 AES-256-CBC 解密（key/iv 为 mmmh_main 里的 base64 常量，"
             "明文=32位校验+JSON+32位校验）拿到真实 API host；② Authorization: Bearer <token_mmmh>"
             "（Django 三段式，32位hex 会 498）；③ 响应用 key=ae52f7ffd2dd66ba5743bb180188b991 + "
             "MD5(X-Response-Length)[8:24] 的动态 IV 做 AES-256-CBC 解密。"
             "接口 /v1/animat/category(.list?category_id&type=1&page)、/v1/fiction/category。"
             "⚠ media 的 m3u8 直取返回 500（分类/列表正常，media 端点另有校验）；"
             "⚠ 封面 encrypt=true 需 MmMhAnimImg+chain 解密，暂未破。", "comic"),
'''

anchor = "    # ---------------- 漫画类（category=comic）----------------\n"
assert anchor in s, "找不到漫画类锚点"
if '"mmmh"' not in s:
    s = s.replace(anchor, anchor + ENTRY, 1)
    io.open(P, "w", encoding="utf-8", newline="\n").write(s)
    print("已追加 mmmh META")
else:
    print("mmmh 已存在")
