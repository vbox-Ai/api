# -*- coding: utf-8 -*-
"""
=================================================
  刁民制作，仅供测试，测试完毕请于24小时删除。
=================================================

山有木兮影视 TVBox / OK影视 / 影视仓 标准 Python 源。

站点: https://film.symx.club (Vue3 + Naive UI + ArtPlayer)

特点:
1. 支持 首页/分类/搜索/详情/播放 全流程。
2. 基于 JSON API，无需解析 HTML（站点为 Vue SPA）。
3. 图片通过站点代理加载，确保正常显示。
4. 底部筛选器: 支持地区、年代、语言、排序筛选。
5. 播放采用 parse:1 网页解析（站点使用 TAC 验证码保护播放地址）。
6. 实时抓取动态域名，防止网站更换域名。
7. 兼容 FongMi/TV (T3) & WebHomeTV / PeekPro (T4)。
"""

import sys
import json
import re
import time
import uuid
from urllib.parse import quote, urlencode

sys.path.append('..')

try:
    from base.spider import Spider
except ImportError:
    import requests as rq

    class Spider:
        def fetch(self, url, headers=None, **kw):
            kw.pop('timeout', None)
            r = rq.get(url, headers=headers, timeout=15, **kw)
            r.encoding = 'utf-8'
            return r


