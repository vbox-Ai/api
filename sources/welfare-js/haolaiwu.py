#!/usr/bin/python
# -*- coding: utf-8 -*-
"""
好莱污影院 - boutiquefire.xyz
MacCMS站点 | DNS劫持绕过 | HTML解析

vbox 适配：
1. 基类导入加 try/except + as _B
2. socket.getaddrinfo patch 加防重复保护
3. 添加 getDependence + warnings 抑制
4. homeVideoContent 精简返回 {"list": [...]}
5. localProxy 返回 pass
"""
import re
import json
import socket
import warnings
from urllib.parse import quote, unquote

warnings.filterwarnings("ignore")

try:
    import urllib3
    urllib3.disable_warnings()
except ImportError:
    pass

import sys
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

# ═══════ DNS劫持绕过: 域名被劫持到反诈站(198.18.x.x), 需解析真实Cloudflare IP ═══════
_DOMAIN = 'boutiquefire.xyz'
_REAL_IP = '172.67.172.213'  # Cloudflare真实IP
_orig_getaddrinfo = socket.getaddrinfo

def _patched_getaddrinfo(host, port, *args, **kwargs):
    if host == _DOMAIN or host == 'www.' + _DOMAIN:
        return _orig_getaddrinfo(_REAL_IP, port, *args, **kwargs)
    return _orig_getaddrinfo(host, port, *args, **kwargs)

# 防重复 patch
if not getattr(socket.getaddrinfo, '_vbox_patched', False):
    _patched_getaddrinfo._vbox_patched = True
    socket.getaddrinfo = _patched_getaddrinfo


