# -*- coding: utf-8 -*-
"""
平台名称：推特APP
平台标识：tuite_py
作者：原始 drpy-writer · 适配：vbox Python Spider 框架
适配日期：2026-08-19
说明：
  - 修复 super().init() 注入 host
  - 修复 isVideoFormat / manualVideoCheck
  - 修复 localProxy URL 协议（用 getProxyUrl() 携带 platformKey）
  - 详情页补封面（从列表 cover 复用）
  - 并发域名探测：defaultHosts + 5 个 .work 顶级域随机子域同时试，先到先用
"""

from base.spider import Spider as BaseSpider
import json
import random
import string
import time
import hashlib
import requests
from concurrent.futures import ThreadPoolExecutor, as_completed
from base64 import b64decode
from urllib.parse import quote, unquote, parse_qs
from Crypto.Cipher import AES
from Crypto.Util.Padding import unpad


class Spider(BaseSpider):
    # ── 5 个 .work 顶级域，配合 random 子域做选线
    HS = ['wcyfhknomg', 'pdcqllfomw', 'alxhzjvean', 'bqeaaxzplt', 'hfbtpixjso']

    # 每个顶级域派生 4 个随机子域，并发探测
    SUB_PER_TOP = 4

    UA = ('Mozilla/5.0 (Linux; Android 11; M2012K10C Build/RP1A.200720.011; wv) '
          'AppleWebKit/537.36 (KHTML, like Gecko) Version/4.0 '
          'Chrome/87.0.4280.141 Mobile Safari/537.36;SuiRui/twitter/ver=1.4.4')

    # AES 响应解密 key（base64）
    AES_KEY_B64 = 'SmhiR2NpT2lKSVV6STFOaQ=='

    # 封面 XOR 解密密钥（图片头 100 字节）
    IMG_XOR_KEY = '2020-zq3-888'

    # 探测超时
    PROBE_TIMEOUT = 4
    # 并发探测时整体最多等多久
    PROBE_DEADLINE = 6

    def getName(self):
        return '推特APP'

    # ──────────────────────────────────────────────
    # 初始化
    # ──────────────────────────────────────────────
    def init(self, extend=""):
        # 1) 先 super，让 base.spider 从 _vbox_effective_hosts 注入 self.host
        super().init(extend)

        # 2) 兜底：super 后 host 仍为空，用 defaultHosts 的第一个
        if not self.host:
            injected = (getattr(self, '_vbox_effective_hosts', None)
                        or globals().get('_vbox_effective_hosts')) or []
            if injected:
                self.host = str(injected[0]).rstrip('/')
                self._backup_hosts = [str(h).rstrip('/') for h in injected[1:]]
            else:
                # 完全没有 defaultHosts 配置，派生第一个候选
                self.host = self._candidate_url(self.HS[0])

        self.did = self._did()
        self.session = requests.Session()
        self.token, self.phost, self.host = self._token()
        self.api_cache = {}
        self.img_cache = {}

    def destroy(self):
        try:
            if self.session:
                self.session.close()
        except Exception:
            pass

    # ──────────────────────────────────────────────
    # 标准 5 接口
    # ──────────────────────────────────────────────
    def homeContent(self, filter):
        data = self._api('/api/video/classifyList')
        classes = [{'type_name': '精选', 'type_id': 'jx'}]
        for i in (data.get('data') or []):
            tid = str(i.get('classifyId', ''))
            name = i.get('classifyTitle', '')
            if tid and name:
                classes.append({'type_name': name, 'type_id': tid})
        sort = [{'key': 'fl', 'name': '分类',
                 'value': [{'n': '最近更新', 'v': '1'},
                           {'n': '最多播放', 'v': '2'},
                           {'n': '好评榜',   'v': '3'}]}]
        filters = {c['type_id']: sort for c in classes if c['type_id'] != 'jx'}
        filters['jx'] = [{'key': 'type', 'name': '精选',
                          'value': [{'n': '日榜', 'v': '1'},
                                    {'n': '周榜', 'v': '2'},
                                    {'n': '月榜', 'v': '3'},
                                    {'n': '总榜', 'v': '4'}]}]
        return {'class': classes, 'filters': filters}

    def homeVideoContent(self):
        return {'list': self.categoryContent('jx', '1', False, {'type': '1'}).get('list', [])}

    def categoryContent(self, tid, pg, filter, extend):
        pg = str(pg or '1')
        ext = extend or {}
        if tid == 'jx':
            path = '/api/video/getRankVideos?pageSize=20&page=%s&type=%s' % (pg, ext.get('type', '1'))
        elif 'click' in str(tid):
            uid = str(tid).replace('click', '')
            path = '/api/video/queryPersonVideoByType?pageSize=20&page=%s&userId=%s' % (pg, uid)
        else:
            path = ('/api/video/queryVideoByClassifyId?pageSize=20&page=%s&classifyId=%s&sortType=%s'
                    % (pg, tid, ext.get('fl', '1')))
        data = self._api(path)
        arr = (data.get('data', []) if isinstance(data.get('data', []), list)
               else data.get('videoList', []))
        return {'list': self._items(arr, 'click' in str(tid)),
                'page': int(pg), 'pagecount': 9999, 'limit': 20, 'total': 999999}

    def detailContent(self, array):
        raw = str(array[0])
        click = 'click' in raw
        pp = raw.replace('click', '').split('?', 2)
        vid = pp[0] if len(pp) > 0 else raw
        uid = pp[1] if len(pp) > 1 else ''
        name = unquote(pp[2]) if len(pp) > 2 else '推特APP'

        data = self._api('/api/video/can/watch?videoId=%s' % vid)
        url = (data.get('playPath', '') or data.get('url', '') or data.get('playUrl', ''))

        # 拿一个可用封面：优先从缓存里 list 抽到
        pic = ''
        try:
            cache_items = []
            for v in (self.api_cache or {}).values():
                if isinstance(v, dict):
                    for arr_key in ('data', 'videoList', 'list'):
                        v2 = v.get(arr_key)
                        if isinstance(v2, list):
                            cache_items.extend(v2)
            for it in cache_items:
                if str(it.get('videoId', '')) == vid:
                    cover = it.get('coverImg') or []
                    p = (cover[0] if isinstance(cover, list) and cover
                         else cover if isinstance(cover, str) else '')
                    if p:
                        pic = self._proxy(p, 'img')
                    break
        except Exception:
            pass

        director = (name if (click or not uid)
                    else '[a=cr:' + json.dumps({'id': uid + 'click', 'name': name},
                                                ensure_ascii=False) + '/]' + name + '[/a]')

        vod = {
            'vod_id': raw,
            'vod_name': name,
            'vod_pic': pic,
            'vod_director': director,
            'vod_content': name,
            'vod_play_from': '推特',
            'vod_play_url': (name + '$' + url) if url else '',
        }
        return {'list': [vod]}

    def searchContent(self, key, quick, pg='1'):
        data = self._api('/api/search/keyWord?pageSize=20&page=%s&searchWord=%s&searchType=1'
                         % (pg, quote(key)))
        return {'list': self._items(data.get('videoList', []), False),
                'page': int(pg), 'pagecount': 9999, 'limit': 20, 'total': 999999}

    def playerContent(self, flag, id, vipFlags):
        # vod_id 格式: "videoId?userId?URLEncoded昵称" 或直接是 playPath
        raw = str(id or '').split('?', 1)[0]
        try:
            if raw.startswith('http://') or raw.startswith('https://'):
                return {'parse': 0, 'playUrl': '', 'url': raw, 'header': self._headers()}
            data = self._api('/api/video/can/watch?videoId=%s' % raw)
            url = (data.get('playPath', '') or data.get('url', '') or
                   data.get('playUrl', '') or raw)
            if url.startswith('http://') or url.startswith('https://'):
                return {'parse': 0, 'playUrl': '', 'url': url, 'header': self._headers()}
            return {'parse': 0, 'playUrl': '', 'url': raw, 'header': self._headers()}
        except Exception:
            return {'parse': 0, 'playUrl': '', 'url': raw, 'header': self._headers()}

    def localProxy(self, param):
        # param 可能是 dict 也可能是 query string
        if isinstance(param, dict):
            tp = param.get('type') or param.get('do') or 'img'
            u = unquote(param.get('url') or param.get('u') or '')
        else:
            q = parse_qs(str(param or ''))
            tp = (q.get('type') or q.get('do') or ['img'])[0]
            u = unquote((q.get('url') or q.get('u') or [''])[0])
        if not u:
            return [404, 'text/plain', b'']
        ct, body = self._img_asset(u)
        return [200, ct or 'image/jpeg', body]

    def isVideoFormat(self, url):
        return any(x in str(url or '').lower() for x in ('.m3u8', '.mp4', '.m3u', '.mpd'))

    def manualVideoCheck(self):
        return False

    # ──────────────────────────────────────────────
    # 列表项构造
    # ──────────────────────────────────────────────
    def _items(self, arr, clicked=False):
        res = []
        for k in (arr or []):
            cover = k.get('coverImg') or []
            pic = (cover[0] if isinstance(cover, list) and cover
                   else cover if isinstance(cover, str) else '')
            vid = str(k.get('videoId', ''))
            uid = str(k.get('userId', ''))
            nick = str(k.get('nickName', ''))
            if not vid:
                continue
            vod_id = '%s?%s?%s%s' % (vid, uid, quote(nick), 'click' if clicked else '')
            res.append({
                'vod_id': vod_id,
                'vod_name': k.get('title') or nick or vid,
                'vod_pic': self._proxy(pic, 'img'),
                'vod_remarks': self._time(k.get('playTime')),
                'style': {'type': 'rect', 'ratio': 1.33},
            })
        return res

    # ──────────────────────────────────────────────
    # API 调用 + AES 解密
    # ──────────────────────────────────────────────
    def _api(self, path, post=None):
        url = self.host + path if path.startswith('/') else path
        if post is not None:
            key = 'POST:' + url + json.dumps(post, sort_keys=True, ensure_ascii=False)
        else:
            key = 'GET:' + url
        if key in self.api_cache:
            return self.api_cache[key]
        try:
            if post is not None:
                r = self.session.post(url, json=post, headers=self._headers(),
                                      timeout=12, verify=False)
            else:
                r = self.session.get(url, headers=self._headers(),
                                     timeout=12, verify=False)
            j = r.json()
            data = self._aes(j.get('encData', '')) if j.get('encData') else j
            if len(self.api_cache) > 80:
                self.api_cache.clear()
            self.api_cache[key] = data
            return data
        except Exception:
            return {}

    # ──────────────────────────────────────────────
    # 并发域名探测
    # ──────────────────────────────────────────────
    def _candidate_url(self, hs_entry):
        """hs_entry: 'wcyfhknomg' → https://xxxxxx.wcyfhknomg.work"""
        sub = ''.join(random.choices(string.ascii_lowercase + string.digits,
                                     k=random.randint(5, 10)))
        return 'https://%s.%s.work' % (sub, hs_entry)

    def _all_candidate_urls(self):
        """生成全部候选 URL：defaultHosts + 5 个顶级域 × SUB_PER_TOP 随机子域"""
        cands = []
        # 1) 用户/默认注入的 host
        try:
            injected = (getattr(self, '_vbox_effective_hosts', None)
                        or globals().get('_vbox_effective_hosts')) or []
            for h in injected:
                u = str(h).strip().rstrip('/')
                if u.startswith(('http://', 'https://')):
                    cands.append(u)
        except Exception:
            pass
        # 2) 当前 host 兜底
        if self.host and self.host not in cands:
            cands.append(self.host.rstrip('/'))
        # 3) 5 个顶级域 × 多个子域
        for hs in self.HS:
            for _ in range(self.SUB_PER_TOP):
                cands.append(self._candidate_url(hs))
        return cands

    def _probe(self, url):
        """单条探测：发 traveler 接口，能拿到 token 即视为可用"""
        try:
            sign, t = self._sign()
            hd = {
                'User-Agent': self.UA,
                'Accept': 'application/json',
                'deviceid': self.did,
                't': t,
                's': sign,
            }
            body = {
                'deviceId': self.did,
                'tt': 'U',
                'code': '##X-4m6Goo4zzPi1hF##',
                'chCode': 'tt09',
            }
            r = self.session.post(url + '/api/user/traveler', json=body,
                                   headers=hd, timeout=self.PROBE_TIMEOUT, verify=False)
            j = r.json()
            d = (j or {}).get('data') or {}
            tok = d.get('token')
            img = d.get('imgDomain')
            if tok and img:
                return (url, tok, img)
        except Exception:
            pass
        return None

    def _token(self):
        """并发探测所有候选，第一个成功的就锁定"""
        cands = self._all_candidate_urls()
        if not cands:
            return '', '', self.host

        with ThreadPoolExecutor(max_workers=len(cands)) as pool:
            futures = {pool.submit(self._probe, u): u for u in cands}
            try:
                for fut in as_completed(futures, timeout=self.PROBE_DEADLINE):
                    res = fut.result()
                    if res:
                        url, tok, img = res
                        # 取消其他还在跑的任务
                        for f in futures:
                            f.cancel()
                        return tok, img, url
            except Exception:
                pass
        return '', '', self.host

    # ──────────────────────────────────────────────
    # 签名 / 头
    # ──────────────────────────────────────────────
    def _headers(self):
        sign, t = self._sign()
        h = {'User-Agent': self.UA, 'deviceid': self.did, 't': t, 's': sign}
        if self.token:
            h['aut'] = self.token
        return h

    def _sign(self):
        t = str(int(time.time() * 1000))
        return self._md5(t), t

    def _aes(self, word):
        try:
            key = b64decode(self.AES_KEY_B64)
            return json.loads(unpad(AES.new(key, AES.MODE_CBC, key).decrypt(b64decode(word)),
                                    AES.block_size).decode('utf-8'))
        except Exception:
            return {}

    def _did(self):
        did = self.getCache('did')
        if not did:
            did = self._md5(str(int(time.time())))
            self.setCache('did', did)
        return did

    def _md5(self, text):
        return hashlib.md5(str(text).encode('utf-8')).hexdigest()

    def _time(self, seconds):
        try:
            s = int(seconds or 0)
            h = s // 3600
            m = s % 3600 // 60
            sec = s % 60
            return '%02d:%02d:%02d' % (h, m, sec) if h else '%02d:%02d' % (m, sec)
        except Exception:
            return ''

    # ──────────────────────────────────────────────
    # 代理 URL（封面图走 localProxy）
    # ──────────────────────────────────────────────
    def _proxy(self, u, tp='img'):
        if not u:
            return ''
        try:
            return self.getProxyUrl() + '&type=%s&url=%s' % (tp, quote(u, safe=''))
        except Exception:
            return self._img_url(u)

    def _img_url(self, u):
        if not u:
            return ''
        if u.startswith('http'):
            return u
        return (self.phost or '') + u

    def _img_asset(self, u):
        if u in self.img_cache:
            return self.img_cache[u]
        try:
            r = self.session.get(self._img_url(u),
                                 headers={'User-Agent': self.UA},
                                 timeout=15, verify=False)
            body = self._img_decode(r.content, 100, self.IMG_XOR_KEY)
            ct = r.headers.get('Content-Type', 'image/jpeg')
            if len(self.img_cache) > 160:
                self.img_cache.clear()
            self.img_cache[u] = (ct, body)
            return ct, body
        except Exception:
            return 'text/plain', b''

    def _img_decode(self, data, length, key):
        if len(data) > 7 and (data[:3] == b'GIF' or data[:3] == b'\xff\xd8\xff'
                              or data[1:8] == b'PNG\r\n\x1a\n'):
            return data
        kb = key.encode('utf-8')
        arr = bytearray(data)
        for i in range(min(length, len(arr))):
            arr[i] ^= kb[i % len(kb)]
        return bytes(arr)
