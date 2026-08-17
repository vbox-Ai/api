# -*- coding: utf-8 -*-
"""
AVtop10 TVBox Spider — vbox 适配版
站点: avtop10.com

vbox 适配：
1. 基类导入 try/except + as _B
2. 补 getDependence(['requests', 'lxml']) + warnings
3. header 格式 → dict
4. session.verify = False
5. homeVideoContent 精简返回 {"list": [...]}
6. playerContent iframe 递归加深度限制
7. extract_play 多策略提取逻辑原样保留
"""
import re, json, html as htmllib, warnings
from urllib.parse import urljoin, quote
from concurrent.futures import ThreadPoolExecutor, as_completed

warnings.filterwarnings("ignore")

try:
    import requests
except ImportError:
    requests = None
try:
    import urllib3
    urllib3.disable_warnings()
except ImportError:
    pass
try:
    from lxml import etree
except ImportError:
    etree = None

import sys
sys.path.append('..')
try:
    from base.spider import Spider as _B
except ImportError:
    class _B:
        pass


# ---------- 工具函数 ----------
def fix_url(url, host):
    if not url:
        return ""
    if url.startswith("//"):
        return "https:" + url
    if url.startswith("/"):
        return urljoin(host, url)
    if url.startswith("http"):
        return url
    return urljoin(host, "/" + url)


def clean_text(text):
    if not text:
        return ""
    return htmllib.unescape(re.sub(r"<[^>]+>", "", str(text))).strip()


def clean_trailing_garbage(url):
    if not url:
        return url
    url = htmllib.unescape(url)
    url = re.sub(r'["\'<>\s].*$', '', url)
    return url


def find_media_recursive(obj):
    if isinstance(obj, dict):
        for v in obj.values():
            res = find_media_recursive(v)
            if res:
                return res
    elif isinstance(obj, list):
        for item in obj:
            res = find_media_recursive(item)
            if res:
                return res
    elif isinstance(obj, str) and ('.m3u8' in obj or '.mp4' in obj):
        return obj
    return None


def extract_play(html, host, _depth=0):
    """增强版播放链接提取，递归深度限制"""
    if _depth >= 2:
        return ''

    # 1. video / source 标签属性
    patterns = [
        r'<video[^>]+src=["\']([^"\']+\.(?:m3u8|mp4)[^"\']*)["\']',
        r'<source[^>]+src=["\']([^"\']+\.(?:m3u8|mp4)[^"\']*)["\']',
        r'data-video-src=["\']([^"\']+\.(?:m3u8|mp4)[^"\']*)["\']',
        r'data-url=["\']([^"\']+\.(?:m3u8|mp4)[^"\']*)["\']',
        r'data-src=["\']([^"\']+\.(?:mp4)[^"\']*)["\']',
    ]
    for pat in patterns:
        m = re.search(pat, html, re.I)
        if m:
            url = m.group(1)
            if url and not url.startswith('${') and 'cdnUrl' not in url:
                return fix_url(clean_trailing_garbage(url), host)

    # 2. script 中的 JSON 数据
    script_blocks = re.findall(r'<script[^>]*>([\s\S]*?)</script>', html)
    for script in script_blocks:
        # 2.1 player_data
        m = re.search(r'player_data\s*=\s*(\{.*?\})', script, re.DOTALL)
        if m:
            try:
                data = json.loads(m.group(1))
                url = data.get('url', '')
                if url and ('.m3u8' in url or '.mp4' in url):
                    return fix_url(clean_trailing_garbage(url), host)
            except:
                pass
        # 2.2 __INITIAL_STATE__
        m = re.search(r'__INITIAL_STATE__\s*=\s*(\{.*?\})', script, re.DOTALL)
        if m:
            try:
                data = json.loads(m.group(1))
                url = find_media_recursive(data)
                if url:
                    return fix_url(clean_trailing_garbage(url), host)
            except:
                pass
        # 2.3 window.__NUXT__
        m = re.search(r'window\.__NUXT__\s*=\s*(\{.*?\});', script, re.DOTALL)
        if m:
            try:
                data = json.loads(m.group(1))
                url = find_media_recursive(data)
                if url:
                    return fix_url(clean_trailing_garbage(url), host)
            except:
                pass

    # 2.4 __NEXT_DATA__
    m = re.search(r'<script\s+id="__NEXT_DATA__"[^>]*>(\{.*?\})</script>', html, re.DOTALL)
    if m:
        try:
            data = json.loads(m.group(1))
            url = find_media_recursive(data)
            if url:
                return fix_url(clean_trailing_garbage(url), host)
        except:
            pass

    # 3. 通用正则兜底
    m = re.search(r'(https?://[^\s"\'<>]+\.(?:m3u8|mp4)(?:[^\s"\'<>]*)?)', html)
    if m:
        url = m.group(1)
        if 'cdnUrl' not in url and '${' not in url:
            return clean_trailing_garbage(url)

    # 4. iframe 递归（加深度限制）
    m = re.search(r'<iframe[^>]+src=["\']([^"\']+)["\']', html)
    if m:
        iframe_src = m.group(1)
        if iframe_src.startswith('//'):
            iframe_src = 'https:' + iframe_src
        elif iframe_src.startswith('/'):
            iframe_src = urljoin(host, iframe_src)
        try:
            sub_html = requests.get(iframe_src, headers={
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
                'Referer': host
            }, timeout=10, verify=False).text
            return extract_play(sub_html, host, _depth=_depth + 1)
        except:
            pass

    return ''


