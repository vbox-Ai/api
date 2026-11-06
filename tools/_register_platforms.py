# -*- coding: utf-8 -*-
"""通用平台注册器：把独立平铺的平台双写进 welfare_platforms.json + all_sources.json

用法：python tools/_register_platforms.py [key1 key2 ...]
    不带参数则注册 META 里全部已就绪平台。
只注册脚本文件确实存在且能通过语法编译的平台。
"""
import json
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = os.path.join(ROOT, "sources")
WJ = os.path.join(SRC, "welfare-js")
WP = os.path.join(SRC, "welfare_platforms.json")
AS = os.path.join(SRC, "all_sources.json")

# key -> (中文名, 图标, sortOrder, 备注)
META = {
    "hdb": ("黄豆瓣", "film.stack.fill", 650,
            "RSA-2048 + AES-128-CBC 双向信封。分类/列表/详情/播放全通（播放为 getM3u8 签名直链）。"),
    "mmav": ("猫咪AV", "cat.fill", 651,
             "AES-256-CBC 动态 IV（固定串 + 响应 suffix）+ wsSecret 播放签名。分类/列表/详情/播放全通。"),
    "rryy": ("2048", "square.stack.3d.up.fill", 652,
             "纯 HTML + 门禁 cookie 解析。分类/列表/详情可出，播放需 VIP。"),
    "one": ("one", "1.circle.fill", 653,
            "AES-128-CBC + MD5 签名。分类可出；列表依赖内置 token，token 过期则列表为空（需外部喂 one_token）。"),
    "lclf": ("绿茶楼凤", "building.2.fill", 654,
             "纯 REST，零鉴权。feed/top/detail 全 POST（detail 参数走 query string 的 postId）。"
             "图文型内容：多图直链可浏览，无视频流。支持 cid 地区过滤（type_id 用 city_<cid>）。"
             "播放按 vbox 漫画约定输出 manga:// + && 连接（客户端渲染图片阅读器）。", "comic"),
    "km": ("快猫", "cat.circle.fill", 655,
           "请求加密：data=base16(AES-128-CBC(json)) + sig=MD5('data='+data+'maomi_pass_xyz')，"
           "响应为 hex(AES)。接口 /api/videos/listAll 与 listHot（路径即方法名，打到 /api/videos/ 会 501）。"
           "列表项自带 mv_play_url mp4 直链，无需 detail（detail 需登录）。"
           "⚠ 实测视频源 IP 119.28.204.36 直连超时/代理 502，播放能否成功取决于客户端网络。"),
    "hsck": ("黄色仓库", "shippingbox.fill", 656,
             "纯 HTML（苹果CMS stui 模板），无加密无签名。站点对任何请求恒返 HTTP 418，"
             "但 body 是完整真实页面 —— 不能用 status==200 判断成功。页面 UTF-8 编码。"
             "分类是 query 风格 /?type={dm|gc|om|ycgc|...}&p={page}，搜索 /?search2={kw}。"
             "播放地址伪装在详情页 <img id=\"video_img\" src=\"...a.m3u8\"> 里。"),
    "live": ("直播盒子", "antenna.radiowaves.left.and.right", 657,
             "零鉴权零加密纯 JSON：/mf/json.txt 下发 130 个平台（pingtai），"
             "/mf/{address} 下发该平台 90+ 主播（zhubo，含 FLV 直播直链，wsSecret 已内嵌 URL）。"
             "平台=分类，主播=列表项，vod_id 用 base64url 包裹播放地址。"),
    "mdtv": ("麻豆TV", "film.fill", 658,
             "AES-256-CBC 双向信封（key=Vq234z…）：请求 biz 加毫秒 timestamp → 按 key 排序拼串 + "
             "MD5(secret) 得 encode_sign → base64(AES(json)) 装进 {\"post-data\"}；"
             "响应 {\"suffix\",\"data\"} 用 IV=\"-p9B[~PnPs\"+suffix 解密。"
             "**请求头必须带 suffix: JGDZMX**（否则服务端还原不了 IV → 恒 1002 参数错误）。"
             "接口 video/channel、video/tags、video/listcache（page/list_row/type/channel|tags）、"
             "video/list（搜索）。列表项自带 video_url = HLS m3u8 直链，客户端无 detail/play 接口。"),
    "aijav": ("AiJav", "film.fill", 659,
              "与 mdtv 同构的 AES-256 双向信封（同一套 encrypt 包胶水层），差异只在 4 个常量："
              "KEY=0XxdjmI55…(32B)、REQ_IV=RWf23muavYNWSdef、SECRET=&NRkw0g3i…、头 suffix=NWSdef；"
              "响应 IV=RWf23muavY+响应 suffix。**成功码是 1 不是 0**；"
              "「路由不存在」恒返 {\"code\":999}，可据此扫接口。"
              "接口 video/lists（首页 type=8&limit=54；分区 tag_id|actor_id|publisher_id；搜索 keyword）、"
              "video/info（参数名 **vid**）、tag/lists、actor/lists、publisher/lists。"
              "⚠ 播放受限：匿名态不下发 m3u8（video/purchase、video/collect 返 2000 登录失效），"
              "仅交付分类/列表/详情三能力。"),
    "javdb": ("JavDB", "magnifyingglass.circle.fill", 664,
              "签名极简：ts=秒；first=MD5(ts+SECRET)；头 jdsignature=\"{ts}.lpw6vgqzsp.{first}\"；"
              "头 accept-language=zh。SECRET 在 service.dart 构造 JavDbInterceptor 时写入（64+ 位十六进制串）。"
              "接口 api/v1/movies/latest、api/v1/movies/tags?filter_by=tag、api/v2/search?q=、api/v4/movies/{id}。"
              "参数缺失会返回 \"參數不能爲空: xxx\"，可据此枚举必填项。"
              "⚠ 正片需登录+VIP（play_sources 为空、show_vip_banner=true），"
              "仅交付 分类/列表/详情 + 官方 720p 试看 m3u8（preview_video_url）。"),
    # ---------------- 漫画类（category=comic）----------------
    "mmmh": ("迷妹漫画", "books.vertical.fill", 661,
             "三层结构：① host_pwa.txt 配置 AES-256-CBC 解密（key/iv 为 mmmh_main 里的 base64 常量，"
             "明文=32位校验+JSON+32位校验）拿到真实 API host；② Authorization: Bearer <token_mmmh>"
             "（Django 三段式，32位hex 会 498）；③ 响应用 key=ae52f7ffd2dd66ba5743bb180188b991 + "
             "MD5(X-Response-Length)[8:24] 的动态 IV 做 AES-256-CBC 解密。"
             "接口 /v1/animat/category(.list?category_id&type=1&page)、/v1/fiction/category。"
             "⚠ media 的 m3u8 直取返回 500（分类/列表正常，media 端点另有校验）；"
             "⚠ 封面 encrypt=true 需 MmMhAnimImg+chain 解密，暂未破。", "comic"),
    "hhlz": ("嘿嘿连载", "books.vertical.fill", 662,
             "抓包+asm 双证据：请求送一套固定设备参数（appId/debug/osType/product/ver/"
             "marketChannel/sysVer/proxyChannel/packageName/time/phoneModel/udid），"
             "其中 **sign 是硬编码常量 d01ef895544ab4f2a1f4d38d66edb283**（无需计算）。"
             "响应用 AES-128-CBC(key=D2o4XyQeIFobJ4tS, iv=sciCuBC7orQtDhTO) 解 data 字段。"
             "接口 /comic/list{cat,page_num}、/cartoon/info{comic_id}、/comic/catalog{comic_id}、"
             "/comic/chapter{comic_id,chapter_id}（缺 comic_id 返 702）。"
             "播放按漫画约定输出 manga:// + && 连接（客户端渲染图片阅读器）。"
             "host https://rrs0a03ak.pye57rf.com 来自抓包（此前被误判为站点已死）。", "comic"),
    "mw": ("漫蛙漫画", "books.vertical.fill", 660,
           "纯 HTML 明文，无加密无签名。列表 /booklist?page&tag&gender，详情 /book/{id} 取章节，"
           "阅读 /chapter/{id} 取正文图。vbox 漫画约定：播放返回 manga:// + 图片以 && 连接。"
           "坑：搜索页/详情页真封面在 data-original（src 是占位图），列表页真封面在 src。", "comic"),
}

