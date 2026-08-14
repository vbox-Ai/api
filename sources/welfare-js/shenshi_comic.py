# -*- coding: utf-8 -*-
"""
绅士漫画 (wnacg) Python 蜘蛛源
条漫长卷模式：manga:// 协议返回图片列表
"""
import sys, json, re, requests, urllib.parse, warnings
warnings.filterwarnings('ignore')

from bs4 import BeautifulSoup
sys.path.append('..')
from base.spider import Spider

class Spider(Spider):
    def getName(self): return "绅士漫画"

    def init(self, extend=""):
        # 当前可用域名列表（按优先级）
        self.domains = [
            "https://www.wnacg.ru",
            "https://wnacg.ru",
            "https://www.wnacg.com",
            "https://www.wn03.ru",
            "https://www.wn07.ru",
        ]
        self.baseUrl = self.domains[0]
        self.session = requests.Session()
        self.session.verify = False  # SSL 绕过
        self.ua = 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/132.0.0.0 Safari/537.36 Edg/132.0.2957.129'
        self.headers = {'User-Agent': self.ua, 'Accept-Language': 'zh-CN,zh;q=0.9', 'Connection': 'keep-alive'}
        self.check_domain()

    def check_domain(self):
        """逐个测试域名，选第一个能访问的"""
        for d in self.domains:
            try:
                r = self.session.get(d, headers=self.headers, timeout=8, allow_redirects=True)
                if r.status_code == 200 and len(r.text) > 500:
                    self.baseUrl = d.rstrip('/')
                    return
            except:
                continue
        # 所有域名都失败，尝试从 wnlink.ru 获取新域名
        self.fetch_new_domain()

    def fetch_new_domain(self):
        try:
            r = requests.get("https://wnlink.ru/", headers=self.headers, timeout=8, verify=False)
            urls = re.findall(r'href="(https?://[^"]+)"', r.text)
            for url in urls:
                if "wn" in url and "link" not in url and "wnacg" not in url:
                    self.baseUrl = url.rstrip('/')
                    try:
                        self.session.get(self.baseUrl, headers=self.headers, timeout=8)
                        return
                    except:
                        continue
        except:
            pass

    def get_header(self, url=None):
        h = self.headers.copy()
        h['Referer'] = url if url else self.baseUrl + '/'
        return h

    def homeContent(self, filter):
        classes = [
            {"type_name": x[0], "type_id": x[1]} for x in [
                ("同人/汉化", "1"), ("单行/汉化", "9"), ("短篇/汉化", "10"),
                ("韩漫/汉化", "20"), ("Cosplay", "3"), ("CG画集", "2"), ("3D漫画", "23")
            ]
        ]
        return {"class": classes}

    def homeVideoContent(self):
        return self.categoryContent("1", "1", None, {})

    def categoryContent(self, tid, pg, filter, extend):
        return self.parse_list(f"{self.baseUrl}/albums-index-page-{pg}-cate-{tid}.html", pg)

    def searchContent(self, key, quick, pg="1"):
        key = urllib.parse.quote(key)
        return self.parse_list(f"{self.baseUrl}/search/?q={key}&f=_all&s=create_time_DESC&p={pg}", pg)

    def parse_list(self, url, pg):
        try:
            r = self.session.get(url, headers=self.get_header(url), timeout=12, allow_redirects=True)
            if r.status_code != 200:
                return {"list": [], "page": int(pg) if str(pg).isdigit() else 1, "pagecount": 1, "limit": 0, "total": 0}
            
            soup = BeautifulSoup(r.text, 'html.parser')
            
            # 多选择器兼容（网站可能改版）
            box = (soup.select_one('.gallary_wrap') 
                   or soup.select_one('#classify_container')
                   or soup.select_one('.pic_box')
                   or soup.select_one('div.gallary_wrap')
                   or soup.select_one('.album_list'))
            items = box.select('li') if box else (soup.select('.gallary_item') or soup.select('ul.pic_box li'))
            
            videos = []
            for item in items:
                a = item.select_one('a')
                if not a or not a.get('href'):
                    continue
                href = a['href']
                if "page-" in href or "javascript" in href:
                    continue
                
                title = a.get('title') or a.get_text(strip=True)
                title = re.sub(r'^\s*\[[^\]]+\]|\d{4}-\d{2}-\d{2}.*', '', title).strip()
                if not title:
                    continue
                
                img = item.select_one('img')
                pic = ""
                if img:
                    pic = img.get('src') or img.get('data-src') or img.get('data-original') or ""
                    if pic.startswith("//"):
                        pic = "https:" + pic
                
                info_text = item.get_text()
                count_m = re.search(r'(\d+)\s*[张張Pp]', info_text)
                count = count_m.group(1) + "P" if count_m else ""
                
                date_m = re.search(r'(\d{4}-\d{2}-\d{2})', info_text)
                date = date_m.group(1) if date_m else ""
                
                remark = f"{date} {count}".strip()
                
                videos.append({
                    "vod_id": href if href.startswith('/') else '/' + href,
                    "vod_name": title,
                    "vod_pic": pic,
                    "vod_remarks": remark
                })
            
            return {
                "list": videos,
                "page": int(pg) if str(pg).isdigit() else 1,
                "pagecount": 999,
                "limit": len(videos),
                "total": 9999
            }
        except Exception as e:
            # 打印实际错误，方便定位
            import traceback
            print(f"[shenshi_comic] parse_list error: {e}\n{traceback.format_exc()[:200]}", file=sys.stderr)
            return {"list": []}

    def detailContent(self, ids):
        vid = ids[0]
        url = self.baseUrl + vid if vid.startswith('/') else vid
        try:
            r = self.session.get(url, headers=self.get_header(self.baseUrl), timeout=12, allow_redirects=True)
            r.encoding = 'utf-8'
            soup = BeautifulSoup(r.text, 'html.parser')
            
            h = soup.select_one('h2') or soup.select_one('h1') or soup.select_one('.title')
            title = h.get_text(strip=True) if h else "未知标题"
            
            img = soup.select_one('.pic_box img') or soup.select_one('img.uwthumb') or soup.select_one('.cover img')
            cover = ""
            if img:
                cover = img.get('src') or img.get('data-src') or ""
                if cover.startswith("//"):
                    cover = "https:" + cover
            
            play_url = vid.replace("index", "gallery")
            if not play_url.startswith("http"):
                play_url = self.baseUrl + play_url
            
            return {"list": [{
                "vod_id": vid,
                "vod_name": title,
                "vod_pic": cover,
                "vod_type": "漫画",
                "vod_play_from": "绅士漫画$$$绅士漫画(Manga)",
                "vod_play_url": f"全集${play_url}$$$全集${play_url}"
            }]}
        except Exception as e:
            print(f"[shenshi_comic] detailContent error: {e}", file=sys.stderr)
            return {"list": [{"vod_id": vid, "vod_name": "加载失败", "vod_play_from": "绅士漫画", "vod_play_url": f"全集${url}"}]}

    def playerContent(self, flag, id, vipFlags):
        try:
            r = self.session.get(id, headers=self.get_header(id), timeout=15, allow_redirects=True)
            html = r.text.replace(r'\/', '/')
            
            img_list = []
            # 广谱正则提取所有图片 URL
            for m in re.findall(r'((?:https?:|//)[^"\'\s<>\[\]{}]+?\.(?:jpg|png|webp|jpeg|gif))', html, re.I):
                url = "https:" + m if m.startswith("//") else m
                # 过滤非内容图片
                if any(x in url.lower() for x in ['logo', 'icon', 'avatar', 'banner', 'button', 'favicon', 'loading', 'placeholder']):
                    continue
                # 缩略图还原
                if "thumb" in url.lower():
                    url = url.replace("thumb_", "").replace("_thumb", "")
                if url not in img_list:
                    img_list.append(url)
            
            if not img_list:
                return {"parse": 0, "url": "", "msg": "未找到图片"}
            
            protocol = "manga" if "Manga" in flag else "pics"
            return {
                "parse": 0,
                "playUrl": "",
                "url": f"{protocol}://" + "&&".join(img_list),
                "header": json.dumps(self.get_header(id))
            }
        except Exception as e:
            print(f"[shenshi_comic] playerContent error: {e}", file=sys.stderr)
            return {"parse": 0, "url": "", "msg": f"Err:{e}"}

    def localProxy(self, param): pass
