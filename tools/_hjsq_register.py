# -*- coding: utf-8 -*-
"""注册 hjsq_py 平台到 welfare_platforms.json 并同步 all_sources.json"""
import json
import os
import shutil

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
WP = os.path.join(ROOT, "sources", "welfare_platforms.json")
AS = os.path.join(ROOT, "sources", "all_sources.json")

ENTRY = {
    "platformKey": "hjsq_py",
    "name": "海角社区",
    "category": "video",
    "icon": "flame.fill",
    "desc": "Python蜘蛛版 — 直连 REST，游客 token 可读全站",
    "serviceType": "python_spider",
    "defaultHosts": ["http://23.225.145.74"],
    "sortOrder": 640,
    "defaultProxy": False,
    "notes": (
        "海角社区（hjsq/haijiao）。协议由 libapp.so 反汇编还原："
        "鉴权头 X-User-Id=171299991201（静态硬编码）+ X-User-Token（游客 token）；"
        "信封 errorCode/message/data。"
        "分类来自 api2/topic/nodes（137 节点扁平表，按 parentId 组树）+ 5 个固定栏目"
        "（热帖/新闻/最新/精华/原创）。"
        "列表 api2/topic/node/topics（page/nodeId/type）、热帖 hot/topics、新闻 node/news、"
        "详情 api2/topic/{id}、搜索 api2/topic/search（keyword）。"
        "视频直链明文在详情 attachments[category=video].remoteUrl（HLS m3u8 + AES-128，"
        "key 同目录可取，实测 24 分片全通）；"
        "图片 *.jpg.txt 为自定义字母表 base64 包裹的 data URI，需解码后才是 JPEG，"
        "由 localProxy 实时解码输出。"
        "api2/video/node_list 需真实登录态，游客 token 不可用。"
    ),
    "api": "./sources/welfare-js/hjsq.py",
    "scriptType": "python",
    "engine": "python",
    "sslBypass": True,
    "contentType": "video",
    "visibleInNormalSpider": False,
    "visibleInGlobalSearch": False,
    "visibleInHome": False,
}

for p in (WP, AS):
    shutil.copy2(p, p + ".bak_hjsq")


def load(p):
    with open(p, encoding="utf-8") as f:
        return json.load(f)


def dump(p, obj):
    with open(p, "w", encoding="utf-8", newline="\n") as f:
        json.dump(obj, f, ensure_ascii=False, indent=2)
        f.write("\n")


# welfare_platforms.json
d = load(WP)
plats = d["platforms"]
keys = {x.get("platformKey") for x in plats}
if "hjsq_py" in keys:
    print("welfare_platforms: 已存在，更新")
    plats[:] = [ENTRY if x.get("platformKey") == "hjsq_py" else x for x in plats]
else:
    plats.append(ENTRY)
    print("welfare_platforms: 追加，共 %d" % len(plats))
dump(WP, d)

# all_sources.json（结构：welfarePlatforms.platforms 数组）
d2 = load(AS)
wl = ((d2.get("welfarePlatforms") or {}).get("platforms"))
if isinstance(wl, list):
    k2 = {x.get("platformKey") for x in wl}
    if "hjsq_py" in k2:
        wl[:] = [ENTRY if x.get("platformKey") == "hjsq_py" else x for x in wl]
        print("all_sources: 已存在，更新")
    else:
        wl.append(ENTRY)
        print("all_sources: 追加，共 %d" % len(wl))
    dump(AS, d2)
else:
    print("all_sources: 结构异常，跳过")
