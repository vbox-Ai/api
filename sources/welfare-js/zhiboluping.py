# -*- coding: utf-8 -*-
import re, json, sys, ssl
from urllib.parse import quote, urlencode
try:
    from base.spider import Spider
except ImportError:
    import requests as rq

    class Spider:
        def fetch(self, url, headers=None, **kw):
            try:
                kw.setdefault('timeout', 15)
                r = rq.get(url, headers=headers, verify=False, **kw)
                r.encoding = 'utf-8'
                return r
            except Exception:
                try:
                    ctx = ssl.create_default_context()
                    ctx.check_hostname = False
                    ctx.verify_mode = ssl.CERT_NONE
                    req = __import__('urllib.request', fromlist=['Request', 'urlopen']).Request(url, headers=headers or {})
                    r = __import__('urllib.request', fromlist=['urlopen']).urlopen(req, timeout=15, context=ctx)
                    return type('R', (), {'text': r.read().decode('utf-8', 'ignore'), 'status_code': 200, 'content': b''})()
                except Exception:
                    return None

        def post(self, url, data, headers=None):
            try:
                r = rq.post(url, data=data, headers=headers, timeout=15, verify=False)
                r.encoding = 'utf-8'
                return r
            except Exception:
                try:
                    body = urlencode(data).encode()
                    ctx = ssl.create_default_context()
                    ctx.check_hostname = False
                    ctx.verify_mode = ssl.CERT_NONE
                    req = __import__('urllib.request', fromlist=['Request']).Request(url, data=body, headers=headers or {})
                    r = __import__('urllib.request', fromlist=['urlopen']).urlopen(req, timeout=15, context=ctx)
                    return type('R', (), {'text': r.read().decode('utf-8', 'ignore'), 'status_code': 200, 'content': b''})()
                except Exception:
                    return None


