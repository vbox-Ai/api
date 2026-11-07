# -*- coding: utf-8 -*-
"""X99视频导航 — vbox 远程源 python 蜘蛛（P0 骨架）

由 build_nav_source.py 生成，请勿手改。
类型: video    快照: 2026.11.07.1434
"""
import base64
import json
import re
import ssl
import threading
import time
import urllib.error
import urllib.parse
import urllib.request

try:
    from base.spider import Spider as SpiderBase
except ImportError:  # 本地调试
    class SpiderBase(object):
        def __init__(self):
            self._vbox_effective_hosts = []

        def getCache(self, key):
            return None

        def setCache(self, key, value):
            return "ok"

        def delCache(self, key):
            return "ok"

KIND = "video"
PLATFORM_KEY = "x99dh_video_py"
TITLE = "X99视频导航"
SNAPSHOT_VERSION = "2026.11.07.1434"
SNAPSHOT = json.loads('{"version":"2026.11.07.1434","entry":["https://x99dh.net","https://x99dh.lat"],"platforms":[{"key":"x99_be9dc0cd","name":"MissAV","kind":"video","adapter":"missav","desc":"著名亚洲视频站点","icon":"play.rectangle.fill","url":"https://www.thisav66.com/cn","lines":[{"url":"https://www.missav05.com/cn","testUrl":"https://www.missav05.com/status.html","ok":true,"ms":513.0},{"url":"https://www.missav03.net/cn","testUrl":"https://www.missav03.net/status.html","ok":true,"ms":525.0},{"url":"https://www.missav666.net/cn","testUrl":"https://www.missav666.net/status.html","ok":true,"ms":651.0},{"url":"https://www.missav08.net/cn","testUrl":"https://www.missav08.net/status.html","ok":true,"ms":681.0},{"url":"https://www.njavtv.my/cn","testUrl":"https://www.njavtv.my/status.html","ok":true,"ms":703.0},{"url":"https://www.missav3.one/cn","testUrl":"https://www.missav3.one/status.html","ok":true,"ms":787.0},{"url":"https://www.njav01.net/cn","testUrl":"https://www.njav01.net/status.html","ok":true,"ms":805.0},{"url":"https://www.njavtv01.com/cn","testUrl":"https://www.njavtv01.com/status.html","ok":true,"ms":817.0},{"url":"https://www.missav08.com/cn","testUrl":"https://www.missav08.com/status.html","ok":true,"ms":831.0},{"url":"https://www.missav1.one/cn","testUrl":"https://www.missav1.one/status.html","ok":true,"ms":858.0},{"url":"https://www.njav01.com/cn","testUrl":"https://www.njav01.com/status.html","ok":true,"ms":890.0},{"url":"https://www.thisav33.net/cn","testUrl":"https://www.thisav33.net/status.html","ok":true,"ms":937.0},{"url":"https://www.missav888.cc/cn","testUrl":"https://www.missav888.cc/status.html","ok":true,"ms":999.0},{"url":"https://www.missav123.nl/cn","testUrl":"https://www.missav123.nl/status.html","ok":true,"ms":1013.0},{"url":"https://www.thisav02.net/cn","testUrl":"https://www.thisav02.net/status.html","ok":true,"ms":1018.0},{"url":"https://www.thisav01.net/cn","testUrl":"https://www.thisav01.net/status.html","ok":true,"ms":1089.0},{"url":"https://www.thisav01.cc/cn","testUrl":"https://www.thisav01.cc/status.html","ok":true,"ms":1103.0},{"url":"https://www.missav05.net/cn","testUrl":"https://www.missav05.net/status.html","ok":true,"ms":1105.0},{"url":"https://www.njavtv.art/cn","testUrl":"https://www.njavtv.art/status.html","ok":true,"ms":1137.0},{"url":"https://www.missav-ai.cc/cn","testUrl":"https://www.missav-ai.cc/status.html","ok":true,"ms":1148.0},{"url":"https://www.missav.watch/cn","testUrl":"https://www.missav.watch/status.html","ok":true,"ms":1153.0},{"url":"https://www.missav02.net/cn","testUrl":"https://www.missav02.net/status.html","ok":true,"ms":1179.0},{"url":"https://www.missav666.cc/cn","testUrl":"https://www.missav666.cc/status.html","ok":true,"ms":1232.0},{"url":"https://www.missav09.com/cn","testUrl":"https://www.missav09.com/status.html","ok":true,"ms":1266.0},{"url":"https://www.thisav02.com/cn","testUrl":"https://www.thisav02.com/status.html","ok":true,"ms":1293.0},{"url":"https://www.missav06.com/cn","testUrl":"https://www.missav06.com/status.html","ok":true,"ms":1416.0},{"url":"https://www.missav07.net/cn","testUrl":"https://www.missav07.net/status.html","ok":true,"ms":1589.0},{"url":"https://www.thisav.pw/cn","testUrl":"https://www.thisav.pw/status.html","ok":true,"ms":1665.0},{"url":"https://www.thisav.sbs/cn","testUrl":"https://www.thisav.sbs/status.html","ok":true,"ms":1803.0},{"url":"https://www.njavtv.nl/cn","testUrl":"https://www.njavtv.nl/status.html","ok":true,"ms":1875.0},{"url":"https://www.missav888.net/cn","testUrl":"https://www.missav888.net/status.html","ok":true,"ms":1903.0},{"url":"https://www.njav.one/cn","testUrl":"https://www.njav.one/status.html","ok":true,"ms":1980.0},{"url":"https://www.missav123.life/cn","testUrl":"https://www.missav123.life/status.html","ok":true,"ms":2100.0},{"url":"https://www.missav06.net/cn","testUrl":"https://www.missav06.net/status.html","ok":true,"ms":2173.0},{"url":"https://www.thisav33.com/cn","testUrl":"https://www.thisav33.com/status.html","ok":true,"ms":2679.0},{"url":"https://www.missav2.one/cn","testUrl":"https://www.missav2.one/status.html","ok":true,"ms":2906.0},{"url":"https://www.missav01.net/cn","testUrl":"https://www.missav01.net/status.html","ok":true,"ms":3097.0},{"url":"https://www.thisav66.com/cn","testUrl":"https://www.thisav66.com/status.html","ok":true,"ms":7358.0},{"url":"https://www.missav1.vip/cn","testUrl":"https://www.missav1.vip/status.html","ok":false,"ms":1006.0},{"url":"https://www.missav365.icu/cn","testUrl":"https://www.missav365.icu/status.html","ok":false,"ms":1714.0},{"url":"https://www.missav365.one/cn","testUrl":"https://www.missav365.one/status.html","ok":false,"ms":1904.0}],"classes":[{"type_id":"20","type_name":"国产"},{"type_id":"21","type_name":"日本有码"},{"type_id":"22","type_name":"日本无码"},{"type_id":"28","type_name":"中文字幕"},{"type_id":"23","type_name":"欧美"},{"type_id":"24","type_name":"动漫"},{"type_id":"25","type_name":"伦理"}]},{"key":"x99_531d29bb","name":"Hanime1","kind":"video","adapter":"missav","desc":"著名动漫视频站点","icon":"play.rectangle.fill","url":"https://www.hanime16.com/enter","lines":[{"url":"https://www.hanime101.net/enter","testUrl":"https://www.hanime101.net/status.html","ok":true,"ms":344.0},{"url":"https://www.hanime102.net/enter","testUrl":"https://www.hanime102.net/status.html","ok":true,"ms":440.0},{"url":"https://www.hanime999.cc/enter","testUrl":"https://www.hanime999.cc/status.html","ok":true,"ms":594.0},{"url":"https://www.hanime169.com/enter","testUrl":"https://www.hanime169.com/status.html","ok":true,"ms":803.0},{"url":"https://www.hanime2.cfd/enter","testUrl":"https://www.hanime2.cfd/status.html","ok":true,"ms":808.0},{"url":"https://www.hanime103.com/enter","testUrl":"https://www.hanime103.com/status.html","ok":true,"ms":808.0},{"url":"https://www.hanime169.net/enter","testUrl":"https://www.hanime169.net/status.html","ok":true,"ms":811.0},{"url":"https://www.hanime101.com/enter","testUrl":"https://www.hanime101.com/status.html","ok":true,"ms":854.0},{"url":"https://www.hanime163.com/enter","testUrl":"https://www.hanime163.com/status.html","ok":true,"ms":860.0},{"url":"https://www.hanime666.net/enter","testUrl":"https://www.hanime666.net/status.html","ok":true,"ms":864.0},{"url":"https://www.hanime1.my/enter","testUrl":"https://www.hanime1.my/status.html","ok":true,"ms":1012.0},{"url":"https://www.hanime169.cc/enter","testUrl":"https://www.hanime169.cc/status.html","ok":true,"ms":1080.0},{"url":"https://www.hanime123.one/enter","testUrl":"https://www.hanime123.one/status.html","ok":true,"ms":1102.0},{"url":"https://www.hanime999.net/enter","testUrl":"https://www.hanime999.net/status.html","ok":true,"ms":1114.0},{"url":"https://www.hanime2.one/enter","testUrl":"https://www.hanime2.one/status.html","ok":true,"ms":1148.0},{"url":"https://www.hanime163.net/enter","testUrl":"https://www.hanime163.net/status.html","ok":true,"ms":1165.0},{"url":"https://www.hanime2.icu/enter","testUrl":"https://www.hanime2.icu/status.html","ok":true,"ms":1199.0},{"url":"https://www.hanime123.org/enter","testUrl":"https://www.hanime123.org/status.html","ok":true,"ms":1384.0},{"url":"https://www.hanime123.cc/enter","testUrl":"https://www.hanime123.cc/status.html","ok":true,"ms":1417.0},{"url":"https://www.hanime123.sbs/enter","testUrl":"https://www.hanime123.sbs/status.html","ok":true,"ms":1565.0},{"url":"https://www.hanime02.com/enter","testUrl":"https://www.hanime02.com/status.html","ok":true,"ms":1679.0},{"url":"https://www.hanime1.art/enter","testUrl":"https://www.hanime1.art/status.html","ok":true,"ms":1711.0},{"url":"https://www.hanime999.com/enter","testUrl":"https://www.hanime999.com/status.html","ok":true,"ms":1805.0},{"url":"https://www.hanime103.net/enter","testUrl":"https://www.hanime103.net/status.html","ok":true,"ms":1994.0},{"url":"https://www.hanime102.com/enter","testUrl":"https://www.hanime102.com/status.html","ok":true,"ms":2600.0},{"url":"https://www.hanime1.life/enter","testUrl":"https://www.hanime1.life/status.html","ok":true,"ms":3269.0},{"url":"https://www.hanime104.com/enter","testUrl":"https://www.hanime104.com/status.html","ok":true,"ms":4640.0},{"url":"https://www.hanime16.com/enter","testUrl":"https://www.hanime16.com/status.html","ok":true,"ms":6543.0},{"url":"https://www.hanime888.net/enter","testUrl":"https://www.hanime888.net/status.html","ok":false,"ms":1150.0},{"url":"https://www.hanime1-me.cc/enter","testUrl":"https://www.hanime1-me.cc/status.html","ok":false,"ms":1185.0},{"url":"https://www.hanime1.pw/enter","testUrl":"https://www.hanime1.pw/status.html","ok":false,"ms":1264.0},{"url":"https://www.hanime2.org/enter","testUrl":"https://www.hanime2.org/status.html","ok":false,"ms":2970.0}],"classes":[]},{"key":"x99_5e2df580","name":"LissAV","kind":"video","adapter":"generic","desc":"最全日本AV站点","icon":"play.rectangle.fill","url":"https://huangguo04.net/asian/zh-CN","lines":[{"url":"https://huangguo02.net/asian/zh-CN","testUrl":"https://huangguo02.net/status.html","ok":true,"ms":649.0},{"url":"https://lissav.net/asian/zh-CN","testUrl":"https://lissav.net/status.html","ok":true,"ms":705.0},{"url":"https://tktube.vip/asian/zh-CN","testUrl":"https://tktube.vip/status.html","ok":true,"ms":744.0},{"url":"https://lissav.nl/asian/zh-CN","testUrl":"https://lissav.nl/status.html","ok":true,"ms":879.0},{"url":"https://lissav.one/asian/zh-CN","testUrl":"https://lissav.one/status.html","ok":true,"ms":881.0},{"url":"https://huangguo01.net/asian/zh-CN","testUrl":"https://huangguo01.net/status.html","ok":true,"ms":994.0},{"url":"https://lissav.ws/asian/zh-CN","testUrl":"https://lissav.ws/status.html","ok":true,"ms":1036.0},{"url":"https://mdba8.com/asian/zh-CN","testUrl":"https://mdba8.com/status.html","ok":true,"ms":1281.0},{"url":"https://madou666.net/asian/zh-CN","testUrl":"https://madou666.net/status.html","ok":true,"ms":1348.0},{"url":"https://lissav.my/asian/zh-CN","testUrl":"https://lissav.my/status.html","ok":true,"ms":1370.0},{"url":"https://lissav.vip/asian/zh-CN","testUrl":"https://lissav.vip/status.html","ok":true,"ms":1409.0},{"url":"https://madou8.pw/asian/zh-CN","testUrl":"https://madou8.pw/status.html","ok":true,"ms":1410.0},{"url":"https://lissav1.com/asian/zh-CN","testUrl":"https://lissav1.com/status.html","ok":true,"ms":1560.0},{"url":"https://madou8.my/asian/zh-CN","testUrl":"https://madou8.my/status.html","ok":true,"ms":1580.0},{"url":"https://tktube.nl/asian/zh-CN","testUrl":"https://tktube.nl/status.html","ok":true,"ms":1658.0},{"url":"https://huangguo123.com/asian/zh-CN","testUrl":"https://huangguo123.com/status.html","ok":true,"ms":2041.0},{"url":"https://javxx.sbs/asian/zh-CN","testUrl":"https://javxx.sbs/status.html","ok":true,"ms":2701.0},{"url":"https://mdba8.net/asian/zh-CN","testUrl":"https://mdba8.net/status.html","ok":true,"ms":2736.0},{"url":"https://madou8.ws/asian/zh-CN","testUrl":"https://madou8.ws/status.html","ok":true,"ms":3145.0},{"url":"https://huangguo04.net/asian/zh-CN","testUrl":"https://huangguo04.net/status.html","ok":true,"ms":3249.0},{"url":"https://huangguo03.net/asian/zh-CN","testUrl":"https://huangguo03.net/status.html","ok":true,"ms":6141.0},{"url":"https://lissav.com/asian/zh-CN","testUrl":"https://lissav.com/status.html","ok":false,"ms":2186.0}],"classes":[]},{"key":"x99_2828ee09","name":"LissAV国产区","kind":"video","adapter":"generic","desc":"数十万精品AV","icon":"play.rectangle.fill","url":"https://huangguo04.net/domestic/zh-CN","lines":[{"url":"https://lissav.my/domestic/zh-CN","testUrl":"https://lissav.my/status.html","ok":true,"ms":190.0},{"url":"https://lissav.nl/domestic/zh-CN","testUrl":"https://lissav.nl/status.html","ok":true,"ms":592.0},{"url":"https://tktube.nl/domestic/zh-CN","testUrl":"https://tktube.nl/status.html","ok":true,"ms":612.0},{"url":"https://mdba8.net/domestic/zh-CN","testUrl":"https://mdba8.net/status.html","ok":true,"ms":618.0},{"url":"https://lissav.one/domestic/zh-CN","testUrl":"https://lissav.one/status.html","ok":true,"ms":729.0},{"url":"https://huangguo123.com/domestic/zh-CN","testUrl":"https://huangguo123.com/status.html","ok":true,"ms":749.0},{"url":"https://madou8.ws/domestic/zh-CN","testUrl":"https://madou8.ws/status.html","ok":true,"ms":768.0},{"url":"https://madou8.pw/domestic/zh-CN","testUrl":"https://madou8.pw/status.html","ok":true,"ms":834.0},{"url":"https://lissav.vip/domestic/zh-CN","testUrl":"https://lissav.vip/status.html","ok":true,"ms":842.0},{"url":"https://javxx.sbs/domestic/zh-CN","testUrl":"https://javxx.sbs/status.html","ok":true,"ms":865.0},{"url":"https://huangguo02.net/domestic/zh-CN","testUrl":"https://huangguo02.net/status.html","ok":true,"ms":992.0},{"url":"https://tktube.vip/domestic/zh-CN","testUrl":"https://tktube.vip/status.html","ok":true,"ms":1146.0},{"url":"https://lissav.ws/domestic/zh-CN","testUrl":"https://lissav.ws/status.html","ok":true,"ms":1150.0},{"url":"https://lissav1.com/domestic/zh-CN","testUrl":"https://lissav1.com/status.html","ok":true,"ms":1172.0},{"url":"https://mdba8.com/domestic/zh-CN","testUrl":"https://mdba8.com/status.html","ok":true,"ms":1225.0},{"url":"https://madou8.my/domestic/zh-CN","testUrl":"https://madou8.my/status.html","ok":true,"ms":1453.0},{"url":"https://lissav.net/domestic/zh-CN","testUrl":"https://lissav.net/status.html","ok":true,"ms":1799.0},{"url":"https://huangguo01.net/domestic/zh-CN","testUrl":"https://huangguo01.net/status.html","ok":true,"ms":1844.0},{"url":"https://madou666.net/domestic/zh-CN","testUrl":"https://madou666.net/status.html","ok":true,"ms":2411.0},{"url":"https://huangguo04.net/domestic/zh-CN","testUrl":"https://huangguo04.net/status.html","ok":true,"ms":3185.0},{"url":"https://huangguo03.net/domestic/zh-CN","testUrl":"https://huangguo03.net/status.html","ok":true,"ms":3965.0},{"url":"https://lissav.com/domestic/zh-CN","testUrl":"https://lissav.com/status.html","ok":false,"ms":1941.0}],"classes":[]},{"key":"x99_2721419a","name":"Jable","kind":"video","adapter":"missav","desc":"另一个亚洲视频站点","icon":"play.rectangle.fill","url":"https://jable02.com/enter","lines":[{"url":"https://jable18.top/enter","testUrl":"https://jable18.top/status.html","ok":true,"ms":530.0},{"url":"https://jable1.cc/enter","testUrl":"https://jable1.cc/status.html","ok":true,"ms":596.0},{"url":"https://jable888.com/enter","testUrl":"https://jable888.com/status.html","ok":true,"ms":878.0},{"url":"https://jable1.com/enter","testUrl":"https://jable1.com/status.html","ok":true,"ms":973.0},{"url":"https://jable01.net/enter","testUrl":"https://jable01.net/status.html","ok":true,"ms":1187.0},{"url":"https://jable1.xyz/enter","testUrl":"https://jable1.xyz/status.html","ok":true,"ms":1204.0},{"url":"https://jable.cfd/enter","testUrl":"https://jable.cfd/status.html","ok":true,"ms":1255.0},{"url":"https://91jable.icu/enter","testUrl":"https://91jable.icu/status.html","ok":true,"ms":1326.0},{"url":"https://jable1.lat/enter","testUrl":"https://jable1.lat/status.html","ok":true,"ms":1430.0},{"url":"https://91jable.top/enter","testUrl":"https://91jable.top/status.html","ok":true,"ms":1498.0},{"url":"https://jable1.net/enter","testUrl":"https://jable1.net/status.html","ok":true,"ms":1536.0},{"url":"https://jable888.net/enter","testUrl":"https://jable888.net/status.html","ok":true,"ms":1756.0},{"url":"https://jable02.com/enter","testUrl":"https://jable02.com/status.html","ok":true,"ms":1808.0},{"url":"https://jable1.vip/enter","testUrl":"https://jable1.vip/status.html","ok":true,"ms":1861.0},{"url":"https://jable01.com/enter","testUrl":"https://jable01.com/status.html","ok":true,"ms":1863.0},{"url":"https://jable666.net/enter","testUrl":"https://jable666.net/status.html","ok":true,"ms":1940.0},{"url":"https://jable666.com/enter","testUrl":"https://jable666.com/status.html","ok":true,"ms":3694.0}],"classes":[]},{"key":"x99_f3faa727","name":"xhamster","kind":"video","adapter":"generic","desc":"著名视频站点","icon":"play.rectangle.fill","url":"https://zh.xhamster02.com/enter","lines":[{"url":"https://zh.xhamster1.nl/enter","testUrl":"https://zh.xhamster1.nl/status.html","ok":true,"ms":635.0},{"url":"https://zh.xhamster01.net/enter","testUrl":"https://zh.xhamster01.net/status.html","ok":true,"ms":689.0},{"url":"https://zh.xhamster1.icu/enter","testUrl":"https://zh.xhamster1.icu/status.html","ok":true,"ms":964.0},{"url":"https://zh.xv123.icu/enter","testUrl":"https://zh.xv123.icu/status.html","ok":true,"ms":1289.0},{"url":"https://zh.xhamster1.one/enter","testUrl":"https://zh.xhamster1.one/status.html","ok":true,"ms":1412.0},{"url":"https://zh.xhamster1.net/enter","testUrl":"https://zh.xhamster1.net/status.html","ok":true,"ms":1501.0},{"url":"https://zh.xv123.xyz/enter","testUrl":"https://zh.xv123.xyz/status.html","ok":true,"ms":1516.0},{"url":"https://zh.xhamster1.top/enter","testUrl":"https://zh.xhamster1.top/status.html","ok":true,"ms":1564.0},{"url":"https://zh.xhamster02.com/enter","testUrl":"https://zh.xhamster02.com/status.html","ok":true,"ms":1670.0},{"url":"https://zh.xhamster1.cc/enter","testUrl":"https://zh.xhamster1.cc/status.html","ok":true,"ms":1776.0},{"url":"https://zh.xhamster1.pw/enter","testUrl":"https://zh.xhamster1.pw/status.html","ok":true,"ms":1871.0},{"url":"https://zh.xhamster1.art/enter","testUrl":"https://zh.xhamster1.art/status.html","ok":true,"ms":2142.0},{"url":"https://zh.xhamster.ist/enter","testUrl":"https://zh.xhamster.ist/status.html","ok":true,"ms":2343.0},{"url":"https://zh.xhamster1.vip/enter","testUrl":"https://zh.xhamster1.vip/status.html","ok":true,"ms":2700.0},{"url":"https://zh.xv123.top/enter","testUrl":"https://zh.xv123.top/status.html","ok":true,"ms":2822.0}],"classes":[]},{"key":"x99_8be4dcd9","name":"肉视频","kind":"video","adapter":"missav","desc":"国产视频为主,AI短剧","icon":"play.rectangle.fill","url":"https://rou07.net/home","lines":[{"url":"https://rou168.com/home","testUrl":"https://rou168.com/status.html","ok":true,"ms":650.0},{"url":"https://rou06.cc/home","testUrl":"https://rou06.cc/status.html","ok":true,"ms":791.0},{"url":"https://rou01.cc/home","testUrl":"https://rou01.cc/status.html","ok":true,"ms":902.0},{"url":"https://rou07.net/home","testUrl":"https://rou07.net/status.html","ok":true,"ms":926.0},{"url":"https://rou1.pw/home","testUrl":"https://rou1.pw/status.html","ok":true,"ms":940.0},{"url":"https://rou1.men/home","testUrl":"https://rou1.men/status.html","ok":true,"ms":1109.0},{"url":"https://rou1.art/home","testUrl":"https://rou1.art/status.html","ok":true,"ms":1126.0},{"url":"https://rou08.net/home","testUrl":"https://rou08.net/status.html","ok":true,"ms":1180.0},{"url":"https://rou1.sbs/home","testUrl":"https://rou1.sbs/status.html","ok":true,"ms":1218.0},{"url":"https://rou08.com/home","testUrl":"https://rou08.com/status.html","ok":true,"ms":1254.0},{"url":"https://rou163.top/home","testUrl":"https://rou163.top/status.html","ok":true,"ms":1261.0},{"url":"https://rou06.net/home","testUrl":"https://rou06.net/status.html","ok":true,"ms":1482.0},{"url":"https://rou888.net/home","testUrl":"https://rou888.net/status.html","ok":true,"ms":1519.0},{"url":"https://rouav.sbs/home","testUrl":"https://rouav.sbs/status.html","ok":true,"ms":1649.0},{"url":"https://rouxxx.net/home","testUrl":"https://rouxxx.net/status.html","ok":true,"ms":1705.0},{"url":"https://rou666.net/home","testUrl":"https://rou666.net/status.html","ok":true,"ms":1748.0},{"url":"https://rou1.my/home","testUrl":"https://rou1.my/status.html","ok":true,"ms":2204.0},{"url":"https://rouxxx.sbs/home","testUrl":"https://rouxxx.sbs/status.html","ok":true,"ms":2306.0},{"url":"https://rou666.com/home","testUrl":"https://rou666.com/status.html","ok":true,"ms":3093.0},{"url":"https://rou07.com/home","testUrl":"https://rou07.com/status.html","ok":true,"ms":3389.0},{"url":"https://rouxxx.cc/home","testUrl":"https://rouxxx.cc/status.html","ok":false,"ms":1003.0}],"classes":[]},{"key":"x99_f642a3a3","name":"好色TV","kind":"video","adapter":"missav","desc":"国产中短精选视频","icon":"play.rectangle.fill","url":"https://hsex02.com/enter","lines":[{"url":"https://pb365.top/enter","testUrl":"https://pb365.top/status.html","ok":true,"ms":497.0},{"url":"https://hsex1.vip/enter","testUrl":"https://hsex1.vip/status.html","ok":true,"ms":625.0},{"url":"https://hsex1.top/enter","testUrl":"https://hsex1.top/status.html","ok":true,"ms":654.0},{"url":"https://hsex.sbs/enter","testUrl":"https://hsex.sbs/status.html","ok":true,"ms":708.0},{"url":"https://hsex.top/enter","testUrl":"https://hsex.top/status.html","ok":true,"ms":768.0},{"url":"https://hsex1.cc/enter","testUrl":"https://hsex1.cc/status.html","ok":true,"ms":817.0},{"url":"https://pb365.one/enter","testUrl":"https://pb365.one/status.html","ok":true,"ms":970.0},{"url":"https://hsex1.sbs/enter","testUrl":"https://hsex1.sbs/status.html","ok":true,"ms":1004.0},{"url":"https://hsex.nl/enter","testUrl":"https://hsex.nl/status.html","ok":true,"ms":1024.0},{"url":"https://hsex01.net/enter","testUrl":"https://hsex01.net/status.html","ok":true,"ms":1027.0},{"url":"https://hsex1.icu/enter","testUrl":"https://hsex1.icu/status.html","ok":true,"ms":1067.0},{"url":"https://pb365.sbs/enter","testUrl":"https://pb365.sbs/status.html","ok":true,"ms":1170.0},{"url":"https://hsex.one/enter","testUrl":"https://hsex.one/status.html","ok":true,"ms":1306.0},{"url":"https://hsex.cfd/enter","testUrl":"https://hsex.cfd/status.html","ok":true,"ms":1313.0},{"url":"https://hsex02.com/enter","testUrl":"https://hsex02.com/status.html","ok":true,"ms":1541.0},{"url":"https://hsex01.com/enter","testUrl":"https://hsex01.com/status.html","ok":true,"ms":3202.0},{"url":"https://pb365.nl/enter","testUrl":"https://pb365.nl/status.html","ok":false,"ms":987.0},{"url":"https://hsex.mom/enter","testUrl":"https://hsex.mom/status.html","ok":false,"ms":1955.0}],"classes":[]},{"key":"x99_99fa5c38","name":"321AV","kind":"video","adapter":"maccms","desc":"视频站点，速度更快","icon":"play.rectangle.fill","url":"https://321av.art/enter","lines":[{"url":"https://321av.ws/enter","testUrl":"https://321av.ws/status.html","ok":true,"ms":181.0},{"url":"https://321av.top/enter","testUrl":"https://321av.top/status.html","ok":true,"ms":676.0},{"url":"https://321xav.cc/enter","testUrl":"https://321xav.cc/status.html","ok":true,"ms":683.0},{"url":"https://321av.icu/enter","testUrl":"https://321av.icu/status.html","ok":true,"ms":694.0},{"url":"https://321av.sbs/enter","testUrl":"https://321av.sbs/status.html","ok":true,"ms":738.0},{"url":"https://321av.org/enter","testUrl":"https://321av.org/status.html","ok":true,"ms":754.0},{"url":"https://321av.men/enter","testUrl":"https://321av.men/status.html","ok":true,"ms":856.0},{"url":"https://321av.fans/enter","testUrl":"https://321av.fans/status.html","ok":true,"ms":951.0},{"url":"https://321av.art/enter","testUrl":"https://321av.art/status.html","ok":true,"ms":1081.0},{"url":"https://321av.xyz/enter","testUrl":"https://321av.xyz/status.html","ok":true,"ms":1091.0},{"url":"https://321av.vip/enter","testUrl":"https://321av.vip/status.html","ok":false,"ms":1010.0}],"classes":[{"type_id":"20","type_name":"有码影片","href":"/vodtype/20.html"},{"type_id":"21","type_name":"无码影片","href":"/vodtype/21.html"},{"type_id":"22","type_name":"中文字幕","href":"/vodtype/22.html"}]},{"key":"x99_5b25e3c1","name":"rouAV","kind":"video","adapter":"maccms","desc":"高品质国产AV","icon":"play.rectangle.fill","url":"https://rou123.ws/enter","lines":[{"url":"https://rou123.org/enter","testUrl":"https://rou123.org/status.html","ok":true,"ms":623.0},{"url":"https://rou123.one/enter","testUrl":"https://rou123.one/status.html","ok":true,"ms":642.0},{"url":"https://rou123.ws/enter","testUrl":"https://rou123.ws/status.html","ok":true,"ms":680.0},{"url":"https://rou123.cc/enter","testUrl":"https://rou123.cc/status.html","ok":true,"ms":988.0},{"url":"https://rou123.cfd/enter","testUrl":"https://rou123.cfd/status.html","ok":true,"ms":1226.0},{"url":"https://rou123.sbs/enter","testUrl":"https://rou123.sbs/status.html","ok":true,"ms":1333.0},{"url":"https://rou123.vip/enter","testUrl":"https://rou123.vip/status.html","ok":false,"ms":849.0},{"url":"https://rou123.top/enter","testUrl":"https://rou123.top/status.html","ok":false,"ms":1050.0}],"classes":[{"type_id":"7","type_name":"国产AV","href":"/vodtype/7.html"},{"type_id":"3","type_name":"日本","href":"/vodtype/3.html"},{"type_id":"6","type_name":"自拍流出","href":"/vodtype/6.html"},{"type_id":"5","type_name":"探花","href":"/vodtype/5.html"},{"type_id":"4","type_name":"OnlyFans","href":"/vodtype/4.html"},{"type_id":"1","type_name":"其他","href":"/vodtype/1.html"}]},{"key":"x99_d7f940f5","name":"黄色仓库","kind":"video","adapter":"maccms","desc":"最新麻豆视频,麻豆视频在线观看,天美传媒,91制片厂,天美传媒,精东影业,蜜桃传媒,麻豆网","icon":"play.rectangle.fill","url":"https://www.hsck01.net/enter","lines":[{"url":"https://www.hsck01.net/enter","testUrl":"https://www.hsck01.net/status.html","ok":true,"ms":166.0},{"url":"https://www.69ck1.com/enter","testUrl":"https://www.69ck1.com/status.html","ok":true,"ms":781.0},{"url":"https://www.hsck.nl/enter","testUrl":"https://www.hsck.nl/status.html","ok":true,"ms":798.0},{"url":"https://www.hsck.sbs/enter","testUrl":"https://www.hsck.sbs/status.html","ok":true,"ms":1005.0},{"url":"https://www.69ck1.net/enter","testUrl":"https://www.69ck1.net/status.html","ok":true,"ms":1017.0},{"url":"https://www.69ck.one/enter","testUrl":"https://www.69ck.one/status.html","ok":true,"ms":1206.0},{"url":"https://www.69ck.ws/enter","testUrl":"https://www.69ck.ws/status.html","ok":true,"ms":1786.0}],"classes":[{"type_id":"1","type_name":"麻豆","href":"/index.php/vod/type/id/1.html"},{"type_id":"2","type_name":"中字","href":"/index.php/vod/type/id/2.html"},{"type_id":"3","type_name":"国产","href":"/index.php/vod/type/id/3.html"},{"type_id":"4","type_name":"欧美","href":"/index.php/vod/type/id/4.html"},{"type_id":"5","type_name":"日韩","href":"/index.php/vod/type/id/5.html"}]},{"key":"x99_2eb3f212","name":"18av","kind":"video","adapter":"18av","desc":"综合性成人站点，包含视频、小说、色图、漫画等","icon":"play.rectangle.fill","url":"https://www.18av02.com/enter","lines":[{"url":"https://www.18av.nl/enter","testUrl":"https://www.18av.nl/status.html","ok":true,"ms":546.0},{"url":"https://www.18av01.cc/enter","testUrl":"https://www.18av01.cc/status.html","ok":true,"ms":699.0},{"url":"https://www.18av.pw/enter","testUrl":"https://www.18av.pw/status.html","ok":true,"ms":890.0},{"url":"https://www.18av01.net/enter","testUrl":"https://www.18av01.net/status.html","ok":true,"ms":1078.0},{"url":"https://www.18av.ws/enter","testUrl":"https://www.18av.ws/status.html","ok":true,"ms":2166.0},{"url":"https://www.18av02.com/enter","testUrl":"https://www.18av02.com/status.html","ok":true,"ms":2477.0}],"classes":[{"type_id":"chinese_list","type_name":"中文字幕"},{"type_id":"censored_list","type_name":"有碼AV"},{"type_id":"uncensored_list","type_name":"無碼AV"},{"type_id":"amateurjav_list","type_name":"素人AV"},{"type_id":"reducing-mosaic_list","type_name":"無碼破解"},{"type_id":"animation_list","type_name":"H動畫"},{"type_id":"dt_list","type_name":"國產自拍"}]},{"key":"x99_f7ba81a6","name":"大哥视频","kind":"video","adapter":"generic","desc":"最新各类国产、日韩、欧美等视频","icon":"play.rectangle.fill","url":"https://dage.one/enter","lines":[{"url":"https://dage.one/enter","testUrl":"https://dage.one/status.html","ok":true,"ms":627.0},{"url":"https://dage01.net/enter","testUrl":"https://dage01.net/status.html","ok":true,"ms":2694.0}],"classes":[]},{"key":"x99_a4235f12","name":"Pornhub","kind":"video","adapter":"generic","desc":"P站","icon":"play.rectangle.fill","url":"https://cn.pornhub06.com/enter","lines":[{"url":"https://cn.pornhub365.com/enter","testUrl":"https://cn.pornhub365.com/status.html","ok":true,"ms":541.0},{"url":"https://cn.pornhub666.com/enter","testUrl":"https://cn.pornhub666.com/status.html","ok":true,"ms":715.0},{"url":"https://cn.pornhub06.com/enter","testUrl":"https://cn.pornhub06.com/status.html","ok":true,"ms":804.0},{"url":"https://cn.pornhub02.com/enter","testUrl":"https://cn.pornhub02.com/status.html","ok":true,"ms":895.0},{"url":"https://cn.pornhub03.net/enter","testUrl":"https://cn.pornhub03.net/status.html","ok":true,"ms":1017.0},{"url":"https://cn.pornhub02.net/enter","testUrl":"https://cn.pornhub02.net/status.html","ok":true,"ms":1066.0},{"url":"https://cn.pornhub365.sbs/enter","testUrl":"https://cn.pornhub365.sbs/status.html","ok":true,"ms":1098.0},{"url":"https://cn.pornhub1.icu/enter","testUrl":"https://cn.pornhub1.icu/status.html","ok":true,"ms":1194.0},{"url":"https://cn.pornhub666.cc/enter","testUrl":"https://cn.pornhub666.cc/status.html","ok":true,"ms":1284.0},{"url":"https://cn.pornhub163.com/enter","testUrl":"https://cn.pornhub163.com/status.html","ok":true,"ms":1502.0},{"url":"https://cn.pornhub03.com/enter","testUrl":"https://cn.pornhub03.com/status.html","ok":true,"ms":1767.0},{"url":"https://cn.pornhub163.net/enter","testUrl":"https://cn.pornhub163.net/status.html","ok":true,"ms":3740.0},{"url":"https://cn.pornhub365.top/enter","testUrl":"https://cn.pornhub365.top/status.html","ok":false,"ms":1370.0},{"url":"https://cn.pornhub1.cc/enter","testUrl":"https://cn.pornhub1.cc/status.html","ok":false,"ms":1382.0},{"url":"https://cn.pornhub365.mom/enter","testUrl":"https://cn.pornhub365.mom/status.html","ok":false,"ms":1484.0},{"url":"https://cn.pornhub1.mom/enter","testUrl":"https://cn.pornhub1.mom/status.html","ok":false,"ms":2273.0}],"classes":[]},{"key":"x99_63401799","name":"XVIDEOS","kind":"video","adapter":"generic","desc":"X站","icon":"play.rectangle.fill","url":"https://www.xvideos163.top/enter","lines":[{"url":"https://www.91xvideos.top/enter","testUrl":"https://www.91xvideos.top/status.html","ok":true,"ms":870.0},{"url":"https://www.xvideos1.icu/enter","testUrl":"https://www.xvideos1.icu/status.html","ok":true,"ms":1836.0},{"url":"https://www.x123.xyz/enter","testUrl":"https://www.x123.xyz/status.html","ok":false,"ms":1334.0},{"url":"https://www.x123.one/enter","testUrl":"https://www.x123.one/status.html","ok":false,"ms":1647.0},{"url":"https://www.xvideos163.top/enter","testUrl":"https://www.xvideos163.top/status.html","ok":false,"ms":24587.0}],"classes":[]},{"key":"x99_a4cb289c","name":"Xanimu","kind":"video","adapter":"missav","desc":"免费2D、3D、动漫性爱、漫画、卡通","icon":"play.rectangle.fill","url":"https://xanimu.ws/zh-CN/","lines":[{"url":"https://xanimu.one/zh-CN/","testUrl":"https://xanimu.one/status.html","ok":true,"ms":695.0},{"url":"https://xanimu.net/zh-CN/","testUrl":"https://xanimu.net/status.html","ok":true,"ms":793.0},{"url":"https://xanimu.art/zh-CN/","testUrl":"https://xanimu.art/status.html","ok":true,"ms":800.0},{"url":"https://xanimu.ws/zh-CN/","testUrl":"https://xanimu.ws/status.html","ok":true,"ms":1087.0},{"url":"https://xanimu.sbs/zh-CN/","testUrl":"https://xanimu.sbs/status.html","ok":true,"ms":1420.0},{"url":"https://xanimu.top/zh-CN/","testUrl":"https://xanimu.top/status.html","ok":true,"ms":1905.0}],"classes":[]},{"key":"x99_becefbcf","name":"avjoy","kind":"video","adapter":"missav","desc":"成人视频","icon":"play.rectangle.fill","url":"https://cn.avjoy.ws/enter","lines":[{"url":"https://cn.avjoy.ws/enter","testUrl":"https://cn.avjoy.ws/status.html","ok":true,"ms":171.0},{"url":"https://cn.avjoy.nl/enter","testUrl":"https://cn.avjoy.nl/status.html","ok":true,"ms":594.0},{"url":"https://cn.avjoy.top/enter","testUrl":"https://cn.avjoy.top/status.html","ok":true,"ms":2554.0}],"classes":[]},{"key":"x99_aa4a47f1","name":"SuperPorn","kind":"video","adapter":"missav","desc":"高质量海外视频","icon":"play.rectangle.fill","url":"https://cn.superporn.ws/enter","lines":[{"url":"https://cn.superporn.icu/enter","testUrl":"https://cn.superporn.icu/status.html","ok":false,"ms":1166.0},{"url":"https://cn.superporn.ws/enter","testUrl":"https://cn.superporn.ws/status.html","ok":false,"ms":1664.0},{"url":"https://cn.superporn.me/enter","testUrl":"https://cn.superporn.me/status.html","ok":false,"ms":1849.0}],"classes":[]},{"key":"x99_73234a95","name":"亚洲素人精选","kind":"video","adapter":"missav","desc":"亚洲素人精选AV","icon":"play.rectangle.fill","url":"https://591av.ws/enter","lines":[{"url":"https://591av.ws/enter","testUrl":"https://591av.ws/status.html","ok":true,"ms":461.0},{"url":"https://91-av.one/enter","testUrl":"https://91-av.one/status.html","ok":true,"ms":485.0},{"url":"https://91-av.men/enter","testUrl":"https://91-av.men/status.html","ok":true,"ms":960.0},{"url":"https://591av.net/enter","testUrl":"https://591av.net/status.html","ok":true,"ms":1291.0},{"url":"https://591av.sbs/enter","testUrl":"https://591av.sbs/status.html","ok":true,"ms":2221.0}],"classes":[]},{"key":"x99_52cd8432","name":"YesPorn","kind":"video","adapter":"missav","desc":"很多收费完整视频(免费)","icon":"play.rectangle.fill","url":"https://cn.yesporn.ws/enter","lines":[{"url":"https://cn.yesporn.ws/enter","testUrl":"https://cn.yesporn.ws/status.html","ok":true,"ms":303.0},{"url":"https://cn.yesporn1.cc/enter","testUrl":"https://cn.yesporn1.cc/status.html","ok":true,"ms":1233.0}],"classes":[]},{"key":"x99_e85133d7","name":"CartoonPorno","kind":"video","adapter":"missav","desc":"免费精品动漫卡通视频","icon":"play.rectangle.fill","url":"https://www.cartoonporno.vip/?hl=zh","lines":[{"url":"https://www.cartoonporno.vip/?hl=zh","testUrl":"https://www.cartoonporno.vip/status.html","ok":true,"ms":478.0},{"url":"https://www.cartoonporno.cc/?hl=zh","testUrl":"https://www.cartoonporno.cc/status.html","ok":true,"ms":882.0},{"url":"https://www.cartoonporno.top/?hl=zh","testUrl":"https://www.cartoonporno.top/status.html","ok":true,"ms":1300.0},{"url":"https://www.cartoonporno.ws/?hl=zh","testUrl":"https://www.cartoonporno.ws/status.html","ok":true,"ms":1357.0},{"url":"https://www.cartoonporno.art/?hl=zh","testUrl":"https://www.cartoonporno.art/status.html","ok":false,"ms":966.0}],"classes":[]},{"key":"x99_9364c1e5","name":"Hentai","kind":"video","adapter":"generic","desc":"提供 漫画、同人志、艺术图集、游戏CG、小说插图 等","icon":"play.rectangle.fill","url":"https://cn.acgmh.art/enter","lines":[{"url":"https://cn.acgmh.art/enter","testUrl":"https://cn.acgmh.art/status.html","ok":true,"ms":763.0},{"url":"https://cn.acgmh.top/enter","testUrl":"https://cn.acgmh.top/status.html","ok":true,"ms":820.0},{"url":"https://cn.acgmh.sbs/enter","testUrl":"https://cn.acgmh.sbs/status.html","ok":true,"ms":1079.0},{"url":"https://cn.bato.icu/enter","testUrl":"https://cn.bato.icu/status.html","ok":true,"ms":1164.0},{"url":"https://cn.acgmh.icu/enter","testUrl":"https://cn.acgmh.icu/status.html","ok":true,"ms":1249.0},{"url":"https://cn.acgmh.vip/enter","testUrl":"https://cn.acgmh.vip/status.html","ok":true,"ms":1574.0}],"classes":[]},{"key":"x99_e8d1404a","name":"OKXXX","kind":"video","adapter":"generic","desc":"OKXXX","icon":"play.rectangle.fill","url":"https://okav.art/enter","lines":[{"url":"https://okav.art/enter","testUrl":"https://okav.art/status.html","ok":true,"ms":431.0},{"url":"https://okxxx.icu/enter","testUrl":"https://okxxx.icu/status.html","ok":true,"ms":1200.0},{"url":"https://okxxxx.net/enter","testUrl":"https://okxxxx.net/status.html","ok":true,"ms":1270.0},{"url":"https://okx18.icu/enter","testUrl":"https://okx18.icu/status.html","ok":true,"ms":1490.0},{"url":"https://okx18.cc/enter","testUrl":"https://okx18.cc/status.html","ok":true,"ms":1792.0},{"url":"https://okxxx.ws/enter","testUrl":"https://okxxx.ws/status.html","ok":true,"ms":2365.0},{"url":"https://okx18.vip/enter","testUrl":"https://okx18.vip/status.html","ok":true,"ms":2369.0},{"url":"https://okxxx.win/enter","testUrl":"https://okxxx.win/status.html","ok":true,"ms":2571.0},{"url":"https://okxxx.men/enter","testUrl":"https://okxxx.men/status.html","ok":true,"ms":2926.0},{"url":"https://okxxx.one/enter","testUrl":"https://okxxx.one/status.html","ok":true,"ms":2969.0}],"classes":[]},{"key":"x99_86c9c1d3","name":"VJAV","kind":"video","adapter":"generic","desc":"VJAV","icon":"play.rectangle.fill","url":"https://vjav1.sbs/enter","lines":[{"url":"https://vjav-com.top/enter","testUrl":"https://vjav-com.top/status.html","ok":true,"ms":581.0},{"url":"https://vjav.icu/enter","testUrl":"https://vjav.icu/status.html","ok":true,"ms":848.0},{"url":"https://vjav1.sbs/enter","testUrl":"https://vjav1.sbs/status.html","ok":true,"ms":1591.0},{"url":"https://vjav-com.icu/enter","testUrl":"https://vjav-com.icu/status.html","ok":true,"ms":1828.0},{"url":"https://vjav1.top/enter","testUrl":"https://vjav1.top/status.html","ok":true,"ms":2013.0}],"classes":[]},{"key":"x99_30b320d4","name":"成人影片数据库","kind":"video","adapter":"generic","desc":"不错的下片站点，巨多高清无广告资源，完全免费，下片爱好者进","icon":"play.rectangle.fill","url":"https://javdb02.com/?locale=zh","lines":[{"url":"https://javdb1.top/?locale=zh","testUrl":"https://javdb1.top/status.html","ok":true,"ms":634.0},{"url":"https://javdb02.com/?locale=zh","testUrl":"https://javdb02.com/status.html","ok":true,"ms":661.0},{"url":"https://javdb.nl/?locale=zh","testUrl":"https://javdb.nl/status.html","ok":true,"ms":936.0},{"url":"https://javdb1.art/?locale=zh","testUrl":"https://javdb1.art/status.html","ok":true,"ms":1016.0},{"url":"https://javdb01.net/?locale=zh","testUrl":"https://javdb01.net/status.html","ok":true,"ms":1269.0},{"url":"https://javdb.sbs/?locale=zh","testUrl":"https://javdb.sbs/status.html","ok":true,"ms":1328.0},{"url":"https://javdb1.sbs/?locale=zh","testUrl":"https://javdb1.sbs/status.html","ok":true,"ms":1386.0},{"url":"https://javdb.pw/?locale=zh","testUrl":"https://javdb.pw/status.html","ok":true,"ms":1987.0},{"url":"https://javdb.icu/?locale=zh","testUrl":"https://javdb.icu/status.html","ok":true,"ms":2691.0}],"classes":[]},{"key":"x99_a5b6d0eb","name":"三级片资源，稀缺资源","kind":"video","adapter":"generic","desc":"最新最热门的电影电视剧动漫综艺台湾剧大陆剧日剧韩剧美剧，完全免费","icon":"play.rectangle.fill","url":"https://ptt03.net/p/1","lines":[{"url":"https://ptt2.one/p/1","testUrl":"https://ptt2.one/status.html","ok":true,"ms":820.0},{"url":"https://ptt01.com/p/1","testUrl":"https://ptt01.com/status.html","ok":true,"ms":849.0},{"url":"https://ptt02.com/p/1","testUrl":"https://ptt02.com/status.html","ok":true,"ms":940.0},{"url":"https://ptt02.net/p/1","testUrl":"https://ptt02.net/status.html","ok":true,"ms":944.0},{"url":"https://ptt03.com/p/1","testUrl":"https://ptt03.com/status.html","ok":true,"ms":976.0},{"url":"https://ptt2.nl/p/1","testUrl":"https://ptt2.nl/status.html","ok":true,"ms":998.0},{"url":"https://ptt2.my/p/1","testUrl":"https://ptt2.my/status.html","ok":true,"ms":1008.0},{"url":"https://ptt02.nl/p/1","testUrl":"https://ptt02.nl/status.html","ok":true,"ms":1098.0},{"url":"https://ptt02.cc/p/1","testUrl":"https://ptt02.cc/status.html","ok":true,"ms":1349.0},{"url":"https://ptt01.ws/p/1","testUrl":"https://ptt01.ws/status.html","ok":true,"ms":1567.0},{"url":"https://ptt2.art/p/1","testUrl":"https://ptt2.art/status.html","ok":true,"ms":1594.0},{"url":"https://ptt03.net/p/1","testUrl":"https://ptt03.net/status.html","ok":true,"ms":2019.0},{"url":"https://ptt2.top/p/1","testUrl":"https://ptt2.top/status.html","ok":true,"ms":2157.0}],"classes":[]}]}')

