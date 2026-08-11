# -*- coding: utf-8 -*-
# ============================================================
# 大马猴影视 - x-client播放线路修复版
# 适配绿豆 TVBox / OK影视 / 影视仓 / WebHome
# 分类接口: /api.php/web/filter/vod?type_id=23/22/24/25&page=1&sort=hits
# 详情接口: /api.php/web/vod/get_detail?vod_id=xxx
# 聚合线路: /api.php/web/internal/search_aggregate?vod_id=xxx  优先提取 m3u8 直链
# ============================================================
# vbox iOS CPython 适配:
#   - 覆写 fetch 方法，使用 ssl._create_unverified_context()
#     解决 iOS CPython 无系统 CA 证书导致 HTTPS 请求失败
#   - 移除 x_client 占位符，避免假 header 导致聚合接口拒绝
#   - homeContent 始终返回 filters
#   - 新增备份域名 + 探测超时降至 5 秒
#   - 关键路径加 print 日志，便于悬浮窗诊断
# ============================================================

import sys
import json
import re
import time
import ssl
import urllib.request
import urllib.error
from urllib.parse import urlencode, quote
from html.parser import HTMLParser

sys.path.append('..')

# iOS CPython 没有 CA 证书 → HTTPS 验证失败
# 创建不验证证书的 SSL 上下文 (与 requests verify=False 等效)
_ssl_ctx = ssl._create_unverified_context()

try:
    from base.spider import Spider as _BaseSpider
except ImportError:
    _BaseSpider = object


class _HTMLTextExtractor(HTMLParser):
    def __init__(self):
        super().__init__()
        self._text = []

    def handle_data(self, data):
        self._text.append(data)

    def get_text(self):
        return ''.join(self._text)