class Spider(Spider):
    host = 'https://www.lookluping.xyz'
    header = {
        'User-Agent': 'Mozilla/5.0 (Linux; Android 13; Pixel 7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Mobile Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
        'Accept-Language': 'zh-CN,zh;q=0.9',
    }
    classes = [
        {'type_name': '免费视频', 'type_id': 'free'},
    ]

    def getName(self):
        return '直播录屏'

    def init(self, extend=''):
        if isinstance(extend, list):
            self.extend = ''
        else:
            self.extend = extend or ''
        return {}

    def isVideoFormat(self, url):
        return any(x in url for x in ['.m3u8', '.mp4', '.flv', '.avi', '.mkv'])

    def manualVideoCheck(self):
        return False

    def destroy(self):
        pass

    def post(self, url, data, headers=None):
        try:
            import requests as rq
            r = rq.post(url, data=data, headers=headers, timeout=15, verify=False)
            r.encoding = 'utf-8'
            return r
        except Exception:
            try:
                ctx = ssl.create_default_context()
                ctx.check_hostname = False
                ctx.verify_mode = ssl.CERT_NONE
                body = urlencode(data).encode()
                req = __import__('urllib.request', fromlist=['Request']).Request(url, data=body, headers=headers or {})
                r = __import__('urllib.request', fromlist=['urlopen']).urlopen(req, timeout=15, context=ctx)
                return type('R', (), {'text': r.read().decode('utf-8', 'ignore'), 'status_code': 200, 'content': b''})()
            except Exception:
                return None

    def _fetch_html(self, path, data=None):
        url = path if path.startswith('http') else self.host + path
        try:
            if data is not None:
                r = self.post(url, data, headers=self.header)
            else:
                r = self.fetch(url, headers=self.header, timeout=15)
            if not r:
                return ''
            t = r.text if hasattr(r, 'text') else r.content.decode('utf-8', 'ignore')
            try:
                return t.encode('latin-1').decode('utf-8')
            except Exception:
                return t
        except Exception:
            return ''

    def _wrap_pic(self, pic):
        if not pic:
            return ''
        pic = pic.strip()
        if pic.startswith(('"', "'")) and pic.endswith(('"', "'")):
            pic = pic[1:-1]
        pic = pic.replace('&amp;', '&')
        if '127.0.0.1' in pic or 'proxy' in pic:
            return pic
        if pic.startswith('//'):
            pic = 'https:' + pic
        elif not pic.startswith(('http://', 'https://')):
            pic = (self.host + pic) if pic.startswith('/') else self.host + '/' + pic
        return pic

    def homeContent(self, filter):
        filters = {}
        for c in self.classes:
            filters[c['type_id']] = []
        return {'class': self.classes, 'filters': filters}

    def homeVideoContent(self):
        html = self._fetch_html('/')
        return {'list': self._items(html)[:48]}

    def categoryContent(self, tid, pg, filter, extend):
        try:
            pg = int(pg or 1)
            if pg < 1:
                pg = 1
            url = '/free/' if pg == 1 else '/free/index_%d.html' % pg
            html = self._fetch_html(url)
            if not html or '信息提示' in html[:2000]:
                return {'page': pg, 'pagecount': 1, 'limit': 24, 'total': 0, 'list': []}
            vod_list = self._items(html)
            pagecount = self._pagecount(html, pg)
            return {'page': pg, 'pagecount': pagecount, 'limit': len(vod_list), 'total': 48 * pagecount, 'list': vod_list}
        except Exception:
            return {'page': pg, 'pagecount': 1, 'limit': 24, 'total': 0, 'list': []}

    def detailContent(self, ids):
        try:
            vid = ids[0] if isinstance(ids, list) else str(ids)
            if vid.isdigit():
                aid = vid
                path = 'free/' + aid
            else:
                aid = re.search(r'(\d+)', vid).group(1) if re.search(r'(\d+)', vid) else vid
                path = vid.strip('/').rstrip('.html')
            html = self._fetch_html('/' + path + '.html')
            if not html or 'buyvideo' not in html:
                return {'list': []}
            vod = {'vod_id': vid}
            m = re.search(r'<h1[^>]*>([^<]+)</h1>', html)
            name = m.group(1).strip() if m else re.search(r'<title>([^<]*)</title>', html).group(1).strip()
            vod['vod_name'] = name
            m = re.search(r'<img[^>]+src="([^"]*?/video/[^"]+)"', html)
            if not m:
                m = re.search(r'<img[^>]+src="([^"]+)"', html)
            vod['vod_pic'] = self._wrap_pic(m.group(1) if m else '')
            vod['vod_remarks'] = ''
            vod['vod_actor'] = ''
            vod['vod_director'] = ''
            vod['type_name'] = '免费视频'
            vod['vod_year'] = ''
            vod['vod_area'] = ''
            vod['vod_content'] = name
            b = re.search(r'buyvideo" classid="(\d+)" xxid="(\d+)"', html)
            if not b:
                b = re.search(r'classid="(\d+)"[^>]*xxid="(\d+)"', html)
            cid = b.group(1) if b else '26'
            xid = b.group(2) if b else aid
            vod['vod_play_from'] = '直播录屏'
            vod['vod_play_url'] = self._series_url(name, vid, path, cid, xid)
            return {'list': [vod]}
        except Exception:
            return {'list': []}

    def _series_url(self, name, vid, path, cid, xid):
        mm = re.search(r'^(.*?)\s*\((\d+)\)\s*\.\w+$', name.strip())
        if not mm:
            return '正片$%s' % path
        sn = mm.group(1)
        cur = int(mm.group(2))
        series = {cur: path}
        for p in range(1, 6):
            url = '/free/' if p == 1 else '/free/index_%d.html' % p
            h = self._fetch_html(url)
            if not h or '信息提示' in h[:2000]:
                break
            for it in self._items(h):
                im = re.search(r'^(.*?)\s*\((\d+)\)\s*\.\w+$', it['vod_name'].strip())
                if im and im.group(1) == sn:
                    n = int(im.group(2))
                    if n not in series:
                        series[n] = it['vod_id']
            if len(series) >= 60:
                break
        eps = ['%s$%s' % (('第%d段' % n), p) for n, p in sorted(series.items())]
        return '#'.join(eps) if eps else '正片$%s' % path

    def searchContent(self, key, quick, pg=1):
        try:
            raw = str(key)
            items = []
            seen = set()
            for p in range(1, 6):
                url = '/free/' if p == 1 else '/free/index_%d.html' % p
                html = self._fetch_html(url)
                if not html:
                    continue
                if '信息提示' in html[:2000]:
                    break
                for it in self._items(html):
                    if raw.lower() not in it['vod_name'].lower():
                        continue
                    if it['vod_id'] in seen:
                        continue
                    seen.add(it['vod_id'])
                    items.append(it)
                if len(items) >= 80:
                    break
            return {'list': items[:80], 'page': 1}
        except Exception:
            return {'list': [], 'page': 1}

    def searchContentPage(self, key, quick, pg=1):
        return self.searchContent(key, quick, pg)

    def playerContent(self, flag, id, vipFlags):
        try:
            vid = str(id)
            if vid.isdigit():
                aid = vid
                path = 'free/' + aid
            else:
                aid = re.search(r'(\d+)', vid).group(1) if re.search(r'(\d+)', vid) else vid
                path = vid.strip('/').rstrip('.html')
            if not aid:
                return {}
            html = self._fetch_html('/' + path + '.html')
            if not html or 'buyvideo' not in html:
                return {}
            b = re.search(r'buyvideo" classid="(\d+)" xxid="(\d+)"', html)
            if not b:
                b = re.search(r'classid="(\d+)"[^>]*xxid="(\d+)"', html)
            cid = b.group(1) if b else '26'
            xid = b.group(2) if b else aid
            r = self._fetch_html('/e/moyublog/bofang/', {'id': xid, 'classid': cid})
            if not r:
                return {}
            try:
                obj = json.loads(r)
                nr = obj.get('nr', '') or ''
            except Exception:
                nr = r
            m = re.search(r'url:\s*["\']([^"\']+)["\']', nr)
            if m:
                return {'parse': 0, 'url': m.group(1).replace('\\/', '/'), 'header': {'Referer': self.host + '/', 'User-Agent': self.header['User-Agent']}}
            m = re.search(r'src\s*=\s*["\']?\s*\\?(/e/DownSys/play/[^"\']+)', nr)
            u = m.group(1).replace('\\/', '/').replace(' ', '') if m else ''
            if u.startswith('/'):
                u = self.host + u
            if not u:
                return {}
            fr = self._fetch_html(u)
            if not fr:
                return {}
            m = re.search(r'url:\s*["\']([^"\']+)["\']', fr)
            if not m:
                return {}
            return {'parse': 0, 'url': m.group(1).replace('\\/', '/'), 'header': {'Referer': self.host + '/', 'User-Agent': self.header['User-Agent']}}
        except Exception:
            return {}

    def localProxy(self, param):
        return []

    def _pagecount(self, html, pn=1):
        pages = [int(x) for x in re.findall(r'index_(\d+)\.html', html)]
        if pages:
            return max(pages)
        return pn + 5 if '下一页' in html or 'index_%d.html' % (pn + 1) in html else pn

    def _items(self, html):
        items = []
        seen = set()
        for m in re.finditer(r'<a href="([^"]*?/(\d+)\.html)"([^>]*)>(.*?)</a>', html, re.S):
            vid = m.group(2)
            path = m.group(1).strip('/')
            if not path.startswith('free/'):
                continue
            if vid in seen:
                continue
            t = re.search(r'title="([^"]*)"', m.group(3))
            name = t.group(1).strip() if t else re.sub(r'<[^>]+>', '', m.group(4)).strip()
            if not name or len(name) > 100:
                continue
            seen.add(vid)
            after = html[m.end():m.end() + 800]
            img = re.search(r'<img[^>]+(?:data-original|original|src)="([^"]+)"', after)
            pic = self._wrap_pic(img.group(1) if img else '')
            items.append({'vod_id': path, 'vod_name': name[:50], 'vod_pic': pic, 'vod_remarks': ''})
        return items