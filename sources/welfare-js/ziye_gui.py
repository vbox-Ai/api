# coding: utf-8
# 性运机场 - TVBox/FongMi 爬虫 (修复版)
# URL: https://xyjc8.cfd/
# CMS: 苹果CMS - 非标准模板

import re
import json
import urllib.parse
from urllib.parse import urljoin
from base.spider import Spider as BaseSpider

class Spider(BaseSpider):
    def __init__(self):
        super().__init__()
        self.host = 'https://xyjc8.cfd'
        self.site_name = '性运机场'
        
        self.classes = [
            {'type_id': '25', 'type_name': '国产视频'},
            {'type_id': '26', 'type_name': '中文字幕'},
            {'type_id': '27', 'type_name': '国产传媒'},
            {'type_id': '28', 'type_name': '日本有码'},
            {'type_id': '29', 'type_name': '日本无码'},
            {'type_id': '30', 'type_name': '欧美无码'},
            {'type_id': '31', 'type_name': '强奸乱伦'},
            {'type_id': '32', 'type_name': '制服诱惑'},
            {'type_id': '33', 'type_name': '国产主播'},
            {'type_id': '34', 'type_name': '激情动漫'},
            {'type_id': '35', 'type_name': '明星换脸'},
            {'type_id': '36', 'type_name': '抖阴视频'},
            {'type_id': '37', 'type_name': '女优明星'},
            {'type_id': '38', 'type_name': '网曝黑料'},
            {'type_id': '39', 'type_name': '伦理三级'},
            {'type_id': '40', 'type_name': 'AV解说'},
            {'type_id': '41', 'type_name': 'SM调教'},
            {'type_id': '42', 'type_name': '萝莉少女'},
            {'type_id': '43', 'type_name': '极品媚黑'},
            {'type_id': '44', 'type_name': '女同性恋'},
            {'type_id': '45', 'type_name': '网红头条'},
            {'type_id': '46', 'type_name': '人妖系列'},
            {'type_id': '47', 'type_name': '韩国主播'},
            {'type_id': '48', 'type_name': 'VR视角'},
        ]
        
        self.filters = {}
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Referer': self.host + '/',
        }
        self.play_headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Referer': self.host + '/',
        }

    def getName(self):
        return self.site_name

    def getDependence(self):
        return []

    def init(self, extend=""):
        self.extend = extend or ""

    def homeContent(self, filter):
        return {"class": self.classes, "filters": self.filters if filter else {}}

    def getHomeContent(self, filter):
        return self.homeContent(filter)

    def homeVideoContent(self):
        try:
            url = f'{self.host}/'
            res = self.fetch(url, headers=self.headers)
            if res:
                html = self._get_text(res)
                if html:
                    items = self._parse_list(html)
                    if items:
                        return {"list": items[:20]}
            return {"list": []}
        except Exception:
            return {"list": []}

    def categoryContent(self, tid, pg, filter, extend):
        try:
            page = str(pg or "1").strip()
            if not page.isdigit():
                page = "1"
            tid = str(tid)
            
            # 根据页码构造URL
            if int(page) == 1:
                url = f'{self.host}/frim/index{tid}.html'
            else:
                url = f'{self.host}/frim/index{tid}-{page}.html'
            
            res = self.fetch(url, headers=self.headers)
            if not res:
                return {"list": [], "page": int(page), "pagecount": 0, "limit": 20}
            
            html = self._get_text(res)
            if not html:
                return {"list": [], "page": int(page), "pagecount": 0, "limit": 20}
            
            items = self._parse_list(html)
            total_pages = self._parse_total_pages(html, tid)
            
            return {
                "list": items,
                "page": int(page),
                "pagecount": total_pages or 99,
                "limit": 20,
                "total": 0
            }
        except Exception:
            return {"list": [], "page": int(pg or "1"), "pagecount": 0, "limit": 20}

    def detailContent(self, ids):
        if not ids:
            return {"list": []}
        try:
            vid = str(ids[0])
            detail_url = f'{self.host}/movie/index{vid}.html'
            res = self.fetch(detail_url, headers=self.headers)
            if not res:
                return {"list": []}
            html = self._get_text(res)
            if not html:
                return {"list": []}

            # ---- 1. 提取标题 ----
            title_match = re.search(r'<title>(.*?)在线播放.*?</title>', html, re.S)
            vod_name = title_match.group(1).strip() if title_match else "视频"

            # ---- 2. 提取封面 (兼容多种写法) ----
            vod_pic = ""
            # 方案A: data-original
            pic_match = re.search(r'<a class="videopic[^"]*"[^>]*data-original="([^"]+)"', html)
            if pic_match:
                vod_pic = pic_match.group(1).strip()
            else:
                # 方案B: style="background: url(...)"
                pic_match2 = re.search(r'<a class="videopic[^"]*"[^>]*style="[^"]*url\(([^)]+)\)', html)
                if pic_match2:
                    vod_pic = pic_match2.group(1).strip()
            if vod_pic and not vod_pic.startswith('http'):
                vod_pic = urljoin(self.host, vod_pic)

            # ---- 3. 提取播放链接（支持多集） ----
            play_urls = []
            play_from = "性运机场"
            
            # 尝试从详情页直接提取 var now / player_aaaa
            play_url = self._extract_play_from_html(html)
            if play_url:
                if not play_url.startswith('http'):
                    play_url = urljoin(self.host, play_url)
                play_urls.append(f"第1集${play_url}")

            # 如果详情页没找到，访问播放页 /play/ 提取（包含多集）
            if not play_urls:
                play_page_url = f'{self.host}/play/{vid}-0-0.html'
                play_res = self.fetch(play_page_url, headers=self.headers)
                if play_res:
                    play_html = self._get_text(play_res)
                    if play_html:
                        # 尝试提取 var now
                        now_url = self._extract_play_from_html(play_html)
                        if now_url:
                            if not now_url.startswith('http'):
                                now_url = urljoin(self.host, now_url)
                            play_urls.append(f"第1集${now_url}")
                        
                        # 进一步解析播放页里的所有集数链接（类似 <a href="/play/...">第X集</a>）
                        ep_links = re.findall(r'<a\s+href="(/play/\d+(?:-\d+-\d+)?\.html)"[^>]*>([^<]+)</a>', play_html)
                        if ep_links:
                            # 如果已存在第1集，则追加剩余集数；否则全部加入
                            existing_ep = {1} if play_urls else set()
                            for href, ep_name in ep_links:
                                ep_num = re.search(r'(\d+)', ep_name)
                                ep_num = int(ep_num.group(1)) if ep_num else 0
                                if ep_num in existing_ep:
                                    continue
                                full_url = href if href.startswith('http') else urljoin(self.host, href)
                                play_urls.append(f"{ep_name.strip() or f'第{len(play_urls)+1}集'}${full_url}")
                                existing_ep.add(ep_num)

            # ---- 4. 构造返回 ----
            vod = {
                "vod_id": vid,
                "vod_name": vod_name,
                "vod_pic": vod_pic,
                "vod_remarks": "",
                "vod_content": "",
                "vod_play_from": play_from,
                "vod_play_url": "#".join(play_urls) if play_urls else ""
            }
            return {"list": [vod]}
        except Exception:
            return {"list": []}

    def _extract_play_from_html(self, html):
        """从HTML中提取 var now 或 player_aaaa 的url"""
        # 尝试 var now
        now_match = re.search(r'var\s+now\s*=\s*"([^"]+)"', html)
        if now_match:
            return now_match.group(1)
        
        # 尝试 var player_aaaa
        start = html.find('var player_aaaa=')
        if start == -1:
            start = html.find('var player_aaaa =')
        if start != -1:
            segment = html[start:start+2000]
            url_match = re.search(r'"url"\s*:\s*"([^"]+)"', segment)
            if url_match:
                return url_match.group(1).replace('\\/', '/')
        return ""

    def searchContent(self, key, quick, pg="1"):
        if not key:
            return {"list": [], "page": int(pg)}
        try:
            url = f'{self.host}/search.php'
            headers = self.headers.copy()
            headers['Content-Type'] = 'application/x-www-form-urlencoded'
            # 使用 quote 编码，默认 utf-8
            data = f'searchword={urllib.parse.quote(key)}'
            res = self.post(url, data=data, headers=headers)
            if not res:
                return {"list": [], "page": int(pg)}
            html = self._get_text(res)
            if not html or '关键字不能为空' in html:
                return {"list": [], "page": int(pg)}
            items = self._parse_list(html)
            return {"list": items, "page": int(pg)}
        except Exception:
            return {"list": [], "page": int(pg)}

    def playerContent(self, flag, id, vipFlags):
        if not id:
            return {"parse": 1, "url": ""}
        # 直链直接播放
        if id.lower().endswith(('.m3u8', '.mp4', '.m3u')):
            return {"parse": 0, "url": id, "header": self.play_headers}
        if id.startswith(('http://', 'https://')):
            return {"parse": 0, "url": id, "header": self.play_headers}
        return {"parse": 1, "url": id, "header": self.play_headers}

    def _get_text(self, res):
        """智能解码，自动检测编码"""
        if hasattr(res, 'text'):
            return res.text
        if hasattr(res, 'content'):
            try:
                # 使用 apparent_encoding 自动识别编码
                if hasattr(res, 'apparent_encoding') and res.apparent_encoding:
                    return res.content.decode(res.apparent_encoding)
                return res.content.decode('utf-8')
            except:
                return str(res.content)
        if isinstance(res, str):
            return res
        return str(res)

    def _parse_list(self, html):
        items = []
        if not html:
            return items
        
        # 提取卡片：兼容 class="videopic" 带或不带 lazy，并从 data-original 或 style 取图
        # 优先匹配详细卡片
        pattern = r'<a class="videopic[^"]*"[^>]*href="([^"]+)"[^>]*title="([^"]*)"[^>]*(?:data-original="([^"]*)"|style="[^"]*url\(([^)]+)\)")[^>]*>.*?<span class="score">([^<]*)</span>'
        matches = re.findall(pattern, html, re.DOTALL)
        
        for match in matches:
            href = match[0]
            title = match[1]
            # 图片可能是 data-original (索引2) 或 style url (索引3)
            pic = match[2] or match[3]
            score = match[4]
            
            if not href or not title:
                continue
            vid_match = re.search(r'/movie/index(\d+)\.html', href)
            vid = vid_match.group(1) if vid_match else ''
            if vid:
                items.append({
                    "vod_id": vid,
                    "vod_name": title.strip(),
                    "vod_pic": pic if pic.startswith('http') else urljoin(self.host, pic),
                    "vod_remarks": f"{score}分" if score and score.strip() else ""
                })
        
        # 如果上面没匹配到（可能是搜索结果页面），尝试第二种结构
        if not items:
            pattern2 = r'<div class="hy-video-details active clearfix">.*?<a class="videopic"[^>]*href="([^"]+)"[^>]*style="[^"]*url\(([^)]+)\)"[^>]*>.*?<h3><a[^>]*href="[^"]+"[^>]*>([^<]*)</a></h3>.*?<span class="branch">([^<]*)</span>'
            matches2 = re.findall(pattern2, html, re.DOTALL)
            for href, pic, title, score in matches2:
                if not href or not title:
                    continue
                vid_match = re.search(r'/movie/index(\d+)\.html', href)
                vid = vid_match.group(1) if vid_match else ''
                if vid:
                    items.append({
                        "vod_id": vid,
                        "vod_name": title.strip(),
                        "vod_pic": pic if pic.startswith('http') else urljoin(self.host, pic),
                        "vod_remarks": f"{score}分" if score and score.strip() else ""
                    })
        return items

    def _parse_total_pages(self, html, tid):
        """解析最大页码，支持尾页链接和普通分页链接"""
        # 尾页链接
        page_match = re.search(r'<a href="[^"]*index' + str(tid) + r'-(\d+)\.html">尾页</a>', html)
        if page_match:
            return int(page_match.group(1))
        
        # 遍历所有分页链接取最大值
        pages = re.findall(r'<a href="[^"]*index' + str(tid) + r'-(\d+)\.html">(\d+)</a>', html)
        if pages:
            max_p = max(int(p[0]) for p in pages)
            return max_p
        return 1

    def localProxy(self, param):
        return [200, "application/vnd.apple.mpegurl", param.get("data", ""), {}]

    def destroy(self):
        pass