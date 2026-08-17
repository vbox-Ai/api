# -*- coding: utf-8 -*-
"""
推图网 - 美女写真福利源
移动站 m.tuiimg.com，图片 CDN i.tuiimg.net
v2.0: 修复 HTML 选择器匹配实际页面结构（h2 > a > img），
      继承 base.spider.Spider 获得代理/域名注入支持，
      添加 localProxy 图片代理。
"""
import sys
import re
import json
import requests
from bs4 import BeautifulSoup
from urllib.parse import unquote as _unquote

try:
    from base.spider import Spider as _B
except ImportError:
    class _B:
        pass


class Spider(_B):
    """推图网 蜘蛛"""

    baseUrl = "https://m.tuiimg.com"
    imgCdn = "https://i.tuiimg.net"

    # 分类配置（type_id 为路径名，对应网站 URL 路径）
    _FIXED_CLASSES = [
        {"type_id": "0", "type_name": "最新推荐"},
        {"type_id": "meinv", "type_name": "美女图片"},
        {"type_id": "fengjing", "type_name": "风景图片"},
        {"type_id": "dongwu", "type_name": "动物图片"},
        {"type_id": "jianzhu", "type_name": "建筑图片"},
    ]

    def __init__(self, opts=None):
        if opts is None:
            opts = {}
        if opts.get("siteUrl"):
            self.baseUrl = opts["siteUrl"].rstrip("/")
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": "Mozilla/5.0 (iPhone; CPU iPhone OS 16_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.0 Mobile/15E148 Safari/604.1",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "zh-CN,zh;q=0.9",
        })
        self._classes = None

    def init(self, ext=''):
        try:
            super().init(ext)
        except Exception:
            pass

    def getName(self):
        return '推图网'

    def isVideoFormat(self, u):
        return False

    def manualVideoCheck(self):
        return False

    def get_header(self, referer=None):
        h = {
            "User-Agent": "Mozilla/5.0 (iPhone; CPU iPhone OS 16_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.0 Mobile/15E148 Safari/604.1",
            "Accept": "image/webp,image/apng,image/svg+xml,image/*,*/*;q=0.8",
            "Accept-Language": "zh-CN,zh;q=0.9",
        }
        if referer:
            h["Referer"] = referer
        return h

    def _fix_url(self, url):
        """补全 URL"""
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

    def _fix_img(self, url):
        """补全图片 URL"""
        if not url:
            return ""
        url = url.strip()
        if url.startswith("http://") or url.startswith("https://"):
            return url
        if url.startswith("//"):
            return "https:" + url
        if url.startswith("/"):
            return self.imgCdn + url
        return url

    def _extract_cover(self, img_tag):
        """从 img 标签提取封面 URL，优先 data-src（懒加载）"""
        if not img_tag:
            return ""
        src = img_tag.get("data-src") or img_tag.get("data-original") or img_tag.get("src") or ""
        return self._fix_img(src)

    def _parse_list(self, soup):
        """从 HTML 中提取图片列表（h2 > a > img 结构）"""
        videos = []
        seen = set()

        # 实际页面结构: <h2><a href="..."><img src="..." alt="..."></a></h2>
        for h2 in soup.select("h2"):
            a = h2.select_one("a[href]")
            if not a:
                continue
            href = a.get("href", "").strip()
            if not href:
                continue

            # 过滤非内容链接
            if any(x in href for x in ["account/", "history.php", "javascript:"]):
                continue

            img = a.select_one("img")
            if not img:
                continue

            title = img.get("alt", "") or a.get("title", "") or a.get_text(strip=True)
            cover = self._extract_cover(img)

            # 过滤 loading.gif 占位图
            if "loading.gif" in cover:
                # 尝试从 URL 模式推断封面
                # 格式: /meinv/4058/ -> i.tuiimg.net/009/4058/mc.jpg
                m = re.search(r'/(\d+)/?$', href)
                if m:
                    nid = m.group(1)
                    # 尝试从 href 推断子目录
                    cat_match = re.search(r'/(meinv|fengjing|dongwu|jianzhu)/(\d+)', href)
                    if cat_match:
                        # 无法确定子目录，跳过
                        cover = ""

            if not title or not href:
                continue

            href = self._fix_url(href)

            if href not in seen:
                seen.add(href)
                # 提取日期
                date_text = h2.get_text(strip=True)
                # 日期在标题后面，格式如 "2026-08-17 发布"
                date_match = re.search(r'(\d{4}-\d{2}-\d{2})\s*发布', date_text)
                date = date_match.group(1) if date_match else ""

                videos.append({
                    "vod_id": href,
                    "vod_name": title.strip(),
                    "vod_pic": cover,
                    "vod_remarks": date,
                })

        return videos

    def homeContent(self, filter=False):
        """首页：返回分类列表"""
        return {"class": self._FIXED_CLASSES}

    def homeVideoContent(self):
        """首页推荐内容：从首页 HTML 中提取"""
        try:
            r = self.session.get(self.baseUrl + "/", timeout=15, allow_redirects=True)
            r.encoding = "utf-8"
            soup = BeautifulSoup(r.text, "html.parser")
            videos = self._parse_list(soup)
            return {"list": videos}
        except Exception as e:
            print(f"[tuiimg] homeVideoContent error: {e}", file=sys.stderr)
            return {"list": []}

    def categoryContent(self, tid, pg=1, filter=False, extend=""):
        """分类页列表"""
        try:
            pg = int(pg)
        except:
            pg = 1

        if tid == "0":
            # "最新推荐"就是首页，分页用 index_{pg}.html
            if pg > 1:
                url = f"{self.baseUrl}/index_{pg}.html"
            else:
                url = self.baseUrl + "/"
        else:
            # 分类页：第一页 /{tid}/，第N页 /{tid}/list_{pg}.html
            if pg > 1:
                url = f"{self.baseUrl}/{tid}/list_{pg}.html"
            else:
                url = f"{self.baseUrl}/{tid}/"

        try:
            r = self.session.get(url, timeout=15, allow_redirects=True)
            r.encoding = "utf-8"
            soup = BeautifulSoup(r.text, "html.parser")

            videos = self._parse_list(soup)

            # 提取总页数
            pagecount = pg
            # 查找分页导航
            page_nav = soup.select_one(".page, .pagination, .pager, .pages")
            if page_nav:
                for a in page_nav.select("a"):
                    href = a.get("href", "")
                    m = re.search(r"(?:list|index)_(\d+)\.html", href)
                    if m:
                        pagecount = max(pagecount, int(m.group(1)))
            else:
                # 没找到分页就假设还有更多页
                pagecount = max(pg, pg + (1 if videos else 0))

            # 如果没有视频，尝试备用选择器
            if not videos:
                # 尝试 ul li 结构（旧版兼容）
                for li in soup.select("ul li, .list li"):
                    a = li.select_one("a[href]")
                    img = li.select_one("img")
                    if not a or not img:
                        continue
                    href = self._fix_url(a.get("href", ""))
                    title = img.get("alt") or a.get("title") or ""
                    cover = self._extract_cover(img)
                    if title and href and href not in {v["vod_id"] for v in videos}:
                        videos.append({
                            "vod_id": href,
                            "vod_name": title.strip(),
                            "vod_pic": cover,
                            "vod_remarks": "",
                        })

            return {
                "list": videos,
                "page": pg,
                "pagecount": pagecount,
            }
        except Exception as e:
            print(f"[tuiimg] categoryContent error: {e}", file=sys.stderr)
            return {"list": [], "page": pg, "pagecount": 1}

    def detailContent(self, ids):
        """详情页：直接返回 pics:// 图片列表协议"""
        url = ids[0] if isinstance(ids, (list, tuple)) else str(ids)
        url = self._fix_url(url)
        try:
            r = self.session.get(url, timeout=15, allow_redirects=True)
            r.encoding = "utf-8"
            html = r.text
            soup = BeautifulSoup(html, "html.parser")

            # 标题
            h = soup.select_one("h1") or soup.select_one("h2") or soup.select_one(".title")
            title = h.get_text(strip=True) if h else "未知标题"

            # 封面
            cover_img = soup.select_one(".content img") or soup.select_one("article img") or soup.select_one(".pic img")
            cover = ""
            if cover_img:
                cover = self._extract_cover(cover_img)

            # 从 JS 变量 _pd 提取图片前缀和总数
            # 格式: var _pd = 'https://i.tuiimg.net/xxx/'; var _pc = 50;
            pd_match = re.search(r"var\s+_pd\s*=\s*['\"]([^'\"]+)['\"]", html)
            pc_match = re.search(r"var\s+_pc\s*=\s*(\d+)", html)

            img_list = []
            if pd_match and pc_match:
                prefix = pd_match.group(1)
                count = int(pc_match.group(1))
                for i in range(1, count + 1):
                    img_url = f"{prefix}{i}.jpg"
                    img_list.append(img_url)
            else:
                # 降级：直接从 HTML 提取图片
                content = soup.select_one(".content, article, .pic-box")
                imgs = content.select("img") if content else soup.select("img")

                for img in imgs:
                    src = self._extract_cover(img)
                    if not src or "loading.gif" in src:
                        continue
                    if any(x in src.lower() for x in ["logo", "icon", "avatar", "banner", "button", "favicon", "loading", "placeholder"]):
                        continue
                    if not re.search(r"\.(jpg|png|webp|jpeg|gif)", src.lower()):
                        continue
                    if src not in img_list:
                        img_list.append(src)

            if not img_list:
                return {"list": [{
                    "vod_id": url,
                    "vod_name": title,
                    "vod_pic": cover,
                    "vod_play_from": "图片浏览",
                    "vod_play_url": "全集$"
                }]}

            pics_url = "pics://" + "&&".join(img_list)
            return {
                "list": [{
                    "vod_id": url,
                    "vod_name": title,
                    "vod_pic": cover,
                    "vod_content": f"共 {len(img_list)} 张图片",
                    "vod_play_from": "图片浏览",
                    "vod_play_url": f"全集${pics_url}"
                }]
            }
        except Exception as e:
            print(f"[tuiimg] detailContent error: {e}", file=sys.stderr)
            return {"list": [{"vod_id": url, "vod_name": "加载失败", "vod_play_from": "图片浏览", "vod_play_url": ""}]}

    def playerContent(self, flag, id, vipFlags=None):
        """播放：如果收到 pics:// 协议直接返回"""
        if id.startswith("pics://"):
            return {"parse": 0, "url": id}
        return {"parse": 0, "url": ""}

    def searchContent(self, key, pg=1):
        """搜索功能"""
        return {"list": [], "page": 1, "pagecount": 0}

    def localProxy(self, param):
        """图片代理：从 i.tuiimg.net 获取图片，带 Referer 防盗链"""
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
                'User-Agent': 'Mozilla/5.0 (iPhone; CPU iPhone OS 16_0 like Mac OS X) AppleWebKit/605.1.15',
                'Referer': self.baseUrl + '/',
                'Accept': 'image/webp,image/*,*/*;q=0.8',
            }
            r = self.session.get(url, headers=headers, timeout=30, allow_redirects=True)
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
    s = Spider()
    print("=== 分类测试 ===")
    r = s.categoryContent("meinv", "1")
    print(f"列表数量: {len(r.get('list', []))}")
    if r.get("list"):
        item = r["list"][0]
        print(f"第一条: {item['vod_name'][:30]}")
        print(f"封面: {item['vod_pic'][:60]}")