class Spider(_B):
    HOST = 'https://' + _DOMAIN
    UA = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/120 Safari/537.36'

    CATS = [
        {'type_id': '20', 'type_name': '国产视频'},
        {'type_id': '21', 'type_name': '中文字幕'},
    ]

    def getDependence(self):
        return ['requests']

    def getName(self):
        return "好莱污影院"

    def init(self, extend=""):
        self.extend = extend or ""
        self.host = self.HOST
        if self.extend:
            if re.match(r'^\d+\.\d+\.\d+\.\d+$', self.extend):
                self._set_ip(self.extend)
            elif self.extend.startswith('http'):
                m = re.match(r'https?://([^/:]+)', self.extend)
                if m:
                    self._set_ip(m.group(1))
        self.headers = {'User-Agent': self.UA, 'Referer': self.host + '/', 'Accept': 'text/html,application/xhtml+xml,*/*'}
        self.session = requests.Session()
        self.session.verify = False
        self.session.headers.update(self.headers)
        self._resolve_ip()

    def _set_ip(self, ip):
        global _REAL_IP
        _REAL_IP = ip

        def _patched(host, port, *args, **kwargs):
            if host == _DOMAIN or host == 'www.' + _DOMAIN:
                return _orig_getaddrinfo(ip, port, *args, **kwargs)
            return _orig_getaddrinfo(host, port, *args, **kwargs)
        _patched._vbox_patched = True
        socket.getaddrinfo = _patched

    def _resolve_ip(self):
        global _REAL_IP
        for doh in ['https://1.1.1.1/dns-query?name=%s&type=A' % _DOMAIN,
                     'https://dns.google/resolve?name=%s&type=A' % _DOMAIN]:
            try:
                r = self.session.get(doh, headers={'Accept': 'application/dns-json'}, timeout=8)
                if r.status_code == 200:
                    data = r.json()
                    for ans in data.get('Answer', []):
                        if ans.get('type') == 1:
                            ip = ans['data']
                            if ip and not ip.startswith('198.18.'):
                                self._set_ip(ip)
                                return
            except:
                pass

    def isVideoFormat(self, url):
        return bool(re.search(r'\.(?:m3u8|mp4|flv)', url, re.I))

    def manualVideoCheck(self):
        return False

    def destroy(self):
        try:
            self.session.close()
        except Exception:
            pass

    def _fetch(self, url, retries=2):
        for i in range(retries + 1):
            try:
                r = self.session.get(url, timeout=15, allow_redirects=True)
                r.encoding = 'utf-8'
                if r.status_code == 200 and len(r.text) > 100:
                    if 'js96110' in r.url or '反诈' in r.text:
                        alt = '104.21.39.253' if _REAL_IP == '172.67.172.213' else '172.67.172.213'
                        self._set_ip(alt)
                        continue
                    return r.text
            except:
                pass
        return ''

    def _fix_pic(self, u):
        if not u:
            return ''
        if u.startswith('//'):
            return 'https:' + u
        if u.startswith('/'):
            return self.host + u
        return u

    def _parse_cards(self, html):
        if not html:
            return []
        vods, seen = [], set()
        title_map = {}
        for vid, text in re.findall(r'<a[^>]*class="[^"]*title[^"]*"[^>]*href="/index\.php/vod/play/id/(\d+)[^"]*"[^>]*>(.*?)</a>', html, re.S):
            clean = re.sub(r'<[^>]+>', '', text).strip()
            if clean and clean != '00:00' and vid not in title_map:
                title_map[vid] = clean
        for vid, content in re.findall(r'<a[^>]*class="[^"]*display[^"]*"[^>]*href="/index\.php/vod/play/id/(\d+)[^"]*"[^>]*>(.*?)</a>', html, re.S):
            if vid in seen:
                continue
            seen.add(vid)
            title = title_map.get(vid, '')
            if not title:
                continue
            pic = ''
            bg = re.search(r"background-image:\s*url\(['\"]?([^'\")]+)['\"]?\)", content)
            if bg:
                pic = self._fix_pic(bg.group(1))
            remarks = ''
            tm = re.search(r'<small[^>]*>(.*?)</small>', content, re.S)
            if tm:
                remarks = re.sub(r'<[^>]+>', '', tm.group(1)).strip()
                if remarks in ('00:00', ''):
                    remarks = ''
            vods.append({'vod_id': vid, 'vod_name': title, 'vod_pic': pic, 'vod_remarks': remarks})
        return vods

    # ============================================================
    # 首页
    # ============================================================
    def homeContent(self, filter):
        return {'class': self.CATS, 'list': [], 'filters': {}}

    def homeVideoContent(self):
        html = self._fetch(self.host + '/')
        vods = self._parse_cards(html)
        return {"list": vods}

    # ============================================================
    # 分类列表
    # ============================================================
    def categoryContent(self, tid, pg, filter, extend):
        page = int(pg) if pg else 1
        if page <= 1:
            url = f'{self.host}/index.php/vod/type/id/{tid}.html'
        else:
            url = f'{self.host}/index.php/vod/type/id/{tid}/page/{page}.html'
        html = self._fetch(url)
        vods = self._parse_cards(html)
        pagecount = 1
        if html:
            pages = re.findall(r'href="/index\.php/vod/type/id/\d+/page/(\d+)\.html"', html)
            if pages:
                pagecount = max(int(p) for p in pages)
        return {'list': vods, 'page': page, 'pagecount': pagecount, 'limit': len(vods), 'total': pagecount * 48 if vods else 0}

    # ============================================================
    # 详情
    # ============================================================
    def detailContent(self, ids):
        vid = str(ids[0] if isinstance(ids, list) else ids)
        html = self._fetch(f'{self.host}/index.php/vod/detail/id/{vid}.html')
        title, pic, year, vod_class, content = '', '', '', '', ''
        if html:
            tm = re.search(r'<title>(.*?)</title>', html, re.S)
            if tm:
                title = tm.group(1).split('详情介绍')[0].split(' - ')[0].strip()
            img_m = re.search(r'<img[^>]*src="(/upload/vod/[^"]+)"[^>]*alt="([^"]*)"', html)
            if img_m:
                pic = self._fix_pic(img_m.group(1))
                if not title:
                    title = img_m.group(2)
            info_divs = re.findall(r'<div[^>]*class="[^"]*info[^"]*"[^>]*>(.*?)</div>', html, re.S)
            for div in info_divs:
                if '主演' in div or '状态' in div:
                    import html as _html
                    info = re.sub(r'\s+', ' ', _html.unescape(re.sub(r'<[^>]+>', ' ', div))).strip()
                    m = re.search(r'类型[：:]\s*(\S+)', info)
                    if m and m.group(1) != '未知':
                        vod_class = m.group(1)
                    m = re.search(r'时间[：:]\s*(\d{4})', info)
                    if m:
                        year = m.group(1)
                    m = re.search(r'年份[：:]\s*(\S+)', info)
                    if m and m.group(1) != '未知':
                        year = m.group(1)
                    m = re.search(r'剧情[：:]\s*(.*?)(?:分享|收藏|访问|$)', info)
                    if m:
                        content = m.group(1).strip()
                    break
        play_url = self._get_play_url(vid)
        vod = {
            'vod_id': vid,
            'vod_name': title or f'视频{vid}',
            'vod_pic': pic,
            'vod_play_from': '好莱污影院',
            'vod_play_url': f'在线播放${play_url}' if play_url else '',
        }
        if year:
            vod['vod_year'] = year
        if vod_class:
            vod['vod_class'] = vod_class
        if content:
            vod['vod_content'] = content
        return {'list': [vod]}

    def _get_play_url(self, vid):
        html = self._fetch(f'{self.host}/index.php/vod/play/id/{vid}/sid/1/nid/1.html')
        if not html:
            return ''
        m = re.search(r'player_aaaa\s*=\s*(\{.*?\})', html, re.S)
        if m:
            try:
                pa = json.loads(m.group(1))
                url = pa.get('url', '')
                if url:
                    return unquote(url)
            except:
                pass
        m = re.search(r'(https?://[^\s"\'<>]+\.m3u8[^\s"\'<>]*)', html)
        return m.group(1) if m else ''

    # ============================================================
    # 搜索（已关闭）
    # ============================================================
    def searchContent(self, key, quick, pg="1"):
        return {'list': [], 'page': 1, 'pagecount': 1, 'limit': 0, 'total': 0}

    # ============================================================
    # 播放
    # ============================================================
    def playerContent(self, flag, id, vipFlags):
        url = unquote(str(id))
        hdr = {'Referer': self.host + '/', 'User-Agent': self.UA}
        return {'parse': 0, 'url': url, 'header': hdr}

    def localProxy(self, param):
        pass
