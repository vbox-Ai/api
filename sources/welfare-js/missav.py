# -*- coding: utf-8 -*-
"""
MissAV TVBox Spider — vbox 适配版
站点: missav.ws / missav02.xyz / missav.app

vbox 适配：
1. pyquery → BeautifulSoup4
2. 多域名并发探测 → 顺序探测（避免 ThreadPoolExecutor 兼容性问题）
3. playerContent header → dict 格式
4. 继承 base.spider.Spider

注意：不使用 localProxy，图片直接返回原始 URL（与原始脚本一致）
"""
import sys, json, re, base64
from urllib.parse import urljoin, quote, unquote

sys.path.append('..')
try:
    from base.spider import Spider as _B
except ImportError:
    class _B:
        pass
try:
    import requests
except ImportError:
    requests = None
try:
    from bs4 import BeautifulSoup
except ImportError:
    BeautifulSoup = None

UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"

# 域名列表（顺序探测）
DOMAINS = [
    'https://missav.ws',
    'https://missav02.xyz',
    'https://missav.app',
]

# 缓存探测到的可用域名
_cached_domain = None

# 分类定义
CATEGORIES = [
    {"type_name": "国产", "type_id": "20"},
    {"type_name": "日本有码", "type_id": "21"},
    {"type_name": "日本无码", "type_id": "22"},
    {"type_name": "中文字幕", "type_id": "28"},
    {"type_name": "欧美", "type_id": "23"},
    {"type_name": "动漫", "type_id": "24"},
    {"type_name": "伦理", "type_id": "25"},
]

FILTERS = {
    "20": [{"key": "cateId", "name": "分类", "value": [
        {"v": "20", "n": "全部"}, {"v": "26", "n": "国产精品"}, {"v": "27", "n": "国产剧情"},
        {"v": "29", "n": "国产自拍"}, {"v": "35", "n": "国产主播"}, {"v": "85", "n": "国模私拍"},
        {"v": "91", "n": "网红明星"}, {"v": "105", "n": "国产SM"}, {"v": "107", "n": "台湾辣妹"},
        {"v": "108", "n": "香港正妹"}]}],
    "21": [{"key": "cateId", "name": "分类", "value": [
        {"v": "21", "n": "全部"}, {"v": "31", "n": "人妻"}, {"v": "44", "n": "素人"},
        {"v": "46", "n": "口爆颜射"}, {"v": "47", "n": "萝莉少女"}, {"v": "48", "n": "美乳巨乳"},
        {"v": "52", "n": "制服诱惑"}, {"v": "57", "n": "调教"}, {"v": "58", "n": "出轨"},
        {"v": "101", "n": "有码精品"}]}],
    "22": [{"key": "cateId", "name": "分类", "value": [
        {"v": "22", "n": "全部"}, {"v": "102", "n": "无码精品"}]}],
    "23": [{"key": "cateId", "name": "分类", "value": [
        {"v": "23", "n": "全部"}, {"v": "104", "n": "欧美精品"}]}],
    "24": [{"key": "cateId", "name": "分类", "value": [
        {"v": "24", "n": "全部"}, {"v": "103", "n": "动漫精品"}]}],
    "25": [{"key": "cateId", "name": "分类", "value": [
        {"v": "25", "n": "全部"}, {"v": "39", "n": "综合三级"}]}],
    "28": [{"key": "cateId", "name": "分类", "value": [
        {"v": "28", "n": "全部"}, {"v": "51", "n": "日本中字"}]}],
}


