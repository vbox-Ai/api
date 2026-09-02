# -*- coding: utf-8 -*-
"""
@header({
  searchable: 1,
  filterable: 1,
  quickSearch: 1,
  title: '流媒体PRO',
  lang: 'hipy',
})
"""
import re, json, requests, urllib.parse
import urllib3
from base.spider import Spider

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

class Spider(Spider):
    def getName(self):
        return "流媒体PRO"

    def init(self, extend=""):
        # ====== 自适应配置 ======
        # 优先级: 1.用户通过extend自定义 > 2.vbox客户端内置值 > 3.硬编码默认值
        DEFAULT_TMDB_KEY = "eea47c6a97dbc2b7cfad319971719cec"  # vbox客户端内置Key
        
        ext_dict = {}
        if isinstance(extend, dict):
            ext_dict = extend
        elif isinstance(extend, str) and extend:
            try:
                ext_dict = json.loads(extend)
            except:
                pass
        
        # TMDB API Key: 支持用户自定义
        self.TMDB_API_KEY = ext_dict.get("tmdb_key", "") or DEFAULT_TMDB_KEY
        
        # TMDB API 代理: 中国大陆需要代理访问 TMDB
        # 用户可通过 extend 传入 tmdb_proxy，格式: "https://your-proxy.com/?url="
        # 代理会将 TMDB URL 编码后附加到代理地址上
        self.TMDB_PROXY = ext_dict.get("tmdb_proxy", "")
        
        # TMDB 基础地址（api.tmdb.org 和 api.themoviedb.org 是同一服务的短/长域名，均可用）
        self.TMDB_API_BASE = "https://api.tmdb.org/3"
        self.TMDB_IMAGE_BASE = "https://images.tmdb.org/t/p"
        self.PANSOU_HOST = "https://so.252035.xyz"
        
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
            "accept": "application/json"
        }
        
        self.GENRE_MAP = {
            10759: "动作冒险", 16: "动画", 35: "喜剧", 80: "犯罪", 99: "纪录片",
            18: "剧情", 10751: "家庭", 10762: "儿童", 9648: "悬疑", 10763: "新闻",
            10764: "真人秀", 10765: "科幻", 10766: "肥皂剧", 10767: "脱口秀",
            10768: "政治", 37: "西部", 28: "动作", 12: "冒险", 14: "奇幻",
            878: "科幻", 27: "恐怖", 10749: "爱情", 53: "惊悚", 10752: "战争"
        }

    def _tmdb_get(self, path, params=None):
        """统一的 TMDB API 请求方法，自动处理代理"""
        if params is None:
            params = {}
        params["api_key"] = self.TMDB_API_KEY
        
        url = f"{self.TMDB_API_BASE}{path}"
        
        # 如果配置了代理，将 TMDB URL 编码后走代理
        if self.TMDB_PROXY:
            proxy_url = self.TMDB_PROXY
            separator = "&" if "?" in proxy_url else "?"
            full_url = f"{proxy_url}{separator}url={urllib.parse.quote(url + '&' + urllib.parse.urlencode(params), safe='')}"
            try:
                r = requests.get(full_url, headers=self.headers, timeout=10, verify=False)
                return r.json()
            except:
                pass
        
        # 直连（海外环境或无代理时）
        try:
            r = requests.get(url, params=params, headers=self.headers, timeout=10, verify=False)
            return r.json()
        except:
            return None

    def _tmdb_image(self, path, size="w500"):
        """生成 TMDB 图片 URL，自动处理代理"""
        if not path:
            return ""
        url = f"{self.TMDB_IMAGE_BASE}/{size}{path}"
        if self.TMDB_PROXY:
            separator = "&" if "?" in self.TMDB_PROXY else "?"
            return f"{self.TMDB_PROXY}{separator}url={urllib.parse.quote(url, safe='')}&type=img"
        return url

    def isVideoFormat(self, url):
        """vbox兼容: 判断是否为视频格式URL"""
        return False

    def manualVideoCheck(self):
        """vbox兼容: 手动视频检测"""
        return False

    def homeContent(self, filter):
        classes = [
            {"type_id": "recommend", "type_name": "推荐"},
            {"type_id": "213", "type_name": "Netflix"},
            {"type_id": "49", "type_name": "HBO Max"},
            {"type_id": "2552", "type_name": "Apple TV+"},
            {"type_id": "2739", "type_name": "Disney+"},
            {"type_id": "1024", "type_name": "Amazon Prime"},
            {"type_id": "453", "type_name": "Hulu"},
            {"type_id": "3353", "type_name": "Peacock"},
            {"type_id": "4330", "type_name": "Paramount+"},
            {"type_id": "2007", "type_name": "腾讯视频"},
            {"type_id": "1330", "type_name": "爱奇艺"},
            {"type_id": "1605", "type_name": "Bilibili"},
            {"type_id": "1419", "type_name": "优酷视频"},
            {"type_id": "1631", "type_name": "芒果TV"}
        ]
        
        filters = {}
        for c in classes:
            filters[c['type_id']] = [
                {"key": "contentType", "name": "内容类型", "value": [
                    {"n": "📺 剧集 (默认)", "v": "tv"},
                    {"n": "🎬 电影", "v": "movie"},
                    {"n": "🌸 动漫/动画", "v": "anime"},
                    {"n": "🎤 综艺/真人秀", "v": "variety"}
                ]},
                {"key": "sortBy", "name": "排序与功能", "value": [
                    {"n": "🔥 综合热度", "v": "popularity.desc"},
                    {"n": "⭐ 最高评分", "v": "vote_average.desc"},
                    {"n": "🆕 最新首播", "v": "first_air_date.desc"},
                    {"n": "📅 按更新时间", "v": "next_episode"},
                    {"n": "📆 今日播出", "v": "daily_airing"}
                ]}
            ]
        return {"class": classes, "filters": filters}

    def categoryContent(self, tid, pg, filter, extend):
        network_id = tid or "recommend"
        content_type = extend.get("contentType", "tv")
        sort_by = extend.get("sortBy", "popularity.desc")
        p = int(pg) if pg else 1

        endpoint = "/discover/movie" if content_type == "movie" else "/discover/tv"
        params = {"language": "zh-CN", "page": p}
        
        if network_id != "recommend":
            params["with_networks"] = network_id

        if content_type == "movie":
            s = sort_by
            if sort_by in ["next_episode", "daily_airing"]: s = "popularity.desc"
            if sort_by == "first_air_date.desc": s = "release_date.desc"
            params["sort_by"] = s
        else:
            if content_type == "anime": params["with_genres"] = "16"
            elif content_type == "variety": params["with_genres"] = "10764|10767"

            if sort_by == "daily_airing":
                import datetime
                today = datetime.datetime.now().strftime("%Y-%m-%d")
                params.update({"air_date.gte": today, "air_date.lte": today, "sort_by": "popularity.desc"})
            else:
                params["sort_by"] = "popularity.desc" if sort_by == "next_episode" else sort_by

        try:
            data = self._tmdb_get(endpoint, params)
            if not data or ("status_code" in data and data.get("status_code") != 1):
                return {"list": [], "page": p}
            videos = []
            
            for item in data.get("results", []):
                full_date = item.get("first_air_date") or item.get("release_date") or ""
                raw_year = full_date[:4] if full_date else "未知"
                genre_ids = item.get("genre_ids", [])
                genre = self.GENRE_MAP.get(genre_ids[0], "影视") if genre_ids else ("电影" if content_type == "movie" else "剧集")
                
                pic = self._tmdb_image(item.get('poster_path'))
                name = item.get("name") or item.get("title") or item.get("original_name", "")
                v_id = f"movie_{item['id']}" if content_type == "movie" else f"tv_{item['id']}"
                
                videos.append({
                    "vod_id": v_id,
                    "vod_name": name,
                    "vod_pic": pic,
                    "vod_remarks": f"☁️网盘 · {genre} · ⭐ {round(item.get('vote_average', 0), 1)}",
                    "vod_year": raw_year
                })
                
            return {"list": videos, "page": p, "pagecount": min(data.get("total_pages", 1), 500), "limit": 20, "total": data.get("total_results", len(videos))}
        except Exception:
            return {"list": [], "page": int(pg)}

    def detailContent(self, ids):
        id_str = ids[0]
        if "_" not in id_str: return {"list": []}
        media_type, tmdb_id = id_str.split("_")
        
        try:
            data = self._tmdb_get(f"/{media_type}/{tmdb_id}", {"language": "zh-CN"})
            if not data or ("status_code" in data and data.get("status_code") != 1):
                return {"list": []}
            
            search_title = data.get("name") or data.get("title") or data.get("original_name")
            pic = self._tmdb_image(data.get('poster_path'))
            year = (data.get("first_air_date") or data.get("release_date") or "")[:4]
            overview = data.get("overview", "暂无简介")
            
            # 获取网盘资源
            pan_r = None
            for _ in range(2):
                try:
                    pan_r = requests.get(f"{self.PANSOU_HOST}/api/search?kw={urllib.parse.quote(search_title)}&res=merge", headers={"User-Agent": "Mozilla/5.0"}, timeout=15, verify=False)
                    if pan_r.status_code == 200 and pan_r.text:
                        break
                except:
                    pass
            text = pan_r.text if pan_r else ""
            
            drive_regex = r"(https?:\/\/(?:www\.)?(?:aliyundrive\.com|alipan\.com|quark\.cn|pan\.baidu\.com|115\.com|123pan\.com|xunlei\.com|uc\.cn)[a-zA-Z0-9_/?=&%.\-+]+)"
            matches = re.finditer(drive_regex, text, re.I)
            
            grouped = {}
            for match in matches:
                link = match.group(1).replace("\\", "")
                context = text[match.end():match.end()+100]
                pwd_match = re.search(r'(?:pwd|提取码|密码|码)["\']?\s*[:：\s"\']*([a-zA-Z0-9]{4})\b', context, re.I)
                pwd = pwd_match.group(1) if pwd_match else ""
                
                drive_key = "other"
                if "baidu.com" in link: drive_key = "baidu"
                elif "quark.cn" in link: drive_key = "quark"
                elif "115.com" in link: drive_key = "a115"
                elif "aliyundrive.com" in link or "alipan.com" in link: drive_key = "ali"
                elif "xunlei.com" in link: drive_key = "xunlei"
                elif "123pan.com" in link: drive_key = "a123"
                elif "uc.cn" in link: drive_key = "uc"
                
                if drive_key != "other":
                    if drive_key not in grouped: grouped[drive_key] = []
                    
                    full_link = link
                    if pwd and "pwd=" not in full_link and "password=" not in full_link:
                        full_link += ("&" if "?" in full_link else "?") + "pwd=" + pwd
                        
                    if full_link not in grouped[drive_key]:
                        grouped[drive_key].append(full_link)
            
            # 构建网盘播放列表（vbox网盘UI模式：返回JSON数组，客户端自动读取网盘内文件）
            PAN_ORDER = ['baidu', 'a115', 'quark', 'ali', 'uc', 'xunlei']
            PAN_NAMES = {'ali': "阿里云盘", 'quark': "夸克网盘", 'uc': "UC网盘", 'xunlei': "迅雷网盘", 'a123': "123云盘", 'a189': "天翼网盘", 'a115': "115网盘", 'baidu': "百度网盘"}
            
            play_list = []
            for p_key in PAN_ORDER:
                if p_key in grouped and grouped[p_key]:
                    pan_name = PAN_NAMES.get(p_key, p_key)
                    # 每个网盘最多展示3个分享链接
                    for i, link in enumerate(grouped[p_key][:3]):
                        name = pan_name if i == 0 else f"{pan_name}#{i+1}"
                        play_list.append({"url": link, "name": name})
            
            if not play_list:
                play_list.append({"url": "", "name": "盘搜暂未收录"})
            
            return {
                "list": [{
                    "vod_id": id_str,
                    "vod_name": search_title,
                    "vod_pic": pic,
                    "vod_year": year,
                    "vod_content": overview,
                    "vod_remarks": f"☁️网盘 · {len(play_list)}个资源",
                    "vod_play_from": "网盘资源",
                    "vod_play_url": json.dumps(play_list, ensure_ascii=False)
                }]
            }
        except Exception:
            return {"list": []}

    def searchContent(self, key, quick, pg="1"):
        p = int(pg) if pg else 1
        try:
            data = self._tmdb_get("/search/multi", {"query": key, "language": "zh-CN", "page": p})
            if not data or ("status_code" in data and data.get("status_code") != 1):
                return {"list": [], "page": p}
            videos = []
            for item in data.get("results", []):
                if item.get("media_type") not in ["movie", "tv"]: continue
                videos.append({
                    "vod_id": f"{item['media_type']}_{item['id']}",
                    "vod_name": item.get("name") or item.get("title") or item.get("original_name", ""),
                    "vod_pic": self._tmdb_image(item.get('poster_path')),
                    "vod_remarks": "☁️网盘 · 电影" if item["media_type"] == "movie" else "☁️网盘 · 剧集"
                })
            return {"list": videos, "page": p}
        except Exception:
            return {"list": [], "page": p}

    def homeVideoContent(self):
        return self.categoryContent("recommend", "1", None, {})

    def playerContent(self, flag, id, vipFlags):
        if id.startswith("push://"):
            return {"parse": 0, "url": id, "header": {}}
            
        pans = ["pan.quark.cn", "drive.uc.cn", "pan.baidu.com", "aliyundrive.com", "alipan.com", "cloud.189.cn", "123pan.com", "pan.xunlei.com", "115.com"]
        if any(x in id for x in pans):
            return {"parse": 0, "url": "push://" + id, "header": {"User-Agent": "Mozilla/5.0"}}
            
        return {"parse": 0, "url": id}
