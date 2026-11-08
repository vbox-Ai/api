# -*- coding: utf-8 -*-
"""X99视频导航 — vbox 远程源 python 蜘蛛

由 build_nav_source.py 生成，请勿手改。
类型: video    快照: 2026.11.07.2251
"""
import base64
import http.client
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
SNAPSHOT_VERSION = "2026.11.07.2251"
SNAPSHOT = json.loads('{"version":"2026.11.07.2251","entry":["https://x99dh.net","https://x99dh.lat"],"platforms":[{"key":"x99_be9dc0cd","name":"MissAV","kind":"video","adapter":"missav","desc":"著名亚洲视频站点","icon":"play.rectangle.fill","url":"https://www.thisav66.com/cn","lines":[{"url":"https://www.missav666.net/cn","testUrl":"https://www.missav666.net/status.html","ok":true,"ms":189.0},{"url":"https://www.missav03.net/cn","testUrl":"https://www.missav03.net/status.html","ok":true,"ms":194.0},{"url":"https://www.missav05.net/cn","testUrl":"https://www.missav05.net/status.html","ok":true,"ms":202.0},{"url":"https://www.thisav01.net/cn","testUrl":"https://www.thisav01.net/status.html","ok":true,"ms":207.0},{"url":"https://www.missav02.net/cn","testUrl":"https://www.missav02.net/status.html","ok":true,"ms":280.0},{"url":"https://www.missav.watch/cn","testUrl":"https://www.missav.watch/status.html","ok":true,"ms":397.0},{"url":"https://www.njavtv01.com/cn","testUrl":"https://www.njavtv01.com/status.html","ok":true,"ms":435.0},{"url":"https://www.missav08.net/cn","testUrl":"https://www.missav08.net/status.html","ok":true,"ms":497.0},{"url":"https://www.missav888.net/cn","testUrl":"https://www.missav888.net/status.html","ok":true,"ms":690.0},{"url":"https://www.missav09.com/cn","testUrl":"https://www.missav09.com/status.html","ok":true,"ms":775.0},{"url":"https://www.thisav01.cc/cn","testUrl":"https://www.thisav01.cc/status.html","ok":true,"ms":809.0},{"url":"https://www.njav01.com/cn","testUrl":"https://www.njav01.com/status.html","ok":true,"ms":873.0},{"url":"https://www.thisav.pw/cn","testUrl":"https://www.thisav.pw/status.html","ok":true,"ms":988.0},{"url":"https://www.njavtv.nl/cn","testUrl":"https://www.njavtv.nl/status.html","ok":true,"ms":994.0},{"url":"https://www.njav.one/cn","testUrl":"https://www.njav.one/status.html","ok":true,"ms":1001.0},{"url":"https://www.missav123.life/cn","testUrl":"https://www.missav123.life/status.html","ok":true,"ms":1047.0},{"url":"https://www.missav-ai.cc/cn","testUrl":"https://www.missav-ai.cc/status.html","ok":true,"ms":1167.0},{"url":"https://www.missav666.cc/cn","testUrl":"https://www.missav666.cc/status.html","ok":true,"ms":1203.0},{"url":"https://www.missav01.net/cn","testUrl":"https://www.missav01.net/status.html","ok":true,"ms":1273.0},{"url":"https://www.missav05.com/cn","testUrl":"https://www.missav05.com/status.html","ok":true,"ms":1327.0},{"url":"https://www.njav01.net/cn","testUrl":"https://www.njav01.net/status.html","ok":true,"ms":1376.0},{"url":"https://www.missav06.com/cn","testUrl":"https://www.missav06.com/status.html","ok":true,"ms":1439.0},{"url":"https://www.missav06.net/cn","testUrl":"https://www.missav06.net/status.html","ok":true,"ms":1628.0},{"url":"https://www.missav888.cc/cn","testUrl":"https://www.missav888.cc/status.html","ok":true,"ms":1657.0},{"url":"https://www.thisav02.com/cn","testUrl":"https://www.thisav02.com/status.html","ok":true,"ms":1757.0},{"url":"https://www.missav2.one/cn","testUrl":"https://www.missav2.one/status.html","ok":true,"ms":1824.0},{"url":"https://www.missav1.one/cn","testUrl":"https://www.missav1.one/status.html","ok":true,"ms":1862.0},{"url":"https://www.missav07.net/cn","testUrl":"https://www.missav07.net/status.html","ok":true,"ms":1900.0},{"url":"https://www.thisav02.net/cn","testUrl":"https://www.thisav02.net/status.html","ok":true,"ms":1977.0},{"url":"https://www.thisav33.net/cn","testUrl":"https://www.thisav33.net/status.html","ok":true,"ms":2302.0},{"url":"https://www.missav123.nl/cn","testUrl":"https://www.missav123.nl/status.html","ok":true,"ms":2343.0},{"url":"https://www.missav08.com/cn","testUrl":"https://www.missav08.com/status.html","ok":true,"ms":3544.0},{"url":"https://www.thisav66.com/cn","testUrl":"https://www.thisav66.com/status.html","ok":true,"ms":3662.0},{"url":"https://www.thisav33.com/cn","testUrl":"https://www.thisav33.com/status.html","ok":true,"ms":4127.0},{"url":"https://www.njavtv.my/cn","testUrl":"https://www.njavtv.my/status.html","ok":false,"ms":651.0},{"url":"https://www.missav1.vip/cn","testUrl":"https://www.missav1.vip/status.html","ok":false,"ms":784.0},{"url":"https://www.missav3.one/cn","testUrl":"https://www.missav3.one/status.html","ok":false,"ms":1010.0},{"url":"https://www.missav365.icu/cn","testUrl":"https://www.missav365.icu/status.html","ok":false,"ms":1659.0},{"url":"https://www.thisav.sbs/cn","testUrl":"https://www.thisav.sbs/status.html","ok":false,"ms":1688.0},{"url":"https://www.missav365.one/cn","testUrl":"https://www.missav365.one/status.html","ok":false,"ms":1908.0},{"url":"https://www.njavtv.art/cn","testUrl":"https://www.njavtv.art/status.html","ok":false,"ms":1950.0}],"classes":[{"type_id":"20","type_name":"国产"},{"type_id":"21","type_name":"日本有码"},{"type_id":"22","type_name":"日本无码"},{"type_id":"28","type_name":"中文字幕"},{"type_id":"23","type_name":"欧美"},{"type_id":"24","type_name":"动漫"},{"type_id":"25","type_name":"伦理"}]},{"key":"x99_531d29bb","name":"Hanime1","kind":"video","adapter":"hanime","desc":"著名动漫视频站点","icon":"play.rectangle.fill","url":"https://www.hanime16.com/enter","lines":[{"url":"https://www.hanime169.net/enter","testUrl":"https://www.hanime169.net/status.html","ok":true,"ms":464.0},{"url":"https://www.hanime101.com/enter","testUrl":"https://www.hanime101.com/status.html","ok":true,"ms":527.0},{"url":"https://www.hanime101.net/enter","testUrl":"https://www.hanime101.net/status.html","ok":true,"ms":593.0},{"url":"https://www.hanime163.com/enter","testUrl":"https://www.hanime163.com/status.html","ok":true,"ms":606.0},{"url":"https://www.hanime666.net/enter","testUrl":"https://www.hanime666.net/status.html","ok":true,"ms":629.0},{"url":"https://www.hanime02.com/enter","testUrl":"https://www.hanime02.com/status.html","ok":true,"ms":641.0},{"url":"https://www.hanime123.org/enter","testUrl":"https://www.hanime123.org/status.html","ok":true,"ms":749.0},{"url":"https://www.hanime169.cc/enter","testUrl":"https://www.hanime169.cc/status.html","ok":true,"ms":797.0},{"url":"https://www.hanime169.com/enter","testUrl":"https://www.hanime169.com/status.html","ok":true,"ms":816.0},{"url":"https://www.hanime999.com/enter","testUrl":"https://www.hanime999.com/status.html","ok":true,"ms":849.0},{"url":"https://www.hanime2.icu/enter","testUrl":"https://www.hanime2.icu/status.html","ok":true,"ms":863.0},{"url":"https://www.hanime103.com/enter","testUrl":"https://www.hanime103.com/status.html","ok":true,"ms":1015.0},{"url":"https://www.hanime999.cc/enter","testUrl":"https://www.hanime999.cc/status.html","ok":true,"ms":1017.0},{"url":"https://www.hanime1.my/enter","testUrl":"https://www.hanime1.my/status.html","ok":true,"ms":1020.0},{"url":"https://www.hanime102.net/enter","testUrl":"https://www.hanime102.net/status.html","ok":true,"ms":1031.0},{"url":"https://www.hanime123.cc/enter","testUrl":"https://www.hanime123.cc/status.html","ok":true,"ms":1158.0},{"url":"https://www.hanime1.life/enter","testUrl":"https://www.hanime1.life/status.html","ok":true,"ms":1239.0},{"url":"https://www.hanime999.net/enter","testUrl":"https://www.hanime999.net/status.html","ok":true,"ms":1449.0},{"url":"https://www.hanime102.com/enter","testUrl":"https://www.hanime102.com/status.html","ok":true,"ms":1516.0},{"url":"https://www.hanime103.net/enter","testUrl":"https://www.hanime103.net/status.html","ok":true,"ms":1681.0},{"url":"https://www.hanime123.sbs/enter","testUrl":"https://www.hanime123.sbs/status.html","ok":true,"ms":1723.0},{"url":"https://www.hanime123.one/enter","testUrl":"https://www.hanime123.one/status.html","ok":true,"ms":2281.0},{"url":"https://www.hanime16.com/enter","testUrl":"https://www.hanime16.com/status.html","ok":true,"ms":3426.0},{"url":"https://www.hanime1.art/enter","testUrl":"https://www.hanime1.art/status.html","ok":true,"ms":3966.0},{"url":"https://www.hanime104.com/enter","testUrl":"https://www.hanime104.com/status.html","ok":true,"ms":9369.0},{"url":"https://www.hanime163.net/enter","testUrl":"https://www.hanime163.net/status.html","ok":true,"ms":11410.0},{"url":"https://www.hanime1-me.cc/enter","testUrl":"https://www.hanime1-me.cc/status.html","ok":false,"ms":945.0},{"url":"https://www.hanime2.one/enter","testUrl":"https://www.hanime2.one/status.html","ok":false,"ms":1022.0},{"url":"https://www.hanime1.pw/enter","testUrl":"https://www.hanime1.pw/status.html","ok":false,"ms":1096.0},{"url":"https://www.hanime888.net/enter","testUrl":"https://www.hanime888.net/status.html","ok":false,"ms":1139.0},{"url":"https://www.hanime2.org/enter","testUrl":"https://www.hanime2.org/status.html","ok":false,"ms":1332.0},{"url":"https://www.hanime2.cfd/enter","testUrl":"https://www.hanime2.cfd/status.html","ok":false,"ms":2362.0}],"classes":[]},{"key":"x99_5e2df580","name":"LissAV","kind":"video","adapter":"kvs","desc":"最全日本AV站点","icon":"play.rectangle.fill","url":"https://huangguo04.net/asian/zh-CN","lines":[{"url":"https://tktube.vip/asian/zh-CN","testUrl":"https://tktube.vip/status.html","ok":true,"ms":484.0},{"url":"https://huangguo01.net/asian/zh-CN","testUrl":"https://huangguo01.net/status.html","ok":true,"ms":810.0},{"url":"https://lissav.nl/asian/zh-CN","testUrl":"https://lissav.nl/status.html","ok":true,"ms":915.0},{"url":"https://lissav.vip/asian/zh-CN","testUrl":"https://lissav.vip/status.html","ok":true,"ms":954.0},{"url":"https://tktube.nl/asian/zh-CN","testUrl":"https://tktube.nl/status.html","ok":true,"ms":1042.0},{"url":"https://lissav.my/asian/zh-CN","testUrl":"https://lissav.my/status.html","ok":true,"ms":1073.0},{"url":"https://lissav.ws/asian/zh-CN","testUrl":"https://lissav.ws/status.html","ok":true,"ms":1176.0},{"url":"https://madou8.ws/asian/zh-CN","testUrl":"https://madou8.ws/status.html","ok":true,"ms":1332.0},{"url":"https://madou666.net/asian/zh-CN","testUrl":"https://madou666.net/status.html","ok":true,"ms":1602.0},{"url":"https://lissav.net/asian/zh-CN","testUrl":"https://lissav.net/status.html","ok":true,"ms":1719.0},{"url":"https://mdba8.com/asian/zh-CN","testUrl":"https://mdba8.com/status.html","ok":true,"ms":1908.0},{"url":"https://madou8.pw/asian/zh-CN","testUrl":"https://madou8.pw/status.html","ok":true,"ms":2182.0},{"url":"https://lissav1.com/asian/zh-CN","testUrl":"https://lissav1.com/status.html","ok":true,"ms":2215.0},{"url":"https://madou8.my/asian/zh-CN","testUrl":"https://madou8.my/status.html","ok":true,"ms":2566.0},{"url":"https://huangguo04.net/asian/zh-CN","testUrl":"https://huangguo04.net/status.html","ok":true,"ms":2960.0},{"url":"https://huangguo02.net/asian/zh-CN","testUrl":"https://huangguo02.net/status.html","ok":true,"ms":4656.0},{"url":"https://huangguo123.com/asian/zh-CN","testUrl":"https://huangguo123.com/status.html","ok":true,"ms":4716.0},{"url":"https://huangguo03.net/asian/zh-CN","testUrl":"https://huangguo03.net/status.html","ok":true,"ms":4726.0},{"url":"https://mdba8.net/asian/zh-CN","testUrl":"https://mdba8.net/status.html","ok":true,"ms":5592.0},{"url":"https://javxx.sbs/asian/zh-CN","testUrl":"https://javxx.sbs/status.html","ok":true,"ms":13261.0},{"url":"https://lissav.one/asian/zh-CN","testUrl":"https://lissav.one/status.html","ok":true,"ms":16098.0},{"url":"https://lissav.com/asian/zh-CN","testUrl":"https://lissav.com/status.html","ok":false,"ms":1897.0}],"classes":[]},{"key":"x99_2828ee09","name":"LissAV国产区","kind":"video","adapter":"kvs","desc":"数十万精品AV","icon":"play.rectangle.fill","url":"https://huangguo04.net/domestic/zh-CN","lines":[{"url":"https://huangguo01.net/domestic/zh-CN","testUrl":"https://huangguo01.net/status.html","ok":true,"ms":130.0},{"url":"https://lissav1.com/domestic/zh-CN","testUrl":"https://lissav1.com/status.html","ok":true,"ms":175.0},{"url":"https://huangguo123.com/domestic/zh-CN","testUrl":"https://huangguo123.com/status.html","ok":true,"ms":204.0},{"url":"https://madou8.ws/domestic/zh-CN","testUrl":"https://madou8.ws/status.html","ok":true,"ms":222.0},{"url":"https://mdba8.net/domestic/zh-CN","testUrl":"https://mdba8.net/status.html","ok":true,"ms":417.0},{"url":"https://tktube.nl/domestic/zh-CN","testUrl":"https://tktube.nl/status.html","ok":true,"ms":482.0},{"url":"https://huangguo02.net/domestic/zh-CN","testUrl":"https://huangguo02.net/status.html","ok":true,"ms":509.0},{"url":"https://lissav.one/domestic/zh-CN","testUrl":"https://lissav.one/status.html","ok":true,"ms":547.0},{"url":"https://lissav.nl/domestic/zh-CN","testUrl":"https://lissav.nl/status.html","ok":true,"ms":567.0},{"url":"https://lissav.net/domestic/zh-CN","testUrl":"https://lissav.net/status.html","ok":true,"ms":1088.0},{"url":"https://madou8.pw/domestic/zh-CN","testUrl":"https://madou8.pw/status.html","ok":true,"ms":1088.0},{"url":"https://tktube.vip/domestic/zh-CN","testUrl":"https://tktube.vip/status.html","ok":true,"ms":1114.0},{"url":"https://lissav.my/domestic/zh-CN","testUrl":"https://lissav.my/status.html","ok":true,"ms":1133.0},{"url":"https://madou8.my/domestic/zh-CN","testUrl":"https://madou8.my/status.html","ok":true,"ms":1353.0},{"url":"https://madou666.net/domestic/zh-CN","testUrl":"https://madou666.net/status.html","ok":true,"ms":1668.0},{"url":"https://mdba8.com/domestic/zh-CN","testUrl":"https://mdba8.com/status.html","ok":true,"ms":3124.0},{"url":"https://huangguo03.net/domestic/zh-CN","testUrl":"https://huangguo03.net/status.html","ok":true,"ms":3202.0},{"url":"https://lissav.ws/domestic/zh-CN","testUrl":"https://lissav.ws/status.html","ok":true,"ms":4031.0},{"url":"https://huangguo04.net/domestic/zh-CN","testUrl":"https://huangguo04.net/status.html","ok":true,"ms":4073.0},{"url":"https://javxx.sbs/domestic/zh-CN","testUrl":"https://javxx.sbs/status.html","ok":true,"ms":7681.0},{"url":"https://lissav.vip/domestic/zh-CN","testUrl":"https://lissav.vip/status.html","ok":true,"ms":13332.0},{"url":"https://lissav.com/domestic/zh-CN","testUrl":"https://lissav.com/status.html","ok":false,"ms":1900.0}],"classes":[]},{"key":"x99_2721419a","name":"Jable","kind":"video","adapter":"jable","desc":"另一个亚洲视频站点","icon":"play.rectangle.fill","url":"https://jable02.com/enter","lines":[{"url":"https://jable02.com/enter","testUrl":"https://jable02.com/status.html","ok":true,"ms":176.0},{"url":"https://jable1.cc/enter","testUrl":"https://jable1.cc/status.html","ok":true,"ms":507.0},{"url":"https://jable888.com/enter","testUrl":"https://jable888.com/status.html","ok":true,"ms":599.0},{"url":"https://jable666.net/enter","testUrl":"https://jable666.net/status.html","ok":true,"ms":760.0},{"url":"https://jable.cfd/enter","testUrl":"https://jable.cfd/status.html","ok":true,"ms":848.0},{"url":"https://jable666.com/enter","testUrl":"https://jable666.com/status.html","ok":true,"ms":874.0},{"url":"https://jable18.top/enter","testUrl":"https://jable18.top/status.html","ok":true,"ms":915.0},{"url":"https://jable01.net/enter","testUrl":"https://jable01.net/status.html","ok":true,"ms":1049.0},{"url":"https://jable1.xyz/enter","testUrl":"https://jable1.xyz/status.html","ok":true,"ms":1337.0},{"url":"https://91jable.top/enter","testUrl":"https://91jable.top/status.html","ok":true,"ms":1537.0},{"url":"https://91jable.icu/enter","testUrl":"https://91jable.icu/status.html","ok":true,"ms":1579.0},{"url":"https://jable1.vip/enter","testUrl":"https://jable1.vip/status.html","ok":true,"ms":1847.0},{"url":"https://jable01.com/enter","testUrl":"https://jable01.com/status.html","ok":true,"ms":2295.0},{"url":"https://jable1.net/enter","testUrl":"https://jable1.net/status.html","ok":true,"ms":2776.0},{"url":"https://jable888.net/enter","testUrl":"https://jable888.net/status.html","ok":true,"ms":4790.0},{"url":"https://jable1.lat/enter","testUrl":"https://jable1.lat/status.html","ok":true,"ms":7908.0},{"url":"https://jable1.com/enter","testUrl":"https://jable1.com/status.html","ok":false,"ms":1557.0}],"classes":[]},{"key":"x99_f3faa727","name":"xhamster","kind":"video","adapter":"xhamster","desc":"著名视频站点","icon":"play.rectangle.fill","url":"https://zh.xhamster02.com/enter","lines":[{"url":"https://zh.xv123.top/enter","testUrl":"https://zh.xv123.top/status.html","ok":true,"ms":561.0},{"url":"https://zh.xhamster1.cc/enter","testUrl":"https://zh.xhamster1.cc/status.html","ok":true,"ms":662.0},{"url":"https://zh.xhamster02.com/enter","testUrl":"https://zh.xhamster02.com/status.html","ok":true,"ms":730.0},{"url":"https://zh.xhamster1.art/enter","testUrl":"https://zh.xhamster1.art/status.html","ok":true,"ms":776.0},{"url":"https://zh.xhamster1.one/enter","testUrl":"https://zh.xhamster1.one/status.html","ok":true,"ms":1576.0},{"url":"https://zh.xhamster01.net/enter","testUrl":"https://zh.xhamster01.net/status.html","ok":true,"ms":1582.0},{"url":"https://zh.xhamster1.net/enter","testUrl":"https://zh.xhamster1.net/status.html","ok":true,"ms":1705.0},{"url":"https://zh.xhamster1.top/enter","testUrl":"https://zh.xhamster1.top/status.html","ok":true,"ms":1721.0},{"url":"https://zh.xhamster1.vip/enter","testUrl":"https://zh.xhamster1.vip/status.html","ok":true,"ms":1870.0},{"url":"https://zh.xhamster.ist/enter","testUrl":"https://zh.xhamster.ist/status.html","ok":true,"ms":1959.0},{"url":"https://zh.xv123.icu/enter","testUrl":"https://zh.xv123.icu/status.html","ok":true,"ms":2082.0},{"url":"https://zh.xhamster1.nl/enter","testUrl":"https://zh.xhamster1.nl/status.html","ok":true,"ms":3138.0},{"url":"https://zh.xhamster1.pw/enter","testUrl":"https://zh.xhamster1.pw/status.html","ok":true,"ms":3212.0},{"url":"https://zh.xhamster1.icu/enter","testUrl":"https://zh.xhamster1.icu/status.html","ok":true,"ms":3388.0},{"url":"https://zh.xv123.xyz/enter","testUrl":"https://zh.xv123.xyz/status.html","ok":true,"ms":5012.0}],"classes":[]},{"key":"x99_8be4dcd9","name":"肉视频","kind":"video","adapter":"rou","desc":"国产视频为主,AI短剧","icon":"play.rectangle.fill","url":"https://rou07.net/home","lines":[{"url":"https://rou07.net/home","testUrl":"https://rou07.net/status.html","ok":true,"ms":173.0},{"url":"https://rou08.com/home","testUrl":"https://rou08.com/status.html","ok":true,"ms":519.0},{"url":"https://rou163.top/home","testUrl":"https://rou163.top/status.html","ok":true,"ms":852.0},{"url":"https://rouav.sbs/home","testUrl":"https://rouav.sbs/status.html","ok":true,"ms":945.0},{"url":"https://rou08.net/home","testUrl":"https://rou08.net/status.html","ok":true,"ms":1010.0},{"url":"https://rou07.com/home","testUrl":"https://rou07.com/status.html","ok":true,"ms":1102.0},{"url":"https://rou1.men/home","testUrl":"https://rou1.men/status.html","ok":true,"ms":1285.0},{"url":"https://rou01.cc/home","testUrl":"https://rou01.cc/status.html","ok":true,"ms":1299.0},{"url":"https://rou168.com/home","testUrl":"https://rou168.com/status.html","ok":true,"ms":1827.0},{"url":"https://rou1.art/home","testUrl":"https://rou1.art/status.html","ok":true,"ms":1888.0},{"url":"https://rou1.my/home","testUrl":"https://rou1.my/status.html","ok":true,"ms":1895.0},{"url":"https://rou888.net/home","testUrl":"https://rou888.net/status.html","ok":true,"ms":1970.0},{"url":"https://rou1.sbs/home","testUrl":"https://rou1.sbs/status.html","ok":true,"ms":1982.0},{"url":"https://rou666.com/home","testUrl":"https://rou666.com/status.html","ok":true,"ms":2343.0},{"url":"https://rou666.net/home","testUrl":"https://rou666.net/status.html","ok":true,"ms":2458.0},{"url":"https://rou06.cc/home","testUrl":"https://rou06.cc/status.html","ok":true,"ms":2546.0},{"url":"https://rou1.pw/home","testUrl":"https://rou1.pw/status.html","ok":true,"ms":3323.0},{"url":"https://rouxxx.net/home","testUrl":"https://rouxxx.net/status.html","ok":true,"ms":3423.0},{"url":"https://rou06.net/home","testUrl":"https://rou06.net/status.html","ok":true,"ms":8858.0},{"url":"https://rouxxx.sbs/home","testUrl":"https://rouxxx.sbs/status.html","ok":false,"ms":611.0},{"url":"https://rouxxx.cc/home","testUrl":"https://rouxxx.cc/status.html","ok":false,"ms":1707.0}],"classes":[]},{"key":"x99_f642a3a3","name":"好色TV","kind":"video","adapter":"hsex","desc":"国产中短精选视频","icon":"play.rectangle.fill","url":"https://hsex02.com/enter","lines":[{"url":"https://pb365.top/enter","testUrl":"https://pb365.top/status.html","ok":true,"ms":472.0},{"url":"https://hsex02.com/enter","testUrl":"https://hsex02.com/status.html","ok":true,"ms":573.0},{"url":"https://hsex.nl/enter","testUrl":"https://hsex.nl/status.html","ok":true,"ms":785.0},{"url":"https://hsex01.net/enter","testUrl":"https://hsex01.net/status.html","ok":true,"ms":896.0},{"url":"https://pb365.one/enter","testUrl":"https://pb365.one/status.html","ok":true,"ms":1019.0},{"url":"https://hsex.top/enter","testUrl":"https://hsex.top/status.html","ok":true,"ms":1031.0},{"url":"https://hsex1.sbs/enter","testUrl":"https://hsex1.sbs/status.html","ok":true,"ms":1056.0},{"url":"https://hsex01.com/enter","testUrl":"https://hsex01.com/status.html","ok":true,"ms":1057.0},{"url":"https://hsex1.cc/enter","testUrl":"https://hsex1.cc/status.html","ok":true,"ms":1214.0},{"url":"https://hsex1.icu/enter","testUrl":"https://hsex1.icu/status.html","ok":true,"ms":1253.0},{"url":"https://hsex1.top/enter","testUrl":"https://hsex1.top/status.html","ok":true,"ms":1319.0},{"url":"https://hsex.cfd/enter","testUrl":"https://hsex.cfd/status.html","ok":true,"ms":1330.0},{"url":"https://hsex.sbs/enter","testUrl":"https://hsex.sbs/status.html","ok":true,"ms":1643.0},{"url":"https://hsex.one/enter","testUrl":"https://hsex.one/status.html","ok":true,"ms":2051.0},{"url":"https://pb365.sbs/enter","testUrl":"https://pb365.sbs/status.html","ok":true,"ms":2253.0},{"url":"https://hsex1.vip/enter","testUrl":"https://hsex1.vip/status.html","ok":true,"ms":2985.0},{"url":"https://hsex.mom/enter","testUrl":"https://hsex.mom/status.html","ok":false,"ms":1402.0},{"url":"https://pb365.nl/enter","testUrl":"https://pb365.nl/status.html","ok":false,"ms":2197.0}],"classes":[]},{"key":"x99_99fa5c38","name":"321AV","kind":"video","adapter":"maccms","desc":"视频站点，速度更快","icon":"play.rectangle.fill","url":"https://321av.art/enter","lines":[{"url":"https://321xav.cc/enter","testUrl":"https://321xav.cc/status.html","ok":true,"ms":193.0},{"url":"https://321av.men/enter","testUrl":"https://321av.men/status.html","ok":true,"ms":332.0},{"url":"https://321av.org/enter","testUrl":"https://321av.org/status.html","ok":true,"ms":409.0},{"url":"https://321av.xyz/enter","testUrl":"https://321av.xyz/status.html","ok":true,"ms":595.0},{"url":"https://321av.fans/enter","testUrl":"https://321av.fans/status.html","ok":true,"ms":1035.0},{"url":"https://321av.ws/enter","testUrl":"https://321av.ws/status.html","ok":true,"ms":1056.0},{"url":"https://321av.sbs/enter","testUrl":"https://321av.sbs/status.html","ok":true,"ms":2066.0},{"url":"https://321av.icu/enter","testUrl":"https://321av.icu/status.html","ok":true,"ms":2870.0},{"url":"https://321av.art/enter","testUrl":"https://321av.art/status.html","ok":true,"ms":3070.0},{"url":"https://321av.top/enter","testUrl":"https://321av.top/status.html","ok":true,"ms":6460.0},{"url":"https://321av.vip/enter","testUrl":"https://321av.vip/status.html","ok":false,"ms":1767.0}],"classes":[{"type_id":"20","type_name":"有码影片","href":"/vodtype/20.html"},{"type_id":"21","type_name":"无码影片","href":"/vodtype/21.html"},{"type_id":"22","type_name":"中文字幕","href":"/vodtype/22.html"}]},{"key":"x99_5b25e3c1","name":"rouAV","kind":"video","adapter":"maccms","desc":"高品质国产AV","icon":"play.rectangle.fill","url":"https://rou123.ws/enter","lines":[{"url":"https://rou123.cc/enter","testUrl":"https://rou123.cc/status.html","ok":true,"ms":273.0},{"url":"https://rou123.cfd/enter","testUrl":"https://rou123.cfd/status.html","ok":true,"ms":1031.0},{"url":"https://rou123.ws/enter","testUrl":"https://rou123.ws/status.html","ok":true,"ms":1179.0},{"url":"https://rou123.org/enter","testUrl":"https://rou123.org/status.html","ok":true,"ms":1474.0},{"url":"https://rou123.top/enter","testUrl":"https://rou123.top/status.html","ok":true,"ms":1753.0},{"url":"https://rou123.sbs/enter","testUrl":"https://rou123.sbs/status.html","ok":true,"ms":1793.0},{"url":"https://rou123.one/enter","testUrl":"https://rou123.one/status.html","ok":false,"ms":1161.0},{"url":"https://rou123.vip/enter","testUrl":"https://rou123.vip/status.html","ok":false,"ms":1376.0}],"classes":[{"type_id":"7","type_name":"国产AV","href":"/vodtype/7.html"},{"type_id":"3","type_name":"日本","href":"/vodtype/3.html"},{"type_id":"6","type_name":"自拍流出","href":"/vodtype/6.html"},{"type_id":"5","type_name":"探花","href":"/vodtype/5.html"},{"type_id":"4","type_name":"OnlyFans","href":"/vodtype/4.html"},{"type_id":"1","type_name":"其他","href":"/vodtype/1.html"}]},{"key":"x99_d7f940f5","name":"黄色仓库","kind":"video","adapter":"maccms","desc":"最新麻豆视频,麻豆视频在线观看,天美传媒,91制片厂,天美传媒,精东影业,蜜桃传媒,麻豆网","icon":"play.rectangle.fill","url":"https://www.hsck01.net/enter","lines":[{"url":"https://www.69ck1.net/enter","testUrl":"https://www.69ck1.net/status.html","ok":true,"ms":551.0},{"url":"https://www.69ck1.com/enter","testUrl":"https://www.69ck1.com/status.html","ok":true,"ms":680.0},{"url":"https://www.hsck.nl/enter","testUrl":"https://www.hsck.nl/status.html","ok":true,"ms":840.0},{"url":"https://www.69ck.one/enter","testUrl":"https://www.69ck.one/status.html","ok":true,"ms":841.0},{"url":"https://www.hsck.sbs/enter","testUrl":"https://www.hsck.sbs/status.html","ok":true,"ms":1004.0},{"url":"https://www.hsck01.net/enter","testUrl":"https://www.hsck01.net/status.html","ok":true,"ms":1365.0},{"url":"https://www.69ck.ws/enter","testUrl":"https://www.69ck.ws/status.html","ok":true,"ms":2140.0}],"classes":[{"type_id":"1","type_name":"麻豆","href":"/index.php/vod/type/id/1.html"},{"type_id":"2","type_name":"中字","href":"/index.php/vod/type/id/2.html"},{"type_id":"3","type_name":"国产","href":"/index.php/vod/type/id/3.html"},{"type_id":"4","type_name":"欧美","href":"/index.php/vod/type/id/4.html"},{"type_id":"5","type_name":"日韩","href":"/index.php/vod/type/id/5.html"}]},{"key":"x99_2eb3f212","name":"18av","kind":"video","adapter":"18av","desc":"综合性成人站点，包含视频、小说、色图、漫画等","icon":"play.rectangle.fill","url":"https://www.18av02.com/enter","lines":[{"url":"https://www.18av.ws/enter","testUrl":"https://www.18av.ws/status.html","ok":true,"ms":513.0},{"url":"https://www.18av.nl/enter","testUrl":"https://www.18av.nl/status.html","ok":true,"ms":798.0},{"url":"https://www.18av01.cc/enter","testUrl":"https://www.18av01.cc/status.html","ok":true,"ms":939.0},{"url":"https://www.18av02.com/enter","testUrl":"https://www.18av02.com/status.html","ok":true,"ms":1127.0},{"url":"https://www.18av01.net/enter","testUrl":"https://www.18av01.net/status.html","ok":true,"ms":1681.0},{"url":"https://www.18av.pw/enter","testUrl":"https://www.18av.pw/status.html","ok":true,"ms":2571.0}],"classes":[{"type_id":"chinese_list","type_name":"中文字幕"},{"type_id":"censored_list","type_name":"有碼AV"},{"type_id":"uncensored_list","type_name":"無碼AV"},{"type_id":"amateurjav_list","type_name":"素人AV"},{"type_id":"reducing-mosaic_list","type_name":"無碼破解"},{"type_id":"animation_list","type_name":"H動畫"},{"type_id":"dt_list","type_name":"國產自拍"}]},{"key":"x99_f7ba81a6","name":"大哥视频","kind":"video","adapter":"dage","desc":"最新各类国产、日韩、欧美等视频","icon":"play.rectangle.fill","url":"https://dage.one/enter","lines":[{"url":"https://dage.one/enter","testUrl":"https://dage.one/status.html","ok":true,"ms":192.0},{"url":"https://dage01.net/enter","testUrl":"https://dage01.net/status.html","ok":true,"ms":692.0}],"classes":[]},{"key":"x99_a4235f12","name":"Pornhub","kind":"video","adapter":"pornhub","desc":"P站","icon":"play.rectangle.fill","url":"https://cn.pornhub06.com/enter","lines":[{"url":"https://cn.pornhub06.com/enter","testUrl":"https://cn.pornhub06.com/status.html","ok":true,"ms":406.0},{"url":"https://cn.pornhub03.net/enter","testUrl":"https://cn.pornhub03.net/status.html","ok":true,"ms":940.0},{"url":"https://cn.pornhub02.net/enter","testUrl":"https://cn.pornhub02.net/status.html","ok":true,"ms":1187.0},{"url":"https://cn.pornhub163.com/enter","testUrl":"https://cn.pornhub163.com/status.html","ok":true,"ms":1281.0},{"url":"https://cn.pornhub163.net/enter","testUrl":"https://cn.pornhub163.net/status.html","ok":true,"ms":1465.0},{"url":"https://cn.pornhub365.com/enter","testUrl":"https://cn.pornhub365.com/status.html","ok":true,"ms":1604.0},{"url":"https://cn.pornhub03.com/enter","testUrl":"https://cn.pornhub03.com/status.html","ok":true,"ms":1636.0},{"url":"https://cn.pornhub365.sbs/enter","testUrl":"https://cn.pornhub365.sbs/status.html","ok":true,"ms":2526.0},{"url":"https://cn.pornhub02.com/enter","testUrl":"https://cn.pornhub02.com/status.html","ok":true,"ms":2650.0},{"url":"https://cn.pornhub666.com/enter","testUrl":"https://cn.pornhub666.com/status.html","ok":true,"ms":2803.0},{"url":"https://cn.pornhub666.cc/enter","testUrl":"https://cn.pornhub666.cc/status.html","ok":true,"ms":2991.0},{"url":"https://cn.pornhub1.icu/enter","testUrl":"https://cn.pornhub1.icu/status.html","ok":true,"ms":3134.0},{"url":"https://cn.pornhub365.top/enter","testUrl":"https://cn.pornhub365.top/status.html","ok":false,"ms":1876.0},{"url":"https://cn.pornhub1.mom/enter","testUrl":"https://cn.pornhub1.mom/status.html","ok":false,"ms":1945.0},{"url":"https://cn.pornhub1.cc/enter","testUrl":"https://cn.pornhub1.cc/status.html","ok":false,"ms":2617.0},{"url":"https://cn.pornhub365.mom/enter","testUrl":"https://cn.pornhub365.mom/status.html","ok":false,"ms":2873.0}],"classes":[]},{"key":"x99_63401799","name":"XVIDEOS","kind":"video","adapter":"xvideos","desc":"X站","icon":"play.rectangle.fill","url":"https://www.xvideos163.top/enter","lines":[{"url":"https://www.91xvideos.top/enter","testUrl":"https://www.91xvideos.top/status.html","ok":true,"ms":1292.0},{"url":"https://www.xvideos1.icu/enter","testUrl":"https://www.xvideos1.icu/status.html","ok":true,"ms":2319.0},{"url":"https://www.x123.xyz/enter","testUrl":"https://www.x123.xyz/status.html","ok":false,"ms":1378.0},{"url":"https://www.x123.one/enter","testUrl":"https://www.x123.one/status.html","ok":false,"ms":1685.0},{"url":"https://www.xvideos163.top/enter","testUrl":"https://www.xvideos163.top/status.html","ok":false,"ms":12684.0}],"classes":[]},{"key":"x99_a4cb289c","name":"Xanimu","kind":"video","adapter":"xanimu","desc":"免费2D、3D、动漫性爱、漫画、卡通","icon":"play.rectangle.fill","url":"https://xanimu.ws/zh-CN/","lines":[{"url":"https://xanimu.one/zh-CN/","testUrl":"https://xanimu.one/status.html","ok":true,"ms":473.0},{"url":"https://xanimu.net/zh-CN/","testUrl":"https://xanimu.net/status.html","ok":true,"ms":515.0},{"url":"https://xanimu.sbs/zh-CN/","testUrl":"https://xanimu.sbs/status.html","ok":true,"ms":884.0},{"url":"https://xanimu.art/zh-CN/","testUrl":"https://xanimu.art/status.html","ok":true,"ms":926.0},{"url":"https://xanimu.ws/zh-CN/","testUrl":"https://xanimu.ws/status.html","ok":true,"ms":1610.0},{"url":"https://xanimu.top/zh-CN/","testUrl":"https://xanimu.top/status.html","ok":true,"ms":2387.0}],"classes":[]},{"key":"x99_becefbcf","name":"avjoy","kind":"video","adapter":"kvs","desc":"成人视频","icon":"play.rectangle.fill","url":"https://cn.avjoy.ws/enter","lines":[{"url":"https://cn.avjoy.nl/enter","testUrl":"https://cn.avjoy.nl/status.html","ok":true,"ms":197.0},{"url":"https://cn.avjoy.top/enter","testUrl":"https://cn.avjoy.top/status.html","ok":true,"ms":1341.0},{"url":"https://cn.avjoy.ws/enter","testUrl":"https://cn.avjoy.ws/status.html","ok":true,"ms":2714.0}],"classes":[]},{"key":"x99_aa4a47f1","name":"SuperPorn","kind":"video","adapter":"superporn","desc":"高质量海外视频","icon":"play.rectangle.fill","url":"https://cn.superporn.ws/enter","lines":[{"url":"https://cn.superporn.me/enter","testUrl":"https://cn.superporn.me/status.html","ok":false,"ms":1628.0},{"url":"https://cn.superporn.ws/enter","testUrl":"https://cn.superporn.ws/status.html","ok":false,"ms":1733.0},{"url":"https://cn.superporn.icu/enter","testUrl":"https://cn.superporn.icu/status.html","ok":false,"ms":1857.0}],"classes":[]},{"key":"x99_73234a95","name":"亚洲素人精选","kind":"video","adapter":"91av","desc":"亚洲素人精选AV","icon":"play.rectangle.fill","url":"https://591av.ws/enter","lines":[{"url":"https://91-av.one/enter","testUrl":"https://91-av.one/status.html","ok":true,"ms":1188.0},{"url":"https://591av.sbs/enter","testUrl":"https://591av.sbs/status.html","ok":true,"ms":1778.0},{"url":"https://591av.ws/enter","testUrl":"https://591av.ws/status.html","ok":true,"ms":1910.0},{"url":"https://91-av.men/enter","testUrl":"https://91-av.men/status.html","ok":true,"ms":2140.0},{"url":"https://591av.net/enter","testUrl":"https://591av.net/status.html","ok":true,"ms":2243.0}],"classes":[]},{"key":"x99_52cd8432","name":"YesPorn","kind":"video","adapter":"yesporn","desc":"很多收费完整视频(免费)","icon":"play.rectangle.fill","url":"https://cn.yesporn.ws/enter","lines":[{"url":"https://cn.yesporn1.cc/enter","testUrl":"https://cn.yesporn1.cc/status.html","ok":true,"ms":1871.0},{"url":"https://cn.yesporn.ws/enter","testUrl":"https://cn.yesporn.ws/status.html","ok":true,"ms":2390.0}],"classes":[]},{"key":"x99_e85133d7","name":"CartoonPorno","kind":"video","adapter":"cartoon","desc":"免费精品动漫卡通视频","icon":"play.rectangle.fill","url":"https://www.cartoonporno.vip/?hl=zh","lines":[{"url":"https://www.cartoonporno.ws/?hl=zh","testUrl":"https://www.cartoonporno.ws/status.html","ok":true,"ms":1056.0},{"url":"https://www.cartoonporno.vip/?hl=zh","testUrl":"https://www.cartoonporno.vip/status.html","ok":true,"ms":1359.0},{"url":"https://www.cartoonporno.cc/?hl=zh","testUrl":"https://www.cartoonporno.cc/status.html","ok":false,"ms":752.0},{"url":"https://www.cartoonporno.top/?hl=zh","testUrl":"https://www.cartoonporno.top/status.html","ok":false,"ms":1011.0},{"url":"https://www.cartoonporno.art/?hl=zh","testUrl":"https://www.cartoonporno.art/status.html","ok":false,"ms":1055.0}],"classes":[]},{"key":"x99_9364c1e5","name":"Hentai","kind":"video","adapter":"acgmh","desc":"提供 漫画、同人志、艺术图集、游戏CG、小说插图 等","icon":"play.rectangle.fill","url":"https://cn.acgmh.art/enter","lines":[{"url":"https://cn.acgmh.icu/enter","testUrl":"https://cn.acgmh.icu/status.html","ok":true,"ms":361.0},{"url":"https://cn.acgmh.art/enter","testUrl":"https://cn.acgmh.art/status.html","ok":true,"ms":833.0},{"url":"https://cn.bato.icu/enter","testUrl":"https://cn.bato.icu/status.html","ok":true,"ms":1152.0},{"url":"https://cn.acgmh.top/enter","testUrl":"https://cn.acgmh.top/status.html","ok":true,"ms":1796.0},{"url":"https://cn.acgmh.vip/enter","testUrl":"https://cn.acgmh.vip/status.html","ok":true,"ms":1832.0},{"url":"https://cn.acgmh.sbs/enter","testUrl":"https://cn.acgmh.sbs/status.html","ok":true,"ms":4701.0}],"classes":[]},{"key":"x99_e8d1404a","name":"OKXXX","kind":"video","adapter":"okxxx","desc":"OKXXX","icon":"play.rectangle.fill","url":"https://okav.art/enter","lines":[{"url":"https://okx18.icu/enter","testUrl":"https://okx18.icu/status.html","ok":true,"ms":1076.0},{"url":"https://okxxx.win/enter","testUrl":"https://okxxx.win/status.html","ok":true,"ms":1497.0},{"url":"https://okav.art/enter","testUrl":"https://okav.art/status.html","ok":true,"ms":1708.0},{"url":"https://okx18.vip/enter","testUrl":"https://okx18.vip/status.html","ok":true,"ms":1721.0},{"url":"https://okxxxx.net/enter","testUrl":"https://okxxxx.net/status.html","ok":true,"ms":1836.0},{"url":"https://okxxx.one/enter","testUrl":"https://okxxx.one/status.html","ok":true,"ms":1876.0},{"url":"https://okxxx.ws/enter","testUrl":"https://okxxx.ws/status.html","ok":true,"ms":1934.0},{"url":"https://okxxx.men/enter","testUrl":"https://okxxx.men/status.html","ok":true,"ms":2201.0},{"url":"https://okxxx.icu/enter","testUrl":"https://okxxx.icu/status.html","ok":true,"ms":2204.0},{"url":"https://okx18.cc/enter","testUrl":"https://okx18.cc/status.html","ok":true,"ms":2911.0}],"classes":[]},{"key":"x99_86c9c1d3","name":"VJAV","kind":"video","adapter":"vjav","desc":"VJAV","icon":"play.rectangle.fill","url":"https://vjav1.sbs/enter","lines":[{"url":"https://vjav-com.icu/enter","testUrl":"https://vjav-com.icu/status.html","ok":true,"ms":434.0},{"url":"https://vjav1.top/enter","testUrl":"https://vjav1.top/status.html","ok":true,"ms":630.0},{"url":"https://vjav-com.top/enter","testUrl":"https://vjav-com.top/status.html","ok":true,"ms":805.0},{"url":"https://vjav.icu/enter","testUrl":"https://vjav.icu/status.html","ok":true,"ms":1634.0},{"url":"https://vjav1.sbs/enter","testUrl":"https://vjav1.sbs/status.html","ok":true,"ms":2048.0}],"classes":[]},{"key":"x99_30b320d4","name":"成人影片数据库","kind":"video","adapter":"javdb","desc":"不错的下片站点，巨多高清无广告资源，完全免费，下片爱好者进","icon":"play.rectangle.fill","url":"https://javdb02.com/?locale=zh","lines":[{"url":"https://javdb.nl/?locale=zh","testUrl":"https://javdb.nl/status.html","ok":true,"ms":541.0},{"url":"https://javdb1.art/?locale=zh","testUrl":"https://javdb1.art/status.html","ok":true,"ms":586.0},{"url":"https://javdb.icu/?locale=zh","testUrl":"https://javdb.icu/status.html","ok":true,"ms":728.0},{"url":"https://javdb02.com/?locale=zh","testUrl":"https://javdb02.com/status.html","ok":true,"ms":735.0},{"url":"https://javdb1.top/?locale=zh","testUrl":"https://javdb1.top/status.html","ok":true,"ms":819.0},{"url":"https://javdb.sbs/?locale=zh","testUrl":"https://javdb.sbs/status.html","ok":true,"ms":820.0},{"url":"https://javdb.pw/?locale=zh","testUrl":"https://javdb.pw/status.html","ok":true,"ms":1076.0},{"url":"https://javdb1.sbs/?locale=zh","testUrl":"https://javdb1.sbs/status.html","ok":true,"ms":1768.0},{"url":"https://javdb01.net/?locale=zh","testUrl":"https://javdb01.net/status.html","ok":true,"ms":2835.0}],"classes":[]},{"key":"x99_a5b6d0eb","name":"三级片资源，稀缺资源","kind":"video","adapter":"ptt","desc":"最新最热门的电影电视剧动漫综艺台湾剧大陆剧日剧韩剧美剧，完全免费","icon":"play.rectangle.fill","url":"https://ptt03.net/p/1","lines":[{"url":"https://ptt2.one/p/1","testUrl":"https://ptt2.one/status.html","ok":true,"ms":140.0},{"url":"https://ptt2.nl/p/1","testUrl":"https://ptt2.nl/status.html","ok":true,"ms":180.0},{"url":"https://ptt01.com/p/1","testUrl":"https://ptt01.com/status.html","ok":true,"ms":430.0},{"url":"https://ptt01.ws/p/1","testUrl":"https://ptt01.ws/status.html","ok":true,"ms":573.0},{"url":"https://ptt02.cc/p/1","testUrl":"https://ptt02.cc/status.html","ok":true,"ms":621.0},{"url":"https://ptt02.com/p/1","testUrl":"https://ptt02.com/status.html","ok":true,"ms":730.0},{"url":"https://ptt2.my/p/1","testUrl":"https://ptt2.my/status.html","ok":true,"ms":1074.0},{"url":"https://ptt03.net/p/1","testUrl":"https://ptt03.net/status.html","ok":true,"ms":1254.0},{"url":"https://ptt02.nl/p/1","testUrl":"https://ptt02.nl/status.html","ok":true,"ms":1608.0},{"url":"https://ptt2.top/p/1","testUrl":"https://ptt2.top/status.html","ok":true,"ms":1779.0},{"url":"https://ptt03.com/p/1","testUrl":"https://ptt03.com/status.html","ok":true,"ms":2254.0},{"url":"https://ptt02.net/p/1","testUrl":"https://ptt02.net/status.html","ok":true,"ms":2643.0},{"url":"https://ptt2.art/p/1","testUrl":"https://ptt2.art/status.html","ok":true,"ms":2854.0}],"classes":[]}]}')

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


