# -*- coding: utf-8 -*-
"""
悦色TV (yuesetv) TVBox Spider — vbox 福利版修复
永久域名: yuesetv.net
备用域名自动发现: 从发布页 8.yuese1286.cc / 8.yuese1287.cc / 8.yuese1288.cc 获取

vbox 修复点：
1. playerContent 的 header 从 json.dumps 字符串改为 dict
2. localProxy 兼容 iOS 端 JSON 字符串参数格式
3. m3u8 直链走本地代理（防盗链）
"""
import sys, re, json, html as htmlmod, base64, io
from urllib.parse import quote, unquote, urljoin
from collections import OrderedDict
from concurrent.futures import ThreadPoolExecutor

try:
    from PIL import Image
except ImportError:
    Image = None


class _LRUCache:
    """简单 LRU 缓存，超出 maxsize 时自动淘汰最久未使用条目。"""

    def __init__(self, maxsize=500):
        self._maxsize = maxsize
        self._od = OrderedDict()

    def get(self, key, default=None):
        if key not in self._od:
            return default
        self._od.move_to_end(key)
        return self._od[key]

    def __setitem__(self, key, value):
        if key in self._od:
            self._od.move_to_end(key)
        self._od[key] = value
        if len(self._od) > self._maxsize:
            self._od.popitem(last=False)

    def __contains__(self, key):
        return key in self._od
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

UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36"

# ==========================================
# 域名候选：主站 + 直接备用
# ==========================================
# 地址发布页（从中动态解析出真实内容域名）
_PUBLISH_PAGES = [
    "https://8.yuese1286.cc",
    "https://8.yuese1287.cc",
    "https://8.yuese1288.cc",
    "https://yuesetv.net",          # 永久域名，也是内容站
]

# 已知内容域名（按优先级排列，供直接测试兜底）
_DIRECT_CANDIDATES = [
    "https://yuesetv.net",
    "https://8.yuese1437.cc:88",
    "https://8.yuese1438.cc:88",
    "https://8.yuese1439.cc:88",
    "https://xxtv02.vip",
]

# ==========================================
# 分类总表
# ==========================================
_CATS = [
    ("国产传媒",  "6"),
    ("偷拍自拍",  "7"),
    ("绿帽偷情",  "35"),
    ("JK萝莉",   "36"),
    ("强奸迷奸",  "37"),
    ("日韩无码",  "10"),
    ("中文字幕",  "11"),
    ("日韩杂类",  "12"),
    ("欧美无码",  "19"),
    ("黑白专区",  "20"),
    ("少女动漫",  "23"),
    ("网爆黑料",  "30"),
]


def _decode_page(raw_html):
    """
    解码悦色TV页面：全站用 document.write(decodeURIComponent("...")) 包裹内容
    """
    if not raw_html:
        return ""
    m = re.search(r'document\.write\(decodeURIComponent\("([^"]+)"\)\)', raw_html)
    if m:
        return unquote(m.group(1))
    # 兼容单引号版本
    m2 = re.search(r"document\.write\(decodeURIComponent\('([^']+)'\)\)", raw_html)
    if m2:
        return unquote(m2.group(1))
    # 不需要解码直接返回（兼容部分子页面）
    return raw_html


