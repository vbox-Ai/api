# -*- coding: utf-8 -*-
"""注册 kpsp_py 平台（双写 welfare_platforms.json + all_sources.json）"""
import json
import os
import shutil

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
WP = os.path.join(ROOT, "sources", "welfare_platforms.json")
AS = os.path.join(ROOT, "sources", "all_sources.json")

ENTRY = {
    "platformKey": "kpsp_py",
    "name": "看片视频",
    "category": "video",
    "icon": "play.rectangle.fill",
    "desc": "Python蜘蛛版 — 响应 Fernet 结构 AES 解密，m3u8 直链",
    "serviceType": "python_spider",
    "defaultHosts": ["https://sm-api.wieuc.com"],
    "sortOrder": 641,
    "defaultProxy": False,
    "notes": (
        "看片视频（kpsp）。响应为 {\"x-data\":\"<密文>\"}，密文是 Fernet 结构："
        "base64url → version(1B)+timestamp(8B)+IV(16B)+ciphertext+HMAC(32B)，"
        "客户端跳过 HMAC 校验，直接 hex[18:50] 取 IV、hex[50:len-64] 取密文，"
        "AES-128-CBC 解密（key=7af630c7e06ccecfa70d5a085f189c06）。"
        "接口：列表 api/vod/video（page/per_page≤100/site_id/tag）、详情 api/vod/video/{id}、"
        "标签 api/vod/tag（全站 6628 个）、搜索 search/vod（search）。"
        "媒体域名 hm-img.hdstfb.com：封面直接可取（.image 实为普通图片），"
        "播放 play_url 为 HLS m3u8 + AES-128，enc.key 同目录匿名可取（16 字节），"
        "另有 down_url 提供 mp4。"
        "坑：tag 过滤必须传 tag id，传中文名会被忽略并返回全站基线数据。"
    ),
    "api": "./sources/welfare-js/kpsp.py",
    "scriptType": "python",
    "engine": "python",
    "sslBypass": True,
    "contentType": "video",
    "visibleInNormalSpider": False,
    "visibleInGlobalSearch": False,
    "visibleInHome": False,
}


def load(p):
    with open(p, encoding="utf-8") as f:
        return json.load(f)


def dump(p, obj):
    with open(p, "w", encoding="utf-8", newline="\n") as f:
        json.dump(obj, f, ensure_ascii=False, indent=2)
        f.write("\n")


for p in (WP, AS):
    shutil.copy2(p, p + ".bak_kpsp")

d = load(WP)
plats = d["platforms"]
if any(x.get("platformKey") == "kpsp_py" for x in plats):
    plats[:] = [ENTRY if x.get("platformKey") == "kpsp_py" else x for x in plats]
    print("welfare_platforms: 更新")
else:
    plats.append(ENTRY)
    print("welfare_platforms: 追加，共 %d" % len(plats))
dump(WP, d)

d2 = load(AS)
wl = (d2.get("welfarePlatforms") or {}).get("platforms")
if isinstance(wl, list):
    if any(x.get("platformKey") == "kpsp_py" for x in wl):
        wl[:] = [ENTRY if x.get("platformKey") == "kpsp_py" else x for x in wl]
        print("all_sources: 更新")
    else:
        wl.append(ENTRY)
        print("all_sources: 追加，共 %d" % len(wl))
    dump(AS, d2)
else:
    print("all_sources: 结构异常，跳过")

for p in (WP + ".bak_kpsp", AS + ".bak_kpsp"):
    try:
        os.remove(p)
    except Exception:
        pass
print("完成")