_POOL = threading.local()
_COOKIES = {}


def _pool():
    pool = getattr(_POOL, "map", None)
    if pool is None:
        pool = _POOL.map = {}
    return pool


def _drop(host):
    conn = _pool().pop(host, None)
    if conn is not None:
        try:
            conn.close()
        except Exception:
            pass


def _request_once(url, timeout, hdrs):
    parts = urllib.parse.urlsplit(url)
    host = parts.netloc
    path = parts.path or "/"
    if parts.query:
        path += "?" + parts.query

    conn = _pool().get(host)
    if conn is None:
        conn = http.client.HTTPSConnection(host, timeout=timeout, context=_SSL)
        _pool()[host] = conn

    conn.request("GET", path, headers=hdrs)
    resp = conn.getresponse()
    raw = resp.read()
    try:
        for line in (resp.headers.get_all("Set-Cookie") or []):
            kv = line.split(";", 1)[0]
            if "=" in kv:
                k, v = kv.split("=", 1)
                _COOKIES.setdefault(host, {})[k.strip()] = v.strip()
    except Exception:
        pass
    if resp.will_close:
        _drop(host)
    return resp.status, raw, resp.getheader("Location"), dict(resp.getheaders())


def _http(url, timeout=HTTP_TIMEOUT, headers=None):
    """连接复用版 GET：同域名复用 TLS（keep-alive），4xx/5xx 也读 body。"""
    hdrs = {
        "User-Agent": UA,
        "Accept": "text/html,application/xhtml+xml,*/*;q=0.8",
        "Accept-Language": "zh-CN,zh;q=0.9",
        "Cache-Control": "no-cache",
        "Accept-Encoding": "gzip",
        "Connection": "keep-alive",
    }
    host0 = urllib.parse.urlsplit(url).netloc
    if _COOKIES.get(host0):
        hdrs["Cookie"] = "; ".join("%s=%s" % kv for kv in _COOKIES[host0].items())
    if headers:
        hdrs.update(headers)

    current = url
    for hop in range(3):
        for attempt in (0, 1):
            try:
                status, raw, location, _ = _request_once(current, timeout, hdrs)
                break
            except Exception:
                _drop(urllib.parse.urlsplit(current).netloc)
                if attempt == 0:
                    continue
                return None, ""

        if status in (301, 302, 303, 307, 308) and location and hop < 2:
            current = urllib.parse.urljoin(current, location)
            continue

        if raw[:2] == b"\x1f\x8b":
            try:
                import gzip as _gz
                raw = _gz.decompress(raw)
            except Exception:
                pass
        return status, raw.decode("utf-8", errors="replace")
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

        # 快照里的线路是构建时实测过的（ok 优先、按 ms 升序），直接用，不再现场探测
        ranked = [l for l in (platform.get("lines") or []) if l.get("ok")] or (platform.get("lines") or [])
        if ranked and ranked[0].get("url"):
            host = ranked[0]["url"]
            self.remember(platform, host)
            return host

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
        """相对地址绝对化（图片、详情链接）。

        注意 `//host/path` 是协议相对地址，要补 scheme；直接 lstrip("/") 会得到
        `https://本站/对方主机/...` 这种坏 URL（99漫画的 CDN 图片就是这个形态）。
        """
        if not url:
            return ""
        if url.startswith("http"):
            return url
        if url.startswith("//"):
            scheme = urllib.parse.urlsplit(self.host or "").scheme or "https"
            return scheme + ":" + url
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
        for item in self.s.cats_for(self.p):
            if item.get("type_id") == cate:
                href = item.get("href") or ""
                break
        if not href:
            href = self._scan_class(cate)
        if not href:
            # 分类 id 无效（如 "0"）时回落到该站任意可用分类，避免拼出 /vodtype/0.html
            scanned = self._scan_all_classes()
            if scanned:
                href = list(scanned.values())[0].get("href", "")
        if not href:
            href = "/vodtype/%s.html" % cate
        base = href.rsplit(".html", 1)[0]
        if "/page/" in href or "/index.php" in href:
            return self._url(base + "/page/%d.html" % int(page))
        if int(page) > 1:
            return self._url(base + "-%d.html" % int(page))
        return self._url(href)

    def _scan_all_classes(self):
        """返回该站 /enter 扫到的全部分类映射（供无分类兜底）。"""
        key = "x99dh:classes:" + self.p["key"]
        cached = self.s.cache_get(key)
        if cached and time.time() - cached.get("ts", 0) < 86400:
            return cached.get("map") or {}
        html = self.s.http(self._url("/enter")) or ""
        found = {}
        for href, label in re.findall(
            r'<a[^>]+href="([^"]*?(?:/vodtype/\d+|/index\.php/vod/type/id/\d+)[^"]*)"[^>]*>(.*?)</a>',
            html, re.S):
            match = re.search(r"(?:vodtype|vod/type/id)/(\d+)", href)
            text = re.sub(r"<[^>]+>", "", label).strip()
            if match and text and len(text) < 14:
                found.setdefault(match.group(1), {"href": href, "name": text})
        if found:
            self.s.cache_set(key, {"map": found, "ts": time.time()})
        return found

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


