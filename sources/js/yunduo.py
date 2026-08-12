# -*- coding: utf-8 -*-
# @Author  : 云朵影视
# @File    : 云朵影视.py
# @Description : TVBox/OK影视 标准爬虫 - 云朵影视 https://ds3xy2yunsa.xyz/

import sys
import json
import requests
from urllib.parse import quote

sys.path.append('..')
try:
    from base.spider import Spider
except:
    class Spider:
        pass


class Spider(Spider):
    def __init__(self):
        self.siteUrl = "https://ds3xy2yunsa.xyz"
        self.apiUrl = "https://ds3xy2yunsa.xyz/api.php/web"
        self.headers = {
            "Accept": "application/json",
            "X-Client": "8f3d2a1c7b6e5d4c9a0b1f2e3d4c5b6a",
            "web-sign": "yda81x6d9ad3c4s",
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Referer": "https://ds3xy2yunsa.xyz/"
        }
        self.typeNames = {
            1: "电影",
            2: "剧集",
            3: "动漫",
            4: "综艺"
        }

    def getName(self):
        return "云朵影视"

    def init(self, extend=""):
        pass

    def isVideoFormat(self, url):
        return url.endswith(".m3u8") or url.endswith(".mp4") or ".m3u8" in url or ".mp4" in url

    def manualVideoCheck(self):
        return False

    def _fetch(self, url, params=None):
        try:
            if params:
                response = requests.get(url, headers=self.headers, params=params, timeout=10)
            else:
                response = requests.get(url, headers=self.headers, timeout=10)
            response.raise_for_status()
            return response.json()
        except Exception as e:
            print(f"[云朵影视] 请求失败: {url} - {str(e)}")
            return {"code": -1, "msg": str(e)}

    def homeContent(self, filter):
        result = {"class": [], "filters": {}, "list": []}
        
        # 分类
        result["class"] = [
            {"type_id": "1", "type_name": "电影"},
            {"type_id": "2", "type_name": "剧集"},
            {"type_id": "3", "type_name": "动漫"},
            {"type_id": "4", "type_name": "综艺"}
        ]
        
        # 筛选器配置
        commonFilters = [
            {
                "key": "sort",
                "name": "排序",
                "value": [
                    {"n": "人气", "v": "hits"},
                    {"n": "最新", "v": "time"},
                    {"n": "评分", "v": "score"},
                    {"n": "年份", "v": "year"}
                ]
            },
            {
                "key": "area",
                "name": "地区",
                "value": [
                    {"n": "全部", "v": ""},
                    {"n": "大陆", "v": "大陆"},
                    {"n": "香港", "v": "香港"},
                    {"n": "台湾", "v": "台湾"},
                    {"n": "美国", "v": "美国"},
                    {"n": "日本", "v": "日本"},
                    {"n": "韩国", "v": "韩国"},
                    {"n": "泰国", "v": "泰国"},
                    {"n": "印度", "v": "印度"},
                    {"n": "英国", "v": "英国"},
                    {"n": "法国", "v": "法国"},
                    {"n": "德国", "v": "德国"},
                    {"n": "加拿大", "v": "加拿大"},
                    {"n": "西班牙", "v": "西班牙"},
                    {"n": "意大利", "v": "意大利"},
                    {"n": "澳大利亚", "v": "澳大利亚"}
                ]
            },
            {
                "key": "year",
                "name": "年份",
                "value": [
                    {"n": "全部", "v": ""},
                    {"n": "2026", "v": "2026"},
                    {"n": "2025", "v": "2025"},
                    {"n": "2024", "v": "2024"},
                    {"n": "2023", "v": "2023"},
                    {"n": "2022", "v": "2022"},
                    {"n": "2021", "v": "2021"},
                    {"n": "2020", "v": "2020"},
                    {"n": "2019", "v": "2019"},
                    {"n": "2018", "v": "2018"},
                    {"n": "2017", "v": "2017"},
                    {"n": "2016", "v": "2016"},
                    {"n": "2015-2011", "v": "2015-2011"},
                    {"n": "2010-2000", "v": "2010-2000"},
                    {"n": "90年代", "v": "90年代"},
                    {"n": "80年代", "v": "80年代"},
                    {"n": "更早", "v": "更早"}
                ]
            }
        ]
        
        # 电影筛选
        movieClass = [
            {"n": "全部", "v": ""},
            {"n": "动作", "v": "动作"},
            {"n": "喜剧", "v": "喜剧"},
            {"n": "爱情", "v": "爱情"},
            {"n": "科幻", "v": "科幻"},
            {"n": "恐怖", "v": "恐怖"},
            {"n": "悬疑", "v": "悬疑"},
            {"n": "犯罪", "v": "犯罪"},
            {"n": "战争", "v": "战争"},
            {"n": "动画", "v": "动画"},
            {"n": "冒险", "v": "冒险"},
            {"n": "历史", "v": "历史"},
            {"n": "灾难", "v": "灾难"},
            {"n": "纪录", "v": "纪录"},
            {"n": "剧情", "v": "剧情"}
        ]
        
        # 剧集筛选
        tvClass = [
            {"n": "全部", "v": ""},
            {"n": "剧情", "v": "剧情"},
            {"n": "爱情", "v": "爱情"},
            {"n": "悬疑", "v": "悬疑"},
            {"n": "古装", "v": "古装"},
            {"n": "都市", "v": "都市"},
            {"n": "犯罪", "v": "犯罪"},
            {"n": "科幻", "v": "科幻"},
            {"n": "奇幻", "v": "奇幻"},
            {"n": "武侠", "v": "武侠"},
            {"n": "喜剧", "v": "喜剧"},
            {"n": "历史", "v": "历史"},
            {"n": "动作", "v": "动作"}
        ]
        
        # 动漫筛选
        animeClass = [
            {"n": "全部", "v": ""},
            {"n": "热血", "v": "热血"},
            {"n": "冒险", "v": "冒险"},
            {"n": "奇幻", "v": "奇幻"},
            {"n": "科幻", "v": "科幻"},
            {"n": "搞笑", "v": "搞笑"},
            {"n": "恋爱", "v": "恋爱"},
            {"n": "战斗", "v": "战斗"},
            {"n": "武侠", "v": "武侠"},
            {"n": "魔法", "v": "魔法"},
            {"n": "竞技", "v": "竞技"},
            {"n": "悬疑", "v": "悬疑"}
        ]
        
        # 综艺筛选
        showClass = [
            {"n": "全部", "v": ""},
            {"n": "真人秀", "v": "真人秀"},
            {"n": "脱口秀", "v": "脱口秀"},
            {"n": "音乐", "v": "音乐"},
            {"n": "舞蹈", "v": "舞蹈"},
            {"n": "美食", "v": "美食"},
            {"n": "旅游", "v": "旅游"},
            {"n": "搞笑", "v": "搞笑"},
            {"n": "访谈", "v": "访谈"},
            {"n": "竞技", "v": "竞技"}
        ]
        
        result["filters"]["1"] = [{"key": "class", "name": "类型", "value": movieClass}] + commonFilters
        result["filters"]["2"] = [{"key": "class", "name": "类型", "value": tvClass}] + commonFilters
        result["filters"]["3"] = [{"key": "class", "name": "类型", "value": animeClass}] + commonFilters
        result["filters"]["4"] = [{"key": "class", "name": "类型", "value": showClass}] + commonFilters
        
        # 获取首页推荐
        try:
            homeData = self._fetch(f"{self.apiUrl}/index/home")
            if homeData.get("code") == 200 and homeData.get("data"):
                data = homeData["data"]
                # 热门推荐
                if "recommend" in data:
                    for item in data["recommend"]:
                        result["list"].append(self._formatVodItem(item))
                # 如果推荐为空，尝试分类视频
                if not result["list"] and "categories" in data:
                    for cat in data["categories"]:
                        for item in cat.get("videos", [])[:3]:
                            result["list"].append(self._formatVodItem(item))
        except Exception as e:
            print(f"[云朵影视] 获取首页失败: {str(e)}")
        
        return result

    def homeVideoContent(self):
        result = {"list": []}
        try:
            homeData = self._fetch(f"{self.apiUrl}/index/home")
            if homeData.get("code") == 200 and homeData.get("data"):
                data = homeData["data"]
                # 热门推荐
                if "recommend" in data:
                    for item in data["recommend"]:
                        result["list"].append(self._formatVodItem(item))
                # 分类视频
                if "categories" in data:
                    for cat in data["categories"]:
                        for item in cat.get("videos", [])[:4]:
                            result["list"].append(self._formatVodItem(item))
        except Exception as e:
            print(f"[云朵影视] 获取首页视频失败: {str(e)}")
        return result

    def categoryContent(self, tid, pg, filter, extend):
        result = {"list": [], "page": int(pg), "pagecount": 1, "limit": 24, "total": 0}
        
        try:
            params = {
                "type_name": self.typeNames.get(int(tid), ""),
                "type_id": tid,
                "page": pg,
                "sort": extend.get("sort", "hits") if extend else "hits"
            }
            
            if extend:
                if extend.get("class"):
                    params["class"] = extend["class"]
                if extend.get("area"):
                    params["area"] = extend["area"]
                if extend.get("year"):
                    params["year"] = extend["year"]
            
            data = self._fetch(f"{self.apiUrl}/filter/vod", params)
            if data.get("code") == 200 and data.get("data"):
                result["list"] = [self._formatVodItem(item) for item in data["data"]]
                result["page"] = data.get("page", int(pg))
                result["pagecount"] = data.get("pageCount", 1)
                result["limit"] = data.get("limit", 24)
                result["total"] = data.get("total", len(data["data"]))
        except Exception as e:
            print(f"[云朵影视] 获取分类失败: {str(e)}")
        
        return result

    def detailContent(self, ids):
        result = {"list": []}
        if not ids:
            return result
        
        vod_id = ids[0] if isinstance(ids, list) else ids
        
        try:
            # 获取详情
            detailData = self._fetch(f"{self.apiUrl}/vod/get_detail", {"vod_id": vod_id})
            if detailData.get("code") == 200 and detailData.get("data"):
                vod = detailData["data"][0] if isinstance(detailData["data"], list) else detailData["data"]
                
                # 获取聚合播放源
                playFrom = []
                playUrl = []
                
                try:
                    aggData = self._fetch(f"{self.apiUrl}/internal/search_aggregate", {"vod_id": vod_id})
                    if aggData.get("code") == 200 and aggData.get("data"):
                        # 优先使用 decode_status=0 的直链源
                        directSources = [s for s in aggData["data"] if s.get("decode_status") == 0]
                        decodeSources = [s for s in aggData["data"] if s.get("decode_status") == 1]
                        
                        # 添加直链源
                        for source in directSources:
                            from_name = source.get("site_name", source.get("from", "未知"))
                            playFrom.append(from_name)
                            playUrl.append(source.get("vod_play_url", ""))
                        
                        # 添加需要解码的源（外部平台链接）
                        for source in decodeSources:
                            from_name = source.get("site_name", source.get("from", "未知"))
                            playFrom.append(from_name)
                            playUrl.append(source.get("vod_play_url", ""))
                except Exception as e:
                    print(f"[云朵影视] 获取聚合播放源失败: {str(e)}")
                
                # 如果聚合没有数据，使用详情自带的播放源
                if not playFrom and vod.get("vod_play_from"):
                    playFrom = vod.get("vod_play_from", "").split("$$$")
                    playUrl = vod.get("vod_play_url", "").split("$$$")
                
                vodItem = {
                    "vod_id": vod.get("vod_id", vod_id),
                    "vod_name": vod.get("vod_name", ""),
                    "vod_pic": vod.get("vod_pic", ""),
                    "type_name": vod.get("type_name", ""),
                    "vod_year": str(vod.get("vod_year", "")),
                    "vod_area": vod.get("vod_area", ""),
                    "vod_remarks": vod.get("vod_remarks", ""),
                    "vod_content": self._cleanHtml(vod.get("vod_content", "")),
                    "vod_actor": vod.get("vod_actor", ""),
                    "vod_director": vod.get("vod_director", ""),
                    "vod_play_from": "$$$".join(playFrom),
                    "vod_play_url": "$$$".join(playUrl)
                }
                result["list"].append(vodItem)
        except Exception as e:
            print(f"[云朵影视] 获取详情失败: {str(e)}")
        
        return result

    def playerContent(self, flag, id, vipFlags):
        result = {"parse": 0, "url": "", "header": "", "jx": 0}
        
        if not id:
            return result
        
        try:
            # 如果是外部平台链接（腾讯、优酷、爱奇艺等），需要解析
            externalSites = ["v.qq.com", "youku.com", "iqiyi.com", "mgtv.com", "bilibili.com"]
            if any(site in id for site in externalSites):
                result["parse"] = 1
                result["jx"] = 1
                result["url"] = id
                return result
            
            # 如果是 co_ 开头的加密链接，需要调用解码接口
            if id.startswith("co_"):
                # 云朵影视的解码接口使用 protobuf，这里直接返回给播放器处理
                # 或者尝试通过解码接口获取
                result["parse"] = 1
                result["url"] = id
                return result
            
            # 如果是直链（m3u8/mp4）
            if self.isVideoFormat(id):
                result["parse"] = 0
                result["url"] = id
                result["header"] = json.dumps({
                    "User-Agent": self.headers["User-Agent"],
                    "Referer": self.siteUrl + "/"
                })
                return result
            
            # 默认直接返回
            result["parse"] = 0
            result["url"] = id
        except Exception as e:
            print(f"[云朵影视] 播放处理失败: {str(e)}")
        
        return result

    def searchContent(self, key, quick, pg="1"):
        result = {"list": [], "page": int(pg), "pagecount": 1, "limit": 15, "total": 0}
        
        try:
            data = self._fetch(f"{self.apiUrl}/search/index", {"wd": key, "page": pg})
            if data.get("code") == 200 and data.get("data"):
                result["list"] = [self._formatVodItem(item) for item in data["data"]]
                result["page"] = data.get("page", int(pg))
                result["pagecount"] = data.get("pageCount", 1)
                result["limit"] = data.get("limit", 15)
                result["total"] = data.get("total", len(data["data"]))
        except Exception as e:
            print(f"[云朵影视] 搜索失败: {str(e)}")
        
        return result

    def searchContentPage(self, key, quick, pg):
        return self.searchContent(key, quick, pg)

    def localProxy(self, param):
        return [200, "video/MP2T", {}, ""]

    def _formatVodItem(self, item):
        return {
            "vod_id": item.get("vod_id", ""),
            "vod_name": item.get("vod_name", ""),
            "vod_pic": item.get("vod_pic", ""),
            "vod_remarks": item.get("vod_remarks", ""),
            "vod_year": str(item.get("vod_year", "")),
            "vod_area": item.get("vod_area", "") if isinstance(item.get("vod_area"), str) else ",".join(item.get("vod_area", [])),
            "type_name": item.get("type_name", "")
        }
    
    def _cleanHtml(self, html):
        if not html:
            return ""
        import re
        html = re.sub(r'<[^>]+>', '', html)
        html = html.replace('&nbsp;', ' ').replace('&lt;', '<').replace('&gt;', '>').replace('&amp;', '&')
        return html.strip()


# 测试入口
if __name__ == '__main__':
    spider = Spider()
    # 测试首页
    # print(json.dumps(spider.homeContent(True), ensure_ascii=False, indent=2))
    # 测试分类
    # print(json.dumps(spider.categoryContent("1", "1", True, {"sort": "hits"}), ensure_ascii=False, indent=2))
    # 测试搜索
    # print(json.dumps(spider.searchContent("镖人", False), ensure_ascii=False, indent=2))
    # 测试详情
    # print(json.dumps(spider.detailContent(["338"]), ensure_ascii=False, indent=2))