# ---- 运行参数（方案 v8 定稿）----
CACHE_TTL = 600          # 线路/入口胜者缓存
DEAD_COOLDOWN = 1800     # 死亡线路冷却
BATCH = 3                # 每批并发探测条数
PROBE_TIMEOUT = 3        # 单条探测超时
PROBE_BUDGET = 6         # 单平台探测总预算
HTTP_TIMEOUT = 7         # 业务请求超时（App 单次调用上限 20s，探测预算 12s + 本值需留余量）
NAV_TTL = 21600          # 快照刷新

UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36")

_SSL = ssl.create_default_context()
_SSL.check_hostname = False
_SSL.verify_mode = ssl.CERT_NONE


def _http(url, timeout=HTTP_TIMEOUT, headers=None):
    """返回 (status, text)。4xx/5xx 也读 body —— 这些站常 500 但页面完整。"""
    hdrs = {
        "User-Agent": UA,
        "Accept": "text/html,application/xhtml+xml,*/*;q=0.8",
        "Accept-Language": "zh-CN,zh;q=0.9",
        "Cache-Control": "no-cache",
    }
    if headers:
        hdrs.update(headers)
    request = urllib.request.Request(url, headers=hdrs)
    try:
        with urllib.request.urlopen(request, timeout=timeout, context=_SSL) as response:
            return response.status, response.read().decode("utf-8", errors="replace")
    except urllib.error.HTTPError as exc:
        body = exc.read() if exc.fp else b""
        return exc.code, body.decode("utf-8", errors="replace")
    except Exception:
        return None, ""


