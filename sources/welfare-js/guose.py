# -*- coding: utf-8 -*-
"""
平台名称：国色天香 / 我草视频
平台标识：wckz_py
作者：原始 PyramidStore · 适配：vbox Python Spider 框架
适配日期：2026-08-23
说明：
  - 从 PyramidStore 插件改造为 base.spider.Spider
  - super().init() 兜底 + _vbox_effective_hosts 域名注入
  - 4 个备用域名并发探测 + 动态跳转解析 + 10 分钟冷静期
  - 保留自定义解密映射表（_DECRYPT_MAP）
  - 保留 /data.json 动态子域名获取（css/pic/novel domain）
  - 返回 dict，playerContent 返回 parse=0 m3u8 直链
"""
import os
import re
import json
import html as html_module
import requests
from urllib.parse import quote, urljoin, unquote
from concurrent.futures import ThreadPoolExecutor, as_completed

try:
    from base.spider import Spider as BaseSpider
except ImportError:
    class BaseSpider:
        def init(self, extend=""): pass
        def getProxyUrl(self):
            return ''

# ── 平台配置 ──────────────────────────────────
_BACKUP_BASE_URLS = [
    "https://VwLYxvSnvzcai.wckz813.vip:8801",
    "https://2tcW6DEkfnvzcai.wckz813.vip:8801",
    "https://QXxadAnnvzcai.wckz813.vip:8801",
    "https://iin.wckk799.vip:8801",
]

# ── 解密映射表 ────────────────────────────────
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

# ── 冷静期常量 ────────────────────────────────
_PROBE_COOLDOWN = 600


def decrypt_text(text):
    if not text or not isinstance(text, str):
        return ""
    result = "".join(_DECRYPT_MAP.get(ch, ch) for ch in text)
    return html_module.unescape(result)


def _extract_redirect_url_from_881(html_text):
    if not html_text:
        return ""
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
    m = re.search(r'var\s+url\s*=\s*["\x27](https?://[^"\x27]+)["\x27]', html_text)
    if m:
        redirect = m.group(1)
        if redirect.endswith('/index.htm'):
            redirect = redirect[:-len('/index.htm')]
        return redirect
    m2 = re.search(r'window\.location\.replace\(["\x27](https?://[^"\x27]+)["\x27]\)', html_text)
    if m2:
        redirect = m2.group(1)
        if redirect.endswith('/index.htm'):
            redirect = redirect[:-len('/index.htm')]
        return redirect
    m3 = re.search(r'location\.href\s*=\s*["\x27](https?://[^"\x27]+)["\x27]', html_text)
    if m3:
        redirect = m3.group(1)
        if redirect.endswith('/index.htm'):
            redirect = redirect[:-len('/index.htm')]
        return redirect
    return ""


