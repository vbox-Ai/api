# -*- coding: utf-8 -*-
"""
《藏姬阁》- vbox 福利专区 Python Spider (继承 base.spider.Spider)

适配 vbox 福利专区，自动享用：
- 自定义域名（_vbox_effective_hosts 注入 → self.host）
- 代理设置（_vbox_proxy_enabled / _vbox_proxy_url 注入 → fetch 自动走代理）
- 封面图代理（localProxy → /proxy?do=py 路由 → DoubanImageProxyServer）

站点: https://藏姬阁.com
类型: MacCMS v10
播放: mac_url unescape 解码 → m3u8/mp4 直链
"""
import sys
import re
import json
import html as ihtml
from urllib.parse import quote, urljoin, unquote

sys.path.append('..')

try:
    from base.spider import Spider as BaseSpider
except ImportError:
    import requests as _rq
    class BaseSpider:
        def fetch(self, url, headers=None, **kw):
            kw.pop('verify', None)
            kw.pop('timeout', None)
            return _rq.get(url, headers=headers, timeout=15, **kw)
        def post(self, url, headers=None, data=None, **kw):
            kw.pop('verify', None)
            kw.pop('timeout', None)
            return _rq.post(url, headers=headers, data=data, timeout=15, **kw)
        def init(self, extend=""):
            pass


