# -*- coding: utf-8 -*-
"""
平台名称：萝莉聚合AV
平台标识：luojubj_py
作者：原始 tvshare23 · 适配：vbox Python Spider 框架
适配日期：2026-08-23
说明：
  - 继承 base.spider.Spider，super().init() 兜底
  - 域名注入：从 _vbox_effective_hosts 取候选域名
  - 并发域名探测：主域名 + 备用域名同时探测，先到先用
  - 10 分钟冷静期：成功域名缓存 600s，过期重新探测
  - 保留 base64 反混淆（var _s）
  - 返回 dict（已是 dict 格式，仅做并发改造）
  - playerContent 返回 parse=0 m3u8 直链
"""
import sys
import re
import json
import base64
import time
from urllib.parse import urljoin, quote

try:
    from base.spider import Spider as BaseSpider
except ImportError:
    import requests as rq
    class BaseSpider:
        def init(self, extend=""): pass
        def fetch(self, url, headers=None, **kw):
            kw.pop('timeout', None)
            r = rq.get(url, headers=headers, timeout=15, **kw)
            r.encoding = 'utf-8'
            return r
        def getProxyUrl(self):
            return ''

# ── 平台配置 ──────────────────────────────────
HOST = 'https://www.luojubj.xyz'
# 备用域名（如主域名不可用时并发探测）
BACKUP_HOSTS = [
    'https://www.luojubj.xyz',
    'https://luojubj.xyz',
]

# ── 冷静期常量 ────────────────────────────────
_PROBE_COOLDOWN = 600  # 10 分钟


