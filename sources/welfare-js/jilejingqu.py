# -*- coding: utf-8 -*-
"""
极乐禁区 TVBox Spider — vbox 适配版
站点: https://iegeewiet-4mag.hscwang26y2m.xyz

vbox 适配：
1. 域名注入：读取 _vbox_effective_hosts 优先使用注入域名
2. requests.Session 自动走 base/spider.py 的域名/代理注入
3. playerContent header → dict 格式（vbox 要求）
4. 继承 base.spider.Spider，使用 self.fetch/self.post
5. localProxy 图片代理（防盗链）
6. _get_pagecount 增加 fallback
"""
import sys, re, json, html, warnings
from urllib.parse import urljoin, quote, unquote
warnings.filterwarnings("ignore")

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

UA = "Mozilla/5.0 (Linux; Android 13; Mobile) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Mobile Safari/537.36"

# 默认域名（fallback）
DEFAULT_HOST = 'https://iegeewiet-4mag.hscwang26y2m.xyz'
DEFAULT_HOME_URL = DEFAULT_HOST + '/jlhs'

# 特殊分类（二级目录）
_SPECIAL_CATS = {
    '百大女优': DEFAULT_HOST + '/label/sortjp/',
    '番号仓库': DEFAULT_HOST + '/label/sortnu/',
    '国产传媒': DEFAULT_HOST + '/label/sortcn/',
    '91探花': DEFAULT_HOST + '/label/sortfl/',
}

# 视频分类
_VIDEO_CATS = [
    {'type_id': '45', 'type_name': '视频一区'},
    {'type_id': '46', 'type_name': '视频二区'},
    {'type_id': '47', 'type_name': '视频三区'},
]

# 子类型筛选（放入分类）
_SUB_TYPES = {
    '45': [
        {'n': '全部', 'v': ''},
        {'n': '精品日韩', 'v': '51'},
        {'n': '国产精品', 'v': '49'},
        {'n': '日韩无码', 'v': '50'},
        {'n': '中文字幕', 'v': '52'},
        {'n': '欧美极品', 'v': '53'},
        {'n': '动漫精品', 'v': '54'},
        {'n': '淫欲痴女', 'v': '55'},
        {'n': 'SM变态', 'v': '56'},
    ],
    '46': [
        {'n': '全部', 'v': ''},
        {'n': '偷拍偷窥', 'v': '57'},
        {'n': '性感人妻', 'v': '61'},
        {'n': '网红主播', 'v': '64'},
        {'n': '黑丝诱惑', 'v': '63'},
        {'n': '三级伦理', 'v': '62'},
        {'n': '童颜巨乳', 'v': '58'},
        {'n': '明星换脸', 'v': '517'},
        {'n': '女优明星', 'v': '59'},
    ],
    '47': [
        {'n': '全部', 'v': ''},
        {'n': '国产自拍', 'v': '66'},
        {'n': '剧情解说', 'v': '68'},
        {'n': '网曝黑料', 'v': '71'},
        {'n': '萝莉少女', 'v': '73'},
        {'n': '同性世界', 'v': '70'},
        {'n': '制服诱惑', 'v': '69'},
        {'n': '网曝吃瓜', 'v': '67'},
        {'n': '门事件', 'v': '72'},
    ],
}

# 传媒类分类
_MEDIA_CATS = [
    {'type_id': '202', 'type_name': '麻豆传媒'},
    {'type_id': '205', 'type_name': '天美传媒'},
    {'type_id': '206', 'type_name': '果冻传媒'},
    {'type_id': '207', 'type_name': '91制片厂'},
    {'type_id': '208', 'type_name': '蜜桃传媒'},
    {'type_id': '209', 'type_name': '精东影业'},
    {'type_id': '210', 'type_name': '皇家华人'},
    {'type_id': '223', 'type_name': '星空传媒'},
]

# 女优类分类
_ACTRESS_CATS = [
    {'type_id': '401', 'type_name': '梦乃爱华'},
    {'type_id': '402', 'type_name': '波多野结衣'},
    {'type_id': '404', 'type_name': '河北彩花'},
    {'type_id': '409', 'type_name': '桃乃木香奈'},
    {'type_id': '412', 'type_name': '相泽南'},
    {'type_id': '414', 'type_name': 'Miru'},
    {'type_id': '419', 'type_name': '木下日葵'},
    {'type_id': '429', 'type_name': '明里紬'},
]