# ---------- 蜘蛛主类 ----------
class Spider(_B):

    def getDependence(self):
        return ['requests', 'lxml']

    def __init__(self):
        self.host = "https://avtop10.com"
        self.s = requests.Session()
        self.s.verify = False
        self.s.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'zh-CN,zh;q=0.9',
            'Referer': self.host + '/',
        })
        self.seen_ids = set()

    def getName(self):
        return "AVTOP10"

    def init(self, extend=""):
        if extend and extend.startswith('http'):
            self.host = extend.rstrip('/')

    def isVideoFormat(self, url):
        return any(x in url for x in ['.m3u8', '.mp4', '.flv', '.ts'])

    def manualVideoCheck(self):
        return False

    def destroy(self):
        pass

    def localProxy(self, param):
        return [200, "video/MP2T", b"", {}]

    def _fetch(self, url, mobile=False):
        try:
            headers = self.s.headers.copy()
            if mobile:
                headers['User-Agent'] = 'Mozilla/5.0 (Linux; Android 10; K) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/118.0.0.0 Mobile Safari/537.36'
            r = requests.get(url, headers=headers, timeout=15, verify=False)
            r.raise_for_status()
            if r.encoding is None or r.encoding.lower() == 'iso-8859-1':
                r.encoding = r.apparent_encoding or 'utf-8'
            return r.text
        except Exception as e:
            print(f"[AVTOP10] 请求失败: {url} - {e}")
            return ""

    # ==================== 首页 ====================
    def homeContent(self, filter):
        try:
            classes = [
                {"type_id": "chinese-subtitle", "type_name": "中文字幕"},
                {"type_id": "madou", "type_name": "国产AV"},
                {"type_id": "genres/%E5%A4%96%E5%9B%BD%E5%A5%B3%E4%BC%98", "type_name": "欧美大片"},
                {"type_id": "new", "type_name": "最近更新"},
                {"type_id": "release", "type_name": "新作上市"},
                {"type_id": "uncensored-leak", "type_name": "無碼流出"},
                {"type_id": "VR", "type_name": "VR"},
                {"type_id": "fc2", "type_name": "FC2"},
                {"type_id": "heyzo", "type_name": "HEYZO"},
                {"type_id": "1pondo", "type_name": "一本道"},
                {"type_id": "caribbeancom", "type_name": "Caribbeancom"},
            ]
            return {"class": classes, "filters": {}}
        except Exception as e:
            print(f"[AVTOP10] 首页失败: {e}")
            return {"class": [], "filters": {}}

    def homeVideoContent(self):
        try:
            result = self.categoryContent("new", "1", False, {})
            return {"list": result.get("list", [])}
        except Exception:
            return {"list": []}

    # ==================== 分类列表 ====================
    def categoryContent(self, tid, pg, filter, extend):
        try:
            result = {"list": [], "page": int(pg), "pagecount": 1, "limit": 24, "total": 0}
            url = f"{self.host}/{tid}?page={pg}"
            html_text = self._fetch(url)
            if not html_text:
                return result
            doc = etree.HTML(html_text)
            if doc is None:
                return result
            items = doc.xpath('//div[contains(@class,"thumbnail")]')
            if not items:
                items = doc.xpath('//div[contains(@class,"group")]')
            self.seen_ids.clear()
            for item in items:
                try:
                    a = item.xpath('.//a[contains(@href,"/")]')
                    if not a:
                        continue
                    href = a[0].xpath('./@href')[0] if a[0].xpath('./@href') else ""
                    vid = href.strip('/').split('/')[-1] if href else ""
                    if not vid or vid in self.seen_ids:
                        continue
                    self.seen_ids.add(vid)
                    title_elem = item.xpath('.//div[contains(@class,"my-2")]//a/text()')
                    title = clean_text(title_elem[0]) if title_elem else vid
                    img = item.xpath('.//img/@data-src') or item.xpath('.//img/@src')
                    pic = fix_url(img[0], self.host) if img else ""
                    result["list"].append({"vod_id": vid, "vod_name": title, "vod_pic": pic})
                except Exception:
                    continue
            result["pagecount"] = int(pg) + 1
            return result
        except Exception as e:
            print(f"[AVTOP10] 分类爬取失败: {e}")
            return {"list": [], "page": int(pg), "pagecount": 1, "limit": 24, "total": 0}

    # ==================== 搜索 ====================
    def searchContent(self, key, quick, pg="1"):
        try:
            result = {"list": [], "page": int(pg), "pagecount": 1, "limit": 24, "total": 0}
            url = f"{self.host}/search?keyword={quote(key)}&page={pg}"
            html_text = self._fetch(url)
            if not html_text:
                return result
            doc = etree.HTML(html_text)
            if doc is None:
                return result
            items = doc.xpath('//div[contains(@class,"thumbnail")]')
            self.seen_ids.clear()
            for item in items:
                try:
                    a = item.xpath('.//a[contains(@href,"/")]')
                    if not a:
                        continue
                    href = a[0].xpath('./@href')[0] if a[0].xpath('./@href') else ""
                    vid = href.strip('/').split('/')[-1] if href else ""
                    if not vid or vid in self.seen_ids:
                        continue
                    self.seen_ids.add(vid)
                    title_elem = item.xpath('.//div[contains(@class,"my-2")]//a/text()')
                    title = clean_text(title_elem[0]) if title_elem else vid
                    img = item.xpath('.//img/@data-src') or item.xpath('.//img/@src')
                    pic = fix_url(img[0], self.host) if img else ""
                    result["list"].append({"vod_id": vid, "vod_name": title, "vod_pic": pic})
                except Exception:
                    continue
            result["pagecount"] = int(pg) + 1
            return result
        except Exception as e:
            print(f"[AVTOP10] 搜索失败: {e}")
            return {"list": [], "page": int(pg), "pagecount": 1, "limit": 24, "total": 0}

    # ==================== 详情 ====================
    def detailContent(self, ids):
        try:
            vid = ids[0] if isinstance(ids, list) else ids
            result = {"list": []}
            url = f"{self.host}/{vid}"
            html_text = self._fetch(url)
            if not html_text:
                return result
            doc = etree.HTML(html_text)
            if doc is None:
                return result

            # 标题
            title = ""
            title_candidates = [
                doc.xpath('//h1/text()'),
                doc.xpath('//h2/text()'),
                doc.xpath('//meta[@property="og:title"]/@content'),
                doc.xpath('//title/text()'),
            ]
            for cand in title_candidates:
                if cand:
                    title = clean_text(cand[0])
                    break
            if not title:
                title = vid

            # 封面
            pic = ""
            pic_candidates = [
                doc.xpath('//meta[@property="og:image"]/@content'),
                doc.xpath('//img[contains(@class,"cover") or contains(@class,"poster")]/@src'),
                doc.xpath('//img/@data-src'),
                doc.xpath('//img/@src'),
            ]
            for cand in pic_candidates:
                if cand:
                    pic = fix_url(cand[0], self.host)
                    break

            # 简介
            desc = ""
            desc_candidates = [
                doc.xpath('//meta[@name="description"]/@content'),
                doc.xpath('//meta[@property="og:description"]/@content'),
                doc.xpath('//div[contains(@class,"description")]//text()'),
                doc.xpath('//div[contains(@class,"content")]//p/text()'),
                doc.xpath('//div[contains(@class,"entry-content")]//text()'),
                doc.xpath('//div[contains(@class,"synopsis")]//text()'),
            ]
            for cand in desc_candidates:
                if cand:
                    text = ' '.join([clean_text(c) for c in cand if clean_text(c)])
                    if text and len(text) > 20:
                        desc = text[:500]
                        break
            if not desc:
                body_text = doc.xpath('//body//text()')
                visible = [clean_text(t) for t in body_text if clean_text(t) and len(clean_text(t)) > 2]
                desc = ' '.join(visible)[:200]

            # 播放地址（多候选页）
            play_pages = [
                f"{self.host}/{vid}",
                f"{self.host}/player/{vid}",
                f"{self.host}/watch/{vid}",
            ]
            names = ["正片详情页", "播放器页", "备用页"]
            result["list"].append({
                "vod_id": vid,
                "vod_name": title,
                "vod_pic": pic,
                "vod_content": desc,
                "vod_play_from": "$$$".join(names),
                "vod_play_url": "$$$".join(play_pages)
            })
            return result
        except Exception as e:
            print(f"[AVTOP10] 详情解析失败: {e}")
            return {"list": []}

    # ==================== 播放 ====================
    def playerContent(self, flag, id, vipFlags=None):
        header = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            'Referer': self.host + '/',
            'Origin': self.host,
        }
        try:
            # 已是直链
            if self.isVideoFormat(id):
                return {'parse': 0, 'url': id, 'header': header}

            # 优先移动端UA
            html_text = self._fetch(id, mobile=True)
            if not html_text:
                html_text = self._fetch(id)

            if html_text:
                play_url = extract_play(html_text, self.host)
                if play_url:
                    play_url = clean_trailing_garbage(play_url)
                    header['Referer'] = id
                    return {'parse': 0, 'url': play_url, 'header': header}

                # 尝试API接口
                vid = id.rstrip('/').split('/')[-1]
                api_urls = [
                    f"{self.host}/api/play/{vid}",
                    f"{self.host}/api/video/{vid}",
                    f"{self.host}/play/geturl?id={vid}",
                    f"{self.host}/ajax/play/{vid}",
                    f"{self.host}/dplay?url={quote(id)}",
                ]
                for api_url in api_urls:
                    try:
                        resp = self.s.get(api_url, headers={
                            "X-Requested-With": "XMLHttpRequest",
                            "Referer": id,
                            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
                        }, timeout=10)
                        if resp.status_code == 200:
                            ctype = resp.headers.get('Content-Type', '')
                            if 'json' in ctype:
                                data = resp.json()
                                play_url = data.get('url') or data.get('data', {}).get('url')
                                if play_url and ('.mp4' in play_url or '.m3u8' in play_url):
                                    play_url = clean_trailing_garbage(play_url)
                                    header['Referer'] = id
                                    return {'parse': 0, 'url': play_url, 'header': header}
                            else:
                                m = re.search(r'(https?://[^\s"\'<>]+\.(?:mp4|m3u8)[^\s"\'<>]*)', resp.text)
                                if m:
                                    play_url = clean_trailing_garbage(m.group(1))
                                    header['Referer'] = id
                                    return {'parse': 0, 'url': play_url, 'header': header}
                    except:
                        continue

            # 全部失败
            return {'parse': 1, 'url': id, 'header': header}
        except Exception as e:
            print(f"[AVTOP10] 播放解析异常: {e}")
            return {'parse': 1, 'url': id, 'header': header}
