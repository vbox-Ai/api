#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
国色天香 / 我草视频 - PyramidStore 插件 (修复版 v2)
目标: https://9njecqnvzcai.wckz803.vip:8801
特性:
  - 动态域名抓取(防域名更换)
  - 标题/分类名解密
  - 首页/分类/搜索/详情 API
  - 多播放源提取(m3u8直链)

修复内容 (2026-08-14):
  1. 更新主域名为 https://9njecqnvzcai.wckz803.vip:8801
  2. 修复 searchContent 返回格式 (TVBox标准 {"list": [...]})
  3. 修复 detailContent 中 vod_play_url 被重复覆盖的问题
  4. 修复 categoryContent 中 extend 过滤参数未使用的问题
  5. 修复 _get_json URL构建双问号隐患
  6. 修复 refresh_domains 失败后的空domain降级处理
  7. 修复 localProxy cover 返回的 Content-Type (webp)
  8. 增强 init 支持通过 extend 传入自定义域名
  9. 增加完善的错误处理和日志输出
  10. 修复 homeContent filters 在API失败时的保底逻辑
"""

import requests
import json
import html as html_module
import re
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed

# 兼容本地调试与 PyramidStore 环境
sys.path.append('../../')
try:
    from base.spider import Spider
except ImportError:
    class Spider:
        def init(self, extend=""):
            pass


# ========== 解密映射表 (来自 public.min.js) ==========
_DECRYPT_MAP = {
    'e':'P','w':'D','T':'y','+':'J','l':'!','t':'L','E':'E','@':'2','d':'a','b':'%',
    'q':'l','X':'v','~':'R','5':'r','&':'X','C':'j',']':'F','a':')','^':'m',',':'~',
    '}':'1','x':'C','c':'(','G':'@','h':'h','.':'*','L':'s','=':',','p':'g','I':'Q',
    '1':'7','_':'u','K':'6','F':'t','2':'n','8':'=','k':'G','Z':']',')':'b','P':'}',
    'B':'U','S':'k','6':'i','g':':','N':'N','i':'S','%':'+','-':'Y','?':'|','4':'z',
    '*':'-','3':'^','[':'{','(':'c','u':'B','y':'M','U':'Z','H':'[','z':'K','9':'H',
    '7':'f','R':'x','v':'&','!':';','M':'_','Q':'9','Y':'e','o':'4','r':'A','m':'.',
    'O':'o','V':'W','J':'p','f':'d',':':'q','{':'8','W':'I','j':'?','n':'5','s':'3',
    '|':'T','A':'V','D':'w',';':'O'
}

# 默认基础域名(当前有效域名 + 历史备用)
_BACKUP_BASE_URLS = [
    "https://9njecqnvzcai.wckz803.vip:8801",
    "https://cvx48e9nvzcai.wckk793.vip:8801",
    "https://www.wocao03.com",
]

# 域名缓存: (timestamp, siteUrl, css_domain, pic_domain, novel_domain, csstime, channel_id)
_DOMAIN_CACHE = (0, "", "", "", "", "", "")
_CACHE_TTL = 600  # 10 分钟缓存


def _try_fetch_domain(candidate: str, timeout: int):
    """尝试从单个域名抓取数据，返回 (success, data_dict)"""
    try:
        resp = requests.get(f"{candidate}/data.json", timeout=timeout)
        resp.raise_for_status()
        content = resp.text

        start = content.find("var Group=")
        if start == -1:
            start = content.find("var Group =")
        end = content.find("var Token=", start)
        if end == -1:
            end = content.find("var Token =", start)

        if start == -1 or end == -1:
            return False, None

        json_str = content[start:end].strip()
        json_str = re.sub(r"var\s+Group\s*=\s*", "", json_str).rstrip(";").strip()

        group = json.loads(json_str)
        return True, {
            "siteUrl": candidate,
            "css_domain": group.get("css_domain", ""),
            "pic_domain": group.get("pic_domain", ""),
            "novel_domain": group.get("novel_domain", ""),
            "csstime": str(group.get("csstime", "")),
            "channel_id": str(group.get("channel_id", "")),
        }
    except Exception:
        return False, None


def refresh_domains_concurrent(timeout: int = 8) -> bool:
    """并发抓取所有候选域名，取最快响应者，10分钟缓存"""
    global _DOMAIN_CACHE

    now = time.time()
    # 检查缓存是否有效
    if now - _DOMAIN_CACHE[0] < _CACHE_TTL and _DOMAIN_CACHE[1]:
        return True

    candidates = list(_BACKUP_BASE_URLS)
    # 去重
    seen = set()
    unique_candidates = []
    for c in candidates:
        if c not in seen:
            seen.add(c)
            unique_candidates.append(c)

    best_result = None
    with ThreadPoolExecutor(max_workers=len(unique_candidates)) as executor:
        futures = {
            executor.submit(_try_fetch_domain, c, timeout): c
            for c in unique_candidates
        }
        for future in as_completed(futures):
            candidate = futures[future]
            try:
                ok, data = future.result()
                if ok and data:
                    best_result = data
                    print(f"[INFO] 域名刷新成功(并发): {candidate} -> {data['siteUrl']}")
                    break  # 第一个成功的就是最快的
            except Exception:
                continue

    if best_result:
        _DOMAIN_CACHE = (
            now,
            best_result["siteUrl"],
            best_result["css_domain"],
            best_result["pic_domain"],
            best_result["novel_domain"],
            best_result["csstime"],
            best_result["channel_id"],
        )
        return True

    # 缓存过期但网络失败时，如果旧缓存还在，降级使用旧缓存
    if _DOMAIN_CACHE[1]:
        print("[WARN] 并发刷新失败，降级使用旧缓存域名")
        return True

    print("[ERROR] 所有域名均无法访问，且无旧缓存可用")
    return False


def get_cached_domain():
    """获取缓存的域名信息，返回 dict"""
    return {
        "siteUrl": _DOMAIN_CACHE[1],
        "css_domain": _DOMAIN_CACHE[2],
        "pic_domain": _DOMAIN_CACHE[3],
        "novel_domain": _DOMAIN_CACHE[4],
        "csstime": _DOMAIN_CACHE[5],
        "channel_id": _DOMAIN_CACHE[6],
    }


def decrypt_text(text: str) -> str:
    """解密网站加密文本(标题/分类名等)"""
    if not text or not isinstance(text, str):
        return ""
    result = "".join(_DECRYPT_MAP.get(ch, ch) for ch in text)
    return html_module.unescape(result)


class Spider(Spider):
    """PyramidStore 标准爬虫插件 (修复版)"""

    def __init__(self):
        self.siteUrl = _BACKUP_BASE_URLS[0]
        self.userAgent = (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/120.0.0.0 Safari/537.36"
        )
        self.timeout = 15
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": self.userAgent,
            "Accept": "application/json, text/plain, */*",
            "Accept-Language": "zh-CN,zh;q=0.9",
        })

        # 动态域名信息
        self.css_domain = ""
        self.pic_domain = ""
        self.novel_domain = ""
        self.csstime = ""
        self.channel_id = ""

    def _sync_from_cache(self):
        """从全局缓存同步域名到实例变量"""
        cached = get_cached_domain()
        self.siteUrl = cached["siteUrl"]
        self.css_domain = cached["css_domain"]
        self.pic_domain = cached["pic_domain"]
        self.novel_domain = cached["novel_domain"]
        self.csstime = cached["csstime"]
        self.channel_id = cached["channel_id"]

        # 降级处理
        if not self.pic_domain:
            self.pic_domain = self.siteUrl
        if not self.novel_domain:
            self.novel_domain = self.siteUrl
        if not self.css_domain:
            self.css_domain = self.siteUrl

    def init(self, extend=""):
        """插件初始化(框架回调)

        extend 支持传入自定义域名，格式:
          - 单域名: "https://xxx.com"
          - 多域名: "https://aaa.com,https://bbb.com"
        """
        global _BACKUP_BASE_URLS
        if extend and isinstance(extend, str):
            custom_urls = [u.strip() for u in extend.split(",") if u.strip().startswith("http")]
            if custom_urls:
                _BACKUP_BASE_URLS = custom_urls + [u for u in _BACKUP_BASE_URLS if u not in custom_urls]
                self.siteUrl = custom_urls[0]
                print(f"[INFO] 使用自定义域名: {self.siteUrl}")

        # 并发刷新域名（取最快响应，10分钟缓存）
        ok = refresh_domains_concurrent(timeout=8)
        if ok:
            self._sync_from_cache()
        else:
            print("[WARN] 所有域名均无法访问，请检查网络或配置新域名")

    def getName(self):
        return "国色天香"

    def refresh_domains(self) -> bool:
        """并发刷新域名（取最快响应），10分钟缓存，支持旧缓存降级"""
        ok = refresh_domains_concurrent(timeout=self.timeout)
        if ok:
            self._sync_from_cache()
        return ok

    def fetch(self, url, headers=None):
        """统一请求方法"""
        if headers is None:
            headers = {
                "User-Agent": self.userAgent,
                "Referer": self.siteUrl,
            }
        try:
            resp = self.session.get(url, headers=headers, timeout=self.timeout)
            resp.raise_for_status()
            return resp
        except Exception as e:
            print(f"[ERROR] fetch {url} failed: {e}")
            return None

    def _get_json(self, path: str, params: dict = None):
        """请求JSON接口"""
        # 分离 path 和 query string
        if "?" in path:
            base_path, existing_query = path.split("?", 1)
            url = f"{self.siteUrl}{base_path}?{existing_query}"
        else:
            url = f"{self.siteUrl}{path}"

        if params:
            query = "&".join(f"{k}={requests.utils.quote(str(v))}" for k, v in params.items())
            url += ("&" if "?" in url else "?") + query

        resp = self.fetch(url)
        if not resp:
            return None
        try:
            return resp.json()
        except Exception as e:
            print(f"[ERROR] JSON解析失败: {e}")
            return None

    def cover_url(self, serial_number: str) -> str:
        """封面 URL — 通过 localProxy 代理解密 XOR 加密的图片

        网站封面存储为 .css 文件, 内容是 XOR(0x88) 加密的 WebP 图片。
        TVBox 无法直接加载加密文件, 需要通过 localProxy 解密后返回。
        """
        if not serial_number:
            return ""
        pic_base = self.pic_domain if self.pic_domain else self.siteUrl
        css_url = f"{pic_base}/pic/{serial_number}/thumbnail.css"
        # 使用 localProxy 代理解密, 端口 9978 为 FongMi/TV 默认值
        return f"http://127.0.0.1:9978/proxy?action=proxy&type=cover&url={requests.utils.quote(css_url)}"

    def m3u8_url(self, serial_number: str) -> str:
        if not serial_number:
            return ""
        novel_base = self.novel_domain if self.novel_domain else self.siteUrl
        return f"{novel_base}/m3u8/{serial_number}/index_domain.m3u8?{self.csstime}"

    def _format_vod(self, item: dict) -> dict:
        """统一格式化为TVBox标准视频条目"""
        serial = item.get("serial_number", "")
        return {
            "vod_id": str(item.get("id", "")),
            "vod_name": decrypt_text(item.get("title", "")),
            "vod_pic": self.cover_url(serial) if serial else "",
            "vod_remarks": str(item.get("read_number", "")),
        }

    # ==================== TVBox 标准接口 ====================

    def homeContent(self, filter):
        """
        获取首页分类及筛选
        返回: {"class": [...], "filters": {...}}
        """
        result = {"class": [], "filters": {}}

        # 保底默认分类
        default_classes = [
            {"type_id": "1", "type_name": "国产"},
            {"type_id": "2", "type_name": "日本"},
            {"type_id": "3", "type_name": "韩国"},
            {"type_id": "4", "type_name": "欧美"},
        ]

        # 动态获取分类
        data = self._get_json(f"/index.json?{self.csstime}")
        classes = []
        filters_map = {}

        if data and "index_videos" in data:
            for key, cat in data["index_videos"].items():
                cat_id = str(cat.get("id", key))
                cat_name = decrypt_text(cat.get("name", ""))
                if not cat_name:
                    continue
                classes.append({
                    "type_id": cat_id,
                    "type_name": cat_name,
                })

                # 子流派作为该分类的筛选器
                genre_filter = {
                    "key": "genre",
                    "name": "流派",
                    "value": [{"n": "全部", "v": ""}]
                }
                for g in cat.get("genres", []):
                    g_name = decrypt_text(g.get("name", ""))
                    if g_name:
                        genre_filter["value"].append({"n": g_name, "v": str(g.get("id", ""))})

                # 标签筛选器
                label_filter = {
                    "key": "label",
                    "name": "标签",
                    "value": [{"n": "全部", "v": ""}]
                }
                for l in cat.get("labels", []):
                    l_name = html_module.unescape(l.get("name", ""))
                    if l_name:
                        label_filter["value"].append({"n": l_name, "v": str(l.get("id", ""))})

                filters_map[cat_id] = [genre_filter, label_filter]

        # 保底: 如果API失败,使用默认分类
        if not classes:
            classes = default_classes
            # 为保底分类也提供空的filters结构
            if filter:
                for c in classes:
                    filters_map[c["type_id"]] = []

        result['class'] = classes
        if filter:
            result['filters'] = filters_map
        return result

    def homeVideoContent(self):
        """
        获取首页推荐视频
        返回: {"list": [...]}
        """
        result = {"list": []}
        data = self._get_json(f"/index.json?{self.csstime}")
        if not data or "index_videos" not in data:
            return result

        videos = []
        seen_ids = set()
        for _, cat in data["index_videos"].items():
            for v in cat.get("videos", [])[:6]:  # 每个分类取6条
                vid = str(v.get("id", ""))
                if vid and vid not in seen_ids:
                    seen_ids.add(vid)
                    videos.append(self._format_vod(v))
        result["list"] = videos
        return result

    def categoryContent(self, tid, pg, filter, extend):
        """
        获取分类内容
        返回: {"list": [...], "page": pg, "pagecount": N, "limit": 20, "total": N}
        """
        result = {"list": [], "page": pg, "pagecount": 0, "limit": 20, "total": 0}

        # 构造分类API: /type/{cat_id}_{page}.json?{csstime}
        # 支持 extend 中的流派(genre)和标签(label)筛选
        api_path = f"/type/{tid}_{pg}.json?{self.csstime}"

        # 如果有筛选参数，通过 params 传递
        params = {}
        if extend and isinstance(extend, dict):
            if extend.get("genre"):
                params["genre"] = extend["genre"]
            if extend.get("label"):
                params["label"] = extend["label"]

        data = self._get_json(api_path, params=params if params else None)
        if not data:
            return result

        videos = []
        for v in data.get("data", {}).get("videos", []):
            videos.append(self._format_vod(v))

        page_count = data.get("data", {}).get("page_count", 1)
        result.update({
            "list": videos,
            "page": pg,
            "pagecount": page_count,
            "limit": 20,
            "total": page_count * 20,
        })
        return result

    def detailContent(self, ids):
        """
        获取详情页内容
        ids: [video_id]
        返回: {"list": [vod]}
        """
        result = {"list": []}
        video_id = ids[0] if isinstance(ids, list) else ids

        data = self._get_json(f"/video/{video_id}.json?{self.csstime}")
        if not data or "video" not in data:
            return result

        video = data["video"]
        serial = video.get("serial_number", "")

        # 构建标准化详情
        vod = {
            "vod_id": str(video_id),
            "vod_name": decrypt_text(video.get("title", "")),
            "vod_pic": self.cover_url(serial) if serial else "",
            "vod_remarks": str(video.get("read_number", "")),
            "vod_year": "",
            "vod_area": "",
            "vod_actor": str(video.get("actresses", "")),
            "vod_director": "",
            "vod_content": html_module.unescape(video.get("description", "")),
            "vod_play_from": "默认",
            "vod_play_url": "",
        }

        # 如果有m3u8直链,直接提供
        if serial:
            m3u8 = self.m3u8_url(serial)
            # TVBox标准格式: "集名$链接"，单集用 "播放$链接"
            vod["vod_play_url"] = f"播放${m3u8}"

        result["list"] = [vod]
        return result

    def searchContent(self, key, quick, pg=1):
        """
        搜索功能
        返回: {"list": [...]}  (TVBox标准格式)
        """
        result = {"list": []}
        data = self._get_json("/search.json", params={"search": key})
        if not data:
            return result

        videos = []
        for v in data.get("videos", []):
            videos.append(self._format_vod(v))
        result["list"] = videos
        return result

    def searchContentPage(self, key, quick, pg=1):
        return self.searchContent(key, quick, pg)

    def playerContent(self, flag, id, vipFlags):
        """
        获取播放内容
        flag: 播放源名称
        id: 播放地址(如果是直链就是m3u8 URL,否则是播放页路径)
        返回: {"parse": 0/1, "url": ..., "header": {...}}
        """
        result = {}
        headers = {
            "User-Agent": self.userAgent,
            "Referer": self.siteUrl,
        }

        if self.isVideoFormat(id):
            result["parse"] = 0
            result["url"] = id
            result["header"] = headers
        else:
            # 如果不是直链,需要解析播放页
            play_url = f"{self.siteUrl}{id}" if not id.startswith("http") else id
            resp = self.fetch(play_url)
            if resp:
                html = resp.text
                # 尝试提取m3u8
                m = re.search(r'https?://[^\s"\']+\.m3u8[^\s"\']*', html)
                if m:
                    result["parse"] = 0
                    result["url"] = m.group(0)
                    result["header"] = headers
                else:
                    result["parse"] = 1
                    result["url"] = play_url
                    result["header"] = headers
            else:
                result["parse"] = 1
                result["url"] = play_url
                result["header"] = headers
        return result

    def isVideoFormat(self, url):
        """判断是否为视频直链格式"""
        if not url or not isinstance(url, str):
            return False
        if not url.startswith("http"):
            return False
        fmt = ['.mp4', '.m3u8', '.ts', '.mkv', '.avi', '.webm', '.flv']
        for f in fmt:
            if url.lower().find(f) > -1:
                return True
        return False

    def manualVideoCheck(self):
        return False

    def localProxy(self, param):
        """本地代理(处理m3u8/key/封面解密等)"""
        action = param.get('action')
        if action == 'proxy':
            url = param.get('url')
            headers = {
                "User-Agent": self.userAgent,
                "Referer": self.siteUrl,
            }
            try:
                if param.get('type') == 'cover':
                    # 封面解密: .css 文件是 XOR(0x88) 加密的 WebP 图片
                    r = self.fetch(url, headers=headers)
                    if r and r.status_code == 200 and r.content:
                        decrypted = bytes(b ^ 0x88 for b in r.content)
                        return [200, "image/webp", decrypted]
                    return [404, "text/plain", "cover not found"]
                elif param.get('type') == 'm3u8':
                    r = self.fetch(url, headers=headers)
                    if r:
                        return [200, "application/vnd.apple.mpegurl", r.text]
                    return [500, "text/plain", "m3u8 fetch failed"]
                elif param.get('type') == 'media':
                    r = self.fetch(url, headers=headers)
                    if r:
                        return [206, "application/octet-stream", r.content]
                    return [500, "text/plain", "media fetch failed"]
                else:
                    r = self.fetch(url, headers=headers)
                    if r:
                        return [200, "text/plain", r.text]
                    return [500, "text/plain", "fetch failed"]
            except Exception as e:
                print(f"[ERROR] localProxy failed: {e}")
                return [500, "text/plain", str(e)]
        return None


# ==================== 本地调试入口 ====================
if __name__ == "__main__":
    spider = Spider()
    spider.init()

    print("=" * 60)
    print(f"爬虫名称: {spider.getName()}")
    print(f"站点URL: {spider.siteUrl}")
    print(f"pic_domain: {spider.pic_domain}")
    print(f"novel_domain: {spider.novel_domain}")
    print(f"csstime: {spider.csstime}")
    print("=" * 60)

    print("\n【测试1】homeContent")
    home = spider.homeContent(filter=True)
    print(f"  分类数: {len(home.get('class', []))}")
    for c in home.get('class', [])[:3]:
        print(f"    [{c['type_id']}] {c['type_name']}")

    print("\n【测试2】homeVideoContent")
    home_videos = spider.homeVideoContent()
    print(f"  推荐视频: {len(home_videos.get('list', []))}")
    for v in home_videos.get('list', [])[:2]:
        print(f"    {v['vod_id']} | {v['vod_name'][:20]} | {v['vod_pic'][:50]}...")

    if home.get('class'):
        tid = home['class'][0]['type_id']
        print(f"\n【测试3】categoryContent(tid={tid}, pg=1)")
        cat = spider.categoryContent(tid, 1, False, {})
        print(f"  视频数: {len(cat.get('list', []))}, 总页数: {cat.get('pagecount', 0)}")
        for v in cat.get('list', [])[:2]:
            print(f"    {v['vod_id']} | {v['vod_name'][:20]}")

        if cat.get('list'):
            vid = cat['list'][0]['vod_id']
            print(f"\n【测试4】detailContent([{vid}])")
            detail = spider.detailContent([vid])
            if detail.get('list'):
                vod = detail['list'][0]
                print(f"  名称: {vod['vod_name']}")
                print(f"  封面: {vod['vod_pic'][:60]}...")
                print(f"  播放源: {vod['vod_play_from']}")
                print(f"  播放地址: {vod['vod_play_url'][:80]}...")

    print("\n【测试5】searchContent('国产')")
    search_res = spider.searchContent("国产", False)
    print(f"  搜索结果: {len(search_res.get('list', []))}")
    for v in search_res.get('list', [])[:2]:
        print(f"    {v['vod_id']} | {v['vod_name'][:20]}")

    print("\n【测试6】playerContent(默认, m3u8_url, '')")
    sample_m3u8 = f"{spider.novel_domain}/m3u8/yl_8cef914fff77f784effa50bb2b1aeafe/index_domain.m3u8?{spider.csstime}"
    play = spider.playerContent("默认", sample_m3u8, "")
    print(f"  parse={play.get('parse')}, url={play.get('url', '')[:80]}...")

    print("\n" + "=" * 60)
    print("所有测试完成")
