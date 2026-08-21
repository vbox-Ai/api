# -*- coding: utf-8 -*-
import re, json, sys
try:
    from base.spider import Spider as BaseSpider
except ImportError:
    class BaseSpider: pass

class Spider(BaseSpider):
    def getName(self):
        return "欧美大片直播"
    
    def init(self, extend=""):
        try:
            super().init(extend)
        except Exception:
            pass
        self.channels = [
            {"title": "EroLuxe 60FPS", "url": "http://u.vipl.one/high/ierw63qgf1/1684.m3u8", "logo": "http://epg.cdntv.online/img/1684.png"},
            {"title": "EroLuxe Anal", "url": "http://u.vipl.one/high/ierw63qgf1/1685.m3u8", "logo": "http://epg.cdntv.online/img/1685.png"},
            {"title": "EroLuxe Blondes", "url": "http://u.vipl.one/high/ierw63qgf1/1686.m3u8", "logo": "http://epg.cdntv.online/img/1686.png"},
            {"title": "EroLuxe Blowjob", "url": "http://u.vipl.one/high/ierw63qgf1/1687.m3u8", "logo": "http://epg.cdntv.online/img/1687.png"},
            {"title": "EroLuxe Cinema", "url": "http://u.vipl.one/high/ierw63qgf1/1688.m3u8", "logo": "http://epg.cdntv.online/img/1688.png"},
            {"title": "EroLuxe Cosplay", "url": "http://u.vipl.one/high/ierw63qgf1/1689.m3u8", "logo": "http://epg.cdntv.online/img/1689.png"},
            {"title": "EroLuxe Ebony", "url": "http://u.vipl.one/high/ierw63qgf1/1690.m3u8", "logo": "http://epg.cdntv.online/img/1690.png"},
            {"title": "EroLuxe Gays", "url": "http://u.vipl.one/high/ierw63qgf1/1691.m3u8", "logo": "http://epg.cdntv.online/img/1691.png"},
            {"title": "EroLuxe Gloryhole", "url": "http://u.vipl.one/high/ierw63qgf1/1692.m3u8", "logo": "http://epg.cdntv.online/img/1692.png"},
            {"title": "EroLuxe Henati", "url": "http://u.vipl.one/high/ierw63qgf1/1693.m3u8", "logo": "http://epg.cdntv.online/img/1693.png"},
            {"title": "EroLuxe Japanese", "url": "http://u.vipl.one/high/ierw63qgf1/1694.m3u8", "logo": "http://epg.cdntv.online/img/1694.png"},
            {"title": "EroLuxe Lesbians", "url": "http://u.vipl.one/high/ierw63qgf1/1695.m3u8", "logo": "http://epg.cdntv.online/img/1695.png"},
            {"title": "EroLuxe Massage", "url": "http://u.vipl.one/high/ierw63qgf1/1696.m3u8", "logo": "http://epg.cdntv.online/img/1696.png"},
            {"title": "EroLuxe Milf", "url": "http://u.vipl.one/high/ierw63qgf1/1697.m3u8", "logo": "http://epg.cdntv.online/img/1697.png"},
            {"title": "EroLuxe Russian Teens", "url": "http://u.vipl.one/high/ierw63qgf1/1698.m3u8", "logo": "http://epg.cdntv.online/img/1698.png"},
            {"title": "EroLuxe Orgy", "url": "http://u.vipl.one/high/ierw63qgf1/1699.m3u8", "logo": "http://epg.cdntv.online/img/1699.png"},
            {"title": "EroLuxe Pregnant", "url": "http://u.vipl.one/high/ierw63qgf1/1700.m3u8", "logo": "http://epg.cdntv.online/img/1700.png"},
            {"title": "EroLuxe Shemales", "url": "http://u.vipl.one/high/ierw63qgf1/1701.m3u8", "logo": "http://epg.cdntv.online/img/1701.png"},
            {"title": "EroLuxe Solo", "url": "http://u.vipl.one/high/ierw63qgf1/1702.m3u8", "logo": "http://epg.cdntv.online/img/1702.png"},
            {"title": "EroLuxe Step Family", "url": "http://u.vipl.one/high/ierw63qgf1/1703.m3u8", "logo": "http://epg.cdntv.online/img/1703.png"},
            {"title": "EroLuxe 4K UHD", "url": "http://u.vipl.one/high/ierw63qgf1/1704.m3u8", "logo": "http://epg.cdntv.online/img/1704.png"},
            {"title": "EroLuxe VIP 4K 60FPS", "url": "http://u.vipl.one/high/ierw63qgf1/1705.m3u8", "logo": "http://epg.cdntv.online/img/1705.png"},
            {"title": "EroLuxe BBW", "url": "http://u.vipl.one/high/ierw63qgf1/1706.m3u8", "logo": "http://epg.cdntv.online/img/1706.png"},
            {"title": "EroLuxe BabySitter", "url": "http://u.vipl.one/high/ierw63qgf1/1707.m3u8", "logo": "http://epg.cdntv.online/img/1707.png"},
            {"title": "EroLuxe BDSM", "url": "http://u.vipl.one/high/ierw63qgf1/1708.m3u8", "logo": "http://epg.cdntv.online/img/1708.png"},
            {"title": "EroLuxe Big Cock", "url": "http://u.vipl.one/high/ierw63qgf1/1709.m3u8", "logo": "http://epg.cdntv.online/img/1709.png"},
            {"title": "EroLuxe Brunette", "url": "http://u.vipl.one/high/ierw63qgf1/1710.m3u8", "logo": "http://epg.cdntv.online/img/1710.png"},
            {"title": "EroLuxe CheerLeader", "url": "http://u.vipl.one/high/ierw63qgf1/1711.m3u8", "logo": "http://epg.cdntv.online/img/1711.png"},
            {"title": "EroLuxe Cuckold", "url": "http://u.vipl.one/high/ierw63qgf1/1712.m3u8", "logo": "http://epg.cdntv.online/img/1712.png"},
            {"title": "EroLuxe Creampie", "url": "http://u.vipl.one/high/ierw63qgf1/1713.m3u8", "logo": "http://epg.cdntv.online/img/1713.png"},
            {"title": "EroLuxe Fake Taxi", "url": "http://u.vipl.one/high/ierw63qgf1/1714.m3u8", "logo": "http://epg.cdntv.online/img/1714.png"},
            {"title": "EroLuxe Foot Fetish", "url": "http://u.vipl.one/high/ierw63qgf1/1715.m3u8", "logo": "http://epg.cdntv.online/img/1715.png"},
            {"title": "EroLuxe Fisting", "url": "http://u.vipl.one/high/ierw63qgf1/1716.m3u8", "logo": "http://epg.cdntv.online/img/1716.png"},
            {"title": "EroLuxe GangBang", "url": "http://u.vipl.one/high/ierw63qgf1/1717.m3u8", "logo": "http://epg.cdntv.online/img/1717.png"},
            {"title": "EroLuxe Parody", "url": "http://u.vipl.one/high/ierw63qgf1/1718.m3u8", "logo": "http://epg.cdntv.online/img/1718.png"},
            {"title": "EroLuxe POV", "url": "http://u.vipl.one/high/ierw63qgf1/1719.m3u8", "logo": "http://epg.cdntv.online/img/1719.png"},
            {"title": "EroLuxe Public Agent", "url": "http://u.vipl.one/high/ierw63qgf1/1720.m3u8", "logo": "http://epg.cdntv.online/img/1720.png"},
            {"title": "EroLuxe RedHeads", "url": "http://u.vipl.one/high/ierw63qgf1/1721.m3u8", "logo": "http://epg.cdntv.online/img/1721.png"},
            {"title": "EroLuxe Schoolgirl", "url": "http://u.vipl.one/high/ierw63qgf1/1722.m3u8", "logo": "http://epg.cdntv.online/img/1722.png"},
            {"title": "EroLuxe Asian", "url": "http://u.vipl.one/high/ierw63qgf1/1723.m3u8", "logo": "http://epg.cdntv.online/img/1723.png"},
        ]
        self.all_channels = sorted(self.channels, key=lambda x: x.get('title', ''))
    
    def homeContent(self, filter):
        return {"class": [{"type_id": "all", "type_name": "全部频道"}]}
    
    def homeVideoContent(self):
        return {"list": self.all_channels[:20]}
    
    def categoryContent(self, tid, pg, filter, extend):
        page = int(pg or 1)
        limit = 20
        channels = self.all_channels
        start = (page - 1) * limit
        return {"list": channels[start:start+limit], "page": page, "pagecount": (len(channels) + limit - 1) // limit, "limit": limit, "total": len(channels)}
    
    def detailContent(self, ids):
        try:
            idx = int(ids[0])
            ch = self.all_channels[idx]
            vod = {"vod_id": str(idx), "vod_name": ch.get('title', ''), "vod_pic": ch.get('logo', ''), "vod_play_from": "播放", "vod_play_url": f"播放${ch.get('url', '')}"}
            return {"list": [vod]}
        except:
            return {"list": []}
    
    def playerContent(self, flag, id, vipFlags):
        try:
            idx = int(id)
            ch = self.all_channels[idx]
            return {"parse": 0, "url": ch.get('url', ''), "header": {"User-Agent": "Mozilla/5.0"}}
        except:
            return {"parse": 0, "url": id, "header": {"User-Agent": "Mozilla/5.0"}}
    
    def searchContent(self, key, quick, pg=1):
        items = [c for c in self.all_channels if key.lower() in c.get('title', '').lower()]
        return {"list": items, "page": 1}