SOFTWARE = {
    "platformKey": None,
    "name": None,
    "category": "video",
    "icon": "film.fill",
    "desc": None,
    "serviceType": "python_spider",
    "defaultHosts": [],
    "sortOrder": 700,
    "defaultProxy": False,
    "notes": None,
    "api": None,
    "scriptType": "python",
    "engine": "python",
    "sslBypass": True,
    "contentType": "video",
    "visibleInNormalSpider": False,
    "visibleInGlobalSearch": False,
    "visibleInHome": False,
}


def plat_hosts(key):
    """从 muse_avbox.py 的 PLATFORM_HOSTS 取该平台主域名。"""
    import re
    s = open(os.path.join(WJ, "muse_avbox.py"), encoding="utf-8").read()
    seg = s[s.index("PLATFORM_HOSTS = {"):]
    seg = seg[:seg.index("\n}") + 2]
    m = re.search(r'"%s":\s*"([^"]+)"' % re.escape(key), seg)
    return [m.group(1)] if m else []


def build_entry(key):
    meta = META[key]
    name, icon, sort, notes = meta[0], meta[1], meta[2], meta[3]
    ctype = meta[4] if len(meta) > 4 else "video"      # 第 5 项可指定 video/comic/live
    e = dict(SOFTWARE)
    e.update({
        "platformKey": "%s_py" % key,
        "name": name,
        "category": ctype,
        "contentType": ctype,
        "icon": icon,
        "desc": "Python蜘蛛版 — 自包含单文件（平铺）",
        "defaultHosts": plat_hosts(key),
        "sortOrder": sort,
        "notes": notes,
        "api": "./sources/welfare-js/%s.py" % key,
    })
    return e


