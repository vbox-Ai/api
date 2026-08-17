# -*- coding: utf-8 -*-
"""
每日大乱斗 TVBox Spider — vbox 适配版
站点: border.bshzjjgq.cc / blood.bshzjjgq.cc

vbox 适配：
1. pycryptodome AES → 纯 Python AES-128-CBC/ECB
2. pyquery → BeautifulSoup
3. playerContent header → dict 格式
4. 继承 base.spider.Spider
"""
import sys, re, json, hashlib, base64, io
from urllib.parse import quote, urljoin
from collections import OrderedDict

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

UA = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"

# ============================================================
# 纯 Python AES-128-CBC/ECB 实现（替代 pycryptodome）
# ============================================================
_sbox = [
    99,124,119,123,242,107,111,197,48,1,103,43,254,215,171,118,202,130,201,125,250,89,71,240,173,212,162,175,156,164,114,192,
    183,253,147,38,54,63,247,204,52,165,229,241,113,216,49,21,4,199,35,195,24,150,5,154,7,18,128,226,235,39,178,117,
    9,131,44,26,27,110,90,160,82,59,214,179,41,227,47,132,83,209,0,237,32,252,177,91,106,203,190,57,74,76,88,207,
    208,239,170,251,67,77,51,133,69,249,2,127,80,60,159,168,81,163,64,143,146,157,56,245,188,182,218,33,16,255,243,210,
    205,12,19,236,95,151,68,23,196,167,126,61,100,93,25,115,96,129,79,220,34,42,144,136,70,238,184,20,222,94,11,219,
    224,50,58,10,73,6,36,92,194,211,172,98,145,149,228,121,231,200,55,109,141,213,78,169,108,86,244,234,101,122,174,8,
    186,120,37,46,28,166,180,198,232,221,116,31,75,189,139,138,112,62,181,102,72,3,246,14,97,53,87,185,134,193,29,158,
    225,248,152,17,105,217,142,148,155,30,135,233,206,85,40,223,140,161,137,13,191,230,66,104,65,153,45,15,176,84,187,22]
_inv_sbox = [
    82,9,106,213,48,54,165,56,191,64,163,158,129,243,215,251,124,227,57,130,155,47,255,135,52,142,67,68,196,222,233,203,
    84,123,148,50,166,194,35,61,238,76,149,11,66,250,195,78,8,46,161,102,40,217,36,178,118,91,162,73,109,139,209,37,
    114,248,246,100,134,104,152,22,212,164,92,204,93,101,182,146,108,112,72,80,253,237,185,218,94,21,70,87,167,141,157,132,
    144,216,171,0,140,188,211,10,247,228,88,5,184,179,69,6,208,44,30,143,202,63,15,2,193,175,189,3,1,19,138,107,
    58,145,17,65,79,103,220,234,151,242,207,206,240,180,230,115,150,172,116,34,231,173,53,133,226,249,55,232,28,117,223,110,
    71,241,26,113,29,41,197,137,111,183,98,14,170,24,190,27,252,86,62,75,198,210,121,32,154,219,192,254,120,205,90,244,
    31,221,168,51,136,7,199,49,177,18,16,89,39,128,236,95,96,81,127,169,25,181,74,13,45,229,122,159,147,201,156,239,
    160,224,59,77,174,42,245,176,200,235,187,60,131,83,153,97,23,43,4,126,186,119,214,38,225,105,20,99,85,33,12,125]
_rcon = [0,1,2,4,8,16,32,64,128,27,54,108,212,137,51]

def _gmul(a, b):
    p = 0
    for _ in range(8):
        if b & 1: p ^= a
        hi = a & 0x80; a = ((a << 1) & 0xff) ^ (0x1b if hi else 0); b //= 2
    return p

def _subw(w): return [_sbox[x] for x in w]
def _rotw(w): return w[1:] + w[:1]

