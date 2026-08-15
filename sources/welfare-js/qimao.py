# -*- coding: utf-8 -*-
"""
55eejj.com (www.55eejj.com) TVBox 源
=================================================
永久主域名: https://www.55eejj.com/  (防止丢失，备用记录)
基于 ENC2 加密后端 (7maohd.xffll.com/api) 的纯 JSON 接口爬虫

【修复要点 (本版)】
1. 必带 project=xs 参数 —— 不带的话 /movie/list 返回的是失效旧域名
   (sq.2277ww.com 图床502 / down.baidu.com DNS失效)，带了之后返回
   可用新域名 (ddd.aisheji8.com / down.mm7878.com)，封面和播放都正常。
2. homeContent 正确解析 /movie/tags 的嵌套结构
   [{category, categoryShow, tags:[{id,name}]}]，展开成完整分类列表。
3. homeVideoContent 正确解析 /movie/home_sections 的 movies 数组。
4. detailContent 直接用 /movie/{id} 详情接口拿可用播放直链与封面。
5. 封面直链优先 (ddd.aisheji8.com 不防盗链)，localProxy 仅作兜底。
6. 播放带 Referer/Origin/UA，CDN 放行。

【接口】
- GET /movie/home_sections       首页各分类 (project=xs)
- GET /movie/list?page=&pageSize=&tagid=&keyword=  列表/搜索
- GET /movie/{movieid}           详情 (含可用 h264mp4url / smallpic)
- GET /movie/tags                 分类 (嵌套: category->tags[])
- GET /config/ini                 站点资源域名
=================================================
"""