def _discover_domain(session, timeout=6):
    """
    域名自动发现（并发版）：
    1. 先从地址发布页解析出所有内容站候选（并发请求发布页）
    2. 并发测试所有候选域名可用性，返回第一个成功的
    """
    candidates = []

    # ---- 步骤1: 并发请求发布页，收集候选域名 ----
    def _fetch_publish(pub_url):
        try:
            r = session.get(pub_url, timeout=timeout, allow_redirects=True)
            decoded = _decode_page(r.text)
            found = re.findall(
                r'https?://(?:\d+\.yuese\d+\.cc(?::\d+)?|yuesetv\.net|xxtv\d*\.vip)',
                decoded
            )
            return [u.rstrip('/') for u in found]
        except Exception as e:
            print(f"[YUESE] 发布页 {pub_url} 失败: {e}")
            return []

    with ThreadPoolExecutor(max_workers=len(_PUBLISH_PAGES)) as pub_exec:
        pub_futures = [pub_exec.submit(_fetch_publish, u) for u in _PUBLISH_PAGES]
        for f in pub_futures:
            for u in f.result():
                if u not in candidates:
                    candidates.append(u)

    # 补充直接候选（防止发布页全挂）
    for u in _DIRECT_CANDIDATES:
        if u not in candidates:
            candidates.append(u)

    # 去除发布页本身（1286/1287/1288 不是内容站）
    publish_hosts = {"8.yuese1286.cc", "8.yuese1287.cc", "8.yuese1288.cc"}
    candidates = [u for u in candidates
                  if not any(h in u for h in publish_hosts)]

    print(f"[YUESE] 候选域名: {len(candidates)}个")

    # ---- 步骤2: 并发测试候选域名，谁先成功用谁 ----
    def _test_domain(domain):
        try:
            r = session.get(domain + "/", timeout=timeout, allow_redirects=True)
            decoded = _decode_page(r.text)
            if re.search(r'/type/\d+', decoded):
                return domain.rstrip('/')
        except Exception:
            pass
        return None

    with ThreadPoolExecutor(max_workers=min(len(candidates), 6)) as executor:
        future_to_domain = {executor.submit(_test_domain, d): d for d in candidates}
        for future in as_completed(future_to_domain):
            result = future.result()
            if result:
                print(f"[YUESE] 使用域名: {result}")
                return result

    # 全挂兜底
    fallback = _DIRECT_CANDIDATES[0]
    print(f"[YUESE] 全部测试失败，使用兜底: {fallback}")
    return fallback