class _Response(object):
    """给宿主/脚本使用的轻量响应对象（requests 兼容的最小子集）。"""

    def __init__(self, status, text):
        self.status_code = status or 0
        self.text = text or ""
        self.content = self.text.encode("utf-8")
        self.headers = {}

    @property
    def ok(self):
        return 200 <= self.status_code < 400

    def json(self):
        return json.loads(self.text)


def _decode_payload(encoded):
    return urllib.parse.unquote(base64.b64decode(encoded).decode("utf-8"))


def _parse_snapshot(html):
    match = re.search(r"const\s+encodedData\s*=\s*(['\"])(.*?)\1\s*;", html, re.S)
    if not match:
        return None
    return json.loads(_decode_payload(match.group(2)))


class _LinePicker(object):
    """线路优选：600s 缓存 + 3 条一批接力 + 死亡冷却。"""

    def __init__(self, spider):
        self.s = spider

    def remember(self, platform, host):
        if host:
            self.s.cache_set("x99dh:line:" + platform["key"], {"host": host, "ts": time.time()})

    def pick(self, platform):
        key = "x99dh:line:" + platform["key"]
        hit = self.s.cache_get(key)
        if hit and time.time() - hit.get("ts", 0) < CACHE_TTL:
            return hit["host"]

        dead = self.s.cache_get("x99dh:dead:" + platform["key"]) or {}
        now = time.time()
        candidates = [
            line["url"] for line in platform.get("lines") or []
            if line.get("url") and now - dead.get(line["url"], 0) > DEAD_COOLDOWN
        ]
        if not candidates:
            candidates = [line["url"] for line in platform.get("lines") or [] if line.get("url")]

        started = time.time()
        for index in range(0, len(candidates), BATCH):
            winner = self._race(candidates[index:index + BATCH])
            if winner:
                self.s.cache_set(key, {"host": winner, "ts": time.time()})
                return winner
            if time.time() - started > PROBE_BUDGET:
                break

        return (hit or {}).get("host") or (candidates[0] if candidates else "")

    def _race(self, batch):
        """批内并发，第一个 ok 者胜出。"""
        done = threading.Event()
        winner = {}

        def probe(url):
            test_url = self.s.test_url(url)
            if not test_url:
                return
            sep = "&" if "?" in test_url else "?"
            status, text = _http(test_url + sep + "ts=" + str(int(time.time() * 1000)),
                                 timeout=PROBE_TIMEOUT)
            if status == 200 and (text or "").strip().lower().startswith("ok"):
                if not winner:
                    winner["host"] = url
                done.set()

        threads = [threading.Thread(target=probe, args=(url,)) for url in batch]
        for thread in threads:
            thread.daemon = True
            thread.start()
        done.wait(PROBE_TIMEOUT + 0.5)
        return winner.get("host", "")

    def mark_dead(self, platform, host):
        key = "x99dh:dead:" + platform["key"]
        dead = self.s.cache_get(key) or {}
        dead[host] = time.time()
        self.s.cache_set(key, dead)