import sys
import re
import json
import base64
from urllib.parse import quote, parse_qs

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
    # ---- 站点配置 ----
    host = 'https://www.55eejj.com'            # 前端站 (Referer / Origin 用)
    site_url = 'https://www.55eejj.com/'      # 永久主域名 (防止丢失，备用记录)
    api_base = 'https://7maohd.xffll.com/api'  # 后端 API (ENC2 密文解出来的)
    project = 'xs'                              # 必带！否则返回失效旧域名

    pic_host = 'https://ddd.aisheji8.com'      # 图床 (从详情接口动态刷新)
    enc_key = 'Mumu2026#'                       # ENC2 默认密钥

    # ---- HTTP 头 ----
    header = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0 Safari/537.36',
        'Accept': 'application/json, text/plain, */*',
        'Accept-Language': 'zh-CN,zh;q=0.9',
        'Referer': 'https://www.55eejj.com/',
        'Origin': 'https://www.55eejj.com',
    }

    # ---- 分类 (硬编码兜底, 真实分类从 /movie/tags 拉) ----
    classes = [
        {'type_name': '国产自拍', 'type_id': '1'},
        {'type_name': '综合强片', 'type_id': '90'},
        {'type_name': '家庭乱伦', 'type_id': '4'},
        {'type_name': '少女萝莉', 'type_id': '3'},
        {'type_name': '熟女少妇', 'type_id': '5'},
        {'type_name': '酒店探花', 'type_id': '7'},
        {'type_name': '偷拍盗摄', 'type_id': '8'},
        {'type_name': '醉酒迷奸', 'type_id': '37'},
        {'type_name': '吃瓜黑料', 'type_id': '38'},
        {'type_name': '直播裸聊', 'type_id': '2'},
        {'type_name': '巨乳诱惑', 'type_id': '76'},
        {'type_name': '户外野战', 'type_id': '36'},
        {'type_name': 'AI换脸', 'type_id': '23'},
        {'type_name': '群P换妻', 'type_id': '73'},
        {'type_name': '网黄博主', 'type_id': '57'},
        {'type_name': '黑人媚黑', 'type_id': '56'},
        {'type_name': '无码素人', 'type_id': '26'},
        {'type_name': '日本无码', 'type_id': '84'},
        {'type_name': '无码破解', 'type_id': '22'},
        {'type_name': '日韩中字', 'type_id': '25'},
        {'type_name': '欧美劲爆', 'type_id': '19'},
        {'type_name': '经典三级', 'type_id': '28'},
        {'type_name': '3D动漫', 'type_id': '20'},
        {'type_name': '全部视频', 'type_id': '0'},
    ]

    def getName(self):
        return '55eejj影视'

    def init(self, extend):
        self._vod_cache = {}
        self._cfg = None
        # 预拉站点配置 (刷新图床域名)
        try:
            self._load_cfg()
        except Exception:
            pass

    def isVideoFormat(self, url):
        return any(x in url for x in ['.m3u8', '.mp4', '.flv', '.avi', '.mkv'])

    def manualVideoCheck(self):
        return False

    def destroy(self):
        pass

    # ============================================================
    # ENC2 解密 (FNV-1a + xorshift32 XOR 流密码)
    # ============================================================

    @staticmethod
    def _b64url_decode(s):
        t = s.replace('-', '+').replace('_', '/')
        t += '=' * (4 - len(t) % 4) if len(t) % 4 else ''
        return base64.b64decode(t)

    @staticmethod
    def _fnv1a(s):
        h = 2166136261
        for b in s.encode('utf-8'):
            h ^= b
            h = (h * 16777619) & 0xFFFFFFFF
        return h

    @staticmethod
    def _xorshift32(e):
        e &= 0xFFFFFFFF
        e ^= (e << 13) & 0xFFFFFFFF
        e ^= (e >> 17) & 0xFFFFFFFF
        e ^= (e << 5) & 0xFFFFFFFF
        return e & 0xFFFFFFFF

    def _decrypt_il(self, data, iv, pwd=None):
        pwd = pwd or self.enc_key
        s = self._fnv1a('%s|%s' % (pwd, iv)) or 2166136261
        n = bytearray(len(data))
        r = 0
        for a in range(len(data)):
            if (a & 3) == 0:
                s = self._xorshift32(s)
                r = s
            n[a] = data[a] ^ ((r >> (8 * (a & 3))) & 0xFF)
        return bytes(n)

    def _dec2(self, v, pwd=None):
        """解密 ENC2.iv.cipher 格式的字符串, 返回原文 (尝试 JSON 解析)"""
        if not isinstance(v, str) or not v.startswith('ENC2.'):
            return v
        t = v.split('.')
        if len(t) != 3:
            return v
        pwd = pwd or self.enc_key
        try:
            data = self._b64url_decode(t[2])
            text = self._decrypt_il(data, t[1], pwd).decode('utf-8', errors='ignore')
        except Exception:
            return v
        try:
            return json.loads(text)
        except Exception:
            return text

    def _dobj(self, o):
        """递归解密响应里所有 ENC2 字段"""
        if isinstance(o, str):
            return self._dec2(o) if o.startswith('ENC2.') else o
        if isinstance(o, dict):
            return {k: self._dobj(v) for k, v in o.items()}
        if isinstance(o, list):
            return [self._dobj(i) for i in o]
        return o

    # ============================================================
    # API 请求 (自动加 project=xs, 自动 ENC2 解密, 返回 data 字段)
    # ============================================================

    def _api(self, path, **params):
        """请求 API, 返回解密后的 data 字段 (list 或 dict)
        当默认 api_base 不可用时, 自动从主域名 www.55eejj.com 拉 runtime-config.js
        解密新的 apiBase 并刷新 project, 然后再重试一次。
        """
        params.setdefault('project', self.project)
        url = self.api_base + path
        raw = None
        try:
            r = self.fetch(url, headers=self.header, timeout=15, params=params)
            text = r.text if hasattr(r, 'text') else r.content.decode('utf-8', errors='ignore')
            if getattr(r, 'status_code', 200) >= 400:
                raise Exception('api status %s' % r.status_code)
            raw = json.loads(text)
        except Exception:
            # 默认 api 失败, 尝试通过主域名刷新 api_base / project 后重试一次
            self._resolve_api_base()
            url = self.api_base + path
            try:
                r = self.fetch(url, headers=self.header, timeout=15, params=params)
                text = r.text if hasattr(r, 'text') else r.content.decode('utf-8', errors='ignore')
                if getattr(r, 'status_code', 200) >= 400:
                    raise Exception('api status %s' % r.status_code)
                raw = json.loads(text)
            except Exception:
                return {}

        if not isinstance(raw, dict):
            return {}
        # 先整体解密 (code/msg/data 都是 ENC2 加密的)
        raw = self._dobj(raw)
        # 解密后检查 code !== 0 视为失败
        code = raw.get('code')
        if code not in (0, None, '0'):
            return {}
        data = raw.get('data')
        # data 可能是 None(无数据)、list、dict —— 直接返回 (已解密)
        return data if data is not None else raw

    def _resolve_api_base(self):
        """从主域名 www.55eejj.com 拉取运行时配置, 刷新 api_base / project / 图床
        这是防止 7maohd.xffll.com 域名被封/更换后源失效的兜底机制。
        """
        try:
            # 1. 先尝试 /runtime-config.js (最干净)
            cfg_url = self.site_url.rstrip('/') + '/runtime-config.js'
            r = self.fetch(cfg_url, headers={'User-Agent': self.header['User-Agent']}, timeout=10)
            text = r.text if hasattr(r, 'text') else r.content.decode('utf-8', errors='ignore')
            if getattr(r, 'status_code', 200) < 400 and text:
                # 提取加密的 apiBase
                m = re.search(r'apiBase:\s*[\'\"](ENC2\.[A-Za-z0-9_\-]+\.[A-Za-z0-9_\-]+)[\'\"]', text)
                if m:
                    api_base = self._dec2(m.group(1))
                    if isinstance(api_base, str):
                        api_base = api_base.strip('\'\"')
                        if api_base.startswith('http'):
                            self.api_base = api_base.rstrip('/')
                # 提取 siteProject
                pm = re.search(r'siteProject:\s*[\'\"]([^\'\"]+)[\'\"]', text)
                if pm:
                    self.project = pm.group(1)
        except Exception:
            pass

        # 2. runtime-config.js 拿不到, 尝试从首页 HTML 的 index-*.js 里找
        if not self.api_base or not self.api_base.startswith('http'):
            try:
                r = self.fetch(self.site_url, headers={'User-Agent': self.header['User-Agent']}, timeout=10)
                html = r.text if hasattr(r, 'text') else r.content.decode('utf-8', errors='ignore')
                if getattr(r, 'status_code', 200) < 400 and html:
                    js_paths = re.findall(r'<script[^>]*src="(/assets/index-[A-Za-z0-9]+\.js)"', html)
                    for js_path in js_paths:
                        try:
                            js_url = self.site_url.rstrip('/') + js_path
                            r2 = self.fetch(js_url, headers={'User-Agent': self.header['User-Agent']}, timeout=10)
                            js_text = r2.text if hasattr(r2, 'text') else r2.content.decode('utf-8', errors='ignore')
                            if getattr(r2, 'status_code', 200) >= 400:
                                continue
                            m = re.search(r'apiBase:\s*[\'\"](ENC2\.[A-Za-z0-9_\-]+\.[A-Za-z0-9_\-]+)[\'\"]', js_text)
                            if m:
                                api_base = self._dec2(m.group(1))
                                if isinstance(api_base, str):
                                    api_base = api_base.strip('\'\"')
                                    if api_base.startswith('http'):
                                        self.api_base = api_base.rstrip('/')
                                        break
                        except Exception:
                            continue
            except Exception:
                pass

        # 3. 兜底: 保证 api_base 有效
        if not self.api_base or not self.api_base.startswith('http'):
            self.api_base = 'https://7maohd.xffll.com/api'

    # ============================================================
    # 图片 (直链优先, 不硬编码代理端口)
    # ============================================================

    def _wrap_pic(self, pic_url):
        """封面 URL 处理: 优先返回直链 (新图床不防盗链)"""
        if not pic_url:
            return ''
        if pic_url.startswith('http://') or pic_url.startswith('https://'):
            return pic_url
        if pic_url.startswith('//'):
            return 'https:' + pic_url
        if pic_url.startswith('/'):
            return self.pic_host.rstrip('/') + pic_url
        return self.pic_host.rstrip('/') + '/' + pic_url

    # ============================================================
    # 首页
    # ============================================================

    def homeContent(self, filter):
        """返回分类列表: 从 /movie/tags 拉真分类, 拉不到用硬编码兜底"""
        cats = []
        try:
            tags = self._api('/movie/tags')
            # 真实结构: [{category, categoryShow, tags:[{id, name}]}, ...]
            if isinstance(tags, list):
                for c in tags:
                    if not isinstance(c, dict):
                        continue
                    # 嵌套结构: category -> tags[]
                    sub_tags = c.get('tags') or c.get('tag') or []
                    if isinstance(sub_tags, list):
                        for t in sub_tags:
                            if not isinstance(t, dict):
                                continue
                            tid = str(t.get('id') or t.get('tagid') or '')
                            tname = t.get('name') or t.get('tagname') or ''
                            if tid and tname:
                                cats.append({'type_id': tid, 'type_name': tname})
                    else:
                        # 扁平结构兜底
                        tid = str(c.get('categoryid') or c.get('id') or '')
                        tname = c.get('categoryname') or c.get('name') or ''
                        if tid and tname:
                            cats.append({'type_id': tid, 'type_name': tname})
        except Exception:
            pass
        if not cats:
            cats = list(self.classes)
        # 末尾加"全部视频"
        if not any(c['type_id'] == '0' for c in cats):
            cats.append({'type_id': '0', 'type_name': '全部视频'})
        return {'class': cats, 'filters': {}}

    def homeVideoContent(self):
        """首页推荐: 拉 /movie/home_sections 拼成扁平列表"""
        try:
            r = self._api('/movie/home_sections', pageSize=20)
            # r 是 [{tagid, tagids, tagname, movies:[...]}, ...]
            sections = r if isinstance(r, list) else []
            items = []
            all_movies = []
            seen = set()
            for sec in sections:
                if not isinstance(sec, dict):
                    continue
                movies = sec.get('movies') or sec.get('list') or []
                for m in movies:
                    if not isinstance(m, dict):
                        continue
                    vid = str(m.get('movieid') or '')
                    if not vid or vid in seen:
                        continue
                    seen.add(vid)
                    all_movies.append(m)
                    items.append({
                        'vod_id': vid,
                        'vod_name': (m.get('Topic') or '')[:100] or '未知',
                        'vod_pic': self._wrap_pic(m.get('smallpic') or ''),
                        'vod_remarks': m.get('formatted_timesize') or '',
                    })
                    if len(items) >= 60:
                        break
                if len(items) >= 60:
                    break
            # 缓存原始数据 (含 h264mp4url 直链), 详情/播放直接命中
            self._cache_items(all_movies)
            return {'list': items}
        except Exception:
            return {'list': []}

    # ============================================================
    # 分类 / 列表
    # ============================================================

    def categoryContent(self, tid, pg, filter, extend):
        try:
            pg = int(pg or 1)
        except Exception:
            pg = 1
        try:
            params = {'page': pg, 'pageSize': 30}
            if tid and str(tid) != '0':
                params['tagid'] = tid
            r = self._api('/movie/list', **params)
            # _api 已返回 data 字段 (list)
            data = r if isinstance(r, list) else []
            self._cache_items(data)
            vod_list = self._parse_list(data)
            pagecount = 999
            if len(vod_list) < 30:
                pagecount = pg
            return {
                'page': pg,
                'pagecount': pagecount,
                'limit': len(vod_list),
                'total': pagecount * 30 if pagecount < 999 else 99999,
                'list': vod_list,
            }
        except Exception:
            return {'page': pg, 'pagecount': 1, 'limit': 0, 'total': 0, 'list': []}

    # ============================================================
    # 详情
    # ============================================================

    def detailContent(self, ids):
        try:
            vod_id = str(ids[0]) if isinstance(ids, list) else str(ids)

            # 优先调详情接口 /movie/{id} 拿完整字段 (含可用 h264mp4url / smallpic)
            item = None
            d = self._api('/movie/' + vod_id)
            if isinstance(d, dict):
                # /movie/{id} 的 data 直接就是视频对象
                if d.get('movieid') or d.get('h264mp4url') or d.get('Topic'):
                    item = d
                else:
                    # 兼容 data.movie 嵌套
                    item = d.get('movie') or None
            if isinstance(item, list):
                item = item[0] if item else None

            # 兜底: 用 cache 里的简表
            if not item or not isinstance(item, dict):
                item = self._vod_cache.get(vod_id)

            if not item or not isinstance(item, dict):
                item = {'movieid': vod_id, 'Topic': '视频 ' + vod_id}

            # 写回 cache, 播放可以直接命中
            if item.get('movieid'):
                self._vod_cache[vod_id] = item

            title = item.get('Topic') or item.get('title') or '未知视频'
            pic = self._wrap_pic(item.get('smallpic') or '')
            duration = item.get('formatted_timesize') or item.get('timesize') or ''
            # 播放直链 (优先 mp4, 其次 m3u8)
            play_url = (item.get('h264mp4url') or item.get('h264mp4url2')
                        or item.get('h265mp4url') or item.get('h264m3u8url')
                        or item.get('h264m3u8url2') or '')

            vod = {
                'vod_id': vod_id,
                'vod_name': title.strip() if isinstance(title, str) else str(title),
                'vod_pic': pic,
                'type_name': item.get('tagname') or '视频',
                'vod_year': str(item.get('release_date') or '')[:4] if item.get('release_date') else '',
                'vod_content': '时长: %s' % duration if duration else '',
                'vod_remarks': duration,
                'vod_play_from': '55eejj',
                'vod_play_url': ('正片$' + play_url) if play_url else ('正片$' + vod_id),
            }
            return {'list': [vod]}
        except Exception:
            return {'list': []}

    # ============================================================
    # 搜索 (走 /movie/list?keyword=)
    # ============================================================

    def searchContent(self, key, quick=False, pg=1):
        try:
            pg = int(pg or 1)
            r = self._api('/movie/list', keyword=str(key), page=pg, pageSize=30)
            data = r if isinstance(r, list) else []
            self._cache_items(data)
            return {'list': self._parse_list(data)[:30], 'page': pg}
        except Exception:
            return {'list': [], 'page': 1}

    def searchContentPage(self, key, quick=False, pg=1):
        return self.searchContent(key, quick, pg)

    # ============================================================
    # 播放 (带 Referer/Origin, CDN 放行)
    # ============================================================

    def playerContent(self, flag, id, vipFlags=None):
        try:
            vod_id = str(id) if id else ''
            # 已经是 http(s) 直链
            if vod_id.startswith('http'):
                return {
                    'parse': 0,
                    'url': vod_id,
                    'header': self._player_header(),
                }

            # 从 cache 找直链
            play_url = ''
            item = self._vod_cache.get(vod_id)
            if item and isinstance(item, dict):
                for k in ('h264mp4url', 'h264mp4url2', 'h265mp4url',
                          'h264m3u8url', 'h264m3u8url2'):
                    v = item.get(k, '')
                    if v:
                        play_url = v
                        break

            # cache 没有, 主动查详情
            if not play_url:
                d = self._api('/movie/' + vod_id)
                if isinstance(d, dict) and (d.get('movieid') or d.get('h264mp4url')):
                    self._vod_cache[vod_id] = d
                    for k in ('h264mp4url', 'h264mp4url2', 'h265mp4url',
                              'h264m3u8url', 'h264m3u8url2'):
                        v = d.get(k, '')
                        if v:
                            play_url = v
                            break

            if play_url:
                return {
                    'parse': 0,
                    'url': play_url,
                    'header': self._player_header(),
                }
            # 完全拿不到直链 — 让壳子去拉播放页自己解析
            return {
                'parse': 1,
                'url': self.host + '/movie/' + vod_id,
                'header': self._player_header(),
            }
        except Exception:
            return {}

    def _player_header(self):
        """播放请求统一 header, 关键: 带 Referer/Origin, 否则 CDN 经常 403"""
        return {
            'User-Agent': self.header['User-Agent'],
            'Referer': self.host + '/',
            'Origin': self.host,
        }

    # ============================================================
    # 本地代理 (图床防盗链兜底, 用相对路径不硬编码端口)
    # ============================================================

    def localProxy(self, param):
        try:
            if isinstance(param, str):
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
                        url = base64.urlsafe_b64decode(url).decode('utf-8')
                    except Exception:
                        pass
                if url:
                    headers = {
                        'User-Agent': self.header['User-Agent'],
                        'Referer': self.host + '/',
                        'Accept': 'image/webp,image/apng,image/*,*/*;q=0.8',
                    }
                    try:
                        r = self.fetch(url, headers=headers, timeout=15)
                    except Exception:
                        r = None
                    if r is not None and getattr(r, 'status_code', 0) == 200:
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
                            elif '.gif' in url:
                                content_type = 'image/gif'
                            else:
                                content_type = 'image/jpeg'
                        content = r.content if hasattr(r, 'content') else r.text.encode('utf-8')
                        return [200, content_type, content, {}]
        except Exception:
            pass
        return [404, 'text/plain', '', {}]

    # ============================================================
    # 列表解析 / 缓存
    # ============================================================

    def _parse_list(self, data):
        vod_list = []
        if not isinstance(data, list):
            return vod_list
        for item in data:
            if not isinstance(item, dict):
                continue
            vid = str(item.get('movieid') or '')
            if not vid:
                continue
            name = item.get('Topic') or item.get('title') or '未知'
            pic = self._wrap_pic(item.get('smallpic') or '')
            duration = item.get('formatted_timesize') or ''
            vod_list.append({
                'vod_id': vid,
                'vod_name': name.strip() if isinstance(name, str) else str(name),
                'vod_pic': pic,
                'vod_remarks': duration,
            })
        return vod_list

    def _cache_items(self, data):
        """把 API 返回的原始 video item 存入缓存, 供 detailContent/playerContent 使用"""
        if not isinstance(data, list):
            return
        for item in data:
            if isinstance(item, dict):
                vid = str(item.get('movieid') or '')
                if vid:
                    self._vod_cache[vid] = item
