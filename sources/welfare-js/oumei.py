# -*- coding: utf-8 -*-
"""
欧美大片直播 — vbox 福利专区直播栏目适配版
数据源: oumei.m3u (仓库内静态文件, 40 频道 EroLuxe 成人直播)
从 m3u 在线读取, 解析频道 → 直链播放 (parse=0)
"""
import re

try:
    from base.spider import Spider as BaseSpider
except ImportError:
    class BaseSpider:
        def init(self, extend=""):
            return {}

DATA_URL = "https://raw.githubusercontent.com/vbox-Ai/api/main/sources/welfare-js/oumei.m3u"


class Spider(BaseSpider):

    def getName(self):
        return "欧美大片直播"

    def init(self, extend=""):
        try:
            super().init(extend)
        except Exception:
            pass
        return {}

    def _load_m3u(self):
        raw = ""
        try:
            r = self.fetch(DATA_URL, timeout=20)
            if r:
                raw = r.text if hasattr(r, 'text') else r.content.decode('utf-8', 'ignore')
        except Exception:
            pass
        if not raw:
            return []
        lines = [l.strip() for l in raw.splitlines()]
        items = []
        i = 0
        while i < len(lines):
            l = lines[i]
            if l.startswith('#EXTINF'):
                logo = ""
                lm = re.search(r'tvg-logo="([^"]*)"', l)
                if lm:
                    logo = lm.group(1)
                name = l.split(',', 1)[1].strip() if ',' in l else "频道"
                # 向后找 URL, 跳过 #EXTGRP 等注释行, 遇到下一条 EXTINF 则停
                j = i + 1
                while j < len(lines):
                    nj = lines[j]
                    if nj.startswith('#EXTINF'):
                        break
                    if nj.startswith('http'):
                        items.append({'name': name, 'url': nj.strip(), 'logo': logo})
                        break
                    j += 1
                i += 1
            else:
                i += 1
        return items

    def homeContent(self, filter=False):
        return {'class': [{'type_id': 'oumei', 'type_name': '欧美直播'}], 'filters': {}}

    def homeVideoContent(self):
        return {'list': self._to_vodlist(self._load_m3u())[:48]}

    def categoryContent(self, tid, pg, filter=False, extend=""):
        all_items = self._to_vodlist(self._load_m3u())
        return {'list': all_items, 'page': int(pg or 1), 'pagecount': 1, 'limit': len(all_items), 'total': len(all_items)}

    def _to_vodlist(self, items):
        out = []
        for it in items:
            out.append({
                'vod_id': it['url'],
                'vod_name': it['name'],
                'vod_pic': it['logo'],
                'vod_remarks': 'EroLuxe'
            })
        return out

    def detailContent(self, ids):
        if not ids:
            return {'list': []}
        raw = ids[0] if isinstance(ids, list) else ids
        url = raw
        return {'list': [{
            'vod_id': url,
            'vod_name': '欧美直播',
            'vod_pic': '',
            'vod_remarks': '',
            'vod_actor': '',
            'vod_content': 'EroLuxe 成人直播',
            'vod_play_from': '欧美大片直播',
            'vod_play_url': '直播$' + url
        }]}

    def playerContent(self, flag, id, vipFlags=None):
        url = str(id).strip()
        if not url.startswith('http'):
            return {'parse': 0, 'url': ''}
        return {'parse': 0, 'url': url, 'header': {'User-Agent': 'Mozilla/5.0'}}

    def searchContent(self, key, quick=False, pg=1):
        items = self._load_m3u()
        kw = str(key).lower()
        out = [x for x in items if kw in x['name'].lower()]
        return {'list': self._to_vodlist(out)[:50], 'page': 1}

    def isVideoFormat(self, url):
        return '.m3u8' in url or '.ts' in url

    def manualVideoCheck(self):
        return False

    def localProxy(self, param):
        return []

    def destroy(self):
        pass