class _BaseAdapter(object):
    """适配器基类：P0 只做骨架，P1 起逐个实现。"""

    def __init__(self, spider, platform, host):
        self.s = spider
        self.p = platform
        self.line = host
        # 线路地址可能带路径（/enter、/cn/…），站点根只取 scheme://netloc
        parts = urllib.parse.urlsplit(host or "")
        self.host = (parts.scheme + "://" + parts.netloc) if parts.scheme else (host or "")

    def _url(self, path):
        if path.startswith("http"):
            return path
        return self.host.rstrip("/") + "/" + path.lstrip("/")

    def _abs(self, url):
        """相对地址绝对化（图片、详情链接）。"""
        if not url:
            return ""
        if url.startswith("http"):
            return url
        return urllib.parse.urljoin(self.host.rstrip("/") + "/", url.lstrip("/"))

    def categories(self):
        return self.p.get("classes") or []

    def list(self, cate, page):
        return {"list": [], "page": int(page), "pagecount": int(page) + 1}

    def detail(self, vod_id):
        return {"list": []}

    def play(self, flag, url):
        return {"parse": "0", "url": ""}


class _MaccmsAdapter(_BaseAdapter):
    """苹果CMS：列表 / 详情 / player_aaaa 解直链。

    覆盖三种路径风格：
      /vodtype/{id}.html               → 分页 /vodtype/{id}-{page}.html
      /index.php/vod/type/id/{id}.html → 分页 .../page/{page}.html
    卡片链接统一按 /vodplay/、/vod/detail/、/vod/detail/id/ 提取。
    """

    CARD_RE = re.compile(
        r'<a[^>]+href="(?P<href>[^"]*(?:/vodplay/|/voddetail/|/vod/detail/|/vod/play/)[^"]*)"'
        r'(?P<attrs>[^>]*)>(?P<inner>.*?)</a>',
        re.S,
    )
    TITLE_RE = re.compile(r'class="[^"]*(?:title|name)[^"]*"[^>]*>(.*?)<', re.S)
    IMG_RE = re.compile(r'(?:data-original|data-src|src)="([^"]+)"')

    def _scan_class(self, cate):
        """运行时抓 /enter 页的分类链接，补上快照里没有的分类（24h 缓存）。"""
        key = "x99dh:classes:" + self.p["key"]
        cached = self.s.cache_get(key)
        if not (cached and time.time() - cached.get("ts", 0) < 86400):
            html = self.s.http(self._url("/enter")) or ""
            found = {}
            for href, label in re.findall(
                r'<a[^>]+href="([^"]*?(?:/vodtype/\d+|/index\.php/vod/type/id/\d+)[^"]*)"[^>]*>(.*?)</a>',
                html, re.S):
                match = re.search(r"(?:vodtype|vod/type/id)/(\d+)", href)
                text = re.sub(r"<[^>]+>", "", label).strip()
                if match and text and len(text) < 14:
                    found.setdefault(match.group(1), {"href": href, "name": text})
            cached = {"map": found, "ts": time.time()}
            if found:
                self.s.cache_set(key, cached)
        return ((cached or {}).get("map") or {}).get(str(cate), {}).get("href", "")

    def _list_url(self, cate, page):
        href = ""
        for item in self.p.get("classes") or []:
            if item.get("type_id") == cate:
                href = item.get("href") or ""
                break
        if not href:
            href = self._scan_class(cate) or ("/vodtype/%s.html" % cate)
        base = href.rsplit(".html", 1)[0]
        if "/page/" in href or "/index.php" in href:
            return self._url(base + "/page/%d.html" % int(page))
        if int(page) > 1:
            return self._url(base + "-%d.html" % int(page))
        return self._url(href)

    def list(self, cate, page):
        html = self.s.http(self._list_url(cate, page))
        if not html:
            return {"list": [], "page": int(page), "pagecount": int(page) + 1}

        videos = []
        seen = set()
        for match in self.CARD_RE.finditer(html):
            href = match.group("href")
            if href in seen:
                continue
            seen.add(href)
            inner = match.group("inner")
            title = ""
            attr = re.search(r'title="([^"]+)"', match.group("attrs") or "")
            if attr:
                title = attr.group(1).strip()
            if not title:
                found = self.TITLE_RE.search(inner)
                if found:
                    title = re.sub(r"<[^>]+>", "", found.group(1)).strip()
            if not title:
                alt = re.search(r'alt="([^"]+)"', inner)
                if alt:
                    title = alt.group(1).strip()
            if not title:
                tail = html[match.end(): match.end() + 600]
                like = re.search(r'class="[^"]*(?:title|name)[^"]*"[^>]*>(.*?)<', tail, re.S)
                if like:
                    title = re.sub(r"<[^>]+>", "", like.group(1)).strip()
            if not title:
                like = re.search(r"<(?:h2|h3|h4|p)[^>]*>(.*?)</", tail if 'tail' in dir() else "", re.S)
                if like:
                    title = re.sub(r"<[^>]+>", "", like.group(1)).strip()
            if not title:
                title = re.sub(r"<[^>]+>", " ", inner)
                title = re.sub(r"\s+", " ", title).strip()[:40]
            if not title:
                digits = re.sub(r"\D", "", href)
                title = ("视频 " + digits[-6:]) if digits else href
            if not title:
                continue
            img = ""
            found = self.IMG_RE.search(inner)
            if found:
                img = found.group(1)
            videos.append({
                "vod_id": self.p["key"] + "::" + href,
                "vod_name": title,
                "vod_pic": self._abs(img),
                "vod_remarks": "",
            })
        return {"list": videos, "page": int(page), "pagecount": int(page) + 1}

    def detail(self, vid):
        url = self._abs(vid)
        html = self.s.http(url)
        if not html:
            return {"list": []}

        title = ""
        found = re.search(r"<title[^>]*>(.*?)</title>", html, re.S)
        if found:
            title = re.sub(r"\s+", " ", found.group(1)).strip()
        name = re.search(r'property="og:title"\s+content="([^"]+)"', html)
        if name:
            title = name.group(1).strip()

        cover = ""
        found = re.search(r'property="og:image"\s+content="([^"]+)"', html)
        if found:
            cover = found.group(1)

        direct = self._resolve(html, url)
        vod = {
            "vod_id": self.p["key"] + "::" + vid,
            "vod_name": title or vid,
            "vod_pic": self._abs(cover),
            "vod_content": "",
            "vod_play_from": "直连",
            "vod_play_url": "正片$" + self.p["key"] + "::" + direct,
        }
        return {"list": [vod]}

    def play(self, flag, url):
        return {"parse": "0", "url": url, "header": self.s.headers()}

    # ---- 播放地址解析 ----
    def _resolve(self, html, page_url):
        candidates = []

        raw = self._balanced(html, "player_aaaa")
        if raw:
            try:
                data = json.loads(raw)
            except Exception:
                data = {}
            value = str(data.get("url") or "")
            enc = data.get("encrypt", 0)
            if enc == 1:
                value = urllib.parse.unquote(value)
            elif enc == 2:
                try:
                    value = urllib.parse.unquote(base64.b64decode(value).decode("utf-8"))
                except Exception:
                    pass
            path = self._from_ss(value)
            if path:
                # 321AV 这类 xplayer：/cn/{slug} -> /private-getvideo/{slug} 返回 playlist
                if path.startswith("/cn/"):
                    slug = path.rstrip("/").rsplit("/", 1)[-1]
                    body = self.s.http(self._url("/private-getvideo/" + slug))
                    try:
                        playlist = json.loads(body).get("playlist") or []
                    except Exception:
                        playlist = []
                    for entry in playlist:
                        link = str((entry or {}).get("url") or "")
                        if link.startswith("http"):
                            return link
                candidates.append(path)

        found = re.search(r"video_url=([^&\"']+)", html)
        if found:
            candidates.append(urllib.parse.unquote(found.group(1)))

        for item in candidates:
            direct = self._resolve_candidate(item, page_url)
            if direct:
                return direct

        # 只认 m3u8 / hls；页面里常有 thumbnail/preview.mp4 悬停预览片，不能当正片
        for regex in (r"https?://[^\s\"'<>]+\.m3u8[^\s\"'<>]*",
                      r"https?://[^\s\"'<>]+/hls/[^\s\"'<>]+"):
            for found in re.finditer(regex, html):
                url = found.group(0)
                if "preview" in url or "thumbnail" in url:
                    continue
                return url
        return ""

    @staticmethod
    def _from_ss(value):
        """player_aaaa 的 url 可能是一层 base64 的 {"ss":[[n,"/path"]]}。"""
        text = value.strip()
        if text.startswith("{"):
            try:
                data = json.loads(text)
                return (data.get("ss") or [[0, ""]])[0][1]
            except Exception:
                return ""
        if re.fullmatch(r"[A-Za-z0-9+/=]+", text) and len(text) > 16:
            try:
                decoded = base64.b64decode(text).decode("utf-8")
                if decoded.startswith("{"):
                    data = json.loads(decoded)
                    return (data.get("ss") or [[0, ""]])[0][1]
            except Exception:
                return ""
        return ""

    def _resolve_candidate(self, item, page_url):
        if not item:
            return ""
        if item.startswith("http"):
            return item
        if item.endswith(".m3u8") or item.endswith(".mp4"):
            return self._abs(item)

        target = self._abs(item)
        body = self.s.http(target)
        if not body:
            return ""
        for regex in (r"https?://[^\s\"'<>]+\.m3u8[^\s\"'<>]*",
                      r"https?://[^\s\"'<>]+\.mp4[^\s\"'<>]*",
                      r"https?://[^\s\"'<>]+/hls/[^\s\"'<>]+"):
            found = re.search(regex, body)
            if found:
                return found.group(0)
        try:
            data = json.loads(body)
            for key in ("url", "play_url", "video_url", "src"):
                value = data.get(key) if isinstance(data, dict) else None
                if isinstance(value, str) and value.startswith("http"):
                    return value
        except Exception:
            pass
        return ""

    @staticmethod
    def _balanced(html, anchor):
        start = html.find(anchor)
        if start < 0:
            return ""
        start = html.find("{", start)
        if start < 0:
            return ""
        depth = 0
        in_str = False
        escaped = False
        for index in range(start, len(html)):
            char = html[index]
            if in_str:
                if escaped:
                    escaped = False
                elif char == "\\":
                    escaped = True
                elif char == '"':
                    in_str = False
                continue
            if char == '"':
                in_str = True
            elif char == "{":
                depth += 1
            elif char == "}":
                depth -= 1
                if depth == 0:
                    return html[start:index + 1]
        return ""


