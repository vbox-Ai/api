#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
国色天香 / 我草视频 - vbox 远程源适配版 (替换仓库旧版 v2, 域更至 wckz813.vip)
目标: 动态域名自适应 + 多域名并发竞速(首个响应域名缓存10分钟)
修复: 2026-08-16 更新域名至 wckz813.vip, 修复881响应解析, 修复data.json解析
适配: 继承 SpiderBase + super().init(extend) + localProxy三元组 + 封面走本地代理(XOR解密)
"""
import sys
sys.path.append('..')
import json
import html as html_module
import re
import time
import threading
import ssl
import urllib.request
import urllib.parse
from urllib.parse import quote, urljoin, unquote

try:
    from base.spider import Spider as SpiderBase
except ImportError:
    class SpiderBase(object):
        def __init__(self):
            self._vbox_effective_hosts = []
        def getCache(self, key): return None
        def setCache(self, key, value): return "fail"
        def delCache(self, key): return "fail"


# ========== 解密映射表 (来自 public.min.js) ==========
_DECRYPT_MAP = {
    'e':'P','w':'D','T':'y','+':'J','l':'!','t':'L','E':'E','@':'2','d':'a','b':'%',
    'q':'l','X':'v','~':'R','5':'r','&':'X','C':'j',']':'F','a':')','^':'m',',':'~',
    '}':'1','x':'C','c':'(','G':'@','h':'h','.':'*','L':'s','=':',','p':'g','I':'Q',
    '1':'7','_':'u','K':'6','F':'t','2':'n','8':'=','k':'G','Z':']',')':'b','P':'}',
    'B':'U','S':'k','6':'i','g':':','N':'N','i':'S','%':'+','-':'Y','?':'|','4':'z',
    '*':'-','3':'^','[':'{','(':'c','u':'B','y':'M','U':'Z','H':'[','z':'K','9':'H',
    '7':'f','R':'x','v':'&','!':';','M':'_','Q':'9','Y':'e','o':'4','r':'A','m':'.',
    'O':'o','V':'W','J':'p','f':'d',':':'q','{':'8','W':'I','j':'?','n':'5','s':'3',
    '|':'T','A':'V','D':'w',';':'O'
}

# 默认基础域名(多域名并发竞速候选池)
_BACKUP_BASE_URLS = [
    "https://VwLYxvSnvzcai.wckz813.vip:8801",
    "https://2tcW6DEkfnvzcai.wckz813.vip:8801",
    "https://QXxadAnnvzcai.wckz813.vip:8801",
    "https://iin.wckk799.vip:8801",
]

# 封面远程代理 (XOR 0x88 加密 webp)
_COVER_PROXY = "http://xg3.mingapi.top/tvbox/php/国色天香_pic.php"

DOMAIN_CACHE_TTL = 600  # 域名缓存 10 分钟


def decrypt_text(text: str) -> str:
    """解密网站加密文本(标题/分类名等)"""
    if not text or not isinstance(text, str):
        return ""
    result = "".join(_DECRYPT_MAP.get(ch, ch) for ch in text)
    return html_module.unescape(result)


def _extract_redirect_url_from_881(html_text: str) -> str:
    """从 HTTP 881 响应的 HTML 中提取跳转目标 URL。"""
    if not html_text:
        return ""

    # 格式1: document.write(decodeURIComponent("..."))
    m = re.search(r'document\.write\(decodeURIComponent\("([^"]+)"\)\)', html_text)
    if m:
        decoded = html_module.unescape(m.group(1))
        decoded2 = unquote(decoded)
        m2 = re.search(r'var\s+url\s*=\s*["\x27](https?://[^"\x27]+)["\x27]', decoded2)
        if m2:
            redirect = m2.group(1)
            if redirect.endswith('/index.htm'):
                redirect = redirect[:-len('/index.htm')]
            return redirect
        m3 = re.search(r'window\.location\.replace\(["\x27](https?://[^"\x27]+)["\x27]\)', decoded2)
        if m3:
            redirect = m3.group(1)
            if redirect.endswith('/index.htm'):
                redirect = redirect[:-len('/index.htm')]
            return redirect

    # 格式2: 直接的 var url
    m = re.search(r'var\s+url\s*=\s*["\x27](https?://[^"\x27]+)["\x27]', html_text)
    if m:
        redirect = m.group(1)
        if redirect.endswith('/index.htm'):
            redirect = redirect[:-len('/index.htm')]
        return redirect

    # 格式3: window.location.replace
    m2 = re.search(r'window\.location\.replace\(["\x27](https?://[^"\x27]+)["\x27]\)', html_text)
    if m2:
        redirect = m2.group(1)
        if redirect.endswith('/index.htm'):
            redirect = redirect[:-len('/index.htm')]
        return redirect

    # 格式4: location.href
    m3 = re.search(r'location\.href\s*=\s*["\x27](https?://[^"\x27]+)["\x27]', html_text)
    if m3:
        redirect = m3.group(1)
        if redirect.endswith('/index.htm'):
            redirect = redirect[:-len('/index.htm')]
        return redirect

    return ""


_SSL_CTX = None
def _ssl_ctx():
    global _SSL_CTX
    if _SSL_CTX is None:
        _SSL_CTX = ssl.create_default_context()
        _SSL_CTX.check_hostname = False
        _SSL_CTX.verify_mode = ssl.CERT_NONE
    return _SSL_CTX


class Spider(SpiderBase):
    PLATFORM_KEY = "guotianxiang_py"
    _UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")
    _TIMEOUT = 15

    def __init__(self):
        try:
            super(Spider, self).__init__()
        except Exception:
            pass
        self.siteUrl = _BACKUP_BASE_URLS[0]
        self.userAgent = self._UA

        # 动态域名信息
        self.css_domain = ""
        self.pic_domain = ""
        self.novel_domain = ""
        self.csstime = ""
        self.channel_id = ""

        # 域名竞速缓存 (10分钟)
        self._domain_winner = None
        self._domain_winner_ts = 0.0
        self._domain_lock = threading.Lock()
        self._candidates = list(_BACKUP_BASE_URLS)

        # 分类 10 分钟缓存
        self._class_cache = None
        self._class_cache_ts = 0.0

    # ==================== 多域名并发竞速 ====================
    def _probe_domain(self, domain: str) -> bool:
        """探测单个域名: /data.json 返回 200 或可提取跳转的 881 即视为可用"""
        if not domain:
            return False
        try:
            req = urllib.request.Request(domain + "/data.json", headers={"User-Agent": self.userAgent})
            with urllib.request.urlopen(req, timeout=8, context=_ssl_ctx()) as resp:
                code = resp.getcode()
                if code == 200:
                    return True
                body = resp.read().decode("utf-8", "ignore")
                if code == 881:
                    return bool(_extract_redirect_url_from_881(body))
                return False
        except urllib.error.HTTPError as e:
            if e.code == 881:
                try:
                    body = e.read().decode("utf-8", "ignore")
                except Exception:
                    body = ""
                if body:
                    redirect = _extract_redirect_url_from_881(body)
                    if redirect and redirect not in self._candidates:
                        self._candidates.append(redirect)
                    return bool(redirect)
            return False
        except Exception:
            return False

    def _resolve_site_url(self, default_url: str = None) -> str:
        """并发竞速获取最快可用域名, 胜者缓存 10 分钟"""
        default_url = default_url or self.siteUrl
        now = time.time()

        if self._domain_winner and (now - self._domain_winner_ts) < DOMAIN_CACHE_TTL:
            self.siteUrl = self._domain_winner
            return self.siteUrl

        # 候选: 当前 siteUrl + default + 备用池
        candidates = [default_url] + [d for d in self._candidates if d and d not in [default_url]]
        seen = set()
        unique = []
        for c in candidates:
            if c not in seen:
                seen.add(c)
                unique.append(c)
        candidates = unique

        winner = None
        def _race(d):
            nonlocal winner
            if self._probe_domain(d):
                with self._domain_lock:
                    if winner is None:
                        winner = d

        threads = [threading.Thread(target=_race, args=(d,), daemon=True) for d in candidates]
        for t in threads:
            t.start()
        deadline = time.time() + 10
        while time.time() < deadline:
            with self._domain_lock:
                if winner is not None:
                    break
            time.sleep(0.2)

        if winner:
            self._domain_winner = winner
            self._domain_winner_ts = time.time()
            final_url = winner
        else:
            final_url = default_url

        # 881 跳转链追踪 (胜者若需跳转则跟随)
        final_url = self._chase_881(final_url)

        self.siteUrl = final_url.rstrip("/")
        return self.siteUrl

    def _chase_881(self, url: str, max_hops: int = 2) -> str:
        try:
            req = urllib.request.Request(url + "/data.json", headers={"User-Agent": self.userAgent})
            with urllib.request.urlopen(req, timeout=8, context=_ssl_ctx()) as resp:
                if resp.getcode() == 200:
                    return url
                body = resp.read().decode("utf-8", "ignore")
        except urllib.error.HTTPError as e:
            body = e.read().decode("utf-8", "ignore") if e.code == 881 else ""
            if e.code != 881:
                return url
        except Exception:
            return url

        redirect = _extract_redirect_url_from_881(body)
        if redirect:
            return self._chase_881(redirect, max_hops - 1)
        return url

    def refresh_domains(self) -> bool:
        """从 /data.json 抓取动态域名信息, 支持备用域名切换 (并发竞速首个成功)"""
        now = time.time()
        if self._domain_winner and (now - self._domain_winner_ts) < DOMAIN_CACHE_TTL:
            candidate = self._domain_winner
        else:
            candidate = self.siteUrl

        candidates = [candidate] + [c for c in self._candidates if c != candidate]
        seen = set()
        unique = []
        for c in candidates:
            if c and c not in seen:
                seen.add(c)
                unique.append(c)

        # 并发: 每个候选独立尝试解析 data.json, 首个成功者胜出
        result = {"ok": False, "candidate": None}
        def _try(c):
            if result["ok"]:
                return
            try:
                content = self._http_get_text(c + "/data.json")
                if content is None:
                    return
                parsed = self._parse_group(content)
                if not parsed:
                    # 881 内嵌跳转
                    redirect = _extract_redirect_url_from_881(content)
                    if redirect and redirect not in self._candidates:
                        self._candidates.append(redirect)
                    return
                with self._domain_lock:
                    if not result["ok"]:
                        result["ok"] = True
                        result["candidate"] = c
                        result["group"] = parsed
            except Exception:
                pass

        threads = [threading.Thread(target=_try, args=(c,), daemon=True) for c in unique]
        for t in threads:
            t.start()
        deadline = time.time() + 10
        while time.time() < deadline:
            if result["ok"]:
                break
            time.sleep(0.2)

        if not result["ok"]:
            return False

        group = result["group"]
        self.siteUrl = result["candidate"]
        self._domain_winner = result["candidate"]
        self._domain_winner_ts = time.time()
        self.css_domain = group.get("css_domain", "")
        self.pic_domain = group.get("pic_domain", "")
        self.novel_domain = group.get("novel_domain", "")
        self.csstime = str(group.get("csstime", ""))
        self.channel_id = str(group.get("channel_id", ""))

        if not self.pic_domain:
            self.pic_domain = self.siteUrl
        if not self.novel_domain:
            self.novel_domain = self.siteUrl
        if not self.css_domain:
            self.css_domain = self.siteUrl
        return True

    # ==================== HTTP 工具 ====================
    def _http_get_text(self, url: str, timeout: int = None) -> str:
        """GET 请求返回 text; 网络错误返回 None; 881 返回响应体"""
        try:
            req = urllib.request.Request(url, headers={"User-Agent": self.userAgent})
            with urllib.request.urlopen(req, timeout=timeout or self._TIMEOUT, context=_ssl_ctx()) as resp:
                return resp.read().decode("utf-8", "ignore")
        except urllib.error.HTTPError as e:
            if e.code == 881:
                try:
                    return e.read().decode("utf-8", "ignore")
                except Exception:
                    return None
            return None
        except Exception:
            return None

    def _parse_group(self, content: str):
        """data.json 返回的是 JS 变量格式, 不是纯 JSON"""
        if not content:
            return None
        start = content.find("var Group=")
        if start == -1:
            start = content.find("var Group =")
        end = content.find("var Token=", start if start != -1 else 0)
        if end == -1:
            end = content.find("var Token =", start if start != -1 else 0)
        if start == -1 or end == -1 or end <= start:
            return None
        json_str = content[start:end].strip()
        json_str = re.sub(r"var\s+Group\s*=\s*", "", json_str).rstrip(";").strip()
        try:
            return json.loads(json_str)
        except Exception:
            return None

    def _get_json(self, path: str, params: dict = None):
        """请求JSON接口 (相对 self.siteUrl)"""
        if path.startswith("http"):
            url = path
        else:
            url = self.siteUrl + path
        if params:
            query = "&".join("%s=%s" % (quote(str(k)), quote(str(v))) for k, v in params.items())
            sep = "&" if "?" in url else "?"
            url = url + sep + query
        text = self._http_get_text(url)
        if not text:
            return None
        try:
            return json.loads(text)
        except Exception:
            return None

    # ==================== 封面/播放地址 ====================
    def cover_url(self, serial_number: str) -> str:
        """封面 URL — 通过远程代理 XOR 解密的图片, 再包本地代理供 localProxy 取图解密"""
        if not serial_number:
            return ""
        pic_base = self.pic_domain if self.pic_domain else self.siteUrl
        css_url = f"{pic_base}/pic/{serial_number}/thumbnail.css"
        remote = f"{_COVER_PROXY}?url={quote(css_url)}"
        return self._proxy_img_url(remote, referer=self.siteUrl)

    def m3u8_url(self, serial_number: str) -> str:
        if not serial_number:
            return ""
        novel_base = self.novel_domain if self.novel_domain else self.siteUrl
        return f"{novel_base}/m3u8/{serial_number}/index_domain.m3u8?{self.csstime}"

    def _format_vod(self, item: dict) -> dict:
        serial = item.get("serial_number", "")
        return {
            "vod_id": str(item.get("id", "")),
            "vod_name": decrypt_text(item.get("title", "")),
            "vod_pic": self.cover_url(serial) if serial else "",
            "vod_remarks": str(item.get("read_number", "")),
        }

    # ==================== 本地代理 ====================
    def _proxy_base(self):
        fn = getattr(self, "getProxyUrl", None)
        if callable(fn):
            try:
                u = fn(True)
                if u:
                    return str(u)
            except Exception:
                pass
        return "http://127.0.0.1:18080/proxy?do=py&key=%s" % self.PLATFORM_KEY

    def _proxy_img_url(self, url, referer=None):
        if not url:
            return ""
        base = self._proxy_base()
        sep = "&" if "?" in base else "?"
        u = base + sep + "type=img&u=" + quote(str(url), safe="")
        if referer:
            u += "&r=" + quote(referer, safe="")
        return u

    def _serve_cover(self, url, referer=None):
        """取封面 (xg3 远程代理返回 XOR 0x88 加密 webp)"""
        try:
            headers = {"User-Agent": self.userAgent}
            if referer:
                headers["Referer"] = referer
            req = urllib.request.Request(url, headers=headers)
            with urllib.request.urlopen(req, timeout=15, context=_ssl_ctx()) as resp:
                raw = resp.read()
            # XOR 0x88 解密
            try:
                decrypted = bytes(b ^ 0x88 for b in raw)
                if decrypted[:4] in (b"\x89PNG", b"RIFF") or decrypted[:2] == b"\xff\xd8" or decrypted[:3] == b"GIF":
                    raw = decrypted
            except Exception:
                pass
            ct = "image/webp"
            if raw[:4] == b"\x89PNG":
                ct = "image/png"
            elif raw[:3] == b"GIF":
                ct = "image/gif"
            elif raw[:2] == b"\xff\xd8":
                ct = "image/jpeg"
            return [200, ct, raw]
        except Exception:
            return [502, "text/plain", b"cover fetch failed"]

    # ==================== 初始化 ====================
    def init(self, extend=""):
        try:
            super().init(extend)
        except AttributeError:
            pass

        # 域名池合并: extend 自定义 > vbox 注入 _vbox_effective_hosts > 硬编码备用池
        custom_urls = []
        if isinstance(extend, dict):
            custom_urls = extend.get("hosts") if isinstance(extend.get("hosts"), list) else []
            if extend.get("site"):
                custom_urls.insert(0, str(extend.get("site")))
        elif extend:
            custom_urls = [u.strip() for u in str(extend).split(",") if u.strip().startswith("http")]

        injected = getattr(self, "_vbox_effective_hosts", None) or []
        inj = [str(h).rstrip("/") for h in injected if str(h).startswith("http")]

        merged = []
        for u in custom_urls + inj + self._candidates:
            if u and u not in merged:
                merged.append(u)
        self._candidates = merged
        if custom_urls:
            self.siteUrl = custom_urls[0]
        elif inj:
            self.siteUrl = inj[0]

        # 动态解析网址 (并发竞速 + 10分钟缓存)
        self._resolve_site_url()

        # 刷新子域名信息
        if not self.refresh_domains():
            pass

    def getName(self):
        return "国色天香"

    # ==================== TVBox/vbox 标准接口 ====================
    def homeContent(self, filter):
        result = {"class": [], "filters": {}}
        default_classes = [
            {"type_id": "1", "type_name": "国产"},
            {"type_id": "2", "type_name": "日本"},
            {"type_id": "3", "type_name": "韩国"},
            {"type_id": "4", "type_name": "欧美"},
        ]

        # 10 分钟分类缓存
        now = time.time()
        if self._class_cache and (now - self._class_cache_ts) < 600:
            classes, filters_map = self._class_cache
            result["class"] = classes
            if filter:
                result["filters"] = filters_map
            return result

        data = self._get_json(f"/index.json?{self.csstime}")
        classes = []
        filters_map = {}

        if data and "index_videos" in data:
            for key, cat in data["index_videos"].items():
                cat_id = str(cat.get("id", key))
                cat_name = decrypt_text(cat.get("name", ""))
                if not cat_name:
                    continue
                classes.append({"type_id": cat_id, "type_name": cat_name})

                genre_filter = {
                    "key": "genre",
                    "name": "流派",
                    "value": [{"n": "全部", "v": ""}]
                }
                for g in (cat.get("genres") or []):
                    g_name = decrypt_text(g.get("name", ""))
                    if g_name:
                        genre_filter["value"].append({"n": g_name, "v": str(g.get("id", ""))})

                label_filter = {
                    "key": "label",
                    "name": "标签",
                    "value": [{"n": "全部", "v": ""}]
                }
                for l in (cat.get("labels") or []):
                    l_name = html_module.unescape(str(l.get("name", "")))
                    if l_name:
                        label_filter["value"].append({"n": l_name, "v": str(l.get("id", ""))})

                filters_map[cat_id] = [genre_filter, label_filter]

        if not classes:
            classes = default_classes

        self._class_cache = (classes, filters_map)
        self._class_cache_ts = now

        result["class"] = classes
        if filter:
            result["filters"] = filters_map
        return result

    def homeVideoContent(self):
        result = {"list": []}
        data = self._get_json(f"/index.json?{self.csstime}")
        if not data or "index_videos" not in data:
            return result

        videos = []
        seen_ids = set()
        for _, cat in data["index_videos"].items():
            for v in (cat.get("videos") or [])[:6]:
                vid = str(v.get("id", ""))
                if vid and vid not in seen_ids:
                    seen_ids.add(vid)
                    videos.append(self._format_vod(v))
        result["list"] = videos
        return result

    def categoryContent(self, tid, pg, filter, extend):
        result = {"list": [], "page": pg, "pagecount": 0, "limit": 20, "total": 0}
        api_path = f"/type/{tid}_{pg}.json?{self.csstime}"

        params = {}
        if extend and isinstance(extend, dict):
            if extend.get("genre"):
                params["genre"] = extend["genre"]
            if extend.get("label"):
                params["label"] = extend["label"]

        data = self._get_json(api_path, params=params if params else None)
        if not data:
            return result

        videos = []
        for v in (data.get("data", {}) or {}).get("videos", []) or []:
            videos.append(self._format_vod(v))

        page_count = (data.get("data", {}) or {}).get("page_count", 1)
        result.update({
            "list": videos,
            "page": pg,
            "pagecount": page_count,
            "limit": 20,
            "total": int(page_count or 0) * 20,
        })
        return result

    def detailContent(self, ids):
        result = {"list": []}
        if not ids:
            return result
        video_id = ids[0] if isinstance(ids, list) else ids

        data = self._get_json(f"/video/{video_id}.json?{self.csstime}")
        if not data or "video" not in data:
            return result

        video = data["video"]
        serial = video.get("serial_number", "")

        vod = {
            "vod_id": str(video_id),
            "vod_name": decrypt_text(video.get("title", "")),
            "vod_pic": self.cover_url(serial) if serial else "",
            "vod_remarks": str(video.get("read_number", "")),
            "vod_year": "",
            "vod_area": "",
            "vod_actor": str(video.get("actresses", "")),
            "vod_director": "",
            "vod_content": html_module.unescape(str(video.get("description", ""))),
            "vod_play_from": "默认",
            "vod_play_url": "",
        }

        if serial:
            m3u8 = self.m3u8_url(serial)
            vod["vod_play_url"] = f"播放${m3u8}"

        result["list"] = [vod]
        return result

    def searchContent(self, key, quick, pg=1):
        result = {"list": []}
        data = self._get_json("/search.json", params={"search": key})
        if not data:
            return result

        videos = []
        for v in data.get("videos", []) or []:
            videos.append(self._format_vod(v))
        result["list"] = videos
        return result

    def searchContentPage(self, key, quick, pg=1):
        return self.searchContent(key, quick, pg)

    def playerContent(self, flag, id, vipFlags):
        result = {}
        if not id:
            return result
        headers = {
            "User-Agent": self.userAgent,
            "Referer": self.siteUrl,
        }

        if self.isVideoFormat(id):
            result["parse"] = 0
            result["url"] = id
            result["header"] = headers
        else:
            play_url = f"{self.siteUrl}{id}" if not id.startswith("http") else id
            text = self._http_get_text(play_url)
            m = re.search(r'https?://[^\s"\']+\.m3u8[^\s"\']*', text or "")
            if m:
                result["parse"] = 0
                result["url"] = m.group(0)
                result["header"] = headers
            else:
                result["parse"] = 1
                result["url"] = play_url
                result["header"] = headers
        return result

    def isVideoFormat(self, url):
        if not url or not isinstance(url, str):
            return False
        if not url.startswith("http"):
            return False
        fmt = ['.mp4', '.m3u8', '.ts', '.mkv', '.avi', '.webm', '.flv']
        low = url.lower()
        return any(f in low for f in fmt)

    def manualVideoCheck(self):
        return False

    def localProxy(self, param):
        """本地代理: 封面取图 + XOR 0x88 解密 → [code, mime, bytes] 三元组"""
        p = {}
        if isinstance(param, dict):
            p = param
        elif isinstance(param, str):
            s = param.strip()
            if s.startswith("{"):
                try:
                    p = json.loads(s)
                except Exception:
                    p = {}
            elif "=" in s:
                try:
                    qs = urllib.parse.parse_qs(s.lstrip("?"))
                    p = {k: v[0] for k, v in qs.items()}
                except Exception:
                    p = {}
        t = str(p.get("type") or p.get("action") or "")
        u = unquote(str(p.get("u") or p.get("url") or ""))
        r = unquote(str(p.get("r") or "")) or None
        if t in ("img", "cover", "proxy") and u:
            return self._serve_cover(u, referer=r)
        return [404, "text/plain", b""]

    def destroy(self):
        self._class_cache = None
        self._domain_winner = None
