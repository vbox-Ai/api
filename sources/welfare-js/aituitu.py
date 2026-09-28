# -*- coding: utf-8 -*-
"""
爱推图 (ww.aituitu.com) - 写真美图福利源
WordPress 图集站：详情页正文直接内嵌图片（data-src 懒加载，CDN tu.aituitu.com）。
匿名访客每篇约 18~22 张预览图（完整套图需 VIP，分页 _2.html 对匿名返回相同内容）。
返回 pics:// 协议，App 端按图集浏览。
"""
import sys
import re
import json
import time
import requests
from concurrent.futures import ThreadPoolExecutor
from urllib.parse import quote as _quote
from urllib.parse import unquote as _unquote
from urllib.parse import urljoin

try:
    from bs4 import BeautifulSoup
except ImportError:
    BeautifulSoup = None

try:
    from base.spider import Spider as _B
except ImportError:
    class _B:
        pass

UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")

# 主站 + 备用域名（客户端 defaultHosts 会按序回退）
DOMAINS = [
    "https://ww.aituitu.com",
    "https://www.aituitu.com",
]

# 域名探测缓存（10 分钟）
_domain_cache = {"url": None, "ts": 0}
CACHE_TTL = 600

# 分类固定表（type_id 对应站点 URL 路径）
_FIXED_CLASSES = [
    {"type_id": "0", "type_name": "最新推荐"},
    {"type_id": "meinvtaotu", "type_name": "美女套图"},
    {"type_id": "xiezhentaotu", "type_name": "写真套图"},
    {"type_id": "meinvxiezhen", "type_name": "美女写真"},
    {"type_id": "cosplay", "type_name": "Cosplay"},
    {"type_id": "ribenxiezhen", "type_name": "日本写真"},
    {"type_id": "hanguotaotu", "type_name": "韩国套图"},
    {"type_id": "oumeitaotu", "type_name": "欧美套图"},
    {"type_id": "aimeitu", "type_name": "AI美图"},
]