class _MissavAdapter(_BaseAdapter):
    """MissAV 模板：/dm{id}/cn/{slug} 列表 + /private-test/{slug}/play 播放。"""

    CAT_RE = re.compile(r'href="[^"]*/(dm\d+/cn/[a-z0-9\-]+)"')
    CARD_RE = re.compile(
        r'<a[^>]+href="([^"]*/cn/[a-z0-9\-]+)"[^>]*alt="([^"]*)"', re.S)
    TITLE_RE = re.compile(r'class="text-secondary[^"]*"[^>]*>(.*?)</a>', re.S)

    def _cdn(self, html):
        found = re.search(r'cdnUrl\(path\)\s*\{\s*return\s*`([^`$]+)', html)
        return found.group(1).rstrip("/") if found else ""

    def _categories(self):
        key = "x99dh:missav:cats:" + self.host
        hit = self.s.cache_get(key)
        if hit and time.time() - hit.get("ts", 0) < 86400:
            return hit["cats"]
        html = self.s.http(self._url("/cn/"))
        cats, seen = [], set()
        for path in self.CAT_RE.findall(html or ""):
            if path in seen:
                continue
            seen.add(path)
            cats.append({"type_id": path, "type_name": path.split("/cn/")[-1]})
        if cats:
            self.s.cache_set(key, {"cats": cats, "ts": time.time()})
        return cats

    def categories(self):
        return self._categories() or self.p.get("classes") or []

    def _resolve_cate(self, cate):
        cats = self._categories()
        for item in cats:
            if item["type_id"] == cate:
                return cate
        return cats[0]["type_id"] if cats else ""

    def list(self, cate, page):
        path = self._resolve_cate(cate)
        if not path:
            return {"list": [], "page": int(page), "pagecount": int(page) + 1}
        url = self._url("/" + path)
        if int(page) > 1:
            url += "?page=%d" % int(page)
        html = self.s.http(url)
        cdn = self._cdn(html or "")
        videos, seen = [], set()
        for href, slug in self.CARD_RE.findall(html or ""):
            if slug in seen:
                continue
            seen.add(slug)
            title = ""
            tail = html[html.find(href) + len(href):][:900]
            found = self.TITLE_RE.search(tail)
            if found:
                title = re.sub(r"<[^>]+>", "", found.group(1)).strip()
            videos.append({
                "vod_id": self.p["key"] + "::" + href,
                "vod_name": title or slug,
                "vod_pic": (cdn + "/" + slug + "/cover-t.jpg") if cdn else "",
                "vod_remarks": "",
            })
        return {"list": videos, "page": int(page), "pagecount": int(page) + 1}

    def detail(self, vid):
        page_url = self._abs(vid)
        html = self.s.http(page_url)
        if not html:
            return {"list": []}
        title = ""
        for pat in (r'property="og:title"\s+content="([^"]+)"', r"<title[^>]*>(.*?)</title>"):
            found = re.search(pat, html, re.S)
            if found:
                title = re.sub(r"\s+", " ", found.group(1)).strip()
                break
        slug = page_url.rstrip("/").rsplit("/", 1)[-1]
        cdn = self._cdn(html)
        cover = ""
        found = re.search(r'data-poster="([^"]+)"', html) or re.search(r'property="og:image"\s+content="([^"]+)"', html)
        if found:
            cover = found.group(1)
        elif cdn:
            cover = cdn + "/" + slug + "/cover-n.jpg"
        direct = ""
        body = self.s.http(self._url("/private-test/" + slug + "/play"))
        try:
            playlist = json.loads(body).get("playlist") or []
            direct = str((playlist[0] or {}).get("url") or "") if playlist else ""
        except Exception:
            direct = ""
        vod = {
            "vod_id": self.p["key"] + "::" + vid,
            "vod_name": title or slug,
            "vod_pic": cover,
            "vod_content": "",
            "vod_play_from": "直连",
            "vod_play_url": "正片$" + self.p["key"] + "::" + direct,
        }
        return {"list": [vod]}

    def play(self, flag, url):
        return {"parse": "0", "url": url, "header": self.s.headers()}