class Spider(_B):

    def init(self, ext=""):
        self.s = requests.Session()
        self.s.headers.update({
            "User-Agent": UA,
            "Accept": "text/html,application/xhtml+xml,*/*;q=0.9",
            "Accept-Language": "zh-CN,zh;q=0.9",
        })
        self._cache = _LRUCache(maxsize=500)  # vod_id -> {name, pic}，LRU 上限 500 条
        self._img_cache = _LRUCache(maxsize=200)  # 原始图片URL -> data URI 缓存
        self._executor = ThreadPoolExecutor(max_workers=4)  # 并行下载封面

        if ext and ext.startswith("http"):
            self.H = ext.rstrip("/")
            print(f"[YUESE] 使用外部传入域名: {self.H}")
        else:
            self.H = _discover_domain(self.s)

        self.s.headers.update({"Referer": self.H + "/"})

    def getName(self):
        return "悦色TV"

    def isVideoFormat(self, url):
        return ".m3u8" in url or ".mp4" in url

    def manualVideoCheck(self):
        return False

    # --------------------------------------------------------
    # 内部工具
    # --------------------------------------------------------

    def _get(self, url, timeout=20):
        """GET 并返回解码后的 HTML"""
        if not url.startswith("http"):
            url = self.H + url
        try:
            r = self.s.get(url, timeout=timeout, allow_redirects=True)
            r.encoding = "utf-8"
            return _decode_page(r.text)
        except Exception as e:
            print(f"[YUESE] GET 失败 {url}: {e}")
            return ""

    def _parse_cards(self, decoded_html):
        """
        解析视频卡片列表。
        """
        items = []
        # 匹配每个 vod-item 块
        for m in re.finditer(
            r'<div[^>]*class="[^"]*vod-item[^"]*"[^>]*to="(/play/[a-f0-9]+)"[^>]*>',
            decoded_html
        ):
            vod_id = m.group(1)          # e.g. /play/ce279d536beb3685
            start = m.end()
            # 找到对应的 </div>（找下一个 vod-item 或一个足够的范围）
            end = decoded_html.find('<div class="vod-item', start)
            block = decoded_html[start: end if end > 0 else start + 2000]

            # 封面图：依次尝试 data-original / data-src（懒加载属性），最后回退到 src
            img_m = (re.search(r'data-original="([^"]+)"', block) or
                     re.search(r'data-src="([^"]+)"', block) or
                     re.search(r'<img[^>]+src="([^"]+)"', block))
            pic = img_m.group(1) if img_m else ""
            # 过滤 data:image/... 占位符（懒加载前的透明像素）
            if pic.startswith("data:"):
                pic = ""
            # 协议相对地址（//cdn.example.com/...）补全 https:
            if pic.startswith("//"):
                pic = "https:" + pic
            # 相对路径补全为绝对地址
            elif pic and not pic.startswith("http"):
                pic = urljoin(self.H + "/", pic)

            # 标题
            title_m = re.search(r'class="rank-title"[^>]*>(.*?)</div>', block, re.S)
            if title_m:
                title = htmlmod.unescape(title_m.group(1)).strip()
                # 去掉可能残留的子标签
                title = re.sub(r'<[^>]+>', '', title).strip()
            else:
                title = vod_id

            # 时长（秒→HH:MM:SS 在服务端算）
            dur_m = re.search(r'secondsToHMS\((\d+)\)', block)
            remarks = ""
            if dur_m:
                secs = int(dur_m.group(1))
                h, rem = divmod(secs, 3600)
                mi, s = divmod(rem, 60)
                remarks = f"{h:02d}:{mi:02d}:{s:02d}" if h else f"{mi:02d}:{s:02d}"

            # 播放量
            hits_m = re.search(r'class="pre-hits"[^>]*>.*?<span[^>]*>([^<]+)</span>', block, re.S)
            if hits_m:
                hits = htmlmod.unescape(hits_m.group(1)).strip()
                if hits:
                    remarks = f"{hits} · {remarks}" if remarks else hits

            item = {
                "vod_id":      vod_id,
                "vod_name":    title,
                "vod_pic":     pic,
                "vod_remarks": remarks,
            }

            items.append(item)

        # 批量并行转换封面为 data URI
        if items:
            pic_urls = [it["vod_pic"] for it in items if it["vod_pic"]]
            converted = self._batch_pics_to_data_uri(pic_urls)
            for it in items:
                raw_pic = it["vod_pic"]
                it["vod_pic"] = converted.get(raw_pic, raw_pic)
                # 缓存供 detailContent 使用
                self._cache[it["vod_id"]] = {"name": it["vod_name"], "pic": it["vod_pic"]}

        return items

    def _fetch_pic_as_data_uri(self, url, max_width=320, quality=70):
        """
        下载封面并转为 data:image/jpeg;base64,... 格式。
        """
        if not url or url.startswith("data:"):
            return url
        # 非 .dat 且是普通图片 URL，直接返回
        if ".dat" not in url and not url.endswith((".jpg", ".jpeg", ".png", ".webp", ".gif")):
            return url
        if url in self._img_cache:
            return self._img_cache[url]

        try:
            r = self.s.get(url, timeout=12)
            data = r.content

            # 悦色TV .dat 文件内容是 base64 编码的 WebP
            try:
                decoded = base64.b64decode(data, validate=True)
                if decoded[:4] == b"RIFF" and decoded[8:12] == b"WEBP":
                    data = decoded
            except Exception:
                pass

            # 用 Pillow 统一转为 JPEG 并缩放
            if Image:
                img = Image.open(io.BytesIO(data))
                if img.mode in ("RGBA", "P", "LA"):
                    img = img.convert("RGB")
                # 等比缩放
                if img.width > max_width:
                    ratio = max_width / img.width
                    new_size = (max_width, int(img.height * ratio))
                    img = img.resize(new_size, Image.LANCZOS)
                out = io.BytesIO()
                img.save(out, format="JPEG", quality=quality)
                jpeg_b64 = base64.b64encode(out.getvalue()).decode()
                result = f"data:image/jpeg;base64,{jpeg_b64}"
                self._img_cache[url] = result
                return result
            else:
                # Pillow 不可用，至少尝试 base64 解码后直接返回 WebP data URI
                if data[:4] == b"RIFF" and data[8:12] == b"WEBP":
                    result = "data:image/webp;base64," + base64.b64encode(data).decode()
                    self._img_cache[url] = result
                    return result
                return url
        except Exception as e:
            print(f"[YUESE] 封面处理失败 {url}: {e}")
            return url

    def _batch_pics_to_data_uri(self, pic_urls):
        """并行批量转换封面为 data URI"""
        if not pic_urls:
            return {}
        # 过滤掉已缓存或不需要处理的
        pending = {u for u in pic_urls if u and not u.startswith("data:") and u not in self._img_cache}
        if not pending:
            return {u: self._img_cache.get(u, u) for u in pic_urls}

        # 并行下载
        try:
            list(self._executor.map(
                lambda u: self._fetch_pic_as_data_uri(u),
                pending
            ))
        except Exception as e:
            print(f"[YUESE] 批量封面处理异常: {e}")

        return {u: self._img_cache.get(u, u) for u in pic_urls}

    def _find_pic_from_lists(self, vod_id):
        """
        缓存未命中时，回列表页按 vod_id 查找正确封面。
        """
        first_tid = _CATS[0][1]
        for tid in [first_tid] + [c[1] for c in _CATS[1:]]:
            try:
                html = self._get(f"/type/{tid}")
                if not html:
                    continue
                items = self._parse_cards(html)
                for it in items:
                    if it.get("vod_id") == vod_id and it.get("vod_pic"):
                        return it["vod_pic"]
            except Exception as e:
                print(f"[YUESE] 列表页回查封面失败 /type/{tid}: {e}")
        return ""

    # --------------------------------------------------------
    # TVBox 接口
    # --------------------------------------------------------

    def homeContent(self, filter=False):
        """返回分类列表"""
        classes = [
            {"type_id": tid, "type_name": name}
            for name, tid in _CATS
        ]
        return {"class": classes}

    def homeVideoContent(self):
        """首页视频：取第一个分类（国产传媒）的第一页"""
        first_tid = _CATS[0][1]
        html = self._get(f"/type/{first_tid}")
        return {"list": self._parse_cards(html) if html else []}

    def categoryContent(self, tid, pg=1, filter=False, extend=None):
        """
        分类列表 + 翻页
        """
        try:
            pg = int(str(pg))
        except Exception:
            pg = 1

        path = f"/type/{tid}" if pg <= 1 else f"/type/{tid}/{pg}"
        decoded = self._get(path)
        if not decoded:
            return {"list": [], "page": pg, "pagecount": max(1, pg - 1)}

        cards = self._parse_cards(decoded)

        # 判断是否还有更多页
        has_next = len(cards) > 0
        pagecount = 999 if has_next else pg

        return {
            "list":      cards,
            "page":      pg,
            "pagecount": pagecount,
            "limit":     len(cards),
            "total":     len(cards),
        }

    def detailContent(self, ids):
        """
        视频详情页
        """
        vod_id = str(ids[0])
        if not vod_id.startswith("/"):
            vod_id = "/" + vod_id
        play_url = self.H + vod_id

        # 从缓存取封面/标题
        cached = self._cache.get(vod_id, {})
        title = cached.get("name", "")
        pic   = cached.get("pic", "")

        decoded = self._get(play_url)
        if not decoded:
            return {"list": []}

        # 提取标题
        if not title:
            tm = re.search(r'class="rank-title"[^>]*>(.*?)</div>', decoded, re.S)
            if tm:
                title = htmlmod.unescape(tm.group(1)).strip()
                title = re.sub(r'<[^>]+>', '', title).strip()
        # 兜底用 og:title
        if not title:
            og = re.search(r'property="og:title"[^>]*content="([^"]+)"', decoded)
            if og:
                title = htmlmod.unescape(og.group(1)).strip()
        if not title:
            title = vod_id

        # 封面图：优先使用列表页缓存的封面
        if not pic:
            pic = self._find_pic_from_lists(vod_id)

        # 相对路径 / 协议相对地址补全
        if pic and pic.startswith("//"):
            pic = "https:" + pic
        if pic and not pic.startswith("http") and not pic.startswith("data:"):
            pic = urljoin(self.H + "/", pic)

        # 将 .dat base64 WebP 封面转为 JPEG data URI
        if pic and not pic.startswith("data:"):
            pic = self._fetch_pic_as_data_uri(pic, max_width=480, quality=75)

        # ------------------------------------------------
        # 提取 m3u8 播放地址
        # ------------------------------------------------
        play_url_found = ""

        # 先取激活行（var url = "..."，行首不是 //）
        for m in re.finditer(r'var\s+url\s*=\s*"(https?://[^"]+\.m3u8[^"]*)"', decoded):
            line_start = decoded.rfind('\n', 0, m.start()) + 1
            line_prefix = decoded[line_start:m.start()].strip()
            if not line_prefix.startswith('//'):
                play_url_found = m.group(1)
                break

        # 再尝试注释行
        if not play_url_found:
            cdn1_m = re.search(
                r'//\s*var\s+url\s*=\s*"(https?://[^"]+\.m3u8[^"]*)"',
                decoded
            )
            if cdn1_m:
                play_url_found = cdn1_m.group(1)

        # 兜底：全文搜索所有 m3u8
        if not play_url_found:
            all_m3u8 = list(dict.fromkeys(
                re.findall(r'https?://[^\s"\'<>]+\.m3u8[^\s"\'<>]*', decoded)
            ))
            if all_m3u8:
                play_url_found = all_m3u8[0]

        # 还是找不到则回退页面 URL
        if not play_url_found:
            play_url_found = play_url

        play_flags   = "线路1"
        play_url_str = f"第1集${play_url_found}"

        return {
            "list": [{
                "vod_id":        vod_id,
                "vod_name":      title,
                "vod_pic":       pic,
                "type_name":     "",
                "vod_year":      "",
                "vod_area":      "",
                "vod_remarks":   "",
                "vod_actor":     "",
                "vod_director":  "",
                "vod_content":   "",
                "vod_play_from": play_flags,
                "vod_play_url":  play_url_str,
            }]
        }

    def playerContent(self, flag, id, vipFlags=None):
        """
        vbox 修复：header 返回 dict 而非 json.dumps 字符串
        m3u8 直链走本地代理
        """
        # id 是 m3u8/mp4 直链时直接播放
        if id and id.startswith("http") and (".m3u8" in id or ".mp4" in id):
            if ".m3u8" in id:
                # m3u8 走本地代理
                proxy_url = self._build_proxy_url("m3u8", id, self.H + "/")
                return {
                    "url": proxy_url,
                    "header": {
                        "User-Agent": UA,
                        "Referer": self.H + "/",
                    },
                    "parse": 0,
                }
            else:
                return {
                    "url": id,
                    "header": {
                        "User-Agent": UA,
                        "Referer": self.H + "/",
                    },
                    "parse": 0,
                }
        # id 是路径时重新解析详情
        d = self.detailContent([id])
        if d and d.get("list"):
            url_str = d["list"][0].get("vod_play_url", "")
            # 先尝试按 flag 匹配对应线路
            for segment in url_str.split("$$$"):
                parts = segment.split("$", 1)
                if len(parts) == 2:
                    seg_flag, seg_url = parts
                    if seg_flag == flag:
                        if ".m3u8" in seg_url:
                            proxy_url = self._build_proxy_url("m3u8", seg_url, self.H + "/")
                            return {
                                "url": proxy_url,
                                "header": {"User-Agent": UA, "Referer": self.H + "/"},
                                "parse": 0,
                            }
                        return {
                            "url": seg_url,
                            "header": {"User-Agent": UA, "Referer": self.H + "/"},
                            "parse": 0,
                        }
            # flag 未匹配，返回第一条
            first = url_str.split("$$$")[0].split("$", 1)
            src = first[1] if len(first) > 1 else first[0]
            if ".m3u8" in src:
                proxy_url = self._build_proxy_url("m3u8", src, self.H + "/")
                return {
                    "url": proxy_url,
                    "header": {"User-Agent": UA, "Referer": self.H + "/"},
                    "parse": 0,
                }
            return {
                "url": src,
                "header": {"User-Agent": UA, "Referer": self.H + "/"},
                "parse": 0,
            }
        return {"url": ""}

    def searchContent(self, key, quick=False, pg=1):
        """
        搜索接口
        """
        try:
            pg = int(str(pg))
        except Exception:
            pg = 1

        encoded_key = quote(key, safe="")
        path = f"/search/{encoded_key}" if pg <= 1 else f"/search/{encoded_key}/{pg}"
        decoded = self._get(path)
        if not decoded:
            return {"list": []}
        return {"list": self._parse_cards(decoded)}

    # --------------------------------------------------------
    # 本地代理（vbox 修复版）
    # --------------------------------------------------------

    def _build_proxy_url(self, ptype, url, referer):
        """构建本地代理 URL"""
        try:
            if hasattr(self, 'getProxyUrl'):
                base = self.getProxyUrl()
                if '?' not in base:
                    base += '?do=py'
                return (base + '&type=' + ptype +
                        '&url=' + quote(url, safe='') +
                        '&referer=' + quote(referer or '', safe=''))
        except:
            pass
        return url

    def _parse_proxy_params(self, param):
        """
        vbox 修复：兼容三种参数格式
        1. dict 字典
        2. JSON 字符串（iOS 端传入）
        3. URL query string
        """
        if isinstance(param, dict):
            return param
        if isinstance(param, str):
            # 尝试 JSON
            try:
                d = json.loads(param)
                if isinstance(d, dict):
                    return d
            except:
                pass
            # 尝试 query string
            result = {}
            qs = param.split('?', 1)[1] if '?' in param else param
            for pair in qs.split('&'):
                if '=' in pair:
                    k, v = pair.split('=', 1)
                    result[k] = unquote(v)
            return result
        return {}

    def localProxy(self, param):
        """
        本地代理：图片代理 + m3u8 代理
        vbox 修复：兼容 iOS JSON 字符串参数
        """
        try:
            p = self._parse_proxy_params(param)
            url = p.get("url", "")
            kind = p.get("kind", "")
            ptype = p.get("type", "")

            if not url or not url.startswith("http"):
                return [200, "text/plain", b""]

            # m3u8 代理
            if ptype == "m3u8" or kind == "m3u8":
                return self._proxy_m3u8(url)

            # 图片代理
            r = self.s.get(url, timeout=15, allow_redirects=True)
            data = r.content

            # 尝试 base64 解码（悦色TV 封面常见情况）
            try:
                decoded = base64.b64decode(data, validate=True)
                if decoded[:4] == b"RIFF" and decoded[8:12] == b"WEBP":
                    data = decoded
            except Exception:
                pass

            # 若是 WebP，转成 JPEG 以提升播放器兼容性
            if Image and data[:4] == b"RIFF" and data[8:12] == b"WEBP":
                try:
                    img = Image.open(io.BytesIO(data))
                    if img.mode in ("RGBA", "P"):
                        img = img.convert("RGB")
                    out = io.BytesIO()
                    img.save(out, format="JPEG", quality=85)
                    return [200, "image/jpeg", out.getvalue()]
                except Exception as e:
                    print(f"[YUESE] WebP 转 JPEG 失败: {e}")

            # 已经是普通图片或转换失败，按原样返回
            content_type = r.headers.get("Content-Type", "image/webp")
            if "octet-stream" in content_type:
                content_type = "image/webp"
            return [200, content_type, data]
        except Exception as e:
            print(f"[YUESE] localProxy 异常: {e}")
            return [200, "text/plain", b""]

    def _proxy_m3u8(self, url):
        """代理 m3u8 文件（处理相对路径和 KEY）"""
        try:
            r = self.s.get(url, timeout=15)
            if r.status_code != 200:
                return [r.status_code, "text/plain", b""]
            text = r.text
            base_url = url.rsplit('/', 1)[0] + '/'
            out_lines = []
            for line in text.splitlines():
                line = line.strip()
                if not line:
                    continue
                if line.startswith('#'):
                    if line.startswith('#EXT-X-KEY:') and 'URI=' in line:
                        line = re.sub(
                            r'URI="([^"]+)"',
                            lambda m: 'URI="' + urljoin(base_url, m.group(1)) + '"',
                            line
                        )
                    out_lines.append(line)
                elif not line.startswith('http'):
                    out_lines.append(urljoin(base_url, line))
                else:
                    out_lines.append(line)
            content = '\n'.join(out_lines) + '\n'
            return [200, 'application/vnd.apple.mpegurl', content.encode('utf-8')]
        except Exception as e:
            print(f"[YUESE] proxy_m3u8 异常: {e}")
            return [500, 'text/plain', b'']
