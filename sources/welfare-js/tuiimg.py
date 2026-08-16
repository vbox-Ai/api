# -*- coding: utf-8 -*-
"""
推图网 - 美女写真福利源
移动站 m.tuiimg.com，图片 CDN i.tuiimg.net
detailContent 直接返回 pics:// 协议，跳过详情页直接浏览
"""
import sys
import re
import requests
from bs4 import BeautifulSoup


class Spider:
    """推图网 蜘蛛"""

    baseUrl = "https://m.tuiimg.com"
    imgCdn = "https://i.tuiimg.net"

    # 分类配置
    classes = [
        {"type_id": "0", "type_name": "最新推荐"},
        {"type_id": "1", "type_name": "性感美女"},
        {"type_id": "2", "type_name": "清纯美女"},
        {"type_id": "3", "type_name": "妹子图"},
        {"type_id": "4", "type_name": "美女写真"},
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
        result = self.categoryContent("0", "1")
        result["class"] = self.classes
        return result

    def categoryContent(self, tid, pg, filter=False, extend=""):
        """分类页列表"""
        if tid == "0":
            # 最新推荐走首页
            url = f"{self.baseUrl}/index_{pg}.html" if int(pg) > 1 else self.baseUrl + "/"
        else:
            url = f"{self.baseUrl}/meinv/{tid}-{pg}.html"

        try:
            r = self.session.get(url, timeout=12, allow_redirects=True)
            r.encoding = "utf-8"
            soup = BeautifulSoup(r.text, "html.parser")

            videos = []
            # 移动站列表结构
            for li in soup.select("ul.main li, .list li, .pic-list li"):
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
                # 懒加载属性
                cover = img.get("data-src") or img.get("data-original") or img.get("src") or ""
                if cover.startswith("//"):
                    cover = "https:" + cover
                elif cover.startswith("/"):
                    cover = self.imgCdn + cover

                title = title.strip()
                if title and cover:
                    videos.append({
                        "vod_id": href,
                        "vod_name": title,
                        "vod_pic": cover,
                        "vod_remarks": "",
                    })

            # 提取总页数
            pagecount = 1
            page_nav = soup.select_one(".page, .pagination, .pager")
            if page_nav:
                last_link = page_nav.select("a")
                if last_link:
                    for a in last_link:
                        href = a.get("href", "")
                        m = re.search(r"[-_](\d+)\.html", href)
                        if m:
                            pagecount = max(pagecount, int(m.group(1)))

            return {
                "class": self.classes,
                "list": videos,
                "page": int(pg),
                "pagecount": pagecount,
            }
        except Exception as e:
            print(f"[tuiimg] categoryContent error: {e}", file=sys.stderr)
            return {"class": self.classes, "list": []}

    def detailContent(self, ids):
        """详情页：直接返回 pics:// 图片列表协议"""
        url = ids[0]
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
                cover = cover_img.get("data-src") or cover_img.get("src") or ""
                if cover.startswith("//"):
                    cover = "https:" + cover
                elif cover.startswith("/"):
                    cover = self.imgCdn + cover

            # 从 JS 变量 _pd 提取图片前缀和总数
            # 格式: var _pd = 'https://i.tuiimg.net/xxx/'; var _pc = 50;
            pd_match = re.search(r"var\s+_pd\s*=\s*['\"]([^'\"]+)['\"]", html)
            pc_match = re.search(r"var\s+_pc\s*=\s*(\d+)", html)

            img_list = []
            if pd_match and pc_match:
                prefix = pd_match.group(1)
                count = int(pc_match.group(1))
                # 批量拼接 URL
                for i in range(1, count + 1):
                    # 推图网格式：前缀 + 序号 + .jpg
                    img_url = f"{prefix}{i}.jpg"
                    img_list.append(img_url)
            else:
                # 降级：直接从 HTML 提取图片
                content = soup.select_one(".content, article, .pic-box")
                if content:
                    imgs = content.select("img")
                else:
                    imgs = soup.select("img")

                for img in imgs:
                    src = img.get("data-src") or img.get("src") or ""
                    if not src:
                        continue
                    if src.startswith("//"):
                        src = "https:" + src
                    elif src.startswith("/"):
                        src = self.imgCdn + src

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

            # 直接返回 pics:// 协议
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

    def playerContent(self, flag, id, vipFlags):
        """播放：如果收到 pics:// 协议直接返回"""
        if id.startswith("pics://"):
            return {"parse": 0, "url": id}
        return {"parse": 0, "url": ""}

    def searchContent(self, key, pg):
        """搜索功能"""
        return {"list": [], "page": 1, "pagecount": 0}


if __name__ == "__main__":
    s = Spider()
    print("=== 分类测试 ===")
    r = s.categoryContent("1", "1")
    print(f"列表数量: {len(r.get('list', []))}")
    if r.get("list"):
        item = r["list"][0]
        print(f"第一条: {item['vod_name'][:30]}")
        print(f"封面: {item['vod_pic'][:60]}")
