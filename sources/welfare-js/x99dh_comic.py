# -*- coding: utf-8 -*-
"""X99漫画导航 — vbox 远程源 python 蜘蛛（P0 骨架）

由 build_nav_source.py 生成，请勿手改。
类型: comic    快照: 2026.11.07.1434
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

KIND = "comic"
PLATFORM_KEY = "x99dh_comic_py"
TITLE = "X99漫画导航"
SNAPSHOT_VERSION = "2026.11.07.1434"
SNAPSHOT = json.loads('{"version":"2026.11.07.1434","entry":["https://x99dh.net","https://x99dh.lat"],"platforms":[{"key":"x99_6cc00cf5","name":"禁漫天堂","kind":"comic","adapter":"comic","desc":"H漫画","icon":"books.vertical.fill","url":"https://18comic66.com/enter","lines":[{"url":"https://18comic888.cc/enter","testUrl":"https://18comic888.cc/status.html","ok":true,"ms":429.0},{"url":"https://18comic01.cc/enter","testUrl":"https://18comic01.cc/status.html","ok":true,"ms":464.0},{"url":"https://18comic01.net/enter","testUrl":"https://18comic01.net/status.html","ok":true,"ms":677.0},{"url":"https://18comic1.top/enter","testUrl":"https://18comic1.top/status.html","ok":true,"ms":711.0},{"url":"https://18comic6.net/enter","testUrl":"https://18comic6.net/status.html","ok":true,"ms":805.0},{"url":"https://jmcomic.nl/enter","testUrl":"https://jmcomic.nl/status.html","ok":true,"ms":821.0},{"url":"https://18comic1.nl/enter","testUrl":"https://18comic1.nl/status.html","ok":true,"ms":933.0},{"url":"https://18comic.pw/enter","testUrl":"https://18comic.pw/status.html","ok":true,"ms":993.0},{"url":"https://18comic04.net/enter","testUrl":"https://18comic04.net/status.html","ok":true,"ms":1136.0},{"url":"https://18comic666.cc/enter","testUrl":"https://18comic666.cc/status.html","ok":true,"ms":1144.0},{"url":"https://18comic888.ws/enter","testUrl":"https://18comic888.ws/status.html","ok":true,"ms":1168.0},{"url":"https://18comic2.icu/enter","testUrl":"https://18comic2.icu/status.html","ok":true,"ms":1240.0},{"url":"https://18comic666.net/enter","testUrl":"https://18comic666.net/status.html","ok":true,"ms":1292.0},{"url":"https://18comic.nl/enter","testUrl":"https://18comic.nl/status.html","ok":true,"ms":1298.0},{"url":"https://18comic03.net/enter","testUrl":"https://18comic03.net/status.html","ok":true,"ms":1384.0},{"url":"https://18comic.cfd/enter","testUrl":"https://18comic.cfd/status.html","ok":true,"ms":1413.0},{"url":"https://18comic1.cc/enter","testUrl":"https://18comic1.cc/status.html","ok":true,"ms":1431.0},{"url":"https://18comic2.sbs/enter","testUrl":"https://18comic2.sbs/status.html","ok":true,"ms":1432.0},{"url":"https://18comic.my/enter","testUrl":"https://18comic.my/status.html","ok":true,"ms":1631.0},{"url":"https://mh99.ws/enter","testUrl":"https://mh99.ws/status.html","ok":true,"ms":1634.0},{"url":"https://mh99.cfd/enter","testUrl":"https://mh99.cfd/status.html","ok":true,"ms":1683.0},{"url":"https://18comic1.sbs/enter","testUrl":"https://18comic1.sbs/status.html","ok":true,"ms":1792.0},{"url":"https://18comic1.icu/enter","testUrl":"https://18comic1.icu/status.html","ok":true,"ms":3055.0},{"url":"https://18comic05.net/enter","testUrl":"https://18comic05.net/status.html","ok":true,"ms":3549.0},{"url":"https://18comic66.com/enter","testUrl":"https://18comic66.com/status.html","ok":true,"ms":4421.0},{"url":"https://18comic6.com/enter","testUrl":"https://18comic6.com/status.html","ok":true,"ms":4994.0},{"url":"https://18comic02.net/enter","testUrl":"https://18comic02.net/status.html","ok":true,"ms":8785.0},{"url":"https://18comic168.top/enter","testUrl":"https://18comic168.top/status.html","ok":false,"ms":825.0},{"url":"https://18comic168.cc/enter","testUrl":"https://18comic168.cc/status.html","ok":false,"ms":886.0},{"url":"https://18comic.sbs/enter","testUrl":"https://18comic.sbs/status.html","ok":false,"ms":1424.0}],"classes":[]},{"key":"x99_2f22a0a6","name":"99漫画","kind":"comic","adapter":"comic","desc":"另一个漫画站，资源多","icon":"books.vertical.fill","url":"https://www.wnacg02.net/enter","lines":[{"url":"https://wnacg.nl/enter","testUrl":"https://www.wnacg.nl/status.html","ok":true,"ms":433.0},{"url":"https://www.wnacg02.com/enter","testUrl":"https://www.wnacg02.com/status.html","ok":true,"ms":511.0},{"url":"https://wnacg.vip/enter","testUrl":"https://www.wnacg.vip/status.html","ok":true,"ms":596.0},{"url":"https://wnacg.pw/enter","testUrl":"https://www.wnacg.pw/status.html","ok":true,"ms":623.0},{"url":"https://99xmh.top/enter","testUrl":"https://www.99xmh.top/status.html","ok":true,"ms":625.0},{"url":"https://99mh.one/enter","testUrl":"https://www.99mh.one/status.html","ok":true,"ms":662.0},{"url":"https://wnacg666.com/enter","testUrl":"https://www.wnacg666.com/status.html","ok":true,"ms":717.0},{"url":"https://www.wnacg01.net/enter","testUrl":"https://www.wnacg01.net/status.html","ok":true,"ms":1095.0},{"url":"https://wnacg888.net/enter","testUrl":"https://www.wnacg888.net/status.html","ok":true,"ms":1116.0},{"url":"https://www.wnacg02.net/enter","testUrl":"https://www.wnacg02.net/status.html","ok":true,"ms":1144.0},{"url":"https://wnacg666.net/enter","testUrl":"https://www.wnacg666.net/status.html","ok":true,"ms":1160.0},{"url":"https://wnacg888.com/enter","testUrl":"https://www.wnacg888.com/status.html","ok":true,"ms":1225.0},{"url":"https://99mh.net/enter","testUrl":"https://www.99mh.net/status.html","ok":true,"ms":1476.0},{"url":"https://99mh.nl/enter","testUrl":"https://www.99mh.nl/status.html","ok":true,"ms":1500.0},{"url":"https://wnacg.my/enter","testUrl":"https://www.wnacg.my/status.html","ok":true,"ms":1759.0},{"url":"https://wnacg.sbs/enter","testUrl":"https://www.wnacg.sbs/status.html","ok":true,"ms":1887.0},{"url":"https://99mh.men/enter","testUrl":"https://www.99mh.men/status.html","ok":true,"ms":2115.0},{"url":"https://wnacg.one/enter","testUrl":"https://www.wnacg.one/status.html","ok":false,"ms":1360.0}],"classes":[]},{"key":"x99_ecb3368e","name":"爱漫岛","kind":"comic","adapter":"maccms","desc":"免费中文汉化、日本漫画、韩国漫画、10万本、色情漫画等","icon":"books.vertical.fill","url":"https://www.amdcomic.art/enter","lines":[{"url":"https://www.amdcomic.art/enter","testUrl":"https://www.amdcomic.art/status.html","ok":true,"ms":224.0},{"url":"https://www.amdcomic.one/enter","testUrl":"https://www.amdcomic.one/status.html","ok":true,"ms":844.0},{"url":"https://www.amdcomic.ws/enter","testUrl":"https://www.amdcomic.ws/status.html","ok":true,"ms":1860.0}],"classes":[{"type_id":"1","type_name":"同人","href":"/vodtype/1.html"},{"type_id":"2","type_name":"单本","href":"/vodtype/2.html"},{"type_id":"3","type_name":"短篇","href":"/vodtype/3.html"},{"type_id":"4","type_name":"韩漫","href":"/vodtype/4.html"},{"type_id":"6","type_name":"校园","href":"/vodtype/6.html"},{"type_id":"7","type_name":"幻想","href":"/vodtype/7.html"},{"type_id":"8","type_name":"都市","href":"/vodtype/8.html"},{"type_id":"9","type_name":"搞笑","href":"/vodtype/9.html"}]}]}')

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
