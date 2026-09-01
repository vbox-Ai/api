# -*- coding: utf-8 -*-
"""
台湾成人直播 — vbox 福利专区直播栏目适配版
数据源: 台湾成人直播频道 (m3u8/ts/flv 直链)
"""
import re

try:
    from base.spider import Spider as BaseSpider
except ImportError:
    class BaseSpider:
        def init(self, extend=""):
            return {}


class Spider(BaseSpider):

    def getName(self):
        return "台湾成人直播"

    def init(self, extend=""):
        try:
            super().init(extend)
        except Exception:
            pass
        # 内嵌 m3u 数据（来源: 用户提供的直播频道列表）
        self._m3u_raw = """#台湾成人直播,#genre#
驚艷台,http://15.204.105.50:25461/live/G2s9zK2n9m/xDtwVfWM8T/87.ts
驚艷台,http://15.204.105.50:25461/live/G2s9zK2n9m/xDtwVfWM8T/85.ts
潘朵拉,http://15.204.105.50:25461/live/G2s9zK2n9m/xDtwVfWM8T/86.ts
松视1,http://15.204.105.50:25461/live/G2s9zK2n9m/xDtwVfWM8T/88.ts
松视2,http://15.204.105.50:25461/live/G2s9zK2n9m/xDtwVfWM8T/89.ts
松視3,http://15.204.105.50:25461/live/G2s9zK2n9m/xDtwVfWM8T/90.ts
24×7东京热,http://1tv41.icu:8080/LaLa34@yahoo.com/LaLa7678/159976
24×7日本道,http://1tv41.icu:8080/LaLa34@yahoo.com/LaLa7678/159958
24x7啪啪啪,http://7707bo.trustdeveloppment.com/live/cx_15642.flv"""
        self._cache = None
        return {}

    def _load_channels(self):
        """解析 m3u 内容，返回频道列表"""
        if self._cache is not None:
            return self._cache
        items = []
        for line in self._m3u_raw.strip().split('\n'):
            line = line.strip()
            if not line or line.startswith('#'):
                continue
            if ',' in line:
                parts = line.split(',', 1)
                name = parts[0].strip()
                url = parts[1].strip()
                if url.startswith('http'):
                    items.append({'name': name, 'url': url})
        self._cache = items
        return items

    def homeContent(self, filter=False):
        channels = self._load_channels()
        return {
            'class': [{'type_id': 'taiwan_live', 'type_name': '台湾成人直播'}],
            'filters': {}
        }

    def homeVideoContent(self):
        channels = self._load_channels()
        return {'list': self._to_vodlist(channels)}

    def categoryContent(self, tid, pg, filter=False, extend=""):
        channels = self._load_channels()
        return {
            'list': self._to_vodlist(channels),
            'page': int(pg or 1),
            'pagecount': 1,
            'limit': len(channels),
            'total': len(channels)
        }

    def _to_vodlist(self, channels):
        out = []
        for ch in channels:
            out.append({
                'vod_id': ch['url'],
                'vod_name': ch['name'],
                'vod_pic': '',
                'vod_remarks': '直播',
                'vod_play_from': '台湾成人直播',
                'vod_play_url': f"{ch['name']}$" + ch['url']
            })
        return out

    def detailContent(self, ids):
        if not ids:
            return {'list': []}
        url = ids[0] if isinstance(ids, list) else ids
        return {'list': [{
            'vod_id': url,
            'vod_name': '台湾成人直播',
            'vod_pic': '',
            'vod_play_from': '台湾成人直播',
            'vod_play_url': f"直播${url}"
        }]}

    def playerContent(self, flag, id, vipFlags=None):
        url = str(id).strip()
        if not url.startswith('http'):
            return {'parse': 0, 'url': ''}
        return {
            'parse': 0,
            'url': url,
            'header': {
                'User-Agent': 'Mozilla/5.0 (iPhone; CPU iPhone OS 16_0 like Mac OS X) AppleWebKit/605.1.15'
            }
        }

    def searchContent(self, key, quick=False, pg=1):
        channels = self._load_channels()
        kw = str(key).lower()
        out = [x for x in channels if kw in x['name'].lower()]
        return {'list': self._to_vodlist(out), 'page': 1}

    def isVideoFormat(self, url):
        if not url:
            return False
        url = url.lower()
        return any(url.endswith(x) for x in ['.ts', '.m3u8', '.flv', '.mp4', '.avi', '.mkv'])

    def manualVideoCheck(self):
        return False
