# -*- coding: utf-8 -*-
# JinriCP / PandaClass 韩国女团录播 vbox Python Spider
# 网站: https://5721004.xyz
# v5: 修复 IPFS 播放 — w3s.link 网关已关闭(301→storacha.network→fil.one)
#     所有 IPFS 分片通过 localProxy 代理, 尝试多个可用网关 (ipfs.io/cloudflare/dweb/pinata/4everland)
# v4: 重写分类逻辑 — 三级结构(季→日期文件夹→m3u8剧集) + 封面图 + 中文URL编码 + 过滤非视频项
# 特性: m3u8直链播放 + SRT中韩双语字幕自动加载 + IPFS分片代理 + preview封面图

import re
import json
import base64
import hashlib
import urllib3
from urllib.parse import quote, unquote
import requests

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

try:
    from base.spider import Spider as BaseSpider
except ImportError:
    class BaseSpider:
        def init(self, extend=""): pass
        def homeContent(self, filter): pass
        def homeVideoContent(self): pass
        def categoryContent(self, tid, pg, filter, extend): pass
        def detailContent(self, ids): pass
        def playerContent(self, flag, id, vipFlags=None): pass
        def searchContent(self, key, quick, pg='1'): pass
        def isVideoFormat(self, url): return False
        def manualVideoCheck(self): return False
        def localProxy(self, param): pass

# ==================== 全局常量 ====================

DEFAULT_HOST = 'https://5721004.xyz'
UA = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'

_EXCLUDE_PATHS = {'player'}
# 非视频/非文件夹文件 — 不在分类列表中展示
_IGNORE_FILES = {'readme.md', '下载链接说明.txt', '节目预览图.gif'}

_cached_categories = None
_m3u8_cache = {}

# ==================== Spider 主类 ====================

