# -*- coding: utf-8 -*-
# JinriCP / PandaClass 韩国女团录播 TVBox Python Spider
# 网站: https://5721004.xyz
# 特性: m3u8直链播放 + SRT中韩双语字幕自动加载

import re
import json
import urllib3
from urllib.parse import quote, unquote
from concurrent.futures import ThreadPoolExecutor, as_completed
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

HOST = 'https://5721004.xyz'
UA = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'

# 需要排除的非分类路径前缀
_EXCLUDE_PATHS = {'player'}  # player=播放器页面

# 运行时缓存分类列表（纯动态获取，无硬编码兜底）
_cached_categories = None

# ==================== Spider 主类 ====================

class Spider(BaseSpider):

    def init(self, extend=""):
        self.headers = {
            'User-Agent': UA,
            'Referer': HOST + '/'
        }
        self.session = requests.Session()
        self.session.headers.update(self.headers)
        self.session.verify = False
        self._timeout = 15
        # 初始化时预加载分类列表
        global _cached_categories
        if _cached_categories is None:
            _cached_categories = self._fetch_categories()

    # ==================== 首页 ====================

    def homeContent(self, filter):
        """动态从网站侧边栏获取分类列表，获取失败则返回空列表"""
        global _cached_categories
        if _cached_categories is None:
            _cached_categories = self._fetch_categories()
        return {'class': _cached_categories}

    def homeVideoContent(self):
        """首页推荐视频（本站无推荐，返回空）"""
        return {}

    # ==================== 分类列表 ====================

    def categoryContent(self, tid, pg, filter, extend):
        """
        请求季度根目录，返回文件夹和 m3u8 文件列表。
        tid: 分类ID，如 'bu', 's2', 'pc' 等
        fans 分类使用独立的 API
        """
        # fans 分类走独立 API
        if tid == 'fans':
            return self._fans_category_content(pg)

        url = '{}/{}'.format(HOST, tid) + '/'
        try:
            resp = self.session.get(url, timeout=self._timeout)
            if resp.status_code != 200:
                return self._empty_list(pg)

            html = resp.text
            vod_list = self._parse_items(html, tid)

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
        """粉丝房分类: 通过 fans.5721004.xyz API 获取列表"""
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
                # 提取标题: 去掉 #标签，取 file_name 或 text 前面部分
                title = text.replace('#', '').strip()
                # 查找视频信息
                video_media = None
                cover_id = post.get('cover_id')
                for m in post.get('media_details', []):
                    if m.get('type') == 'video':
                        video_media = m
                        break

                # 构造封面图 URL
                cover_url = ''
                if cover_id:
                    cover_url = 'https://fans.5721004.xyz/stream/{}'.format(cover_id)

                # vod_id 使用 fans_api:pid 格式标记，便于 detailContent 识别
                vod_id = 'fans_api:{}'.format(pid)

                # 视频时长
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
                'pagecount': '10',  # 粉丝房支持翻页
                'limit': str(len(vod_list)),
                'total': str(len(vod_list))
            }
        except Exception as e:
            print('[JinriCP] _fans_category_content err: ' + str(e))
            return self._empty_list(pg)

    # ==================== 详情 ====================

    def detailContent(self, ids):
        """
        点击某个文件夹后，请求该文件夹页面，列出所有 m3u8 文件作为播放列表。
        ids: [vod_id]，vod_id 为文件夹列表页 URL 或 m3u8 直链
        """
        if not ids:
            return {'list': []}

        vod_id = ids[0]

        # 如果已经是 m3u8 直链，直接返回单集
        if '.m3u8' in vod_id:
            name = self._extract_filename(vod_id)
            return {'list': [{
                'vod_id': vod_id,
                'vod_name': name,
                'vod_pic': '',
                'vod_play_from': 'JinriCP',
                'vod_play_url': '播放$' + vod_id
            }]}

        # 请求文件夹页面
        try:
            resp = self.session.get(vod_id, timeout=self._timeout)
            if resp.status_code != 200:
                return {'list': []}

            html = resp.text
            tid = self._extract_tid(vod_id)

            # 解析 m3u8 文件列表
            play_items = self._parse_m3u8_items(html, tid)

            # 尝试提取封面图
            cover_url = self._find_cover_image(html, tid)

            if play_items:
                # 构造播放列表: 名称$URL#名称$URL#...
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
            else:
                return {'list': []}
        except Exception as e:
            print('[JinriCP] detailContent err: ' + str(e))
            return {'list': []}

    # ==================== 播放（核心：m3u8 + 字幕） ====================

    def playerContent(self, flag, id, vipFlags=None):
        """
        返回播放地址和字幕地址。
        id: m3u8 文件完整 URL
        parse=0 表示直链播放，TVBox 直接用播放器加载 m3u8
        subt 字段返回同名 .srt 字幕文件 URL
        """
        result = {
            'parse': '0',
            'playUrl': '',
            'url': id,
            'header': {
                'User-Agent': UA,
                'Referer': HOST + '/'
            }
        }

        # 自动构造字幕 URL：将 .m3u8 替换为 .srt
        if '.m3u8' in id:
            srt_url = id.rsplit('.m3u8', 1)[0] + '.srt'
            result['subt'] = srt_url
            print('[JinriCP] 字幕: ' + srt_url)

        return result

    # ==================== 搜索 ====================

    def searchContent(self, key, quick, pg='1'):
        """
        本站无搜索 API，通过遍历各季度的文件夹名进行关键词匹配。
        使用 ThreadPoolExecutor 并发请求，提升搜索速度。
        """
        results = []

        def _search_one(cat):
            tid = cat['type_id']
            cat_name = cat['type_name']
            try:
                url = '{}/{}/'.format(HOST, tid)
                resp = self.session.get(url, timeout=10)
                if resp.status_code != 200:
                    return []
                items = self._parse_items(resp.text, tid)
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

        # 并发搜索所有分类
        cats = _cached_categories or []
        try:
            with ThreadPoolExecutor(max_workers=5) as executor:
                futures = [executor.submit(_search_one, cat) for cat in cats]
                for future in as_completed(futures):
                    try:
                        results.extend(future.result())
                    except:
                        pass
        except:
            # 并发失败时退回串行
            for cat in cats:
                results.extend(_search_one(cat))

        return results

    # ==================== 工具方法 ====================

    def _fetch_categories(self):
        """
        动态获取分类列表 —— 完全从网站侧边栏 HTML 解析，不依赖硬编码。
        
        网站每个页面都包含相同的侧边栏，所以从任意可用页面获取即可。
        首页可能因服务器 PHP 错误不可用，因此依次尝试多个已知页面。
        未来网站新增的分类会自动出现在侧边栏中，无需修改代码。

        侧边栏 HTML 有两种 <a> 结构:
          1) <a href="/bu/" class="mdui-list-item mdui-ripple">JinriCP第一季</a>
          2) <a href="/fans" class="mdui-list-item mdui-ripple">
               <i ...>web</i>
               <div class="mdui-list-item-content">粉丝房分享</div>
             </a>

        排除规则:
          - 外链 (http 开头: t.me, azurewebsites 等)
          - 播放器页面 (/player/)
          - 已知非分类路径 (_EXCLUDE_PATHS)
        """
        # 依次尝试多个页面获取侧边栏 HTML
        # 每个分类页面的侧边栏内容完全一致
        candidate_urls = [
            HOST + '/bu/',   # JinriCP 第一季（最稳定，几乎不可能下线）
            HOST + '/s2/',   # JinriCP 第二季
            HOST + '/pc/',   # PandaClass 第一季
            HOST + '/',      # 首页（可能恢复）
        ]

        html = None
        for url in candidate_urls:
            try:
                resp = self.session.get(url, timeout=self._timeout)
                if resp.status_code != 200:
                    continue
                text = resp.text
                # 确认页面包含侧边栏 HTML（而非 PHP 错误页）
                if 'mdui-list-item' in text and 'mdui-ripple' in text:
                    html = text
                    print('[JinriCP] 侧边栏来源: ' + url)
                    break
            except:
                continue

        if html is None:
            print('[JinriCP] 所有页面均不可用, 分类列表为空')
            return []

        categories = []

        # 匹配侧边栏导航链接，提取 href 和对应的文字
        # 文字可能在 <a>直接文本</a> 或 <a><div>文本</div></a> 中
        pattern = (
            r'<a\s+href="(/[a-zA-Z0-9_]+)/?"\s+class="mdui-list-item\s+mdui-ripple"[^>]*>'
            r'(.*?)'
            r'</a>'
        )

        seen_tids = set()
        for m in re.finditer(pattern, html, re.S):
            raw_path = m.group(1)  # 如 /bu, /s2, /fans
            inner = m.group(2)    # <a> 标签内部内容

            # 去掉前导 /
            tid = raw_path.lstrip('/')

            # 排除非分类页面
            if tid in _EXCLUDE_PATHS:
                continue
            # 排除重复
            if tid in seen_tids:
                continue

            # 提取分类名称: 优先 mdui-list-item-content 中的文字，否则取纯文本
            name = ''
            content_match = re.search(
                r'mdui-list-item-content[^>]*>([^<]+)</div>', inner, re.S
            )
            if content_match:
                name = content_match.group(1).strip()
            else:
                # 去掉所有标签，取纯文本
                name = re.sub(r'<[^>]+>', '', inner).strip()

            if not name:
                continue

            seen_tids.add(tid)
            categories.append({
                'type_id': tid,
                'type_name': name
            })

        if categories:
            print('[JinriCP] 动态获取到 ' + str(len(categories)) + ' 个分类: ' +
                  ', '.join(c['type_name'] for c in categories))
            return categories
        else:
            print('[JinriCP] 动态获取分类为空')
            return []

    def _parse_items(self, html, tid):
        """
        解析文件目录页面 HTML，提取文件夹和 m3u8 文件列表。
        HTML 结构:
          <li class="mdui-list-item ..." data-sort-name="xxx" data-sort-size="xxx">
            <a href="xxx">...</a>
          </li>
        data-sort-size="-" 表示文件夹，否则为文件
        """
        result = []

        # 正则: data-sort-name → data-sort-size → href（同一 <li> 内）
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
                # 文件夹：作为可点击的下一级列表项
                result.append({
                    'vod_name': name,
                    'vod_id': self._fix_url(href, tid),
                    'vod_pic': '',
                    'vod_remarks': '📁'
                })
            elif '.m3u8' in name:
                # m3u8 文件：作为可播放的视频项
                display_name = self._safe_unquote(name.replace('.m3u8', ''))
                result.append({
                    'vod_name': display_name,
                    'vod_id': self._fix_url(href, tid),
                    'vod_pic': '',
                    'vod_remarks': size or '▶️'
                })
            # 其他文件类型（.srt, .txt, .jpg, .md 等）不显示在列表中

        return result

    def _parse_m3u8_items(self, html, tid):
        """
        从文件夹页面解析所有 m3u8 文件，返回播放列表。
        """
        result = []

        pattern = (
            r'data-sort-name="([^"]+\.m3u8)"'
            r'[^>]*>.*?href="([^"]+)"'
        )

        for m in re.finditer(pattern, html, re.S):
            raw_name = m.group(1)
            href = m.group(2)
            display_name = self._safe_unquote(raw_name.replace('.m3u8', ''))
            result.append({
                'name': display_name,
                'url': self._fix_url(href, tid)
            })

        return result

    def _find_cover_image(self, html, tid):
        """尝试从文件夹页面提取封面图（.jpg 文件）"""
        pattern = (
            r'data-sort-name="([^"]+\.jpg)"'
            r'[^>]*>.*?href="([^"]+)"'
        )
        m = re.search(pattern, html, re.S)
        if m:
            return self._fix_url(m.group(2), tid)
        return ''

    def _fix_url(self, href, tid):
        """
        将相对 URL 转为完整 URL。
        - http:// → 原样返回
        - // → https://
        - /bu/... → HOST + href（文件夹链接）
        - ./xxx → HOST/tid/xxx（文件链接，相对于季度根目录）
        """
        if not href:
            return ''
        if href.startswith('http'):
            return href
        if href.startswith('//'):
            return 'https:' + href
        if href.startswith('/'):
            return HOST + href
        # ./folder/file.m3u8 → HOST/tid/folder/file.m3u8
        if href.startswith('./'):
            href = href[2:]
        return '{}/{}/{}'.format(HOST, tid, href)

    def _extract_tid(self, url):
        """从 URL 中提取 tid（如 /bu/ → bu, /s2/ → s2, /pc3/ → pc3）"""
        m = re.search(r'5721004\.xyz/(\w+)/', url)
        if m:
            return m.group(1)
        # 从 path 参数提取
        m = re.search(r'path=/(\w+)/', url)
        if m:
            return m.group(1)
        return 'bu'

    def _extract_folder_name(self, url):
        """从 URL 中提取文件夹名用于显示"""
        # 处理 https://5721004.xyz/bu/?/3.25/ 格式
        m = re.search(r'\?/([^/]+)/?$', url)
        if m:
            return self._safe_unquote(m.group(1))
        # 处理 https://5721004.xyz/s2/ 格式
        m = re.search(r'5721004\.xyz/(\w+)/?$', url)
        if m:
            return m.group(1)
        # 兜底: 取最后一段路径
        parts = url.rstrip('/').split('/')
        return self._safe_unquote(parts[-1]) if parts else url

    def _extract_filename(self, url):
        """从 URL 中提取文件名（去掉扩展名）"""
        name = url.split('/')[-1]
        name = self._safe_unquote(name)
        if '.m3u8' in name:
            name = name.replace('.m3u8', '')
        return name

    def _safe_unquote(self, text):
        """安全 URL 解码"""
        try:
            return unquote(text)
        except:
            return text

    def _empty_list(self, pg):
        """返回空列表结果"""
        return {
            'list': [],
            'page': str(pg),
            'pagecount': '1',
            'limit': '0',
            'total': '0'
        }

    # ==================== 基类必需方法 ====================

    def isVideoFormat(self, url):
        """判断 URL 是否为视频格式"""
        return '.m3u8' in url or '.mp4' in url

    def manualVideoCheck(self):
        """是否需要手动视频检查"""
        return False

    def localProxy(self, param):
        """本地代理（本站不需要）"""
        return {}
