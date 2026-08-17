# -*- coding: utf-8 -*-
"""
74P福利图 - 写真美图福利源
v2.0: 网站结构更新，URL 从 /xinggan/1-1.html 变为 /xiurenwang 等，
      分类从首页动态发现，selectors 更灵活。
"""
import sys
import re
import requests
from bs4 import BeautifulSoup

try:
    from base.spider import Spider as _B
except ImportError:
    class _B:
        pass


class Spider(_B):
    """74P福利图 蜘蛛"""

    baseUrl = "https://www.74p.net"

    # 硬编码回退分类（当无法访问首页时使用）
    _FALLBACK_CLASSES = [
        {"type_id": "xiurenwang", "type_name": "秀人网"},
        {"type_id": "yuhuajie", "type_name": "语画界"},
        {"type_id": "huayang", "type_name": "花漾"},
        {"type_id": "xingyanshe", "type_name": "星颜社"},
        {"type_id": "feilin", "type_name": "菲林"},
        {"type_id": "aimishe", "type_name": "爱蜜社"},
        {"type_id": "boluoshe", "type_name": "菠萝社"},
        {"type_id": "youmi", "type_name": "尤蜜"},
        {"type_id": "meinv", "type_name": "美女"},
    ]

    def __init__(self, opts=None):
        if opts is None:
            opts = {}
        if opts.get("siteUrl"):
            self.baseUrl = opts["siteUrl"].rstrip("/")
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": "Mozilla/5.0 (iPhone; CPU iPhone OS 16_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.0 Mobile/15E148 Safari/604.1",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
            "Accept-Language": "zh-CN,zh;q=0.9",
        })
        self._classes = None
        self._last_home = None

    def _discover_classes(self):
        """从首页动态发现分类"""
        if self._classes is not None:
            return self._classes
        try:
            r = self.session.get(self.baseUrl, timeout=15, allow_redirects=True)
            r.encoding = "utf-8"
            soup = BeautifulSoup(r.text, "html.parser")
            seen = set()
            classes = []
            for a in soup.select("a[href]"):
                href = a.get("href", "").strip()
                text = a.get_text(strip=True)
                if not href or not text:
                    continue
                # 格式: /xiurenwang 之类
                if href.startswith("/") and href != "/" and len(href) > 1 and not href.startswith("/app"):
                    # 过滤掉非分类链接
                    if any(x in href.lower() for x in ["http", "javascript", "mailto", "tel:"]):
                        continue
                    slug = href.lstrip("/")
                    if slug not in seen and len(text) < 20:
                        seen.add(slug)
                        classes.append({"type_id": slug, "type_name": text})
            if len(classes) >= 3:
                self._classes = classes
                self._last_home = r.text
                return classes
        except Exception as e:
            print(f"[fuli74p] _discover_classes error: {e}", file=sys.stderr)
        self._classes = self._FALLBACK_CLASSES
        return self._classes

    def _get_home_html(self):
        """获取首页 HTML（缓存）"""
        if self._last_home:
            return self._last_home
        try:
            r = self.session.get(self.baseUrl, timeout=15, allow_redirects=True)
            r.encoding = "utf-8"
            self._last_home = r.text
        except Exception as e:
            print(f"[fuli74p] _get_home_html error: {e}", file=sys.stderr)
        return self._last_home or ""

    def get_header(self, referer=None):
        h = {
            "User-Agent": "Mozilla/5.0 (iPhone; CPU iPhone OS 16_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.0 Mobile/15E148 Safari/604.1",
            "Accept": "image/webp,image/apng,image/svg+xml,image/*,*/*;q=0.8",
            "Accept-Language": "zh-CN,zh;q=0.9",
        }
        if referer:
            h["Referer"] = referer
        return h

    def homeContent(self, filter=False):
        """首页：返回分类列表"""
        classes = self._discover_classes()
        return {"class": classes}

    def homeVideoContent(self):
        """首页推荐内容：从首页 HTML 中提取"""
        try:
            html = self._get_home_html()
            if not html:
                return {"list": []}
            soup = BeautifulSoup(html, "html.parser")
            videos = self._parse_list(soup)
            return {"list": videos}
        except Exception as e:
            print(f"[fuli74p] homeVideoContent error: {e}", file=sys.stderr)
            return {"list": []}

    def _fix_url(self, url):
        """补全 URL"""
        if not url:
            return ""
        url = url.strip()
        if url.startswith("http"):
            return url
        if url.startswith("//"):
            return "https:" + url
        if url.startswith("/"):
            return self.baseUrl + url
        return self.baseUrl + "/" + url

    def _parse_list(self, soup):
        """从 HTML 中提取图片列表（兼容多种结构）"""
        videos = []
        seen = set()

        # 尝试多种选择器
        item_selectors = [
            "ul.meinv li", "ul.list li", ".pic-list li",
            "article", ".post", ".item", ".entry", ".loop-item",
            ".grid-item", ".list-item", "figure", ".card",
            ".content-item", ".pic-item", ".gallery-item",
            "ul li", "li",
        ]

        for sel in item_selectors:
            items = soup.select(sel)
            if not items:
                continue

            for item in items:
                # 找链接
                a = item.select_one("a[href]")
                if not a:
                    a = item if item.name == "a" else None
                if not a:
                    continue

                href = a.get("href", "")
                if not href:
                    continue

                href = self._fix_url(href)

                # 找图片
                img = item.select_one("img")
                cover = ""
                if img:
                    cover = img.get("data-original") or img.get("data-src") or img.get("src") or ""
                    cover = self._fix_url(cover)

                # 标题
                title = ""
                if img:
                    title = img.get("alt", "")
                if not title:
                    title = a.get("title", "")
                if not title:
                    title = a.get_text(strip=True)
                if not title:
                    # 尝试从 h2/h3 获取
                    h = item.select_one("h2, h3, .title, .name")
                    if h:
                        title = h.get_text(strip=True)

                if not title:
                    title = href

                if href not in seen:
                    seen.add(href)
                    videos.append({
                        "vod_id": href,
                        "vod_name": title.strip() if title else "",
                        "vod_pic": cover,
                        "vod_remarks": "",
                    })

            if videos:
                break

        return videos

    def categoryContent(self, tid, pg, filter=False, extend=""):
        """分类页列表"""
        try:
            pg = int(pg)
        except:
            pg = 1

        url = f"{self.baseUrl}/{tid}"
        if pg > 1:
            url = f"{self.baseUrl}/{tid}/page/{pg}"

        try:
            r = self.session.get(url, timeout=15, allow_redirects=True)
            r.encoding = "utf-8"
            soup = BeautifulSoup(r.text, "html.parser")

            videos = self._parse_list(soup)

            # 尝试提取总页数
            pagecount = 1
            page_info = soup.select_one(".pageinfo, .page, .pagination, .pager, .nav-links")
            if page_info:
                pages = re.findall(r"共(\d+)页|共(\d+)条|/(\d+)页", page_info.get_text())
                if pages:
                    for p in pages:
                        val = next((v for v in p if v), None)
                        if val:
                            pagecount = int(val)
                            break

            if not pagecount or pagecount < pg:
                pagecount = max(pg, pg + (1 if videos else 0))

            return {
                "list": videos,
                "page": pg,
                "pagecount": pagecount,
            }
        except Exception as e:
            print(f"[fuli74p] categoryContent error: {e}", file=sys.stderr)
            return {"list": [], "page": pg, "pagecount": 1}

    def detailContent(self, ids):
        """详情页：直接返回 pics:// 图片列表协议"""
        url = ids[0] if isinstance(ids, (list, tuple)) else str(ids)
        url = self._fix_url(url)
        try:
            r = self.session.get(url, timeout=15, allow_redirects=True)
            r.encoding = "utf-8"
            soup = BeautifulSoup(r.text, "html.parser")

            # 标题
            h = soup.select_one("h1") or soup.select_one("h2") or soup.select_one(".title")
            title = h.get_text(strip=True) if h else "未知标题"

            # 封面
            cover_img = (
                soup.select_one(".content img") or
                soup.select_one(".article img") or
                soup.select_one("article img") or
                soup.select_one(".entry img") or
                soup.select_one("img")
            )
            cover = ""
            if cover_img:
                cover = (
                    cover_img.get("data-original") or
                    cover_img.get("data-src") or
                    cover_img.get("src") or ""
                )
                cover = self._fix_url(cover)

            # 自动翻页抓取所有图片
            img_list = self._scrape_all_images(url)

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
            print(f"[fuli74p] detailContent error: {e}", file=sys.stderr)
            return {"list": [{"vod_id": url, "vod_name": "加载失败", "vod_play_from": "图片浏览", "vod_play_url": ""}]}

    def _scrape_all_images(self, start_url, max_pages=50):
        """自动翻页抓取所有图片"""
        img_list = []
        current_url = start_url
        visited = set()

        for page in range(max_pages):
            if current_url in visited:
                break
            visited.add(current_url)

            try:
                r = self.session.get(current_url, timeout=15, allow_redirects=True)
                r.encoding = "utf-8"
                soup = BeautifulSoup(r.text, "html.parser")

                # 提取内容区域的图片
                content = (
                    soup.select_one(".content") or
                    soup.select_one(".article") or
                    soup.select_one(".post-content") or
                    soup.select_one("#post_content") or
                    soup.select_one("article") or
                    soup.select_one(".entry") or
                    soup
                )

                imgs = content.select("img") if content else soup.select("img")
                for img in imgs:
                    src = (
                        img.get("data-original") or
                        img.get("data-src") or
                        img.get("src") or
                        ""
                    )
                    if not src:
                        continue
                    src = self._fix_url(src)

                    # 过滤非内容图
                    if any(x in src.lower() for x in [
                        "logo", "icon", "avatar", "banner", "button",
                        "favicon", "loading", "placeholder", "ad_", "advert",
                        "background", "bg.", "-bg", "sprite",
                    ]):
                        continue
                    # 只保留图片格式
                    if not re.search(r"\.(jpg|png|webp|jpeg|gif)(\?|$)", src.lower()):
                        # 也接受不含扩展名但来自图片CDN的URL
                        if not any(x in src.lower() for x in ["/img/", "/image/", "/pic/", "/photo/", "/upload/", ".com/images"]):
                            continue
                    if src not in img_list:
                        img_list.append(src)

                # 找下一页链接
                next_link = None
                for a in soup.select("a"):
                    text = a.get_text(strip=True)
                    if text in ["下一页", "下页", "下一张", "→", ">", "Next", "next", "»"]:
                        next_link = a.get("href")
                        break
                # 也尝试找 page-numbers 链接
                if not next_link:
                    for a in soup.select(".page a, .pagination a, .pager a, .nav-links a"):
                        text = a.get_text(strip=True)
                        if text and text.isdigit() and int(text) == page + 2:
                            next_link = a.get("href")
                            break

                if not next_link:
                    break

                current_url = self._fix_url(next_link)

            except Exception as e:
                print(f"[fuli74p] scrape page {page} error: {e}", file=sys.stderr)
                break

        return img_list

    def playerContent(self, flag, id, vipFlags=None):
        """播放：如果收到 pics:// 协议直接返回，否则兼容旧模式"""
        if id.startswith("pics://"):
            return {"parse": 0, "url": id}

        # 兼容：从详情页提取图片
        try:
            img_list = self._scrape_all_images(id)
            if not img_list:
                return {"parse": 0, "url": "", "msg": "未找到图片"}
            return {
                "parse": 0,
                "url": "pics://" + "&&".join(img_list),
            }
        except Exception as e:
            print(f"[fuli74p] playerContent error: {e}", file=sys.stderr)
            return {"parse": 0, "url": ""}

    def localProxy(self, param):
        """图片代理：从 74p.net 获取图片，带 Referer 防盗链"""
        try:
            import json as _json
            if isinstance(param, str):
                try:
                    param = _json.loads(param)
                except Exception:
                    param = {}
            url = param.get('url', '') if isinstance(param, dict) else ''
            if not url:
                return [404, 'text/plain', b'']

            from urllib.parse import unquote as _unquote
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
            if 'text/plain' in ct:
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

    def searchContent(self, key, pg):
        """搜索功能（如网站支持）"""
        return {"list": [], "page": 1, "pagecount": 0}


if __name__ == "__main__":
    s = Spider()
    print("=== 分类测试 ===")
    r = s.categoryContent("xiurenwang", "1")
    print(f"分类数量: {len(r.get('class', []))}")
    print(f"列表数量: {len(r.get('list', []))}")
    if r.get("list"):
        item = r["list"][0]
        print(f"第一条: {item['vod_name'][:30]}")
        print(f"封面: {item['vod_pic'][:60]}")
        print(f"详情URL: {item['vod_id'][:60]}")