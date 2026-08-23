# -*- coding: utf-8 -*-
"""
平台名称：6182104.xyz
平台标识：6182104_py
作者：原始 tvshare23 · 适配：vbox Python Spider 框架
适配日期：2026-08-23
说明：
  - 继承 base.spider.Spider，super().init() 兜底
  - 域名注入：从 _vbox_effective_hosts 取候选域名
  - 3 个候选域名并发探测，先到先用
  - 10 分钟冷静期：成功域名缓存 600s，过期重新探测
  - 保留 XOR 128 标题解密
  - 返回 dict，playerContent 返回 parse=0 m3u8 直链
"""
import re
import json
import time
import requests
from urllib.parse import quote, unquote, parse_qs, urlparse
from concurrent.futures import ThreadPoolExecutor, as_completed

try:
    from base.spider import Spider as BaseSpider
except ImportError:
    class BaseSpider:
        def init(self, extend=""): pass
        def getProxyUrl(self):
            return ''

# ── 平台配置 ──────────────────────────────────
_DEFAULT_HOSTS = [
    "https://6182104.xyz",
    "https://www.6182104.xyz",
    "https://6182104.com",
]

# ── 冷静期常量 ────────────────────────────────
_PROBE_COOLDOWN = 600


class Spider(BaseSpider):
    def __init__(self):
        self._probe_cache = {}

    def getName(self):
        return "6182104"

    def init(self, extend=""):
        try:
            super().init(extend)
        except Exception:
            pass

        injected = getattr(self, '_vbox_effective_hosts', None) or []
        if injected:
            self._candidates = [str(h).rstrip('/') for h in injected]
        else:
            self._candidates = list(_DEFAULT_HOSTS)

        self.host = self._get_domain()
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Referer': self.host + '/'
        }
        self.cateManual = {
            "全部视频": "1", "香蕉精品": "13", "制服诱惑": "22",
            "国产视频": "6", "清纯少女": "8", "辣妹大奶": "9",
            "女同专属": "10", "素人出演": "11", "角色扮演": "12",
            "人妻熟女": "20", "日韩剧情": "23", "经典伦理": "21",
            "成人动漫": "7", "精品二区": "14", "精品三区": "40"
        }

    def destroy(self):
        pass

    def isVideoFormat(self, url):
        if re.search(r'\.(m3u8|mp4|flv|avi|mkv|rmvb|wmv)(\?|#|$)', url, re.IGNORECASE):
            return True
        return False

    def manualVideoCheck(self):
        return False

    # ── 并发域名探测（带 10 分钟冷静期）────────
    def _probe_domain(self, domain):
        now = time.time()
        if domain in self._probe_cache:
            ok, ts = self._probe_cache[domain]
            if now - ts < _PROBE_COOLDOWN:
                return ok
        try:
            resp = requests.head(domain, headers=self.headers, timeout=8, allow_redirects=True)
            ok = resp.status_code < 500
        except Exception:
            ok = False
        self._probe_cache[domain] = (ok, now)
        return ok

    def _get_domain(self):
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
            return cached_ok[0]
        if need_probe:
            with ThreadPoolExecutor(max_workers=len(need_probe)) as ex:
                futs = {ex.submit(self._probe_domain, d): d for d in need_probe}
                for f in as_completed(futs):
                    d = futs[f]
                    if f.result():
                        cached_ok.append(d)
            if cached_ok:
                return cached_ok[0]
        return self._candidates[0]

    # ── XOR 128 解密 ──────────────────────────
    def decrypt(self, text):
        if not text:
            return ""
        result = []
        for ch in text:
            result.append(chr(128 ^ ord(ch)))
        return ''.join(result)

    def get_cate_url(self, tid, pg=1, wd=None):
        if wd:
            return f"{self.host}/index.php/vod/type/id/{tid}/wd/{quote(wd)}/page/{pg}.html"
        else:
            return f"{self.host}/index.php/vod/type/id/{tid}/page/{pg}.html"

    def parse_list(self, html):
        videos = []
        total_pages = 1
        m = re.search(r"totalPages='(\d+)'", html)
        if m:
            total_pages = int(m.group(1))
        pattern = r'<a[^>]*href="([^"]*\/html\/dcdc\/[^"]+)"[^>]*>(.*?)</a>'
        matches = re.findall(pattern, html, re.DOTALL)
        for href, inner in matches:
            try:
                href = href.replace('&amp;', '&')
                parsed = urlparse(href)
                params = parse_qs(parsed.query)
                v_url = params.get('v', [''])[0]
                b_url = params.get('b', [''])[0]
                pic = b_url
                if not pic:
                    img_match = re.search(r'data-original="([^"]+)"', inner)
                    if img_match:
                        pic = img_match.group(1)
                title = ""
                km_match = re.search(r'<(?:p|span)[^>]*class="[^"]*km-script[^"]*"[^>]*>(.*?)</(?:p|span)>', inner, re.DOTALL)
                if km_match:
                    title = self.decrypt(km_match.group(1).strip())
                if not title:
                    fallback_match = re.search(r'<(?:p|span)[^>]*>(.*?)</(?:p|span)>', inner, re.DOTALL)
                    if fallback_match:
                        raw = fallback_match.group(1).strip()
                        try:
                            title = self.decrypt(raw)
                        except:
                            title = raw
                if not title:
                    title = "未知"
                vod_id = href if href.startswith('http') else self.host + href
                videos.append({
                    "vod_id": vod_id, "vod_name": title, "vod_pic": pic, "vod_remarks": ""
                })
            except Exception:
                continue
        return videos, total_pages

    def homeContent(self, filter=False):
        result = {}
        classes = []
        for k in self.cateManual:
            classes.append({"type_name": k, "type_id": self.cateManual[k]})
        result['class'] = classes
        filters = {}
        for tid in self.cateManual.values():
            filters[tid] = []
        result['filters'] = filters
        try:
            url = self.get_cate_url("13", 1)
            resp = requests.get(url, headers=self.headers)
            html = resp.text
            videos, _ = self.parse_list(html)
            result['list'] = videos
        except Exception:
            result['list'] = []
        return result

    def homeVideoContent(self):
        try:
            url = self.get_cate_url("13", 1)
            resp = requests.get(url, headers=self.headers)
            html = resp.text
            videos, _ = self.parse_list(html)
            return {'list': videos}
        except:
            return {'list': []}

    def categoryContent(self, tid, pg, filter=False, extend=None):
        result = {}
        page = int(pg) if pg else 1
        wd = None
        if extend and isinstance(extend, dict):
            wd = extend.get('wd', '')
        try:
            url = self.get_cate_url(tid, page, wd)
            resp = requests.get(url, headers=self.headers)
            html = resp.text
            videos, total_pages = self.parse_list(html)
            result['list'] = videos
            result['page'] = page
            result['pagecount'] = total_pages
            result['limit'] = len(videos)
            result['total'] = total_pages * len(videos)
        except Exception:
            result['list'] = []
            result['page'] = page
            result['pagecount'] = 1
            result['limit'] = 0
            result['total'] = 0
        return result

    def get_m3u8_by_mk(self, mk):
        try:
            api_url = f"https://h5.xxoo475.org/api/v2/vod/reqplay/{mk}"
            resp = requests.get(api_url, headers=self.headers)
            data = json.loads(resp.text)
            if data.get('retcode') == 3:
                vod_url = data.get('data', {}).get('httpurl_preview', '')
            else:
                vod_url = data.get('data', {}).get('httpurl', '')
            vod_url = vod_url.replace('?300', '')
            return vod_url
        except Exception:
            return ""

    def detailContent(self, array):
        vod_id = array[0]
        result = {}
        try:
            vod_id = vod_id.replace('&amp;', '&')
            parsed = urlparse(vod_id)
            params = parse_qs(parsed.query)
            v_url = params.get('v', [''])[0]
            m_url = params.get('m', [''])[0]
            b_url = params.get('b', [''])[0]
            if v_url:
                m3u8_url = v_url
            elif m_url:
                m3u8_url = self.get_m3u8_by_mk(m_url)
            else:
                m3u8_url = ""
            title = ""
            resp = requests.get(vod_id, headers=self.headers)
            html = resp.text
            km_match = re.search(r'<(?:p|span)[^>]*class="[^"]*km-script[^"]*"[^>]*>(.*?)</(?:p|span)>', html, re.DOTALL)
            if km_match:
                title = self.decrypt(km_match.group(1).strip())
            if not title:
                path = unquote(parsed.path)
                path_match = re.search(r'/html/dcdc/(.+?)\.html', path)
                if path_match:
                    raw_title = path_match.group(1)
                    try:
                        title = self.decrypt(raw_title)
                    except:
                        title = raw_title
            if not title:
                title = "未知"
            play_from = "6182104"
            play_url = title + "$" + m3u8_url
            vod = {
                "vod_id": vod_id, "vod_name": title, "vod_pic": b_url,
                "type_name": "", "vod_year": "", "vod_area": "",
                "vod_remarks": "", "vod_actor": "", "vod_director": "",
                "vod_content": "", "vod_play_from": play_from, "vod_play_url": play_url
            }
            result['list'] = [vod]
        except Exception:
            result['list'] = []
        return result

    def searchContent(self, key, quick=False):
        result = {}
        try:
            url = self.get_cate_url("2", 1, key)
            resp = requests.get(url, headers=self.headers)
            html = resp.text
            videos, _ = self.parse_list(html)
            result['list'] = videos
        except Exception:
            result['list'] = []
        return result

    def playerContent(self, flag, id, vipFlags=None):
        m3u8_url = id
        result = {
            "parse": 0,
            "playUrl": "",
            "url": m3u8_url,
            "header": {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                "Referer": self.host + "/"
            }
        }
        return result

    def localProxy(self, param):
        return [404, 'text/plain', b'']

    def manualVideoCheck(self):
        return False