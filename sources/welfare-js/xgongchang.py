# coding=utf-8
#!/usr/bin/python
import sys
sys.path.append('..')
from base.spider import Spider
import json
import time
import urllib.parse
import re
import requests
from lxml import etree


class Spider(Spider):
    # ============================================================
    #  基础配置
    # ============================================================
    def getName(self):
        return "X工厂(自适应)"

    def init(self, extend=""):
        self.baseUrl = "https://hkcfrsm6.xgongchang.buzz"
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Referer": self.baseUrl
        }
        # 缓存分类列表
        self._cached_classes = None
        # 支持的图片属性（按优先级）
        self._img_attrs = ['data-src', 'data-original', 'data-lazy-src', 'src']

    # ============================================================
    #  工具方法
    # ============================================================
    def _get_image_url(self, element, base_url=None):
        """自适应提取图片URL"""
        if base_url is None:
            base_url = self.baseUrl
        for attr in self._img_attrs:
            src = element.get(attr)
            if src and src.strip() and 'loading' not in src.lower() and 'placeholder' not in src.lower():
                url = src.strip()
                if url.startswith('//'):
                    url = 'https:' + url
                elif url.startswith('/'):
                    url = base_url + url
                return url
        return ""

    def _extract_vod_id(self, href):
        """从链接中提取视频ID"""
        if not href:
            return ""
        # 匹配 /vodplay/1755337-1-1/ 格式
        m = re.search(r'/vodplay/(\d+)', href)
        if m:
            return m.group(1)
        # 匹配 /vod/detail/id/12345.html 格式
        m = re.search(r'/id/(\d+)', href)
        if m:
            return m.group(1)
        # 兜底
        m = re.search(r'(\d+)\.html', href)
        if m:
            return m.group(1)
        return ""

    def _parse_video_items(self, html):
        """自适应解析视频列表"""
        videos = []
        tree = etree.HTML(html)
        if tree is None:
            return videos

        # 策略1：a-video-grid 下的 a 标签
        items = tree.xpath('//div[contains(@class,"a-video-grid")]//a[.//img and .//h3]')
        if not items:
            # 策略2：a-update-list 下的项
            items = tree.xpath('//div[contains(@class,"a-update-list")]//a[.//img]')
        if not items:
            # 策略3：包含图片和标题的链接
            items = tree.xpath('//a[.//img and (.//h3 or .//h4 or .//h5)]')
        if not items:
            # 策略4：任何带图片的链接（从href判断）
            items = tree.xpath('//a[.//img and contains(@href,"/vodplay/")]')

        for item in items:
            try:
                href = item.get('href', '')
                if not href or href == '/' or href.startswith('#'):
                    continue

                vid = self._extract_vod_id(href)
                if not vid:
                    continue

                # 提取标题
                title = ""
                for tag in ['h3', 'h4', 'h5', 'h2', '.title', '.name']:
                    t = item.xpath(f'.//{tag}/text()')
                    if t:
                        title = t[0].strip()
                        break
                if not title:
                    alt = item.xpath('.//img/@alt')
                    if alt:
                        title = alt[0].strip()
                if not title:
                    title = item.get('title', '').strip()

                # 提取封面图
                pic = ""
                img = item.xpath('.//img')
                if img:
                    pic = self._get_image_url(img[0])

                # 提取备注（日期、播放量等）
                remark = ""
                # 找播放图标旁边的文本
                r = item.xpath('.//span/text() | .//em/text() | .//div[contains(@class,"meta")]//text()')
                if r:
                    texts = [x.strip() for x in r if x.strip()]
                    remark = ' '.join(texts)[:60]

                videos.append({
                    "vod_id": vid,
                    "vod_name": title,
                    "vod_pic": pic,
                    "vod_remarks": remark
                })
            except Exception:
                continue

        # 去重
        seen = set()
        unique_videos = []
        for v in videos:
            if v['vod_id'] not in seen:
                seen.add(v['vod_id'])
                unique_videos.append(v)

        return unique_videos

    # ============================================================
    #  分类自适应
    # ============================================================
    def _fetch_classes(self):
        """从首页导航自动提取所有视频分类"""
        if self._cached_classes is not None:
            return self._cached_classes

        classes = []
        try:
            rsp = self.fetch(self.baseUrl, headers=self.headers)
            tree = etree.HTML(rsp.text)
            if tree is None:
                return []

            # 策略1：从 a-category-nav 提取视频分类（vodtype）
            nav_links = tree.xpath('//div[contains(@class,"a-category-nav")]//a[contains(@href,"/vodtype/")]')
            if not nav_links:
                # 策略2：所有 vodtype 链接
                nav_links = tree.xpath('//a[contains(@href,"/vodtype/")]')

            seen = set()
            for a in nav_links:
                href = a.get('href', '')
                name = (a.text or '').strip()
                if not name or not href:
                    continue
                # 提取分类ID
                m = re.search(r'/vodtype/(\d+)', href)
                if not m:
                    continue
                tid = m.group(1)
                if tid in seen:
                    continue
                # 过滤掉非分类（太长的ID）
                if len(tid) > 5:
                    continue
                seen.add(tid)
                classes.append({
                    'type_name': name,
                    'type_id': tid
                })
        except Exception:
            pass

        # 兜底分类
        if not classes:
            fallback = {
                "亚洲无码": "51", "亚洲有码": "50", "中文字幕": "55",
                "国产精品": "44", "国产探花": "43", "国产盗摄": "42",
                "主播网红": "47", "黑料吃瓜": "46", "欧美极品": "21",
                "动漫电影": "22", "三级伦理": "17", "SM调教": "18"
            }
            for k, v in fallback.items():
                classes.append({'type_name': k, 'type_id': v})

        self._cached_classes = classes
        return classes

    # ============================================================
    #  首页
    # ============================================================
    def homeContent(self, filter):
        result = {}
        result['class'] = self._fetch_classes()
        return result

    def homeVideoContent(self):
        result = {}
        try:
            rsp = self.fetch(self.baseUrl, headers=self.headers)
            result['list'] = self._parse_video_items(rsp.text)
        except Exception:
            result['list'] = []
        return result

    # ============================================================
    #  分类页
    # ============================================================
    def categoryContent(self, tid, pg, filter, extend):
        result = {}
        # 自适应URL格式
        url_patterns = [
            f'{self.baseUrl}/vodtype/{tid}/page/{pg}/',
            f'{self.baseUrl}/vodtype/{tid}/{pg}.html',
            f'{self.baseUrl}/index.php/vodtype/{tid}/page/{pg}/',
        ]

        html = ""
        for url in url_patterns:
            try:
                rsp = self.fetch(url, headers=self.headers)
                if rsp.status_code == 200 and len(rsp.text) > 1000:
                    html = rsp.text
                    break
            except Exception:
                continue

        vodList = self._parse_video_items(html) if html else []

        # 自适应获取总页数
        pagecount = 9999
        total = 999999
        if html:
            tree = etree.HTML(html)
            if tree is not None:
                # 从"共XXXX条数据" 获取总数
                total_text = tree.xpath('//*[contains(text(),"共") and contains(text(),"条")]/text()')
                if total_text:
                    m = re.search(r'共\s*(\d+)\s*条', total_text[0])
                    if m:
                        total = int(m.group(1))
                        pagecount = (total + 19) // 20

                # 从"第X / Y页" 获取总页数
                page_text = tree.xpath('//*[contains(text(),"第") and contains(text(),"页")]/text()')
                if page_text:
                    m = re.search(r'第\s*\d+\s*/\s*(\d+)\s*页', page_text[0])
                    if m:
                        pagecount = int(m.group(1))
                        total = pagecount * 20

        result['list'] = vodList
        result['page'] = pg
        result['pagecount'] = pagecount
        result['limit'] = 20
        result['total'] = total
        return result

    # ============================================================
    #  详情页 - 自适应多线路
    # ============================================================
    def detailContent(self, array):
        tid = array[0]
        # 先尝试标准播放页URL获取详情（因为这个站播放页同时也是详情页）
        url = f'{self.baseUrl}/vodplay/{tid}-1-1/'
        rsp = self.fetch(url, headers=self.headers)
        html = rsp.text
        tree = etree.HTML(html)

        # ---- 提取基本信息 ----
        title = ""
        t = tree.xpath('//title/text()')
        if t:
            # 标题格式："标题 - 分类 - 网站名"
            title_text = t[0].strip()
            # 去掉后面的分类和网站名
            parts = re.split(r'\s*[-—|]\s*', title_text)
            if parts:
                title = parts[0].strip()

        # 封面图：从播放页或从og:image获取
        pic = ""
        og_img = tree.xpath('//meta[@property="og:image"]/@content')
        if og_img:
            pic = og_img[0].strip()
        # 从页面中找海报图
        if not pic:
            poster = tree.xpath('//div[contains(@class,"a-player")]//img/@src | //div[contains(@class,"player")]//img/@data-src')
            if poster:
                pic = poster[0].strip()
                if pic.startswith('/'):
                    pic = self.baseUrl + pic

        # 简介
        desc = ""
        d = tree.xpath('//meta[@name="description"]/@content')
        if d:
            desc = d[0].strip()

        # ---- 自适应提取多线路 ----
        play_from = []
        play_url = []

        # 策略1：从 a-play-lines 区域提取所有线路按钮
        line_btns = tree.xpath('//div[contains(@class,"a-play-lines")]//a[contains(@class,"line") or contains(text(),"线路")]')
        if not line_btns:
            # 策略2：所有包含"线路"的链接
            line_btns = tree.xpath('//a[contains(text(),"线路") or contains(@class,"line")]')
        if not line_btns:
            # 策略3：所有 vodplay 链接
            line_btns = tree.xpath('//a[contains(@href,"/vodplay/")]')

        if line_btns:
            episode_map = {}  # sid -> [(name, url)]
            for btn in line_btns:
                try:
                    btn_text = (btn.text or '').strip()
                    btn_href = btn.get('href', '')
                    if not btn_href:
                        continue

                    # 解析 sid 和 nid
                    sid = '1'
                    nid = '1'
                    m = re.search(r'/vodplay/\d+-(\d+)-(\d+)', btn_href)
                    if m:
                        sid = m.group(1)
                        nid = m.group(2)

                    # 线路名
                    line_name = btn_text if btn_text else f"线路{sid}"
                    if not re.match(r'^线路\s*\d+$', line_name):
                        pass  # 已经是标准格式

                    # 完整URL
                    full_url = btn_href
                    if full_url.startswith('/'):
                        full_url = self.baseUrl + full_url

                    if sid not in episode_map:
                        episode_map[sid] = {'name': line_name, 'episodes': []}

                    # 剧集名
                    ep_name = f"第{nid}集"
                    episode_map[sid]['episodes'].append(f"{ep_name}${full_url}")
                except Exception:
                    continue

            # 按sid排序
            sids = sorted(episode_map.keys(), key=lambda x: int(x) if x.isdigit() else 999)
            for sid in sids:
                info = episode_map[sid]
                play_from.append(info['name'])
                play_url.append("#".join(info['episodes']))

        # 策略4：如果只有一条线路，用当前播放页作为默认
        if not play_from:
            play_from = ["默认线路"]
            play_url = [f"第1集${url}"]

        vod = {
            "vod_id": tid,
            "vod_name": title,
            "vod_pic": pic,
            "vod_content": desc,
            "vod_play_from": "$$$".join(play_from),
            "vod_play_url": "$$$".join(play_url)
        }

        return {'list': [vod]}

    # ============================================================
    #  搜索
    # ============================================================
    def searchContent(self, key, quick):
        result = {}
        # 自适应搜索URL格式
        url_patterns = [
            f'{self.baseUrl}/vodsearch/-------------.html?wd={urllib.parse.quote(key)}',
            f'{self.baseUrl}/vodsearch/{urllib.parse.quote(key)}/',
            f'{self.baseUrl}/search.html?wd={urllib.parse.quote(key)}',
            f'{self.baseUrl}/index.php/vodsearch/wd/{urllib.parse.quote(key)}.html',
        ]

        html = ""
        for url in url_patterns:
            try:
                rsp = self.fetch(url, headers=self.headers)
                if rsp.status_code == 200 and len(rsp.text) > 500:
                    html = rsp.text
                    break
            except Exception:
                continue

        result['list'] = self._parse_video_items(html) if html else []
        return result

    # ============================================================
    #  播放解析 - 自适应多种播放源
    # ============================================================
    def playerContent(self, flag, id, vipFlags):
        result = {}
        # id 可能是完整URL或相对路径
        url = id if id.startswith('http') else (self.baseUrl + id if id.startswith('/') else id)

        # 已经是直链
        if id.endswith('.m3u8') or id.endswith('.mp4'):
            result["parse"] = 0
            result["playUrl"] = ""
            result["url"] = id
            result["header"] = json.dumps(self.headers)
            return result

        try:
            rsp = self.fetch(url, headers=self.headers)
            html = rsp.text
        except Exception:
            result["parse"] = 1
            result["playUrl"] = ""
            result["url"] = url
            result["header"] = json.dumps(self.headers)
            return result

        # ===== 方法1：从 player_aaaa 变量提取（MacCMS标准格式）=====
        pattern = r'var player_aaaa\s*=\s*({.*?});'
        match = re.search(pattern, html, re.DOTALL)
        if match:
            try:
                player_info = json.loads(match.group(1))
                video_url = player_info.get('url', '')
                if video_url:
                    video_url = video_url.replace('\\/', '/')
                    if video_url.startswith('//'):
                        video_url = 'https:' + video_url
                    result["parse"] = 0
                    result["playUrl"] = ""
                    result["url"] = video_url
                    result["header"] = json.dumps(self.headers)
                    return result
            except Exception:
                pass

        # ===== 方法2：从各种JS变量中提取 =====
        url_patterns = [
            r'"url"\s*:\s*"([^"]+)"',
            r"url\s*:\s*'([^']+)'",
            r'video_url\s*:\s*"([^"]+)"',
            r"video_url\s*:\s*'([^']+)'",
            r'video[_\-]*src\s*[=:]\s*["\']([^"\']+)["\']',
            r'src\s*:\s*"([^"]+\.m3u8[^"]*)"',
            r'src\s*:\s*\'([^\']+\.m3u8[^\']*)\'',
        ]

        for pat in url_patterns:
            matches = re.findall(pat, html)
            for m in matches:
                video_url = m.replace('\\/', '/')
                if video_url and ('.m3u8' in video_url or '.mp4' in video_url):
                    if video_url.startswith('//'):
                        video_url = 'https:' + video_url
                    elif video_url.startswith('/'):
                        video_url = self.baseUrl + video_url
                    result["parse"] = 0
                    result["playUrl"] = ""
                    result["url"] = video_url
                    result["header"] = json.dumps(self.headers)
                    return result

        # ===== 方法3：从 video 标签提取 =====
        video_match = re.search(r'<video[^>]+src="([^"]+)"', html)
        if video_match:
            video_url = video_match.group(1)
            if video_url.startswith('//'):
                video_url = 'https:' + video_url
            elif video_url.startswith('/'):
                video_url = self.baseUrl + video_url
            result["parse"] = 0
            result["playUrl"] = ""
            result["url"] = video_url
            result["header"] = json.dumps(self.headers)
            return result

        # ===== 方法4：从iframe中提取，递归解析 =====
        iframe_pattern = r'<iframe[^>]+src="([^"]+)"'
        iframe_match = re.search(iframe_pattern, html)
        if iframe_match:
            iframe_src = iframe_match.group(1)
            if iframe_src.startswith('//'):
                iframe_src = 'https:' + iframe_src
            elif iframe_src.startswith('/'):
                iframe_src = self.baseUrl + iframe_src
            return self.playerContent(flag, iframe_src, vipFlags)

        # ===== 方法5：全文提取所有m3u8链接 =====
        m3u8_matches = re.findall(r'["\']([^"\']+\.m3u8[^"\']*)["\']', html)
        for m in m3u8_matches:
            video_url = m.replace('\\/', '')
            if video_url.startswith('//'):
                video_url = 'https:' + video_url
            elif video_url.startswith('/'):
                video_url = self.baseUrl + video_url
            if 'm3u8' in video_url:
                result["parse"] = 0
                result["playUrl"] = ""
                result["url"] = video_url
                result["header"] = json.dumps(self.headers)
                return result

        # 以上都失败
        result["parse"] = 1
        result["playUrl"] = ""
        result["url"] = url
        result["header"] = json.dumps(self.headers)

        return result

    # ============================================================
    #  其他方法
    # ============================================================
    def isVideoFormat(self, url):
        pass

    def manualVideoCheck(self):
        pass

    def localProxy(self, param):
        return []