# ---- AES-128-CBC（18av 播放 id 是 JS 里 AES 解出来的，蜘蛛侧用纯标准库复刻）----
_AES_SBOX = (
    0x63, 0x7c, 0x77, 0x7b, 0xf2, 0x6b, 0x6f, 0xc5, 0x30, 0x01, 0x67, 0x2b, 0xfe, 0xd7, 0xab, 0x76,
    0xca, 0x82, 0xc9, 0x7d, 0xfa, 0x59, 0x47, 0xf0, 0xad, 0xd4, 0xa2, 0xaf, 0x9c, 0xa4, 0x72, 0xc0,
    0xb7, 0xfd, 0x93, 0x26, 0x36, 0x3f, 0xf7, 0xcc, 0x34, 0xa5, 0xe5, 0xf1, 0x71, 0xd8, 0x31, 0x15,
    0x04, 0xc7, 0x23, 0xc3, 0x18, 0x96, 0x05, 0x9a, 0x07, 0x12, 0x80, 0xe2, 0xeb, 0x27, 0xb2, 0x75,
    0x09, 0x83, 0x2c, 0x1a, 0x1b, 0x6e, 0x5a, 0xa0, 0x52, 0x3b, 0xd6, 0xb3, 0x29, 0xe3, 0x2f, 0x84,
    0x53, 0xd1, 0x00, 0xed, 0x20, 0xfc, 0xb1, 0x5b, 0x6a, 0xcb, 0xbe, 0x39, 0x4a, 0x4c, 0x58, 0xcf,
    0xd0, 0xef, 0xaa, 0xfb, 0x43, 0x4d, 0x33, 0x85, 0x45, 0xf9, 0x02, 0x7f, 0x50, 0x3c, 0x9f, 0xa8,
    0x51, 0xa3, 0x40, 0x8f, 0x92, 0x9d, 0x38, 0xf5, 0xbc, 0xb6, 0xda, 0x21, 0x10, 0xff, 0xf3, 0xd2,
    0xcd, 0x0c, 0x13, 0xec, 0x5f, 0x97, 0x44, 0x17, 0xc4, 0xa7, 0x7e, 0x3d, 0x64, 0x5d, 0x19, 0x73,
    0x60, 0x81, 0x4f, 0xdc, 0x22, 0x2a, 0x90, 0x88, 0x46, 0xee, 0xb8, 0x14, 0xde, 0x5e, 0x0b, 0xdb,
    0xe0, 0x32, 0x3a, 0x0a, 0x49, 0x06, 0x24, 0x5c, 0xc2, 0xd3, 0xac, 0x62, 0x91, 0x95, 0xe4, 0x79,
    0xe7, 0xc8, 0x37, 0x6d, 0x8d, 0xd5, 0x4e, 0xa9, 0x6c, 0x56, 0xf4, 0xea, 0x65, 0x7a, 0xae, 0x08,
    0xba, 0x78, 0x25, 0x2e, 0x1c, 0xa6, 0xb4, 0xc6, 0xe8, 0xdd, 0x74, 0x1f, 0x4b, 0xbd, 0x8b, 0x8a,
    0x70, 0x3e, 0xb5, 0x66, 0x48, 0x03, 0xf6, 0x0e, 0x61, 0x35, 0x57, 0xb9, 0x86, 0xc1, 0x1d, 0x9e,
    0xe1, 0xf8, 0x98, 0x11, 0x69, 0xd9, 0x8e, 0x94, 0x9b, 0x1e, 0x87, 0xe9, 0xce, 0x55, 0x28, 0xdf,
    0x8c, 0xa1, 0x89, 0x0d, 0xbf, 0xe6, 0x42, 0x68, 0x41, 0x99, 0x2d, 0x0f, 0xb0, 0x54, 0xbb, 0x16,
)
_AES_INV = [0] * 256
for _aes_i, _aes_v in enumerate(_AES_SBOX):
    _AES_INV[_aes_v] = _aes_i
_AES_RCON = (0x01, 0x02, 0x04, 0x08, 0x10, 0x20, 0x40, 0x80, 0x1B, 0x36)


def _aes_xt(a):
    return ((a << 1) ^ 0x1B) & 0xFF if a & 0x80 else (a << 1) & 0xFF


def _aes_mul(a, b):
    out = 0
    while b:
        if b & 1:
            out ^= a
        a = _aes_xt(a)
        b >>= 1
    return out


