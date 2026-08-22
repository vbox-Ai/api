# -*- coding: utf-8 -*-
"""
平台名称：51木瓜
平台标识：wugua_py
作者：原始 tvshare23 · 适配：vbox Python Spider 框架
适配日期：2026-08-23
说明：
  - 继承 base.spider.Spider，super().init() 兜底
  - 域名注入：从 _vbox_effective_hosts 取候选域名
  - 并发域名探测：CDN + Supabase 同时探测，先到先用
  - 10 分钟冷静期：成功域名缓存 600s，过期重新探测
  - 保留 Supabase API Key 硬编码（原始脚本特性）
  - 返回 dict 而非 JSON 字符串
  - playerContent 返回 parse=0 直链
"""
import sys
import re
import json
import base64
import time
import requests
from concurrent.futures import ThreadPoolExecutor, as_completed
from urllib.parse import quote

try:
    from base.spider import Spider as BaseSpider
except ImportError:
    class BaseSpider:
        def init(self, extend=""): pass
        def fetch(self, url, headers=None, **kw):
            kw.pop('timeout', None)
            r = requests.get(url, headers=headers, timeout=15, **kw)
            r.encoding = 'utf-8'
            return r
        def getProxyUrl(self):
            return ''

# ── 平台配置 ──────────────────────────────────
HOST = 'https://51papaya-api.b-cdn.net'
SUP = 'https://phbobyhxsyymolsmyzmq.supabase.co'
KEY = 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InBoYm9ieWh4c3l5bW9sc215em1xIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NjkzOTMwOTgsImV4cCI6MjA4NDk2OTA5OH0.gPMNlZP9X1lN1tdhkRia7QZg8UakWcY2UVbgD7Pc7H0'
UA = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0.0.0 Safari/537.36'
CATEGORIES = [
    {"type_id": "feed", "type_name": "最新视频"},
    {"type_id": "series", "type_name": "AI短剧"},
    {"type_id": "rt:ai", "type_name": "AI"},
    {"type_id": "rt:ai短剧", "type_name": "AI短剧标签"},
    {"type_id": "rt:短剧", "type_name": "短剧"},
    {"type_id": "rt:ai视频", "type_name": "AI视频"},
]

# ── 冷静期常量 ────────────────────────────────
_PROBE_COOLDOWN = 600  # 10 分钟


