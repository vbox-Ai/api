#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
平台名称：51暗网
平台标识：aw51_py
作者：原始 drpy-writer · 适配：vbox Python Spider 框架
适配日期：2026-08-19
说明：
  - 删掉 sys.path.append('..')（iOS 端无意义）
  - 删掉 init 里从 extend 读 host 的逻辑（走 base.spider 注入）
  - super().__init__() 直接调，加 try/except 兜住
  - localProxy 协议修复：不再 base64 编码 url，直接传 url 参数（getProxyUrl 携带 platformKey）
  - 并发域名探测：site_url + 4 个 CloudFront 子域 + 1 个直连备选，先到先用
  - 修复 isVideoFormat
"""

import base64
import json
import re
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
from html import unescape
from urllib.parse import quote, urljoin

import requests
from Crypto.Cipher import AES
from Crypto.Util.Padding import unpad

from base.spider import Spider as BaseSpider


class Spider(BaseSpider):
    name = "51aw"

    # 多线路候选（按优先级）
    SITE_URL = "https://51aw23.com"            # 发布页
    BASE_URL = "https://burden.gtrazibvz.com"  # 默认线路

    # 探测超时 & 整体 deadline
    PROBE_TIMEOUT = 5
    PROBE_DEADLINE = 6

    # 已知线路（CloudFront 子域）
    KNOWN_LINES = [
        "https://adjust.gtrazibvz.com",
        "https://burden.gtrazibvz.com",
        "https://borrow.gtrazibvz.com",
        "https://bite.gtrazibvz.com",
    ]

    class_name = [
        "今日吃瓜", "全网热搜", "暗网爆料", "暗网网红", "每日大赛",
        "AI短剧", "暗网反差", "暗网校园", "暗网乱伦", "暗网视频",
        "海外大片", "暗网AV解说", "暗网猎奇", "探花偷拍", "每日top",
        "寸止挑战", "动漫天堂", "暗史档案", "世界杯",
    ]
    class_url = [
        "jrrg", "qwrs", "awcg", "dywh", "mrds",
        "aidj", "fcll", "xycg", "anwangluanlun", "sxzq",
        "hwaw", "awdz", "awlq", "tanhua", "meiri-top",
        "cunzhi", "dmtt", "dark-history", "sjb",
    ]

    headers = {
        "User-Agent": ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                       "AppleWebKit/537.36 (KHTML, like Gecko) "
                       "Chrome/120.0.0.0 Safari/537.36"),
    }
    timeout = 15
    page_size = 20

    def __init__(self):
        # iOS CPython 缺 base.spider 时打日志但继续
        try:
            super().__init__()
        except Exception as e:
            print("BaseSpider init failed: %s" % e)
        self.session = requests.Session()
        self._line_checked = False
        self._selecting_line = False
        self._lock = threading.Lock()  # 保护 _selecting_line 状态

    def getName(self):
        return self.name

    def init(self, extend=''):
        # 1) 先 super，让 base.spider 从 _vbox_effective_hosts 注入 self.host
        try:
            super().init(extend)
        except Exception:
            pass

        # 2) 兜底：super 后 host 仍为空
        if not self.host:
            injected = (getattr(self, '_vbox_effective_hosts', None)
                        or globals().get('_vbox_effective_hosts')) or []
            if injected:
                self.host = str(injected[0]).rstrip('/')
                self._backup_hosts = [str(h).rstrip('/') for h in injected[1:]]
            else:
                self.host = self.BASE_URL
                self._line_checked = True
        return None

    def destroy(self):
        try:
            if self.session:
                self.session.close()
        except Exception:
            pass

    def getDependence(self):
        return []

    def homeLayout(self):
        return 0

    def isVideoFormat(self, url):
        return any(x in str(url or '').lower() for x in ('.m3u8', '.mp4', '.m3u', '.mpd'))

    def manualVideoCheck(self):
        return False

    # ──────────────────────────────────────────────
    # 发布页解析
    # ──────────────────────────────────────────────
    def _decode_publish_page(self, text):
        match = re.search(r"Base64\.decode\(['\"]([^'\"]+)", text or "", re.I)
        if not match:
            return text or ""
        try:
            return base64.b64decode(match.group(1)).decode("utf-8", errors="replace")
        except Exception:
            return text or ""

    def _line_candidates(self):
        """从发布页抽线路 + 已知线路 + 当前 host"""
        candidates = []
        # 当前 host
        if self.host:
            candidates.append(self.host)
        # 发布页
        try:
            response = self.session.get(self.SITE_URL + "/", headers=self.headers,
                                        timeout=4, allow_redirects=True)
            page = self._decode_publish_page(response.content.decode("utf-8", errors="replace"))
            for host in re.findall(r'line4Target\s*=\s*["\']([a-zA-Z0-9.-]+)', page, re.I):
                if "." in host:
                    candidates.append("https://" + host.strip("/"))
            for host in re.findall(r'https?://([a-zA-Z0-9.-]+)', page, re.I):
                if any(x in host for x in ("gtrazibvz.com", "cloudfront.net",
                                            "cvmmahzip.com", "wmwrtmwk.com")):
                    candidates.append("https://" + host.strip("/"))
        except Exception:
            pass
        # 兜底
        candidates.extend(self.KNOWN_LINES)
        # 去重保序
        result = []
        for item in candidates:
            item = str(item or "").strip().rstrip("/")
            if item.startswith(("http://", "https://")) and item not in result:
                result.append(item)
        return result

    def _line_alive(self, host):
        try:
            response = self.session.get(host + "/", headers=self.headers,
                                        timeout=self.PROBE_TIMEOUT, allow_redirects=True)
            text = response.content.decode("utf-8", errors="replace")
            return (response.status_code == 200
                    and bool(re.search(r'/archives/\d+/', text) and "post-card-title" in text))
        except Exception:
            return False

    def _line_candidates_with_injected(self):
        """注入域名 + 发布页抽出 + 已知线路"""
        cands = []
        # 1) 注入域名（用户/默认）
        try:
            injected = (getattr(self, '_vbox_effective_hosts', None)
                        or globals().get('_vbox_effective_hosts')) or []
            for h in injected:
                u = str(h).strip().rstrip('/')
                if u.startswith(('http://', 'https://')):
                    cands.append(u)
        except Exception:
            pass
        # 2) _line_candidates 的结果
        cands.extend(self._line_candidates())
        # 3) 兜底
        if self.BASE_URL not in cands:
            cands.append(self.BASE_URL)
        return cands

    def _select_line(self, force=False):
        with self._lock:
            if self._selecting_line:
                return self.host
            if self._line_checked and not force:
                return self.host
            self._selecting_line = True

        try:
            cands = self._line_candidates_with_injected()
            if not cands:
                self.host = self.BASE_URL
                self._line_checked = True
                return self.host

            with ThreadPoolExecutor(max_workers=len(cands)) as pool:
                futures = {pool.submit(self._line_alive, c): c for c in cands}
                try:
                    for fut in as_completed(futures, timeout=self.PROBE_DEADLINE):
                        if fut.result():
                            host = futures[fut]
                            for f in futures:
                                f.cancel()
                            self.host = host
                            self._line_checked = True
                            return self.host
                except Exception:
                    pass
            self.host = self.BASE_URL
            self._line_checked = True
            return self.host
        finally:
            with self._lock:
                self._selecting_line = False

    def _get(self, url, headers=None):
        h = headers or self.headers
        original_host = self.host
        try:
            if not self._line_checked and not self._selecting_line:
                self._select_line()
                if str(url).startswith(original_host) and self.host != original_host:
                    url = self.host + str(url)[len(original_host):]
            resp = self.session.get(url, headers=h, timeout=self.timeout, allow_redirects=True)
            if resp.status_code != 200:
                raise RuntimeError("HTTP %s" % resp.status_code)
            raw = resp.content
            charset = "utf-8"
            ct = resp.headers.get("Content-Type", "")
            if "charset=" in ct:
                charset = ct.split("charset=")[-1].split(";")[0].strip().lower()
            elif b"charset=" in raw[:1024]:
                m = re.search(rb"charset=[\"']?([a-zA-Z0-9-]+)", raw[:1024])
                if m:
                    charset = m.group(1).decode("ascii").lower()
            return raw.decode(charset, errors="replace")
        except Exception as e:
            # 当前线路失效时重新选线，并使用相同路径重试一次
            try:
                if not self._selecting_line and str(url).startswith(original_host):
                    path = str(url)[len(original_host):]
                    self._line_checked = False
                    self._select_line(force=True)
                    if self.host != original_host:
                        response = self.session.get(self.host + path, headers=h,
                                                    timeout=self.timeout, allow_redirects=True)
                        if response.status_code == 200:
                            return response.content.decode("utf-8", errors="replace")
            except Exception:
                pass
            print("请求失败: %s" % e)
            return None

    def _image_url(self, url):
        if not url:
            return ""
        real = urljoin(self.host + "/", unescape(str(url)).replace("\\/", "/"))
        try:
            return self.getProxyUrl() + '&type=img&url=%s' % quote(real, safe="")
        except Exception:
            return real

    def _strip_html(self, text):
        text = unescape(str(text or ""))
        text = re.sub(r"<[^>]+>", " ", text)
        return re.sub(r"\s+", " ", text).strip()

    def _extract_articles(self, html):
        result = []
        if not html:
            return result
        articles = re.findall(r"<article[^>]*>(.*?)</article>", html, re.DOTALL)
        for art in articles:
            title_m = re.search(
                r'<h2[^>]*class="[^"]*post-card-title[^"]*"[^>]*>(.*?)</h2>',
                art, re.DOTALL,
            )
            title = self._strip_html(title_m.group(1)) if title_m else ""
            if not title:
                continue
            link_m = re.search(r'href=["\'](?:https?://[^/]+)?(/archives/\d+/)["\']', art, re.I)
            link = link_m.group(1) if link_m else ""
            if not link:
                continue
            pic_m = re.search(r'<img[^>]+(?:data-original|data-src|src)=["\']([^"\']+)', art, re.I)
            if not pic_m:
                pic_m = re.search(r"(?:loadBannerDirect|loadImage)\(['\"]([^'\"]+)", art, re.I)
            pic = self._image_url(pic_m.group(1)) if pic_m else ""
            date_m = re.search(r"(\d{4}\s*年\s*\d{2}\s*月\s*\d{2}\s*日)", art)
            date = date_m.group(1).replace(" ", "") if date_m else ""
            cats = re.findall(r"<span[^>]*>([^<]+)</span>", art)
            cat_tag = ""
            for c in cats:
                c = c.strip()
                if c and not c.startswith("•") and "年" not in c and "月" not in c:
                    cat_tag = c
                    break
            result.append({
                "vod_id": link,
                "vod_name": title,
                "vod_pic": pic,
                "vod_remarks": date or cat_tag or "",
            })
        return result

    def _parse_pagecount(self, html):
        if not html:
            return 1
        m = re.search(r'class=["\'][^"\']*page-current[^"\']*["\'][^>]*>\s*(\d+)\s*/\s*(\d+)', html, re.I)
        if not m:
            m = re.search(r'<span[^>]+class=["\'][^"\']*page-current[^"\']*["\'][^>]*>\s*(\d+)\s*/\s*(\d+)', html, re.I)
        if m:
            try:
                return int(m.group(2))
            except Exception:
                pass
        pages = re.findall(r'href="[^"]*page/(\d+)[^"]*"', html)
        if pages:
            try:
                return max(int(p) for p in pages)
            except Exception:
                return 1
        return 1

    def _extract_video_urls(self, html):
        urls = []
        if not html:
            return urls
        seen = set()

        # 新版 data-config JSON
        configs = re.findall(r'data-config\s*=\s*(["\'])(.*?)\1', html, re.I | re.S)
        for _, raw in configs:
            try:
                config = json.loads(unescape(raw))
                video = config.get("video") or {}
                url = video.get("url")
                if not url:
                    h265 = config.get("video_h265")
                    if isinstance(h265, dict):
                        url = h265.get("url")
                    elif isinstance(h265, list):
                        url = next((x.get("url") for x in h265 if isinstance(x, dict) and x.get("url")), "")
                url = str(url or "").replace("\\/", "/").replace("\\u0068", "h")
                if url.startswith("http") and url not in seen:
                    seen.add(url)
                    urls.append(url)
            except Exception:
                pass

        # 兜底：全页媒体地址
        if not urls:
            decoded = unescape(html).replace("\\/", "/").replace("\\u0068", "h")
            for url in re.findall(r'["\']url["\']\s*:\s*["\']([^"\']+\.(?:m3u8|mp4)[^"\']*)', decoded, re.I):
                if url.startswith("http") and url not in seen:
                    seen.add(url)
                    urls.append(url)

        # 旧版 Base64 dp_video_url
        if not urls:
            for _, value in re.findall(r"var\s+dp_video_url(_\d+)?\s*=\s*['\"]([^'\"]+)['\"]", html):
                try:
                    url = base64.b64decode(value).decode("utf-8")
                except Exception:
                    continue
                if url.startswith("//"):
                    url = "https:" + url
                if url.startswith("http") and url not in seen:
                    seen.add(url)
                    urls.append(url)
        return urls

    # ── 五接口 ──────────────────────────────────────────
    def homeContent(self, filter=False):
        classes = [{"type_name": name, "type_id": slug}
                   for name, slug in zip(self.class_name, self.class_url)]
        videos = []
        try:
            videos = self._extract_articles(self._get(self.host + "/"))
        except Exception:
            pass
        return {"class": classes, "filters": {}, "list": videos}

    def homeVideoContent(self):
        try:
            html = self._get(self.host + "/")
            return {"list": self._extract_articles(html)}
        except Exception as e:
            print("首页推荐失败: %s" % e)
            return {"list": []}

    def categoryContent(self, tid, pg, filter=False, extend=None):
        pg = int(pg) if pg else 1
        # 用 slug 而非 index，避免 vbox router 传 index 时不一致
        if str(tid).isdigit() and int(tid) < len(self.class_url):
            slug = self.class_url[int(tid)]
        else:
            slug = str(tid)
        result = {"list": [], "page": pg, "pagecount": 1, "limit": self.page_size, "total": 0}
        try:
            if pg == 1:
                url = "%s/category/%s/" % (self.host, slug)
            else:
                url = "%s/category/%s/%d/" % (self.host, slug, pg)
            html = self._get(url)
            result["list"] = self._extract_articles(html)
            result["pagecount"] = self._parse_pagecount(html)
            result["total"] = result["pagecount"] * self.page_size
        except Exception as e:
            print("分类失败: %s" % e)
        return result

    def detailContent(self, ids):
        result = []
        try:
            vod_id = ids if isinstance(ids, str) else (ids[0] if ids else "")
            if not vod_id:
                return result
            if not vod_id.startswith("http"):
                url = self.host + vod_id
            else:
                url = vod_id
            html = self._get(url)
            if not html:
                return result

            title_m = re.search(r"<h1[^>]*class=\"[^\"]*post-title[^\"]*\"[^>]*>(.*?)</h1>",
                                html, re.DOTALL)
            title = self._strip_html(title_m.group(1)) if title_m else ""

            pic_m = re.search(r"<meta\s+property=\"og:image\"\s+content=\"([^\"]+)\"", html)
            pic = self._image_url(pic_m.group(1)) if pic_m else ""

            date_m = re.search(r"<li[^>]*>\s*(\d{4}\s*年\s*\d{2}\s*月\s*\d{2}\s*日)", html)
            date = date_m.group(1).replace(" ", "") if date_m else ""

            cat_m = re.findall(r'<a[^>]+href="/category/[^"]+"[^>]*>([^<]+)</a>', html)
            cat = cat_m[0] if cat_m else ""

            desc_m = re.search(r'<meta\s+name="description"\s+content="([^"]+)"', html)
            desc = desc_m.group(1)[:200] if desc_m else ""

            video_urls = self._extract_video_urls(html)

            vod = {
                "vod_id": vod_id,
                "vod_name": title,
                "vod_pic": pic,
                "vod_year": date[:4] if len(date) >= 4 else "",
                "vod_area": "",
                "vod_actor": "",
                "vod_director": "",
                "vod_type": cat,
                "vod_remarks": date,
                "vod_content": desc,
            }

            if video_urls:
                lines = ["视频%d$%s" % (i + 1, v) for i, v in enumerate(video_urls)]
                vod["vod_play_from"] = "51暗网"
                vod["vod_play_url"] = "#".join(lines)
            else:
                vod["vod_play_from"] = "51暗网"
                vod["vod_play_url"] = ""
            return {"list": [vod]}
        except Exception as e:
            print("详情失败: %s" % e)
        return {"list": []}

    def searchContent(self, key, pg, filter=False):
        pg = int(pg) if pg else 1
        result = {"list": [], "page": pg, "pagecount": 1, "limit": self.page_size, "total": 0}
        if not key:
            return result
        try:
            if pg == 1:
                url = "%s/search/%s/" % (self.host, quote(str(key), safe=""))
            else:
                url = "%s/search/%s/%d/" % (self.host, quote(str(key), safe=""), pg)
            html = self._get(url)
            result["list"] = self._extract_articles(html)
            result["pagecount"] = self._parse_pagecount(html)
            result["total"] = result["pagecount"] * self.page_size
        except Exception as e:
            print("搜索失败: %s" % e)
        return result

    def _decrypt_image(self, data):
        if not data or data.startswith((b"\xff\xd8", b"\x89PNG", b"GIF8", b"RIFF")):
            return data
        keys = (
            (b"f5d965df75336270", b"97b60394abc2fbe1"),
            (b"75336270f5d965df", b"abc2fbe197b60394"),
        )
        for key, iv in keys:
            try:
                decoded = unpad(AES.new(key, AES.MODE_CBC, iv).decrypt(data), 16)
                if decoded.startswith((b"\xff\xd8", b"\x89PNG", b"GIF8", b"RIFF")):
                    return decoded
            except Exception:
                pass
            try:
                decoded = unpad(AES.new(key, AES.MODE_ECB).decrypt(data), 16)
                if decoded.startswith((b"\xff\xd8", b"\x89PNG", b"GIF8", b"RIFF")):
                    return decoded
            except Exception:
                pass
        return data

    def _image_mime(self, data, url=""):
        if data.startswith(b"\xff\xd8"):
            return "image/jpeg"
        if data.startswith(b"\x89PNG"):
            return "image/png"
        if data.startswith(b"GIF8"):
            return "image/gif"
        if data.startswith(b"RIFF"):
            return "image/webp"
        clean_url = str(url).lower().split("?", 1)[0]
        return "image/png" if clean_url.endswith(".png") else "image/jpeg"

    def localProxy(self, param):
        try:
            if not isinstance(param, dict):
                return [404, "text/plain", b""]
            if str(param.get("type") or "") != "img":
                return [404, "text/plain", b""]
            url = str(param.get("url") or "")
            if not url:
                return [404, "text/plain", b""]
            headers = dict(self.headers)
            headers["Referer"] = self.host + "/"
            response = self.session.get(url, headers=headers, timeout=self.timeout,
                                        allow_redirects=True)
            if response.status_code != 200:
                return [response.status_code, "text/plain", b""]
            content = self._decrypt_image(response.content)
            content_type = self._image_mime(content, url)
            return [200, content_type, content]
        except Exception:
            return [404, "text/plain", b""]

    def playerContent(self, flag, id, vipFlags=None):
        try:
            if ".m3u8" in id or ".mp4" in id:
                return {
                    "parse": 0,
                    "url": id,
                    "header": {
                        "User-Agent": self.headers["User-Agent"],
                        "Referer": self.host + "/",
                    },
                }
            if id.startswith("http") or id.startswith("/"):
                if not id.startswith("http"):
                    url = self.host + id
                else:
                    url = id
                html = self._get(url)
                if html:
                    video_urls = self._extract_video_urls(html)
                    if video_urls:
                        return {
                            "parse": 0,
                            "url": video_urls[0],
                            "header": {
                                "User-Agent": self.headers["User-Agent"],
                                "Referer": self.host + "/",
                            },
                        }
            return {"parse": 1, "url": id, "header": {}}
        except Exception as e:
            print("播放失败: %s" % e)
            return {"parse": 1, "url": id, "header": {}}
