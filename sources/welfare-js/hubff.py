# -*- coding: utf-8 -*-
"""
hubff TVBox Spider — vbox 适配版
站点: hubff.com

vbox 适配：
1. pyquery → BeautifulSoup4
2. 重写 fetch → 继承基类 self.fetch
3. playerContent header → dict 格式
4. 继承 base.spider.Spider
5. localProxy 图片代理（防盗链）
6. 补齐标准方法 destroy/action/getDependence
"""
import sys, json, re
from urllib.parse import urljoin, quote

sys.path.append('..')
try:
    from base.spider import Spider as _B
except ImportError:
    class _B:
        pass
try:
    import requests
except ImportError:
    requests = None
try:
    from bs4 import BeautifulSoup
except ImportError:
    BeautifulSoup = None

UA = "Mozilla/5.0 (Linux; Android 15; 2407FRK8EC Build/AP3A.240617.008; wv) AppleWebKit/537.36 (KHTML, like Gecko) Version/4.0 Chrome/128.0.6613.127 Mobile Safari/537.36"
SITE_URL = "https://hubff.com/"


class Spider(_B):
    headers = {
        "User-Agent": UA,
        "Origin": SITE_URL,
        "Referer": SITE_URL
    }
    playHeaders = {
        "User-Agent": UA,
        "Referer": SITE_URL
    }
    timeout = 22

    def getDependence(self):
        return ['bs4', 'requests']

    def getName(self):
        return "hubff"

    def isVideoFormat(self, url):
        return True

    def manualVideoCheck(self):
        pass

    def init(self, extend=""):
        pass

    def destroy(self):
        pass

    def action(self, action):
        pass

    # ============================================================
    # 1. 首页
    # ============================================================
    def homeContent(self, filter):
        result = {}
        classes = []
        try:
            html = self.fetch(SITE_URL, headers=self.headers, timeout=self.timeout).text
            if html and BeautifulSoup:
                soup = BeautifulSoup(html, 'html.parser')
                dropdown = soup.select_one('.dropdown-content') or soup.select_one('#class')
                if dropdown:
                    for a in dropdown.find_all('a'):
                        title = a.get_text(strip=True)
                        href = a.get('href', '')
                        if title and href and title not in ["首頁", "網站首頁", "免費註冊", "會員登錄"]:
                            type_id = href.replace(SITE_URL, "").lstrip('/')
                            classes.append({
                                "type_name": title,
                                "type_id": type_id
                            })
        except Exception as e:
            print(f"[hubff] homeContent error: {e}")

        if not classes:
            classes = [
                {"type_name": "最新", "type_id": "update.php?tags=latest"},
                {"type_name": "热门", "type_id": "update.php?tags=hot"},
                {"type_name": "国产", "type_id": "tag.php?tags=國產"}
            ]

        result['class'] = classes
        result['filters'] = {}
        return result

    def homeVideoContent(self):
        result = {}
        try:
            html = self.fetch(SITE_URL, headers=self.headers, timeout=self.timeout).text
            videos = self.parse_video_list(html)
        except Exception as e:
            print(f"[hubff] homeVideoContent error: {e}")
            videos = []
        result['list'] = videos
        return result

    # ============================================================
    # 2. 分类列表
    # ============================================================
    def categoryContent(self, tid, pg, filter, extend):
        result = {}
        try:
            if not tid or tid in ["首頁", "/"]:
                tid = "update.php?tags=latest"

            url = urljoin(SITE_URL, tid)
            if "page=" in url:
                url = re.sub(r'page=\d+', f'page={pg}', url)
            else:
                delimiter = "&" if "?" in url else "?"
                url = f"{url}{delimiter}page={pg}"

            html = self.fetch(url, headers=self.headers, timeout=self.timeout).text
            videos = self.parse_video_list(html)
        except Exception as e:
            print(f"[hubff] categoryContent error: {e}")
            videos = []

        result['list'] = videos
        result['page'] = pg
        result['pagecount'] = 9999
        result['limit'] = len(videos)
        result['total'] = 999999
        return result

    # ============================================================
    # 3. 详情页
    # ============================================================
    def detailContent(self, array):
        result = {}
        try:
            vid = array[0]
            html = self.fetch(vid, headers=self.headers, timeout=self.timeout).text

            iframe_match = re.search(r'<iframe[^>]+src=["\']([^"\']+)["\']', html, re.I)
            play_url = iframe_match.group(1) if iframe_match else vid

            if play_url and not play_url.startswith('http'):
                play_url = urljoin(SITE_URL, play_url)

            title_match = re.search(r'<title>([^<]+)</title>', html)
            title = title_match.group(1).strip() if title_match else "未知"

            img_match = re.search(r'<img[^>]+src=["\']([^"\']+)["\'][^>]*class=["\'][^"\']*poster', html)
            if not img_match:
                img_match = re.search(r'<img[^>]+src=["\']([^"\']+)["\']', html)
            pic = img_match.group(1) if img_match else ""

            vod = {
                "vod_id": vid,
                "vod_name": title,
                "vod_pic": self._wrap_proxy(pic),
                "vod_remarks": "",
                "vod_content": vid,
                "vod_play_from": "hubff",
                "vod_play_url": f"高清${play_url}"
            }
            result['list'] = [vod]
        except Exception as e:
            print(f"[hubff] detailContent error: {e}")
        return result

    # ============================================================
    # 4. 搜索
    # ============================================================
    def searchContent(self, key, quick, pg="1"):
        result = {}
        try:
            encoded_key = quote(key)
            url = f"{SITE_URL}tag.php?tags={encoded_key}&page={pg}"
            html = self.fetch(url, headers=self.headers, timeout=self.timeout).text
            videos = self.parse_video_list(html)
        except Exception as e:
            print(f"[hubff] searchContent error: {e}")
            videos = []
        result['list'] = videos
        return result

    def searchContentPage(self, key, quick, pg):
        return self.searchContent(key, quick, pg)

    # ============================================================
    # 5. 播放接口
    # ============================================================
    def playerContent(self, flag, id, vipFlags):
        result = {}
        try:
            if id.startswith('http'):
                req_headers = {
                    "User-Agent": UA,
                    "Referer": SITE_URL
                }
                html = self.fetch(id, headers=req_headers, timeout=self.timeout).text

                # 移除 HTML 注释，排除废弃脚本干扰
                clean_html = re.sub(r'<!--.*?-->', '', html, flags=re.DOTALL)

                # 匹配 Aliplayer 内的 source
                ali_match = re.search(r'source:\s*["\']([^"\']+)["\']', clean_html, re.I)
                if ali_match:
                    real_url = ali_match.group(1).strip()
                    if real_url.startswith('//'):
                        real_url = 'https:' + real_url

                    result["parse"] = 0
                    result["playUrl"] = ""
                    result["url"] = real_url
                    result["header"] = {
                        "User-Agent": UA,
                        "Referer": SITE_URL,
                        "Origin": SITE_URL.rstrip('/')
                    }
                    return result

            # 二次备用解析
            result["parse"] = 1
            result["playUrl"] = ""
            result["url"] = id
            result["header"] = dict(self.playHeaders)
        except Exception as e:
            print(f"[hubff] playerContent error: {e}")
            result["parse"] = 1
            result["playUrl"] = ""
            result["url"] = id
            result["header"] = dict(self.playHeaders)
        return result

    # ============================================================
    # 辅助: 解析视频列表
    # ============================================================
    def parse_video_list(self, html):
        """通用精准去广告提取函数"""
        videos = []
        if not html or not BeautifulSoup:
            return videos
        try:
            soup = BeautifulSoup(html, 'html.parser')
            list_box = soup.select_one('.list_box')
            if not list_box:
                return videos

            for ul in list_box.find_all('ul'):
                a = ul.find('a')
                link = a.get('href', '') if a else ""
                if not link or link.strip('/') == SITE_URL.strip('/'):
                    continue

                title_el = ul.select_one('.title')
                title = title_el.get_text(strip=True) if title_el else ""
                if '廣告' in title or '广告' in title:
                    continue

                if 'view.php' not in link:
                    continue

                img = ul.find('img')
                pic = ""
                if img:
                    pic = img.get('img') or img.get('src') or ''

                views = ""
                view_el = ul.select_one('.intro .view')
                if view_el:
                    views = view_el.get_text(strip=True)

                pub_time = ""
                timeago_el = ul.select_one('.intro .timeago')
                if timeago_el:
                    title_attr = timeago_el.get('title', '')
                    if title_attr and len(title_attr) >= 10:
                        pub_time = title_attr[5:10]
                if not pub_time:
                    time_el = ul.select_one('.intro .time')
                    if time_el:
                        pub_time = time_el.get_text(strip=True)

                remarks = f"\U0001F441 {views} | {pub_time}" if views and pub_time else (views or pub_time)

                if title and link:
                    videos.append({
                        "vod_id": self._abs_url(link),
                        "vod_name": title,
                        "vod_pic": self._wrap_proxy(self._abs_url(pic)),
                        "vod_remarks": remarks
                    })
        except Exception as e:
            print(f"[hubff] parse_video_list error: {e}")

        return videos

    # ============================================================
    # 辅助: URL 拼接
    # ============================================================
    def _abs_url(self, url):
        if not url:
            return ""
        if url.startswith('http'):
            return url
        return urljoin(SITE_URL, url)

    # ============================================================
    # localProxy: 图片代理（防盗链）
    # ============================================================
    def _wrap_proxy(self, url):
        if not url:
            return url
        if url.startswith('http'):
            return self._get_proxy_url(url)
        return url

    def _get_proxy_url(self, url):
        base = 'http://127.0.0.1:9978/proxy?do=py&url='
        return base + quote(url, safe='')

    def localProxy(self, param):
        if isinstance(param, str):
            from urllib.parse import parse_qs, urlparse
            params = parse_qs(urlparse(param).query)
        elif isinstance(param, dict):
            params = param
        else:
            params = {}

        url = params.get('url', [''])[0] if isinstance(params.get('url'), list) else params.get('url', '')
        if not url:
            url = params.get('key', [''])[0] if isinstance(params.get('key'), list) else params.get('key', '')

        if not url:
            return [200, 'text/plain', b'no url', {}]

        try:
            rsp = requests.get(url, headers={
                'User-Agent': UA,
                'Referer': SITE_URL,
            }, timeout=10, verify=False)
            content_type = rsp.headers.get('Content-Type', 'image/jpeg')
            return [200, content_type, rsp.content, {}]
        except Exception as e:
            print(f"[hubff] localProxy error: {e}")
            return [200, 'text/plain', b'proxy err', {}]