def _aes_expand(key):
    words = [list(key[i:i + 4]) for i in range(0, 16, 4)]
    for i in range(4, 44):
        tail = list(words[i - 1])
        if i % 4 == 0:
            tail = [_AES_SBOX[b] for b in tail[1:] + tail[:1]]
            tail[0] ^= _AES_RCON[i // 4 - 1]
        words.append([words[i - 4][j] ^ tail[j] for j in range(4)])
    return [sum(words[i:i + 4], []) for i in range(0, 44, 4)]


def _aes_decrypt_block(block, round_keys):
    state = [block[i] ^ round_keys[10][i] for i in range(16)]
    for rnd in range(9, -1, -1):
        state = [_AES_INV[state[((col - row) % 4) * 4 + row]]
                 for col in range(4) for row in range(4)]
        state = [state[i] ^ round_keys[rnd][i] for i in range(16)]
        if rnd == 0:
            break
        mixed = [0] * 16
        for col in range(4):
            a = state[col * 4:col * 4 + 4]
            mixed[col * 4 + 0] = _aes_mul(a[0], 14) ^ _aes_mul(a[1], 11) ^ _aes_mul(a[2], 13) ^ _aes_mul(a[3], 9)
            mixed[col * 4 + 1] = _aes_mul(a[0], 9) ^ _aes_mul(a[1], 14) ^ _aes_mul(a[2], 11) ^ _aes_mul(a[3], 13)
            mixed[col * 4 + 2] = _aes_mul(a[0], 13) ^ _aes_mul(a[1], 9) ^ _aes_mul(a[2], 14) ^ _aes_mul(a[3], 11)
            mixed[col * 4 + 3] = _aes_mul(a[0], 11) ^ _aes_mul(a[1], 13) ^ _aes_mul(a[2], 9) ^ _aes_mul(a[3], 14)
        state = mixed
    return state


def _aes_cbc_decrypt(data, key, iv):
    """PKCS7 填充的 AES-128-CBC 解密，返回 bytes。"""
    round_keys = _aes_expand(key)
    prev = list(iv)
    plain = []
    for off in range(0, len(data), 16):
        block = list(data[off:off + 16])
        plain.extend(_aes_decrypt_block(block, round_keys)[i] ^ prev[i] for i in range(16))
        prev = block
    pad = plain[-1] if plain else 0
    if 0 < pad <= 16 and len(plain) >= pad:
        plain = plain[:-pad]
    return bytes(plain)


class _Av18Adapter(_BaseAdapter):
    """18av：/zh/{cate}/all/{page}.html 列表；详情 mvarr 串（baseN 逐段异或）→
    AES-128-CBC 解出 player id → /js/player/play.php → m3u8（必须带站点 Referer）。"""

    UA_MOBILE = ("Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) "
                 "AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Mobile/15E148 Safari/604.1")
    POST_SPLIT = re.compile(r"<div class='post\b", re.I)
    CONTENT_HREF = re.compile(r"href=['\"]([^'\"]*?/zh/chinese_content/[^'\"]+)['\"]")

    def _page(self, path, referer=None):
        return self.s.http(self._url(path), referer=referer,
                           headers={"User-Agent": self.UA_MOBILE}) or ""

    @staticmethod
    def _abs_url(host, url):
        if url.startswith("//"):
            return "https:" + url
        if url.startswith("/"):
            return host + url
        return url

    @staticmethod
    def _jsint(text):
        text = (text or "").strip()
        if len(text) > 1 and text[0] == "0" and all(c in "01234567" for c in text):
            return int(text, 8)
        return int(text)

    def _player_id(self, html):
        enc = re.search(r"mvarr\['10_1'\]=\[\['[^']+','([0-9a-z]+)'", html)
        base = re.search(r"hcdeedg252=(\d+)", html)
        xor = re.search(r"hadeedg252=(\d+)", html)
        key = re.search(r"var argdeqweqweqwe = '([0-9a-f]{16})'", html)
        iv = re.search(r"var hdddedg252 = '([0-9a-f]{16})'", html)
        if not (enc and base and xor and key and iv):
            return ""
        try:
            radix = self._jsint(base.group(1))
            mask = self._jsint(xor.group(1))
            parts = enc.group(1).split(chr(radix + 97))
            b64 = "".join(chr(int(p, radix) ^ mask) for p in parts)
            plain = _aes_cbc_decrypt(base64.b64decode(b64), key.group(1).encode(), iv.group(1).encode())
            return plain.decode("utf-8", errors="replace").strip()
        except Exception:
            return ""

    def _streams(self, player_id, referer):
        page = self._page("/js/player/play.php?numresolution=1080&id="
                          + urllib.parse.quote(player_id), referer=referer)
        found = re.findall(r"\{\s*src:\s*'([^']+)'[^}]*?size:\s*(\d+)", page)
        streams = []
        for src, size in found:
            streams.append((int(size), self._abs_url(self.host, src)))
        streams.sort(reverse=True)
        return streams

    def list(self, cate, page):
        slug = cate if cate and not str(cate).isdigit() else "chinese_list"
        page = max(1, int(page))
        html = self._page("/zh/%s/all/%d.html" % (slug, page))
        videos = []
        for block in self.POST_SPLIT.split(html)[1:]:
            href = self.CONTENT_HREF.search(block)
            if not href:
                continue
            url = self._abs_url(self.host, href.group(1))
            title = re.search(r"<h3[^>]*>.*?<a[^>]*>(.*?)</a>", block, re.S)
            name = re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", title.group(1))).strip() if title else ""
            img = re.search(r"<img[^>]+src=['\"]([^'\"]+)['\"]", block)
            meta = re.search(r"<div class='meta'>(.*?)</div>", block, re.S)
            videos.append({
                "vod_id": self.p["key"] + "::" + url,
                "vod_name": name or url,
                "vod_pic": self._abs_url(self.host, img.group(1)) if img else "",
                "vod_remarks": re.sub(r"<[^>]+>", "", meta.group(1)).strip() if meta else "",
            })
        total = 0
        for num in re.findall(r"/all/(\d+)\.html", html):
            total = max(total, int(num))
        return {"list": videos, "page": page, "pagecount": total or page + 1}

    def detail(self, vid):
        url = self._abs_url(self.host, vid)
        html = self._page(url)
        title = ""
        found = re.search(r"<h1[^>]*>(.*?)</h1>", html, re.S) or \
            re.search(r"<title[^>]*>(.*?)</title>", html, re.S)
        if found:
            title = re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", found.group(1))).strip()
        pic = re.search(r'"thumbnailUrl"\s*:\s*"([^"]+)"', html)
        player_id = self._player_id(html)
        streams = self._streams(player_id, url) if player_id else []
        episodes = ["%dp$%s::%s" % (size, self.p["key"], src) for size, src in streams]
        vod = {
            "vod_id": self.p["key"] + "::" + url,
            "vod_name": title or vid,
            "vod_pic": pic.group(1) if pic else "",
            "vod_content": "player:" + player_id if player_id else "",
            "vod_play_from": "18av",
            "vod_play_url": "#".join(episodes) if episodes else "正片$%s::%s" % (self.p["key"], url),
        }
        return {"list": [vod]}

    def play(self, flag, url):
        return {"parse": "0", "url": url,
                "header": {"User-Agent": self.UA_MOBILE, "Referer": self.host + "/"}}


class _JableAdapter(_BaseAdapter):
    """Jable：/latest-updates/{page}/ 列表；详情页 var hlsUrl 直接给 m3u8（302 到 CDN）。"""

    UA_MOBILE = ("Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) "
                 "AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Mobile/15E148 Safari/604.1")
    CARD_RE = re.compile(
        r'<h6 class="title"><a href="([^"]+)">(.*?)</a></h6>', re.S)

    def _page(self, path, referer=None):
        return self.s.http(self._url(path), referer=referer,
                           headers={"User-Agent": self.UA_MOBILE}) or ""

    def categories(self):
        """从 /categories/ 取分类（slug）与标签，合并成 type_id=slug。"""
        html = self._page("/categories/")
        cats, seen = [], set()
        for m in re.finditer(
                r'href="(?:https?://[^"]+)?/categories/([a-z0-9\-]+)/?"[^>]*>(.*?)</a>',
                html, re.S):
            slug = m.group(1)
            if slug in seen:
                continue
            text = re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", m.group(2))).strip()
            if text and len(text) < 24:
                seen.add(slug)
                cats.append({"type_id": slug, "type_name": text[:24]})
        for m in re.finditer(
                r'href="(?:https?://[^"]+)?/tags/([a-z0-9\-]+)/?"[^>]*>(.*?)</a>',
                html, re.S):
            slug = m.group(1)
            if slug in seen or len(cats) >= 60:
                continue
            text = re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", m.group(2))).strip()
            if text and len(text) < 24:
                seen.add(slug)
                cats.append({"type_id": slug, "type_name": text[:24]})
        return cats[:60] or (self.p.get("classes") or [])

    def list(self, cate, page):
        page = max(1, int(page))
        cid = str(cate or "").strip()
        if cid and not cid.isdigit():
            path = "/categories/%s/%d/" % (cid, page)
            html = self._page(path, referer=self.host + "/categories/")
        else:
            html = self._page("/latest-updates/%d/" % page)
        videos, seen = [], set()
        for href, inner in self.CARD_RE.findall(html):
            if href in seen:
                continue
            seen.add(href)
            name = re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", inner)).strip()
            img = re.search(r'<img[^>]+data-src="([^"]+)"', html[max(0, html.find(href) - 800):html.find(href) + 100])
            label = re.search(r'<span class="label">([^<]+)</span>',
                              html[max(0, html.find(href) - 800):html.find(href) + 100])
            videos.append({
                "vod_id": self.p["key"] + "::" + self._abs(href),
                "vod_name": name or href,
                "vod_pic": self._abs(img.group(1)) if img else "",
                "vod_remarks": label.group(1).strip() if label else "",
            })
        total = 0
        for num in re.findall(r"/latest-updates/(\d+)/", html):
            total = max(total, int(num))
        return {"list": videos, "page": page, "pagecount": total or page + 1}

    def detail(self, vid):
        url = self._abs(vid)
        html = self._page(url)
        title = ""
        found = re.search(r"<title[^>]*>(.*?)</title>", html, re.S)
        if found:
            title = re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", found.group(1))).strip()
            title = re.split(r"\s*-\s*jable", title)[0]
        pic = re.search(r'<video\b[^>]*poster="([^"]+)"', html)
        hls = re.search(r"var hlsUrl = '([^']+)'", html)
        vod = {
            "vod_id": self.p["key"] + "::" + url,
            "vod_name": title or vid,
            "vod_pic": self._abs(pic.group(1)) if pic else "",
            "vod_content": "",
            "vod_play_from": "直连",
            "vod_play_url": "正片$%s::%s" % (self.p["key"], self._abs(hls.group(1)) if hls else url),
        }
        return {"list": [vod]}

    def play(self, flag, url):
        return {"parse": "0", "url": url,
                "header": {"User-Agent": self.UA_MOBILE, "Referer": self.host + "/"}}


class _RouAdapter(_BaseAdapter):
    """肉视频：/home SSR 嵌视频记录；详情页 ev:{d,k} 解出 /api/hls/{id}（302 到签名 CDN）。

    解码：base64(d) 每个字节 -k，得到 JSON {videoUrl, thumbVTTUrl}。
    """

    UA_MOBILE = ("Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) "
                 "AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Mobile/15E148 Safari/604.1")
    REC_RE = re.compile(r"\{id:\"cmw[0-9a-z]+\"")

    def _page(self, path, referer=None):
        return self.s.http(self._url(path), referer=referer,
                           headers={"User-Agent": self.UA_MOBILE}) or ""

    @staticmethod
    def _match_obj(text, start):
        depth = 0
        i = start
        n = len(text)
        in_str = False
        while i < n:
            c = text[i]
            if in_str:
                if c == "\\":
                    i += 2
                    continue
                if c == '"':
                    in_str = False
            elif c == '"':
                in_str = True
            elif c == "{":
                depth += 1
            elif c == "}":
                depth -= 1
                if depth == 0:
                    return i
            i += 1
        return -1

    @staticmethod
    def _ev(html):
        """返回 (videoUrl, thumbVTTUrl) 或 (None, None)。"""
        m = re.search(r"ev:\$R\[\d+\]=\{d:\"([^\"]+)\",k:(-?\d+)\}", html)
        if not m:
            return None, None
        try:
            blob = base64.b64decode(m.group(1))
            out = bytes((b - int(m.group(2))) & 0xFF for b in blob).decode("utf-8", "replace")
            obj = json.loads(out)
            return obj.get("videoUrl") or "", obj.get("thumbVTTUrl") or ""
        except Exception:
            return None, None

    def _records(self, html):
        out, seen = [], set()
        for m in self.REC_RE.finditer(html):
            vid_id = m.group(0)[5:-1]
            if vid_id in seen:
                continue
            end = self._match_obj(html, m.start())
            if end < 0:
                continue
            body = html[m.start():end + 1]
            if "sources:" not in body:
                continue  # 短剧/系列记录没有 sources，走 /s/ 系列页，先不接
            name = re.search(r"nameZh:\"(.*?)\"", body) or re.search(r"name:\"(.*?)\"", body)
            cover = re.search(r"coverImageUrl:\"(.*?)\"", body)
            ext = re.search(r"vid:\"(.*?)\"", body)
            dur = re.search(r"duration:([\d.]+)", body)
            seen.add(vid_id)
            out.append({
                "id": vid_id,
                "name": re.sub(r"\s+", " ", name.group(1)) if name else vid_id,
                "cover": cover.group(1) if cover else "",
                "vid": ext.group(1) if ext else "",
                "duration": float(dur.group(1)) if dur else 0,
            })
        return out

    def categories(self):
        """从 /cat 页取标签（type_id = "/t/{urlencoded}"，list 直接用该路径）。"""
        html = self._page("/cat")
        cats, seen = [], set()
        for m in re.finditer(r'href="(/t/[^"?#]+)"[^>]*>\s*([^<]{1,20})\s*<', html, re.S):
            path, name = m.group(1), m.group(2).strip()
            if path in seen or not name or len(name) > 12:
                continue
            # 排除把 query 拼进 href 的脏值
            if "?" in path or "&" in path:
                continue
            seen.add(path)
            cats.append({"type_id": path, "type_name": name})
        return cats[:60] or (self.p.get("classes") or [])

    def list(self, cate, page):
        page = max(1, int(page))
        cid = str(cate or "").strip()
        if cid.startswith("/t/"):
            html = self._page(cid, referer=self.host + "/cat")
        else:
            html = self._page("/home" if page == 1 else "/home?page=%d" % page)
        videos = []
        for rec in self._records(html):
            minutes = int(rec["duration"] // 60) if rec["duration"] else 0
            videos.append({
                "vod_id": self.p["key"] + "::" + self._abs("/v/" + rec["id"]),
                "vod_name": rec["name"],
                "vod_pic": self._abs(rec["cover"]),
                "vod_remarks": rec["vid"] or ("%d 分" % minutes if minutes else ""),
            })
        return {"list": videos, "page": page, "pagecount": page + 1}

    def detail(self, vid):
        url = self._abs(vid)
        html = self._page(url)
        title, pic = vid, ""
        m = re.search(r"video:\$R\[\d+\]=\{id:\"cmw[0-9a-z]+\"", html)
        if m:
            end = self._match_obj(html, m.start())
            body = html[m.start():end + 1]
            name = re.search(r"nameZh:\"(.*?)\"", body) or re.search(r"name:\"(.*?)\"", body)
            if name:
                title = re.sub(r"\s+", " ", name.group(1))
            cover = re.search(r"coverImageUrl:\"(.*?)\"", body)
            if cover:
                pic = cover.group(1)
        video_url, _ = self._ev(html)
        target = self._abs(video_url) if video_url else url
        vod = {
            "vod_id": self.p["key"] + "::" + url,
            "vod_name": title,
            "vod_pic": self._abs(pic),
            "vod_content": "",
            "vod_play_from": "直连",
            "vod_play_url": "正片$%s::%s" % (self.p["key"], target),
        }
        return {"list": [vod]}

    def play(self, flag, url):
        return {"parse": "0", "url": url,
                "header": {"User-Agent": self.UA_MOBILE, "Referer": self.host + "/"}}


class _XhamsterAdapter(_BaseAdapter):
    """xhamster：/enter 拿 cookie 后纯 HTML 列表；详情页 window 数据里的
    mp4/hls 签名直链；正片取 hls 主播放列表（_TPL_.h264.mp4.m3u8，比 AV1 兼容性好）。"""

    UA_DESKTOP = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                  "(KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36")
    CARD_RE = re.compile(
        r'<a class="video-thumb__image-container[^"]*"[^>]*href="([^"]+)"[^>]*aria-label="([^"]+)"',
        re.S)
    IMG_RE = re.compile(r'<img class="tnum-[^"]* thumb-image-container__image" src="([^"]+)"')
    SHELL_RE = re.compile(r"继续访问|Continue|Just a moment", re.I)

    def _page(self, path, referer=None):
        """带 cookie 访问；偶发反爬壳（<3KB）时先过 /enter 拿 cookie 再重试。"""
        for attempt in range(2):
            html = self.s.http(self._url(path), referer=referer,
                               headers={"User-Agent": self.UA_DESKTOP}) or ""
            if len(html) > 4000 or not self.SHELL_RE.search(html):
                return html
            self.s.http(self._url("/enter"), headers={"User-Agent": self.UA_DESKTOP}) or ""
        return html

    def categories(self):
        """从 /categories 页取分类（slug 作 type_id，list 时走 /categories/{slug}）。"""
        html = self._page("/categories")
        cats, seen = [], set()
        for m in re.finditer(r'href="[^"]*/categories/([a-z0-9\-]+)"[^>]*>(.*?)</a>', html, re.S):
            slug = m.group(1)
            if slug in seen:
                continue
            seen.add(slug)
            text = re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", m.group(2))).strip()
            if text and 1 < len(text) < 20:
                cats.append({"type_id": slug, "type_name": text[:20]})
        return cats[:60] or (self.p.get("classes") or [])

    def list(self, cate, page):
        page = max(1, int(page))
        cid = str(cate or "").strip()
        if cid and not cid.isdigit():
            html = self._page("/categories/" + cid + ("/%d" % page if page > 1 else ""),
                              referer=self.host + "/categories")
        else:
            html = self._page("/" if page <= 1 else "/%d" % page)
        anchors = self.CARD_RE.findall(html)
        imgs = self.IMG_RE.findall(html)
        videos, seen = [], set()
        for i, (href, label) in enumerate(anchors):
            if href in seen:
                continue
            seen.add(href)
            name = re.sub(r"\s+", " ", label).strip()
            pic = imgs[i] if i < len(imgs) else ""
            videos.append({
                "vod_id": self.p["key"] + "::" + self._abs(href),
                "vod_name": name or href,
                "vod_pic": self._abs(pic),
                "vod_remarks": "",
            })
        return {"list": videos, "page": page, "pagecount": page + 1}

    def detail(self, vid):
        url = self._abs(vid)
        html = self._page(url, referer=self.host + "/")
        title = ""
        m = re.search(r'"videoTitle":"((?:[^"\\]|\\.)*)"', html)
        if m:
            try:
                title = json.loads('"%s"' % m.group(1))
            except Exception:
                title = m.group(1)
        if not title:
            m = re.search(r'property="og:title" content="([^"]+)"', html)
            if m:
                title = m.group(1)
        if not title:
            m = re.search(r"<title[^>]*>(.*?)</title>", html, re.S)
            if m:
                title = re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", m.group(1))).strip()
        pic = ""
        m = re.search(r'"videoImage":"((?:[^"\\]|\\.)*)"', html)
        if m:
            try:
                pic = json.loads('"%s"' % m.group(1))
            except Exception:
                pic = m.group(1)
        if not pic:
            m = re.search(r'property="og:image" content="([^"]+)"', html)
            if m:
                pic = m.group(1)
        master = ""
        m = re.search(r'<link rel="preload" href="(https?:[^"]+?_TPL_\.av1\.mp4\.m3u8)"', html)
        if m:
            master = m.group(1).replace("\\/", "/").replace("_TPL_.av1.mp4.m3u8", "_TPL_.h264.mp4.m3u8")
        vod = {
            "vod_id": self.p["key"] + "::" + url,
            "vod_name": title or vid,
            "vod_pic": pic,
            "vod_content": "",
            "vod_play_from": "直连",
            "vod_play_url": "正片$%s::%s" % (self.p["key"], master),
        }
        return {"list": [vod]}

    def play(self, flag, url):
        return {"parse": "0", "url": url,
                "header": {"User-Agent": self.UA_DESKTOP, "Referer": self.host + "/"}}


class _VjavAdapter(_BaseAdapter):
    """VJAV：JSON API（列表/详情/videofile），video_url 是西里尔同形字 base64。
    解码：АВСЕМ→AB CEM、.→+、,→/、~→空，再补 =。"""

    UA_DESKTOP = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                  "(KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36")
    B64MAP = {"А": "A", "В": "B", "С": "C", "Е": "E", "М": "M", ".": "+", ",": "/", "~": ""}

    def _page(self, path, referer=None):
        for attempt in range(2):
            html = self.s.http(self._url(path), referer=referer,
                               headers={"User-Agent": self.UA_DESKTOP,
                                        "Accept": "application/json"}) or ""
            if len(html) > 200:
                return html
        return html

    def _json(self, path, referer=None):
        html = self._page(path, referer=referer)
        try:
            return json.loads(html)
        except Exception:
            return None

    @staticmethod
    def _decode_b64(raw):
        s = "".join(_VjavAdapter.B64MAP.get(c, c) for c in raw or "")
        s += "=" * ((4 - len(s) % 4) % 4)
        try:
            return base64.b64decode(s).decode("utf-8", "replace")
        except Exception:
            return ""

    def categories(self):
        """从列表项的 categories_data（"slug|id|名称,slug|id|名称"）聚合出全部分类。"""
        path = "/api/json/videos2/86400/str/latest-updates/60/..1.all...json"
        data = self._json(path, referer=self.host + "/")
        seen, cats = set(), []
        for it in (data or {}).get("videos") or []:
            raw = str(it.get("categories_data") or "")
            for part in raw.split(","):
                bits = part.split("|")
                if len(bits) < 3:
                    continue
                slug, cid, name = bits[0].strip(), bits[1].strip(), bits[2].strip()
                if not cid or not cid.isdigit() or cid in seen or not name:
                    continue
                # 名称是纯数字的是编码类标签（如 "69"），不是内容分类
                if name.isdigit():
                    continue
                seen.add(cid)
                cats.append({"type_id": cid, "type_name": name[:24]})
        cats.sort(key=lambda c: c["type_name"])
        return cats[:60] or (self.p.get("classes") or [])

    def list(self, cate, page):
        page = max(1, int(page))
        cid = str(cate or "").strip()
        if cid and cid.isdigit():
            # 路径第 7 段是 categories 筛选：…/..{page}.all.{cid}..json
            path = ("/api/json/videos2/86400/str/latest-updates/60/"
                    "..%d.all.%s..json" % (page, cid))
        else:
            path = "/api/json/videos2/86400/str/latest-updates/60/..%d.all...json" % page
        data = self._json(path, referer=self.host + "/")
        videos = []
        for it in (data or {}).get("videos") or []:
            vid = str(it.get("video_id") or "")
            if not vid:
                continue
            title = it.get("title") or it.get("title_jp") or vid
            videos.append({
                "vod_id": self.p["key"] + "::" + vid,
                "vod_name": str(title)[:120],
                "vod_pic": self._abs(it.get("thumb") or ""),
                "vod_remarks": str(it.get("duration") or ""),
            })
        total = int((data or {}).get("pages") or 0)
        return {"list": videos, "page": page, "pagecount": total or page + 1}

    def detail(self, vid):
        vid = vid.split("::")[-1].strip("/")
        if not vid.isdigit():
            return {"list": []}
        vid_i = int(vid)
        shard = "%d/%d" % (1000000 * (vid_i // 1000000), 1000 * (vid_i // 1000))
        data = self._json("/api/json/video/86400/%s/%s.json" % (shard, vid), referer=self.host + "/")
        v = (data or {}).get("video") or {}
        title = str(v.get("title") or v.get("title_jp") or vid)
        pic = self._abs(v.get("thumb") or "")
        vod = {
            "vod_id": self.p["key"] + "::" + vid,
            "vod_name": title[:120],
            "vod_pic": pic,
            "vod_content": "",
            "vod_play_from": "直连",
            "vod_play_url": "正片$%s::%s" % (self.p["key"], vid),
        }
        return {"list": [vod]}

    def play(self, flag, url):
        data = self._json("/api/videofile.php?video_id=%s&lifetime=8640000" % url,
                          referer=self.host + "/")
        target = ""
        for item in (data or []) if isinstance(data, list) else []:
            raw = item.get("video_url") or ""
            path = self._decode_b64(raw)
            if path.startswith("/"):
                target = self._abs(path)
                break
        return {"parse": "0", "url": target,
                "header": {"User-Agent": self.UA_DESKTOP, "Referer": self.host + "/"}}


class _91avAdapter(_BaseAdapter):
    """亚洲素人精选(91-av/591av)：/pp1/ 首页 card-video 卡片；详情 /v/{slug}/ 页内 jmpres m3u8。
    取流需 Referer + gzip（无 Referer 返回 143 字节 tip.ts 提示页）。"""

    UA_DESKTOP = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                  "(KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36")
    CARD_RE = re.compile(
        r'<div class="item card-video[^"]*"[^>]*>.*?<a href="([^"]+/v/[a-z0-9\-]+/)"[^>]*>.*?data-src="([^"]+)"[^>]*>.*?<figcaption[^>]*>([^<]+)</figcaption>.*?<h4 class="card-video__title">\s*<a[^>]*>(.*?)</a>',
        re.S)

    def _page(self, path, referer=None):
        return self.s.http(self._url(path), referer=referer,
                           headers={"User-Agent": self.UA_DESKTOP}) or ""

    def categories(self):
        """从 /categories/ 取分类（slug 作 type_id，list 走 /categories/{slug}/）。"""
        html = self._page("/categories/")
        cats, seen = [], set()
        for m in re.finditer(
                r'href="[^"]*/categories/([a-z0-9\-]+)/"[^>]*>.*?card-cat-v2__title[^>]*>(.*?)<',
                html, re.S):
            slug, name = m.group(1), re.sub(r"\s+", " ", m.group(2)).strip()
            if slug in seen or not name:
                continue
            seen.add(slug)
            cats.append({"type_id": slug, "type_name": name[:20]})
        return cats[:60] or (self.p.get("classes") or [])

    def list(self, cate, page):
        page = max(1, int(page))
        cid = str(cate or "").strip()
        if cid and not cid.isdigit():
            path = "/categories/%s/" % cid
            if page > 1:
                path = "/categories/%s/%d/" % (cid, page)
            html = self._page(path, referer=self.host + "/")
        else:
            html = self._page("/pp1/" if page == 1 else "/pp1/%d/" % page)
        videos, seen = [], set()
        for href, img, dur, title in self.CARD_RE.findall(html):
            if href in seen:
                continue
            seen.add(href)
            videos.append({
                "vod_id": self.p["key"] + "::" + self._abs(href),
                "vod_name": re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", title)).strip(),
                "vod_pic": self._abs(img),
                "vod_remarks": dur.strip(),
            })
        return {"list": videos, "page": page, "pagecount": page + 1}

    def detail(self, vid):
        url = self._abs(vid)
        html = self._page(url, referer=self.host + "/")
        title = ""
        m = re.search(r"<title[^>]*>(.*?)</title>", html, re.S)
        if m:
            title = re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", m.group(1))).strip()
            title = re.split(r"\s*-\s*PPP\.Porn", title)[0]
        hls = ""
        for u in re.findall(r'https?://[^"\'\s<>]+\.m3u8', html):
            if "preview.m3u8" not in u and ".jpg" not in u:
                hls = u
                break
        vod = {
            "vod_id": self.p["key"] + "::" + url,
            "vod_name": title or vid,
            "vod_pic": "",
            "vod_content": "",
            "vod_play_from": "直连",
            "vod_play_url": "正片$%s::%s" % (self.p["key"], hls or url),
        }
        return {"list": [vod]}

    def play(self, flag, url):
        return {"parse": "0", "url": url,
                "header": {"User-Agent": self.UA_DESKTOP, "Referer": self.host + "/"}}


class _YespornAdapter(_BaseAdapter):
    """YesPorn：/enter 首页 /video/{id}/{slug}/ 卡片；详情页 kt_player 配置里 video_url/
    video_alt_url2 给 get_file mp4 直链（1080p/720p/trim）。CDN 可能挡（返回 gif），待复验。"""

    UA_DESKTOP = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                  "(KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36")
    CARD_RE = re.compile(
        r'<div class="thumb[^"]*"[^>]*>\s*<a href="([^"]+/video/\d+/[a-z0-9\-]+/)"[^>]*title="([^"]*)"[^>]*>.*?<img[^>]+src="([^"]+)"',
        re.S)

    def _page(self, path, referer=None):
        return self.s.http(self._url(path), referer=referer,
                           headers={"User-Agent": self.UA_DESKTOP}) or ""

    def categories(self):
        """从 /categories/ 取分类（<a href="…/categories/{slug}/" title="名称">）。"""
        html = self._page("/categories/")
        cats, seen = [], set()
        for m in re.finditer(
                r'href="(?:https?://[^"]+)?/categories/([a-z0-9\-]+)/"[^>]*title="([^"]{1,24})"',
                html, re.S):
            slug, name = m.group(1), m.group(2).strip()
            if slug in seen or not name:
                continue
            seen.add(slug)
            cats.append({"type_id": slug, "type_name": name[:24]})
            if len(cats) >= 60:
                break
        return cats or (self.p.get("classes") or [])

    def list(self, cate, page):
        page = max(1, int(page))
        cid = str(cate or "").strip()
        if cid and not cid.isdigit():
            path = "/categories/%s/" % cid
            if page > 1:
                path += "%d/" % page
            html = self._page(path, referer=self.host + "/categories/")
        else:
            html = self._page("/enter")
        videos, seen = [], set()
        for href, title, img in self.CARD_RE.findall(html):
            if href in seen:
                continue
            seen.add(href)
            videos.append({
                "vod_id": self.p["key"] + "::" + self._abs(href),
                "vod_name": title.strip(),
                "vod_pic": self._abs(img),
                "vod_remarks": "",
            })
        return {"list": videos, "page": page, "pagecount": page + 1}

    def detail(self, vid):
        url = self._abs(vid)
        html = self._page(url, referer=self.host + "/")
        title = ""
        m = re.search(r"<title[^>]*>(.*?)</title>", html, re.S)
        if m:
            title = re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", m.group(1))).strip()
        def grab(key):
            m = re.search(re.escape(key) + r":\s*'function/0/([^']+)'", html)
            return m.group(1) if m else ""
        mp4 = grab("video_alt_url2") or grab("video_alt_url") or grab("video_url")
        vod = {
            "vod_id": self.p["key"] + "::" + url,
            "vod_name": title or vid,
            "vod_pic": "",
            "vod_content": "",
            "vod_play_from": "直连",
            "vod_play_url": "正片$%s::%s" % (self.p["key"], mp4 or url),
        }
        return {"list": [vod]}

    def play(self, flag, url):
        return {"parse": "0", "url": url,
                "header": {"User-Agent": self.UA_DESKTOP, "Referer": self.host + "/"}}


