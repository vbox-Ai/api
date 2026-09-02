# -*- coding: utf-8 -*-
"""
红果短剧 TVBox 爬虫
站点: hongguoduanju.com (字节跳动系 React SSR)
数据来源: 页面内嵌 _ROUTER_DATA JSON
视频格式: MP4 (qznovelvod CDN)
"""
from base.spider import Spider
import json
import urllib.parse
import urllib.request


class Spider(Spider):
    host = "https://hongguoduanju.com"
    UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/132.0.0.0 Safari/537.36"
    timeout = 15

    def getName(self):
        return "红果短剧"

    def init(self, extend=""):
        pass

    def isVideoFormat(self, url):
        pass

    def manualVideoCheck(self):
        pass

    # ---- network & parse helpers ----

    def _header_str(self):
        return "User-Agent=%s&Referer=%s" % (self.UA, self.host)

    def _fetch_text(self, url, t=None):
        try:
            rsp = self.fetch(url)
            text = rsp.text
            if text and len(text) > 500:
                return text
        except Exception:
            pass
        req = urllib.request.Request(url)
        req.add_header("User-Agent", self.UA)
        req.add_header("Referer", self.host)
        with urllib.request.urlopen(req, timeout=t or self.timeout) as resp:
            return resp.read().decode("utf-8", errors="ignore")

    def _extract_router_data(self, html):
        """从 HTML 中提取 _ROUTER_DATA JSON 对象"""
        idx = html.find("_ROUTER_DATA")
        if idx == -1:
            return None
        eq = html.find("=", idx)
        start = eq + 1
        while start < len(html) and html[start] in " \t\n":
            start += 1
        json_start = html.find("{", start)
        if json_start == -1:
            return None
        try:
            decoder = json.JSONDecoder()
            obj, _ = decoder.raw_decode(html[json_start:])
            return obj
        except Exception:
            return None

    def _get_loader_data(self, url, key=None):
        """获取页面 loaderData, 可选按 key 取子项"""
        try:
            text = self._fetch_text(url)
            obj = self._extract_router_data(text)
            if obj and "loaderData" in obj:
                ld = obj["loaderData"]
                if key:
                    return ld.get(key)
                return ld
            return None
        except Exception:
            return None

    @staticmethod
    def _build_video_item(item, title_key="series_name"):
        """将 SSR item 转为 TVBox vod dict"""
        series_id = str(item.get("series_id", ""))
        title = item.get(title_key, item.get("series_title", ""))
        pic = item.get("series_cover", "")
        remarks = item.get("episode_right_text", "")
        if not remarks:
            ep_cnt = item.get("episode_cnt", "")
            if ep_cnt:
                remarks = "全%s集" % ep_cnt
        return {
            "vod_id": series_id,
            "vod_name": title,
            "vod_pic": pic,
            "vod_remarks": remarks,
            "vod_content": ""
        }

    # ---- home ----

    def homeContent(self, filter):
        classes = [{"type_id": "", "type_name": "全部"}]
        filters = {}
        try:
            cat_data = self._get_loader_data(self.host + "/category", "category_page")
            if cat_data:
                sl = cat_data.get("selectorList", [])
                # row 0: background -> classes
                if sl and len(sl) > 0:
                    for item in sl[0].get("items", []):
                        classes.append({
                            "type_id": item.get("selector_item_id", ""),
                            "type_name": item.get("show_name", "")
                        })
                # row 3: gender
                if len(sl) > 3:
                    gf = [{"n": "全部", "v": "2"}]
                    for item in sl[3].get("items", []):
                        gf.append({"n": item.get("show_name", ""), "v": str(item.get("selector_item_id", ""))})
                    filters["gender"] = gf
                # row 1: topic
                if len(sl) > 1:
                    tf = [{"n": "全部", "v": ""}]
                    for item in sl[1].get("items", []):
                        tf.append({"n": item.get("show_name", ""), "v": item.get("selector_item_id", "")})
                    filters["topic"] = tf
                # row 2: setting
                if len(sl) > 2:
                    sf = [{"n": "全部", "v": ""}]
                    for item in sl[2].get("items", []):
                        sf.append({"n": item.get("show_name", ""), "v": item.get("selector_item_id", "")})
                    filters["setting"] = sf
                # row 4: time
                if len(sl) > 4:
                    tmf = [{"n": "全部", "v": "0"}]
                    for item in sl[4].get("items", []):
                        tmf.append({"n": item.get("show_name", ""), "v": str(item.get("selector_item_id", ""))})
                    filters["min_first_visible_time"] = tmf
                # row 5: sort
                if len(sl) > 5:
                    stf = [{"n": "默认", "v": "0"}]
                    for item in sl[5].get("items", []):
                        stf.append({"n": item.get("show_name", ""), "v": str(item.get("selector_item_id", ""))})
                    filters["sort_type"] = stf
        except Exception:
            pass
        return {"class": classes, "filters": filters}

    def homeVideoContent(self):
        try:
            data = self._get_loader_data(self.host + "/", "page")
            if not data:
                return {"list": []}
            hs = data.get("homeSections", [])
            videos = []
            if hs:
                vl = hs[0].get("video_list", [])
                for item in vl:
                    videos.append(self._build_video_item(item, title_key="series_title"))
            return {"list": videos}
        except Exception:
            return {"list": []}

    # ---- category ----

    def categoryContent(self, cid, pg, filter, ext):
        page = int(pg) if pg else 1
        params = []
        if cid:
            params.append("background=%s" % cid)
        ext = ext or {}
        gender = ext.get("gender", "2")
        sort_type = ext.get("sort_type", "0")
        topic = ext.get("topic", "")
        setting = ext.get("setting", "")
        min_time = ext.get("min_first_visible_time", "0")
        params.append("gender=%s" % gender)
        params.append("sort_type=%s" % sort_type)
        if topic:
            params.append("topic=%s" % topic)
        if setting:
            params.append("setting=%s" % setting)
        if min_time and min_time != "0":
            params.append("min_first_visible_time=%s" % min_time)
        if page > 1:
            params.append("page=%d" % page)
        url = "%s/category?%s" % (self.host, "&".join(params))
        try:
            data = self._get_loader_data(url, "category_page")
            if not data:
                return {"list": [], "page": page, "pagecount": 1, "limit": 24, "total": 0}
            rl = data.get("recommendList", [])
            pg_data = data.get("pagination", {})
            videos = [self._build_video_item(item, title_key="series_name") for item in rl]
            return {
                "list": videos,
                "page": pg_data.get("pageNum", page),
                "pagecount": pg_data.get("totalPages", 1),
                "limit": pg_data.get("pageSize", 24),
                "total": pg_data.get("total", 0)
            }
        except Exception:
            return {"list": [], "page": page, "pagecount": 1, "limit": 24, "total": 0}

    # ---- detail ----

    def detailContent(self, ids):
        series_id = str(ids[0])
        url = "%s/detail?series_id=%s" % (self.host, series_id)
        try:
            data = self._get_loader_data(url, "detail_page")
            if not data:
                return {"list": []}
            sd = data.get("seriesDetail", {})
            if not sd:
                return {"list": []}
            vid_list = sd.get("vid_list", [])
            series_name = sd.get("series_name", "")
            series_cover = sd.get("series_cover", "")
            series_intro = sd.get("series_intro", "")
            episode_cnt = sd.get("episode_cnt", 0)
            tags = sd.get("tags", [])
            episode_right_text = sd.get("episode_right_text", "")
            # expose all episodes; player will handle playback per episode
            play_urls = []
            for i, vid in enumerate(vid_list):
                play_urls.append("第%d集$%s_%s" % (i + 1, series_id, vid))
            # notice about free vs paid (some episodes may require login)
            free_cnt = sd.get("accessible_episode_cnt", len(vid_list))
            notice = ""
            if episode_cnt > free_cnt:
                notice = "（前%d集免费，后续%d集可能需登录解锁）" % (free_cnt, episode_cnt - free_cnt)
            vod = {
                "vod_id": series_id,
                "vod_name": series_name,
                "vod_pic": series_cover,
                "vod_content": series_intro + notice,
                "vod_remarks": episode_right_text or ("全%s集" % episode_cnt),
                "type_name": " ".join(tags) if tags else "短剧",
                "vod_play_from": "红果短剧",
                "vod_play_url": "#".join(play_urls)
            }
            return {"list": [vod]}
        except Exception:
            return {"list": []}

    # ---- player ----

    def playerContent(self, flag, id, vipFlags):
        try:
            parts = str(id).split("_")
            if len(parts) < 2:
                return {"parse": 0, "playUrl": "", "url": "", "header": self._header_str()}
            series_id = parts[0]
            vid = "_".join(parts[1:])
            url = "%s/player/%s/%s" % (self.host, series_id, vid)
            ld = self._get_loader_data(url)
            if not ld:
                return {"parse": 0, "playUrl": "", "url": "", "header": self._header_str()}
            # find player page key (contains "player" and "page")
            player_key = None
            for k in ld:
                if "player" in k and "page" in k:
                    player_key = k
                    break
            if not player_key:
                return {"parse": 0, "playUrl": "", "url": "", "header": self._header_str()}
            vpi = ld[player_key].get("video_player_info", {})
            main_url = vpi.get("main_url", "")
            if not main_url:
                return {"parse": 0, "playUrl": "", "url": "", "header": self._header_str()}
            return {
                "parse": 0,
                "playUrl": "",
                "url": main_url,
                "header": self._header_str()
            }
        except Exception:
            return {"parse": 0, "playUrl": "", "url": "", "header": self._header_str()}

    # ---- search ----

    def searchContent(self, key, quick, pg=1):
        page = int(pg) if pg else 1
        keyword = urllib.parse.quote(key)
        url = "%s/search?keyword=%s" % (self.host, keyword)
        if page > 1:
            url += "&page=%d" % page
        try:
            ld = self._get_loader_data(url)
            if not ld:
                return {"list": []}
            # find search page key
            search_key = None
            for k in ld:
                if "search" in k:
                    search_key = k
                    break
            if not search_key:
                return {"list": []}
            sp = ld[search_key]
            sl = sp.get("searchList", [])
            if not sl:
                return {"list": []}
            videos = [self._build_video_item(item, title_key="series_name") for item in sl]
            total = sp.get("totalCount", 0)
            return {
                "list": videos,
                "page": page,
                "pagecount": (total + 23) // 24 if total > 0 else 1,
                "limit": 24,
                "total": total
            }
        except Exception:
            return {"list": []}