class Spider(BaseSpider):
    def getName(self):
        return "51木瓜"

    def init(self, extend=None):
        # 1) 先 super，让 base.spider 注入 _vbox_effective_hosts
        try:
            super().init(extend)
        except Exception:
            pass

        # 2) 域名注入：优先 _vbox_effective_hosts，其次 extend，最后默认
        injected = getattr(self, '_vbox_effective_hosts', None) or []
        if injected:
            self._candidates = [str(h).rstrip('/') for h in injected]
        else:
            self._candidates = [HOST, SUP]

        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': UA,
            'apikey': KEY,
            'Authorization': 'Bearer ' + KEY
        })
        self.base = self._candidates[0]
        self._probe_cache = {}       # {domain: (success, timestamp)}
        self._probe_lock = None
        self._feed_cache = None

    # ── 并发域名探测（带 10 分钟冷静期）────────
    def _probe_domain(self, domain):
        """探测单个域名是否可用，带冷静期缓存"""
        now = time.time()
        if domain in self._probe_cache:
            ok, ts = self._probe_cache[domain]
            if now - ts < _PROBE_COOLDOWN:
                return ok
        # 实际探测
        try:
            u = domain + '/functions/v1/content-feed?limit=1'
            r = self.session.get(u, timeout=8)
            ok = r.status_code == 200
        except Exception:
            ok = False
        self._probe_cache[domain] = (ok, now)
        return ok

    def _resolve_hosts(self):
        """并发探测所有候选域名，返回可用域名列表（按响应顺序）"""
        # 先过滤冷静期内已知可用的
        now = time.time()
        cached_ok = []
        need_probe = []
        for d in self._candidates:
            if d in self._probe_cache:
                ok, ts = self._probe_cache[d]
                if now - ts < _PROBE_COOLDOWN:
                    if ok:
                        cached_ok.append(d)
                    continue
            need_probe.append(d)

        if cached_ok and not need_probe:
            return cached_ok

        if need_probe:
            results = []
            with ThreadPoolExecutor(max_workers=len(need_probe)) as ex:
                futs = {ex.submit(self._probe_domain, d): d for d in need_probe}
                for f in as_completed(futs):
                    d = futs[f]
                    if f.result():
                        results.append(d)
            return cached_ok + results
        return cached_ok

    def _call(self, name, body=None, query=''):
        """并发调用：所有可用域名同时请求，先到先得"""
        hosts = self._resolve_hosts()
        if not hosts:
            hosts = self._candidates

        def go(base):
            try:
                u = base + '/functions/v1/' + name + (('?' + query) if query else '')
                if body is not None:
                    r = self.session.post(u, json=body, timeout=10)
                else:
                    r = self.session.get(u, timeout=10)
                if r.status_code == 200:
                    return r.json()
            except Exception:
                pass
            return None

        with ThreadPoolExecutor(max_workers=len(hosts)) as ex:
            futs = [ex.submit(go, b) for b in hosts]
            for f in as_completed(futs):
                d = f.result()
                if d:
                    # 记录成功域名（更新冷静期）
                    idx = futs.index(f)
                    self._probe_cache[hosts[idx]] = (True, time.time())
                    self.base = hosts[idx]
                    return d
        return None

    def _feed(self, deep=8):
        if self._feed_cache is not None:
            return self._feed_cache
        items = []
        cur = None
        for _ in range(deep):
            body = {'limit': 50}
            if cur:
                body['cursor'] = cur
            d = self._call('content-feed', body=body)
            if not d:
                break
            chunk = d.get('items') or []
            items.extend(chunk)
            cur = d.get('next_cursor')
            if not cur or not chunk:
                break
        self._feed_cache = items
        return items

    def _pic(self, item):
        v2 = item.get('v2_poster_url')
        if v2:
            return v2
        pf = item.get('preview_frame_urls') or []
        if pf:
            return pf[0]
        pm = item.get('post_media') or []
        for m in pm:
            if m.get('media_type') == 'image' and m.get('url'):
                return m['url']
        return ''

    def _items(self, d, tag=None):
        rows = []
        for it in d.get('items') or []:
            if it.get('price_pc'):
                continue
            if not it.get('is_video'):
                continue
            if tag:
                tl = tag.lower()
                if not any(tl in str(x).lower() for x in (it.get('tags') or [])):
                    continue
            title = it.get('title') or ''
            vid = 'p:%s:%s' % (it.get('id', ''), base64.urlsafe_b64encode(title.encode()).decode().rstrip('='))
            rows.append({
                'vod_id': vid,
                'vod_name': title,
                'vod_pic': self._pic(it),
                'vod_remarks': self._rm(it)
            })
        return rows

    def _series_items(self, d):
        rows = []
        for s in d.get('series') or []:
            free = s.get('free_episode_count') or 0
            total = s.get('episode_count') or 0
            if free < 1:
                continue
            st = s.get('stats') or {}
            total2 = st.get('total_episodes') or total or ''
            remark = '共%s集·免费%s集' % (total2, free)
            if free < total:
                remark += '·VIP%d集' % (total - free)
            rows.append({
                'vod_id': 'b:' + s.get('bundle_id', ''),
                'vod_name': s.get('title') or '',
                'vod_pic': s.get('cover_url') or '',
                'vod_remarks': remark
            })
        return rows

    def _rm(self, it):
        price = it.get('price_pc') or 0
        return ('VIP·%s' % price) if price else '免费'

    def homeContent(self, filter=False):
        d = self._call('content-feed', query='limit=20')
        return {'class': CATEGORIES, 'list': self._items(d) if d else []}

    def homeVideoContent(self):
        d = self._call('content-feed', query='limit=20')
        return {'list': self._items(d) if d else []}

    def categoryContent(self, tid, pg, filter=False, extend=None):
        try:
            pg = int(pg or 1)
        except Exception:
            pg = 1
        if tid == 'series':
            d = self._call('series-feed', query='limit=20&offset=%d' % ((pg - 1) * 20))
            if not d:
                return {'list': [], 'page': pg, 'pagecount': pg}
            total = d.get('total') or 0
            return {
                'list': self._series_items(d),
                'page': pg,
                'pagecount': max(1, total // 20 + 1)
            }
        if tid == 'feed' or not tid:
            d = self._call('content-feed', query='limit=20')
            return {'list': self._items(d) if d else [], 'page': pg, 'pagecount': 1}
        label = tid[3:] if tid.startswith('rt:') else tid
        return {
            'list': self._items({'items': self._feed()}, label),
            'page': pg,
            'pagecount': 1
        }

    def detailContent(self, ids):
        u = ids[0] if isinstance(ids, (list, tuple)) else str(ids)
        if u.startswith('b:'):
            return self._bundle_detail(u[2:])
        return self._post_detail(u)

    def _post_detail(self, raw):
        parts = raw.split(':', 2)
        pid = parts[1]
        title = ''
        if len(parts) > 2:
            try:
                title = base64.urlsafe_b64decode(parts[2] + '=' * (-len(parts[2]) % 4)).decode()
            except Exception:
                title = ''
        durl = ''
        if title:
            d2 = self._call('content-feed', body={'limit': 20, 'keyword': title})
            hit = next((x for x in (d2.get('items') or []) if x.get('id') == pid), None) if d2 else None
            if hit:
                srcs = hit.get('v2_video_srcs') or {}
                for k in ['hd', 'sd', 'mobile', '360p']:
                    if srcs.get(k):
                        durl = srcs[k]
                        break
        if durl:
            return {'list': [{
                'vod_id': 'p:' + pid,
                'vod_name': title,
                'vod_pic': '',
                'vod_remarks': '直链',
                'vod_play_from': '直链',
                'vod_play_url': '第1集$%s' % durl
            }]}
        d = self._call('content-detail', body={'post_id': pid})
        if not d:
            return {'list': []}
        vs = d.get('video_sources') or {}
        pm = d.get('post_media') or []
        srcs = {}
        for k in ['1080p', '720p', '360p', 'hd', 'sd', 'mobile']:
            v = vs.get(k)
            if v:
                srcs[k] = v
        for m in pm:
            if m.get('media_type') == 'video' and m.get('url'):
                srcs.setdefault('sd', m['url'])
        if not srcs:
            return {'list': []}
        keys = [k for k in ['1080p', '720p', '360p', 'hd', 'sd', 'mobile'] if k in srcs]
        return {'list': [{
            'vod_id': 'p:' + pid,
            'vod_name': d.get('title') or title,
            'vod_pic': self._pic(d),
            'vod_content': d.get('description') or '',
            'vod_remarks': self._rm(d),
            'vod_play_from': '$$$'.join(keys),
            'vod_play_url': '$$$'.join('第1集$p:%s' % pid for _ in keys)
        }]}

    def _bundle_detail(self, bid):
        d = self._call('bundle-detail', query='bundle_id=' + bid)
        if not d:
            return {'list': []}
        b = d.get('bundle') or {}
        items = d.get('items') or []
        plays = []
        locked = 0
        for it in items:
            order = it.get('item_order')
            title = it.get('title') or ('第%s集' % order)
            access = it.get('access') or {}
            if access.get('can_access'):
                plays.append('%s$b:%s:%s' % (title, bid, order))
            else:
                locked += 1
        if not plays:
            return {'list': []}
        return {'list': [{
            'vod_id': 'b:' + bid,
            'vod_name': b.get('title') or '',
            'vod_pic': b.get('cover_url') or '',
            'vod_content': b.get('description') or '',
            'vod_remarks': '免费%s集%s' % (len(plays), ('·VIP%d集' % locked) if locked else ''),
            'vod_play_from': '短剧',
            'vod_play_url': '#'.join(plays)
        }]}

    def searchContent(self, key, quick=False):
        d = self._call('content-feed', body={'limit': 20, 'keyword': str(key)})
        return {'list': self._items(d) if d else []}

    def playerContent(self, flag, pid, vipFlags=None):
        pid = str(pid)
        if pid.startswith('http'):
            return {'parse': 0, 'url': pid, 'header': {'User-Agent': UA, 'Referer': 'https://www.51papaya.com/'}}
        if pid.startswith('b:'):
            parts = pid.split(':')
            bid = parts[1]
            order = parts[2] if len(parts) > 2 else '1'
            d = self._call('series-media-url', query='bundle_id=%s&episode_order=%s' % (bid, order))
            if d and d.get('url'):
                return {'parse': 0, 'url': d['url'], 'header': {'User-Agent': UA, 'Referer': 'https://www.51papaya.com/'}}
            return {'parse': 0, 'url': ''}
        post_id = pid[2:] if pid.startswith('p:') else pid
        d = self._call('content-detail', body={'post_id': post_id})
        if not d:
            return {'parse': 0, 'url': ''}
        vs = d.get('video_sources') or {}
        url = vs.get(flag) or vs.get('1080p') or vs.get('720p') or vs.get('sd') or vs.get('mobile') or ''
        if not url:
            pm = d.get('post_media') or []
            for m in pm:
                if m.get('media_type') == 'video' and m.get('url'):
                    url = m['url']
                    break
        return {'parse': 0, 'url': url, 'header': {'User-Agent': UA, 'Referer': 'https://www.51papaya.com/'}}

    def localProxy(self, param):
        return [404, 'text/plain', '']

    def isVideoFormat(self, url):
        url = str(url).lower()
        return '.m3u8' in url or '.mp4' in url or '.ts' in url or '.flv' in url

    def manualVideoCheck(self):
        return False

    def destroy(self):
        try:
            if hasattr(self, 'session'):
                self.session.close()
        except Exception:
            pass