class _CartoonAdapter(_BaseAdapter):
    """CartoonPorno：/videos?hl=zh 列表 lnk 卡片（data-s/data-i/data-u 拼详情 URL）；
    详情页第一个 jmpres 签名 mp4 即正片（其余是推荐预览 p320-180）。
    取流需 Referer（根即可）+ Range。"""

    UA_DESKTOP = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                  "(KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36")
    CARD_RE = re.compile(
        r"<a class='[^']*lnk[^']*' data-s='/v/' data-i='(\d+)' data-u='([^']+)'[^>]*title=\"([^\"]+)\"[^>]*>.*?<img[^>]+data-src=\"([^\"]+)\"",
        re.S)

    def _page(self, path, referer=None):
        return self.s.http(self._url(path), referer=referer,
                           headers={"User-Agent": self.UA_DESKTOP}) or ""

    def categories(self):
        """从 /categories 取分类（type_id = "{id}/{slug}"，list 走 /categories/{id}/{slug}）。"""
        html = self._page("/categories?hl=zh")
        cats, seen = [], set()
        for m in re.finditer(
                r'href="(?:https?://[^"]+)?/categories/(\d+)/([a-z0-9\-]+)\?hl=zh"[^>]*>\s*([^<]{1,24})',
                html, re.S):
            cid, slug, name = m.group(1), m.group(2), m.group(3).strip()
            key = "%s/%s" % (cid, slug)
            if key in seen or not name:
                continue
            seen.add(key)
            cats.append({"type_id": key, "type_name": name[:24]})
        return cats[:80] or (self.p.get("classes") or [])

    def list(self, cate, page):
        page = max(1, int(page))
        cid = str(cate or "").strip()
        if cid and "/" in cid:
            html = self._page("/categories/%s?hl=zh" % cid,
                              referer=self.host + "/categories?hl=zh")
        else:
            html = self._page("/videos?hl=zh")
        videos, seen = [], set()
        for vid, slug, title, img in self.CARD_RE.findall(html):
            href = "/v/%s%s?hl=zh" % (vid, slug)
            if href in seen:
                continue
            seen.add(href)
            videos.append({
                "vod_id": self.p["key"] + "::" + self._abs(href),
                "vod_name": title.strip(),
                "vod_pic": self._abs(img),
                "vod_remarks": "",
            })
        return {"list": videos, "page": page, "pagecount": page + 1}

    def detail(self, vid):
        url = self._abs(vid)
        html = self._page(url, referer=self.host + "/")
        title = ""
        m = re.search(r"<title[^>]*>(.*?)</title>", html, re.S)
        if m:
            title = re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", m.group(1))).strip()
        mp4 = ""
        for u in re.findall(r'https?://[^"\'\s<>]+\.mp4[^"\'\s<>]*', html):
            if "jmpres" in u and "p320-180" not in u:
                mp4 = u
                break
        vod = {
            "vod_id": self.p["key"] + "::" + url,
            "vod_name": title or vid,
            "vod_pic": "",
            "vod_content": "",
            "vod_play_from": "直连",
            "vod_play_url": "正片$%s::%s" % (self.p["key"], mp4 or url),
        }
        return {"list": [vod]}

    def play(self, flag, url):
        return {"parse": "0", "url": url,
                "header": {"User-Agent": self.UA_DESKTOP, "Referer": self.host + "/"}}


class _OkxxxAdapter(_BaseAdapter):
    """OKXXX.MEN：/enter 列表 /video/{id}/ 卡片；详情页 get_file mp4 直链
    （实际返回 master m3u8，多画质 720p/360p/full）。"""

    UA_DESKTOP = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                  "(KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36")
    CARD_RE = re.compile(
        r'<a href="(/video/\d+/)"[^>]*title="([^"]*)"[^>]*>.*?<img[^>]+data-original="([^"]+)"',
        re.S)

    def _page(self, path, referer=None):
        return self.s.http(self._url(path), referer=referer,
                           headers={"User-Agent": self.UA_DESKTOP}) or ""

    def categories(self):
        """从首页取片商频道（/sites/{slug}/），比 1.7MB 的 /tags/ 轻得多。"""
        html = self._page("/enter")
        cats, seen = [], set()
        for m in re.finditer(r'href="(/sites/[a-z0-9\-]+/)"[^>]*>\s*(?:<[^>]+>\s*)*([^<]{1,26})',
                             html, re.S):
            path, name = m.group(1), re.sub(r"\s+", " ", m.group(2)).strip()
            if path in seen or not name:
                continue
            seen.add(path)
            cats.append({"type_id": path, "type_name": name[:26]})
        return cats[:60] or (self.p.get("classes") or [])

    def list(self, cate, page):
        page = max(1, int(page))
        cid = str(cate or "").strip()
        if cid.startswith("/"):
            html = self._page(cid, referer=self.host + "/")
        else:
            html = self._page("/enter")
        videos, seen = [], set()
        for href, title, img in self.CARD_RE.findall(html):
            if href in seen:
                continue
            seen.add(href)
            videos.append({
                "vod_id": self.p["key"] + "::" + self._abs(href),
                "vod_name": title.strip()[:120],
                "vod_pic": self._abs(img),
                "vod_remarks": "",
            })
        return {"list": videos, "page": page, "pagecount": page + 1}

    def detail(self, vid):
        url = self._abs(vid)
        html = self._page(url, referer=self.host + "/")
        title = ""
        m = re.search(r"<title[^>]*>(.*?)</title>", html, re.S)
        if m:
            title = re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", m.group(1))).strip()
            title = re.split(r"\s*-\s*OKXXX", title)[0]
        mp4 = ""
        links = list(dict.fromkeys(
            re.findall(r'https?://[^"\'\s<>]+?get_file[^"\'\s<>]*?\.mp4[^"\'\s<>]*', html)))
        for u in links:
            if "_preview" in u:
                continue
            if "_720p" in u:
                mp4 = u
                break
        if not mp4:
            for u in links:
                if "_preview" not in u:
                    mp4 = u
                    break
        vod = {
            "vod_id": self.p["key"] + "::" + url,
            "vod_name": title or vid,
            "vod_pic": "",
            "vod_content": "",
            "vod_play_from": "直连",
            "vod_play_url": "正片$%s::%s" % (self.p["key"], mp4 or url),
        }
        return {"list": [vod]}

    def play(self, flag, url):
        return {"parse": "0", "url": url,
                "header": {"User-Agent": self.UA_DESKTOP, "Referer": self.host + "/"}}


class _PttAdapter(_BaseAdapter):
    """三级片资源(ptt2.one)：/p/{page} 列表 /{id} 卡片；详情页 JSON-LD
    VideoObject.contentUrl 给 m3u8 直链（v.gsuus.com，无 Referer 也能拉）。"""

    UA_DESKTOP = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                  "(KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36")
    CARD_RE = re.compile(
        r'<a class="visited" href="/(\d+)"[^>]*>\s*<img[^>]+(?:src|data-src)="([^"]+)"'
        r'.*?<a class="visited" href="/\1"[^>]*>\s*(?:<i[^>]*></i>)?\s*([^<]+)</a>',
        re.S)

    def _page(self, path, referer=None):
        return self.s.http(self._url(path), referer=referer,
                           headers={"User-Agent": self.UA_DESKTOP}) or ""

    def categories(self):
        """从 /p/{n} 页取类型导航（/p/{n}/c/{cid}）。"""
        html = self._page("/p/1")
        cats, seen = [], set()
        for m in re.finditer(r'href="/p/\d+/c/(\d+)"[^>]*>\s*([^<]{1,12})', html, re.S):
            cid, name = m.group(1), re.sub(r"\s+", " ", m.group(2)).strip()
            if cid in seen or not name or name == "全部":
                continue
            seen.add(cid)
            cats.append({"type_id": cid, "type_name": name[:12]})
        return cats or (self.p.get("classes") or [])

    def list(self, cate, page):
        page = max(1, int(page))
        cid = str(cate or "").strip()
        if cid.isdigit() and cid != "0":
            html = self._page("/p/%d/c/%s" % (page, cid), referer=self.host + "/p/1")
        else:
            html = self._page("/p/%d" % page)
        videos, seen = [], set()
        for vid, img, title in self.CARD_RE.findall(html):
            if vid in seen:
                continue
            seen.add(vid)
            videos.append({
                "vod_id": self.p["key"] + "::" + vid,
                "vod_name": title.strip()[:120],
                "vod_pic": self._abs(img),
                "vod_remarks": "",
            })
        if not videos:
            for vid in list(dict.fromkeys(re.findall(r'<a class="visited" href="/(\d+)"', html))):
                videos.append({"vod_id": self.p["key"] + "::" + vid,
                               "vod_name": vid, "vod_pic": "", "vod_remarks": ""})
        return {"list": videos, "page": page, "pagecount": page + 1}

    def detail(self, vid):
        vid = vid.strip("/").split("/")[0]
        url = self._url("/" + vid)
        html = self._page("/" + vid, referer=self.host + "/")
        title = ""
        m = re.search(r"<title[^>]*>(.*?)</title>", html, re.S)
        if m:
            title = re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", m.group(1))).strip()
            title = re.split(r"\s*-\s*线上看", title)[0]
        pic = ""
        m = re.search(r'"thumbnailUrl"\s*:\s*"([^"]+)"', html)
        if m:
            pic = m.group(1).replace("\\/", "/")
        hls = ""
        m = re.search(r'"contentUrl"\s*:\s*"([^"]+)"', html)
        if m:
            hls = m.group(1).replace("\\/", "/")
        if not hls:
            m = re.search(r'https?://[^"\'\s<>]+\.m3u8[^"\'\s<>]*', html)
            if m:
                hls = m.group(0)
        vod = {
            "vod_id": self.p["key"] + "::" + vid,
            "vod_name": title or vid,
            "vod_pic": pic,
            "vod_content": "",
            "vod_play_from": "直连",
            "vod_play_url": "正片$%s::%s" % (self.p["key"], hls or url),
        }
        return {"list": [vod]}

    def play(self, flag, url):
        return {"parse": "0", "url": url,
                "header": {"User-Agent": self.UA_DESKTOP, "Referer": self.host + "/"}}


class _XanimuAdapter(_BaseAdapter):
    """Xanimu（WP 系动漫站）：列表 video-block 卡片；详情页 _high.mp4/_low.mp4
    正片直链（nosofiles CDN，带 verify 签名）。trailer/preview 要排除。"""

    UA_DESKTOP = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                  "(KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36")
    CARD_RE = re.compile(
        r'<div class="video-block[^"]*"[^>]*data-post-id="(\d+)"[^>]*>.*?'
        r'<a class="thumb[^"]*" href="([^"]+)"[^>]*>.*?<img[^>]+(?:src|data-src)="([^"]+)".*?'
        r'<a class="infos[^"]*"[^>]*>.*?<span class="title">([^<]+)</span>',
        re.S)

    def _page(self, path, referer=None):
        if path and not path.startswith(("/", "http")):
            path = "/" + path
        return self.s.http(self._url(path or "/"), referer=referer,
                           headers={"User-Agent": self.UA_DESKTOP}) or ""

    def categories(self):
        """从首页 cat-name-mobile 导航取分类（/zh-CN/{id}-{slug}/ + img title）。"""
        html = self._page("/zh-CN/")
        cats, seen = [], set()
        for m in re.finditer(
                r'<a class="cat-name-mobile" href="(?:https?://[^"]+)?(/zh-CN/[^"]+/)">'
                r'<img[^>]+title="([^"]+)"',
                html, re.S):
            path, name = m.group(1), m.group(2).strip()
            if path in seen or not name:
                continue
            seen.add(path)
            cats.append({"type_id": path, "type_name": name[:20]})
        return cats[:60] or (self.p.get("classes") or [])

    def list(self, cate, page):
        page = max(1, int(page))
        cid = str(cate or "").strip()
        if cid.startswith("/zh-CN/"):
            path = cid if page <= 1 else cid.rstrip("/") + "/page/%d/" % page
            html = self._page(path, referer=self.host + "/zh-CN/")
        else:
            base = urllib.parse.urlsplit((self.p.get("lines") or [{}])[0].get("url", "")).path or "/zh-CN/"
            path = base if page <= 1 else "%s/page/%d/" % (base.rstrip("/"), page)
            html = self._page(path)
        videos, seen = [], set()
        for _pid, href, img, title in self.CARD_RE.findall(html):
            if href in seen:
                continue
            seen.add(href)
            videos.append({
                "vod_id": self.p["key"] + "::" + self._abs(href),
                "vod_name": title.strip()[:120],
                "vod_pic": self._abs(img),
                "vod_remarks": "",
            })
        return {"list": videos, "page": page, "pagecount": page + 1}

    def detail(self, vid):
        url = self._abs(vid)
        html = self._page(url, referer=self.host + "/")
        title = ""
        m = re.search(r"<title[^>]*>(.*?)</title>", html, re.S)
        if m:
            title = re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", m.group(1))).strip()
            title = re.split(r"\s*-\s*xanimu", title)[0]
        mp4 = ""
        links = [u for u in dict.fromkeys(
            re.findall(r'https?://[^"\'\s<>]+?\.mp4[^"\'\s<>]*', html))
            if "trailer" not in u and "preview" not in u]
        for u in links:
            if "_high" in u:
                mp4 = u
                break
        if not mp4 and links:
            mp4 = links[0]
        vod = {
            "vod_id": self.p["key"] + "::" + url,
            "vod_name": title or vid,
            "vod_pic": "",
            "vod_content": "",
            "vod_play_from": "直连",
            "vod_play_url": "正片$%s::%s" % (self.p["key"], mp4 or url),
        }
        return {"list": [vod]}

    def play(self, flag, url):
        return {"parse": "0", "url": url,
                "header": {"User-Agent": self.UA_DESKTOP, "Referer": self.host + "/"}}