class _Response:
    """HTTP 响应对象 — 兼容 requests 库的常用属性"""
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
    host = 'https://dmhyy.com'

    _backup_hosts = [
        'https://www.dmhyy.com',
        'https://dmhyy.net',
        'https://www.dmhyy.net',
    ]

    _last_host_check = 0
    _host_cache_ttl = 1800

    # 大马猴真实分类 ID 来自网页 /type/xx 和 XHR 返回：
    # /type/23 电影，/type/22 剧集，/type/24 动漫，/type/25 综艺
    classes = [
        {'type_id': '23', 'type_name': '电影'},
        {'type_id': '22', 'type_name': '剧集'},
        {'type_id': '24', 'type_name': '动漫'},
        {'type_id': '25', 'type_name': '综艺'},
    ]

    # 子分类筛选（当前无子分类数据，返回空 dict 保证 UI 不报错）
    filters = {}

    web_sign = ''
    # x_client: 移除占位符，不发送假 header
    # 如需启用聚合线路，通过 ext 传入真实 x_client
    x_client = ''

    # ==================== HTTP 请求 (覆写 base.spider) ====================

    def fetch(self, url, headers=None, **kw):
        """发起 HTTP GET 请求 — 覆写 base.spider.fetch
        使用 ssl._create_unverified_context() 绕过 iOS CA 证书缺失问题
        返回兼容 requests 风格的 Response 对象
        """
        timeout = kw.get('timeout', 12)
        req = urllib.request.Request(url, headers=headers or {})
        try:
            r = urllib.request.urlopen(req, timeout=timeout, context=_ssl_ctx)
            data = r.read()
            resp_headers = r.headers if hasattr(r, 'headers') else None
            encoding = 'utf-8'
            if resp_headers and hasattr(resp_headers, 'get_content_charset'):
                ct_encoding = resp_headers.get_content_charset()
                if ct_encoding:
                    encoding = ct_encoding
            return _Response(data, status_code=r.status, encoding=encoding, headers=resp_headers)
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
            print('[大马猴] fetch 异常: %s, url=%s' % (e, url[:100]))
            raise

    # ==================== 动态域名 ====================

    def _ensure_host(self):
        now = time.time()
        if now - self._last_host_check < self._host_cache_ttl:
            return self.host
        self._last_host_check = now
        for h in [self.host] + self._backup_hosts:
            try:
                r = self.fetch(h, headers=self._headers(), timeout=5)
                text = r.text if hasattr(r, 'text') else ''
                if r.status_code == 200 and ('大马猴' in text or 'dmhyy' in text or 'vod' in text):
                    self.host = h.rstrip('/')
                    print('[大马猴] 域名探测成功: %s' % self.host)
                    return self.host
            except Exception as e:
                print('[大马猴] 域名探测失败: %s, err=%s' % (h, e))
        print('[大马猴] 所有域名探测失败，使用默认: %s' % self.host)
        return self.host

    def _ensure_ready(self):
        if not getattr(self, 'host', ''):
            self.host = 'https://dmhyy.com'
        self.host = self.host.rstrip('/')

    # ==================== 基础方法 ====================

    def getName(self):
        return '大马猴影视'

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
                self.web_sign = ext.get('web-sign') or ext.get('web_sign') or self.web_sign
                self.x_client = ext.get('x-client') or ext.get('x_client') or self.x_client
        except Exception:
            pass
        print('[大马猴] init 完成, host=%s, x_client=%s' % (self.host, '有' if self.x_client else '无'))
        return None

    def isVideoFormat(self, url):
        return bool(re.search(r'\.(m3u8|mp4|flv|mkv|avi)(\?|#|$|\s)', str(url or ''), re.I))

    def manualVideoCheck(self):
        return False

    def localProxy(self, param):
        return None

    def destroy(self):
        pass

    # ==================== HTTP 辅助 ====================

    def _headers(self, referer=''):
        self._ensure_ready()
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/149.0.0.0 Safari/537.36',
            'Accept': 'application/json, text/plain, */*',
            'Accept-Language': 'zh-CN,zh;q=0.9',
            'Referer': referer or (self.host + '/'),
            'x-platform': 'web',
            'x-requested-with': 'XMLHttpRequest',
        }
        # 只在 x_client 有真实值时才带 (移除占位符)
        if getattr(self, 'x_client', '') and self.x_client != 'YOUR_PUBLIC_CLIENT_ID':
            headers['x-client'] = self.x_client
        if getattr(self, 'web_sign', ''):
            headers['web-sign'] = self.web_sign
        return headers

    def _api_get(self, path, params=None, referer=''):
        self._ensure_ready()
        params = params or {}
        qs = urlencode(params, doseq=True)
        url = self.host + path + (('?' + qs) if qs else '')
        try:
            r = self.fetch(url, headers=self._headers(referer), timeout=12)
            text = getattr(r, 'text', '') or getattr(r, 'content', b'')
            if isinstance(text, bytes):
                text = text.decode('utf-8', errors='ignore')
            if not text:
                return {}
            return json.loads(text)
        except Exception as e:
            print('[大马猴] 接口请求失败: %s, params=%s, err=%s' % (path, params, e))
            return {}

    def _clean_text(self, s):
        s = str(s or '')
        s = re.sub(r'<[^>]+>', ' ', s)
        s = s.replace('&nbsp;', ' ')
        return re.sub(r'\s+', ' ', s).strip()

    def _html2text(self, html):
        try:
            p = _HTMLTextExtractor()
            p.feed(str(html or ''))
            return self._clean_text(p.get_text())
        except Exception:
            return self._clean_text(html)

    def _as_list(self, data):
        if isinstance(data, list):
            return data
        if isinstance(data, dict):
            for k in ('data', 'list', 'items', 'records', 'rows', 'vod_list'):
                v = data.get(k)
                if isinstance(v, list):
                    return v
                if isinstance(v, dict):
                    vv = self._as_list(v)
                    if vv:
                        return vv
        return []

    def _vod_item(self, item):
        if not isinstance(item, dict):
            return None
        vid = item.get('vod_id') or item.get('id') or item.get('vodId')
        name = item.get('vod_name') or item.get('name') or item.get('title')
        if not vid or not name:
            return None
        area = item.get('vod_area', '')
        cls = item.get('vod_class', '')
        if isinstance(area, list):
            area = ','.join([str(x) for x in area if x])
        if isinstance(cls, list):
            cls = ','.join([str(x) for x in cls if x])
        return {
            'vod_id': str(vid),
            'vod_name': self._clean_text(name),
            'vod_pic': str(item.get('vod_pic') or item.get('pic') or item.get('cover') or ''),
            'vod_remarks': str(item.get('vod_remarks') or item.get('remarks') or item.get('vod_douban_score') or item.get('vod_year') or ''),
            'vod_year': str(item.get('vod_year') or ''),
            'type_name': self._clean_text(item.get('type_name') or cls or ''),
            'vod_area': self._clean_text(area),
        }

    def _vod_list(self, data):
        arr = self._as_list(data)
        out = []
        seen = set()
        for item in arr:
            v = self._vod_item(item)
            if not v:
                continue
            if v['vod_id'] in seen:
                continue
            seen.add(v['vod_id'])
            out.append(v)
        return out

    def _category_match(self, item, real_tid):
        """大马猴的接口即使传 type_id=22，也会混入电影/动漫/综艺。
        所以必须在脚本内按真实 type_id/type_name 再过滤一次，避免所有分类显示相同内容。
        """
        if not isinstance(item, dict):
            return False
        real_tid = str(real_tid)
        item_tid = str(item.get('type_id') or item.get('typeId') or item.get('tid') or '')
        if item_tid == real_tid:
            return True
        name = str(item.get('type_name') or '')
        class_value = item.get('vod_class') or []
        if isinstance(class_value, list):
            cls = ','.join([str(x) for x in class_value if x])
        else:
            cls = str(class_value or '')
        text = name + ',' + cls
        if real_tid == '23':
            return ('电影' in text or '动作片' in text or '剧情片' in text or '喜剧片' in text) and '电视剧' not in text
        if real_tid == '22':
            return any(k in text for k in ('剧集', '电视剧', '国产剧', '连续剧', '韩剧', '陆剧', '欧美剧', '日剧'))
        if real_tid == '24':
            return '动漫' in text or '动画' in text or '国产动漫' in text or '日韩动漫' in text
        if real_tid == '25':
            return '综艺' in text or '真人秀' in text
        return True

    def _filter_items_by_category(self, data, real_tid):
        arr = self._as_list(data)
        return [x for x in arr if self._category_match(x, real_tid)]

    # ==================== 首页 ====================

    def homeContent(self, filter):
        result = {'class': self.classes}
        result['filters'] = self.filters  # 始终返回 filters
        return result

    def homeVideoContent(self):
        try:
            j = self._api_get('/api.php/web/filter/vod', {
                'type_id': '23',
                'page': '1',
                'sort': 'hits'
            }, self.host + '/type/23')
            vods = self._vod_list(j)
            print('[大马猴] 首页推荐: %d条' % len(vods))
            return {'list': vods}
        except Exception as e:
            print('[大马猴] 首页推荐异常: %s' % e)
            return {'list': []}

    # ==================== 分类 ====================

    def categoryContent(self, tid, pg, filter, extend):
        self._ensure_ready()
        page = str(pg or '1')
        sort = 'hits'
        if isinstance(extend, dict):
            sort = extend.get('sort') or extend.get('by') or sort

        # 真实 XHR 分类接口。注意大马猴不是 1/2/3/4，而是 23/22/24/25。
        # 这里保留一个兼容映射，防止旧配置或壳缓存还传入 1/2/3/4。
        tid_map = {'1': '23', '2': '22', '3': '24', '4': '25'}
        real_tid = tid_map.get(str(tid), str(tid))

        print('[大马猴] 分类请求: tid=%s, real_tid=%s, pg=%s' % (tid, real_tid, page))

        j = self._api_get('/api.php/web/filter/vod', {
            'type_id': real_tid,
            'page': page,
            'sort': sort
        }, self.host + '/type/' + real_tid)

        filtered_items = self._filter_items_by_category(j, real_tid)

        # 如果当前页过滤后太少，补抓后面 2 页同分类资源，避免分类页空白。
        try:
            cur_page = int(page)
        except Exception:
            cur_page = 1
        if len(filtered_items) < 8:
            seen_ids = set(str(x.get('vod_id') or x.get('id') or '') for x in filtered_items if isinstance(x, dict))
            for extra_page in range(cur_page + 1, cur_page + 3):
                jj = self._api_get('/api.php/web/filter/vod', {
                    'type_id': real_tid,
                    'page': str(extra_page),
                    'sort': sort
                }, self.host + '/type/' + real_tid)
                for item in self._filter_items_by_category(jj, real_tid):
                    vid = str(item.get('vod_id') or item.get('id') or '')
                    if vid and vid not in seen_ids:
                        seen_ids.add(vid)
                        filtered_items.append(item)
                if len(filtered_items) >= 24:
                    break

        videos = self._vod_list(filtered_items)
        pagecount = 1
        total = len(videos)
        limit = 24
        if isinstance(j, dict):
            pagecount = int(j.get('pageCount') or j.get('pagecount') or (cur_page + 1 if videos else cur_page))
            total = int(j.get('total') or total)
            limit = int(j.get('limit') or limit)

        print('[大马猴] 分类结果: %d条, page=%d/%d' % (len(videos), cur_page, pagecount))

        return {
            'list': videos,
            'page': cur_page,
            'pagecount': pagecount,
            'limit': limit,
            'total': total
        }

    # ==================== 搜索 ====================

    def searchContent(self, key, quick, pg='1'):
        self._ensure_ready()
        wd = str(key or '').strip()
        page = str(pg or '1')
        if not wd:
            return {'list': [], 'page': int(page)}

        print('[大马猴] 搜索: key=%s, pg=%s' % (wd, page))

        # 先尝试网页搜索常见接口
        paths = [
            ('/api.php/web/search/vod', {'wd': wd, 'page': page}),
            ('/api.php/web/vod/search', {'wd': wd, 'page': page}),
            ('/api.php/web/search', {'wd': wd, 'page': page}),
            ('/api.php/web/filter/vod', {'keyword': wd, 'page': page, 'sort': 'hits'}),
        ]
        for path, params in paths:
            j = self._api_get(path, params, self.host + '/search?keyword=' + quote(wd))
            videos = self._vod_list(j)
            if videos:
                print('[大马猴] 搜索结果: %d条, path=%s' % (len(videos), path))
                return {'list': videos, 'page': int(page)}
        print('[大马猴] 搜索无结果')
        return {'list': [], 'page': int(page)}

    # ==================== 详情 ====================

    def _first_detail(self, ids):
        vid = str(ids[0] if isinstance(ids, list) else ids)
        j = self._api_get('/api.php/web/vod/get_detail', {'vod_id': vid}, self.host + '/play/' + vid)
        arr = self._as_list(j)
        return (arr[0] if arr else {}), j

    def _aggregate_sources(self, vid):
        paths = [
            '/api.php/web/internal/search_aggregate',
            '/api.php/web/search_aggregate',
        ]
        for path in paths:
            j = self._api_get(path, {'vod_id': str(vid)}, self.host + '/play/' + str(vid))
            arr = self._as_list(j)
            if arr:
                print('[大马猴] 聚合线路: %d条, path=%s' % (len(arr), path))
                return arr
        print('[大马猴] 聚合线路无数据')
        return []

    def _line_rank(self, src):
        name = str(src.get('site_name') or src.get('external_display_name') or src.get('vod_play_from') or '').lower()
        from_code = str(src.get('vod_play_from') or src.get('external_play_from') or '').lower()
        url = str(src.get('vod_play_url') or '')
        if re.search(r'\.(m3u8|mp4|flv)(\?|#|$|\s)', url, re.I):
            if '暴风' in name or 'bfzy' in from_code:
                return 1
            if '爱坤' in name or 'ikm3u8' in from_code:
                return 2
            if '极速' in name or 'jsm3u8' in from_code:
                return 3
            if '如意' in name or 'rym3u8' in from_code:
                return 4
            if '量子' in name or 'lzm3u8' in from_code:
                return 5
            return 10
        if int(src.get('decode_status') or 0) == 0:
            return 50
        return 99

    def _build_sources(self, vid, detail):
        sources = []
        seen = set()

        def add_source(name, play_url):
            name = self._clean_text(name or '')
            play_url = str(play_url or '').strip()
            if not name or not play_url:
                return
            key = name + '|' + play_url[:80]
            if key in seen:
                return
            seen.add(key)
            sources.append((name, play_url))

        # 1. 优先用真实聚合接口，它返回的是可直接播放的 m3u8 线路。
        agg = self._aggregate_sources(vid)
        if agg:
            agg = sorted(agg, key=self._line_rank)
            for src in agg:
                play_url = str(src.get('vod_play_url') or '').strip()
                if not play_url:
                    continue
                if not re.search(r'\.(m3u8|mp4|flv)(\?|#|$|\s)', play_url, re.I):
                    continue
                line_name = (
                    src.get('site_name')
                    or src.get('external_display_name')
                    or src.get('external_play_from')
                    or src.get('vod_play_from')
                    or '线路'
                )
                add_source(line_name, play_url)
                if len(sources) >= 4:
                    break

        # 2. 兜底：从 get_detail 里只提取含 m3u8/mp4 的线路
        pf = str(detail.get('vod_play_from') or '')
        pu = str(detail.get('vod_play_url') or '')
        if pf and pu and len(sources) < 2:
            froms = pf.split('$$$')
            urls = pu.split('$$$')
            for idx, f in enumerate(froms):
                u = urls[idx] if idx < len(urls) else ''
                if not f or not u:
                    continue
                if not re.search(r'\.(m3u8|mp4|flv)(\?|#|$|\s)', u, re.I):
                    continue
                add_source(f, u)
                if len(sources) >= 4:
                    break

        # 3. 最后兜底：如果完全没有直链，再少量加入解析线路。
        if not sources and pf and pu:
            froms = pf.split('$$$')
            urls = pu.split('$$$')
            for idx, f in enumerate(froms[:3]):
                u = urls[idx] if idx < len(urls) else ''
                add_source(f, u)

        print('[大马猴] 构建播放线路: %d条' % len(sources))
        return sources

    def detailContent(self, ids):
        self._ensure_ready()
        if not ids:
            return {'list': []}
        vid = str(ids[0] if isinstance(ids, list) else ids)
        print('[大马猴] 详情请求: vid=%s' % vid)

        detail, raw = self._first_detail([vid])

        if not detail:
            agg = self._aggregate_sources(vid)
            if agg:
                detail = agg[0]
            else:
                print('[大马猴] 详情无数据')
                return {'list': []}

        area = detail.get('vod_area', '')
        cls = detail.get('vod_class', '')
        if isinstance(area, list):
            area = ','.join([str(x) for x in area if x])
        if isinstance(cls, list):
            cls = ','.join([str(x) for x in cls if x])

        sources = self._build_sources(vid, detail)
        vod = {
            'vod_id': vid,
            'vod_name': self._clean_text(detail.get('vod_name') or ''),
            'vod_pic': str(detail.get('vod_pic') or ''),
            'vod_remarks': str(detail.get('vod_remarks') or ''),
            'type_name': self._clean_text(detail.get('type_name') or cls or ''),
            'vod_year': str(detail.get('vod_year') or ''),
            'vod_area': self._clean_text(area),
            'vod_actor': self._clean_text(detail.get('vod_actor') or ''),
            'vod_director': self._clean_text(detail.get('vod_director') or ''),
            'vod_content': self._html2text(detail.get('vod_content') or ''),
            'vod_play_from': '$$$'.join([x[0] for x in sources]),
            'vod_play_url': '$$$'.join([x[1] for x in sources]),
        }
        return {'list': [vod]}

    # ==================== 播放 ====================

    def playerContent(self, flag, id, vipFlags):
        self._ensure_ready()
        url = str(id or '').strip()
        if not url:
            return {'parse': 0, 'url': ''}

        print('[大马猴] 播放解析: flag=%s, url=%s' % (flag, url[:80]))

        # 直链直接播放
        if url.startswith('http') and self.isVideoFormat(url):
            return {
                'parse': 0,
                'jx': 0,
                'url': url,
                'header': json.dumps({
                    'User-Agent': 'Mozilla/5.0',
                    'Referer': self.host + '/'
                })
            }

        # 官方站外编码线路尝试用 decode 接口解析
        decode_candidates = [
            ('/api.php/web/decode/url', {'url': url}),
            ('/api.php/web/decode/url', {'play_url': url}),
            ('/api.php/web/decode/url', {'vod_url': url}),
        ]
        for path, params in decode_candidates:
            j = self._api_get(path, params, self.host + '/play')
            data = j.get('data') if isinstance(j, dict) else None
            final_url = ''
            headers = {}
            if isinstance(data, str):
                final_url = data
            elif isinstance(data, dict):
                final_url = data.get('url') or data.get('play_url') or data.get('playUrl') or data.get('video') or ''
                headers = data.get('header') or data.get('headers') or {}
            elif isinstance(j, dict):
                final_url = j.get('url') or j.get('play_url') or ''
                headers = j.get('header') or j.get('headers') or {}

            if final_url:
                is_video = self.isVideoFormat(final_url)
                print('[大马猴] 解析成功: %s, 直链=%s' % (final_url[:80], is_video))
                return {
                    'parse': 0 if is_video else 1,
                    'jx': 0 if is_video else 1,
                    'url': final_url,
                    'header': json.dumps(headers) if headers else json.dumps({'User-Agent': 'Mozilla/5.0', 'Referer': self.host + '/'})
                }

        # 腾讯/优酷/爱奇艺等网页地址交给壳解析
        if re.search(r'(v\.qq\.com|youku\.com|iqiyi\.com|mgtv\.com|bilibili\.com)', url, re.I):
            print('[大马猴] 交壳解析: %s' % url[:80])
            return {'parse': 1, 'jx': 1, 'url': url}

        # 其它未知地址也交给壳解析
        print('[大马猴] 未知地址交壳解析: %s' % url[:80])
        return {'parse': 1, 'jx': 1, 'url': url}