# 番号类分类
_CODE_CATS = [
    {'type_id': '301', 'type_name': '200GANA'},
    {'type_id': '302', 'type_name': '300MIUM'},
    {'type_id': '308', 'type_name': '300MAAN'},
    {'type_id': '309', 'type_name': '300NTK'},
    {'type_id': '313', 'type_name': '336KNB'},
    {'type_id': '329', 'type_name': 'AARM'},
    {'type_id': '345', 'type_name': 'DVAJ'},
    {'type_id': '326', 'type_name': 'MUDR'},
]

# 91探花类分类
_TANFLOWER_CATS = [
    {'type_id': '501', 'type_name': '91沈先生'},
    {'type_id': '502', 'type_name': '文轩探花'},
    {'type_id': '503', 'type_name': '千人斩'},
    {'type_id': '509', 'type_name': '李寻欢探花'},
    {'type_id': '513', 'type_name': '酒店'},
    {'type_id': '514', 'type_name': '小宝寻花'},
    {'type_id': '515', 'type_name': '午夜寻花'},
    {'type_id': '516', 'type_name': '91系列'},
]


class Spider(_B):
    def init(self, extend=""):
        self.extend = extend
        self.host = DEFAULT_HOST
        self.home_url = DEFAULT_HOME_URL
        self._session = requests.Session() if requests else None
        if self._session:
            self._session.headers.update({'User-Agent': UA})
            self._session.verify = False

        # ✅ vbox 域名注入：优先使用注入的域名
        try:
            effective_hosts = globals().get('_vbox_effective_hosts', [])
            if effective_hosts and len(effective_hosts) > 0:
                self.host = effective_hosts[0].rstrip('/')
                self.home_url = self.host + '/jlhs'
                print('[极乐禁区] 使用注入域名: ' + self.host)
        except Exception as e:
            print('[极乐禁区] 读取注入域名失败: ' + str(e))

        return '{}'

    def getName(self):
        return '极乐禁区'

    def isVideoFormat(self, url):
        return False

    def manualVideoCheck(self):
        return False

    def destroy(self):
        if self._session:
            self._session.close()

    # ==================== 内部工具 ====================

    def _headers(self, referer=None):
        return {'User-Agent': UA, 'Referer': referer or self.host}

    def _get(self, url, referer=None):
        """使用 base/spider.py 的 self.fetch 方法（自动走域名注入和代理）"""
        hdrs = self._headers(referer)
        try:
            text = self.fetch(url, headers=hdrs)
            if not text:
                return ''
            # 处理编码
            if hasattr(self, '_encoding'):
                try:
                    text = text.encode('latin-1').decode(self._encoding)
                except Exception:
                    pass
            return text
        except Exception as e:
            print('[极乐禁区] fetch error: ' + str(e))
            return ''

    def _clean(self, s):
        """清理 HTML 标签并解码实体"""
        if not s:
            return ''
        s = html.unescape(s)
        s = re.sub(r'<[^>]+>', '', s)
        s = re.sub(r'&#(\d+);', lambda m: chr(int(m.group(1))), s)
        return re.sub(r'\s+', ' ', s).strip()

    def _href(self, h):
        """补全相对 URL"""
        if not h:
            return ''
        h = h.replace('\\/', '/')
        h = unquote(h)
        return urljoin(self.host, h)

    @staticmethod
    def _extract(text, rule):
        """TVBox JSON 规则提取: prefix&&suffix 格式"""
        parts = rule.split('&&')
        if len(parts) != 2:
            return ''
        prefix, suffix = parts
        idx = text.find(prefix)
        if idx == -1:
            return ''
        start = idx + len(prefix)
        end = text.find(suffix, start)
        if end == -1:
            return ''
        return text[start:end]

    def _fix_pic(self, pic):
        """补全图片 URL"""
        if not pic:
            return ''
        pic = html.unescape(pic.replace('\\/', '/'))
        pic = unquote(pic)
        if not pic.startswith('http'):
            pic = self._href(pic)
        return pic

    def _get_pagecount(self, text):
        """获取总页数"""
        m = re.search(r'href="[^"]*-(\d+)/?"[^>]*title="尾页"', text, re.I)
        if m:
            return int(m.group(1))
        nums = re.findall(r'class="page_link"\s+href="[^"]*-(\d+)/', text)
        if nums:
            max_page = max(int(n) for n in nums)
            if max_page > 1:
                return max_page
        m = re.search(r'共\s*(\d+)\s*页', text)
        if m:
            return int(m.group(1))
        if '下一页' in text or '尾页' in text:
            return 2
        return 1

    # ==================== 列表解析 ====================

    def _parse_video_list(self, text):
        """解析视频列表（分类页、首页通用）"""
        out = []
        # 移除 HTML 注释（广告占位）
        text = re.sub(r'<!--.*?-->', '', text, flags=re.DOTALL)
        segments = text.split('</li>')
        for seg in segments:
            block = self._extract(seg, '<a class="thumbnail"&&</div>')
            if not block:
                continue
            # 标题
            title = self._clean(self._extract(block, '">&&</a></h5>'))
            if not title:
                continue
            # 副标题
            subtitle = self._clean(self._extract(block, '<p>&&</p>'))
            # 封面图
            pic = self._fix_pic(self._extract(block, 'data-original="&&"'))
            if not pic:
                pic = self._fix_pic(self._extract(block, '<img src="&&"'))
            # vod_id
            vod_id = self._extract(seg, '<a href="/voddetail/&&/')
            if not vod_id:
                continue
            play_url = self.host + '/vodplay/' + vod_id + '-1-1/'
            out.append({
                'vod_id': play_url,
                'vod_name': title,
                'vod_pic': pic,
                'vod_remarks': subtitle,
            })
        return out

    def _parse_search_list(self, text):
        """解析搜索结果列表"""
        out = []
        text = re.sub(r'<!--.*?-->', '', text, flags=re.DOTALL)
        segments = text.split('</li>')
        for seg in segments:
            block = self._extract(seg, '<a class="thumbnail"&&</div>')
            if not block:
                continue
            title = self._clean(self._extract(block, 'title="&&"'))
            if not title:
                title = self._clean(self._extract(block, '">&&</a></h5>'))
            if not title:
                continue
            pic = self._fix_pic(self._extract(block, '<img src="&&"'))
            if not pic:
                pic = self._fix_pic(self._extract(block, 'data-original="&&"'))
            vod_id = self._extract(seg, '<a href="/voddetail/&&/')
            if not vod_id:
                continue
            play_url = self.host + '/vodplay/' + vod_id + '-1-1/'
            out.append({
                'vod_id': play_url,
                'vod_name': title,
                'vod_pic': pic,
                'vod_remarks': '',
            })
        return out

    def _parse_special_list(self, text, cate_pg=1):
        """解析特殊分类列表（百大女优/番号仓库/国产传媒/91探花）"""
        out = []
        # 移除注释
        text = re.sub(r'<!--.*?-->', '', text, flags=re.DOTALL)
        for m in re.finditer(r'<li>\s*<a\s+hr', text, re.I):
            end = text.find('</li>', m.start())
            if end == -1:
                continue
            block = text[m.start():end + 5]
            title = self._clean(self._extract(block, '#;">&&</span>'))
            if not title:
                continue
            pic = self._fix_pic(self._extract(block, '<img src="&&"'))
            href_m = re.search(r'href="([^"]+)"', block)
            if not href_m:
                continue
            href = href_m.group(1)
            if not href.startswith('http'):
                href = self._href(href)
            play_url = href.rstrip('/') + '-' + str(cate_pg) + '/'
            out.append({
                'vod_id': play_url,
                'vod_name': title,
                'vod_pic': pic,
                'vod_remarks': '',
                'vod_tag': 'folder',
            })
        return out

    # ==================== TVBox 接口 ====================

    def homeContent(self, filter=False):
        """首页分类"""
        categories = []

        # 特殊分类
        for name in self._special_cats:
            categories.append({
                'type_id': 'special_' + name,
                'type_name': name,
            })

        # 视频分类及子类型
        for cat in self._video_cats:
            categories.append({
                'type_id': cat['type_id'],
                'type_name': cat['type_name'],
            })
            tid = cat['type_id']
            if tid in self._sub_types:
                for sub in self._sub_types[tid]:
                    if sub['v']:
                        # ✅ 子类型加前缀避免 type_id 冲突
                        categories.append({
                            'type_id': tid + '_' + sub['v'],
                            'type_name': sub['n'],
                        })

        # 传媒类分类
        for cat in self._media_cats:
            categories.append({
                'type_id': cat['type_id'],
                'type_name': cat['type_name'],
            })

        # 女优类分类
        for cat in self._actress_cats:
            categories.append({
                'type_id': cat['type_id'],
                'type_name': cat['type_name'],
            })

        # 番号类分类
        for cat in self._code_cats:
            categories.append({
                'type_id': cat['type_id'],
                'type_name': cat['type_name'],
            })

        # 91探花类分类
        for cat in self._tanflower_cats:
            categories.append({
                'type_id': cat['type_id'],
                'type_name': cat['type_name'],
            })

        return {'class': categories}

    def homeVideoContent(self):
        """首页视频列表"""
        text = self._get(self.home_url)
        return {'list': self._parse_video_list(text)}

    def categoryContent(self, tid, pg=1, filter=False, extend=None):
        """分类内容"""
        page = int(pg) if pg else 1
        tid = str(tid)

        # 特殊分类（二级目录）
        if tid.startswith('special_'):
            cat_name = tid[8:]
            url = self._special_cats.get(cat_name, '')
            if not url:
                return {'page': page, 'pagecount': 1, 'list': []}
            if page != 1:
                url = url.rstrip('/') + '/' + str(page) + '/'
            text = self._get(url)
            items = self._parse_special_list(text, page)
            pc = self._get_pagecount(text)
            return {
                'page': page,
                'pagecount': pc,
                'limit': len(items),
                'total': pc * len(items) if items else 0,
                'list': items,
            }

        # URL 类型的 tid（来自特殊分类子项点击）
        if tid.startswith('http') or tid.startswith('/'):
            url = tid if tid.startswith('http') else self._href(tid)
            url = re.sub(r'-\d+$', '', url.rstrip('/'))
            url = url + '-' + str(page) + '/'
            text = self._get(url)
            items = self._parse_video_list(text)
            pc = self._get_pagecount(text)
            return {
                'page': page,
                'pagecount': pc,
                'limit': len(items),
                'total': pc * len(items) if items else 0,
                'list': items,
            }

        # 子类型: '45_51' → parent=45, sub=51
        if '_' in tid and not tid.startswith('special_'):
            parts = tid.split('_')
            if len(parts) == 2:
                sub_id = parts[1]
                url = self.host + '/vodtype/' + sub_id + '-' + str(page) + '/'
                text = self._get(url)
                items = self._parse_video_list(text)
                pc = self._get_pagecount(text)
                return {
                    'page': page,
                    'pagecount': pc,
                    'limit': len(items),
                    'total': pc * len(items) if items else 0,
                    'list': items,
                }

        # 视频分类
        url = self.host + '/vodtype/' + tid + '-' + str(page) + '/'

        # 处理 extend 筛选
        if extend:
            if isinstance(extend, str):
                try:
                    extend = json.loads(extend)
                except Exception:
                    extend = {}
            sub_type = extend.get('type', '')
            if sub_type:
                url = self.host + '/vodtype/' + sub_type + '-' + str(page) + '/'

        text = self._get(url)
        items = self._parse_video_list(text)
        pc = self._get_pagecount(text)
        return {
            'page': page,
            'pagecount': pc,
            'limit': len(items),
            'total': pc * len(items) if items else 0,
            'list': items,
        }

    def searchContent(self, key, quick=False, pg='1'):
        """搜索"""
        page = int(pg) if pg else 1
        wd = quote(str(key))
        url = self.host + '/vodsearch/' + wd + '----------' + str(page) + '---/'
        text = self._get(url)
        items = self._parse_search_list(text)
        pc = self._get_pagecount(text)
        if pc <= page and len(items) >= 12:
            pc = page + 1
        return {
            'page': page,
            'pagecount': pc,
            'limit': len(items),
            'total': len(items),
            'list': items,
        }

    def detailContent(self, ids):
        """详情页"""
        u = ids[0] if isinstance(ids, (list, tuple)) else str(ids)
        if not str(u).startswith('http'):
            u = self._href(str(u))

        text = self._get(u)

        # 标题
        title = ''
        m = re.search(r'<h5[^>]*>(.*?)</h5>', text, re.I | re.S)
        if m:
            title = self._clean(m.group(1))
        if not title:
            m = re.search(r'<h1[^>]*>(.*?)</h1>', text, re.I | re.S)
            if m:
                title = self._clean(m.group(1))
        if not title:
            m = re.search(r'<title>(.*?)</title>', text, re.I | re.S)
            if m:
                raw_title = self._clean(m.group(1))
                for prefix in ['在线观看', '极乐禁区']:
                    if raw_title.startswith(prefix):
                        raw_title = raw_title[len(prefix):]
                title = raw_title.split('-')[0].split('_')[0].strip()

        # 图片
        pic = ''
        m = re.search(r'data-original="([^"]+)"', text)
        if m:
            pic = m.group(1)
        if not pic:
            m = re.search(r'<meta[^>]+property="og:image"[^>]+content="([^"]+)', text, re.I)
            if m:
                pic = m.group(1)
        if not pic:
            m = re.search(r'<img[^>]+src="([^"]+)"', text)
            if m:
                pic = m.group(1)
        pic = self._fix_pic(pic)

        # 简介
        content = ''
        m = re.search(r'<meta[^>]+name="description"[^>]+content="([^"]+)', text, re.I)
        if m:
            content = self._clean(m.group(1))

        vod = {
            'vod_id': u,
            'vod_name': title,
            'vod_pic': pic,
            'vod_content': content,
            'vod_play_from': '极乐禁区',
            'vod_play_url': '正片$' + u,
        }
        return {'list': [vod]}

    def playerContent(self, flag, id, vipFlags=None):
        """播放（✅ header 改为 dict 格式）"""
        url = str(id)

        if not re.search(r'\.(?:m3u8|mp4|flv)(?:$|[?#])', url, re.I):
            try:
                text = self._get(url)
                # 从 player_aaaa 变量提取视频URL
                m = re.search(r'var\s+player_aaaa\s*=\s*(\{.*?\})\s*</script>', text, re.S)
                if m:
                    try:
                        data = json.loads(m.group(1))
                        vurl = data.get('url', '')
                        if vurl:
                            url = vurl
                    except Exception:
                        pass
                # 嗅探 .m3u8 和 .mp4
                if not re.search(r'\.(?:m3u8|mp4)(?:$|[?#])', url, re.I):
                    m = re.search(r'(https?://[^\s"\'<>]+?\.(?:m3u8|mp4)[^\s"\'<>]*)', text, re.I)
                    if m:
                        url = m.group(1)
                # 从 iframe 提取
                if not re.search(r'\.(?:m3u8|mp4)(?:$|[?#])', url, re.I):
                    m = re.search(r'<iframe[^>]+src="([^"]+)"', text, re.I)
                    if m:
                        iframe_url = self._href(m.group(1))
                        try:
                            iframe_text = self._get(iframe_url)
                            m2 = re.search(r'(https?://[^\s"\'<>]+?\.(?:m3u8|mp4)[^\s"\'<>]*)', iframe_text, re.I)
                            if m2:
                                url = m2.group(1)
                        except Exception:
                            pass
            except Exception as e:
                print('[极乐禁区] playerContent err: ' + str(e))

        # ✅ 使用 dict 格式（不是字符串）
        return {
            'Parse': 0,
            'jx': 0,
            'playUrl': '',
            'url': url,
            'header': {
                'User-Agent': UA,
                'Referer': self.host,
            }
        }

    def localProxy(self, param):
        """图片代理（防盗链）"""
        try:
            from urllib.parse import parse_qs, urlparse
            parsed = urlparse(param)
            qs = parse_qs(parsed.query)
            img_url = qs.get('url', [''])[0]

            if not img_url:
                return [404, 'text/plain', b'']

            r = self._session.get(img_url, headers={
                'User-Agent': UA,
                'Referer': self.host + '/',
            }, timeout=10, verify=False)

            content_type = r.headers.get('Content-Type', 'image/jpeg')
            return [200, content_type, r.content]
        except Exception as e:
            print('[极乐禁区] localProxy err: ' + str(e))
            return [404, 'text/plain', b'']