class Spider(_B):
    headers = {'User-Agent': UA}

    def getName(self):
        return "MissAV"

    def isVideoFormat(self, url):
        pass

    def manualVideoCheck(self):
        pass

    def init(self, extend=""):
        pass

    def destroy(self):
        pass

    def action(self, action):
        pass

    # ============================================================
    # 顺序域名探测：逐个尝试，第一个成功的就用
    # ============================================================
    def _fetch_best(self, path):
        """顺序探测域名并请求，返回 (html, base_domain)"""
        global _cached_domain

        # 先用缓存域名直接请求
        if _cached_domain:
            try:
                full_url = urljoin(_cached_domain, path)
                rsp = self.fetch(full_url, headers=self.headers)
                if rsp and rsp.status_code == 200 and 'Just a moment...' not in rsp.text:
                    return rsp.text, _cached_domain
            except Exception:
                pass

        # 缓存域名失败，顺序探测所有域名
        for domain in DOMAINS:
            try:
                full_url = urljoin(domain, path)
                rsp = self.fetch(full_url, headers=self.headers)
                if rsp and rsp.status_code == 200 and 'Just a moment...' not in rsp.text:
                    _cached_domain = domain
                    return rsp.text, domain
            except Exception:
                continue

        return None, DOMAINS[0]

    # ============================================================
    # 1. 首页
    # ============================================================
    def homeContent(self, filter):
        result = {'class': CATEGORIES}
        if filter:
            result['filters'] = FILTERS
        try:
            html, base_domain = self._fetch_best("/label/new/")
            if html:
                videos = self._parse_cards(html, base_domain)
                result['list'] = videos
            else:
                result['list'] = []
        except Exception as e:
            print("[MissAV] homeContent err: " + str(e))
            result['list'] = []
        return result

    def homeVideoContent(self):
        return self.homeContent(False)

    # ============================================================
    # 2. 分类列表
    # ============================================================
    def categoryContent(self, tid, pg, filter, extend):
        result = {}
        page = int(pg) if pg else 1
        target_cate_id = extend.get('cateId', tid) if extend else tid
        path = f"/vodtype/{target_cate_id}-{page}/"
        try:
            html, base_domain = self._fetch_best(path)
            if html:
                videos = self._parse_cards(html, base_domain)
                result['list'] = videos
                result['page'] = page
                result['pagecount'] = page + 1
                result['limit'] = 20
                result['total'] = 9999
            else:
                result['list'] = []
        except Exception as e:
            print("[MissAV] categoryContent err: " + str(e))
            result['list'] = []
        return result

    # ============================================================
    # 3. 详情页
    # ============================================================
    def detailContent(self, array):
        vod_id = array[0]
        try:
            path = vod_id
            for d in DOMAINS:
                if path.startswith(d):
                    path = path.replace(d, '')
                    break

            html, base_domain = self._fetch_best(path)
            if not html:
                return {'list': []}

            soup = BeautifulSoup(html, 'html.parser')

            # 标题
            title = ''
            og_title = soup.find('meta', property='og:title')
            if og_title:
                title = og_title.get('content', '')
            if not title:
                title_tag = soup.find('title')
                title = title_tag.get_text(strip=True) if title_tag else ''

            # 封面图（直接返回原始 URL，不代理）
            pic = ''
            img_tag = soup.find('img', class_='w-full')
            if img_tag:
                pic = img_tag.get('src') or img_tag.get('data-src') or ''
            if not pic:
                any_img = soup.find('img')
                if any_img:
                    pic = any_img.get('data-src') or any_img.get('src') or ''
            if pic and not pic.startswith('http'):
                pic = urljoin(base_domain, pic)

            # 分类名
            type_name = ''
            muted_a = soup.select('.text-muted a')
            if muted_a:
                type_name = ' '.join(a.get_text(strip=True) for a in muted_a)

            # 演员
            actor = ''
            if '</a>：' in html and '</p>' in html:
                try:
                    actor = html.split('</a>：')[1].split('</p>')[0]
                    actor = re.sub(r'<[^>]+>', '', actor).strip()
                except Exception:
                    actor = ''

            # 简介
            remarks = ''
            if '概要：</span>' in html and '</p>' in html:
                try:
                    remarks = html.split('概要：</span>')[1].split('</p>')[0]
                    remarks = re.sub(r'<[^>]+>', '', remarks).strip()
                except Exception:
                    remarks = ''

            play_url = urljoin(base_domain, path)
            vod_play_from = "MissAV直连"
            vod_play_url = f"正片播放${play_url}"

            vod = {
                'vod_id': vod_id,
                'vod_name': title,
                'vod_pic': pic,
                'type_name': type_name,
                'vod_actor': actor,
                'vod_content': remarks,
                'vod_play_from': vod_play_from,
                'vod_play_url': vod_play_url
            }
            return {'list': [vod]}
        except Exception as e:
            print("[MissAV] detailContent err: " + str(e))
            return {'list': []}

    # ============================================================
    # 4. 搜索
    # ============================================================
    def searchContent(self, key, quick, pg="1"):
        result = {}
        encoded_key = quote(key)
        page = int(pg) if pg else 1
        path = f"/vodsearch/{encoded_key}-------------{page-1}/"
        try:
            html, base_domain = self._fetch_best(path)
            if html:
                videos = self._parse_cards(html, base_domain)
                result['list'] = videos
            else:
                result['list'] = []
        except Exception as e:
            print("[MissAV] searchContent err: " + str(e))
            result['list'] = []
        return result

    # ============================================================
    # 5. 播放接口
    # ============================================================
    def playerContent(self, flag, id, vipFlags):
        result = {
            'parse': '1',
            'playUrl': '',
            'url': id,
            'header': dict(self.headers)
        }
        try:
            rsp = self.fetch(id, headers=self.headers)
            html = rsp.text if rsp else ""

            # 优先: player_aaaa 正则提取
            match = re.search(r'var\s+player_aaaa\s*=\s*(\{.*?\});', html)
            if match:
                player_json = json.loads(match.group(1))
                raw_url = player_json.get('url', '')
                encrypt = player_json.get('encrypt', 0)

                if encrypt == 1:
                    raw_url = unquote(raw_url)
                elif encrypt == 2:
                    raw_url = unquote(base64.b64decode(raw_url).decode('utf-8'))

                if raw_url and ('.m3u8' in raw_url or '.mp4' in raw_url or 'http' in raw_url):
                    result['parse'] = '0'
                    result['url'] = raw_url
                    return result

            # 兜底: 正则搜索 m3u8/mp4
            m3u8_match = re.search(r'https?://[^\s"\'<>]+\.m3u8[^\s"\'<>]*', html)
            if m3u8_match:
                result['parse'] = '0'
                result['url'] = m3u8_match.group(0)
                return result

            mp4_match = re.search(r'https?://[^\s"\'<>]+\.mp4[^\s"\'<>]*', html)
            if mp4_match:
                result['parse'] = '0'
                result['url'] = mp4_match.group(0)
                return result

        except Exception as e:
            print("[MissAV] playerContent err: " + str(e))

        return result

    # ============================================================
    # 辅助: 解析视频列表卡片
    # ============================================================
    def _parse_cards(self, html, base_domain):
        videos = []
        if not html or not BeautifulSoup:
            return videos
        try:
            soup = BeautifulSoup(html, 'html.parser')
            container = soup.find('body') or soup
            groups = container.select('.gap-5 .group')
            if not groups:
                groups = container.select('.group')

            for item in groups:
                a_tag = item.find('a')
                if not a_tag:
                    continue
                link = a_tag.get('href', '')
                if not link:
                    continue

                vod_id = link if link.startswith('http') else urljoin(base_domain, link)

                # 标题
                title = ''
                title_el = item.select_one('.text-nord4')
                if title_el:
                    title = title_el.get_text(strip=True)
                if not title:
                    title = a_tag.get('title', '') or a_tag.get_text(strip=True)

                # 封面图（直接返回原始 URL，不代理）
                img = item.find('img')
                pic = ''
                if img:
                    pic = img.get('data-src') or img.get('src') or ''
                if pic and not pic.startswith('http'):
                    pic = urljoin(base_domain, pic)

                # 备注
                remarks = ''
                abs_els = item.select('.absolute')
                texts = []
                for el in abs_els:
                    t = el.get_text(strip=True)
                    if t:
                        texts.append(t)
                if texts:
                    remarks = ' '.join(texts)

                videos.append({
                    'vod_id': vod_id,
                    'vod_name': title,
                    'vod_pic': pic,
                    'vod_remarks': remarks
                })
        except Exception as e:
            print("[MissAV] _parse_cards err: " + str(e))

        return videos

    def localProxy(self, param):
        pass