class Spider(_B):
    """爱推图 蜘蛛"""

    baseUrl = "https://ww.aituitu.com"

    def __init__(self, opts=None):
        if opts is None:
            opts = {}
        # 客户端注入的自定义域名优先
        if opts.get("siteUrl"):
            self.baseUrl = opts["siteUrl"].rstrip("/")
        self.session = requests.Session()
        self.session.verify = False
        self.session.headers.update({
            "User-Agent": UA,
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "zh-CN,zh;q=0.9",
            "Referer": self.baseUrl + "/",
        })

    def init(self, ext=''):
        try:
            super().init(ext)
        except Exception:
            pass
        # iOS 注入的有效域名（用户自定义优先），跳过探测
        injected = globals().get('_vbox_effective_hosts')
        if injected and isinstance(injected, list) and len(injected) > 0:
            self.baseUrl = str(injected[0]).rstrip('/')

    def getName(self):
        return '爱推图'

    def isVideoFormat(self, u):
        return False

    def manualVideoCheck(self):
        return False

    # ------------------------------------------------------------------
    # 网络
    # ------------------------------------------------------------------
    def get_header(self, referer=None):
        h = {
            "User-Agent": UA,
            "Accept": "image/webp,image/apng,image/svg+xml,image/*,*/*;q=0.8",
            "Accept-Language": "zh-CN,zh;q=0.9",
        }
        h["Referer"] = referer if referer else (self.baseUrl + "/")
        return h

    def fetch(self, url, headers=None, **kw):
        """统一请求入口（基类 fetch 在 iSH 环境不可用，脚本自实现）"""
        kw.pop('timeout', None)
        try:
            r = self.session.get(url, headers=headers or self.get_header(),
                                 timeout=15, verify=False, allow_redirects=True, **kw)
            r.encoding = 'utf-8'
            return r
        except Exception:
            return None

    def _get_best_domain(self):
        """并发探测最快可用域名，10 分钟内复用"""
        now = time.time()
        if _domain_cache['url'] and (now - _domain_cache['ts']) < CACHE_TTL:
            return _domain_cache['url']

        def _try(d):
            try:
                t0 = time.time()
                r = requests.get(d, headers=self.get_header(), timeout=6,
                                 verify=False, allow_redirects=True)
                if r.status_code == 200 and len(r.text) > 500:
                    return d, time.time() - t0
            except Exception:
                pass
            return None, 999

        try:
            with ThreadPoolExecutor(max_workers=len(DOMAINS)) as pool:
                results = list(pool.map(_try, DOMAINS))
            valid = [x for x in results if x[0]]
            if valid:
                best = min(valid, key=lambda x: x[1])
                _domain_cache['url'] = best[0]
                _domain_cache['ts'] = now
                return best[0]
        except Exception:
            pass
        return self.baseUrl.rstrip('/')

    def _req(self, path, referer=None):
        """GET 请求：自动拼接最优域名，返回 HTML 文本或 None"""
        base = self._get_best_domain()
        url = urljoin(base + '/', path.lstrip('/'))
        r = self.fetch(url, headers=self.get_header(referer or base + '/'))
        return r.text if (r is not None and r.status_code == 200) else None

    def _fix_url(self, url):
        if not url:
            return ""
        url = url.strip()
        if url.startswith("http://") or url.startswith("https://"):
            return url
        if url.startswith("//"):
            return "https:" + url
        if url.startswith("/"):
            return self.baseUrl + url
        return self.baseUrl + "/" + url

    # ------------------------------------------------------------------
    # 列表解析
    # ------------------------------------------------------------------
    def _parse_list(self, html):
        videos = []
        if not html:
            return videos
        # 优先用 BeautifulSoup，缺失时回退正则
        if BeautifulSoup is not None:
            soup = BeautifulSoup(html, "html.parser")
            for art in soup.select("article.picture, article.post, .picture-box"):
                a = art.select_one("a.sc[href]") or art.select_one("h2.grid-title a[href]") or art.select_one("a[href]")
                if not a:
                    continue
                href = a.get("href", "").strip()
                if not href or "javascript" in href.lower():
                    continue
                href = self._fix_url(href)

                img = art.select_one("img")
                cover = ""
                if img:
                    cover = img.get("data-src") or img.get("data-original") or img.get("src") or ""
                    cover = self._fix_url(cover)

                title = ""
                h2 = art.select_one("h2.grid-title a")
                if h2:
                    title = h2.get("title") or h2.get_text(strip=True)
                if not title and img:
                    title = img.get("alt", "")
                if not title:
                    title = a.get("title", "") or a.get_text(strip=True)

                date_m = re.search(r'(\d{2,4}[-/]\d{2}[-/]\d{2})', art.get_text())
                date = date_m.group(1) if date_m else ""

                if href and title:
                    videos.append({
                        "vod_id": href,
                        "vod_name": title.strip(),
                        "vod_pic": cover,
                        "vod_remarks": date,
                    })
            return self._dedup(videos)

        # 正则回退
        for m in re.finditer(r'<article[^>]*class="[^"]*picture[^"]*".*?</article>', html, re.S):
            block = m.group(0)
            hm = re.search(r'href="(https?://[^"]+|/[^"]+\.html)"', block)
            im = re.search(r'data-src="([^"]+)"', block)
            tm = re.search(r'<h2 class="grid-title"><a[^>]*title="([^"]*)"', block)
            if not hm:
                continue
            title = tm.group(1) if tm else (im.group(1) if im else "")
            videos.append({
                "vod_id": self._fix_url(hm.group(1)),
                "vod_name": title.strip(),
                "vod_pic": self._fix_url(im.group(1)) if im else "",
                "vod_remarks": "",
            })
        return self._dedup(videos)

    @staticmethod
    def _dedup(videos):
        out, seen = [], set()
        for v in videos:
            if v["vod_id"] not in seen:
                seen.add(v["vod_id"])
                out.append(v)
        return out

    @staticmethod
    def _max_page(html):
        """从分页链接提取最大页码（多模式取最大值）"""
        if not html:
            return 1
        nums = []
        nums += [int(n) for n in re.findall(r'data-ci-pagination-page="(\d+)"', html)]
        nums += [int(n) for n in re.findall(r'index_(\d+)\.html', html)]
        nums += [int(n) for n in re.findall(r'sou-[^"\']*?-(\d+)\.html', html)]
        nums += [int(n) for n in re.findall(r'/page/(\d+)', html)]
        return max(nums) if nums else 1

    # ------------------------------------------------------------------
    # 标准接口
    # ------------------------------------------------------------------
    def homeContent(self, filter=False):
        return {"class": _FIXED_CLASSES}

    def homeVideoContent(self):
        html = self._req("/")
        return {"list": self._parse_list(html)}

    def categoryContent(self, tid, pg, filter=False, extend=""):
        try:
            pg = int(pg)
        except Exception:
            pg = 1

        if str(tid) in ("0", "", None):
            path = "/" if pg <= 1 else f"/index_{pg}.html"
        else:
            path = f"/{tid}/" if pg <= 1 else f"/{tid}/index_{pg}.html"

        html = self._req(path)
        videos = self._parse_list(html)
        pagecount = self._max_page(html)
        if pagecount < pg:
            pagecount = pg + (1 if videos else 0)
        return {"list": videos, "page": pg, "pagecount": pagecount}

    def searchContent(self, key, pg=1):
        try:
            pg = int(pg)
        except Exception:
            pg = 1
        path = f"/sou-{_quote(key)}-{pg}.html"
        html = self._req(path)
        videos = self._parse_list(html)
        pagecount = self._max_page(html)
        if pagecount < pg:
            pagecount = pg + (1 if videos else 0)
        return {"list": videos, "page": pg, "pagecount": pagecount}

    def _extract_images(self, html):
        """从详情页提取正文图片（.single-content 内的 tu.aituitu.com 图）"""
        img_list = []
        if not html:
            return img_list

        srcs = []
        if BeautifulSoup is not None:
            soup = BeautifulSoup(html, "html.parser")
            content = (soup.select_one(".single-content") or
                       soup.select_one("article") or soup)
            for img in content.select("img"):
                s = (img.get("data-src") or img.get("data-original") or img.get("src") or "").strip()
                if s:
                    srcs.append(s)
        else:
            # 正则回退：不依赖 bs4
            for tag in re.findall(r'<img[^>]+>', html, re.I):
                m = (re.search(r'data-src="([^"]+)"', tag) or
                     re.search(r'data-original="([^"]+)"', tag) or
                     re.search(r'src="([^"]+)"', tag))
                if m:
                    srcs.append(m.group(1).strip())

        for s in srcs:
            if not s or s.startswith("data:image"):
                continue
            s = self._fix_url(s)
            low = s.lower()
            if any(x in low for x in ["/statics/", "logo", "icon", "avatar", "banner",
                                      "button", "favicon", "loading", "placeholder", "400-600.jpg"]):
                continue
            if not re.search(r"\.(jpg|jpeg|png|webp|gif)(\?|$)", low):
                continue
            if s not in img_list:
                img_list.append(s)
        return img_list

    def detailContent(self, ids):
        url = ids[0] if isinstance(ids, (list, tuple)) else str(ids)
        url = self._fix_url(url)
        try:
            r = self.fetch(url, headers=self.get_header(self.baseUrl + "/"))
            html = r.text if r is not None else ""
            title = "未知标题"
            cover = ""
            if BeautifulSoup is not None and html:
                soup = BeautifulSoup(html, "html.parser")
                h = soup.select_one("h1.entry-title") or soup.select_one("h1") or soup.select_one(".title")
                if h:
                    title = h.get_text(strip=True)
                cimg = soup.select_one(".single-content img") or soup.select_one("article img")
                if cimg:
                    cover = self._fix_url(cimg.get("data-src") or cimg.get("src") or "")
            else:
                tm = re.search(r'<title>([^<]*)</title>', html)
                if tm:
                    title = re.sub(r'-第\d+页.*$', '', tm.group(1)).strip()

            img_list = self._extract_images(html)
            play_from = "图片浏览"
            if img_list:
                play_url = "全集$pics://" + "&&".join(img_list)
                content = f"共 {len(img_list)} 张图片（完整套图需原站 VIP）"
            else:
                play_url = "全集$"
                content = "未提取到图片"

            return {"list": [{
                "vod_id": url,
                "vod_name": title,
                "vod_pic": cover,
                "vod_content": content,
                "vod_play_from": play_from,
                "vod_play_url": play_url,
            }]}
        except Exception as e:
            print(f"[aituitu] detailContent error: {e}", file=sys.stderr)
            return {"list": [{"vod_id": url, "vod_name": "加载失败",
                              "vod_play_from": "图片浏览", "vod_play_url": ""}]}

    def playerContent(self, flag, id, vipFlags=None):
        if str(id).startswith("pics://"):
            return {"parse": 0, "url": id}
        # 兼容：传入详情页 URL 时现场提取
        try:
            r = self.fetch(id, headers=self.get_header(self.baseUrl + "/"))
            img_list = self._extract_images(r.text if r is not None else "")
            if not img_list:
                return {"parse": 0, "url": "", "msg": "未找到图片"}
            return {"parse": 0, "url": "pics://" + "&&".join(img_list)}
        except Exception as e:
            print(f"[aituitu] playerContent error: {e}", file=sys.stderr)
            return {"parse": 0, "url": ""}

    def localProxy(self, param):
        """图片代理：带 Referer 绕过防盗链"""
        try:
            if isinstance(param, str):
                try:
                    param = json.loads(param)
                except Exception:
                    param = {}
            url = param.get('url', '') if isinstance(param, dict) else ''
            if not url:
                return [404, 'text/plain', b'']
            url = _unquote(url) if '%' in url else url
            if not url.startswith('http'):
                return [404, 'text/plain', b'']

            headers = {
                'User-Agent': UA,
                'Referer': self.baseUrl + '/',
                'Accept': 'image/webp,image/*,*/*;q=0.8',
            }
            r = self.session.get(url, headers=headers, timeout=30,
                                 verify=False, allow_redirects=True)
            if r.status_code != 200:
                return [r.status_code, 'text/plain', b'']

            content = r.content
            ct = r.headers.get('Content-Type', 'image/jpeg')
            if 'text/plain' in ct or not ct.startswith('image/'):
                if content[:3] == b'\xff\xd8\xff':
                    ct = 'image/jpeg'
                elif content[:4] == b'\x89PNG':
                    ct = 'image/png'
                elif content[:4] == b'RIFF':
                    ct = 'image/webp'
                elif content[:6] in (b'GIF89a', b'GIF87a'):
                    ct = 'image/gif'
                else:
                    ct = 'image/jpeg'
            return [200, ct, content]
        except Exception:
            return [404, 'text/plain', b'']


if __name__ == "__main__":
    import warnings
    warnings.filterwarnings('ignore')
    s = Spider()
    print("=== homeContent ===")
    print([c["type_name"] for c in s.homeContent().get("class", [])])
    print("=== categoryContent(meinvtaotu, 1) ===")
    r = s.categoryContent("meinvtaotu", 1)
    print("列表数:", len(r.get("list", [])), " 总页数:", r.get("pagecount"))
    if r.get("list"):
        it = r["list"][0]
        print("  标题:", it["vod_name"][:40])
        print("  封面:", it["vod_pic"][:80])
        print("  详情:", it["vod_id"])
        d = s.detailContent([it["vod_id"]])
        dd = d["list"][0]
        print("=== detailContent ===")
        print("  标题:", dd["vod_name"][:40])
        print("  图片:", dd["vod_content"])
        print("  play_url 前缀:", dd["vod_play_url"][:60])