class Spider(BaseSpider):
    HOST = HOST

    def getName(self):
        return "萝莉聚合AV"

    def init(self, extend=''):
        # 1) 先 super，让 base.spider 注入 _vbox_effective_hosts
        try:
            super().init(extend)
        except Exception:
            pass

        # 2) 域名注入
        injected = getattr(self, '_vbox_effective_hosts', None) or []
        if injected:
            self.hosts = [str(h).rstrip('/') for h in injected]
        else:
            self.hosts = list(BACKUP_HOSTS)

        self.host = self.hosts[0]
        self.header = {
            'User-Agent': 'Mozilla/5.0 (Linux; Android 13) AppleWebKit/537.36 '
                          '(KHTML, like Gecko) Chrome/120.0 Mobile Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            'Accept-Language': 'zh-CN,zh;q=0.9',
            'Referer': self.host + '/',
            'Cookie': 'verified=true',
        }
        self._home_cache = []
        self._home_cache_time = 0
        self._classes = None
        self._filters = None
        self._probe_cache = {}  # {domain: (success, timestamp)}

    # ── 并发域名探测（带 10 分钟冷静期）────────
    def _probe_domain(self, domain):
        now = time.time()
        if domain in self._probe_cache:
            ok, ts = self._probe_cache[domain]
            if now - ts < _PROBE_COOLDOWN:
                return ok
        try:
            rsp = requests.get(domain + '/', headers=self.header, timeout=8, verify=False)
            ok = rsp is not None and len(rsp.text) > 100
        except Exception:
            ok = False
        self._probe_cache[domain] = (ok, now)
        return ok

    def _resolve_hosts(self):
        """并发探测所有候选域名，返回可用域名列表"""
        now = time.time()
        cached_ok = []
        need_probe = []
        for d in self.hosts:
            if d in self._probe_cache:
                ok, ts = self._probe_cache[d]
                if now - ts < _PROBE_COOLDOWN:
                    if ok:
                        cached_ok.append(d)
                    continue
            need_probe.append(d)

        if cached_ok and not need_probe:
            return cached_ok

        if need_probe:
            results = []
            from concurrent.futures import ThreadPoolExecutor, as_completed
            with ThreadPoolExecutor(max_workers=len(need_probe)) as ex:
                futs = {ex.submit(self._probe_domain, d): d for d in need_probe}
                for f in as_completed(futs):
                    d = futs[f]
                    if f.result():
                        results.append(d)
            return cached_ok + results
        return cached_ok

    def _url(self, path):
        if not path:
            return self.host
        if path.startswith('http'):
            return path
        return self.host + path if path.startswith('/') else self.host + '/' + path

    def _fetch_html(self, url, timeout=20):
        try:
            rsp = requests.get(url, headers=self.header, timeout=timeout, verify=False)
            rsp.encoding = 'utf-8'
            text = rsp.text
            if len(text) < 100 or 'var _s' not in text:
                return ''
            m = re.search(r'var\s+_s\s*=\s*"([^"]+)"', text)
            if m:
                return base64.b64decode(m.group(1)).decode('utf-8')
            return text
        except Exception:
            return ''

    def _parse_videos(self, html):
        """解析视频卡片（兼容列表页和搜索页两种结构）"""
        videos = []
        seen = set()
        items = re.findall(
            r'<a[^>]*href=["\'](/news/(\d+)\.html)["\'][^>]*>(.*?)</a>',
            html, re.S
        )
        for href, vid, content in items:
            if vid in seen:
                continue
            if 'data-src' not in content:
                continue
            seen.add(vid)

            img = re.search(r'data-src=["\']([^"\']+)["\']', content)
            pic = img.group(1) if img else ''
            if pic and not pic.startswith('http'):
                pic = self.host + pic

            title = ''
            h3_match = re.search(r'<h3[^>]*class=["\'][^"\']*v-title[^"\']*["\'][^>]*>(.*?)</h3>', content, re.S)
            if h3_match:
                title = re.sub(r'<[^>]+>', '', h3_match.group(1)).strip()
            if not title:
                alt = re.search(r'alt=["\']([^"\']+)["\']', content)
                if alt and alt.group(1) != 'video':
                    title = alt.group(1)
            if not title:
                text_only = re.sub(r'<[^>]+>', '', content).strip()
                title = text_only[:50] if text_only else ''

            videos.append({
                'vod_id': vid,
                'vod_name': title,
                'vod_pic': pic,
                'vod_remarks': '',
            })
        return videos

    def _parse_detail(self, html, vid):
        title = ''
        title_match = re.search(r'<title>([^<]+)</title>', html)
        if title_match:
            title = title_match.group(1).replace(' - 播放页', '').strip()

        pic = ''
        pic_match = re.search(r'<img[^>]*data-src=["\']([^"\']+)["\'][^>]*alt=', html)
        if not pic_match:
            pic_match = re.search(r'<img[^>]*src=["\']([^"\']+)["\'][^>]*alt=', html)
        if pic_match:
            pic = pic_match.group(1)
            if not pic.startswith('http'):
                pic = self.host + pic

        m3u8 = ''
        src_match = re.search(r'<source[^>]*src=["\']([^"\']+\.m3u8)["\']', html)
        if src_match:
            m3u8 = src_match.group(1)
        if not m3u8:
            m3u8_match = re.search(r'm3u8=["\']([^"\']+\.m3u8)["\']', html)
            if m3u8_match:
                m3u8 = m3u8_match.group(1)

        content = ''
        desc_match = re.search(r'<div[^>]*class=["\'][^"\']*desc[^"\']*["\'][^>]*>(.*?)</div>', html, re.S)
        if desc_match:
            content = re.sub(r'<[^>]+>', '', desc_match.group(1)).strip()

        play_url = f"播放${m3u8}" if m3u8 else ''

        return {
            'vod_id': vid,
            'vod_name': title,
            'vod_pic': pic,
            'type_name': '',
            'vod_year': '',
            'vod_area': '',
            'vod_remarks': '',
            'vod_actor': '',
            'vod_director': '',
            'vod_content': content[:500] if content else '',
            'vod_play_from': '默认线路',
            'vod_play_url': play_url,
        }

    def _get_pagecount(self, html):
        pages = re.findall(r'[?&]page=(\d+)', html)
        if pages:
            return max([int(p) for p in pages if p.isdigit()])
        return 1

    # ========== 分类与筛选器 ==========
    def _load_classes(self):
        if self._classes is not None:
            return self._classes

        classes = [
            {'type_id': '番号', 'type_name': '番号视频'},
            {'type_id': '国产', 'type_name': '国产视频'},
            {'type_id': '排行', 'type_name': '视频排行榜'},
            {'type_id': '专题', 'type_name': '热门专题'},
        ]

        filters = {
            '番号': [{
                'key': 'cat',
                'name': '子分类',
                'value': [
                    {'n': '中文字幕', 'v': '中文字幕'},
                    {'n': '美乳巨乳', 'v': '美乳巨乳'},
                    {'n': '童颜巨乳', 'v': '童颜巨乳'},
                    {'n': '强奸乱伦', 'v': '强奸乱伦'},
                    {'n': '邻家人妻', 'v': '邻家人妻'},
                    {'n': '萝莉少女', 'v': '萝莉少女'},
                    {'n': '制服丝袜', 'v': '制服丝袜'},
                    {'n': '亚洲情色', 'v': '亚洲情色'},
                    {'n': '日本有码', 'v': '日本有码'},
                    {'n': '日韩无码', 'v': '日韩无码'},
                    {'n': '成人动漫', 'v': '成人动漫'},
                    {'n': '重口色情', 'v': '重口色情'},
                ]
            }],
            '国产': [{
                'key': 'cat',
                'name': '子分类',
                'value': [
                    {'n': '网红主播', 'v': '网红主播'},
                    {'n': '国产自拍', 'v': '国产自拍'},
                    {'n': '国产情色', 'v': '国产情色'},
                    {'n': '吃瓜爆料', 'v': '吃瓜爆料'},
                    {'n': '麻豆传媒', 'v': '麻豆传媒'},
                    {'n': '萝莉少女', 'v': '萝莉少女'},
                    {'n': '三级伦理', 'v': '三级伦理'},
                    {'n': '国产丝袜', 'v': '国产丝袜'},
                ]
            }],
            '排行': [{
                'key': 'type',
                'name': '榜单类型',
                'value': [
                    {'n': '国产榜', 'v': 'guochan'},
                    {'n': '番号榜', 'v': 'fanhao'},
                ]
            }, {
                'key': 'time',
                'name': '时间',
                'value': [
                    {'n': '日榜', 'v': 'daily'},
                    {'n': '周榜', 'v': 'weekly'},
                    {'n': '月榜', 'v': 'monthly'},
                ]
            }],
            '专题': [{
                'key': 'region',
                'name': '视频区域',
                'value': [
                    {'n': '国产视频热门', 'v': '国产'},
                    {'n': '番号视频热门', 'v': '番号'},
                ]
            }, {
                'key': 'cat',
                'name': '专题',
                'value': [
                    {'n': '潮吹喷水', 'v': '潮吹喷水'},
                    {'n': '糖心vlog', 'v': '糖心vlog'},
                    {'n': '后入', 'v': '后入'},
                    {'n': '黑丝', 'v': '黑丝'},
                    {'n': '水果派', 'v': '水果派'},
                    {'n': '口爆吞精', 'v': '口爆吞精'},
                    {'n': '小宝寻花', 'v': '小宝寻花'},
                    {'n': '大学生', 'v': '大学生'},
                    {'n': '童颜巨乳', 'v': '童颜巨乳'},
                    {'n': '玩偶姐姐', 'v': '玩偶姐姐'},
                    {'n': '制服', 'v': '制服'},
                ]
            }],
        }

        self._classes = classes
        self._filters = filters
        return classes

    def _get_filters(self):
        if self._filters is None:
            self._load_classes()
        return self._filters or {}

    # ========== 首页 ==========
    def homeContent(self, filter=False):
        return {
            'class': self._load_classes(),
            'filters': self._get_filters(),
        }

    def homeVideoContent(self):
        now = int(time.time())
        if self._home_cache and now - self._home_cache_time < 300:
            return {'list': self._home_cache[:72]}

        videos = []
        seen = set()

        picks = [
            ('番号', '中文字幕'),
            ('国产', '麻豆传媒'),
            ('番号', '日韩无码'),
        ]
        for reg, cat in picks:
            if len(videos) >= 72:
                break
            try:
                url = f"{self.host}/video-list.html?reg={quote(reg, safe='')}&category={quote(cat, safe='')}&page=1"
                html = self._fetch_html(url, timeout=12)
                items = self._parse_videos(html)
                for v in items:
                    vid = v.get('vod_id')
                    if vid and vid not in seen:
                        seen.add(vid)
                        videos.append(v)
                    if len(videos) >= 72:
                        break
            except Exception:
                continue

        if len(videos) < 24:
            try:
                html = self._fetch_html(self.host + '/?site=lltdh&refer_host=obes.llt2-2.top', timeout=12)
                items = self._parse_videos(html)
                for v in items:
                    vid = v.get('vod_id')
                    if vid and vid not in seen:
                        seen.add(vid)
                        videos.append(v)
                    if len(videos) >= 72:
                        break
            except Exception:
                pass

        self._home_cache = videos[:72]
        self._home_cache_time = now
        return {'list': self._home_cache}

    # ========== 分类列表 ==========
    def categoryContent(self, tid, pg, filter=False, extend=None):
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

        if tid == '排行':
            ttype = ext.get('type', 'guochan')
            ttime = ext.get('time', 'daily')
            url = f"{self.host}/top.html?type={quote(ttype, safe='')}&time={quote(ttime, safe='')}"
            if pg > 1:
                url += f"&page={pg}"
            html = self._fetch_html(url, timeout=20)

        elif tid == '专题':
            keyword = ext.get('cat', '潮吹喷水')
            region = ext.get('region', '国产')
            url = f"{self.host}/search.html?q={quote(keyword, safe='')}&region={quote(region, safe='')}&order=latest"
            if pg > 1:
                url += f"&page={pg}"
            html = self._fetch_html(url, timeout=20)

        else:
            reg = tid if tid in ('番号', '国产') else '番号'
            cat = ext.get('cat', '')
            if not cat:
                cat = '中文字幕' if reg == '番号' else '麻豆传媒'
            url = f"{self.host}/video-list.html?reg={quote(reg, safe='')}&category={quote(cat, safe='')}&page={pg}"
            html = self._fetch_html(url, timeout=20)

        if not html:
            return {'list': [], 'page': pg, 'pagecount': 1, 'limit': 20, 'total': 0}

        videos = self._parse_videos(html)
        pagecount = self._get_pagecount(html)
        if not pagecount and videos:
            pagecount = 1

        return {
            'list': videos,
            'page': pg,
            'pagecount': pagecount or 1,
            'limit': 20,
            'total': len(videos) * (pagecount or 1),
        }

    # ========== 详情页 ==========
    def detailContent(self, ids):
        if isinstance(ids, str):
            ids = [ids]
        vid = ids[0]

        url = f"{self.host}/news/{vid}.html"
        html = self._fetch_html(url, timeout=20)

        if not html:
            return {'list': []}

        vod = self._parse_detail(html, vid)
        return {'list': [vod]}

    # ========== 搜索 ==========
    def searchContent(self, key, quick=False, pg='1'):
        pg = int(pg or 1)
        url = f"{self.host}/search.html?q={quote(key, safe='')}"
        if pg > 1:
            url += f"&page={pg}"

        html = self._fetch_html(url, timeout=20)
        videos = self._parse_videos(html)

        pagecount = self._get_pagecount(html)
        if not pagecount and videos:
            pagecount = 1

        return {
            'list': videos,
            'page': pg,
            'pagecount': pagecount or 1,
            'limit': 20,
            'total': len(videos) * (pagecount or 1),
        }

    # ========== 播放解析 ==========
    def playerContent(self, flag, id, vipFlags=None):
        if not id:
            return {"parse": 1, "url": ""}

        url = id if str(id).startswith('http') else self._url(id)

        if '.m3u8' in url:
            return {
                "parse": 0,
                "url": url,
                "header": {
                    'User-Agent': self.header['User-Agent'],
                    'Referer': self.host + '/',
                },
                'format': 'application/x-mpegURL',
            }

        if '.mp4' in url:
            return {
                "parse": 0,
                "url": url,
                "header": {
                    'User-Agent': self.header['User-Agent'],
                    'Referer': self.host + '/',
                },
            }

        return {"parse": 1, "url": url, "header": self.header}

    def localProxy(self, param):
        return [200, 'video/MP2T', b'', '']

    def isVideoFormat(self, url):
        url = str(url).lower()
        return '.m3u8' in url or '.mp4' in url or '.ts' in url or '.flv' in url

    def manualVideoCheck(self):
        return False

    def destroy(self):
        try:
            if hasattr(self, 'session'):
                self.session.close()
        except Exception:
            pass

    def close(self):
        self.destroy()