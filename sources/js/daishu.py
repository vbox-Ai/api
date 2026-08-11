# -*- coding: utf-8 -*-
# ============================================================
# 袋鼠影视 Python 蜘蛛
# 站点: https://dsystv.com
# 适配 vbox iOS CPython:
#   - 使用 urllib + 不验证 SSL 上下文，避免 iOS CA 证书问题
#   - 播放地址使用 daishu:// 包装，只让本脚本优先解析播放页
#   - playerContent 提取播放页 var now / player_data / m3u8/mp4 直链
# ============================================================

import sys
import re
import json
import ssl
import base64
import urllib.request
import urllib.error
from urllib.parse import quote, unquote, urljoin
from html import unescape

sys.path.append('..')

_ssl_ctx = ssl._create_unverified_context()

try:
    from base.spider import Spider as _BaseSpider
except ImportError:
    _BaseSpider = object


class _Response:
    def __init__(self, content_bytes, status_code=200, encoding='utf-8', headers=None):
        self.content = content_bytes
        self.status_code = status_code
        self.encoding = encoding
        self.headers = headers
        try:
            self.text = content_bytes.decode(encoding, errors='replace')
        except Exception:
            self.text = ''


class Spider(_BaseSpider):
    host = 'https://dsystv.com'
    _backup_hosts = [
        'https://www.dsystv.com',
    ]

    ua = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'

    classes = [
        {'type_id': '1', 'type_name': '电影'},
        {'type_id': '2', 'type_name': '电视剧'},
        {'type_id': '3', 'type_name': '综艺'},
        {'type_id': '4', 'type_name': '动漫'},
        {'type_id': '44', 'type_name': '短剧'},
    ]

    def getName(self):
        return '袋鼠影视'

    def init(self, extend=''):
        try:
            if extend:
                if isinstance(extend, dict):
                    ext = extend
                else:
                    text = str(extend).strip()
                    ext = json.loads(text) if text.startswith('{') else {'site': text}
                site = ext.get('site') or ext.get('host') or ''
                if site:
                    self.host = str(site).split(',')[0].strip().rstrip('/')
        except Exception:
            pass
        print('[袋鼠影视] init 完成, host=%s' % self.host)
        return None

    def fetch(self, url, headers=None, **kw):
        timeout = kw.get('timeout', 12)
        req = urllib.request.Request(url, headers=headers or self._headers())
        try:
            r = urllib.request.urlopen(req, timeout=timeout, context=_ssl_ctx)
            data = r.read()
            resp_headers = r.headers if hasattr(r, 'headers') else None
            encoding = 'utf-8'
            if resp_headers and hasattr(resp_headers, 'get_content_charset'):
                ct_encoding = resp_headers.get_content_charset()
                if ct_encoding:
                    encoding = ct_encoding
            return _Response(data, status_code=getattr(r, 'status', 200), encoding=encoding, headers=resp_headers)
        except urllib.error.HTTPError as e:
            data = b''
            try:
                data = e.read()
            except Exception:
                pass
            resp_headers = e.headers if hasattr(e, 'headers') else None
            encoding = 'utf-8'
            if resp_headers and hasattr(resp_headers, 'get_content_charset'):
                ct_encoding = resp_headers.get_content_charset()
                if ct_encoding:
                    encoding = ct_encoding
            return _Response(data, status_code=e.code, encoding=encoding, headers=resp_headers)
        except Exception as e:
            print('[袋鼠影视] fetch 异常: %s, url=%s' % (e, str(url)[:100]))
            raise

    def isVideoFormat(self, url):
        return bool(re.search(r'\.(m3u8|mp4|flv|m4v|ts|webm|mkv|avi|mov)(\?|#|$|\s)', str(url or ''), re.I))

    def manualVideoCheck(self):
        return False

    def destroy(self):
        pass

    def localProxy(self, param):
        return [404, 'text/plain', '', {}]

    def homeContent(self, filter):
        html = self._html('/')
        classes = self._parse_categories(html) or self.classes
        return {'class': classes, 'filters': {}}

    def homeVideoContent(self):
        html = self._html('/')
        return {'list': self._parse_list(html)[:30]}

    def categoryContent(self, tid, pg, filter, extend):
        try:
            page = int(pg or 1)
        except Exception:
            page = 1
        if page <= 1:
            path = '/frim/index%s.html' % tid
        else:
            path = '/search.php?searchtype=5&tid=%s&page=%d' % (tid, page)
        html = self._html(path)
        vods = self._parse_list(html)
        return {
            'page': page,
            'pagecount': page + 1 if vods else page,
            'limit': len(vods) if vods else 24,
            'total': page * (len(vods) if vods else 24),
            'list': vods,
        }

    def detailContent(self, ids):
        try:
            vod_id = ids[0] if isinstance(ids, list) else str(ids)
            m = re.search(r'(\d+)', str(vod_id))
            if not m:
                return {'list': []}
            vid = m.group(1)
            html = self._html('/movie/index%s.html' % vid)
            if not html:
                return {'list': []}

            name = self._clean(self._match(html, r'<h1[^>]*>(.*?)</h1>') or self._match(html, r'<meta property=["\']og:title["\'] content=["\'](.*?)["\']'))
            name = name.replace('全集在线观看 - 国产剧 | 袋鼠影视', '').replace('全集在线观看 - 袋鼠影视', '').replace('《', '').replace('》', '').strip()
            pic = self._fix_url(
                self._match(html, r'<meta property=["\']og:image["\'] content=["\'](.*?)["\']')
                or self._match(html, r'<a[^>]+class=["\'][^"\']*videopic[^"\']*["\'][\s\S]*?<img[^>]+(?:data-original|data-src)=["\']([^"\']+)')
                or self._match(html, r'<a[^>]+class=["\'][^"\']*videopic[^"\']*["\'][\s\S]*?<img[^>]+src=["\']([^"\']+)')
            )
            desc = self._clean(self._match(html, r'<div class=["\']plot["\'][^>]*>\s*<p>(.*?)</p>') or self._match(html, r'<meta property=["\']og:description["\'] content=["\'](.*?)["\']'))
            actor = self._clean(self._match(html, r'<li[^>]+data-video-meta=["\']([^"\']*)["\'][^>]*><span class=["\']text-muted["\']>主演：'))
            director = self._clean(self._match(html, r'<li[^>]+data-video-meta=["\']([^"\']*)["\'][^>]*><span class=["\']text-muted["\']>导演：'))
            year = self._clean(self._match(html, r'年份：</span>([^<]+)'))
            area = self._clean(self._match(html, r'地区：</span>([^<]+)'))
            lang = self._clean(self._match(html, r'语言：</span>([^<]+)'))
            cate = self._clean(self._match(html, r'类型：</span><a[^>]*>(.*?)</a>'))
            remarks = self._clean(self._match(html, r'<span class=["\']note textbg["\']>(.*?)</span>'))

            play_from, play_url = self._parse_play_lists(html, vid)

            return {'list': [{
                'vod_id': vid,
                'vod_name': name,
                'vod_pic': pic,
                'vod_remarks': remarks,
                'type_name': cate,
                'vod_year': year,
                'vod_area': area,
                'vod_lang': lang,
                'vod_actor': actor,
                'vod_director': director,
                'vod_content': desc,
                'vod_play_from': '$$$'.join(play_from),
                'vod_play_url': '$$$'.join(play_url),
            }]}
        except Exception as e:
            print('[袋鼠影视] 详情异常: %s' % e)
            return {'list': []}

    def searchContent(self, key, quick, pg):
        return self.searchContentPage(key, quick, pg)

    def searchContentPage(self, key, quick, pg):
        try:
            page = int(pg or 1)
        except Exception:
            page = 1
        keyword = str(key or '').strip()
        html = ''

        try:
            headers = self._headers()
            headers['Content-Type'] = 'application/x-www-form-urlencoded'
            data = ('searchword=' + quote(keyword)).encode('utf-8')
            url = self.host + '/search.php'
            req = urllib.request.Request(url, data=data, headers=headers, method='POST')
            r = urllib.request.urlopen(req, timeout=12, context=_ssl_ctx)
            html = r.read().decode('utf-8', errors='replace')
        except Exception as e:
            print('[袋鼠影视] POST 搜索失败: %s' % e)

        vods = self._parse_list(html)
        if not vods:
            html = self._html('/search.php?searchword=%s&page=%d' % (quote(keyword), page))
            vods = self._parse_list(html)

        return {
            'page': page,
            'pagecount': page + 1 if vods else page,
            'limit': len(vods) if vods else 20,
            'total': page * (len(vods) if vods else 20),
            'list': vods,
        }

    def playerContent(self, flag, id, vipFlags):
        play_id = str(id or '').strip()
        play_url = self._unwrap_play_id(play_id)
        headers = {
            'User-Agent': self.ua,
            'Referer': self.host + '/',
        }
        if not play_url:
            return {'parse': 0, 'jx': 0, 'url': '', 'header': json.dumps(headers)}

        if self.isVideoFormat(play_url):
            return {'parse': 0, 'jx': 0, 'url': play_url, 'header': json.dumps(headers)}

        try:
            html = self._html(play_url)
            final_url = self._extract_play_url(html)
            if not final_url:
                final_url = play_url
            final_url = self._fix_url(final_url)
            is_direct = self.isVideoFormat(final_url)
            print('[袋鼠影视] 播放解析: direct=%s, url=%s' % (is_direct, final_url[:100]))
            return {
                'parse': 0 if is_direct else 1,
                'jx': 0 if is_direct else 1,
                'url': final_url,
                'header': json.dumps(headers),
            }
        except Exception as e:
            print('[袋鼠影视] 播放异常: %s' % e)
            return {'parse': 1, 'jx': 1, 'url': play_url, 'header': json.dumps(headers)}

    def _headers(self, referer=''):
        return {
            'User-Agent': self.ua,
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            'Accept-Language': 'zh-CN,zh;q=0.9',
            'Referer': referer or (self.host + '/'),
            'Origin': self.host,
        }

    def _html(self, url, timeout=12):
        full = url if str(url).startswith('http') else urljoin(self.host + '/', str(url).lstrip('/'))
        r = self.fetch(full, headers=self._headers(), timeout=timeout)
        text = getattr(r, 'text', '') or ''
        if r.status_code >= 400:
            print('[袋鼠影视] HTTP %s: %s' % (r.status_code, full[:100]))
        return text

    def _fix_url(self, url):
        url = unescape(str(url or '').strip())
        if not url:
            return ''
        if url.startswith('//'):
            return 'https:' + url
        if url.startswith('/'):
            return urljoin(self.host + '/', url.lstrip('/'))
        return url

    def _clean(self, text):
        text = unescape(str(text or ''))
        text = re.sub(r'<[^>]+>', ' ', text)
        text = text.replace('&nbsp;', ' ')
        return re.sub(r'\s+', ' ', text).strip()

    def _match(self, text, pattern):
        m = re.search(pattern, text or '', re.S | re.I)
        return m.group(1) if m else ''

    def _parse_categories(self, html):
        classes, seen = [], set()
        for tid, name in re.findall(r'<a[^>]+href=["\']/frim/index(\d+)\.html["\'][^>]*>(.*?)</a>', html or '', re.S | re.I):
            if tid in seen:
                continue
            seen.add(tid)
            name = self._clean(name)
            if name:
                classes.append({'type_id': tid, 'type_name': name})
        return classes

    def _parse_list(self, html):
        vods, seen = [], set()
        if not html:
            return vods

        pattern = r'<a[^>]+class=["\'][^"\']*videopic[^"\']*["\'][^>]+href=["\']/movie/index(\d+)\.html["\'][^>]*title=["\']([^"\']+)["\']([\s\S]{0,1200}?)</a>'
        for vid, title, tail in re.findall(pattern, html, re.S | re.I):
            if vid in seen:
                continue
            seen.add(vid)
            item_html = tail
            pic = ''
            m = re.search(r'(?:data-original|data-src)=["\']([^"\']+\.(?:jpg|jpeg|png|webp|gif)[^"\']*)["\']', item_html, re.I)
            if not m:
                m = re.search(r'src=["\']([^"\']+\.(?:jpg|jpeg|png|webp|gif)[^"\']*)["\']', item_html, re.I)
            if m:
                p = m.group(1)
                if all(x not in p for x in ('load.gif', 'nopic', 'logo', 'templets')):
                    pic = self._fix_url(p)
            remarks = self._clean(
                self._match(item_html, r'<span[^>]+class=["\'][^"\']*note[^"\']*["\'][^>]*>(.*?)</span>')
                or self._match(item_html, r'<span[^>]+class=["\'][^"\']*textbg[^"\']*["\'][^>]*>(.*?)</span>')
            )
            name = self._clean(title)
            if name:
                vods.append({'vod_id': str(vid), 'vod_name': name, 'vod_pic': pic, 'vod_remarks': remarks, 'vod_year': '', 'vod_area': ''})

        if vods:
            return vods

        pattern2 = r'href=["\']/movie/index(\d+)\.html["\'][^>]*title=["\']([^"\']+)["\'][\s\S]{0,1200}?<img[^>]+([^>]+)>'
        for vid, title, img_attr in re.findall(pattern2, html, re.S | re.I):
            if vid in seen:
                continue
            seen.add(vid)
            pic = self._match(img_attr, r'(?:data-original|data-src)=["\']([^"\']+)["\']') or self._match(img_attr, r'src=["\']([^"\']+)["\']')
            if 'load.gif' in pic or 'templets' in pic:
                pic = ''
            name = self._clean(title)
            if name:
                vods.append({'vod_id': str(vid), 'vod_name': name, 'vod_pic': self._fix_url(pic), 'vod_remarks': '', 'vod_year': '', 'vod_area': ''})
        return vods

    def _parse_play_lists(self, html, vid):
        tabs = [self._clean(x) for x in re.findall(r'<a class=["\']option["\'][\s\S]*?title=["\']([^"\']+)["\'][\s\S]*?</a>', html or '', re.S | re.I)]
        panels = re.findall(r'<div[^>]+class=["\']playlist[^"\']*["\'][^>]*>\s*<ul[^>]*>([\s\S]*?)</ul>', html or '', re.S | re.I)
        play_from, play_url = [], []

        for idx, panel in enumerate(panels):
            eps = []
            for title, href in re.findall(r'<a[^>]+title=["\']([^"\']+)["\'][^>]+href=["\']([^"\']*?/play/[^"\']+)["\']', panel, re.S | re.I):
                title = self._clean(title)
                href = self._fix_url(href)
                if title and href:
                    eps.append('%s$%s' % (title, self._wrap_play_url(href)))
            if not eps:
                for href, title in re.findall(r'<a[^>]+href=["\']([^"\']*?/play/[^"\']+)["\'][^>]*>(.*?)</a>', panel, re.S | re.I):
                    title = self._clean(title)
                    href = self._fix_url(href)
                    if title and href:
                        eps.append('%s$%s' % (title, self._wrap_play_url(href)))
            if eps:
                name = tabs[idx] if idx < len(tabs) and tabs[idx] else '线路%s' % (idx + 1)
                if name not in play_from:
                    play_from.append(name)
                    play_url.append('#'.join(eps))

        if not play_url:
            eps = []
            fb = r'<a[^>]+href=["\']([^"\']*?/play/%s-[^"\']+)["\'][^>]*>(.*?)</a>' % re.escape(str(vid))
            for href, title in re.findall(fb, html or '', re.S | re.I):
                title = self._clean(title) or '播放'
                href = self._fix_url(href)
                if title and href:
                    eps.append('%s$%s' % (title, self._wrap_play_url(href)))
            if eps:
                play_from.append('默认')
                play_url.append('#'.join(eps))

        return play_from, play_url

    def _wrap_play_url(self, url):
        return 'daishu://' + quote(url, safe='')

    def _unwrap_play_id(self, play_id):
        if play_id.startswith('daishu://'):
            return unquote(play_id[len('daishu://'):])
        return play_id

    def _extract_play_url(self, html):
        if not html:
            return ''

        play_url = self._match(html, r'var\s+now\s*=\s*["\']([^"\']+)["\']')
        if play_url:
            play_url = unquote(play_url)
            return self._decode_maybe(play_url)

        data_text = self._match(html, r'var\s+player_?data\s*=\s*(\{[\s\S]*?\})\s*[;<]')
        if data_text:
            try:
                data = json.loads(data_text)
                url = data.get('url') or data.get('play_url') or ''
                encrypt = int(data.get('encrypt') or 0)
                if encrypt == 1:
                    return unquote(url)
                if encrypt == 2:
                    return base64.b64decode(url).decode('utf-8', errors='replace')
                return self._decode_maybe(url)
            except Exception:
                pass

        for pattern in (
            r'(https?://[^"\'<>\s]+\.m3u8[^"\'<>\s]*)',
            r'(https?://[^"\'<>\s]+\.mp4[^"\'<>\s]*)',
            r'source\s*:\s*["\']([^"\']+)["\']',
            r'url\s*:\s*["\']([^"\']+)["\']',
        ):
            url = self._match(html, pattern)
            if url:
                return self._decode_maybe(url)
        return ''

    def _decode_maybe(self, url):
        url = unescape(str(url or '').strip())
        if not url:
            return ''
        try:
            url = unquote(url)
        except Exception:
            pass
        if re.match(r'^[A-Za-z0-9+/=]{20,}$', url or ''):
            try:
                decoded = base64.b64decode(url).decode('utf-8', errors='replace').strip()
                if decoded.startswith('http'):
                    return decoded
            except Exception:
                pass
        return url