def _expand_key(k):
    Nk = len(k) // 4; Nr = Nk + 6
    w = [list(k[i:i+4]) for i in range(0, len(k), 4)]
    for i in range(Nk, 4 * (Nr + 1)):
        t = w[i - 1][:]
        if i % Nk == 0:
            t = _subw(_rotw(t)); t[0] ^= _rcon[i // Nk]
        elif Nk > 6 and i % Nk == 4:
            t = _subw(t)
        w.append([w[i - Nk][j] ^ t[j] for j in range(4)])
    return [sum(w[4*r:4*r+4], []) for r in range(Nr + 1)], Nr

def _add_round_key(s, rk):
    for c in range(4):
        for r in range(4): s[r][c] ^= rk[4 * c + r]

def _inv_shift_rows(s):
    s[1] = s[1][-1:] + s[1][:-1]; s[2] = s[2][-2:] + s[2][:-2]; s[3] = s[3][-3:] + s[3][:-3]

def _inv_sub_bytes(s):
    for r in range(4):
        for c in range(4): s[r][c] = _inv_sbox[s[r][c]]

def _inv_mix_columns(s):
    for c in range(4):
        a = [s[r][c] for r in range(4)]
        s[0][c] = _gmul(a[0], 14) ^ _gmul(a[1], 11) ^ _gmul(a[2], 13) ^ _gmul(a[3], 9)
        s[1][c] = _gmul(a[0], 9) ^ _gmul(a[1], 14) ^ _gmul(a[2], 11) ^ _gmul(a[3], 13)
        s[2][c] = _gmul(a[0], 13) ^ _gmul(a[1], 9) ^ _gmul(a[2], 14) ^ _gmul(a[3], 11)
        s[3][c] = _gmul(a[0], 11) ^ _gmul(a[1], 13) ^ _gmul(a[2], 9) ^ _gmul(a[3], 14)

def _aes_block_decrypt(block, key):
    rks, Nr = _expand_key(key)
    s = [[block[4 * c + r] for c in range(4)] for r in range(4)]
    _add_round_key(s, rks[Nr])
    for rnd in range(Nr - 1, 0, -1):
        _inv_shift_rows(s); _inv_sub_bytes(s); _add_round_key(s, rks[rnd]); _inv_mix_columns(s)
    _inv_shift_rows(s); _inv_sub_bytes(s); _add_round_key(s, rks[0])
    return bytes(s[r][c] for c in range(4) for r in range(4))

def _aes_ecb_decrypt_block(ct_block, key):
    """AES-128-ECB 单块解密"""
    return _aes_block_decrypt(ct_block, key)

def _aes_cbc_decrypt(ct, key, iv):
    """AES-128-CBC 解密 + PKCS7 unpad"""
    out = b''; prev = iv
    for i in range(0, len(ct), 16):
        block = ct[i:i+16]
        if len(block) < 16:
            break
        dec = _aes_block_decrypt(block, key)
        out += bytes(a ^ b for a, b in zip(dec, prev))
        prev = block
    # PKCS7 unpad
    if out:
        pad = out[-1]
        if 1 <= pad <= 16 and out.endswith(bytes([pad]) * pad):
            out = out[:-pad]
    return out

def _aes_ecb_decrypt(ct, key):
    """AES-128-ECB 解密 + PKCS7 unpad"""
    out = b''
    for i in range(0, len(ct), 16):
        block = ct[i:i+16]
        if len(block) < 16:
            break
        out += _aes_ecb_decrypt_block(block, key)
    if out:
        pad = out[-1]
        if 1 <= pad <= 16 and out.endswith(bytes([pad]) * pad):
            out = out[:-pad]
    return out

# ============================================================
# 图片解密（替代原 aesimg 方法）
# ============================================================
_IMG_KEYS = [
    (b'f5d965df75336270', b'97b60394abc2fbe1'),  # CBC
    (b'75336270f5d965df', b'abc2fbe197b60394'),  # CBC (交换)
]

def _aes_decrypt_image(data):
    """纯 Python 图片 AES 解密，替代 pycryptodome 版本"""
    if len(data) < 16:
        return data
    for k, v in _IMG_KEYS:
        try:
            dec = _aes_cbc_decrypt(data, k, v)
            if dec.startswith(b'\xff\xd8') or dec.startswith(b'\x89PNG'):
                return dec
        except Exception:
            pass
        try:
            dec = _aes_ecb_decrypt(data, k)
            if dec.startswith(b'\xff\xd8'):
                return dec
        except Exception:
            pass
    return data


# ============================================================
# LRU 缓存
# ============================================================
class _LRUCache:
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

    def clear(self):
        self._od.clear()


# ============================================================
# Spider 类
# ============================================================
class Spider(_B):

    def init(self, extend=""):
        try:
            self._ext = json.loads(extend) if extend else {}
        except Exception:
            self._ext = {}
        self.headers = {
            'User-Agent': UA,
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8',
            'Accept-Language': 'zh-CN,zh;q=0.9',
        }
        self.host = self._get_working_host()
        self.headers.update({'Origin': self.host, 'Referer': self.host + '/'})
        self._img_cache = _LRUCache(maxsize=200)
        print(f"[DABATTLE] 使用站点: {self.host}")

    def getName(self):
        return "每日大乱斗"

    def isVideoFormat(self, url):
        return bool(url) and any(ext in url for ext in ['.m3u8', '.mp4', '.ts'])

    def manualVideoCheck(self):
        return False

    def destroy(self):
        self._img_cache.clear()

    # --------------------------------------------------------
    # 域名探测
    # --------------------------------------------------------
    def _get_working_host(self):
        candidates = [
            'https://border.bshzjjgq.cc/',
            'https://blood.bshzjjgq.cc/'
        ]
        for url in candidates:
            try:
                r = requests.get(url, headers=self.headers, timeout=10)
                if r.status_code == 200:
                    return url.rstrip('/')
            except Exception:
                continue
        return candidates[0].rstrip('/')

    # --------------------------------------------------------
    # HTTP 工具
    # --------------------------------------------------------
    def _fetch(self, url, timeout=15):
        if not url.startswith('http'):
            url = self.host + url
        try:
            r = requests.get(url, headers=self.headers, timeout=timeout)
            return r
        except Exception as e:
            print(f"[DABATTLE] GET 失败 {url}: {e}")
            return None

    def _soup(self, html):
        """BeautifulSoup 解析（替代 pyquery）"""
        if not html:
            return BeautifulSoup('', 'html.parser')
        return BeautifulSoup(html, 'html.parser')

    # --------------------------------------------------------
    # 图片处理
    # --------------------------------------------------------
    def _e64(self, text):
        return base64.b64encode(str(text).encode()).decode()

    def _d64(self, text):
        return base64.b64decode(str(text).encode()).decode()

    def _build_proxy_url(self, ptype, url):
        """构建 localProxy 代理 URL"""
        try:
            if hasattr(self, 'getProxyUrl'):
                base = self.getProxyUrl()
                if '?' not in base:
                    base += '?do=py'
                return base + '&type=' + ptype + '&url=' + quote(self._e64(url), safe='')
        except Exception:
            pass
        return url

    def _get_img_url(self, soup_elem, html_block=''):
        """从 card 元素中提取图片 URL（替代原 getimg）"""
        if not html_block and soup_elem:
            html_block = str(soup_elem)

        # 1. loadBannerDirect('...')
        m = re.search(r"loadBannerDirect\('([^']+)'", html_block)
        if m:
            return self._process_img_url(m.group(1))

        html_block = html_block.replace('&quot;', '"').replace('&apos;', "'").replace('&amp;', '&')

        # 2. data:image...
        m = re.search(r'(data:image/[a-zA-Z0-9+/=;,]+)', html_block)
        if m:
            return self._process_img_url(m.group(1))

        # 3. http(s)图片 URL
        m = re.search(r'(https?://[^"\'\s)]+\.(?:jpg|png|jpeg|webp))', html_block, re.I)
        if m:
            return self._process_img_url(m.group(1))

        # 4. CSS url(...)
        m = re.search(r'url\s*\(\s*[\'"]?([^"\'\)]+)[\'"]?\s*\)', html_block, re.I)
        if m:
            return self._process_img_url(m.group(1))

        # 5. 从 soup 元素提取 img src
        if soup_elem:
            img = soup_elem.find('img')
            if img:
                src = img.get('data-original') or img.get('data-src') or img.get('src')
                if src:
                    return self._process_img_url(src)

        return ''

    def _process_img_url(self, url):
        if not url:
            return ''
        url = url.strip('\'" ')
        # data: URI → 尝试 AES 解密
        if url.startswith('data:'):
            try:
                _, b64_str = url.split(',', 1)
                raw = base64.b64decode(b64_str)
                if not (raw.startswith(b'\xff\xd8') or raw.startswith(b'\x89PNG') or raw.startswith(b'GIF8')):
                    raw = _aes_decrypt_image(raw)
                key = hashlib.md5(raw).hexdigest()
                self._img_cache[key] = raw
                return self._build_proxy_url('cache', key)
            except Exception:
                return ''
        # 相对路径
        if not url.startswith('http'):
            url = self.host + url if url.startswith('/') else self.host + '/' + url
        return self._build_proxy_url('img', url)

    # --------------------------------------------------------
    # 列表解析
    # --------------------------------------------------------
    def _parse_list(self, soup, tid=''):
        videos = []
        is_folder = '/mrdg' in (tid or '')
        articles = soup.select('article') or soup.select('#index article') or soup.select('#archive article')
        if not articles:
            articles = soup.select('a[href]')

        for art in articles:
            a_tag = art if art.name == 'a' else art.find('a')
            if not a_tag:
                continue
            href = a_tag.get('href', '')
            if not href:
                continue

            # 标题
            title = ''
            for t in ['h2', '.entry-title', '.post-title']:
                el = art.select_one(t) if hasattr(art, 'select_one') else (art.find(t.lstrip('.')) if t.startswith('.') else art.find(t))
                if el:
                    title = el.get_text(strip=True)
                    break
            if not title and art.name == 'a':
                title = art.get_text(strip=True)
            if not title:
                continue

            img = self._get_img_url(art)
            time_tag = art.find('time') if hasattr(art, 'find') else None
            remarks = time_tag.get_text(strip=True) if time_tag else ''

            videos.append({
                'vod_id': href + ('@folder' if is_folder else ''),
                'vod_name': title.strip(),
                'vod_pic': img,
                'vod_remarks': remarks,
                'vod_tag': 'folder' if is_folder else '',
                'style': {"type": "rect", "ratio": 1.33}
            })
        return videos

    def _parse_folder(self, href):
        """解析合集页（原 getfod）"""
        url = self.host + href
        r = self._fetch(url)
        if not r:
            return []
        soup = self._soup(r.text)
        post_content = soup.select_one('.post-content')
        if not post_content:
            return []
        h2s = post_content.select('h2')
        ps = post_content.select('p')
        videos = []
        for i, h2 in enumerate(h2s):
            p_txt = ps[i * 2] if i * 2 < len(ps) else None
            p_img = ps[i * 2 + 1] if i * 2 + 1 < len(ps) else None
            a_tag = p_txt.find('a') if p_txt else None
            if a_tag:
                videos.append({
                    'vod_id': a_tag.get('href', ''),
                    'vod_name': p_txt.get_text(strip=True),
                    'vod_pic': self._get_img_url(p_img) if p_img else '',
                    'vod_remarks': h2.get_text(strip=True)
                })
        return videos

    # --------------------------------------------------------
    # TVBox 接口
    # --------------------------------------------------------
    def homeContent(self, filter=False):
        try:
            r = self._fetch(self.host)
            if not r:
                return {'class': [], 'list': []}
            soup = self._soup(r.text)

            classes = []
            for sel in ['.category-list ul li', '.nav-menu li', '.menu li', 'nav ul li']:
                for li in soup.select(sel):
                    a = li.find('a')
                    if a:
                        href = (a.get('href') or '').strip()
                        name = a.get_text(strip=True)
                        if href and href != '#' and name:
                            classes.append({'type_name': name, 'type_id': href})
                if classes:
                    break

            if not classes:
                classes = [
                    {'type_name': '最新', 'type_id': '/latest/'},
                    {'type_name': '热门', 'type_id': '/hot/'}
                ]

            return {'class': classes, 'list': self._parse_list(soup)}
        except Exception as e:
            print(f"[DABATTLE] homeContent 异常: {e}")
            return {'class': [], 'list': []}

    def homeVideoContent(self):
        try:
            r = self._fetch(self.host)
            if not r:
                return {'list': []}
            return {'list': self._parse_list(self._soup(r.text))}
        except Exception as e:
            print(f"[DABATTLE] homeVideoContent 异常: {e}")
            return {'list': []}

    def categoryContent(self, tid, pg=1, filter=False, extend=None):
        try:
            # 合集页
            if '@folder' in tid:
                v = self._parse_folder(tid.replace('@folder', ''))
                return {'list': v, 'page': 1, 'pagecount': 1, 'limit': 90, 'total': len(v)}

            pg = int(pg) if pg else 1

            if tid.startswith('http'):
                base_url = tid.rstrip('/')
            else:
                base_url = (self.host + tid).rstrip('/') if tid.startswith('/') else (self.host + '/' + tid).rstrip('/')

            url = base_url + '/' if pg == 1 else base_url + '/' + str(pg) + '/'
            r = self._fetch(url)
            if not r:
                return {'list': [], 'page': pg, 'pagecount': 9999, 'limit': 90, 'total': 0}

            soup = self._soup(r.text)
            videos = self._parse_list(soup, tid)
            return {'list': videos, 'page': pg, 'pagecount': 9999, 'limit': 90, 'total': 999999}
        except Exception as e:
            print(f"[DABATTLE] categoryContent 异常: {e}")
            return {'list': [], 'page': pg, 'pagecount': 9999, 'limit': 90, 'total': 0}

    def detailContent(self, ids):
        try:
            vod_id = ids[0]
            url = vod_id if vod_id.startswith('http') else self.host + vod_id
            r = self._fetch(url)
            if not r:
                return {'list': []}
            soup = self._soup(r.text)

            plist = []
            used_names = set()

            # DPlayer data-config 解析
            for c, dplayer in enumerate(soup.select('.dplayer'), start=1):
                config_attr = dplayer.get('data-config')
                if config_attr:
                    try:
                        config = json.loads(config_attr)
                        video_url = config.get('video', {}).get('url', '')
                        if video_url:
                            ep_name = ''
                            parent = dplayer.parent
                            for _ in range(4):
                                if not parent:
                                    break
                                heading = parent.find('h2') or parent.find('h3') or parent.find('h4')
                                if heading:
                                    ep_name = heading.get_text(strip=True)
                                    break
                                parent = parent.parent
                            base_name = ep_name if ep_name else f"视频{c}"
                            name = base_name
                            count = 2
                            while name in used_names:
                                name = f"{base_name} {count}"
                                count += 1
                            used_names.add(name)
                            plist.append(f"{name}${video_url}")
                    except Exception:
                        continue

            # 正文链接回退
            if not plist:
                post_content = soup.select_one('.post-content') or soup.select_one('article')
                if post_content:
                    for i, a in enumerate(post_content.select('a'), start=1):
                        link_text = a.get_text(strip=True)
                        link_href = a.get('href')
                        if link_href and any(kw in link_text for kw in ['点击观看', '观看', '播放', '视频', '第一弹', '第二弹', '第三弹', '第四弹', '第五弹', '第六弹', '第七弹', '第八弹', '第九弹', '第十弹']):
                            ep_name = link_text.replace('点击观看：', '').replace('点击观看', '').strip()
                            if not ep_name:
                                ep_name = f"视频{i}"
                            if not link_href.startswith('http'):
                                link_href = self.host + link_href if link_href.startswith('/') else self.host + '/' + link_href
                            plist.append(f"{ep_name}${link_href}")

            play_url = '#'.join(plist) if plist else f"未找到视频源${url}"

            # 标签
            vod_content = ''
            try:
                tags = []
                seen_names = set()
                seen_ids = set()
                candidates = []
                for a in soup.select('.tags a, .keywords a, .post-tags a'):
                    title = a.get_text(strip=True)
                    href = a.get('href')
                    if title and href:
                        candidates.append({'name': title, 'id': href})
                candidates.sort(key=lambda x: len(x['name']), reverse=True)
                for item in candidates:
                    name = item['name']
                    id_ = item['id']
                    if id_ in seen_ids:
                        continue
                    is_dup = any(name in s for s in seen_names)
                    if not is_dup:
                        target = json.dumps({'id': id_, 'name': name})
                        tags.append(f'[a=cr:{target}/]{name}[/a]')
                        seen_names.add(name)
                        seen_ids.add(id_)
                vod_content = ' '.join(tags) if tags else soup.select_one('.post-title').get_text(strip=True) if soup.select_one('.post-title') else ''
            except Exception:
                vod_content = ''

            if not vod_content:
                h1 = soup.find('h1')
                vod_content = h1.get_text(strip=True) if h1 else '每日大乱斗'

            return {'list': [{
                'vod_play_from': '每日大乱斗',
                'vod_play_url': play_url,
                'vod_content': vod_content
            }]}
        except Exception as e:
            print(f"[DABATTLE] detailContent 异常: {e}")
            return {'list': [{'vod_play_from': '每日大乱斗', 'vod_play_url': '获取失败'}]}

    def playerContent(self, flag, id, vipFlags=None):
        """播放：直链 parse=0，m3u8 走代理"""
        if not id:
            return {'url': ''}
        if self.isVideoFormat(id):
            if '.m3u8' in id:
                proxy_url = self._build_proxy_url('m3u8', id)
                return {
                    'parse': 0,
                    'url': proxy_url,
                    'header': {
                        'User-Agent': UA,
                        'Referer': self.host + '/',
                    }
                }
            return {
                'parse': 0,
                'url': id,
                'header': {
                    'User-Agent': UA,
                    'Referer': self.host + '/',
                }
            }
        # 需要解析的 URL
        return {'parse': 1, 'url': id, 'header': {'User-Agent': UA}}

    def searchContent(self, key, quick=False, pg="1"):
        try:
            pg = int(pg) if pg else 1
            url = self.host + '/search/' + quote(key, safe='') + '/' if pg == 1 else self.host + '/search/' + quote(key, safe='') + '/' + str(pg) + '/'
            r = self._fetch(url)
            if not r:
                return {'list': [], 'page': pg, 'pagecount': 9999}
            soup = self._soup(r.text)
            return {'list': self._parse_list(soup), 'page': pg, 'pagecount': 9999}
        except Exception as e:
            print(f"[DABATTLE] searchContent 异常: {e}")
            return {'list': [], 'page': pg, 'pagecount': 9999}

    # --------------------------------------------------------
    # localProxy 代理
    # --------------------------------------------------------
    def _parse_proxy_params(self, param):
        if isinstance(param, dict):
            return param
        if isinstance(param, str):
            try:
                d = json.loads(param)
                if isinstance(d, dict):
                    return d
            except Exception:
                pass
            result = {}
            qs = param.split('?', 1)[1] if '?' in param else param
            for pair in qs.split('&'):
                if '=' in pair:
                    from urllib.parse import unquote
                    k, v = pair.split('=', 1)
                    result[k] = unquote(v)
            return result
        return {}

    def localProxy(self, param):
        try:
            p = self._parse_proxy_params(param)
            type_ = p.get('type', '')
            url = p.get('url', '')

            if type_ == 'cache':
                key = p.get('key', '')
                content = self._img_cache.get(key)
                if content:
                    return [200, 'image/jpeg', content]
                return [404, 'text/plain', b'Expired']

            if type_ == 'img':
                real_url = self._d64(url) if url and not url.startswith('http') else url
                if not real_url or not real_url.startswith('http'):
                    return [404, 'text/plain', b'']
                r = requests.get(real_url, headers=self.headers, timeout=10)
                content = _aes_decrypt_image(r.content)
                return [200, 'image/jpeg', content]

            if type_ == 'm3u8':
                return self._proxy_m3u8(url)

            # ts 代理
            if type_ == 'ts':
                real_url = self._d64(url) if url else ''
                if not real_url or not real_url.startswith('http'):
                    return [404, 'text/plain', b'']
                r = requests.get(real_url, headers=self.headers, timeout=10)
                return [200, 'video/mp2t', r.content]

            return [404, 'text/plain', b'']
        except Exception as e:
            print(f"[DABATTLE] localProxy 异常: {e}")
            return [404, 'text/plain', b'']

    def _proxy_m3u8(self, url_b64):
        """代理 m3u8"""
        try:
            url = self._d64(url_b64) if url_b64 else ''
            if not url or not url.startswith('http'):
                return [404, 'text/plain', b'']
            r = requests.get(url, headers=self.headers, timeout=15)
            if r.status_code != 200:
                return [r.status_code, 'text/plain', b'']
            text = r.text
            base = url.rsplit('/', 1)[0] + '/'
            lines = []
            for line in text.split('\n'):
                stripped = line.strip()
                if not stripped:
                    continue
                if '#EXT' not in stripped and stripped:
                    if not stripped.startswith('http'):
                        stripped = base + '/' + stripped.lstrip('/')
                    lines.append(self._build_proxy_url('ts', stripped))
                else:
                    lines.append(stripped)
            content = '\n'.join(lines) + '\n'
            return [200, 'application/vnd.apple.mpegurl', content.encode('utf-8')]
        except Exception as e:
            print(f"[DABATTLE] _proxy_m3u8 异常: {e}")
            return [500, 'text/plain', b'']