# -*- coding: utf-8 -*-
"""
74P福利图 - 写真美图福利源
仅保留写真分类，detailContent 直接返回 pics:// 协议，跳过详情页直接浏览
"""
import sys
import re
import requests
from bs4 import BeautifulSoup


class Spider:
    """74P福利图 蜘蛛"""

    baseUrl = "https://www.74p.net"

    # 分类配置：只保留写真/美图类
    classes = [
        {"type_id": "1", "type_name": "性感美女"},
        {"type_id": "2", "type_name": "清纯美女"},
        {"type_id": "3", "type_name": "尤物私房"},
        {"type_id": "4", "type_name": "网络红人"},
        {"type_id": "5", "type_name": "美女模特"},
        {"type_id": "6", "type_name": "唯美写真"},
        {"type_id": "7", "type_name": "美腿丝袜"},
        {"type_id": "8", "type_name": "街拍美女"},
        {"type_id": "9", "type_name": "明星写真"},
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
        """首页 = 分类 + 第一页列表"""
        result = self.categoryContent("1", "1")
        result["class"] = self.classes
        return result

    def categoryContent(self, tid, pg, filter=False, extend=""):
        """分类页列表"""
        url = f"{self.baseUrl}/xinggan/{tid}-{pg}.html"
        try:
            r = self.session.get(url, timeout=12, allow_redirects=True)
            r.encoding = "utf-8"
            soup = BeautifulSoup(r.text, "html.parser")

            videos = []
            for li in soup.select("ul.meinv li, ul.list li, .pic-list li"):
                a = li.select_one("a")
                img = li.select_one("img")
                if not a or not img:
                    continue

                href = a.get("href", "")
                if href.startswith("/"):
                    href = self.baseUrl + href
                elif not href.startswith("http"):
                    continue

                title = img.get("alt") or a.get("title") or ""
                # 优先用 data-original（懒加载），其次 src
                cover = img.get("data-original") or img.get("src") or ""
                if cover.startswith("//"):
                    cover = "https:" + cover
                elif cover.startswith("/"):
                    cover = self.baseUrl + cover

                if title and cover:
                    videos.append({
                        "vod_id": href,
                        "vod_name": title.strip(),
                        "vod_pic": cover,
                        "vod_remarks": "",
                    })

            # 尝试提取总页数
            pagecount = 1
            page_info = soup.select_one(".pageinfo, .page, .pagination")
            if page_info:
                pages = re.findall(r"共(\d+)页|共(\d+)条", page_info.get_text())
                if pages:
                    pagecount = int(pages[0][0] or pages[0][1])

            return {
                "class": self.classes,
                "list": videos,
                "page": int(pg),
                "pagecount": pagecount,
            }
        except Exception as e:
            print(f"[fuli74p] categoryContent error: {e}", file=sys.stderr)
            return {"class": self.classes, "list": []}

    def detailContent(self, ids):
        """详情页：直接返回 pics:// 图片列表协议"""
        url = ids[0]
        try:
            r = self.session.get(url, timeout=15, allow_redirects=True)
            r.encoding = "utf-8"
            soup = BeautifulSoup(r.text, "html.parser")

            # 标题
            h = soup.select_one("h1") or soup.select_one("h2") or soup.select_one(".title")
            title = h.get_text(strip=True) if h else "未知标题"

            # 封面
            cover_img = soup.select_one(".content img") or soup.select_one(".article img") or soup.select_one("img.aligncenter")
            cover = ""
            if cover_img:
                cover = cover_img.get("data-original") or cover_img.get("src") or ""
                if cover.startswith("//"):
                    cover = "https:" + cover
                elif cover.startswith("/"):
                    cover = self.baseUrl + cover

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

            # 直接返回 pics:// 协议，客户端跳过详情页直接浏览
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
                r = self.session.get(current_url, timeout=12, allow_redirects=True)
                r.encoding = "utf-8"
                soup = BeautifulSoup(r.text, "html.parser")

                # 提取内容区域的图片
                content = soup.select_one(".content, .article, .post-content, #post_content")
                if content:
                    imgs = content.select("img")
                else:
                    imgs = soup.select("article img, .entry img")

                for img in imgs:
                    src = img.get("data-original") or img.get("src") or ""
                    if not src:
                        continue
                    if src.startswith("//"):
                        src = "https:" + src
                    elif src.startswith("/"):
                        src = self.baseUrl + src

                    # 过滤非内容图
                    if any(x in src.lower() for x in ["logo", "icon", "avatar", "banner", "button", "favicon", "loading", "placeholder", "ad_", "advert"]):
                        continue
                    if not re.search(r"\.(jpg|png|webp|jpeg|gif)$", src.lower()):
                        continue
                    if src not in img_list:
                        img_list.append(src)

                # 找下一页链接
                next_link = None
                for a in soup.select(".page a, .pagination a, .pager a"):
                    text = a.get_text(strip=True)
                    if text in ["下一页", "下页", "下一张", "→", ">", "Next"]:
                        next_link = a.get("href")
                        break

                if not next_link:
                    break

                if next_link.startswith("/"):
                    current_url = self.baseUrl + next_link
                elif next_link.startswith("http"):
                    current_url = next_link
                else:
                    break

            except Exception as e:
                print(f"[fuli74p] scrape page {page} error: {e}", file=sys.stderr)
                break

        return img_list

    def playerContent(self, flag, id, vipFlags):
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

    def searchContent(self, key, pg):
        """搜索功能（如网站支持）"""
        return {"list": [], "page": 1, "pagecount": 0}


if __name__ == "__main__":
    # 简单测试
    s = Spider()
    print("=== 分类测试 ===")
    r = s.categoryContent("1", "1")
    print(f"分类数量: {len(r.get('class', []))}")
    print(f"列表数量: {len(r.get('list', []))}")
    if r.get("list"):
        item = r["list"][0]
        print(f"第一条: {item['vod_name'][:30]}")
        print(f"封面: {item['vod_pic'][:60]}")
        print(f"详情URL: {item['vod_id'][:60]}")
