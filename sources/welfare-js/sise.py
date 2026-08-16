# -*- coding: utf-8 -*-
"""
四色福利 — vbox 修复版
修复内容：
1. getName 返回"四色"（原 R3E2O）
2. playerContent 的 header 从 json.dumps 字符串改为 dict
3. localProxy 兼容 iOS 端 JSON 字符串参数格式
4. m3u8 直链走本地代理（防盗链 + HLS 代理）
5. 清理过多的调试 print
"""
import sys, re, json, base64
from urllib.parse import quote, unquote, urljoin, urlparse
sys.path.append('..')
try:
    from base.spider import Spider as _B
except:
    class _B: pass
try:
    import requests
except:
    requests = None

U = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
IMG_HOST = 'https://4sbase64.dt188.site'

_DOMAIN_CANDIDATES = [
         'https://www.b5y0e.top',
         'https://www.q4k3i.top',
         'https://www.p4d9s.top'
                                  ]
_ENTER_PATH = '/enter.html'

def _discover_domain(candidates=None, timeout=10):
    candidates = candidates or _DOMAIN_CANDIDATES
    session = requests.Session()
    session.headers.update({'User-Agent': U, 'Referer': ''})
    for domain in candidates:
        try:
            r = session.get(domain + _ENTER_PATH, timeout=timeout, allow_redirects=True)
            if r.status_code in (200, 301, 302):
                final_url = r.url
                parsed = urlparse(final_url)
                return f'{parsed.scheme}://{parsed.netloc}'
        except:
            continue
    return candidates[0] if candidates else 'https://www.o8q9m.top'

_AES_KEY = 'IdTJq0HklpuI6mu8iB%OO@!vd^4K&uXW'
_AES_IV = '$0v@krH7V2883346'

_sbox = [
99,124,119,123,242,107,111,197,48,1,103,43,254,215,171,118,202,130,201,125,250,89,71,240,173,212,162,175,156,164,114,192,
183,253,147,38,54,63,247,204,52,165,229,241,113,216,49,21,4,199,35,195,24,150,5,154,7,18,128,226,235,39,178,117,
9,131,44,26,27,110,90,160,82,59,214,179,41,227,47,132,83,209,0,237,32,252,177,91,106,203,190,57,74,76,88,207,
208,239,170,251,67,77,51,133,69,249,2,127,80,60,159,168,81,163,64,143,146,157,56,245,188,182,218,33,16,255,243,210,
205,12,19,236,95,151,68,23,196,167,126,61,100,93,25,115,96,129,79,220,34,42,144,136,70,238,184,20,222,94,11,219,
224,50,58,10,73,6,36,92,194,211,172,98,145,149,228,121,231,200,55,109,141,213,78,169,108,86,244,234,101,122,174,8,
186,120,37,46,28,166,180,198,232,221,116,31,75,189,139,138,112,62,181,102,72,3,246,14,97,53,87,185,134,193,29,158,
225,248,152,17,105,217,142,148,155,30,135,233,206,85,40,223,140,161,137,13,191,230,66,104,65,153,45,15,176,84,187,22]
_inv_sbox = [82,9,106,213,48,54,165,56,191,64,163,158,129,243,215,251,124,227,57,130,155,47,255,135,52,142,67,68,196,222,233,203,84,123,148,50,166,194,35,61,238,76,149,11,66,250,195,78,8,46,161,102,40,217,36,178,118,91,162,73,109,139,209,37,114,248,246,100,134,104,152,22,212,164,92,204,93,101,182,146,108,112,72,80,253,237,185,218,94,21,70,87,167,141,157,132,144,216,171,0,140,188,211,10,247,228,88,5,184,179,69,6,208,44,30,143,202,63,15,2,193,175,189,3,1,19,138,107,58,145,17,65,79,103,220,234,151,242,207,206,240,180,230,115,150,172,116,34,231,173,53,133,226,249,55,232,28,117,223,110,71,241,26,113,29,41,197,137,111,183,98,14,170,24,190,27,252,86,62,75,198,210,121,32,154,219,192,254,120,205,90,244,31,221,168,51,136,7,199,49,177,18,16,89,39,128,236,95,96,81,127,169,25,181,74,13,45,229,122,159,147,201,156,239,160,224,59,77,174,42,245,176,200,235,187,60,131,83,153,97,23,43,4,126,186,119,214,38,225,105,20,99,85,33,12,125]
_rcon=[0,1,2,4,8,16,32,64,128,27,54]
def _gmul(a,b):
    p=0
    for _ in range(8):
        if b&1:p^=a
        hi=a&0x80; a=((a<<1)&0xff) ^ (0x1b if hi else 0); b//=2
    return p