class Spider(Spider):
    """
    山有木兮影视 Spider
    Vue3 + Naive UI + ArtPlayer, JSON API
    """

    # 默认域名（会被动态域名覆盖）
    host = 'https://film.symx.club'

    # 导航站（固定入口，用于探测最新影视域名）
    _portal = 'https://symx.club'

    # 已知备用域名
    _known_domains = [
        'https://film.symx.club',
        'https://film.symx.cc',
        'https://film.symx.me',
        'https://film.symx.net',
        'https://film.symx.cn',
        'https://film.symx.tv',
    ]

    # 域名缓存
    _last_domain_check = 0
    _domain_cache_hours = 1

    # 客户端ID（用于API认证）
    _client_id = ''

    header = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 '
                      '(KHTML, like Gecko) Chrome/120.0 Safari/537.36',
        'Accept': 'application/json, text/plain, */*',
        'Accept-Language': 'zh-CN,zh;q=0.9',
    }

    # 分类列表
    classes = [
        {'type_name': '电视剧', 'type_id': '1'},
        {'type_name': '电影', 'type_id': '2'},
        {'type_name': '综艺', 'type_id': '3'},
        {'type_name': '动漫', 'type_id': '4'},
        {'type_name': '短剧', 'type_id': '5'},
    ]

    # ===================================================================
    #  动态域名探测
    # ===================================================================

    def _get_client_id(self):
        """生成或获取客户端ID"""
        if not self._client_id:
            self._client_id = uuid.uuid4().hex
        return self._client_id

    def _detect_domain(self):
        """实时探测最新可用域名"""
        now = time.time()
        if now - self._last_domain_check < self._domain_cache_hours * 3600:
            return self.host

        self._last_domain_check = now

        # 方法1: 从导航站提取域名
        discovered = self._fetch_domains_from_portal()
        for domain in discovered:
            if self._test_domain(domain):
                self.host = domain
                return self.host

        # 方法2: 从已知域名列表探测
        for domain in self._known_domains:
            if self._test_domain(domain):
                self.host = domain
                return self.host

        # 方法3: 尝试当前 host
        if self._test_domain(self.host):
            return self.host

        return self.host

    def _fetch_domains_from_portal(self):
        """从导航站提取所有可用域名"""
        domains = []
        try:
            r = self.fetch(self._portal, headers=self.header, timeout=10)
            text = r.text if hasattr(r, 'text') else r.content.decode('utf-8', errors='ignore')
            # 提取所有 symx 相关域名
            found = re.findall(r'https?://(?:film|video|movie)\.(symx\.[a-z]+)', text, re.I)
            for d in found:
                full = 'https://film.' + d.lower()
                if full not in domains:
                    domains.append(full)
            # 也提取通配的 symx 域名
            found2 = re.findall(r'https?://(symx\.[a-z]+)', text, re.I)
            for d in found2:
                full = 'https://film.' + d.lower()
                if full not in domains:
                    domains.append(full)
        except Exception:
            pass
        return domains

    def _test_domain(self, domain):
        """测试域名是否可访问且是山有木兮影视站点"""
        try:
            r = self.fetch(
                domain + '/api/sites/info',
                headers=self._api_headers(),
                timeout=10
            )
            text = r.text if hasattr(r, 'text') else r.content.decode('utf-8', errors='ignore')
            return r.status_code == 200 and '山有木兮' in text
        except Exception:
            return False

    # ===================================================================
    #  基础方法
    # ===================================================================

    def getName(self):
        return '山有木兮影视'

    def init(self, extend=''):
        if isinstance(extend, list):
            self.extend = ''
        else:
            self.extend = extend or ''
        self._detect_domain()

    def isVideoFormat(self, url):
        return any(x in url for x in ['.m3u8', '.mp4', '.flv', '.avi', '.mkv'])

    def manualVideoCheck(self):
        return False

    def destroy(self):
        pass

    # ===================================================================
    #  API 请求封装
    # ===================================================================

    def _api_headers(self):
        """构建API请求头"""
        return {
            'User-Agent': self.header['User-Agent'],
            'Accept': 'application/json, text/plain, */*',
            'Referer': self.host + '/m/index',
            'Origin': self.host,
            'X-Platform': 'web',
            'X-Client-Id': self._get_client_id(),
        }

    def _api_get(self, path, params=None):
        """发送GET API请求"""
        self._detect_domain()
        url = path if path.startswith('http') else self.host + path
        if params:
            url = url + '?' + urlencode(params)

        headers = self._api_headers()

        try:
            r = self.fetch(url, headers=headers, timeout=15)
            text = r.text if hasattr(r, 'text') else r.content.decode('utf-8', errors='ignore')
            if r.status_code == 200:
                try:
                    return json.loads(text)
                except Exception:
                    return None
            # 域名可能失效，刷新后重试
            if r.status_code >= 500 or r.status_code == 403:
                self._last_domain_check = 0
                self._detect_domain()
                url = self.host + path
                if params:
                    url = url + '?' + urlencode(params)
                r = self.fetch(url, headers=self._api_headers(), timeout=15)
                text = r.text if hasattr(r, 'text') else r.content.decode('utf-8', errors='ignore')
                try:
                    return json.loads(text)
                except Exception:
                    return None
        except Exception:
            # 域名可能失效，刷新后重试
            self._last_domain_check = 0
            self._detect_domain()
            try:
                url = self.host + path
                if params:
                    url = url + '?' + urlencode(params)
                r = self.fetch(url, headers=self._api_headers(), timeout=15)
                text = r.text if hasattr(r, 'text') else r.content.decode('utf-8', errors='ignore')
                try:
                    return json.loads(text)
                except Exception:
                    return None
            except Exception:
                return None
        return None

    # ===================================================================
    #  图片处理
    # ===================================================================

    def _wrap_pic(self, pic_url):
        """将图片 URL 通过站点代理加载"""
        if not pic_url:
            return ''

        pic_url = pic_url.strip()
        if pic_url.startswith(('"', "'")) and pic_url.endswith(('"', "'")):
            pic_url = pic_url[1:-1]

        pic_url = pic_url.replace('&amp;', '&')

        if '127.0.0.1' in pic_url or 'proxy' in pic_url:
            return pic_url

        if pic_url.startswith('//'):
            pic_url = 'https:' + pic_url
        elif not pic_url.startswith(('http://', 'https://')):
            if pic_url.startswith('/'):
                pic_url = self.host + pic_url
            else:
                pic_url = self.host + '/' + pic_url

        # 通过站点代理加载图片
        return self.host + '/api/files/proxy?url=' + quote(pic_url, safe='')

    # ===================================================================
    #  首页
    # ===================================================================

    def homeContent(self, filter):
        """返回分类列表和筛选器配置"""
        # 动态获取分类
        try:
            data = self._api_get('/api/category/top')
            if data and data.get('code') == 200 and data.get('data'):
                cats = data['data']
                self.classes = [{'type_name': c['name'], 'type_id': str(c['id'])} for c in cats]
        except Exception:
            pass

        filters = {}
        for c in self.classes:
            tid = c['type_id']
            filters[tid] = [
                {'key': 'area', 'name': '地区', 'value': self._get_filter_area(tid)},
                {'key': 'year', 'name': '年代', 'value': self._get_filter_year(tid)},
                {'key': 'language', 'name': '语言', 'value': self._get_filter_language(tid)},
                {'key': 'sort', 'name': '排序', 'value': [
                    {'n': '最新更新', 'v': 'updateTime'},
                    {'n': '最多播放', 'v': 'hits'},
                    {'n': '评分最高', 'v': 'doubanScore'},
                ]},
            ]
        return {'class': self.classes, 'filters': filters}

    def _get_filter_area(self, category_id):
        """获取地区筛选器"""
        default = [
            {'n': '全部', 'v': ''},
            {'n': '中国大陆', 'v': '中国大陆'},
            {'n': '香港', 'v': '香港'},
            {'n': '台湾', 'v': '台湾'},
            {'n': '美国', 'v': '美国'},
            {'n': '日本', 'v': '日本'},
            {'n': '韩国', 'v': '韩国'},
            {'n': '英国', 'v': '英国'},
            {'n': '法国', 'v': '法国'},
            {'n': '泰国', 'v': '泰国'},
            {'n': '印度', 'v': '印度'},
        ]
        try:
            data = self._api_get('/api/film/category/filter', {'categoryId': category_id})
            if data and data.get('code') == 200:
                areas = data.get('data', {}).get('areaOptions', [])
                if areas:
                    return [{'n': '全部', 'v': ''}] + [{'n': a, 'v': a} for a in areas]
        except Exception:
            pass
        return default

    def _get_filter_year(self, category_id):
        """获取年份筛选器"""
        default = [
            {'n': '全部', 'v': ''},
            {'n': '2026', 'v': '2026'},
            {'n': '2025', 'v': '2025'},
            {'n': '2024', 'v': '2024'},
            {'n': '2023', 'v': '2023'},
            {'n': '2022', 'v': '2022'},
            {'n': '2021', 'v': '2021'},
            {'n': '2020', 'v': '2020'},
            {'n': '2019', 'v': '2019'},
            {'n': '2018', 'v': '2018'},
        ]
        try:
            data = self._api_get('/api/film/category/filter', {'categoryId': category_id})
            if data and data.get('code') == 200:
                years = data.get('data', {}).get('yearOptions', [])
                if years:
                    return [{'n': '全部', 'v': ''}] + [{'n': y, 'v': y} for y in years]
        except Exception:
            pass
        return default

    def _get_filter_language(self, category_id):
        """获取语言筛选器"""
        default = [
            {'n': '全部', 'v': ''},
            {'n': '汉语', 'v': '汉语'},
            {'n': '英语', 'v': '英语'},
            {'n': '粤语', 'v': '粤语'},
            {'n': '日语', 'v': '日语'},
            {'n': '韩语', 'v': '韩语'},
        ]
        try:
            data = self._api_get('/api/film/category/filter', {'categoryId': category_id})
            if data and data.get('code') == 200:
                langs = data.get('data', {}).get('languageOptions', [])
                if langs:
                    return [{'n': '全部', 'v': ''}] + [{'n': l, 'v': l} for l in langs]
        except Exception:
            pass
        return default

    def homeVideoContent(self):
        """首页推荐内容"""
        vod_list = []
        try:
            # 从各分类获取最新内容
            for cat_id in ['1', '2', '3', '4']:
                data = self._api_get('/api/film/category/list', {
                    'categoryId': cat_id,
                    'pageNum': 1,
                    'pageSize': 10,
                })
                if data and data.get('code') == 200:
                    items = data.get('data', {}).get('list', [])
                    for item in items:
                        vod = self._parse_film_item(item)
                        if vod:
                            vod_list.append(vod)
                if len(vod_list) >= 30:
                    break
        except Exception:
            pass
        return {'list': vod_list[:30]}

    # ===================================================================
    #  分类内容
    # ===================================================================

    def categoryContent(self, tid, pg, filter, extend):
        """分类页内容"""
        try:
            pg = int(pg or 1)

            # 解析筛选器
            ext = {}
            if extend:
                if isinstance(extend, dict):
                    ext = extend
                elif isinstance(extend, str):
                    try:
                        ext = json.loads(extend)
                    except Exception:
                        ext = {}

            area = ext.get('area', '')
            year = ext.get('year', '')
            language = ext.get('language', '')
            sort = ext.get('sort', 'updateTime')

            # 构建API参数
            params = {
                'categoryId': tid,
                'pageNum': pg,
                'pageSize': 15,
                'sort': sort,
            }
            if area:
                params['area'] = area
            if year:
                params['year'] = year
            if language:
                params['language'] = language

            data = self._api_get('/api/film/category/list', params)

            if data and data.get('code') == 200:
                items = data.get('data', {}).get('list', [])
                total = data.get('data', {}).get('total', 0)
                vod_list = []
                for item in items:
                    vod = self._parse_film_item(item)
                    if vod:
                        vod_list.append(vod)

                pagecount = (total + 14) // 15 if total > 0 else 1

                return {
                    'page': pg,
                    'pagecount': pagecount,
                    'limit': len(vod_list),
                    'total': total,
                    'list': vod_list,
                }
        except Exception:
            pass
        return {'page': pg, 'pagecount': 1, 'limit': 15, 'total': 0, 'list': []}

    # ===================================================================
    #  详情页
    # ===================================================================

    def detailContent(self, ids):
        """影片详情"""
        try:
            vod_id = ids[0] if isinstance(ids, list) else str(ids)
            # vod_id 格式: "categoryId|filmId" 或 "filmId"
            category_id = ''
            film_id = vod_id
            if '|' in vod_id:
                parts = vod_id.split('|', 1)
                category_id = parts[0]
                film_id = parts[1]

            # 使用 play API 获取详情（detail API 需要 TAC 验证）
            data = self._api_get('/api/film/detail/play', {'filmId': film_id})

            if not data or data.get('code') != 200:
                return {'list': []}

            info = data.get('data', {})

            vod_name = info.get('name', '')
            vod_pic = self._wrap_pic(info.get('cover', ''))
            vod_year = info.get('year', '')
            vod_area = info.get('area', '')
            vod_content = info.get('blurb', '')
            vod_remarks = info.get('updateStatus', '')
            category_name = info.get('categoryName', '')

            # 如果没有 categoryId，从信息中获取
            if not category_id:
                category_id = str(info.get('categoryId', ''))

            # 构建播放列表
            play_from_list = []
            play_url_list = []

            play_lines = info.get('playLineList', [])
            for pl in play_lines:
                player_name = pl.get('playerName', '线路')
                lines = pl.get('lines', [])
                if not lines:
                    continue

                episodes = []
                for line in lines:
                    ep_name = line.get('name', str(line.get('index', '')))
                    line_id = line.get('id', '')
                    # 格式: 集数名$categoryId|filmId|lineId
                    episodes.append('%s$%s|%s|%s' % (ep_name, category_id, film_id, line_id))

                if episodes:
                    play_from_list.append(player_name)
                    play_url_list.append('#'.join(episodes))

            if not play_from_list:
                play_from_list.append('山有木兮')
                play_url_list.append('播放$%s|%s|' % (category_id, film_id))

            vod = {
                'vod_id': vod_id,
                'vod_name': vod_name,
                'vod_pic': vod_pic,
                'type_name': category_name,
                'vod_year': vod_year,
                'vod_area': vod_area,
                'vod_actor': '',
                'vod_director': '',
                'vod_content': vod_content,
                'vod_remarks': vod_remarks,
                'vod_play_from': '$$$'.join(play_from_list),
                'vod_play_url': '$$$'.join(play_url_list),
            }
            return {'list': [vod]}
        except Exception:
            return {'list': []}

    # ===================================================================
    #  搜索
    # ===================================================================

    def searchContent(self, key, quick, pg=1):
        """搜索影片"""
        try:
            pg = int(pg or 1)
            # 搜索 API 需要 TAC 验证，尝试请求
            data = self._api_get('/api/film/search', {
                'keyword': key,
                'pageNum': pg,
                'pageSize': 15,
            })

            if data and data.get('code') == 200:
                items = data.get('data', {}).get('list', [])
                vod_list = []
                for item in items:
                    vod = self._parse_film_item(item)
                    if vod:
                        vod_list.append(vod)
                return {'list': vod_list, 'page': pg}
        except Exception:
            pass
        return {'list': [], 'page': pg}

    def searchContentPage(self, key, quick, pg=1):
        return self.searchContent(key, quick, pg)

    # ===================================================================
    #  播放
    # ===================================================================

    def playerContent(self, flag, id, vipFlags):
        """
        播放解析。
        站点使用 TAC 验证码保护播放地址，无法直接提取 m3u8。
        采用 parse:1 网页解析，由 TVBox 内置浏览器加载播放页。
        """
        try:
            play_id = str(id or '')

            # 解析 categoryId|filmId|lineId
            category_id = ''
            film_id = ''
            line_id = ''

            if '|' in play_id:
                parts = play_id.split('|')
                category_id = parts[0] if len(parts) > 0 else ''
                film_id = parts[1] if len(parts) > 1 else ''
                line_id = parts[2] if len(parts) > 2 else ''
            else:
                film_id = play_id

            # 如果没有 lineId，先获取播放信息拿到第一个 lineId
            if not line_id and film_id:
                try:
                    data = self._api_get('/api/film/detail/play', {'filmId': film_id})
                    if data and data.get('code') == 200:
                        play_lines = data.get('data', {}).get('playLineList', [])
                        if play_lines and play_lines[0].get('lines'):
                            line_id = str(play_lines[0]['lines'][0].get('id', ''))
                            if not category_id:
                                category_id = str(data['data'].get('categoryId', ''))
                except Exception:
                    pass

            # 构建播放页 URL
            if category_id and film_id and line_id:
                url = self.host + '/m/player?cid=%s&film_id=%s&line_id=%s' % (category_id, film_id, line_id)
            elif film_id:
                url = self.host + '/m/detail/%s/%s' % (category_id or '1', film_id)
            else:
                url = self.host + '/m/index'

            return {
                'parse': 1,
                'url': url,
                'header': {
                    'User-Agent': self.header['User-Agent'],
                    'Referer': self.host + '/',
                },
            }
        except Exception:
            return {
                'parse': 1,
                'url': self.host + '/m/index',
                'header': {
                    'User-Agent': self.header['User-Agent'],
                    'Referer': self.host + '/',
                },
            }

    # ===================================================================
    #  本地代理 (图片代理) - 保留备用
    # ===================================================================

    def localProxy(self, param):
        """本地代理: 处理图片加载（备用）"""
        try:
            if isinstance(param, str):
                from urllib.parse import parse_qs
                param_dict = parse_qs(param)
            else:
                param_dict = param

            do = param_dict.get('do', '')
            if isinstance(do, list):
                do = do[0] if do else ''

            if do == 'img':
                url = param_dict.get('url', '')
                if isinstance(url, list):
                    url = url[0] if url else ''

                if url:
                    try:
                        url = __import__('base64').urlsafe_b64decode(url).decode('utf-8')
                    except Exception:
                        pass

                    if url:
                        headers = {
                            'User-Agent': self.header['User-Agent'],
                            'Referer': self.host + '/',
                            'Accept': 'image/webp,image/apng,image/*,*/*;q=0.8',
                        }
                        r = self.fetch(url, headers=headers, timeout=15)
                        content_type = ''
                        if hasattr(r, 'headers'):
                            ct = r.headers.get('Content-Type', '')
                            if ct and 'image' in ct:
                                content_type = ct
                        if not content_type:
                            if '.png' in url:
                                content_type = 'image/png'
                            elif '.webp' in url:
                                content_type = 'image/webp'
                            else:
                                content_type = 'image/jpeg'
                        content = r.content if hasattr(r, 'content') else r.text.encode('utf-8')
                        return [200, content_type, content, {}]
        except Exception:
            pass
        return [404, 'text/plain', '', {}]

    # ===================================================================
    #  数据解析
    # ===================================================================

    def _parse_film_item(self, item):
        """解析影片列表项为 TVBox vod 格式"""
        try:
            film_id = item.get('id', '')
            if not film_id:
                return None

            category_id = item.get('categoryId', '')
            name = item.get('name', '')
            cover = item.get('cover', '')
            blurb = item.get('blurb', '')
            score = item.get('doubanScore', '0.0')
            update_status = item.get('updateStatus', '')

            # 评分显示
            remarks = ''
            if score and score != '0.0' and score != '0':
                remarks = score
            if update_status:
                if remarks:
                    remarks = remarks + ' | ' + update_status
                else:
                    remarks = update_status

            # vod_id 格式: categoryId|filmId
            vod_id = '%s|%s' % (category_id, film_id) if category_id else str(film_id)

            return {
                'vod_id': vod_id,
                'vod_name': name,
                'vod_pic': self._wrap_pic(cover),
                'vod_remarks': remarks,
            }
        except Exception:
            return None
