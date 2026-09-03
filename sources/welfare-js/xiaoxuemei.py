# -*- coding: utf-8 -*-
"""
小学妹影视 - v4 修复版
修复：详情页和播放都返回正确数据
  - API 详情接口不支持按 ID 查询，改用列表页数据缓存 + HTML 详情页解析
  - categoryContent/homeVideoContent/searchContent 缓存完整数据
  - detailContent 优先从缓存读取
  - 多域名并发探测 + 10分钟缓存
"""
import sys
import json
import re
import time
import base64
import concurrent.futures
from urllib.parse import urljoin, quote

sys.path.append('..')

try:
    from base.spider import Spider
except ImportError:
    import requests as rq
    class Spider:
        def fetch(self, url, headers=None, **kw):
            kw.pop('timeout', None)
            r = rq.get(url, headers=headers, timeout=15, **kw)
            try:
                r.encoding = 'utf-8'
            except Exception:
                pass
            return r


class Spider(Spider):

    def getName(self):
        return "小学妹"

    def init(self, extend=""):
        if isinstance(extend, list):
            self.extend = ''
        else:
            self.extend = extend or ''

        # vbox 适配: 多域名并发探测 + 10分钟缓存
        self.hosts = [
            "https://91.xiaoxuemei91912.com",
        ]
        self.host = self.hosts[0]
        self.header = {
            'User-Agent': 'Mozilla/5.0 (Linux; Android 13) AppleWebKit/537.36 '
                          '(KHTML, like Gecko) Chrome/120.0 Mobile Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            'Accept-Language': 'zh-CN,zh;q=0.9',
            'Referer': self.host + '/',
        }
        # vbox 域名注入
        try:
            _hosts = globals().get('_vbox_effective_hosts', [])
            if _hosts:
                self.hosts.insert(0, str(_hosts[0]).rstrip('/'))
        except Exception:
            pass
        self._effective_host = None
        self._last_host_check = 0
        self._host_cache_ttl = 600  # 10分钟缓存
        self._probe_domain()
        self._home_cache = []
        self._home_cache_time = 0
        self._vod_cache = {}

    def _probe_domain(self):
        """并发探测可用域名，10分钟缓存"""
        now = time.time()
        if self._effective_host and (now - self._last_host_check) < self._host_cache_ttl:
            self.host = self._effective_host
            self.header['Referer'] = self.host + '/'
            return

        def _try_domain(host):
            try:
                r = self.fetch(host, headers=self.header, timeout=10)
                if r and len(r.text) > 500:
                    return host
            except Exception:
                pass
            return None

        with concurrent.futures.ThreadPoolExecutor(max_workers=len(self.hosts)) as pool:
            futures = {pool.submit(_try_domain, h): h for h in self.hosts}
            for f in concurrent.futures.as_completed(futures):
                result = f.result()
                if result:
                    self._effective_host = result
                    self.host = result
                    self.header['Referer'] = self.host + '/'
                    self._last_host_check = now
                    return
        # 全部失败，回退第一个
        self.host = self.hosts[0]
        self.header['Referer'] = self.host + '/'
        self._effective_host = self.host
        self._last_host_check = now

    def _url(self, path):
        if not path:
            return self.host
        if path.startswith('http'):
            return path
        return self.host + path if path.startswith('/') else self.host + '/' + path

    def _txt(self, url, referer=None, timeout=30):
        headers = dict(self.header)
        if referer:
            headers['Referer'] = referer
        try:
            rsp = self.fetch(url, headers=headers, timeout=timeout)
            try:
                rsp.encoding = 'utf-8'
            except Exception:
                pass
            return rsp.text
        except Exception:
            return ''

    def _json(self, url, referer=None, timeout=15):
        text = self._txt(url, referer=referer, timeout=timeout)
        if not text:
            return {}
        try:
            return json.loads(text)
        except Exception:
            return {}

    # ========== 分类定义 ==========
    classes = [
        {'type_name': '国产視頻', 'type_id': '20'},
        {'type_name': '传媒系列', 'type_id': '114'},
        {'type_name': '日本无码', 'type_id': '22'},
        {'type_name': '番號库', 'type_id': '300'},
        {'type_name': '日本有码', 'type_id': '21'},
        {'type_name': '有码精品', 'type_id': '101'},
        {'type_name': '无码精品', 'type_id': '102'},
        {'type_name': '欧美精品', 'type_id': '104'},
        {'type_name': '动漫精品', 'type_id': '103'},
        {'type_name': 'SWAG系列', 'type_id': '125'},
    ]

    filters = {
        '20': [
            {'key': 'type', 'name': '子分类', 'value': [
                {'n': '全部', 'v': ''},
                {'n': '国产精品', 'v': '26'},
                {'n': '国产自拍', 'v': '29'},
                {'n': '国产主播', 'v': '35'},
                {'n': '抖阴视频', 'v': '84'},
            ]},
        ],
        '114': [
            {'key': 'type', 'name': '子分类', 'value': [
                {'n': '全部', 'v': ''},
                {'n': '综合传媒', 'v': '116'},
                {'n': '蜜桃传媒', 'v': '122'},
                {'n': 'SWAG', 'v': '125'},
            ]},
        ],
        '21': [
            {'key': 'type', 'name': '子分类', 'value': [
                {'n': '全部', 'v': ''},
                {'n': '强姦', 'v': '49'},
                {'n': '有码精品', 'v': '101'},
            ]},
        ],
    }

    DEFAULT_SUBTYPE = {
        '20': '26',
        '114': '116',
        '22': '102',
        '300': '350',
        '21': '49',
        '101': '101',
        '102': '102',
        '104': '104',
        '103': '103',
        '125': '125',
    }

    # ========== 首页 ==========
    def homeContent(self, filter):
        return {
            'class': self.classes,
            'filters': self.filters,
        }

    def homeVideoContent(self):
        now = int(time.time())
        if self._home_cache and now - self._home_cache_time < 300:
            return {'list': self._home_cache[:72]}

        tids = ['20', '114', '22', '300', '21']
        videos = []
        seen = set()

        for tid in tids:
            if len(videos) >= 72:
                break
            try:
                query_type = self.DEFAULT_SUBTYPE.get(tid, tid)
                data = self._api_list(tid=query_type, pg=1, limit=12)
                for v in data.get('list', []):
                    vid = v.get('vod_id')
                    if vid and str(vid) not in seen:
                        seen.add(str(vid))
                        videos.append(v)
                    if len(videos) >= 72:
                        break
            except Exception:
                continue

        self._home_cache = videos[:72]
        self._home_cache_time = now
        return {'list': self._home_cache}

    # ========== 分类列表 ==========
    def categoryContent(self, tid, pg, filter, extend):
        pg = int(pg or 1)
        ext = {}
        if extend:
            if isinstance(extend, dict):
                ext = extend
            elif isinstance(extend, str):
                try:
                    ext = json.loads(extend)
                except Exception:
                    ext = {}

        sub_type = ext.get('type', '')
        query_type = sub_type if sub_type else self.DEFAULT_SUBTYPE.get(tid, tid)

        result = self._api_list(tid=query_type, pg=pg)
        if result and result.get('list'):
            return result

        return {
            'list': [],
            'page': pg,
            'pagecount': 1,
            'limit': 10,
            'total': 0,
        }

    def _api_list(self, tid='', pg=1, limit=10):
        """苹果CMS AJAX API - 同时缓存完整数据"""
        try:
            url = f"{self.host}/index.php/ajax/data?mid=1&page={pg}"
            if tid:
                url += f"&tid={tid}"

            data = self._json(url, referer=self.host + '/', timeout=10)
            if not data or data.get('code') != 1:
                return None

            vod_list = data.get('list', [])
            videos = []
            for item in vod_list:
                vid = str(item.get('vod_id', ''))
                # 缓存完整原始数据，供 detailContent 使用
                self._vod_cache[vid] = item
                videos.append({
                    'vod_id': vid,
                    'vod_name': item.get('vod_name', ''),
                    'vod_pic': item.get('vod_pic', ''),
                    'vod_remarks': item.get('vod_remarks', item.get('vod_class', '')),
                    'type_name': item.get('type', {}).get('type_name', ''),
                    'vod_year': str(item.get('vod_year', '')),
                    'vod_area': item.get('vod_area', ''),
                })

            return {
                'list': videos,
                'page': pg,
                'pagecount': int(data.get('pagecount', 1)),
                'limit': int(data.get('limit', limit)),
                'total': int(data.get('total', len(videos))),
            }
        except Exception:
            return None

    # ========== 详情页（核心修复：优先从缓存取数据） ==========
    def detailContent(self, ids):
        if isinstance(ids, str):
            ids = [ids]
        vod_id = str(ids[0])

        # 1. 优先从缓存取（列表页已缓存完整数据）
        if vod_id in self._vod_cache:
            vod = self._format_vod_from_cache(self._vod_cache[vod_id])
            if vod:
                return {'list': [vod]}

        # 2. 缓存没有，访问 HTML 详情页解析
        vod = self._html_detail(vod_id)
        return {'list': [vod] if vod else []}

    def _format_vod_from_cache(self, item):
        """从缓存的列表数据构建详情"""
        vid = str(item.get('vod_id', ''))
        play_url = f"第1集${self._url('/v/' + vid + '/sid/1/nid/1/')}"

        return {
            'vod_id': vid,
            'vod_name': item.get('vod_name', ''),
            'vod_pic': item.get('vod_pic', ''),
            'type_name': item.get('type', {}).get('type_name', ''),
            'vod_year': str(item.get('vod_year', '')),
            'vod_area': item.get('vod_area', ''),
            'vod_remarks': item.get('vod_remarks', item.get('vod_class', '')),
            'vod_actor': item.get('vod_actor', ''),
            'vod_director': item.get('vod_director', ''),
            'vod_content': item.get('vod_content', item.get('vod_blurb', ''))[:500],
            'vod_play_from': '默认线路',
            'vod_play_url': play_url,
        }

    def _html_detail(self, vod_id):
        """HTML 详情页 fallback"""
        try:
            url = self._url(f'/voddetail/{vod_id}/')
            html = self._txt(url, timeout=15)
            if not html or len(html) < 200:
                return None

            # 标题从 <title> 取
            title = self._match(r'<title>(.*?)</title>', html)
            title = re.sub(r'\s*[-_|].*$', '', title or '').strip()
            title = re.sub(r'^在线播放', '', title).strip()

            # 图片取第一个大图（排除图标）
            pic = ''
            imgs = re.findall(r'src="(https?://[^"]+\.(?:jpg|jpeg|png))"', html)
            for img in imgs:
                if 'icon' not in img and 'logo' not in img and 'favicon' not in img:
                    pic = img
                    break

            # 简介从 meta description
            content = self._match(r'<meta name="description" content="([^"]*)"', html)
            if content:
                content = re.sub(r'免费在线观看.*$', '', content).strip()

            return {
                'vod_id': str(vod_id),
                'vod_name': title,
                'vod_pic': pic,
                'type_name': '',
                'vod_year': '',
                'vod_area': '',
                'vod_remarks': '',
                'vod_actor': '',
                'vod_director': '',
                'vod_content': content[:500],
                'vod_play_from': '默认线路',
                'vod_play_url': f"第1集${self._url('/v/' + str(vod_id) + '/sid/1/nid/1/')}",
            }
        except Exception:
            pass
        return None

    # ========== 搜索 ==========
    def searchContent(self, key, quick, pg="1"):
        pg = int(pg or 1)
        result = self._api_search(key, pg)
        if result and result.get('list'):
            return result
        return {'list': [], 'page': pg, 'pagecount': 1, 'limit': 10, 'total': 0}

    def _api_search(self, key, pg):
        try:
            url = f"{self.host}/index.php/ajax/data?mid=1&page={pg}&wd={quote(key, safe='')}"
            data = self._json(url, timeout=10)
            if data and data.get('code') == 1:
                vods = []
                for item in data.get('list', []):
                    vid = str(item.get('vod_id', ''))
                    self._vod_cache[vid] = item  # 缓存
                    vods.append({
                        'vod_id': vid,
                        'vod_name': item.get('vod_name', ''),
                        'vod_pic': item.get('vod_pic', ''),
                        'vod_remarks': item.get('vod_remarks', item.get('vod_class', '')),
                    })
                return {
                    'list': vods,
                    'page': pg,
                    'pagecount': int(data.get('pagecount', 1)),
                    'limit': int(data.get('limit', 10)),
                    'total': int(data.get('total', len(vods))),
                }
        except Exception:
            pass
        return None

    # ========== 播放解析 ==========
    def playerContent(self, flag, id, vipFlags):
        if not id:
            return {"parse": 1, "playUrl": "", "url": ""}

        url = id if str(id).startswith('http') else self._url(id)

        # 已经是直链
        if self._is_direct_media(url):
            return {
                "parse": 0,
                "playUrl": "",
                "url": url,
                "header": self.header,
            }

        # 访问播放页，提取 player_aaaa
        html = self._txt(url, referer=self.host + '/', timeout=30)
        if not html:
            return {"parse": 1, "playUrl": "", "url": url, "header": self.header}

        real = ""

        # 提取 player_aaaa JSON
        m = re.search(r'var\s+player_[a-zA-Z0-9_]+\s*=\s*(\{.*?\})\s*</script>', html, re.S)
        if m:
            try:
                pdata = json.loads(m.group(1))
                real = pdata.get('url', '')
                encrypt = pdata.get('encrypt', 0)
                if encrypt in [1, 2] and real:
                    try:
                        real = base64.b64decode(real).decode('utf-8')
                    except Exception:
                        pass
            except Exception:
                pass

        # iframe
        if not real:
            iframe = re.search(r'<iframe[^>]+src=["\']([^"\']+)["\']', html, re.S)
            if iframe:
                iframe_url = self._url(iframe.group(1))
                iframe_html = self._txt(iframe_url, referer=url, timeout=30)
                m2 = re.search(r'var\s+player_[a-zA-Z0-9_]+\s*=\s*(\{.*?\})\s*</script>', iframe_html, re.S)
                if m2:
                    try:
                        pdata = json.loads(m2.group(1))
                        real = pdata.get('url', '')
                    except:
                        pass
                if not real:
                    real = self._match(r'"url"\s*:\s*"([^"]+)"', iframe_html)
                if not real:
                    real = self._match(r'src=["\'](https?://[^"\']+\.(?:m3u8|mp4))["\']', iframe_html)

        # 全局 m3u8/mp4
        if not real:
            m2 = re.search(r'["\'](https?://[^"\']+\.(?:m3u8|mp4)[^"\']*)["\']', html, re.I)
            if m2:
                real = m2.group(1)

        # 子 m3u8 解析
        if real and ".m3u8" in real:
            real = self._resolve_m3u8_child(real, referer=url)

        if real:
            real = real.replace("\\/", "/")
            return {
                "parse": 0,
                "playUrl": "",
                "url": real,
                "header": {
                    "User-Agent": self.header["User-Agent"],
                    "Referer": url,
                },
            }

        # 兜底
        return {
            "parse": 1,
            "playUrl": "",
            "url": url,
            "header": self.header,
        }

    def _is_direct_media(self, url):
        url = (url or "").lower()
        return any(ext in url for ext in [".m3u8", ".mp4", ".flv", ".mkv"])

    def _resolve_m3u8_child(self, m3u8_url, referer=""):
        text = self._txt(m3u8_url, referer=referer or self.host + '/', timeout=20)
        if not text or "#EXTM3U" not in text:
            return m3u8_url
        lines = [x.strip() for x in text.splitlines() if x.strip()]
        for i, line in enumerate(lines):
            if line.startswith("#EXT-X-STREAM-INF"):
                for nxt in lines[i + 1:]:
                    if nxt and not nxt.startswith("#"):
                        return urljoin(m3u8_url, nxt)
        return m3u8_url

    # ========== 本地代理 ==========
    def localProxy(self, param):
        return [200, "video/MP2T", b"", ""]

    # ========== 工具方法 ==========
    def _match(self, pattern, text, flags=0):
        m = re.search(pattern, text, flags)
        return m.group(1) if m else ""

    def _strip_tags(self, text):
        if not text:
            return ""
        text = re.sub(r'<script[^>]*>.*?</script>', '', text, flags=re.S)
        text = re.sub(r'<style[^>]*>.*?</style>', '', text, flags=re.S)
        text = re.sub(r'<[^>]+>', '', text)
        text = re.sub(r'\s+', ' ', text).strip()
        return text

    def destroy(self):
        pass

    def close(self):
        self.destroy()