class _GenericAdapter(_BaseAdapter):
    """未知平台：先兜底空列表，P4 逐个补。"""


ADAPTERS = {
    "maccms": _MaccmsAdapter,
    "missav": _MissavAdapter,
    "18av": _GenericAdapter,
    "comic": _GenericAdapter,
    "generic": _GenericAdapter,
}


class Spider(SpiderBase):
    def __init__(self):
        try:
            super(Spider, self).__init__()
        except Exception:
            pass
        self._mem = {}
        self._lock = threading.Lock()
        self._snapshot = SNAPSHOT
        self._index = {p["key"]: p for p in SNAPSHOT.get("platforms") or []}
        self._picker = _LinePicker(self)

    # ---------- 宿主能力封装 ----------
    def cache_get(self, key):
        try:
            value = self.getCache(key)
            if isinstance(value, dict):
                return value
            if isinstance(value, str) and value.startswith("{"):
                return json.loads(value)
        except Exception:
            pass
        with self._lock:
            return self._mem.get(key)

    def cache_set(self, key, value):
        try:
            self.setCache(key, value)
        except Exception:
            pass
        with self._lock:
            self._mem[key] = value

    def test_url(self, line_url):
        if not hasattr(self, "_test_map"):
            self._test_map = {}
            for platform in self._snapshot.get("platforms") or []:
                for line in platform.get("lines") or []:
                    if line.get("url"):
                        self._test_map[line["url"]] = line.get("testUrl") or ""
        return self._test_map.get(line_url, "")

    # ---------- 请求与响应（宿主契约要求的 fetch） ----------
    def headers(self):
        return {"User-Agent": UA, "Accept-Language": "zh-CN,zh;q=0.9"}

    def http(self, url, referer=None):
        hdrs = self.headers()
        if referer:
            hdrs["Referer"] = referer
        return _http(url, timeout=HTTP_TIMEOUT, headers=hdrs)[1]

    def fetch(self, url, headers=None, **kw):
        """基类 fetch 在 iSH 环境不可用，必须自带；返回 requests 兼容对象。"""
        kw.pop("timeout", None)
        status, text = _http(url, timeout=HTTP_TIMEOUT, headers=headers or self.headers())
        return _Response(status, text)

    # ---------- 蜘蛛接口 ----------
    def init(self, extend=""):
        try:
            super().init(extend)
        except Exception:
            pass
        hosts = getattr(self, "_vbox_effective_hosts", None) or []
        self._entries = [h.rstrip("/") for h in hosts if str(h).startswith("http")] or \
                        list(SNAPSHOT.get("entry") or [])
        # 重置进程内状态，避免宿主常驻单例把上次的临时结果带过来
        self._test_map = {}
        with self._lock:
            self._mem.clear()

    def getName(self):
        return TITLE

    def getDependence(self):
        return []

    def isVideoFormat(self, url):
        low = (url or "").lower()
        return any(k in low for k in (".m3u8", ".mp4", ".flv", ".mkv", ".webm"))

    def manualVideoCheck(self):
        return False

    def destroy(self):
        pass

    def action(self, action):
        pass

    def homeContent(self, filter=True):
        classes = []
        filters = {}
        for platform in self._snapshot.get("platforms") or []:
            item = {"type_id": platform["key"], "type_name": platform["name"]}
            # 客户端读 class[].sub_categories（国色天香同款约定），选中后回传 "平台key|分类id"
            if platform.get("adapter") != "missav":
                subs = [
                    {"type_id": platform["key"] + "|" + c["type_id"], "type_name": c["type_name"]}
                    for c in (platform.get("classes") or [])
                ]
                if subs:
                    item["sub_categories"] = subs
            classes.append(item)
            chips = []
            cats = platform.get("classes") or []
            if cats:
                chips.append({
                    "key": "cate",
                    "name": "分类",
                    "value": [{"v": c["type_id"], "n": c["type_name"]} for c in cats],
                })
            lines = platform.get("lines") or []
            chips.append({
                "key": "line",
                "name": "线路",
                "value": [{"v": "0", "n": "自动"}] +
                         [{"v": str(i + 1), "n": "线路 " + str(i + 1)} for i in range(len(lines))],
            })
            filters[platform["key"]] = chips
        return {"class": classes, "filters": filters, "list": []}

    def homeVideoContent(self):
        return {"list": []}

    @staticmethod
    def _norm_extend(extend, filter):
        data = {}
        for src in (extend, filter):
            if isinstance(src, str):
                try:
                    src = json.loads(src)
                except Exception:
                    continue
            if isinstance(src, dict):
                for k, v in src.items():
                    data[str(k)] = v
            elif isinstance(src, list):
                for item in src:
                    if isinstance(item, dict) and item.get("key"):
                        data[str(item["key"])] = item.get("value")
        return data

    def categoryContent(self, tid, pg, filter, extend):
        # 二级分类：tid = "平台key|分类id"
        tid = str(tid or "")
        sub_cate = ""
        if "|" in tid:
            tid, _, sub_cate = tid.partition("|")
        platform = self._index.get(tid)
        if not platform:
            return {"list": []}
        extend = self._norm_extend(extend, filter)
        if sub_cate:
            extend.setdefault("cate", sub_cate)
        line_no = str(extend.get("line") or "0")
        if line_no.isdigit() and int(line_no) > 0:
            lines = platform.get("lines") or []
            index = int(line_no) - 1
            host = lines[index]["url"] if index < len(lines) else ""
            if host:
                # 显式选的线路直接记为胜者，后续自动模式不再探测
                self._picker.remember(platform, host)
        else:
            host = self._picker.pick(platform)
        if not host:
            return {"list": []}

        cate = str(extend.get("cate") or "")
        if not cate:
            cats = platform.get("classes") or []
            cate = cats[0]["type_id"] if cats else "0"

        cache_key = "x99dh:list:%s:%s:%s" % (platform["key"], cate, pg)
        hit = self.cache_get(cache_key)
        if hit and time.time() - hit.get("ts", 0) < 180:
            return hit["data"]

        adapter_cls = ADAPTERS.get(platform.get("adapter") or "generic", _GenericAdapter)
        try:
            result = adapter_cls(self, platform, host).list(cate, pg)
            if result.get("list"):
                self.cache_set(cache_key, {"data": result, "ts": time.time()})
            return result
        except Exception:
            return {"list": []}

    def detailContent(self, array):
        try:
            vod_id = array[0] if array else ""
        except Exception:
            vod_id = ""
        if not vod_id:
            return {"list": []}
        key, _, vid = vod_id.partition("::")
        platform = self._index.get(key)
        if not platform:
            return {"list": []}
        host = self._picker.pick(platform)
        adapter_cls = ADAPTERS.get(platform.get("adapter") or "generic", _GenericAdapter)
        try:
            return adapter_cls(self, platform, host).detail(vid)
        except Exception:
            return {"list": []}

    def playerContent(self, flag, id, vipFlags):
        try:
            key, _, target = (id or "").partition("::")
            platform = self._index.get(key)
            if not platform:
                return {"parse": "0", "url": ""}
            host = self._picker.pick(platform)
            adapter_cls = ADAPTERS.get(platform.get("adapter") or "generic", _GenericAdapter)
            return adapter_cls(self, platform, host).play(flag, target)
        except Exception:
            return {"parse": "0", "url": ""}

    def searchContent(self, key, quick, pg="1"):
        return {"list": []}

    def localProxy(self, param):
        return None