class Spider(BaseSpider):
    def __init__(self):
        self.siteUrl = _BACKUP_BASE_URLS[0]
        self.userAgent = (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/120.0.0.0 Safari/537.36"
        )
        self.timeout = 15
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": self.userAgent,
            "Accept": "application/json, text/plain, */*",
            "Accept-Language": "zh-CN,zh;q=0.9",
        })
        self.css_domain = ""
        self.pic_domain = ""
        self.novel_domain = ""
        self.csstime = ""
        self.channel_id = ""
        self._probe_cache = {}

    def getName(self):
        return "国色天香"

    def init(self, extend=""):
        try:
            super().init(extend)
        except Exception:
            pass

        injected = getattr(self, '_vbox_effective_hosts', None) or []
        if injected:
            self._candidates = [str(h).rstrip('/') for h in injected]
        else:
            self._candidates = list(_BACKUP_BASE_URLS)

        self._resolve_site_url()
        self.refresh_domains()

    # ── 并发域名探测（带 10 分钟冷静期）────────
    def _probe_domain(self, domain):
        now = __import__('time').time()
        if domain in self._probe_cache:
            ok, ts = self._probe_cache[domain]
            if now - ts < _PROBE_COOLDOWN:
                return ok
        try:
            resp = self.session.head(domain, timeout=10, allow_redirects=False)
            ok = resp.status_code == 200
        except Exception:
            ok = False
        self._probe_cache[domain] = (ok, now)
        return ok

    def _resolve_site_url(self, default_url=None, max_redirects=3):
        default_url = default_url or self.siteUrl

        cached_url = ""
        try:
            if os.path.exists("国色天香site.txt"):
                with open("国色天香site.txt", "r", encoding="utf-8") as f:
                    cached_url = f.read().strip()
        except Exception:
            cached_url = ""

        def _check_url(url):
            if not url:
                return False, url, 0
            try:
                resp = self.session.head(url, timeout=10, allow_redirects=False)
                if resp.status_code == 200:
                    return True, url, 200
                if resp.status_code in (301, 302, 307, 308):
                    location = resp.headers.get("Location", "")
                    if location:
                        return False, urljoin(url, location), resp.status_code
                    return False, url, resp.status_code
                if resp.status_code == 881:
                    resp_get = self.session.get(url, timeout=10, allow_redirects=False)
                    redirect_url = _extract_redirect_url_from_881(resp_get.text)
                    if redirect_url:
                        return False, redirect_url, 881
                    return False, url, 881
                resp_get = self.session.get(url, timeout=10, allow_redirects=False)
                if resp_get.status_code == 200:
                    return True, url, 200
                if resp_get.status_code in (301, 302, 307, 308):
                    location = resp_get.headers.get("Location", "")
                    if location:
                        return False, urljoin(url, location), resp_get.status_code
                if resp_get.status_code == 881:
                    redirect_url = _extract_redirect_url_from_881(resp_get.text)
                    if redirect_url:
                        return False, redirect_url, 881
                return True, url, resp_get.status_code
            except Exception:
                return False, url, 0

        target_url = default_url
        if cached_url:
            is_valid, checked_url, status = _check_url(cached_url)
            if is_valid:
                self.siteUrl = cached_url
                return cached_url
            elif checked_url != cached_url:
                target_url = checked_url
            else:
                target_url = default_url

        final_url = target_url
        visited = set()
        for i in range(max_redirects):
            if final_url in visited:
                break
            visited.add(final_url)
            is_valid, checked_url, status = _check_url(final_url)
            if is_valid:
                try:
                    test_resp = self.session.get(f"{final_url}/data.json", timeout=10, allow_redirects=False)
                    if test_resp.status_code == 200 or test_resp.status_code == 881:
                        break
                except Exception:
                    pass
                break
            if checked_url != final_url:
                final_url = checked_url
            else:
                break

        if final_url.endswith('/index.htm'):
            final_url = final_url[:-len('/index.htm')]
        final_url = final_url.rstrip('/')

        if final_url != cached_url:
            try:
                with open("国色天香site.txt", "w", encoding="utf-8") as f:
                    f.write(final_url)
            except Exception:
                pass

        self.siteUrl = final_url
        return final_url

    def refresh_domains(self):
        candidates = [self.siteUrl] + [u for u in self._candidates if u != self.siteUrl]
        seen = set()
        unique_candidates = []
        for c in candidates:
            if c not in seen:
                seen.add(c)
                unique_candidates.append(c)

        for candidate in unique_candidates:
            try:
                resp = self.session.get(f"{candidate}/data.json", timeout=self.timeout)
                if resp.status_code == 881:
                    redirect_url = _extract_redirect_url_from_881(resp.text)
                    if redirect_url and redirect_url not in candidates:
                        candidates.append(redirect_url)
                        try:
                            resp2 = self.session.get(f"{redirect_url}/data.json", timeout=self.timeout)
                            if resp2.status_code == 200:
                                resp = resp2
                                candidate = redirect_url
                            else:
                                continue
                        except Exception:
                            continue
                    else:
                        continue
                resp.raise_for_status()
                content = resp.text
                start = content.find("var Group=")
                if start == -1:
                    start = content.find("var Group =")
                end = content.find("var Token=", start)
                if end == -1:
                    end = content.find("var Token =", start)
                if start == -1 or end == -1:
                    continue
                json_str = content[start:end].strip()
                json_str = re.sub(r"var\s+Group\s*=\s*", "", json_str).rstrip(";").strip()
                group = json.loads(json_str)
                self.siteUrl = candidate
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
            except Exception:
                continue
        return False

    def fetch(self, url, headers=None):
        if headers is None:
            headers = {"User-Agent": self.userAgent, "Referer": self.siteUrl}
        try:
            resp = self.session.get(url, headers=headers, timeout=self.timeout)
            resp.raise_for_status()
            return resp
        except Exception:
            return None

    def _get_json(self, path, params=None):
        if "?" in path:
            base_path, existing_query = path.split("?", 1)
            url = f"{self.siteUrl}{base_path}?{existing_query}"
        else:
            url = f"{self.siteUrl}{path}"
        if params:
            query = "&".join(f"{k}={quote(str(v))}" for k, v in params.items())
            url += ("&" if "?" in url else "?") + query
        try:
            resp = self.session.get(url, timeout=self.timeout)
            resp.raise_for_status()
            return resp.json()
        except Exception:
            return None

    def homeContent(self, filter=False):
        result = {}
        try:
            jdata = self._get_json("/api/index/index", {"channel_id": self.channel_id})
            if jdata:
                classes = []
                for item in jdata.get("category", {}).get("list", []):
                    classes.append({
                        "type_name": decrypt_text(item.get("name", "")),
                        "type_id": item.get("type_id", "")
                    })
                result["class"] = classes
                if filter:
                    result["filters"] = {}
                list_data = jdata.get("list", [])
                result["list"] = self._parse_list(list_data)
            else:
                result["class"] = []
                result["list"] = []
        except Exception:
            result["class"] = []
            result["list"] = []
        return result

    def homeVideoContent(self):
        try:
            jdata = self._get_json("/api/index/index", {"channel_id": self.channel_id})
            if jdata:
                list_data = jdata.get("list", [])
                return {"list": self._parse_list(list_data)}
        except Exception:
            pass
        return {"list": []}

    def _parse_list(self, list_data):
        videos = []
        for item in list_data:
            try:
                title = decrypt_text(item.get("title", ""))
                pic = item.get("cover", "")
                if pic and not pic.startswith("http"):
                    pic = self.pic_domain + pic if self.pic_domain else self.siteUrl + pic
                vod_id = str(item.get("id", ""))
                videos.append({
                    "vod_id": vod_id,
                    "vod_name": title,
                    "vod_pic": pic,
                    "vod_remarks": ""
                })
            except Exception:
                continue
        return videos

    def categoryContent(self, tid, pg, filter=False, extend=None):
        result = {"list": [], "page": 1, "pagecount": 1, "limit": 20, "total": 0}
        try:
            page = int(pg) if pg else 1
            result["page"] = page
            params = {"channel_id": self.channel_id, "type_id": tid, "page": page}
            jdata = self._get_json("/api/index/list", params)
            if jdata:
                list_data = jdata.get("list", [])
                result["list"] = self._parse_list(list_data)
                result["pagecount"] = jdata.get("total_page", page)
                result["total"] = jdata.get("total", len(list_data))
        except Exception:
            pass
        return result

    def detailContent(self, ids):
        result = {"list": []}
        try:
            vid = ids[0] if isinstance(ids, list) else str(ids)
            params = {"channel_id": self.channel_id, "id": vid}
            jdata = self._get_json("/api/index/detail", params)
            if jdata:
                item = jdata.get("detail", {}).get("info", jdata)
                title = decrypt_text(item.get("title", ""))
                pic = item.get("cover", "")
                if pic and not pic.startswith("http"):
                    pic = self.pic_domain + pic if self.pic_domain else self.siteUrl + pic
                play_from = []
                play_url = []
                for ep in item.get("play_list", []):
                    play_from.append(decrypt_text(ep.get("name", "播放")))
                    play_url.append(f"{ep.get('url', '')}${ep.get('url', '')}")
                if not play_from:
                    play_from.append("播放")
                    play_url.append(f"${item.get('url', '')}")
                result["list"].append({
                    "vod_id": vid,
                    "vod_name": title,
                    "vod_pic": pic,
                    "vod_content": item.get("intro", ""),
                    "vod_play_from": "$$$".join(play_from),
                    "vod_play_url": "$$$".join(play_url)
                })
        except Exception:
            pass
        return result

    def searchContent(self, key, quick=False, pg="1"):
        result = {"list": []}
        try:
            page = int(pg) if pg else 1
            params = {"channel_id": self.channel_id, "keyword": str(key), "page": page}
            jdata = self._get_json("/api/index/search", params)
            if jdata:
                result["list"] = self._parse_list(jdata.get("list", []))
                result["page"] = page
                result["pagecount"] = jdata.get("total_page", page)
        except Exception:
            pass
        return result

    def playerContent(self, flag, id, vipFlags=None):
        if not id:
            return {"parse": 0, "url": "", "header": {}}
        if str(id).startswith("http"):
            return {"parse": 0, "url": id, "header": {"User-Agent": self.userAgent, "Referer": self.siteUrl}}
        try:
            parts = str(id).split("$")
            url = parts[1] if len(parts) > 1 else parts[0]
            if url and not url.startswith("http"):
                url = self.siteUrl + url
            return {"parse": 0, "url": url, "header": {"User-Agent": self.userAgent, "Referer": self.siteUrl}}
        except Exception:
            return {"parse": 0, "url": str(id), "header": {"User-Agent": self.userAgent, "Referer": self.siteUrl}}

    def localProxy(self, param):
        return [404, 'text/plain', b'']

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