# -*- coding: utf-8 -*-
"""
《色播聚合》- vbox 福利专区 Python Spider (继承 base.spider.Spider)

适配 vbox 福利专区（直播栏目），自动享用：
- 自定义域名（_vbox_effective_hosts 注入 → self.host）
- 代理设置（_vbox_proxy_enabled / _vbox_proxy_url 注入 → fetch 自动走代理）
- 封面图代理（localProxy → /proxy?do=py 路由 → DoubanImageProxyServer）

站点: http://api.hclyz.com:81/mf
类型: 直播聚合（平台 → 频道）
播放: 频道地址是 m3u8 直播流，iOS AVPlayer 原生支持

【D2 方案】
- homeContent 返回 1 个分类"全部平台"
- homeVideoContent / categoryContent 返回所有直播平台卡片
- detailContent 把指定平台的所有频道用 # 串成 1 条线路
- playerContent 直接返 m3u8 地址，parse=0
"""

import sys
import re
import json
import gzip
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


# ── 常量 ──
NAME = '色播聚合'
HOST = 'http://api.hclyz.com:81/mf'

# GitHub 图床（参考原脚本约定）
_GH_IMG_BASE = 'https://slink.ltd/https://raw.githubusercontent.com/fish2018/lib/refs/heads/main/imgs/'
# 原 CDN（GitHub 失败时 fallback）
_ORIG_CDN_BASE = 'http://cdn.gcufbd.top/img/'

# 频道列表截断（避免 vod_play_url 过长）
_MAX_EPISODES = 200

_UA = ('Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 '
       '(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36')


def _clean(s):
    if s is None:
        return ''
    return re.sub(r'\s+', ' ', ihtml.unescape(re.sub(r'<[^>]+>', '', str(s)))).strip()


def _fix_cover(raw):
    """把源站封面图做双 CDN 兜底：原 CDN → GitHub 图床。
    客户端 localProxy 会自动加 Referer，这里只给绝对 URL。"""
    if not raw:
        return ''
    raw = str(raw).strip()
    if raw.startswith('//'):
        raw = 'http:' + raw
    if raw.startswith(_ORIG_CDN_BASE):
        # 用 GitHub 图床替代（参考原脚本策略）
        return raw.replace(_ORIG_CDN_BASE, _GH_IMG_BASE)
    return raw