class _KvsAdapter(_BaseAdapter):
    """KVS / streamit 系（LissAV / LissAV国产区 / avjoy）。

    列表：入口路径本身就是内容根（LissAV `/asian/zh-CN`、国产区 `/domestic/zh-CN`、
    avjoy `/enter`）；卡片 `<a href="…/video/…">`，标题在 `aria-label`/`title`/`img alt`，
    封面在 `style` 背景图或 `img src`。

    **播放不需要登录**（旧结论"播放需 streamitUser 登录态"是误判——之前用 POST 打的，
    接口其实是 GET）：
      · streamit 皮肤（LissAV 系）：详情页内联脚本给 `videoUid`，
        `GET {入口前缀}/api/video/stream?video_uid={uid}` 直接回 JSON，无 Cookie/token，
        `playlist[].url` 是多画质 m3u8（720p/原画）；
      · dark-magenta 皮肤（avjoy）：`<video><source src="…_480p.mp4">` 签名直链。
    两种直链都带时间戳时效，所以存详情页地址、`play()` 每次现取。
    取流必须带站点 Referer，否则回 132 字节提示页。
    """

    UA_DESKTOP = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                  "(KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36")
    CARD_RE = re.compile(
        r'<a[^>]+href="([^"]*?/video/[^"]+)"([^>]*)>(.*?)</a>', re.S)
    TITLE_RE = re.compile(r'(?:aria-label|title|alt)="([^"]+)"', re.S)
    THUMB_RE = re.compile(
        r'(?:background-image:\s*url\(([^)]+)\)|<img[^>]+(?:data-original|src)="([^"]+)")',
        re.S)

    def _page(self, path, referer=None):
        # 分类路径可能含中文（/videos/genre/探花），需按 UTF-8 百分号编码
        url = self._url(path)
        if any(ord(ch) > 127 for ch in url):
            url = urllib.parse.quote(url, safe=":/?&=%#")
        return self.s.http(url, referer=referer,
                           headers={"User-Agent": self.UA_DESKTOP}) or ""

    @staticmethod
    def _kvs_base(entry):
        """入口路径可能是 /enter 或 /asian/zh-CN；后者才是内容根。"""
        path = urllib.parse.urlsplit(entry or "").path.rstrip("/") or ""
        if not path or path.endswith("/enter") or path == "/enter":
            return ""
        return path

    def categories(self):
        """从 {entry}/genres 取类型（/videos/genre/{urlencoded 中文名}）；
        没有 genres 页的站（avjoy）改用 /tags 页的 /search/videos/{标签}。"""
        entry = (self.p.get("lines") or [{}])[0].get("url", "")
        base = self._kvs_base(entry)
        html = self._page(base + "/genres", referer=entry)
        cats, seen = [], set()
        for m in re.finditer(
                r'href="([^"]*/videos/genre/[^"]+)"[^>]*>(.*?)</a>', html, re.S):
            path = m.group(1)
            name = re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", m.group(2))).strip()
            if path in seen or not name or len(name) > 14:
                continue
            seen.add(path)
            cats.append({"type_id": path, "type_name": name[:14]})
            if len(cats) >= 60:
                break
        if cats:
            return cats
        # 备用：/tags 页的搜索标签
        tag_html = self._page(base + "/tags", referer=entry)
        for m in re.finditer(
                r'href="/search/videos/([^"]+)"[^>]*>(.*?)</a>', tag_html, re.S):
            kw = m.group(1)
            name = re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", m.group(2))).strip()
            if kw in seen or not name or len(name) > 14:
                continue
            seen.add(kw)
            cats.append({"type_id": "/search/videos/" + kw, "type_name": name[:14]})
            if len(cats) >= 60:
                break
        return cats or (self.p.get("classes") or [])

    def list(self, cate, page):
        page = max(1, int(page))
        entry = (self.p.get("lines") or [{}])[0].get("url", "")
        base = self._kvs_base(entry)
        # 首页列表要用完整入口路径（avjoy 的 /enter 才有卡片，剥掉会拿到 2337 壳页）
        home = urllib.parse.urlsplit(entry).path.rstrip("/") or "/"
        cid = str(cate or "").strip()
        if cid.startswith("/search/videos/"):
            path = cid if page <= 1 else "%s?page=%d" % (cid, page)
        elif cid.startswith("/") and "/videos/genre/" in cid:
            path = cid if page <= 1 else "%s?page=%d" % (cid, page)
        else:
            path = home if page <= 1 else "%s?page=%d" % (home, page)
        html = self._page(path, referer=entry)
        videos, seen = [], set()
        for href, attrs, inner in self.CARD_RE.findall(html):
            if href in seen:
                continue
            seen.add(href)
            tm = self.TITLE_RE.search(attrs) or self.TITLE_RE.search(inner)
            title = tm.group(1) if tm else ""
            pic = ""
            tb = self.THUMB_RE.search(attrs) or self.THUMB_RE.search(inner)
            if tb:
                pic = tb.group(1) or tb.group(2) or ""
            videos.append({
                "vod_id": self.p["key"] + "::" + self._abs(href),
                "vod_name": title.strip()[:120],
                "vod_pic": self._abs(pic),
                "vod_remarks": "",
            })
        return {"list": videos, "page": page, "pagecount": page + 1}

    @staticmethod
    def _detail_title(html):
        """streamit 用 .video-detail-headline，avjoy 用 .well-filters 里的 h1。"""
        for pat in (r'video-detail-headline[^>]*>(.*?)</h[1-6]>',
                    r'class="well-filters"[^>]*>\s*<h[1-6][^>]*>(.*?)</h[1-6]>',
                    r"<h1[^>]*>(.*?)</h1>"):
            m = re.search(pat, html, re.S)
            if m:
                text = re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", m.group(1))).strip()
                text = re.sub(r"^[^|]{1,14}\s*\|\s*", "", text)          # "TKTube | …"
                text = re.sub(r"\s*[-–—]\s*AVJOY\s*$", "", text, flags=re.I)
                if text:
                    return text
        m = re.search(r"<title[^>]*>(.*?)</title>", html, re.S)
        if m:
            text = re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", m.group(1))).strip()
            return re.sub(r"^[^|]{1,14}\s*\|\s*", "", text).strip()
        return ""

    def _stream_of(self, page_url, html):
        """先试 stream API（videoUid → playlist[0]），再退 mp4 <source>。"""
        m = re.search(r'videoUid\s*=\s*"([\w]+)"', html or "")
        if m:
            prefix = (page_url or "").split("/video/")[0].rstrip("/")
            if prefix:
                api = "%s/api/video/stream?video_uid=%s" % (prefix, m.group(1))
                text = self.s.http(api, referer=page_url, headers={
                    "User-Agent": self.UA_DESKTOP,
                    "Accept": "application/json, text/plain, */*",
                    "X-Requested-With": "XMLHttpRequest",
                }) or ""
                if text.strip().startswith("{"):
                    try:
                        data = json.loads(text)
                    except Exception:
                        data = {}
                    for item in (data.get("playlist") or []):
                        url = str(item.get("url") or "").replace("\\/", "/").strip()
                        if url:
                            return url
        m = re.search(r'<source[^>]+src="([^"]+)"', html or "")
        return m.group(1).replace("&amp;", "&") if m else ""

    def detail(self, vid):
        url = self._abs(vid)
        html = self._page(url, referer=self.host + "/")
        pic = ""
        m = re.search(r'poster="([^"]+)"', html)
        if m:
            pic = self._abs(m.group(1))
        vod = {
            "vod_id": self.p["key"] + "::" + url,
            "vod_name": self._detail_title(html) or vid,
            "vod_pic": pic,
            "vod_content": "",
            "vod_play_from": "直连",
            # 直链签名带时效（小时～天级），存详情页地址，play() 现取
            "vod_play_url": "正片$%s::%s" % (self.p["key"], url),
        }
        return {"list": [vod]}

    def play(self, flag, url):
        target = str(url or "").strip()
        stream = ""
        if target:
            page = self._abs(target)
            stream = self._stream_of(page, self._page(page, referer=self.host + "/"))
        return {"parse": "0", "url": stream or target,
                "header": {"User-Agent": self.UA_DESKTOP, "Referer": self.host + "/"}}


class _PornhubAdapter(_BaseAdapter):
    """Pornhub：/enter 首页 videoblock 卡片（viewkey）；详情页 mediaDefinitions
    里的 hls 多画质（1080/720/480/240）；取流需站点 Referer + gzip。"""

    UA_DESKTOP = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                  "(KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36")
    CARD_RE = re.compile(
        r'<a\s+href="(/view_video\.php\?viewkey=[a-z0-9]+)"\s+title="([^"]*)"[^>]*>.*?<img[^>]+src="([^"]+)"',
        re.S)

    def _page(self, path, referer=None):
        """Pornhub 连续请求会触发 321B 维护页，退避重试一次。"""
        html = self.s.http(self._url(path), referer=referer,
                           headers={"User-Agent": self.UA_DESKTOP}) or ""
        if len(html) > 50000:
            return html
        time.sleep(1.2)
        if referer is None:
            self.s.http(self._url("/enter"), headers={"User-Agent": self.UA_DESKTOP}) or ""
        html2 = self.s.http(self._url(path), referer=self.host + "/",
                            headers={"User-Agent": self.UA_DESKTOP}) or ""
        return html2 if len(html2) > len(html) else html

    @staticmethod
    def _balanced(text, start):
        """从 text[start] 的 [ 或 { 起做括号配平，返回完整片段。"""
        depth, in_str, i = 0, False, start
        while i < len(text):
            c = text[i]
            if in_str:
                if c == "\\":
                    i += 2
                    continue
                if c == '"':
                    in_str = False
            else:
                if c == '"':
                    in_str = True
                elif c in "[{":
                    depth += 1
                elif c in "]}":
                    depth -= 1
                    if depth == 0:
                        return text[start:i + 1]
            i += 1
        return ""

    def _hls(self, html):
        """取 mediaDefinitions 里 hls 的最高画质直链。"""
        idx = html.find('"mediaDefinitions"')
        if idx < 0:
            return ""
        blob = self._balanced(html, html.find("[", idx))
        try:
            defs = json.loads(blob)
        except Exception:
            return ""
        hls = sorted([x for x in defs if x.get("format") == "hls"],
                     key=lambda y: -int(y.get("quality") or 0))
        return hls[0]["videoUrl"].replace("\\/", "/") if hls else ""

    def categories(self):
        """从 /categories 取分类（type_id 形如 "c=27"，list 走 /video?c=27）。"""
        html = self._page("/categories")
        cats, seen = [], set()
        for m in re.finditer(
                r'href="/video\?c=(\d+)"[^>]*>.*?<span>\s*([^<]{1,24}?)\s*</span>',
                html, re.S):
            cid, name = m.group(1), re.sub(r"\s+", " ", m.group(2)).strip()
            if cid in seen or not name:
                continue
            seen.add(cid)
            cats.append({"type_id": "c=" + cid, "type_name": name[:24]})
        return cats[:60] or (self.p.get("classes") or [])

    def list(self, cate, page):
        page = max(1, int(page))
        cid = str(cate or "").strip()
        if cid.startswith("c="):
            q = "/video?" + cid
            if page > 1:
                q += "&page=%d" % page
            html = self._page(q, referer=self.host + "/categories")
        else:
            html = self._page("/enter")
        videos, seen = [], set()
        for href, title, img in self.CARD_RE.findall(html):
            if href in seen:
                continue
            seen.add(href)
            videos.append({
                "vod_id": self.p["key"] + "::" + self._abs(href),
                "vod_name": title.strip()[:120],
                "vod_pic": self._abs(img),
                "vod_remarks": "",
            })
        return {"list": videos, "page": page, "pagecount": page + 1}

    def detail(self, vid):
        url = self._abs(vid)
        html = self._page(url, referer=self.host + "/")
        title = ""
        m = re.search(r"<title[^>]*>(.*?)</title>", html, re.S)
        if m:
            title = re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", m.group(1))).strip()
            title = re.split(r"\s*-\s*Pornhub", title)[0]
        vod = {
            "vod_id": self.p["key"] + "::" + url,
            "vod_name": title or vid,
            "vod_pic": "",
            "vod_content": "",
            "vod_play_from": "直连",
            "vod_play_url": "正片$%s::%s" % (self.p["key"], self._hls(html) or url),
        }
        return {"list": [vod]}

    def play(self, flag, url):
        return {"parse": "0", "url": url,
                "header": {"User-Agent": self.UA_DESKTOP, "Referer": self.host + "/"}}


class _AcgmhAdapter(_BaseAdapter):
    """Hentai(acgmh)：首页 /g/{id}/ 画廊卡片；详情页 reader 图片数组 → pics:// 图集。
    API 被 403，纯 HTML 解析。"""

    UA_DESKTOP = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                  "(KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36")
    CARD_RE = re.compile(
        r'<a href="(/g/[0-9a-f]+/)" class="cover"[^>]*>.*?<img[^>]+src="([^"]+)"[^>]*>.*?<div class="caption">([^<]+)</div>',
        re.S)

    def _page(self, path, referer=None):
        html = self.s.http(self._url(path), referer=referer,
                           headers={"User-Agent": self.UA_DESKTOP}) or ""
        if len(html) < 4000 and "继续访问" in html:
            self.s.http(self._url("/enter"),
                        headers={"User-Agent": self.UA_DESKTOP}) or ""
            html = self.s.http(self._url(path), referer=referer,
                               headers={"User-Agent": self.UA_DESKTOP}) or ""
        return html

    def categories(self):
        """从 /tags/ 取热门标签（/tag/{slug}/ + span.name）。"""
        html = self._page("/tags/")
        cats, seen = [], set()
        for m in re.finditer(
                r'href="/tag/([a-z0-9\-]+)/"[^>]*>.*?<span class="name[^"]*"[^>]*>(.*?)</span>',
                html, re.S):
            slug, name = m.group(1), re.sub(r"\s+", " ",
                                            re.sub(r"<[^>]+>|<!--.*?-->", " ", m.group(2))).strip()
            if slug in seen or not name:
                continue
            seen.add(slug)
            cats.append({"type_id": slug, "type_name": name[:24]})
            if len(cats) >= 60:
                break
        return cats or (self.p.get("classes") or [])

    def list(self, cate, page):
        page = max(1, int(page))
        cid = str(cate or "").strip()
        if cid and not cid.isdigit() and not cid.startswith("/"):
            path = "/tag/%s/" % cid
            if page > 1:
                path += "?page=%d" % page
            html = self._page(path, referer=self.host + "/tags/")
        else:
            html = self._page("/enter")
        videos, seen = [], set()
        for href, img, title in self.CARD_RE.findall(html):
            if href in seen:
                continue
            seen.add(href)
            videos.append({
                "vod_id": self.p["key"] + "::" + self._abs(href),
                "vod_name": title.strip(),
                "vod_pic": self._abs(img),
                "vod_remarks": "",
            })
        return {"list": videos, "page": page, "pagecount": page + 1}

    def detail(self, vid):
        url = self._abs(vid)
        html = self._page(url, referer=self.host + "/")
        title = ""
        m = re.search(r"<title[^>]*>(.*?)</title>", html, re.S)
        if m:
            title = re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", m.group(1))).strip()
        imgs = []
        for u in re.findall(r'<img[^>]+src="(https?://[^"]+\.(?:webp|png|jpg))"', html):
            if "cover" in u or "thumb" in u:
                continue
            imgs.append(u)
        vod = {
            "vod_id": self.p["key"] + "::" + url,
            "vod_name": title or vid,
            "vod_pic": "",
            "vod_content": "pics:%d" % len(imgs),
            "vod_play_from": "图集",
            "vod_play_url": "图集$%s::pics://%s" % (self.p["key"], "&&".join(imgs[:20])) if imgs else "正片$%s::%s" % (self.p["key"], url),
        }
        return {"list": [vod]}

    def play(self, flag, url):
        return {"parse": "0", "url": url,
                "header": {"User-Agent": self.UA_DESKTOP, "Referer": self.host + "/"}}


class _HsexAdapter(_BaseAdapter):
    """好色TV(hsex)：/enter 列表 video-{id}.htm 卡片；详情页 player.html?video_url=<m3u8>，
    取流需站点 Referer + gzip（无 Referer 返回 143 字节提示页）。"""

    UA_DESKTOP = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                  "(KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36")
    CARD_RE = re.compile(r'<a[^>]+href="(video-\d+\.htm)"[^>]*>\s*<div class="image"[^>]*title="([^"]*)"', re.S)

    def _page(self, path, referer=None):
        return self.s.http(self._url(path), referer=referer,
                           headers={"User-Agent": self.UA_DESKTOP}) or ""

    def categories(self):
        """导航栏是榜单/时长筛选（list-1 / top7_list-1 / top_list-1 / 5min_list-1 / long_list-1）。"""
        html = self._page("/enter")
        cats, seen = [], set()
        for m in re.finditer(
                r'href="((?:[a-z0-9]+_)?list-\d+)\.htm"[^>]*>\s*([^<]{1,20})', html, re.S):
            tid, name = m.group(1), re.sub(r"\s+", " ", m.group(2)).strip()
            if tid in seen or not name or name.isdigit():
                continue
            seen.add(tid)
            cats.append({"type_id": tid, "type_name": name[:20]})
        return cats or (self.p.get("classes") or [])

    def list(self, cate, page):
        page = max(1, int(page))
        if cate and str(cate).strip():
            html = self._page("/%s.htm" % str(cate).strip())
        else:
            html = self._page("/enter")
        videos, seen = [], set()
        for href, title in self.CARD_RE.findall(html):
            if href in seen:
                continue
            seen.add(href)
            img = re.search(r'background-image:\s*url\(["\']([^"\']+)["\']\s*\)[^>]*title="%s"' % re.escape(title), html, re.S)
            videos.append({
                "vod_id": self.p["key"] + "::" + self._abs(href),
                "vod_name": title.strip(),
                "vod_pic": self._abs(img.group(1)) if img else "",
                "vod_remarks": "",
            })
        return {"list": videos, "page": page, "pagecount": page + 1}

    def detail(self, vid):
        url = self._abs(vid)
        html = self._page(url, referer=self.host + "/")
        title = ""
        m = re.search(r"<title[^>]*>(.*?)</title>", html, re.S)
        if m:
            title = re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", m.group(1))).strip()
            title = re.split(r"\s*-\s*片吧|-\s*Tv", title)[0]
        hls = ""
        m = re.search(r"player\.html\?video_url=([^&\s\"']+)", html)
        if m:
            try:
                hls = urllib.parse.unquote(m.group(1))
            except Exception:
                hls = ""
        vod = {
            "vod_id": self.p["key"] + "::" + url,
            "vod_name": title or vid,
            "vod_pic": "",
            "vod_content": "",
            "vod_play_from": "直连",
            "vod_play_url": "正片$%s::%s" % (self.p["key"], hls or url),
        }
        return {"list": [vod]}

    def play(self, flag, url):
        return {"parse": "0", "url": url,
                "header": {"User-Agent": self.UA_DESKTOP, "Referer": self.host + "/"}}


class _XvideosAdapter(_BaseAdapter):
    """XVIDEOS 系（xvideos.com 皮肤镜像：91xvideos.top / xvideos1.icu）。

    首页先回 2337 字节「继续访问」壳页，壳页 JS 只做一件事：
    写 `x-index-auth=authed` 再跳 `/enter`——服务端不校验 Referer/UA，
    直接带上这个 Cookie 就能拿到全量 HTML（143KB），所以壳页不是反爬。

    列表：`/enter` = 第 1 页，`/new/{n-1}` = 第 n 页（站内页码比路径大 1）；
    分类 `/c/{slug}` = 第 1 页，`/c/{slug}/{n-1}` = 第 n 页。
    卡片 `div.frame-block.thumb-block` → 标题锚点 `<a href="/video.{id}/{shard}/{n}/{slug}"
    title="…">`，封面在 `img[data-src]`，清晰度在 `span.video-hd-mark`。
    详情：`html5player.setVideoHLS('…/hls.m3u8')` = 多码率主播放列表
    （480p/1080p/360p），`setVideoUrlHigh/Low` 是同源签名 mp4；
    取流必须带站点 Referer，否则回 143 字节 `tip.ts` 提示页。
    签名带 `secure=…,<过期时间戳>`（数小时），所以 play() 每次回详情页现取。
    """

    UA_DESKTOP = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                  "(KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36")
    COOKIE = "x-index-auth=authed"
    BLOCK_RE = re.compile(
        r'<div[^>]+class="frame-block thumb-block[^"]*"(.*?)(?=<div[^>]+class="frame-block thumb-block|</body>)',
        re.S)
    HREF_RE = re.compile(r'<a\s+href="(/video\.[^"]+)"')
    TITLE_RE = re.compile(r'<a\s+href="/video\.[^"]*"\s+title="([^"]*)"')
    IMG_RE = re.compile(r'data-src="([^"]+)"')
    HD_RE = re.compile(r'class="video-hd-mark"[^>]*>([^<]{1,8})<')
    DUR_RE = re.compile(r'class="duration"[^>]*>([^<]{1,12})<')

    @staticmethod
    def _text(raw):
        """HTML 实体还原 + 压缩空白（标题里有 &amp; / &#039;）。"""
        if not raw:
            return ""
        raw = re.sub(r"&#(\d+);", lambda m: chr(int(m.group(1))), raw)
        raw = re.sub(r"&#[xX]([0-9a-fA-F]+);", lambda m: chr(int(m.group(1), 16)), raw)
        for entity, char in (("&amp;", "&"), ("&lt;", "<"), ("&gt;", ">"),
                             ("&quot;", '"'), ("&apos;", "'"), ("&nbsp;", " ")):
            raw = raw.replace(entity, char)
        return re.sub(r"\s+", " ", raw).strip()

    def _page(self, path, referer=None):
        return self.s.http(self._url(path),
                           referer=referer or (self.host + "/enter"),
                           headers={"User-Agent": self.UA_DESKTOP,
                                    "Cookie": self.COOKIE}) or ""

    def categories(self):
        """首页主导航 ul.sub-list：/c/{Slug}-{id} → 名称。"""
        html = self._page("/enter")
        cats, seen = [], set()
        for m in re.finditer(r'href="/c/([^"/]+)"[^>]*>\s*([^<]{1,32}?)\s*</a>', html):
            tid, name = m.group(1), self._text(m.group(2))
            if not tid or not name or tid in seen:
                continue
            seen.add(tid)
            cats.append({"type_id": tid, "type_name": name[:24]})
        return cats or (self.p.get("classes") or [])

    def _cards(self, html):
        videos, seen = [], set()
        for block in self.BLOCK_RE.findall(html):
            href = self.HREF_RE.search(block)
            if not href or href.group(1) in seen:
                continue
            seen.add(href.group(1))
            title = self.TITLE_RE.search(block)
            name = self._text(title.group(1)) if title else ""
            if not name:
                # 无 title 属性时退回锚点文本（去掉尾部时长）
                m = re.search(r'<a\s+href="/video\.[^"]*"[^>]*>(.*?)</a>', block, re.S)
                name = self._text(re.sub(r"<[^>]+>", " ", m.group(1))) if m else ""
            img = self.IMG_RE.search(block)
            hd = self.HD_RE.search(block)
            dur = self.DUR_RE.search(block)
            marks = [x for x in (self._text(hd.group(1)) if hd else "",
                                 self._text(dur.group(1)) if dur else "") if x]
            videos.append({
                "vod_id": self.p["key"] + "::" + self._abs(href.group(1)),
                "vod_name": name,
                "vod_pic": self._abs(img.group(1)) if img else "",
                "vod_remarks": " · ".join(marks),
            })
        return videos

    def list(self, cate, page):
        page = max(1, int(page))
        # 平台级 Tab 会把 cate 传成 "0"，那不是分类（分类 id 形如 AI-239）
        cate = str(cate or "").strip()
        if cate.isdigit():
            cate = ""
        if cate:
            path = "/c/%s" % cate if page <= 1 else "/c/%s/%d" % (cate, page - 1)
        else:
            path = "/enter" if page <= 1 else "/new/%d" % (page - 1)
        return {"list": self._cards(self._page(path)), "page": page, "pagecount": page + 1}

    def _detail_html(self, url):
        return self._page(url, referer=self.host + "/enter")

    @staticmethod
    def _setting(html, name):
        m = re.search(r"html5player\.%s\(\s*'([^']*)'" % name, html)
        return (m.group(1).replace("\\/", "/") if m else "").strip()

    def detail(self, vid):
        url = self._abs(vid)
        html = self._detail_html(url)
        title = self._text(self._setting(html, "setVideoTitle"))
        if not title:
            m = re.search(r"<title[^>]*>(.*?)</title>", html, re.S)
            title = self._text(re.sub(r"<[^>]+>", " ", m.group(1))) if m else ""
            title = re.split(r"\s*-\s*91xvideos|\s*-\s*xvideos", title)[0].strip()
        pic = self._setting(html, "setThumbUrl169") or self._setting(html, "setThumbUrl")
        vod = {
            "vod_id": self.p["key"] + "::" + url,
            "vod_name": title or vid,
            "vod_pic": pic,
            "vod_content": "",
            "vod_play_from": "直连",
            # 签名 secure=…,<过期戳> 只活几小时（实测约 4h），所以存详情页地址，
            # play() 每次回详情页现取 setVideoHLS（和 Pornhub/VJAV 同思路）
            "vod_play_url": "正片$%s::%s" % (self.p["key"], url),
        }
        return {"list": [vod]}

    def play(self, flag, url):
        target = str(url or "").strip()
        if target and ".m3u8" not in target and ".mp4" not in target:
            html = self._detail_html(self._abs(target))
            target = self._setting(html, "setVideoHLS") or \
                self._setting(html, "setVideoUrlHigh") or target
        return {"parse": "0", "url": target,
                "header": {"User-Agent": self.UA_DESKTOP, "Referer": self.host + "/"}}


