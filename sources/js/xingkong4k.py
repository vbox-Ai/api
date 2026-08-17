import base64
import json
import time

import requests
from Crypto.Cipher import AES
from Crypto.Util.Padding import unpad

try:
    from base.spider import Spider as BaseSpider
except ImportError:
    class BaseSpider:
        pass


class Spider(BaseSpider):
    # API 域名：v1.2.7 起从 xk211 变更为 xk21127
    _API_DOMAINS = [
        "https://xk21127.xkgzs.xyz",
        "https://xk211.xkgzs.xyz",
    ]
    AES_KEY = b"11320jkjksdkxxaw"
    PAGE_SIZE = 36

    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": "okhttp/4.12.0",
            "Content-Type": "application/x-www-form-urlencoded",
            "App-Version-Code": "127",
            "App-Os-Type": "android",
            "App-Ui-Mode": "2",
            "App-Device-Id": "1234567890abcdef1234567890abcdef",
        })
        self._api_base = None
        self._init_data = None
        self._init_time = 0

    def _get_api(self):
        """并发探测可用域名，选第一个响应正常的"""
        if self._api_base:
            return self._api_base
        import concurrent.futures
        def _try(domain):
            try:
                r = self.session.post(domain + "/api/vod/init", data={}, timeout=8)
                d = r.json()
                if d.get("code") == 0 and d.get("data"):
                    return domain + "/api/vod/"
            except:
                pass
            return None
        with concurrent.futures.ThreadPoolExecutor(max_workers=len(self._API_DOMAINS)) as pool:
            futures = {pool.submit(_try, d): d for d in self._API_DOMAINS}
            for f in concurrent.futures.as_completed(futures):
                result = f.result()
                if result:
                    self._api_base = result
                    return result
        self._api_base = self._API_DOMAINS[0] + "/api/vod/"
        return self._api_base

    def getName(self):
        return "星空4K"

    def init(self, extend=""):
        pass

    def isVideoFormat(self, url):
        return bool(url and any(x in url.lower() for x in (".m3u8", ".mp4", ".flv", ".mkv", ".mpd")))

    def manualVideoCheck(self):
        pass

    def destroy(self):
        self.session.close()

    def _decrypt(self, value):
        raw = base64.b64decode(value)
        cipher = AES.new(self.AES_KEY, AES.MODE_CBC, self.AES_KEY)
        return json.loads(unpad(cipher.decrypt(raw), AES.block_size).decode("utf-8"))

    def _post(self, endpoint, data=None):
        api = self._get_api()
        response = self.session.post(api + endpoint, data=data or {}, timeout=15)
        response.raise_for_status()
        payload = response.json()
        if payload.get("code") != 0:
            raise RuntimeError(payload.get("msg") or "API request failed")
        encrypted = payload.get("data")
        return self._decrypt(encrypted) if encrypted else {}

    def _get_init(self):
        if self._init_data is None or time.time() - self._init_time > 600:
            self._init_data = self._post("init")
            self._init_time = time.time()
        return self._init_data

    @staticmethod
    def _vod(item):
        return {
            "vod_id": str(item.get("vod_id", "")),
            "vod_name": item.get("vod_name", ""),
            "vod_pic": item.get("vod_pic", ""),
            "vod_remarks": item.get("vod_remarks", ""),
        }

    def homeContent(self, filter):
        data = self._get_init()
        classes = [
            {"type_id": str(item["type_id"]), "type_name": item.get("type_name", "")}
            for item in data.get("type_list", [])
            if item.get("type_id")
        ]
        videos = data.get("recommend_list") or data.get("hot_search_list") or []
        return {"class": classes, "list": [self._vod(v) for v in videos], "filters": {}}

    def homeVideoContent(self):
        data = self._get_init()
        videos = data.get("recommend_list") or data.get("hot_search_list") or []
        return {"list": [self._vod(v) for v in videos]}

    def categoryContent(self, tid, pg, filter, extend):
        page = max(int(pg or 1), 1)
        params = {"type_id": tid, "page": page}
        for key in ("class", "area", "lang", "year", "sort", "by"):
            if extend and extend.get(key):
                params[key] = extend[key]
        data = self._post("typeFilterVodList", params)
        items = data.get("recommend_list", [])
        total = int(data.get("total") or 0)
        page_size = int(data.get("page_size") or self.PAGE_SIZE)
        pagecount = (total + page_size - 1) // page_size if total else page + (1 if len(items) >= page_size else 0)
        return {
            "page": page,
            "pagecount": max(pagecount, page),
            "limit": page_size,
            "total": total,
            "list": [self._vod(v) for v in items],
        }

    def detailContent(self, ids):
        data = self._post("vodDetail", {"vod_id": ids[0]})
        vod = data.get("vod") or {}
        source_info = {}
        for source in data.get("player_source_list", []):
            source_info.setdefault(source.get("player_code"), source)
        play_from = []
        play_urls = []
        for source in data.get("vod_play_url_list", []):
            code = source.get("player_code", "")
            player = source_info.get(code) or {}
            source_id = player.get("id")
            if source_id is None:
                continue
            episodes = []
            for episode in source.get("urls", []):
                url = episode.get("url", "")
                if url and url.startswith("http"):
                    # 平台直链（v.qq.com、iqiyi.com 等）或视频直链（.m3u8/.mp4）
                    play_id = url
                else:
                    # 无 URL 时走服务端解析
                    play_id = "xk://{}/{}/{}".format(ids[0], source_id, episode.get("episode_index", 0))
                episodes.append(f'{episode.get("name") or "播放"}${play_id}')
            if episodes:
                play_from.append(player.get("player_name") or code or "播放")
                play_urls.append("#".join(episodes))
        item = self._vod(vod)
        item.update({
            "vod_actor": vod.get("vod_actor", ""),
            "vod_director": vod.get("vod_director", ""),
            "vod_content": vod.get("vod_content") or vod.get("vod_blurb", ""),
            "vod_year": vod.get("vod_year", ""),
            "vod_area": vod.get("vod_area", ""),
            "vod_play_from": "$$$".join(play_from),
            "vod_play_url": "$$$".join(play_urls),
        })
        return {"list": [item]}

    def searchContent(self, key, quick, pg="1"):
        page = max(int(pg or 1), 1)
        data = self._post("searchList", {"keywords": key, "page": page})
        items = data.get("search_list", [])
        return {"page": page, "pagecount": page + (1 if len(items) >= self.PAGE_SIZE else 0), "list": [self._vod(v) for v in items]}

    def searchContentPage(self, key, quick, pg):
        return self.searchContent(key, quick, pg)

    def playerContent(self, flag, id, vipFlags=None):
        url = id
        if vipFlags and id and "://" not in str(id):
            url = vipFlags
        if url and "$" in str(url):
            url = str(url).rsplit("$", 1)[-1]
        # xk:// 协议走服务端解析
        if str(url).startswith("xk://"):
            parts = str(url)[5:].split("/")
            vod_id = parts[0] or flag or ""
            source_id = parts[1] if len(parts) > 1 else ""
            episode_index = parts[2] if len(parts) > 2 else "0"
            api = self._get_api()
            response = self.session.post(api + "vodParse", data={
                "vod_id": vod_id,
                "player_source_id": source_id,
                "episode_index": episode_index,
                "scene": 0,
            }, timeout=15)
            payload = response.json()
            # code=10001: 解析次数用完，需看激励视频
            if payload.get("code") != 0:
                raise RuntimeError(payload.get("msg") or "解析失败")
            encrypted = payload.get("data")
            if encrypted:
                data = self._decrypt(encrypted)
                url = data.get("play_url", "")
        direct = self.isVideoFormat(url)
        return {
            "parse": 0 if direct else 1,
            "url": url,
            "header": {"User-Agent": self.session.headers["User-Agent"]},
        }