class Spider(BaseSpider):
    """vbox 福利专区 Spider，继承 base.spider.Spider 自动获取域名注入和代理"""

    def __init__(self):
        try:
            super().__init__()
        except Exception:
            pass
        self.name = NAME
        self.host = HOST
        self.timeout = 15
        self.headers = {
            'User-Agent': _UA,
            'Accept': 'application/json, text/plain, */*',
            'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
        }

    # ── 生命周期 ──

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
        return any(x in v for x in ('.m3u8', '.mp4', '.m4v', '.flv', '.webm', '.ts'))

    def init(self, extend=''):
        try:
            super().init(extend)
        except Exception:
            pass
        config = extend if isinstance(extend, dict) else {}
        if not config and extend and isinstance(extend, str):
            try:
                config = json.loads(extend)
            except Exception:
                config = {}
        host = str(config.get('host') or config.get('HOST') or '').strip().rstrip('/')
        if host.startswith(('http://', 'https://')):
            self.host = host
        return None

    # ── 统一请求（带 gzip 解压 + 日志） ──

    def _fetch_page(self, url, params=None, referer=None, post=False, data=None, retry=2):
        headers = dict(self.headers)
        if referer:
            headers['Referer'] = referer
        last_err = None
        for att in range(max(1, retry)):
            try:
                if post:
                    r = self.post(url, headers=headers, data=data,
                                  timeout=self.timeout, verify=False)
                else:
                    r = self.fetch(url, headers=headers,
                                   timeout=self.timeout, verify=False)
                if r is None:
                    continue
                if hasattr(r, 'status_code') and r.status_code in (403, 503, 429):
                    last_err = 'http %s' % r.status_code
                    continue
                # gzip 解压（源站是 HTTP JSON 不会 gzip，但保持一致性）
                content = r.content if hasattr(r, 'content') else b''
                if content and len(content) >= 2 and content[0:2] == b'\x1f\x8b':
                    try:
                        decompressed = gzip.decompress(content)
                        r.content = decompressed
                        r.text = decompressed.decode(r.encoding or 'utf-8', errors='replace')
                    except Exception:
                        pass
                self._log('fetch %s → status=%s, %d bytes' % (
                    url.split('/')[-1] or url, getattr(r, 'status_code', '?'),
                    len(r.text or '')))
                return r
            except Exception as e:
                last_err = str(e)
                self._log('request fail %s: %s' % (url, last_err))
        return None

    def _fetch_json(self, url):
        r = self._fetch_page(url)
        if r is None:
            return {}
        try:
            if hasattr(r, 'json'):
                return r.json() or {}
        except Exception:
            pass
        try:
            return json.loads(r.text or '{}')
        except Exception:
            return {}

    def _log(self, msg):
        try:
            self.log('[%s] %s' % (self.name, msg))
        except Exception:
            print('[%s] %s' % (self.name, msg))

    # ── 数据加载 ──

    def _load_platforms(self):
        """拉根 json.txt，返回平台列表（已 skip 第一个）"""
        data = self._fetch_json(self.host + '/json.txt')
        items = data.get('pingtai') or []
        if not items:
            self._log('平台列表为空: json.txt 返回无 pingtai 字段')
            return []
        return items[1:]  # 原脚本约定：跳过第 1 个

    def _load_channels(self, platform_file):
        """拉指定平台的 json 文件，返回频道列表。
        接口 404（平台挂了）时返空列表，由 detailContent 容错提示。"""
        url = '%s/%s' % (self.host, platform_file)
        r = self._fetch_page(url)
        if r is None:
            self._log('频道接口无响应: %s' % platform_file)
            return []
        sc = getattr(r, 'status_code', 200)
        if sc in (404, 410):
            self._log('频道接口已失效(平台挂了): %s → HTTP %s' % (platform_file, sc))
            return []
        try:
            data = r.json() if hasattr(r, 'json') else json.loads(r.text or '{}')
        except Exception:
            data = {}
        items = (data or {}).get('zhubo') or []
        if not items:
            self._log('频道列表为空: %s' % platform_file)
        return items

    # ── TVBox 接口 ──

    def homeContent(self, filter=False):
        """D2 方案：只 1 个分类 '全部平台'，平台卡片通过 homeVideoContent 提供"""
        return {
            'class': [
                {'type_id': 'all', 'type_name': '全部平台'},
            ],
            'filters': {},
        }

    def homeVideoContent(self):
        """首页视频 = 全部直播平台（每张卡当一个视频，点进去是该平台所有频道）"""
        return {'list': self._platforms_as_videos()}

    def categoryContent(self, tid, pg, filter=False, extend=None):
        """分类页：tid='all' 时和首页一致"""
        try:
            page = int(pg)
        except (ValueError, TypeError):
            page = 1
        if page > 1:
            # D2 方案：平台列表是单页，>1 给空
            return {'list': [], 'page': page, 'pagecount': 1, 'limit': 99, 'total': 0}
        return {
            'list': self._platforms_as_videos(),
            'page': 1,
            'pagecount': 1,
            'limit': 99,
            'total': 0,
        }

    def _platforms_as_videos(self):
        items = self._load_platforms()
        vods = []
        for item in items:
            title = _clean(item.get('title') or '')
            address = str(item.get('address') or '').strip()
            if not title or not address:
                continue
            # address 形如 "jsonweishizhibo.txt" 或 "/jsonweishizhibo.txt"
            platform_file = address.split('/')[-1]
            if not platform_file:
                continue
            num = str(item.get('Number') or '0')
            vods.append({
                'vod_id': platform_file,
                'vod_name': title,
                'vod_pic': _fix_cover(item.get('xinimg') or ''),
                'vod_remarks': '含 %s 频道' % num if num != '0' else '',
                'style': {'type': 'rect', 'ratio': 1.33},
            })
        self._log('首页/分类: 共 %d 个平台' % len(vods))
        return vods

    def detailContent(self, array):
        """点平台卡片 → 拉该平台所有频道，串成 1 条线路"""
        if not array:
            return {'list': []}
        platform_file = str(array[0]).split('/')[-1]
        if not platform_file:
            return {'list': []}

        # 用平台名作为详情标题（从根列表里取，或从接口 title 取）
        plat_title = platform_file
        for p in self._load_platforms():
            if str(p.get('address') or '').endswith(platform_file):
                plat_title = _clean(p.get('title') or platform_file)
                break

        channels = self._load_channels(platform_file)
        if not channels:
            return {
                'list': [{
                    'vod_id': platform_file,
                    'vod_name': plat_title,
                    'vod_pic': '',
                    'vod_play_from': '',
                    'vod_play_url': '',
                    'vod_content': '未获取到频道列表',
                }]
            }

        # 截断防超长
        if len(channels) > _MAX_EPISODES:
            self._log('频道数 %d 超过 %d，截断' % (len(channels), _MAX_EPISODES))
            channels = channels[:_MAX_EPISODES]

        parts = []
        for ch in channels:
            t = _clean(ch.get('title') or '')
            a = str(ch.get('address') or '').strip()
            if not a:
                continue
            if not t:
                t = '频道'
            parts.append('%s$%s' % (t, a))
        play_url = '#'.join(parts)

        return {
            'list': [{
                'vod_id': platform_file,
                'vod_name': plat_title,
                'vod_pic': '',
                'vod_play_from': '全部频道',
                'vod_play_url': play_url,
                'vod_content': '色播聚合 · 共 %d 个频道' % len(parts),
            }]
        }

    def searchContent(self, key, quick, pg='1'):
        """D2 方案不支持搜索，返回空"""
        return {'list': [], 'page': 1, 'pagecount': 1, 'limit': 99, 'total': 0}

    def playerContent(self, flag, id, vipFlags=None):
        """直接返 m3u8 直播流，parse=0 由 AVPlayer 播放"""
        url = str(id or '').strip()
        if not url:
            return {'parse': 0, 'url': '', 'header': {}}
        headers = {
            'User-Agent': _UA,
            'Referer': 'http://api.hclyz.com/',
        }
        return {'parse': 0, 'url': url, 'header': headers}

    # ── 封面图代理（供 vbox DoubanImageProxyServer 回调） ──

    def localProxy(self, param):
        _p = param if isinstance(param, dict) else {}
        url = unquote(_p.get('url', '') or '')
        if not url:
            return None
        try:
            resp = self.fetch(url, headers={
                'User-Agent': _UA,
                'Referer': _p.get('referer', 'http://api.hclyz.com/'),
            }, timeout=self.timeout, verify=False)
            if resp is None:
                return None
            ct = 'image/jpeg'
            if hasattr(resp, 'headers') and resp.headers is not None:
                ct = resp.headers.get('Content-Type', 'image/jpeg')
            content = resp.content if hasattr(resp, 'content') else b''
            return [200, ct, content]
        except Exception:
            return None