def load(p):
    with open(p, encoding="utf-8") as f:
        return json.load(f)


def dump(p, o):
    with open(p, "w", encoding="utf-8", newline="\n") as f:
        json.dump(o, f, ensure_ascii=False, indent=2)
        f.write("\n")


def upsert(lst, entry):
    pk = entry["platformKey"]
    for i, x in enumerate(lst):
        if x.get("platformKey") == pk:
            lst[i] = entry
            return "update"
    lst.append(entry)
    return "append"


if __name__ == "__main__":
    keys = sys.argv[1:] or list(META.keys())
    ready, skipped = [], []
    for k in keys:
        if k not in META:
            skipped.append((k, "无 META"))
            continue
        p = os.path.join(WJ, k + ".py")
        if not os.path.exists(p):
            skipped.append((k, "脚本不存在"))
            continue
        try:
            compile(open(p, encoding="utf-8").read(), p, "exec")
        except SyntaxError as e:
            skipped.append((k, "语法错 line %s" % e.lineno))
            continue
        ready.append(k)

    if not ready:
        print("无就绪平台；跳过:", skipped)
        raise SystemExit(1)

    wp = load(WP)
    asrc = load(AS)
    asl = (asrc.get("welfarePlatforms") or {}).get("platforms")
    if not isinstance(asl, list):
        print("all_sources 结构异常")
        raise SystemExit(1)

    for k in ready:
        e = build_entry(k)
        r1 = upsert(wp["platforms"], e)
        r2 = upsert(asl, e)
        print("%-6s -> %-10s welfare=%s  all_sources=%s  hosts=%s" %
              (k, e["platformKey"], r1, r2, e["defaultHosts"]))

    dump(WP, wp)
    dump(AS, asrc)
    print("\n平台总数: welfare=%d  all_sources=%d" % (
        len(wp["platforms"]), len(asl)))
    if skipped:
        print("跳过:", skipped)