def _subw(w): return [_sbox[x] for x in w]
def _rotw(w): return w[1:]+w[:1]
def _expand_key(k):
    Nk=len(k)//4; Nr=Nk+6; w=[list(k[i:i+4]) for i in range(0,len(k),4)]
    for i in range(Nk,4*(Nr+1)):
        t=w[i-1][:]
        if i%Nk==0:
            t=_subw(_rotw(t)); t[0]^=_rcon[i//Nk]
        elif Nk>6 and i%Nk==4:
            t=_subw(t)
        w.append([w[i-Nk][j]^t[j] for j in range(4)])
    return [sum(w[4*r:4*r+4],[]) for r in range(Nr+1)],Nr
def _add_round_key(s,rk):
    for c in range(4):
        for r in range(4): s[r][c]^=rk[4*c+r]
def _inv_sub_bytes(s):
    for r in range(4):
        for c in range(4): s[r][c]=_inv_sbox[s[r][c]]
def _inv_shift_rows(s):
    s[1]=s[1][-1:]+s[1][:-1]; s[2]=s[2][-2:]+s[2][:-2]; s[3]=s[3][-3:]+s[3][:-3]
def _inv_mix_columns(s):
    for c in range(4):
        a=[s[r][c] for r in range(4)]
        s[0][c]=_gmul(a[0],14)^_gmul(a[1],11)^_gmul(a[2],13)^_gmul(a[3],9)
        s[1][c]=_gmul(a[0],9)^_gmul(a[1],14)^_gmul(a[2],11)^_gmul(a[3],13)
        s[2][c]=_gmul(a[0],13)^_gmul(a[1],9)^_gmul(a[2],14)^_gmul(a[3],11)
        s[3][c]=_gmul(a[0],11)^_gmul(a[1],13)^_gmul(a[2],9)^_gmul(a[3],14)
def _aes_block_decrypt(block,key):
    rks,Nr=_expand_key(key)
    s=[[block[4*c+r] for c in range(4)] for r in range(4)]
    _add_round_key(s,rks[Nr])
    for rnd in range(Nr-1,0,-1):
        _inv_shift_rows(s); _inv_sub_bytes(s); _add_round_key(s,rks[rnd]); _inv_mix_columns(s)
    _inv_shift_rows(s); _inv_sub_bytes(s); _add_round_key(s,rks[0])
    return bytes(s[r][c] for c in range(4) for r in range(4))
def _aes_cbc_decrypt_pure(ct,key,iv):
    out=b''; prev=iv
    for i in range(0,len(ct),16):
        block=ct[i:i+16]
        dec=_aes_block_decrypt(block,key)
        out+=bytes(a^b for a,b in zip(dec,prev)); prev=block
    pad=out[-1]
    if 1<=pad<=16 and out.endswith(bytes([pad])*pad): out=out[:-pad]
    return out

def _py_aes_decrypt(ciphertext):
    if not ciphertext or not isinstance(ciphertext, str):
        return ciphertext
    ciphertext = unquote(ciphertext).strip()
    if ciphertext.startswith('http://') or ciphertext.startswith('https://'):
        return ciphertext
    if re.search(r'[\u4e00-\u9fff]', ciphertext):
        return ciphertext
    key = _AES_KEY.encode('utf-8')
    iv = _AES_IV.encode('utf-8')
    try:
        raw = ciphertext + '=' * ((4 - len(ciphertext) % 4) % 4)
        ct = base64.b64decode(raw)
        if ct.startswith(b'Salted__') and len(ct) > 16:
            ct = ct[16:]
        try:
            from Crypto.Cipher import AES
            from Crypto.Util.Padding import unpad
            out = unpad(AES.new(key, AES.MODE_CBC, iv).decrypt(ct), AES.block_size)
        except Exception:
            out = _aes_cbc_decrypt_pure(ct, key, iv)
        txt = out.decode('utf-8', 'ignore').strip().strip('"').strip("'")
        return txt if txt else ciphertext
    except Exception:
        return ciphertext

def _batch_decrypt(enc_list):
    if not enc_list:
        return {}
    return {enc: _py_aes_decrypt(enc) for enc in enc_list}

CLASSES = [
    {'type_id': 'juqing', 'type_name': '剧情区'},
    {'type_id': 'shipin', 'type_name': '电影区'},
    {'type_id': 'jingpin', 'type_name': '精品区'},
    {'type_id': 'image', 'type_name': '图片区'},
    {'type_id': 'lulu', 'type_name': '撸撸区'},
    {'type_id': 'novel', 'type_name': '小说区'},
    {'type_id': 'yousheng', 'type_name': '有声区'},
]

ZONE_SUB = {
    'juqing': [('最新剧情','/cYcL2p1cWluZy9saXN0cy5odG1s.html'),('  麻豆传媒','/cYcL2p1cWluZy9saXN0Lem6u%2BixhuS8oOWqki5odG1s.html'),('  天美传媒','/cYcL2p1cWluZy9saXN0LeWkqee%2BjuS8oOWqki5odG1s.html'),('  星空果冻','/cYcL2p1cWluZy9saXN0LeaYn%2BepuuaenOWGuy5odG1s.html'),('  蜜桃精东','/cYcL2p1cWluZy9saXN0LeicnOahg%2BeyvuS4nC5odG1s.html'),('  韩国伦理','/cYcL2p1cWluZy9saXN0LemfqeWbveS8pueQhi5odG1s.html'),('  COSPLAY','/cYcL2p1cWluZy9saXN0LUNPU1BMQVkuaHRtbA%3D%3D.html'),('  经典三级','/cYcL2p1cWluZy9saXN0Lee7j%2BWFuOS4iee6py5odG1s.html'),('  中文字幕','/cYcL2p1cWluZy9saXN0LeS4reaWh%2BWtl%2BW5lS5odG1s.html')],
    'shipin': [('最新电影','/cYcL3NoaXBpbi9saXN0cy5odG1s.html'),('  日本av','/cYcL3NoaXBpbi9saXN0LeaXpeacrGF2Lmh0bWw%3D.html'),('  韩国热舞','/cYcL3NoaXBpbi9saXN0LemfqeWbveeDreiIni5odG1s.html'),('  欧美精品','/cYcL3NoaXBpbi9saXN0Leasp%2Be%2BjueyvuWTgS5odG1s.html'),('  动漫电影','/cYcL3NoaXBpbi9saXN0LeWKqOa8q%2BeUteW9sS5odG1s.html'),('  国产自拍','/cYcL3NoaXBpbi9saXN0LeWbveS6p%2BiHquaLjS5odG1s.html'),('  岛国无码','/cYcL3NoaXBpbi9saXN0LeWym%2BWbveaXoOeggS5odG1s.html'),('  JVID','/cYcL3NoaXBpbi9saXN0LUpWSUQuaHRtbA%3D%3D.html'),('  SM调教','/cYcL3NoaXBpbi9saXN0LVNN6LCD5pWZLmh0bWw%3D.html')],
    'jingpin': [('最新精选','/cYcL2ppbmdwaW4vbGlzdHMuaHRtbA%3D%3D.html'),('  软萌福利姬','/cYcL2ppbmdwaW4vbGlzdC3ova%2FokIznpo%2FliKnlp6wuaHRtbA%3D%3D.html'),('  黑料头条','/cYcL2ppbmdwaW4vbGlzdC3pu5HmlpnlpLTmnaEuaHRtbA%3D%3D.html'),('  明星AI','/cYcL2ppbmdwaW4vbGlzdC3mmI7mmJ9BSS5odG1s.html'),('  人妖伪娘','/cYcL2ppbmdwaW4vbGlzdC3kurrlppbkvKrlqJguaHRtbA%3D%3D.html'),('  onlyfans','/cYcL2ppbmdwaW4vbGlzdC1vbmx5ZmFucy5odG1s.html'),('  探花系列','/cYcL2ppbmdwaW4vbGlzdC3mjqLoirHns7vliJcuaHRtbA%3D%3D.html'),('  主播大秀','/cYcL2ppbmdwaW4vbGlzdC3kuLvmkq3lpKfnp4AuaHRtbA%3D%3D.html'),('  韩国主播','/cYcL2ppbmdwaW4vbGlzdC3pn6nlm73kuLvmkq0uaHRtbA%3D%3D.html')],
    'image': [('卡通动漫','/cYcL3R1cGlhbi9saXN0LeWNozemAmuWKqOa8qy5odG1s.html'),('  亚洲图片','/cYcL3R1cGlhbi9saXN0LeS6mua0suWbvueJhy5odG1s.html'),('  欧美图片','/cYcL3R1cGlhbi9saXN0Leasp%2Be%2BjuWbvueJhy5odG1s.html'),('  偷拍自拍','/cYcL3R1cGlhbi9saXN0LeWBt%2BaLjeiHquaLjS5odG1s.html'),('  乱伦熟女','/cYcL3R1cGlhbi9saXN0LeS5seS8pueGn%2BWlsy5odG1s.html'),('  同性美图','/cYcL3R1cGlhbi9saXN0LeWQjOaAp%2Be%2BjuWbvi5odG1s.html'),('  美腿丝袜','/cYcL3R1cGlhbi9saXN0Lee%2BjuiFv%2BS4neiinC5odG1s.html'),('  辣椒漫画','/cYcL3R1cGlhbi9saXN0Le62jOaApeWKqOa8qy5odG1s.html')],
    'lulu': [('推女郎','/cYcL21laW52L2xpc3Qt5o6o5aWz6YOOLmh0bWw%3D.html'),('  头条女神','/cYcL21laW52L2xpc3Qt5aS05p2h5aWz56WeLmh0bWw%3D.html'),('  3Agirl写真','/cYcL21laW52L2xpc3QtM0FnaXJs5YaZ55yfLmh0bWw%3D.html'),('  推女神','/cYcL21laW52L2xpc3Qt5o6o5aWz56WeLmh0bWw%3D.html'),('  爱蜜社','/cYcL21laW52L2xpc3Qt54ix6Jyc56S%2BLmh0bWw%3D.html'),('  美媛馆新刊','/cYcL21laW52L2xpc3Qt576O5aqb6aaG5paw5YiKLmh0bWw%3D.html'),('  秀人网','/cYcL21laW52L2xpc3Qt56eA5Lq6572RLmh0bWw%3D.html'),('  日本女优','/cYcL21laW52L2xpc3Qt5ZKo6K6v55uG57O7Lmh0bWw%3D.html')],
    'novel': [('家庭乱伦','/cYcL3hpYW9zaHVvL2xpc3Qt5a625bqt5Lmx5LymLmh0bWw%3D.html'),('  武侠古典','/cYcL3hpYW9zaHVvL2xpc3Qt5q2m5L6g5Y%2Bk5YW4Lmh0bWw%3D.html'),('  都市生活','/cYcL3hpYW9zaHVvL2xpc3Qt6YO95biC55Sf5rS7Lmh0bWw%3D.html'),('  校园春色','/cYcL3hpYW9zaHVvL2xpc3Qt5qCh5Zut5pil6ImyLmh0bWw%3D.html'),('  明星系列','/cYcL3hpYW9zaHVvL2xpc3Qt5piO5pif57O75YiXLmh0bWw%3D.html'),('  午夜怪谈','/cYcL3hpYW9zaHVvL2xpc3Qt5Y2I5aSc5oCq6LCILmh0bWw%3D.html'),('  十大名著','/cYcL3hpYW9zaHVvL2xpc3Qt5Y2B5aSn5ZCN6JGXLmh0bWw%3D.html'),('  长篇连载','/cYcL3hpYW9zaHVvL2xpc3Qt6ZW%2F56%2BH6L%2Be6L29Lmh0bWw%3D.html')],
    'yousheng': [('长篇有声','/cYcL3lvdXNoZW5nL2xpc3Qt6ZW%2F56%2BH5pyJ5aOwLmh0bWw%3D.html'),('  短篇有声','/cYcL3lvdXNoZW5nL2xpc3Qt55%2Bt56%2BH5pyJ5aOwLmh0bWw%3D.html')],
}

class Spider(_B):
    def init(self, ext=''):
        self.s = requests.Session()
        self.s.headers.update({'User-Agent': U})
        self.cache = {}
        if ext and ext.startswith('http'):
            self.H = ext.rstrip('/')
        else:
            self.H = _discover_domain()

        # 解密子分类名称
        try:
            all_names = list({n for items in ZONE_SUB.values() for n, u in items})
            if all_names:
                dec = _batch_decrypt(all_names)
                for zone in ZONE_SUB:
                    ZONE_SUB[zone] = [(dec.get(n, n), u) for n, u in ZONE_SUB[zone]]
        except Exception as e:
            print(f'[四色]解密异常: {e}')

    def getName(self):
        return '四色'

    def isVideoFormat(self, u):
        return '.m3u8' in u or '.mp4' in u

    def manualVideoCheck(self):
        return False

    def _get(self, u):
        if not u.startswith('http'):
            u = self.H + u
        try:
            r = self.s.get(u, timeout=20, headers={'User-Agent': U, 'Referer': self.H + '/'}, allow_redirects=True)
            r.encoding = 'utf-8'
            return r.text
        except Exception as e:
            print(f'[四色]请求异常: {e}')
            return ''

    def _proxy(self, kind, url):
        """构建本地代理 URL（vbox 基类 getProxyUrl）"""
        try:
            return self.getProxyUrl() + '&kind=' + kind + '&url=' + quote(url, safe='')
        except:
            return url

    def _image(self, path):
        return self._proxy('img', IMG_HOST + path) if path else ''

    def _hls(self, url):
        return self._proxy('hls', url)

    def _abs(self, u):
        if not u:
            return ''
        u = unquote(u).replace('\\/', '/')
        if u.startswith('http://') or u.startswith('https://'):
            return u
        if u.startswith('//'):
            return 'https:' + u
        return self.H + u if u.startswith('/') else self.H + '/' + u

    def _extract_mp3(self, h):
        if not h:
            return ''
        m = re.search(r'https?://[^\"\s<>]+\.mp3(?:\?[^\"\s<>]*)?', h, re.I)
        if m:
            return unquote(m.group(0).replace('\\/', '/'))
        for p in [r'(?:src|data-src|href)=[\"\']([^\"\']+\.mp3[^\"\']*)', r'playUrl\s*=\s*[\"\']([^\"\']+\.mp3[^\"\']*)']:
            m = re.search(p, h, re.I)
            if m:
                return self._abs(m.group(1))
        return ''

    def _novel_result_from_html(self, h, fallback_title='小说阅读'):
        title = fallback_title or '小说阅读'
        for ptn in [r'class="novel-detail-title[^\"]*"[^>]*title="([^\"]+)"', r'class="novel-nav-bar-title[^\"]*"[^>]*title="([^\"]+)"', r'<title>([^<]+)</title>']:
            tm = re.search(ptn, h, re.S)
            if tm:
                title = _py_aes_decrypt(tm.group(1).strip()) or title
                break
        cm = re.search(r'class="novel-detail-content"[^>]*data-content="([^\"]+)"', h, re.S)
        if not cm:
            return None
        text = _py_aes_decrypt(cm.group(1).strip())
        text = re.sub(r'<br\s*/?>', '\n', text, flags=re.I)
        text = re.sub(r'</p\s*>', '\n', text, flags=re.I)
        text = re.sub(r'<[^>]+>', '', text)
        lines = [x.strip() for x in text.split('\n') if x.strip()]
        content = '　　' + '\n\n　　'.join(lines) if lines else text.strip()
        if not content.strip():
            return None
        return {'parse': 0, 'url': 'novel://' + json.dumps({'title': title, 'content': content}, ensure_ascii=False), 'header': ''}

    def _pic(self, path):
        if not path:
            return ''
        if path.startswith('http://') or path.startswith('https://'):
            return self._proxy('img', path)
        if path.startswith('//'):
            return self._proxy('img', 'https:' + path)
        return self._image(path if path.startswith('/') else '/' + path)

    def _cyc_page_path(self, path, pg):
        try:
            pg = int(pg)
        except:
            pg = 1
        if pg <= 1 or not path.startswith('/cYc') or not path.endswith('.html'):
            return path
        enc = path[4:-5]
        enc = unquote(enc)
        enc += '=' * ((4 - len(enc) % 4) % 4)
        raw = base64.b64decode(enc).decode('utf-8')
        if raw.endswith('.html'):
            raw = raw[:-5] + '-' + str(pg) + '.html'
        out = base64.b64encode(raw.encode('utf-8')).decode('utf-8')
        return '/cYc' + quote(out, safe='') + '.html'

    def _parse_items(self, h, zone_type):
        if zone_type in ('juqing', 'shipin', 'jingpin'):
            return self._parse_video_items(h)
        elif zone_type in ('image', 'lulu'):
            return self._parse_image_items(h)
        elif zone_type == 'novel':
            return self._parse_novel_items(h)
        elif zone_type == 'yousheng':
            return self._parse_audio_items(h)
        return self._parse_video_items(h)

    def _parse_video_items(self, h):
        v, enc = [], {}
        for m in re.finditer(r'<a[^>]*class="video-item"[^>]*href="([^"]+)"[^>]*>', h, re.S):
            href = m.group(1)
            end = h.find('</a>', m.end())
            inner = h[m.end():end] if end > 0 else ''
            tm = re.search(r'class="video-item-title[^"]*"[^>]*title="([^"]*)"', inner)
            raw_title = _py_aes_decrypt(tm.group(1).strip()) if tm else ''
            im = re.search(r'data-base64="([^"]+)"', inner)
            img = self._image(im.group(1)) if im else ''
            dm = re.search(r'class="video-item-date"[^>]*>([^<]+)', inner)
            date = dm.group(1).strip() if dm else ''
            enc[href] = raw_title
            v.append({'vod_id': href, 'vod_name': raw_title, 'vod_pic': img, 'vod_remarks': date})
        if enc:
            dec = _batch_decrypt(list(enc.values()))
            for item in v:
                k = enc[item['vod_id']]
                item['vod_name'] = dec.get(k, k)
                self.cache[item['vod_id']] = {'name': item['vod_name'], 'pic': item['vod_pic']}
                if not item['vod_id'].startswith('http'):
                    self.cache[self.H + item['vod_id']] = {'name': item['vod_name'], 'pic': item['vod_pic']}
                elif item['vod_id'].startswith(self.H):
                    self.cache[item['vod_id'][len(self.H):]] = {'name': item['vod_name'], 'pic': item['vod_pic']}
        return v

    def _parse_image_items(self, h):
        v, seen = [], set()
        for m in re.finditer(r'<a[^>]*class="[^"]*video-item[^"]*"[^>]*href="([^"]+)"[^>]*>(.*?)</a>', h, re.S):
            href, inner = m.group(1), m.group(2)
            title = ''
            tm = re.search(r'class="[^"]*video-item-title[^"]*"[^>]*title="([^"]*)"', inner, re.S)
            if tm:
                title = _py_aes_decrypt(tm.group(1).strip())
            if not title:
                tm = re.search(r'class="[^"]*video-item-title[^"]*"[^>]*>(.*?)</div>', inner, re.S)
                if tm:
                    title = _py_aes_decrypt(re.sub(r'<[^>]+>', '', tm.group(1)).strip())
            pic = ''
            im = re.search(r'data-pic-base64="([^"]+)"', inner, re.S)
            if im:
                pic = self._pic(im.group(1).strip())
            dm = re.search(r'class="[^"]*video-item-date[^"]*"[^>]*>([^<]+)', inner, re.S)
            date = dm.group(1).strip() if dm else ''
            if href and title:
                key = href if href.startswith('http') else (self.H + href if href.startswith('/') else self.H + '/' + href)
                if key not in seen:
                    seen.add(key)
                    v.append({'vod_id': href, 'vod_name': title, 'vod_pic': pic, 'vod_remarks': date})
                    self.cache[href] = {'name': title, 'pic': pic}
                    self.cache[key] = {'name': title, 'pic': pic}
        return v

    def _parse_novel_items(self, h):
        v, seen = [], set()
        for m in re.finditer(r'<a[^>]*class="[^"]*novel-item[^"]*"[^>]*href="([^"]+)"[^>]*>(.*?)</a>', h, re.S):
            href, inner = m.group(1), m.group(2)
            title = ''
            tm = re.search(r'class="[^"]*novel-item-title[^"]*"[^>]*title="([^"]*)"', inner, re.S)
            if tm:
                title = _py_aes_decrypt(tm.group(1).strip())
            if not title:
                tm = re.search(r'class="[^"]*novel-item-title[^"]*"[^>]*>(.*?)</div>', inner, re.S)
                if tm:
                    title = _py_aes_decrypt(re.sub(r'<[^>]+>', '', tm.group(1)).strip())
            dm = re.search(r'class="[^"]*novel-item-date[^"]*"[^>]*>([^<]+)', inner, re.S)
            date = dm.group(1).strip() if dm else ''
            if href and title:
                key = href if href.startswith('http') else (self.H + href if href.startswith('/') else self.H + '/' + href)
                if key not in seen:
                    seen.add(key)
                    v.append({'vod_id': href, 'vod_name': title, 'vod_pic': self.H + '/assets/images/cover-default.png', 'vod_remarks': date})
                    self.cache[href] = {'name': title, 'pic': self.H + '/assets/images/cover-default.png'}
                    self.cache[key] = {'name': title, 'pic': self.H + '/assets/images/cover-default.png'}
        return v

    def _parse_audio_items(self, h):
        return self._parse_novel_items(h)

    def homeContent(self, filter=False):
        flt = {}
        for c in CLASSES:
            zone = c['type_id']
            items = ZONE_SUB.get(zone, [])
            flt[zone] = [{'key': 'z', 'name': '子分类', 'value': [{'n': n, 'v': u} for n, u in items]}]
        return {'class': CLASSES, 'filters': flt}

    def homeVideoContent(self):
        h = self._get('/index/home.html')
        if not h or 'enter-content' in h:
            return {'list': []}
        cards = self._parse_items(h, 'juqing')
        if not cards:
            cards = self._parse_items(h, 'image')
        return {'list': cards}

    def categoryContent(self, tid, pg=1, filter=False, extend=None):
        try:
            pg = int(str(pg))
        except:
            pg = 1
        try:
            zone = str(tid)
            sub_list = ZONE_SUB.get(zone, [])
            path = sub_list[0][1] if sub_list else ''
            if extend and 'z' in extend:
                for n, u in sub_list:
                    if u == extend['z'] or n.strip() == extend['z']:
                        path = u
                        break
            if not path:
                return {'list': [], 'page': pg, 'pagecount': 1}
            if zone in ('juqing', 'shipin', 'jingpin'):
                url = self.H + path
                if pg > 1:
                    url += ('&page=' if '?' in url else '?page=') + str(pg)
            else:
                url = self.H + self._cyc_page_path(path, pg)

            h = self._get(url)
            if not h or 'enter-content' in h:
                return {'list': [], 'page': pg, 'pagecount': pg}
            cards = self._parse_items(h, zone)

            if zone in ('juqing', 'shipin', 'jingpin'):
                pagecount = 999 if cards else pg
            else:
                pagecount = pg
                m = re.search(r'(\d+)\s*/\s*(\d+)', h)
                if m:
                    try:
                        pagecount = int(m.group(2))
                    except:
                        pagecount = 999 if cards else pg
                elif cards:
                    pagecount = max(pg + 1, 999)

            return {'list': cards, 'page': pg, 'pagecount': pagecount, 'limit': len(cards), 'total': len(cards)}
        except Exception as e:
            print(f'[四色]cat error: {e}')
            return {'list': [], 'page': pg, 'pagecount': pg}

    def detailContent(self, ids):
        play_url = str(ids[0])
        if not play_url.startswith('http'):
            play_url = self.H + play_url

        cached = self.cache.get(play_url, {})
        if not cached and play_url.startswith(self.H):
            cached = self.cache.get(play_url[len(self.H):], {})
        title = cached.get('name', '')
        img = cached.get('pic', '')

        h = self._get(play_url)
        if not h:
            return {'list': []}

        if not title:
            for pattern in [
                r'<h1[^>]*>(.*?)</h1>',
                r'<title>([^<]+)</title>',
                r'class="[^\"]*dec-ti[^\"]*"[^>]*title="([^\"]+)"',
                r'class="video-item-title[^\"]*"[^>]*title="([^\"]+)"',
                r'class="tupian-detail-title"[^>]*>.*?title="([^\"]+)"',
                r'class="common-detail-title[^\"]*"[^>]*title="([^\"]+)"',
            ]:
                m = re.search(pattern, h, re.S)
                if m:
                    raw = re.sub(r'<[^>]+>', '', m.group(1)).strip()
                    title = _py_aes_decrypt(raw)
                    if title:
                        break
            if not title:
                title = play_url

        # 图集
        if 'tupian-detail-content' in h or 'videopic lazy' in h:
            pics = []
            for m in re.finditer(r'data-pic-base64="([^"]+)"', h):
                pic = self._pic(m.group(1).strip())
                if pic and pic not in pics:
                    pics.append(pic)
            if pics:
                return {'list': [{'vod_id': play_url, 'vod_name': title, 'vod_pic': pics[0],
                    'type_name': '圖片', 'vod_year': '', 'vod_area': '', 'vod_remarks': '',
                    'vod_actor': '', 'vod_director': '', 'vod_content': '',
                    'vod_play_from': '圖片集', 'vod_play_url': '圖片集$' + 'pics://' + '&&'.join(pics)}]}

        mp3 = self._extract_mp3(h)
        if not mp3 and ('common-detail-button' in h or 'novel-chapter-item' in h or 'yousheng' in play_url):
            btn_match = re.search(r'class="[^"]*common-detail-button[^"]*"[^>]*href="([^"]+)"', h)
            if not btn_match:
                btn_match = re.search(r'class="[^"]*novel-chapter-item[^"]*"[^>]*href="([^"]+)"', h)

            if btn_match:
                real_play_page = self._abs(btn_match.group(1))
                return {'list': [{'vod_id': real_play_page, 'vod_name': title, 'vod_pic': img,
                    'type_name': '有聲', 'vod_year': '', 'vod_area': '', 'vod_remarks': '有聲播放',
                    'vod_actor': '', 'vod_director': '', 'vod_content': '',
                    'vod_play_from': '有聲播放', 'vod_play_url': '立即收聽$' + real_play_page}]}

        if mp3:
            return {'list': [{'vod_id': mp3, 'vod_name': title, 'vod_pic': img,
                'type_name': '有聲', 'vod_year': '', 'vod_area': '', 'vod_remarks': '',
                'vod_actor': '', 'vod_director': '', 'vod_content': '',
                'vod_play_from': '有聲', 'vod_play_url': '有聲$' + mp3}]}

        if 'novel-chapter' in h or 'novel-item-wrap' in h or 'common-detail' in h:
            chapter_url = ''
            m = re.search(r'href="([^"]*chapter[^"]*)"', h)
            if m:
                chapter_url = self._abs(m.group(1))
            if chapter_url:
                return {'list': [{'vod_id': chapter_url, 'vod_name': title, 'vod_pic': img,
                    'type_name': '小說/有聲', 'vod_year': '', 'vod_area': '', 'vod_remarks': '',
                    'vod_actor': '', 'vod_director': '', 'vod_content': '',
                    'vod_play_from': '閱讀', 'vod_play_url': '閱讀$' + chapter_url}]}

        if not img:
            for pattern in [
                r'<meta[^>]*property="og:image"[^>]*content="([^"]+)"',
                r'<img[^>]*data-base64="([^"]+)"',
                r'data-original="([^"]+)"',
            ]:
                m = re.search(pattern, h)
                if m:
                    img_raw = _py_aes_decrypt(m.group(1))
                    if img_raw.startswith('http'):
                        img = img_raw
                    elif img_raw:
                        img = IMG_HOST + img_raw
                    break

        # 提取视频地址
        vm = re.search(r"var video\s*=\s*decodeString\('([^']+)'\)", h)
        hm = re.search(r"var m3u8_host\s*=\s*decodeString\('([^']+)'\)", h)
        src = ''
        if vm and hm:
            try:
                vpath = base64.b64decode(vm.group(1)).decode()
            except Exception:
                vpath = ''
            try:
                hurl = base64.b64decode(hm.group(1)).decode()
            except Exception:
                hurl = ''
            if hurl and vpath:
                src = self._hls(hurl.rstrip('/') + '/' + vpath.lstrip('/'))

        pf = ['线路1']
        pu = ['线路1$' + src] if src else ['线路1$' + play_url]
        return {'list': [{'vod_id': play_url, 'vod_name': title, 'vod_pic': img,
            'type_name': '', 'vod_year': '', 'vod_area': '', 'vod_remarks': '',
            'vod_actor': '', 'vod_director': '', 'vod_content': '',
            'vod_play_from': '$$$'.join(pf), 'vod_play_url': '$$$'.join(pu)}]}

    def playerContent(self, flag, id, vipFlags=None):
        """
        vbox 修复：header 返回 dict 而非 json.dumps 字符串
        m3u8 直链直接返回（已经走了 hls 代理）
        """
        if id.startswith('pics://'):
            return {'parse': 0, 'url': id, 'header': {'User-Agent': U, 'Referer': self.H + '/'}}

        # m3u8 / mp4 / mp3 直链
        if id and ('.m3u8' in id or '.mp4' in id or id.lower().split('?', 1)[0].endswith('.mp3')):
            return {'parse': 0, 'url': id, 'header': {'User-Agent': U, 'Referer': self.H + '/'}}

        # http 链接，尝试二次解析
        if id.startswith('http://') or id.startswith('https://'):
            try:
                h = self._get(id)
                mp3 = self._extract_mp3(h)
                if not mp3:
                    mp3_match = re.search(r'<source[^>]*src="([^"]+\.mp3)"', h, re.I) or re.search(r'(https?://[^"\s]+\.mp3)', h, re.I)
                    if mp3_match:
                        mp3 = mp3_match.group(1).strip()

                if mp3:
                    return {'parse': 0, 'url': mp3, 'header': {'User-Agent': U, 'Referer': id}}

                nr = self._novel_result_from_html(h)
                if nr:
                    return nr
            except Exception as e:
                print(f'[四色]player pass error: {e}')

        # 兜底：重新走 detailContent
        d = self.detailContent([id])
        if d and d.get('list'):
            us = d['list'][0].get('vod_play_url', '').split('$$$')
            if us:
                f = us[0]
                url = f.split('$', 1)[1] if '$' in f else f
                return {'parse': 0, 'url': url, 'header': {'User-Agent': U, 'Referer': self.H + '/'}}
        return {'url': ''}

    def searchContent(self, key, quick=False, pg=1):
        return {'list': []}

    # ==================== 本地代理（vbox 修复版） ====================

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
        本地代理：img / hls / bin
        vbox 修复：兼容 iOS JSON 字符串参数
        """
        try:
            p = self._parse_proxy_params(param)
            raw = p.get('url', '')
            kind = p.get('kind', '')
            url = unquote(raw) if raw else ''

            if not url.startswith('https://'):
                return [404, 'text/plain', b'']

            headers = {'User-Agent': U, 'Referer': self.H + '/'}
            r = self.s.get(url, headers=headers, timeout=30)
            if r.status_code != 200:
                return [r.status_code, 'text/plain', b'']

            if kind == 'img':
                text = r.text.strip()
                if text.startswith('data:image/') and ',' in text:
                    meta, payload = text.split(',', 1)
                    return [200, meta[5:meta.index(';')], base64.b64decode(payload)]
                return [200, r.headers.get('Content-Type', 'image/jpeg'), r.content]

            if kind == 'hls' or kind == 'm3u8':
                out = []
                for line in r.text.splitlines():
                    if line.startswith('#EXT-X-KEY:'):
                        line = re.sub(r'URI="([^"]+)"', lambda m: 'URI="' + self._proxy('bin', urljoin(url, m.group(1))) + '"', line)
                    out.append(line)
                return [200, 'application/vnd.apple.mpegurl', '\n'.join(out).encode()]

            # bin / 默认
            return [200, r.headers.get('Content-Type', 'application/octet-stream'), r.content]
        except Exception as e:
            print(f'[四色]localProxy error: {e}')
            return [500, 'text/plain', b'']