class _HanimeAdapter(_BaseAdapter):
    """Hanime1 系（hanime169/101/999… 33 条同模板线路，实测 27 条可用）。

    推翻旧结论「站点长期 500，抓不到分类」：**只有首页 `/` 恒回 2337 字节
    "继续访问"壳页**（所有线路都一样），而 `/watch?v={id}` 与
    `/search?genre={名称}` 直接 200 全量页面。所以列表与分类都不碰 `/`：
    列表用任一观看页当种子（该页含 90 条推荐），分类取顶部导航的 10 个
    `/search?genre={中文名}`（中文必须百分号编码）。
    详情 `/watch?v={id}` 页内 `-720p.mp4` 直链；用 iPhone UA。
    """

    WATCH_RE = re.compile(r'href="(?:https?://[^"]+)?(/watch\?v=(\d+))"[^>]*>(.*?)</a>', re.S)

    FALLBACK = "https://www.hanime999.cc"
    SEED = "/watch?v=407765"          # 首页是壳页，拿这个当列表种子
    SHELL_MAX = 60000                 # 壳页 2337 字节，真页面 ≥110KB
    MOBILE_UA = ("Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) "
                 "AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Mobile/15E148 Safari/604.1")

    def _page(self, path, host=None):
        """取页面；主线路拿到壳页/500 时换备用域再试一次。"""
        base = (host or self.host or "").rstrip("/") or self.FALLBACK

        def one(root):
            url = root.rstrip("/") + path
            if any(ord(ch) > 127 for ch in url):   # /search?genre=裏番
                url = urllib.parse.quote(url, safe=":/?&=%#")
            return self.s.http(url, headers={"User-Agent": self.MOBILE_UA}) or ""

        html = one(base)
        if len(html) < self.SHELL_MAX and base != self.FALLBACK:
            alt = one(self.FALLBACK)
            if len(alt) > len(html):
                return alt
        return html

    def categories(self):
        """顶部导航 10 个 /search?genre={中文名}。"""
        html = self._page(self.SEED)
        cats, seen = [], set()
        for m in re.finditer(
                r'<a class="[^"]*nav-desktop-items[^"]*"[^>]*href="[^"]*?/search\?genre=([^"&]+)"'
                r"[^>]*>([^<]{1,20})</a>", html):
            genre = urllib.parse.unquote(m.group(1)).strip()
            name = re.sub(r"\s+", " ", m.group(2)).strip()
            if not genre or not name or genre in seen:
                continue
            seen.add(genre)
            cats.append({"type_id": "/search?genre=" + urllib.parse.quote(genre),
                         "type_name": name[:14]})
        return cats or (self.p.get("classes") or [])

    def list(self, cate, page):
        page = max(1, int(page))
        cid = str(cate or "").strip()
        if cid.startswith("/search"):
            path = cid if page <= 1 else cid + ("&" if "?" in cid else "?") + "page=%d" % page
            html = self._page(path)
        else:
            html = self._page(self.SEED)
            if page > 1:
                more = self._page("/?page=%d" % page)
                if "/watch?v=" in more:
                    html = more
        videos, seen = [], set()
        for href, vid, inner in self.WATCH_RE.findall(html):
            if vid in seen:
                continue
            seen.add(vid)
            title = re.sub(r"<[^>]+>", " ", inner)
            title = re.sub(r"\s+", " ", title.replace("&nbsp;", " ").replace("&amp;", "&")).strip()[:60]
            title = title or ("视频 " + vid)
            img = ""
            found = re.search(r'(?:data-src|data-original|src)="([^"]+)"', inner)
            if found:
                img = found.group(1)
            videos.append({
                "vod_id": self.p["key"] + "::" + vid,
                "vod_name": title,
                "vod_pic": self._abs(img),
                "vod_remarks": "",
            })
        return {"list": videos, "page": page, "pagecount": page + 1}

    def detail(self, vid):
        html = self._page("/watch?v=" + str(vid))
        title = ""
        found = re.search(r'property="og:title"\s+content="([^"]+)"', html)
        if found:
            title = found.group(1).strip()
        elif re.search(r"<title[^>]*>(.*?)</title>", html, re.S):
            title = re.sub(r"\s+", " ", re.search(r"<title[^>]*>(.*?)</title>", html, re.S).group(1)).strip()
            title = re.split(r"\s+-\s+hanime[\w.\-]*", title)[0].strip()   # 去掉 "- hanime169.net"
        title = re.sub(r"\s+", " ", title.replace("&nbsp;", " ").replace("&amp;", "&")).strip()
        direct = ""
        found = re.search(r'href="([^"]*?(?:-720p\.mp4|\.m3u8)[^"]*)"', html)
        if found:
            direct = found.group(1)
        vod = {
            "vod_id": self.p["key"] + "::" + str(vid),
            "vod_name": title or ("视频 " + str(vid)),
            "vod_pic": "",
            "vod_content": "",
            "vod_play_from": "直连",
            "vod_play_url": "正片$" + self.p["key"] + "::" + direct,
        }
        return {"list": [vod]}

    def play(self, flag, url):
        return {"parse": "0", "url": url, "header": self.s.headers()}


class _JmAdapter(_BaseAdapter):
    """禁漫天堂(18comic)：/enter 列表 → /album/{id}/{slug} 章节(/photo/{pid}) →
    阅读页 media/photos/{aid}/{page}.webp 图片序列 → pics://。

    注意：URL 含中文，必须 quote；线路上游抖动大，需多线路重试。
    """

    UA_DESKTOP = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                  "(KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36")
    ALBUM_RE = re.compile(r'href="(/album/\d+/[^"]*)"')
    PHOTO_RE = re.compile(r'href="(/photo/\d+[^"]*)"')
    PAGE_RE = re.compile(r'https?://[^"\'\s<>]*?/media/photos/[^"\'\<>]*?\.(?:webp|jpg|jpeg|png)')

    def _page(self, path, referer=None):
        """多线路兜底：当前线路失败时换平台其余线路重试（最多 4 条，避免长拖）。"""
        if path.startswith("http"):
            url = path
        else:
            url = self._url(path)
        html = self.s.http(url, referer=referer, headers={"User-Agent": self.UA_DESKTOP}) or ""
        if len(html) > 4000:
            return html
        if "站点维护中" in html:
            return ""
        tried = 0
        for line in (self.p.get("lines") or []):
            other = (line.get("url") or "").rstrip("/")
            if not other or tried >= 4:
                break
            root = other.split("://")[0] + "://" + other.split("://")[1].split("/")[0]
            if root == self.host.rstrip("/"):
                continue
            tried += 1
            url2 = path if path.startswith("http") else root + "/" + path.lstrip("/")
            html = self.s.http(urllib.parse.quote(url2, safe=":/?&=%#"),
                               referer=root + "/",
                               headers={"User-Agent": self.UA_DESKTOP}) or ""
            if len(html) > 4000:
                self.host = root
                return html
            if "站点维护中" in html:
                return ""
        return html

    def list(self, cate, page):
        html = self._page("/enter")
        videos, seen = [], set()
        for path in self.ALBUM_RE.findall(html):
            if path in seen:
                continue
            seen.add(path)
            aid = re.search(r"/album/(\d+)", path)
            slug = urllib.parse.unquote(path.rsplit("/", 1)[-1])
            videos.append({
                "vod_id": self.p["key"] + "::" + path,
                "vod_name": slug.replace("-", " ")[:60],
                "vod_pic": "",
                "vod_remarks": "漫画",
            })
        return {"list": videos, "page": int(page), "pagecount": int(page) + 1}

    def detail(self, vid):
        path = vid if vid.startswith("/") else "/" + vid.lstrip("/")
        html = self._page(urllib.parse.quote(path, safe="/"))
        title = ""
        m = re.search(r"<title[^>]*>(.*?)</title>", html, re.S)
        if m:
            title = re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", m.group(1))).strip()
        chapters = list(dict.fromkeys(self.PHOTO_RE.findall(html)))
        if not chapters:
            return {"list": []}
        eps = "#".join("第%d話$%s::%s" % (i + 1, self.p["key"], p)
                       for i, p in enumerate(chapters))
        vod = {
            "vod_id": self.p["key"] + "::" + path,
            "vod_name": title or path,
            "vod_pic": "",
            "vod_content": "",
            "vod_play_from": "漫画",
            "vod_play_url": eps,
        }
        return {"list": [vod]}

    def play(self, flag, url):
        path = url if url.startswith("/") else "/" + url.lstrip("/")
        html = self._page(urllib.parse.quote(path, safe="/"))
        imgs, seen = [], set()
        for src in self.PAGE_RE.findall(html):
            full = self._abs(src)
            if full and full not in seen:
                seen.add(full)
                imgs.append(full)
        if not imgs:
            return {"parse": "0", "url": ""}
        return {"parse": "0", "url": "pics://" + "&&".join(imgs),
                "header": {"User-Agent": self.UA_DESKTOP, "Referer": self.host + "/"}}


class _DageAdapter(_BaseAdapter):
    """大哥视频(dage)：Vue SPA + JSON API（baseURL /api，返回 data 字段混淆）。

    解密：data.replace('/','0').replace('@','/').replace('.','+') → 反转 → 补 '=' → base64 → JSON。
    接口：/api/core.json（配置+菜单）、/api/index.json（首页）、/api/lists/{id}/{page}/{limit}.json、
    /api/play/{id}.json（player[0].play 即 m3u8 直链）。
    """

    UA_DESKTOP = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                  "(KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36")

    @staticmethod
    def _decode(data):
        """复刻前端解密：链式字符替换 → 反转 → 补齐 → base64 → JSON。"""
        if not data:
            return None
        t = data.replace("/", "0").replace("@", "/").replace(".", "+")[::-1]
        pad = len(t) % 4
        if pad:
            t = t + "=" * (4 - pad)
        try:
            return json.loads(base64.b64decode(t).decode("utf-8", "replace"))
        except Exception:
            return None

    def _api(self, path, referer=None):
        root = self.host.rstrip("/")
        ref = referer or (root + "/")
        head = {"User-Agent": self.UA_DESKTOP,
                "Accept": "application/json, text/plain, */*"}
        body = self.s.http(root + path, referer=ref, headers=head) or ""
        try:
            obj = json.loads(body)
        except Exception:
            return None
        if isinstance(obj, dict) and "data" in obj:
            return self._decode(obj.get("data"))
        return obj

    def categories(self):
        """从 /api/core.json 的 menu 取 vod 分区的子分类（约 32 个）。"""
        core = self._api("/api/core.json")
        cats = []
        for menu in (core or {}).get("menu") or []:
            if menu.get("type") != "vod":
                continue
            zone = str(menu.get("name") or "")
            for child in menu.get("children") or []:
                cid = str(child.get("id") or "")
                name = str(child.get("name") or "")
                if cid and name:
                    cats.append({"type_id": cid,
                                 "type_name": ("%s·%s" % (zone, name)) if zone else name})
        return cats or (self.p.get("classes") or [])

    def list(self, cate, page):
        page = max(1, int(page))
        data = None
        cid = str(cate or "").strip()
        if cid and cid.isdigit():
            data = self._api("/api/lists/%s/%d/24.json" % (cid, page))
        if not data:
            data = self._api("/api/index.json")
        items = []
        if isinstance(data, dict):
            for key in ("items", "list", "videos"):
                if isinstance(data.get(key), list):
                    items = data[key]
                    break
            if not items and isinstance(data.get("new"), dict):
                items = data["new"].get("items") or []
        videos, seen = [], set()
        for it in items or []:
            url = str(it.get("url") or "")
            vid = url.rstrip(".html").replace("/play/", "").strip("/")
            if not vid or vid in seen:
                continue
            seen.add(vid)
            videos.append({
                "vod_id": self.p["key"] + "::" + vid,
                "vod_name": str(it.get("title") or vid)[:110],
                "vod_pic": self._abs(it.get("img") or ""),
                "vod_remarks": str(it.get("duration") or it.get("time") or ""),
            })
        return {"list": videos, "page": page, "pagecount": page + 1}

    def detail(self, vid):
        vid = str(vid).rstrip(".html").strip("/")
        data = self._api("/api/play/%s.json" % vid)
        if not isinstance(data, dict):
            return {"list": []}
        players = data.get("player") or []
        url = ""
        for p in players:
            if p.get("play"):
                url = p["play"]
                break
        name = str(data.get("title") or vid)
        vod = {
            "vod_id": self.p["key"] + "::" + vid,
            "vod_name": name[:110],
            "vod_pic": self._abs(data.get("img") or ""),
            "vod_content": "",
            "vod_play_from": "直连",
            "vod_play_url": "正片$%s::%s" % (self.p["key"], url or ("https://%s/play/%s.html" % (self.host.split("://")[-1], vid))),
        }
        return {"list": [vod]}

    def play(self, flag, url):
        return {"parse": "0", "url": url,
                "header": {"User-Agent": self.UA_DESKTOP, "Referer": self.host + "/"}}


class _JavdbAdapter(_BaseAdapter):
    """成人影片数据库(javdb)：**数据库站，无正片流**，只有磁力/云盘。

    可提供列表 + 详情（标题/封面/番号/评分），播放返回空。
    入口必须用 /enter（其他路径一律 2337 壳页或 500）；列表另有
    /rankings/movies?p=weekly&t=censored（60 条）、/tags?c10=1（40 条）。
    """

    UA_DESKTOP = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                  "(KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36")
    CARD_RE = re.compile(
        r'<a href="(/v/[A-Za-z0-9]+)"[^>]*title="([^"]*)"[^>]*>\s*<div class="cover[^"]*">\s*'
        r'<img[^>]+src="([^"]+)"[^>]*>\s*</div>\s*<div class="video-title">(.*?)</div>',
        re.S)

    def _page(self, path, referer=None):
        url = path if path.startswith("http") else self._url(path)
        return self.s.http(url, referer=referer or (self.host + "/enter"),
                           headers={"User-Agent": self.UA_DESKTOP}) or ""

    def categories(self):
        """固定用站内已验证的 3 个列表入口（/enter 每周推荐、周榜、有码标签）。"""
        return [
            {"type_id": "recommend", "type_name": "每周推荐"},
            {"type_id": "weekly", "type_name": "周榜"},
            {"type_id": "censored", "type_name": "有码"},
        ]

    def list(self, cate, page):
        page = max(1, int(page))
        cid = str(cate or "").strip()
        if cid == "weekly":
            path = "/rankings/movies?p=weekly&t=censored"
        elif cid == "censored":
            path = "/tags?c10=1"
        else:
            path = "/enter"
        html = self._page(path)
        videos, seen = [], set()
        for href, title, img, vtitle in self.CARD_RE.findall(html):
            if href in seen:
                continue
            seen.add(href)
            name = re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", vtitle)).strip()
            videos.append({
                "vod_id": self.p["key"] + "::" + href,
                "vod_name": (name or title.strip())[:110],
                "vod_pic": self._abs(img),
                "vod_remarks": "数据库",
            })
        return {"list": videos, "page": page, "pagecount": page + 1}

    def detail(self, vid):
        path = vid if vid.startswith("/") else "/" + vid.lstrip("/")
        html = self._page(path)
        title = ""
        m = re.search(r"<title[^>]*>(.*?)</title>", html, re.S)
        if m:
            title = re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", m.group(1))).strip()
            title = re.split(r"\s*\|", title)[0]
        pic = ""
        m = re.search(r'<img[^>]+class="[^"]*video-cover[^"]*"[^>]+src="([^"]+)"', html) or \
            re.search(r'"thumbnailUrl"\s*:\s*"([^"]+)"', html)
        if m:
            pic = m.group(1)
        vod = {
            "vod_id": self.p["key"] + "::" + path,
            "vod_name": title or vid,
            "vod_pic": pic,
            "vod_content": "数据库收录（无在线播放，仅磁力/云盘信息）",
            "vod_play_from": "数据库",
            "vod_play_url": "",
        }
        return {"list": [vod]}

    def play(self, flag, url):
        return {"parse": "0", "url": ""}


class _SuperpornAdapter(_BaseAdapter):
    """SuperPorn：thumb-video 卡片；详情页 <source src="…jmpres/…mp4?secure=…"> 直链。
    坑：快照线路是 cn.superporn.*（本地网络全拒连），实际可用入口是 www.superporn.me，
    适配器内部做域名修正。"""

    UA_DESKTOP = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                  "(KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36")
    CARD_RE = re.compile(
        r'<a href="((?:https?://[^"]+)?/video/[^"]+)"[^>]*class="thumb-duracion"[^>]*>\s*'
        r'<img[^>]+alt="([^"]*)"[^>]*data-src="([^"]+)"',
        re.S)
    SRC_RE = re.compile(r'<source\s+src="([^"]+\.mp4[^"]*)"', re.I)

    def _root(self):
        """cn.* 入口在本网被拒，统一用 www 入口。"""
        host = self.host.replace("://cn.", "://www.")
        if "superporn" in host:
            host = re.sub(r"://[^/]*superporn[^/]*", "://www.superporn.me", host)
        return host.rstrip("/")

    def _page(self, path, referer=None):
        root = self._root()
        url = path if path.startswith("http") else root + "/" + path.lstrip("/")
        return self.s.http(url, referer=referer,
                           headers={"User-Agent": self.UA_DESKTOP}) or ""

    def list(self, cate, page):
        cid = str(cate or "").strip()
        html = self._page("/" + cid if cid else "/")
        videos, seen = [], set()
        for href, title, img in self.CARD_RE.findall(html):
            full = self._abs(href)
            if full in seen:
                continue
            seen.add(full)
            videos.append({
                "vod_id": self.p["key"] + "::" + full,
                "vod_name": title.strip()[:110],
                "vod_pic": self._abs(img),
                "vod_remarks": "",
            })
        return {"list": videos, "page": int(page), "pagecount": int(page) + 1}

    def categories(self):
        """从 /categories 取标签（slug 作 type_id，list 时走 /{slug}）。"""
        html = self._page("/categories")
        cats, seen = [], set()
        for m in re.finditer(
                r'href="(?:https?://[^"]+)?/([a-z0-9\-]+)"[^>]*>\s*([A-Za-z][^<]{1,24})</a>',
                html, re.S):
            slug, name = m.group(1), m.group(2).strip()
            if slug in seen or slug in ("categories", "series", "pornstars", "channels",
                                        "enter", "video", "videos", "tags", "login"):
                continue
            seen.add(slug)
            cats.append({"type_id": slug, "type_name": name[:24]})
        return cats[:60] or (self.p.get("classes") or [])

    def detail(self, vid):
        url = self._abs(vid)
        html = self._page(url, referer=self._root() + "/")
        title = ""
        m = re.search(r"<title[^>]*>(.*?)</title>", html, re.S)
        if m:
            title = re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", m.group(1))).strip()
            title = re.split(r"\s*-\s*SuperPorn", title)[0]
        pic = ""
        m = re.search(r'<video[^>]+poster="([^"]+)"', html)
        if m:
            pic = m.group(1)
        mp4 = ""
        m = self.SRC_RE.search(html)
        if m:
            mp4 = m.group(1).replace("&amp;", "&")
        vod = {
            "vod_id": self.p["key"] + "::" + url,
            "vod_name": title or vid,
            "vod_pic": pic,
            "vod_content": "",
            "vod_play_from": "直连",
            "vod_play_url": "正片$%s::%s" % (self.p["key"], mp4 or url),
        }
        return {"list": [vod]}

    def play(self, flag, url):
        return {"parse": "0", "url": url,
                "header": {"User-Agent": self.UA_DESKTOP, "Referer": self._root() + "/"}}


