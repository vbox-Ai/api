# -*- coding: utf-8 -*-
"""
番号网 (fanhaowang) TVBox Spider — vbox 适配版
站点: web.fanhaowang1.cc

vbox 适配：
1. 基类导入 try/except + as _B（修复类名冲突）
2. urllib.request → requests.get（走基类 patch，自动 SSL 绕过/域名注入）
3. 补 getDependence + warnings + homeVideoContent + filters
4. playerContent 补 Referer + 递归深度限制
5. eval packer 解密逻辑原样保留（核心特色）
6. localProxy 返回 pass
"""
import sys, re, json, html as htmllib, warnings
from urllib.parse import quote

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
try:
    import urllib3
    urllib3.disable_warnings()
except ImportError:
    pass


class Spider(_B):

    def getDependence(self):
        return ['requests']

    def __init__(self):
        self.host = 'https://web.fanhaowang1.cc'
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/120 Safari/537.36',
            'Accept-Language': 'zh-CN,zh;q=0.9',
        }
        self.classes = [
            ('兔儿资源', '286'), ('精品推荐', '304'), ('主播秀色', '305'),
            ('日本有码', '306'), ('日本无码', '307'), ('中文字幕', '308'),
            ('童颜巨乳', '309'), ('性感人妻', '310'), ('强歼乱伦', '311'),
            ('欧美情色', '312'), ('三级伦理', '313'), ('卡通动漫', '314'),
            ('丝袜OL', '315'), ('剧情介绍', '316'), ('网曝系列', '317'),
            ('相同性别', '318'), ('探花', '319'), ('国产人妻', '320'),
            ('国产SM', '321'), ('国产丝袜', '322'),
        ]

    def getName(self):
        return '番号网'

    def init(self, extend=''):
        if extend and extend.startswith('http'):
            self.host = extend.rstrip('/')

    def isVideoFormat(self, url):
        return url and url.endswith(('.m3u8', '.mp4', '.flv', '.avi', '.mkv'))

    def manualVideoCheck(self):
        return False

    def destroy(self):
        pass

    # ============================================================
    # 工具
    # ============================================================
    def fetch(self, url, headers=None, timeout=20):
        """使用 requests.get，走基类 patch"""
        try:
            r = requests.get(url, headers=headers or self.headers, timeout=timeout, verify=False)
            r.encoding = 'utf-8'
            return r.text
        except Exception as e:
            print(f"[番号网] 请求失败: {url} -> {e}")
            return ""

    def clean(self, s):
        return re.sub(r'\s+', ' ', htmllib.unescape(re.sub(r'<.*?>', '', s or ''))).strip()

    def abs(self, u):
        return u if u.startswith('http') else self.host + u

    def pic_proxy(self, u):
        u = htmllib.unescape(u or '').replace('&#x2F;', '/').replace('&#x3D;', '=')
        if u.startswith('//'):
            u = 'https:' + u
        return u

    def field(self, html, name):
        m = re.search(r'<[^>]*>' + name + r'<[^>]*>\s*<[^>]*>([^<]*)', html)
        return self.clean(m.group(1)) if m else ''

    # ============================================================
    # 首页
    # ============================================================
    def homeContent(self, filter):
        return {
            'class': [{'type_name': n, 'type_id': i} for n, i in self.classes],
            'filters': {}
        }

    def homeVideoContent(self):
        try:
            html = self.fetch(self.host + '/' + self.classes[0][1])
            return {"list": self.parse_list(html)}
        except Exception:
            return {"list": []}

    # ============================================================
    # 分类列表
    # ============================================================
    def categoryContent(self, tid, pg, filter, extend):
        result = {}
        try:
            pg = int(pg) if pg else 1
            url = self.host + '/' + tid
            if pg > 1:
                url += '?page=' + str(pg)
            html = self.fetch(url)
            result['list'] = self.parse_list(html)
            result['page'] = pg
            result['pagecount'] = 999
            result['limit'] = len(result.get('list', []))
            result['total'] = 999 * 24
        except Exception:
            result['list'] = []
            result['page'] = 1
            result['pagecount'] = 1
            result['limit'] = 0
            result['total'] = 0
        return result

    # ============================================================
    # 列表解析
    # ============================================================
    def parse_list(self, html):
        arr, seen = [], set()
        for m in re.finditer(r'<a\s+href="([^"]+)"[^>]*>.*?<img[^>]+(?:data-src|src)="([^"]*)"[^>]*>.*?</a>', html, re.S | re.I):
            vid = m.group(1)
            pic = m.group(2)
            if vid in seen or not vid or vid.startswith('http'):
                continue
            seen.add(vid)
            # 提取标题
            title = ''
            tm = re.search(r'<a[^>]*href="' + re.escape(vid) + r'"[^>]*>(.*?)</a>', html[m.start():m.start() + 800], re.S)
            if tm:
                title = self.clean(tm.group(1))
            if len(title) < 2:
                continue
            pic = self.pic_proxy(pic)
            # 时长
            dur = ''
            dm = re.search(r'<span[^>]*>(\s*\d{1,2}:\d{2}(?::\d{2})?\s*)</span>', html[m.start():m.start() + 600], re.S)
            if dm:
                dur = dm.group(1).strip()
            arr.append({'vod_id': vid, 'vod_name': title, 'vod_pic': pic, 'vod_remarks': dur})
        return arr

    # ============================================================
    # 详情
    # ============================================================
    def detailContent(self, ids):
        result = {}
        try:
            vid = ids[0] if isinstance(ids, list) else ids
            url = vid if vid.startswith('http') else self.host + vid
            html = self.fetch(url)
            # 标题
            title = self.clean((re.search(r'<meta property="og:title" content="([^"]*)"', html) or
                                re.search(r'<title>(.*?)</title>', html, re.S) or ['', ''])[1])
            # 封面
            pic = ''
            pm = re.search(r'<meta property="og:image" content="([^"]*)"', html)
            if pm:
                pic = htmllib.unescape(pm.group(1)).replace('&#x2F;', '/').replace('&#x3D;', '=')
            # 简介
            desc = self.clean((re.search(r'<meta property="og:description"\s*content="([^"]*)"', html, re.S) or ['', ''])[1])
            # 信息
            year = self.field(html, '发行日期') or self.field(html, '年份') or self.field(html, '上映时间')
            director = self.field(html, '导演')
            actresses = self.field(html, '演员') or self.field(html, '主演')
            # 播放源（eval packer 解密）
            sources = self.unpack_sources(html)
            play = []
            if sources:
                for k, u in sources:
                    play.append(k + '$' + u)
            else:
                play.append('播放$' + url)
            vod = {
                'vod_id': vid,
                'vod_name': title or vid.upper(),
                'vod_pic': pic,
                'vod_year': year,
                'vod_director': director,
                'vod_actor': actresses,
                'vod_content': desc,
                'vod_play_from': '$$$'.join([x.split('$')[0] for x in play]),
                'vod_play_url': '$$$'.join(play),
            }
            result['list'] = [vod]
        except Exception as e:
            print(f"[番号网] 详情解析失败: {e}")
            result['list'] = []
        return result

    # ============================================================
    # eval packer 解密（核心特色，原样保留）
    # ============================================================
    def unpack_sources(self, html):
        out = []
        p = re.search(r"eval\(function\(p,a,c,k,e,d\).*?\('(.*?)',\s*(\d+),\s*(\d+),\s*'([^']*)'\.split\('\|'\)", html, re.S)
        if not p:
            return out
        s, base, count, keys = p.group(1).replace("\\'", "'"), int(p.group(2)), int(p.group(3)), p.group(4).split('|')

        def b36(n):
            chars = '0123456789abcdefghijklmnopqrstuvwxyz'
            n = int(n)
            r = ''
            if n == 0:
                return '0'
            while n:
                r = chars[n % 36] + r
                n //= 36
            return r

        for c in range(count - 1, -1, -1):
            k = keys[c] if c < len(keys) else ''
            if k:
                s = re.sub(r'\b' + b36(c) + r'\b', k, s)
        for name, url in re.findall(r"(source(?:842|1280)?)='(https?://[^']+?\.m3u8)'", s):
            label = {'source': '原画', 'source842': '842x480', 'source1280': '1280x720'}.get(name, name)
            out.append((label, url))
        return out

    # ============================================================
    # 搜索
    # ============================================================
    def searchContent(self, key, quick, pg='1'):
        try:
            pg = int(pg) if pg else 1
            url = self.host + '/search/' + quote(key)
            html = self.fetch(url)
            return {
                'list': self.parse_list(html),
                'page': pg,
                'pagecount': pg + 1 if self.parse_list(html) else pg,
                'limit': 0,
                'total': 0
            }
        except Exception:
            return {'list': [], 'page': 1, 'pagecount': 1, 'limit': 0, 'total': 0}

    # ============================================================
    # 播放（递归加深度限制）
    # ============================================================
    def playerContent(self, flag, id, vipFlags, _depth=0):
        header = {
            'User-Agent': self.headers['User-Agent'],
            'Referer': self.host + '/',
        }
        if id and id.startswith('http') and '.m3u8' in id:
            return {'parse': 0, 'url': id, 'header': header}
        if _depth >= 2:
            return {'parse': 1, 'url': id if id.startswith('http') else self.abs(id), 'header': header}
        # id 是路径，调 detailContent 获取播放地址
        try:
            vid = id.split('/')[-1] if '/' in id else id
            d = self.detailContent([vid])
            if d.get('list'):
                play_url_str = d['list'][0].get('vod_play_url', '')
                # 按 flag 匹配线路
                for segment in play_url_str.split('$$$'):
                    parts = segment.split('$', 1)
                    if len(parts) == 2:
                        seg_flag, seg_url = parts
                        if seg_flag == flag and '.m3u8' in seg_url:
                            return {'parse': 0, 'url': seg_url, 'header': header}
                # flag 未匹配，返回第一条
                first = play_url_str.split('$$$')[0].split('$', 1)
                src = first[1] if len(first) > 1 else first[0]
                if '.m3u8' in src:
                    return {'parse': 0, 'url': src, 'header': header}
                return {'parse': 1, 'url': src, 'header': header}
        except Exception as e:
            print(f"[番号网] 播放解析失败: {e}")
        return {'parse': 0, 'url': '', 'header': header}

    def localProxy(self, param):
        pass