class Spider(BaseSpider):

    def init(self, extend=""):
        self.headers = {
            'User-Agent': UA,
            'Referer': DEFAULT_HOST + '/'
        }
        self.session = requests.Session()
        self.session.headers.update(self.headers)
        self.session.verify = False
        self._timeout = 15

        self.host = DEFAULT_HOST
        try:
            effective_hosts = globals().get('_vbox_effective_hosts', [])
            if effective_hosts and len(effective_hosts) > 0:
                self.host = effective_hosts[0].rstrip('/')
                print('[JinriCP] 使用注入域名: ' + self.host)
        except Exception as e:
            print('[JinriCP] 读取注入域名失败, 使用默认: ' + str(e))

        global _cached_categories
        if _cached_categories is None:
            _cached_categories = self._fetch_categories()

    # ==================== 首页 ====================

    def homeContent(self, filter):
        global _cached_categories
        if _cached_categories is None:
            _cached_categories = self._fetch_categories()
        return {'class': _cached_categories}

    def homeVideoContent(self):
        return {}

    # ==================== 分类列表（一级：季） ====================

    def categoryContent(self, tid, pg, filter, extend):
        if tid == 'fans':
            return self._fans_category_content(pg)

        url = '{}/{}/'.format(self.host, tid)
        try:
            resp = self.session.get(url, timeout=self._timeout)
            if resp.status_code != 200:
                return self._empty_list(pg)

            html = resp.text
            vod_list = self._parse_category_items(html, tid)

            return {
                'list': vod_list,
                'page': str(pg),
                'pagecount': '1',
                'limit': str(len(vod_list)),
                'total': str(len(vod_list))
            }
        except Exception as e:
            print('[JinriCP] categoryContent err: ' + str(e))
            return self._empty_list(pg)

    def _fans_category_content(self, pg):
        FANS_API = 'https://fans.5721004.xyz/api'
        try:
            page = int(pg) if pg else 1
            resp = self.session.get(
                '{}/posts?page={}'.format(FANS_API, page),
                timeout=self._timeout
            )
            if resp.status_code != 200:
                return self._empty_list(pg)

            posts = resp.json()
            vod_list = []
            for post in posts:
                pid = post.get('pid') or post.get('message_id')
                text = post.get('text', '')
                title = text.replace('#', '').strip()
                video_media = None
                cover_id = post.get('cover_id')
                for m in post.get('media_details', []):
                    if m.get('type') == 'video':
                        video_media = m
                        break

                cover_url = ''
                if cover_id:
                    cover_url = 'https://fans.5721004.xyz/stream/{}'.format(cover_id)

                vod_id = 'fans@@{}'.format(pid)

                remarks = ''
                if video_media and video_media.get('duration'):
                    mins = video_media['duration'] // 60
                    secs = video_media['duration'] % 60
                    remarks = '{}:{:02d}'.format(mins, secs)

                vod_list.append({
                    'vod_name': title[:50],
                    'vod_id': vod_id,
                    'vod_pic': cover_url,
                    'vod_remarks': remarks
                })

            return {
                'list': vod_list,
                'page': str(pg),
                'pagecount': '10',
                'limit': str(len(vod_list)),
                'total': str(len(vod_list))
            }
        except Exception as e:
            print('[JinriCP] _fans_category_content err: ' + str(e))
            return self._empty_list(pg)

    # ==================== 详情（二级→三级：文件夹→m3u8剧集） ====================

    def detailContent(self, ids):
        if not ids:
            return {'list': []}

        vod_id = ids[0]

        # 粉丝房
        if vod_id.startswith('fans@@'):
            return self._fans_detail_content(vod_id[6:])

        # m3u8 直链 — 直接返回单集
        if '.m3u8' in vod_id and vod_id.startswith('http'):
            name = self._extract_filename(vod_id)
            return {'list': [{
                'vod_id': vod_id,
                'vod_name': name,
                'vod_pic': '',
                'vod_play_from': 'JinriCP',
                'vod_play_url': '播放$' + vod_id
            }]}

        # v4: folder@@tid@@folder_name — 获取子目录的 m3u8 剧集列表
        if vod_id.startswith('folder@@'):
            parts = vod_id.split('@@', 2)
            if len(parts) == 3:
                tid = parts[1]
                folder_name = parts[2]
                # v4: URL编码中文文件夹名
                encoded_name = quote(folder_name, safe='')
                folder_url = '{}/{}/?/{}/'.format(self.host, tid, encoded_name)
                return self._fetch_folder_detail(folder_url, tid, folder_name)

        # 兼容旧格式：直接 URL
        if vod_id.startswith('http'):
            try:
                resp = self.session.get(vod_id, timeout=self._timeout)
                if resp.status_code != 200:
                    return {'list': []}
                html = resp.text
                tid = self._extract_tid(vod_id)
                play_items = self._parse_m3u8_items(html, tid)
                cover_url = self._find_cover_image(html, tid)

                if play_items:
                    play_parts = []
                    for item in play_items:
                        play_parts.append(item['name'] + '$' + item['url'])
                    play_url = '#'.join(play_parts)

                    folder_name = self._extract_folder_name(vod_id)
                    vod = {
                        'vod_id': vod_id,
                        'vod_name': folder_name,
                        'vod_pic': cover_url,
                        'vod_play_from': 'JinriCP',
                        'vod_play_url': play_url,
                        'vod_content': 'JinriCP/PandaClass 韩国女团录播'
                    }
                    return {'list': [vod]}
            except Exception as e:
                print('[JinriCP] detailContent err: ' + str(e))

        return {'list': []}

    def _fetch_folder_detail(self, folder_url, tid, folder_name):
        """请求子目录页面，解析 m3u8 文件列表 + 封面图"""
        try:
            resp = self.session.get(folder_url, timeout=self._timeout)
            if resp.status_code != 200:
                print('[JinriCP] 子目录请求失败: HTTP ' + str(resp.status_code) + ' ' + folder_url)
                return {'list': [{
                    'vod_id': 'folder@@' + tid + '@@' + folder_name,
                    'vod_name': self._safe_unquote(folder_name),
                    'vod_pic': '',
                    'vod_play_from': 'JinriCP',
                    'vod_play_url': '加载失败$' + self.host
                }]}

            html = resp.text
            play_items = self._parse_m3u8_items(html, tid)
            cover_url = self._fetch_preview_cover(tid, folder_name)

            if play_items:
                play_parts = []
                for item in play_items:
                    play_parts.append(item['name'] + '$' + item['url'])
                play_url = '#'.join(play_parts)

                vod = {
                    'vod_id': 'folder@@' + tid + '@@' + folder_name,
                    'vod_name': self._safe_unquote(folder_name),
                    'vod_pic': cover_url,
                    'vod_play_from': 'JinriCP',
                    'vod_play_url': play_url,
                    'vod_content': 'JinriCP/PandaClass 韩国女团录播'
                }
                return {'list': [vod]}
            else:
                print('[JinriCP] 子目录内未找到 m3u8: ' + folder_url)
                return {'list': [{
                    'vod_id': 'folder@@' + tid + '@@' + folder_name,
                    'vod_name': self._safe_unquote(folder_name),
                    'vod_pic': '',
                    'vod_play_from': 'JinriCP',
                    'vod_play_url': '暂无剧集$' + self.host
                }]}
        except Exception as e:
            print('[JinriCP] _fetch_folder_detail err: ' + str(e))
            return {'list': [{
                'vod_id': 'folder@@' + tid + '@@' + folder_name,
                'vod_name': self._safe_unquote(folder_name),
                'vod_pic': '',
                'vod_play_from': 'JinriCP',
                'vod_play_url': '加载失败$' + self.host
            }]}

    def _fetch_preview_cover(self, tid, folder_name):
        """尝试从 preview 子文件夹获取封面图"""
        try:
            encoded_name = quote(folder_name, safe='')
            preview_url = '{}/{}/?/{}/preview/'.format(self.host, tid, encoded_name)
            resp = self.session.get(preview_url, timeout=10)
            if resp.status_code != 200:
                return ''

            html = resp.text
            # 找第一个图片文件
            img_pattern = (
                r'data-sort-name="([^"]+\.(?:jpg|png|gif))"'
                r'[^>]*>.*?href="([^"]+)"'
            )
            m = re.search(img_pattern, html, re.S | re.I)
            if m:
                href = m.group(2)
                return self._fix_url(href, tid)
        except Exception as e:
            print('[JinriCP] 获取封面图失败: ' + str(e))
        return ''

    def _fans_detail_content(self, pid):
        """粉丝房详情：通过 API 获取视频播放地址"""
        FANS_API = 'https://fans.5721004.xyz/api'
        try:
            resp = self.session.get(
                '{}/post/{}'.format(FANS_API, pid),
                timeout=self._timeout
            )
            if resp.status_code != 200:
                return {'list': []}

            post = resp.json()
            text = post.get('text', '')
            title = text.replace('#', '').strip()[:50]

            play_items = []
            for m in post.get('media_details', []):
                if m.get('type') == 'video':
                    file_id = m.get('file_id', '')
                    if file_id:
                        url = 'https://fans.5721004.xyz/stream/{}'.format(file_id)
                        play_items.append({
                            'name': '播放',
                            'url': url
                        })

            if play_items:
                play_url = '#'.join(item['name'] + '$' + item['url'] for item in play_items)
                vod = {
                    'vod_id': 'fans@@' + str(pid),
                    'vod_name': title,
                    'vod_pic': '',
                    'vod_play_from': 'JinriCP',
                    'vod_play_url': play_url,
                    'vod_content': '粉丝房分享'
                }
                return {'list': [vod]}
            return {'list': []}
        except Exception as e:
            print('[JinriCP] _fans_detail_content err: ' + str(e))
            return {'list': []}

    # ==================== 播放（m3u8 + 字幕 + IPFS网关） ====================

    def playerContent(self, flag, id, vipFlags=None):
        play_header = {
            'User-Agent': UA,
            'Referer': self.host + '/'
        }

        if '.m3u8' in id and id.startswith('http'):
            rewritten_url = self._rewrite_m3u8_if_needed(id)
            if rewritten_url:
                result = {
                    'parse': 0,
                    'playUrl': '',
                    'url': rewritten_url,
                    'header': play_header
                }
            else:
                result = {
                    'parse': 0,
                    'playUrl': '',
                    'url': id,
                    'header': play_header
                }
        else:
            result = {
                'parse': 0,
                'playUrl': '',
                'url': id,
                'header': play_header
            }

        if '.m3u8' in id:
            srt_url = id.rsplit('.m3u8', 1)[0] + '.srt'
            result['subt'] = srt_url

        return result

    def _rewrite_m3u8_if_needed(self, m3u8_url):
        """下载 m3u8，重写死掉的 IPFS 网关 URL，通过 localProxy 代理分片

        w3s.link 网关已关闭 (301 → storacha.network → fil.one 营销页)
        所有 IPFS 分片 URL 需通过 localProxy 代理，尝试多个可用网关
        """
        try:
            resp = self.session.get(m3u8_url, timeout=10)
            if resp.status_code != 200:
                return None

            content = resp.text

            # 检查是否包含 IPFS URL
            if 'ipfs' not in content and 'w3s.link' not in content and 'raribleuserdata' not in content:
                return None

            proxy_base = self._get_proxy_base()

            # 重写所有 IPFS 分片 URL 为 localProxy 代理 URL
            # 原始: https://ipfs.w3s.link/ipfs/CID
            # 重写: http://127.0.0.1:port?do=ipfs&cid=CID
            def _replace_ipfs(match):
                cid = match.group(1)
                return proxy_base + '?do=ipfs&cid=' + cid

            rewritten = re.sub(
                r'https?://[a-z0-9.-]+/ipfs/([a-zA-Z0-9]+)',
                _replace_ipfs,
                content
            )

            if rewritten == content:
                return None

            # 缓存重写后的 m3u8，用 md5 作为 key (避免 URL 过长)
            cache_key = hashlib.md5(rewritten.encode('utf-8')).hexdigest()[:12]
            globals()['_m3u8_cache'][cache_key] = rewritten

            print('[JinriCP] IPFS 分片 URL 重写完成, cache=' + cache_key)
            proxy_url = proxy_base + '?do=m3u8&id=' + cache_key
            return proxy_url

        except Exception as e:
            print('[JinriCP] m3u8 重写异常: ' + str(e))
            return None

    def _get_proxy_base(self):
        try:
            proxy_port = globals().get('_vbox_local_proxy_port', '')
            if proxy_port:
                return 'http://127.0.0.1:' + str(proxy_port)
        except:
            pass
        return 'http://127.0.0.1:9938'

    # ==================== 搜索 ====================

    def searchContent(self, key, quick, pg='1'):
        results = []

        def _search_one(cat):
            tid = cat['type_id']
            cat_name = cat['type_name']
            try:
                url = '{}/{}/'.format(self.host, tid)
                resp = self.session.get(url, timeout=10)
                if resp.status_code != 200:
                    return []
                items = self._parse_category_items(resp.text, tid)
                matched = []
                kw = key.lower()
                for item in items:
                    if kw in item['vod_name'].lower():
                        matched.append({
                            'vod_id': item['vod_id'],
                            'vod_name': '[{}] {}'.format(cat_name, item['vod_name']),
                            'vod_pic': item.get('vod_pic', ''),
                            'vod_remarks': cat_name
                        })
                return matched
            except:
                return []

        cats = _cached_categories or []

        try:
            from concurrent.futures import ThreadPoolExecutor, as_completed
            with ThreadPoolExecutor(max_workers=5) as executor:
                futures = [executor.submit(_search_one, cat) for cat in cats]
                for future in as_completed(futures):
                    try:
                        results.extend(future.result())
                    except:
                        pass
        except:
            for cat in cats:
                results.extend(_search_one(cat))

        return results

    # ==================== 工具方法 ====================

    def _fetch_categories(self):
        """从网站侧边栏 HTML 动态获取分类列表"""
        candidate_urls = [
            self.host + '/bu/',
            self.host + '/s2/',
            self.host + '/pc/',
            self.host + '/',
        ]

        html = None
        for url in candidate_urls:
            try:
                resp = self.session.get(url, timeout=self._timeout)
                if resp.status_code != 200:
                    continue
                text = resp.text
                if 'mdui-list-item' in text and 'mdui-ripple' in text:
                    html = text
                    print('[JinriCP] 侧边栏来源: ' + url)
                    break
            except:
                continue

        if html is None:
            print('[JinriCP] 所有页面均不可用, 使用备用分类')
            return self._fallback_categories()

        categories = []

        # 侧边栏分类链接格式: <a href="/bu/" class="mdui-list-item mdui-ripple">
        pattern = (
            r'<a\s+href="(/[a-zA-Z0-9_]+)/?"\s+class="mdui-list-item\s+mdui-ripple"[^>]*>'
            r'(.*?)'
            r'</a>'
        )

        seen_tids = set()
        for m in re.finditer(pattern, html, re.S):
            raw_path = m.group(1)
            inner = m.group(2)

            tid = raw_path.lstrip('/')

            if tid in _EXCLUDE_PATHS:
                continue
            if tid in seen_tids:
                continue

            name = ''
            content_match = re.search(
                r'mdui-list-item-content[^>]*>([^<]+)</div>', inner, re.S
            )
            if content_match:
                name = content_match.group(1).strip()
            else:
                name = re.sub(r'<[^>]+>', '', inner).strip()

            if not name:
                continue

            seen_tids.add(tid)
            categories.append({
                'type_id': tid,
                'type_name': name
            })

        if categories:
            print('[JinriCP] 动态获取到 ' + str(len(categories)) + ' 个分类')
            return categories
        else:
            print('[JinriCP] 动态获取分类为空, 使用备用')
            return self._fallback_categories()

    def _fallback_categories(self):
        """备用分类列表（当网站侧边栏不可用时）"""
        return [
            {'type_id': 'bu', 'type_name': 'JinriCP第一季'},
            {'type_id': 's2', 'type_name': 'JinriCP第二季'},
            {'type_id': 's3', 'type_name': 'JinriCP第三季'},
            {'type_id': 's4', 'type_name': 'JinriCP第四季'},
            {'type_id': 's5', 'type_name': 'JinriCP第五季'},
            {'type_id': 's6', 'type_name': 'JinriCP第六季'},
            {'type_id': 'pc', 'type_name': 'PandaClass第一季'},
            {'type_id': 'pc2', 'type_name': 'PandaClass第二季'},
            {'type_id': 'pc3', 'type_name': 'PandaClass第三季'},
            {'type_id': 'fans', 'type_name': '粉丝房分享'},
        ]

    def _parse_category_items(self, html, tid):
        """
        v4: 解析分类页面，只返回文件夹和顶层m3u8文件
        过滤掉 README.md、txt、gif 等非视频内容
        文件夹使用 folder@@tid@@name 格式
        """
        result = []

        pattern = (
            r'data-sort-name="([^"]+)"'
            r'[^>]*data-sort-size="([^"]*)"'
            r'[^>]*>.*?href="([^"]+)"'
        )

        for m in re.finditer(pattern, html, re.S):
            name = m.group(1)
            size = m.group(2)
            href = m.group(3)
            is_folder = (size == '-')

            if is_folder:
                # v4: 跳过 preview 文件夹（它是封面图文件夹，不是剧集目录）
                if name.lower() == 'preview':
                    continue
                folder_name = self._safe_unquote(name)
                vod_id = 'folder@@' + tid + '@@' + name
                result.append({
                    'vod_name': folder_name,
                    'vod_id': vod_id,
                    'vod_pic': '',
                    'vod_remarks': '📁'
                })
            elif '.m3u8' in name.lower():
                # v4: 过滤非视频文件
                name_lower = name.lower()
                if name_lower in _IGNORE_FILES:
                    continue
                display_name = self._safe_unquote(name.replace('.m3u8', ''))
                result.append({
                    'vod_name': display_name,
                    'vod_id': self._fix_url(href, tid),
                    'vod_pic': '',
                    'vod_remarks': size or '▶️'
                })
            # 其他文件类型（txt, gif, md）直接跳过

        return result

    def _parse_m3u8_items(self, html, tid):
        """从子目录页面解析所有 m3u8 文件"""
        result = []

        pattern = (
            r'data-sort-name="([^"]+\.m3u8)"'
            r'[^>]*>.*?href="([^"]+)"'
        )

        for m in re.finditer(pattern, html, re.S | re.I):
            raw_name = m.group(1)
            href = m.group(2)
            display_name = self._safe_unquote(raw_name.replace('.m3u8', ''))
            result.append({
                'name': display_name,
                'url': self._fix_url(href, tid)
            })

        return result

    def _find_cover_image(self, html, tid):
        """尝试从页面提取封面图"""
        pattern = (
            r'data-sort-name="([^"]+\.(?:jpg|png|gif))"'
            r'[^>]*>.*?href="([^"]+)"'
        )
        m = re.search(pattern, html, re.S | re.I)
        if m:
            return self._fix_url(m.group(2), tid)
        return ''

    def _fix_url(self, href, tid):
        """将相对 URL 转为完整 URL"""
        if not href:
            return ''
        if href.startswith('http'):
            return href
        if href.startswith('//'):
            return 'https:' + href
        if href.startswith('/'):
            return self.host + href
        if href.startswith('./'):
            href = href[2:]
        return '{}/{}/{}'.format(self.host, tid, href)

    def _extract_tid(self, url):
        """从 URL 中提取 tid"""
        m = re.search(r'https?://[^/]+/(\w+)/', url)
        if m:
            return m.group(1)
        m = re.search(r'path=/(\w+)/', url)
        if m:
            return m.group(1)
        return 'bu'

    def _extract_folder_name(self, url):
        """从 URL 中提取文件夹名"""
        m = re.search(r'\?/([^/]+)/?$', url)
        if m:
            return self._safe_unquote(m.group(1))
        m = re.search(r'https?://[^/]+/(\w+)/?$', url)
        if m:
            return m.group(1)
        parts = url.rstrip('/').split('/')
        return self._safe_unquote(parts[-1]) if parts else url

    def _extract_filename(self, url):
        """从 URL 中提取文件名"""
        name = url.split('/')[-1]
        name = self._safe_unquote(name)
        if '.m3u8' in name:
            name = name.replace('.m3u8', '')
        return name

    def _safe_unquote(self, text):
        try:
            return unquote(text)
        except:
            return text

    def _empty_list(self, pg):
        return {
            'list': [],
            'page': str(pg),
            'pagecount': '1',
            'limit': '0',
            'total': '0'
        }

    # ==================== 基类必需方法 ====================

    def isVideoFormat(self, url):
        return '.m3u8' in url or '.mp4' in url

    def manualVideoCheck(self):
        return False

    def localProxy(self, param):
        """本地代理: 返回 m3u8 内容或代理 IPFS 分片"""
        try:
            from urllib.parse import parse_qs, urlparse
            parsed = urlparse('?' + param if '?' not in param else param)
            params = parse_qs(parsed.query)

            do = params.get('do', [''])[0]

            if do == 'm3u8':
                cache_key = params.get('id', [''])[0]
                if cache_key:
                    m3u8_content = globals().get('_m3u8_cache', {}).get(cache_key)
                    if m3u8_content:
                        return {
                            'mime': 'application/vnd.apple.mpegurl',
                            'content': m3u8_content
                        }
                return {}

            elif do == 'ipfs':
                cid = params.get('cid', [''])[0]
                if not cid:
                    return {}

                # 尝试多个 IPFS 网关 (w3s.link 已关闭)
                gateways = [
                    'https://ipfs.io/ipfs/',
                    'https://cloudflare-ipfs.com/ipfs/',
                    'https://dweb.link/ipfs/',
                    'https://gateway.pinata.cloud/ipfs/',
                    'https://4everland.io/ipfs/',
                ]

                for gw in gateways:
                    try:
                        gw_resp = requests.get(
                            gw + cid, timeout=10, verify=False, stream=True,
                            headers={'User-Agent': UA}
                        )
                        if gw_resp.status_code != 200:
                            gw_resp.close()
                            continue

                        content_type = gw_resp.headers.get('Content-Type', '')
                        # 跳过 HTML 响应 (网关返回的是错误页/营销页)
                        if 'text/html' in content_type:
                            gw_resp.close()
                            continue

                        data = gw_resp.content
                        gw_resp.close()

                        if data and len(data) > 0:
                            print('[JinriCP] IPFS 分片获取成功: ' + gw + ' ' + str(len(data)) + ' bytes')
                            return {
                                'mime': 'video/mp2t',
                                'content': data
                            }
                    except Exception as e:
                        print('[JinriCP] 网关 ' + gw + ' 失败: ' + str(e))
                        continue

                print('[JinriCP] IPFS 分片获取失败, 所有网关不可用, cid=' + cid)
                return {}

            return {}
        except Exception as e:
            print('[JinriCP] localProxy err: ' + str(e))
            return {}