class _AmdAdapter(_BaseAdapter):
    """爱漫岛(amdcomic)：苹果CMS 漫画站。

    列表 /voddetail/{id}.html → 章节 /vodplay-{id}-{sid}-{pid}.html（连字符版苹果CMS）；
    阅读页图片由页内 JS 拼接：/jmpimg/cdn-msp.{dom_string}/media/photos/{aid}/{page:05d}.webp
    （aid 与总页数 s2 来自 player_aaaa.url 的 JSON 串，dom_string 取最后一次赋值）。
    """

    UA_DESKTOP = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                  "(KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36")
    CARD_RE = re.compile(
        r'<a[^>]+href="(/voddetail/\d+\.html)"[^>]*?title="([^"]*)"[^>]*?'
        r'(?:data-background|data-original|data-src)="([^"]+)"',
        re.S)
    CARD_RE2 = re.compile(
        r'<a[^>]+href="(/voddetail/\d+\.html)"[^>]*?title="([^"]*)"[^>]*>\s*(?:<[^>]+>\s*)*<img[^>]+src="([^"]+)"',
        re.S)
    EP_RE = re.compile(r'href="(/vodplay-\d+-\d+-\d+\.html)"')

    def _page(self, path, referer=None):
        url = path if path.startswith("http") else self._url(path)
        html = self.s.http(url, referer=referer, headers={"User-Agent": self.UA_DESKTOP}) or ""
        if len(html) > 4000:
            return html
        if "站点维护中" in html:
            return ""
        for line in (self.p.get("lines") or [])[:3]:
            other = (line.get("url") or "")
            if not other:
                continue
            root = other.split("://")[0] + "://" + other.split("://")[1].split("/")[0]
            if root == self.host:
                continue
            html = self.s.http(root + path, referer=root + "/",
                               headers={"User-Agent": self.UA_DESKTOP}) or ""
            if len(html) > 4000:
                self.host = root
                return html
        return html

    def list(self, cate, page):
        html = self._page("/enter")
        videos, seen = [], set()
        found = self.CARD_RE.findall(html) or self.CARD_RE2.findall(html)
        for href, title, img in found:
            if href in seen:
                continue
            seen.add(href)
            videos.append({
                "vod_id": self.p["key"] + "::" + href,
                "vod_name": title.strip()[:80],
                "vod_pic": self._abs(img),
                "vod_remarks": "漫画",
            })
        return {"list": videos, "page": int(page), "pagecount": int(page) + 1}

    def detail(self, vid):
        path = vid if vid.startswith("/") else "/" + vid.lstrip("/")
        html = self._page(path, referer=self.host + "/enter")
        title = ""
        m = re.search(r"<title[^>]*>(.*?)</title>", html, re.S)
        if m:
            title = re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", m.group(0))).strip()
            title = re.sub(r"^.*?<title[^>]*>", "", title)
            title = re.split(r"\s*-\s*爱漫岛|\s*_更新至", title)[0]
        eps = list(dict.fromkeys(self.EP_RE.findall(html)))
        if not eps:
            return {"list": []}
        play_url = "#".join("第%d話$%s::%s" % (i + 1, self.p["key"], p)
                            for i, p in enumerate(eps))
        vod = {
            "vod_id": self.p["key"] + "::" + path,
            "vod_name": title or path,
            "vod_pic": "",
            "vod_content": "",
            "vod_play_from": "漫画",
            "vod_play_url": play_url,
        }
        return {"list": [vod]}

    def play(self, flag, url):
        path = url if url.startswith("/") else "/" + url.lstrip("/")
        html = self._page(path, referer=self.host + "/enter")
        m = re.search(r'"url":"(\{\\"s1\\".*?\\"\})"', html, re.S)
        if not m:
            return {"parse": "0", "url": ""}
        try:
            info = json.loads(json.loads('"%s"' % m.group(1)))
        except Exception:
            return {"parse": "0", "url": ""}
        aid = str(info.get("aid") or "")
        pages = int(info.get("s2") or 0)
        doms = re.findall(r"dom_string\s*=\s*'([^']+)'", html)
        if not aid or not pages or not doms:
            return {"parse": "0", "url": ""}
        dom = doms[-1]
        root = self.host.rstrip("/")
        imgs = ["%s/jmpimg/cdn-msp.%s/media/photos/%s/%05d.webp" % (root, dom, aid, i)
                for i in range(1, pages + 1)]
        return {"parse": "0", "url": "pics://" + "&&".join(imgs),
                "header": {"User-Agent": self.UA_DESKTOP, "Referer": root + "/"}}


class _WnacgAdapter(_BaseAdapter):
    """99漫画(wnacg · MeiuPic)：/enter 列表 /photos-index-aid-{aid}.html 卡片。

    第十二轮复测结论（推翻「详情站点维护中」的旧结论，逐条实测）：

      · 专辑页 `/photos-index-aid-{aid}.html` —— **200**（多数 aid；少数 aid 回 403），
        标题/封面齐全；
      · **图集数据接口 `/photos-item-aid-{aid}.html` —— 200**，内容是
        `mReader.initData({"page_url":[…]})`，一次给出整册全部原图（实测 53/250/520 张），
        **不需要登录、不需要 Cookie**。这是本适配器的播放入口；
      · 阅读页 `/photos-view-id-*.html`、`/photos-slide-*` —— 全线路 403
        （换桌面/移动 UA、加 Referer、带 `/enter` 下的 `x-index-auth` Cookie 都无效），
        所以**不碰阅读页**；
      · 但图片 CDN 的签名当前是**过期**的：`verify=<时间戳>-<签名>`，
        实测 aid 399855 的时间戳是 2026-10-30（-9 天）、399000 是 2026-10-26（-13 天），
        拿这个签名去取图一律 404/拒连。也就是说站点页面数据没刷新，
        **本站目前取不到图**；站方刷新签名后本适配器无需改动即可出图。

    列表：`/enter` 卡片 / 图集：`photos-item-aid-{aid}` → pics:// 图片序列。
    """

    UA_DESKTOP = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                  "(KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36")
    CARD_RE = re.compile(
        r'<a href="(/photos-index-aid-\d+\.html)" title="([^"]*)"[^>]*>\s*<img[^>]+src="([^"]+)"',
        re.S)
    ITEM_RE = re.compile(r'"(https?://[^"]+?\.(?:webp|jpg|jpeg|png)\?verify=[^"]*)"')

    def _page(self, path, referer=None):
        """壳页(2337/2563B)多为频率限制：退避重试；维护页(403)快速放弃；跨线路兜底。"""
        url = path if path.startswith("http") else self._url(path)

        def fetch(u, ref):
            html = self.s.http(u, referer=ref, headers={"User-Agent": self.UA_DESKTOP}) or ""
            return html

        for attempt in range(3):
            html = fetch(url, referer)
            if len(html) > 4000:
                return html
            if "站点维护中" in html:
                return ""  # 站点侧维护，重试无意义
            time.sleep(1.2 * (attempt + 1))
        tried = 0
        for line in (self.p.get("lines") or []):
            other = (line.get("url") or "")
            if not other or tried >= 3:
                break
            root = other.split("://")[0] + "://" + other.split("://")[1].split("/")[0]
            if root == self.host:
                continue
            tried += 1
            html = fetch(root + path, root + "/")
            if len(html) > 4000:
                self.host = root
                return html
            if "站点维护中" in html:
                return ""
        return html

    def list(self, cate, page):
        html = self._page("/enter")
        videos, seen = [], set()
        for href, title, img in self.CARD_RE.findall(html):
            if href in seen:
                continue
            seen.add(href)
            videos.append({
                "vod_id": self.p["key"] + "::" + href,
                "vod_name": title.strip()[:80],
                "vod_pic": self._abs(img),
                "vod_remarks": "漫画",
            })
        return {"list": videos, "page": int(page), "pagecount": int(page) + 1}

    @staticmethod
    def _clean_title(html):
        m = re.search(r"<title[^>]*>(.*?)</title>", html, re.S)
        if not m:
            return ""
        text = re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", m.group(1))).strip()
        text = re.split(r"\s*-\s*绅士漫画|\s*-\s*99漫画", text)[0].strip()
        return text.replace("&amp;", "&")

    def detail(self, vid):
        path = vid if vid.startswith("/") else "/" + vid.lstrip("/")
        html = self._page(path, referer=self.host + "/enter")
        if not html:
            return {"list": []}
        pic = ""
        m = re.search(r'<img[^>]+src="([^"]+\.(?:webp|jpg|jpeg|png))"', html)
        if m:
            pic = self._abs(m.group(1))
        vod = {
            "vod_id": self.p["key"] + "::" + path,
            "vod_name": self._clean_title(html) or path,
            "vod_pic": pic,
            "vod_content": "整册图集（/photos-item-aid 一次取全）",
            "vod_play_from": "图集",
            # 一整册就是一个 vod：目标存专辑路径，play() 去 photos-item 接口取全套图
            "vod_play_url": "全集$%s::%s" % (self.p["key"], path),
        }
        return {"list": [vod]}

    def play(self, flag, url):
        """专辑路径 → /photos-item-aid-{aid}.html → mReader.initData 的 page_url 序列。"""
        path = str(url or "")
        m = re.search(r"aid-(\d+)", path) or re.search(r"(?:^|/)(\d+)(?:\.html)?$", path)
        if not m:
            return {"parse": "0", "url": ""}
        data = self._page("/photos-item-aid-%s.html" % m.group(1),
                          referer=self.host + path)
        imgs, seen = [], set()
        for src in self.ITEM_RE.findall(data or ""):
            src = src.replace("\\/", "/")
            if src.startswith("http://"):
                src = "https://" + src[len("http://"):]
            if src not in seen:
                seen.add(src)
                imgs.append(src)
        if not imgs:
            return {"parse": "0", "url": ""}
        return {"parse": "0", "url": "pics://" + "&&".join(imgs),
                "header": {"User-Agent": self.UA_DESKTOP, "Referer": self.host + "/"}}


class _ComicAdapter(_BaseAdapter):
    """18comic 类：/enter 列表 -> /album/{id} 章节(/photo) -> 图片 -> manga://"""

    ALBUM_RE = re.compile(r'href="(/album/\d+/[^"]*)"[^>]*>(.*?)</a>', re.S)
    PHOTO_RE = re.compile(r'href="(/photo/\d+[^"]*)"')
    IMG_RE = re.compile(r'data-original="([^"]+)"')

    def _warm(self):
        cached = getattr(self, "_entry_html", "")
        if cached:
            return cached
        self._entry_html = self.s.http(self._url("/enter")) or ""
        return self._entry_html

    def list(self, cate, page):
        html = self._warm()
        videos, seen = [], set()
        for href, inner in self.ALBUM_RE.findall(html):
            if href in seen:
                continue
            seen.add(href)
            text = re.sub(r"<[^>]+>", " ", inner)
            title = re.sub(r"\s+", " ", text).strip()[:60]
            img = ""
            found = re.search(r'(?:data-original|data-src|src)="([^"]+)"', inner)
            if found:
                img = found.group(1)
            videos.append({
                "vod_id": self.p["key"] + "::" + href,
                "vod_name": title or href,
                "vod_pic": self._abs(img),
                "vod_remarks": "漫画",
            })
        return {"list": videos, "page": int(page), "pagecount": int(page) + 1}

    def detail(self, vid):
        self._warm()
        html = self.s.http(self._abs(vid), referer=self._url("/enter")) or ""
        title = ""
        found = re.search(r"<title[^>]*>(.*?)</title>", html, re.S)
        if found:
            title = re.sub(r"\s+", " ", found.group(1)).strip()
        chapters, seen = [], set()
        for path in self.PHOTO_RE.findall(html):
            if path in seen:
                continue
            seen.add(path)
            chapters.append(path)
        if not chapters:
            return {"list": []}
        eps = "#".join("第%d话$%s::%s" % (i + 1, self.p["key"], path)
                       for i, path in enumerate(chapters))
        vod = {
            "vod_id": self.p["key"] + "::" + vid,
            "vod_name": title or vid,
            "vod_pic": "",
            "vod_content": "",
            "vod_play_from": "漫画",
            "vod_play_url": eps,
        }
        return {"list": [vod]}

    def play(self, flag, url):
        self._warm()
        html = self.s.http(self._abs(url), referer=self._url("/enter")) or ""
        imgs, seen = [], set()
        for src in self.IMG_RE.findall(html):
            full = self._abs(src)
            if full and full not in seen:
                seen.add(full)
                imgs.append(full)
        if not imgs:
            return {"parse": "0", "url": ""}
        return {"parse": "0", "url": "manga://" + "&&".join(imgs),
                "header": self.s.headers()}

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
    "hanime": _HanimeAdapter,
    "18av": _Av18Adapter,
    "jable": _JableAdapter,
    "rou": _RouAdapter,
    "xhamster": _XhamsterAdapter,
    "vjav": _VjavAdapter,
    "hsex": _HsexAdapter,
    "91av": _91avAdapter,
    "yesporn": _YespornAdapter,
    "cartoon": _CartoonAdapter,
    "acgmh": _AcgmhAdapter,
    "pornhub": _PornhubAdapter,
    "okxxx": _OkxxxAdapter,
    "kvs": _KvsAdapter,
    "xanimu": _XanimuAdapter,
    "ptt": _PttAdapter,
    "jm": _JmAdapter,
    "wnacg": _WnacgAdapter,
    "amd": _AmdAdapter,
    "superporn": _SuperpornAdapter,
    "dage": _DageAdapter,
    "javdb": _JavdbAdapter,
    "xvideos": _XvideosAdapter,
    "comic": _ComicAdapter,
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

    CLASS_RE = re.compile(
        r'<a[^>]+href="([^"]*?(?:/vodtype/\d+|/index\.php/vod/type/id/\d+)[^"]*)"[^>]*>(.*?)</a>',
        re.S)
    CATS_TTL = 86400

    def cats_for(self, platform):
        """分类来源优先级：运行时缓存 → 快照 classes → 适配器自实现 categories()。"""
        cached = self.cache_get("x99dh:cats:" + platform["key"])
        if cached and time.time() - cached.get("ts", 0) < self.CATS_TTL:
            cats = cached.get("cats") or []
            if cats:
                return cats
        cats = platform.get("classes") or []
        if cats:
            return cats
        # 快照没带分类时，问适配器要（各平台入口形态不同，适配器最清楚）
        try:
            lines = [l["url"] for l in (platform.get("lines") or []) if l.get("ok")] or \
                    [l["url"] for l in (platform.get("lines") or [])]
            if not lines:
                return []
            cls = ADAPTERS.get(platform.get("adapter") or "generic", _GenericAdapter)
            adapter = cls(self, platform, lines[0])
            got = adapter.categories() or []
            if got:
                self.cache_set("x99dh:cats:" + platform["key"],
                               {"cats": got, "ts": time.time()})
            return got
        except Exception:
            return []

    def scan_categories(self, platform, timeout=HTTP_TIMEOUT):
        """抓 /enter 页解析分类，写缓存。"""
        base = ""
        lines = platform.get("lines") or []
        if lines:
            parts = urllib.parse.urlsplit(lines[0].get("url") or "")
            base = parts.scheme + "://" + parts.netloc
        if not base:
            return []
        html = self.http(base + "/enter") or ""
        if "vodtype" not in html and "/vod/type/" not in html:
            html = self.http(base + "/") or ""
        cats, seen = [], set()
        for href, label in self.CLASS_RE.findall(html):
            match = re.search(r"(?:vodtype|vod/type/id)/(\d+)", href)
            text = re.sub(r"<[^>]+>", "", label).strip()
            if not match or not text or len(text) > 14:
                continue
            tid = match.group(1)
            if tid in seen:
                continue
            seen.add(tid)
            cats.append({"type_id": tid, "type_name": text, "href": href})
        if cats:
            self.cache_set("x99dh:cats:" + platform["key"], {"cats": cats, "ts": time.time()})
        return cats

    LIST_TTL = 180
    LIST_MAX = 40

    def _lists(self):
        store = self.cache_get("x99dh:lists")
        return store if isinstance(store, dict) else {}

    def _list_get(self, key):
        item = self._lists().get(key)
        if item and time.time() - item.get("ts", 0) < self.LIST_TTL:
            return item.get("data")
        return None

    def _list_put(self, key, data):
        now = time.time()
        store = {k: v for k, v in self._lists().items()
                 if isinstance(v, dict) and now - v.get("ts", 0) < self.LIST_TTL}
        store[key] = {"data": data, "ts": now}
        if len(store) > self.LIST_MAX:
            newest = sorted(store.items(), key=lambda kv: kv[1].get("ts", 0), reverse=True)
            store = dict(newest[:self.LIST_MAX])
        self.cache_set("x99dh:lists", store)

    def _prefetch(self, platform, cate):
        """返回列表后，后台把同平台接下来的 1-2 个分类也抓一遍。"""
        now = time.time()
        seen = getattr(self, "_prefetched", None)
        if seen is None:
            seen = self._prefetched = {}
        key = platform["key"]
        if now - seen.get(key, 0) < 600:
            return
        seen[key] = now

        others = [c["type_id"] for c in self.cats_for(platform) if c["type_id"] != str(cate)][:3]
        if not others:
            return
        self._prefetch_worker(platform, others)

    def _prefetch_worker(self, platform, cates):
        """并行抓若干分类并写缓存（最多 3 个线程）。"""
        adapter_cls = ADAPTERS.get(platform.get("adapter") or "generic", _GenericAdapter)

        def job(cate):
            if self._list_get("%s|%s|1" % (platform["key"], cate)) is not None:
                return
            try:
                host = self._picker.pick(platform)
                res = adapter_cls(self, platform, host).list(cate, 1)
                if res.get("list"):
                    self._list_put("%s|%s|1" % (platform["key"], cate), res)
            except Exception:
                pass

        threads = []
        for cate in cates[:3]:
            th = threading.Thread(target=job, args=(cate,))
            th.daemon = True
            th.start()
            threads.append(th)
        for th in threads:
            th.join(6)

    def warm_first_tabs(self):
        """首屏后台预热前 3 个平台的首个分类（约 180KB 流量），本次进程只做一次。"""
        if getattr(self, "_warmed", False):
            return
        self._warmed = True

        def work():
            time.sleep(1)
            # 只预热"有分类"的平台（当前 6 个），每个抓首个分类，约 360KB
            for platform in (self._snapshot.get("platforms") or []):
                cats = self.cats_for(platform)
                if cats:
                    self._prefetch_worker(platform, [cats[0]["type_id"]])

        th = threading.Thread(target=work)
        th.daemon = True
        th.start()

    def kick_refresh(self):
        """后台把各平台分类刷新一遍，不阻塞首屏。"""
        if getattr(self, "_refreshing", False):
            return
        self._refreshing = True

        def work():
            try:
                pending = []
                for platform in self._snapshot.get("platforms") or []:
                    if platform.get("adapter") == "missav":
                        continue
                    cached = self.cache_get("x99dh:cats:" + platform["key"])
                    if not (cached and time.time() - cached.get("ts", 0) < self.CATS_TTL):
                        pending.append(platform)
                for index in range(0, len(pending), 4):
                    threads = []
                    for platform in pending[index:index + 4]:
                        th = threading.Thread(target=self._safe_scan, args=(platform,))
                        th.daemon = True
                        th.start()
                        threads.append(th)
                    for th in threads:
                        th.join(8)
            finally:
                self._refreshing = False

        th = threading.Thread(target=work)
        th.daemon = True
        th.start()

    def _safe_scan(self, platform):
        try:
            self.scan_categories(platform)
        except Exception:
            pass

    # ---------- 请求与响应（宿主契约要求的 fetch） ----------
    def headers(self):
        return {"User-Agent": UA, "Accept-Language": "zh-CN,zh;q=0.9"}

    def http(self, url, referer=None, headers=None):
        hdrs = self.headers()
        if referer:
            hdrs["Referer"] = referer
        if headers:
            hdrs.update(headers)
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
                    for c in self.cats_for(platform)
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
        self.kick_refresh()
        self.warm_first_tabs()
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

        cache_key = "%s|%s|%s" % (platform["key"], cate, pg)
        hit = self._list_get(cache_key)
        if hit is not None:
            return hit

        adapter_cls = ADAPTERS.get(platform.get("adapter") or "generic", _GenericAdapter)
        try:
            result = adapter_cls(self, platform, host).list(cate, pg)
            if result.get("list"):
                self._list_put(cache_key, result)
                self._prefetch(platform, cate)
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