class Spider(BaseSpider):
    name = '藏姬阁'
    HOST = 'https://xn--e2o-gocjgcom-nw8u993cql8elmwejgrb.cjggo.com'

    def __init__(self):
        try:
            super().__init__()
        except Exception:
            pass
        self.host = self.HOST
        self.timeout = 30
        self.CATEGORIES = (
            ('国产精品', '15'), ('原创偷拍', '13'), ('中文字幕', '20'),
            ('亚洲无码', '70'), ('亚洲有码', '603'), ('欧美精选', '30'),
            ('动漫卡通', '613'),
        )
        self.headers = {
            'User-Agent': ('Mozilla/5.0 (Linux; Android 11) AppleWebKit/537.36 '
                           'Chrome/120.0 Mobile Safari/537.36'),
            'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
        }

    def init(self, extend=''):
        try:
            super().init(extend)
        except Exception:
            pass
        config = extend if isinstance(extend, dict) else {}
        if not config and extend:
            try:
                config = json.loads(extend)
            except Exception:
                config = {}
        host = str(config.get('host') or config.get('siteUrl') or '').strip().rstrip('/')
        if host.startswith(('http://', 'https://')):
            self.host = host
        return None

    def getName(self):
        return self.name

    def getDependence(self):
        return []

    def homeLayout(self):
        return 0

    def destroy(self):
        pass

    def manualVideoCheck(self):
        return False

    def isVideoFormat(self, url):
        v = str(url or '').lower()
        return any(x in v for x in ('.m3u8', '.mp4', '.m4v', '.mpd', '.flv', '.webm', '.ts'))

    def _request(self, url, params=None, referer=None, post=False, data=None):
        """统一请求方法 — 使用 base.spider.fetch 自动处理 SSL/代理/域名注入"""
        headers = dict(self.headers)
        headers['Accept'] = 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8'
        if referer:
            headers['Referer'] = referer
        try:
            if post:
                r = self.post(url, headers=headers, data=data,
                              timeout=self.timeout, verify=False)
            else:
                r = self.fetch(url, headers=headers,
                               timeout=self.timeout, verify=False)
            if r is not None:
                try:
                    r.encoding = r.apparent_encoding or 'utf-8'
                except Exception:
                    pass
                return r
        except Exception as e:
            self._log('request fail %s: %s' % (url, e))
        return None

    def _log(self, msg):
        try:
            self.log('[%s] %s' % (self.name, msg))
        except Exception:
            print('[%s] %s' % (self.name, msg))

    @staticmethod
    def clean(s):
        return re.sub(r'\s+', ' ', ihtml.unescape(re.sub(r'<[^>]+>', '', s or ''))).strip()

    def _cards(self, html_text, base_url):
        """解析 item wrap-vid 卡片列表。"""
        vods = []
        for m in re.finditer(
                r'<div class="item wrap-vid[^"]*">(.*?)<h3 class="vid-name">(.*?)</h3>',
                html_text or '', re.S):
            head, tail = m.group(1), m.group(2)
            link = re.search(r'href="([^"]*/content/(\d+)\.html)"', head + tail)
            if not link:
                continue
            href, vid = link.group(1), link.group(2)
            title_m = re.search(r'title="([^"]*)"', head + tail)
            title = title_m.group(1) if title_m else ''
            if not title:
                tm = re.search(r'<a[^>]*>([^<]+)</a>', tail)
                if tm:
                    title = tm.group(1)
            img = re.search(r"background-image:\s*url\('([^']+)'\)", head + tail) or \
                  re.search(r'data-original="([^"]*)"', head + tail)
            dur = re.search(r'<span class="vodtime">([^<]*)</span>', head + tail)
            pic = urljoin(base_url, img.group(1)) if img else ''
            vods.append({
                'vod_id': vid,
                'vod_name': self.clean(title),
                'vod_pic': pic,
                'vod_remarks': self.clean(dur.group(1)) if dur else '',
            })
        seen, out = set(), []
        for v in vods:
            k = v['vod_id'] + '|' + v['vod_name']
            if k in seen:
                continue
            seen.add(k)
            out.append(v)
        return out

    def homeContent(self, filter=False):
        classes = [{'type_id': str(i), 'type_name': n} for n, i in self.CATEGORIES]
        return {'class': classes, 'filters': {}}

    def homeVideoContent(self):
        r = self._request(self.host + '/')
        return {'list': self._cards(r.text, r.url if r else self.host + '/') if r else []}

    def categoryContent(self, tid, pg, filter=False, extend=None):
        try:
            page = int(pg)
        except (ValueError, TypeError):
            page = 1
        if page < 1:
            page = 1
        url = '%s/list/%s%s.html' % (self.host, tid, '' if page == 1 else '-%s' % page)
        r = self._request(url)
        if not r:
            return {'list': [], 'page': page, 'pagecount': 1, 'limit': 24, 'total': 0}
        vods = self._cards(r.text, r.url)
        pc = self._pagecount(r.text, tid)
        return {'list': vods, 'page': page, 'pagecount': pc, 'limit': 24, 'total': 0}

    def _pagecount(self, html_text, tid):
        m = re.search(r'/list/%s(?:-\d+)?\.html[^>]*>\s*尾页' % re.escape(str(tid)), html_text)
        if m:
            href = re.search(r'/list/%s(?:-(\d+))?\.html' % re.escape(str(tid)), m.group(0))
            if href:
                try:
                    return max(1, int(href.group(1) or 1))
                except ValueError:
                    pass
        nums = [int(x) for x in re.findall(r'/list/%s-(\d+)\.html' % re.escape(str(tid)), html_text)]
        return max(nums) if nums else 1

    def detailContent(self, ids):
        vid = str(ids[0] if isinstance(ids, (list, tuple)) and ids else ids or '').strip()
        if not vid:
            return {'list': []}
        r = self._request('%s/content/%s.html' % (self.host, vid))
        if not r:
            return {'list': []}
        return {'list': [self._detail(r.text, vid, r.url)]}

    def _detail(self, html_text, vid, base_url):
        title = ''
        tm = re.search(r'<h1[^>]*>([\s\S]*?)</h1>', html_text) or \
             re.search(r'<title>.*?([\s\S]*?)</title>', html_text)
        if tm:
            title = self.clean(tm.group(1))
        if not title or title.startswith('正在播放'):
            tm2 = re.search(r'<h3 class="vid-name"[^>]*>\s*<a[^>]*title="([^"]*)"', html_text)
            title = self.clean(tm2.group(1)) if tm2 else title
        img = re.search(r"postimg\s*=\s*'([^']+)'", html_text) or \
              re.search(r"background-image:\s*url\('([^']+)'\)", html_text) or \
              re.search(r'<img[^>]+(?:src|data-original)="([^"]+\.(?:jpg|png|webp))"', html_text)
        play_from = '在线播放'
        play_url = ''
        mu = re.search(r"var\s+mac_url\s*=\s*unescape\('([^']+)'\)", html_text)
        if mu:
            decoded = unquote(mu.group(1))
            parts = decoded.split('#')
            pairs = []
            for p in parts:
                if '$' in p:
                    n, u = p.split('$', 1)
                    pairs.append((n.strip(), u.strip()))
            if pairs:
                play_url = '#'.join('%s$%s' % (n, u) for n, u in pairs)
        else:
            mu2 = re.search(r'(https?://[^\s\'"]+\.(?:m3u8|mp4|mpd|flv)[^\s\'"]*)', html_text)
            if mu2:
                play_url = '第1集$%s' % mu2.group(1)
        return {
            'vod_id': vid,
            'vod_name': title or vid,
            'vod_pic': urljoin(base_url or self.host + '/', img.group(1)) if img else '',
            'vod_content': '',
            'vod_type_name': '',
            'vod_play_from': play_from if play_url else '',
            'vod_play_url': play_url,
        }

    def searchContent(self, key, quick=False, pg='1'):
        keyword = str(key or '').strip()
        try:
            page = int(pg)
        except (ValueError, TypeError):
            page = 1
        if page < 1:
            page = 1
        vods = []
        found = False
        for path in ['/search.php?searchtype=5&wd=%s' % quote(keyword),
                     '/index.php/vod/search.html?wd=%s' % quote(keyword),
                     '/?wd=%s' % quote(keyword)]:
            r = self._request(self.host + path)
            if r:
                cand = self._cards(r.text, r.url)
                if cand:
                    vods = cand
                    found = True
                    break
        if not found:
            r = self._request(self.host + '/')
            if r:
                allv = self._cards(r.text, r.url)
                vods = [v for v in allv if keyword in v['vod_name']]
        return {'list': vods, 'page': page, 'pagecount': 1, 'limit': 24, 'total': 0}

    def playerContent(self, flag, id, vipFlags=None):
        url = str(id or '').strip()
        if not url:
            return {'parse': 0, 'url': '', 'header': {}}
        if self.isVideoFormat(url):
            return {'parse': 0, 'url': url,
                    'header': {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)',
                               'Referer': self.host + '/'}}
        if re.search(r'/content/\d+\.html', url):
            vid = re.search(r'/content/(\d+)\.html', url).group(1)
            r = self._request('%s/content/%s.html' % (self.host, vid))
            if r:
                mu = re.search(r"var\s+mac_url\s*=\s*unescape\('([^']+)'\)", r.text)
                if mu:
                    decoded = unquote(mu.group(1))
                    mm = re.search(r'(https?://[^\s\'"]+\.(?:m3u8|mp4|mpd|flv)[^\s\'"]*)', decoded)
                    if mm:
                        return {'parse': 0, 'url': mm.group(1),
                                'header': {'User-Agent': 'Mozilla/5.0', 'Referer': self.host + '/'}}
        return {'parse': 1, 'url': url, 'header': {}}

    def localProxy(self, param):
        """本地代理 — 图片防盗链处理

        通过 getProxyUrl() 生成代理 URL，vbox 的 DoubanImageProxyServer
        会拦截 /proxy?do=py 请求并调用此方法。
        """
        _p = param if isinstance(param, dict) else {}
        url = unquote(_p.get('url', '')) or ''
        if not url:
            return None
        try:
            resp = self.fetch(url, headers={
                'User-Agent': self.headers.get('User-Agent'),
                'Referer': self.host + '/'
            }, timeout=15, verify=False)
            if resp is None:
                return None
            ct = 'image/jpeg'
            if hasattr(resp, 'headers'):
                ct = resp.headers.get('Content-Type', 'image/jpeg')
            content = resp.content if hasattr(resp, 'content') else b''
            return [200, ct, content]
        except Exception:
            return None
