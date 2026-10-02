# -*- coding: utf-8 -*-
"""
TVBox影视壳插件 - 三年高考五年模拟 - vbox 远程源适配版
适配自 lold.py 全自动点播抓取
适配: 继承 SpiderBase + super().init(extend) + localProxy三元组
     + 多域名并发竞速(首个 /api/setapp.php 200 的域名缓存10分钟)
     + 搜索并发化(52分类并发抓取)
"""
import sys
sys.path.append('..')
import json
import gzip
import random
import time
import re
import ssl
import threading
import urllib.request
import urllib.parse
import os
from concurrent.futures import ThreadPoolExecutor

try:
    from base.spider import Spider as SpiderBase
except ImportError:
    class SpiderBase(object):
        def __init__(self):
            self._vbox_effective_hosts = []
        def getCache(self, key): return None
        def setCache(self, key, value): return "fail"
        def delCache(self, key): return "fail"


_SSL_CTX = ssl.create_default_context()
_SSL_CTX.check_hostname = False
_SSL_CTX.verify_mode = ssl.CERT_NONE


class Spider(SpiderBase):

    PLATFORM_KEY = "gaokao_py"

    # ========== 配置 ==========
    DOMAIN_API = "https://lwncnss3api.cc/api/getapi.php"
    CACHE_FILE = "domain_cache_3n.json"
    CACHE_EXPIRE = 3600  # 域名池缓存有效期1小时

    # 硬编码备用域名
    BACKUP_DOMAINS = [
        "dag29jmgma1g.site",
        "ldngksapi.cc",
        "lagh23ksapi.cc",
        "ldagwhdgpi.cc",
        "lwetasdf3api.cc",
        "lwasga289api.cc",
        "lw2wthchhaapi.cc",
        "lwncnss3api.cc",
        "lw23412gaapi.cc"
    ]

    DOMAIN_TTL = 600  # 竞速胜者域名缓存10分钟

    TIMEOUT = 15
    DETAIL_RETRY = 3
    REG_GAP = 1.2
    REG_TRY = 5

    # 分类列表（从原代码迁移）
    VOD_CLASSES = [
        '重口猎奇', '迷奸强奸', '校园霸凌', '真实乱伦', '监控偷拍',
        '学生破处', '淫荡孕妇', '萝莉', "小学", "初中",
        "高中", "小马", "人妖伪娘", '户外露出', '绿帽抓奸',
        '反差母犬', '少女媚黑', '暗网萝莉', '少女萝莉', '学生',
        '自慰', 'JK', '母子通奸', '父女禁恋', '兄妹相爱',
        '姐弟情深', '舅侄畸恋', '全家乱P', '师生淫乱', '偷窥偷拍',
        '裸聊实录', '主播大秀', '原创自拍', '车震野战', 'SM捆绑',
        '探花大神', '勾引搭讪', '最新热点', '独家精选', '学生校园',
        '网红网暴', '热门大瓜', '明星黑幕', '反差母狗', '领导干部',
        '百合', '足交', '丝袜', '内射', 'Cospaly',
        '换妻Club', '偷窥萝莉'
    ]

    # 设备伪装列表
    DEVICES = [
        ("ONEPLUS A5000", "OPR6.170623.013"),
        ("Pixel 4", "QQ3A.200805.001"),
        ("SM-G973F", "QP1A.190711.020"),
        ("Mi 9", "PKQ1.181121.001"),
        ("Redmi Note 8", "QKQ1.200114.002"),
    ]

    def __init__(self):
        try:
            super(Spider, self).__init__()
        except Exception:
            pass
        self.token = None
        self.last_reg = 0.0
        self._reg_dead = False
        self.cache = {}
        self.domains = []
        self._base_winner = None
        self._base_winner_ts = 0.0
        self._race_lock = threading.Lock()
        self._load_domains()
        if len(self.domains) < 3:
            self.domains.extend(self.BACKUP_DOMAINS)
            self.domains = list(set(self.domains))

    def getName(self):
        return "三年高考五年模拟"

    def init(self, extend=""):
        try:
            super().init(extend)
        except AttributeError:
            pass
        # vbox 注入域名池合并 (裸域名, 优先于缓存/API 域名池)
        from urllib.parse import urlparse
        injected = getattr(self, "_vbox_effective_hosts", None) or []
        inj = []
        for h in injected:
            h = str(h)
            if h.startswith("http"):
                host = urlparse(h).netloc
                if host:
                    inj.append(host)
        inj = list(dict.fromkeys(inj))
        if inj:
            self.domains = inj + [d for d in self.domains if d not in inj]

    def isVideoFormat(self, url):
        low = (url or "").lower()
        return any(k in low for k in (".m3u8", ".mp4", ".ts"))

    def manualVideoCheck(self):
        return False

    def destroy(self):
        pass

    # ========== 域名池管理 ==========
    def _get_cache_path(self):
        return os.path.join(os.path.dirname(os.path.abspath(__file__)), self.CACHE_FILE)

    def _load_domains(self):
        cache_path = self._get_cache_path()
        if os.path.exists(cache_path):
            try:
                with open(cache_path, 'r', encoding='utf-8') as f:
                    cache_data = json.load(f)
                cache_time = cache_data.get('cache_time', 0)
                if time.time() - cache_time < self.CACHE_EXPIRE:
                    domains = cache_data.get('domains', [])
                    self.domains = [d for d in domains if d and isinstance(d, str) and '.' in d]
                    if self.domains:
                        return
            except Exception:
                pass
        self._fetch_domains()

    def _fetch_domains(self):
        """从API获取域名列表并缓存 (不写文件失败不影响运行)"""
        try:
            r = self._http_get(self.DOMAIN_API, timeout=10)
            text = r[0]
            if text is None:
                self.domains = self.BACKUP_DOMAINS.copy()
                return
            try:
                data = json.loads(text)
            except Exception:
                domains = re.findall(r'[\w\-\.]+\.(?:com|cc|net|org|site|top|xyz)', text)
                if domains:
                    self.domains = list(set(domains))
                    self._save_cache(self.domains)
                else:
                    self.domains = self.BACKUP_DOMAINS.copy()
                return

            if data.get('code') == 200:
                domains = data.get('data', [])
                blacklist = data.get('blackdomain', [])

                if isinstance(domains, str):
                    try:
                        domains = json.loads(domains)
                    except Exception:
                        domains = [domains]

                if not isinstance(domains, list):
                    domains = [str(domains)] if domains else []

                all_domains = list(set(domains + blacklist))
                self.domains = [d for d in all_domains if d and isinstance(d, str) and '.' in d]

                priority_domains = [d for d in domains if d and '.' in d]
                other_domains = [d for d in self.domains if d not in priority_domains]
                self.domains = priority_domains + other_domains

                if self.domains:
                    self._save_cache(all_domains)
                else:
                    self.domains = self.BACKUP_DOMAINS.copy()
            else:
                self.domains = self.BACKUP_DOMAINS.copy()
        except Exception:
            self.domains = self.BACKUP_DOMAINS.copy()

    def _save_cache(self, domains):
        try:
            cache_data = {
                'domains': domains,
                'cache_time': time.time()
            }
            cache_path = self._get_cache_path()
            with open(cache_path, 'w', encoding='utf-8') as f:
                json.dump(cache_data, f, ensure_ascii=False, indent=2)
        except Exception:
            pass

    # ========== HTTP 工具 (stdlib urllib) ==========
    def _maybe_decompress(self, raw):
        """响应体可能是 gzip(请求头含 Accept-Encoding: gzip), 检测魔数解压"""
        if raw is None:
            return b''
        if raw[:2] == b'\x1f\x8b':
            try:
                return gzip.decompress(raw)
            except Exception:
                return raw
        return raw

    def _http_get(self, url, timeout=15, data=None, headers=None):
        """GET/POST 请求, 返回 (text, status_code)"""
        hdrs = self._headers()
        if headers:
            hdrs.update(headers)
        try:
            body = None
            if data is not None:
                if isinstance(data, dict):
                    body = urllib.parse.urlencode(data).encode('utf-8')
                elif isinstance(data, str):
                    body = data.encode('utf-8')
                else:
                    body = data
            req = urllib.request.Request(url, data=body, headers=hdrs)
            with urllib.request.urlopen(req, timeout=timeout, context=_SSL_CTX) as resp:
                return self._maybe_decompress(resp.read()).decode('utf-8', 'ignore'), resp.getcode()
        except urllib.error.HTTPError as e:
            try:
                return self._maybe_decompress(e.read()).decode('utf-8', 'ignore'), e.code
            except Exception:
                return None, e.code
        except Exception:
            return None, -1

    def _post_form(self, url, data, timeout=15):
        hdrs = self._headers()
        hdrs["Content-Type"] = "application/x-www-form-urlencoded"
        try:
            body = urllib.parse.urlencode(data).encode('utf-8') if isinstance(data, dict) else data.encode('utf-8')
            req = urllib.request.Request(url, data=body, headers=hdrs)
            with urllib.request.urlopen(req, timeout=timeout, context=_SSL_CTX) as resp:
                return self._maybe_decompress(resp.read()).decode('utf-8', 'ignore'), resp.getcode()
        except urllib.error.HTTPError as e:
            try:
                return self._maybe_decompress(e.read()).decode('utf-8', 'ignore'), e.code
            except Exception:
                return None, e.code
        except Exception:
            return None, -1

    def _parse_json(self, text):
        if not text:
            return None
        t = str(text).strip()
        if not t:
            return None
        try:
            return json.loads(t)
        except Exception:
            return None

    # ========== 多域名并发竞速 ==========
    def _probe_base(self, base_url):
        """探测 base_url 是否可用: GET /api/setapp.php 200"""
        try:
            text, code = self._http_get(base_url + "/api/setapp.php", timeout=5, data="")
            return code == 200
        except Exception:
            return False

    def _race_bases(self):
        """多域名并发竞速: 首个 200 的域名胜出, 缓存 10 分钟"""
        now = time.time()
        if self._base_winner and (now - self._base_winner_ts) < self.DOMAIN_TTL:
            return self._base_winner
        if not self.domains:
            self._load_domains()
        if not self.domains:
            return "https://dag29jmgma1g.site"

        targets = []
        for d in self.domains:
            for proto in ('https', 'http'):
                targets.append("%s://%s" % (proto, d))

        def _try(url):
            if self._probe_base(url):
                with self._race_lock:
                    if self._base_winner is None:
                        self._base_winner = url
                        self._base_winner_ts = time.time()

        threads = [threading.Thread(target=_try, args=(u,), daemon=True) for u in targets]
        for t in threads:
            t.start()
        deadline = time.time() + 8
        while time.time() < deadline:
            with self._race_lock:
                if self._base_winner is not None:
                    break
            time.sleep(0.15)

        return self._base_winner or ("https://" + self.domains[0])

    def _invalidate_winner(self):
        self._base_winner = None
        self._base_winner_ts = 0.0

    def _request_api(self, path, method='post', data=None, _retried=False):
        """通用API请求, 域名失效时重新竞速一次"""
        base_url = self._race_bases()
        url = base_url + path
        text, code = self._post_form(url, data or "", timeout=self.TIMEOUT)
        if code not in (200, 0) or text is None:
            if not _retried:
                self._invalidate_winner()
                return self._request_api(path, method, data, _retried=True)
            return None
        return text

    # ========== 工具方法 ==========
    def _ua(self):
        m, b = random.choice(self.DEVICES)
        a = random.choice(["8.0.0", "9", "10", "11", "12"])
        c = random.randint(120, 138)
        return (
            f"Mozilla/5.0 (Linux; Android {a}; {m} Build/{b}; wv) "
            f"AppleWebKit/537.36 (KHTML, like Gecko) Version/4.0 "
            f"Chrome/{c}.0.{random.randint(0,7204)}.{random.randint(100,200)} "
            f"Mobile Safari/537.36 uni-app Html5Plus/1.0 (Immersed/24.0)"
        )

    def _headers(self):
        return {
            "User-Agent": self._ua(),
            "Content-Type": "application/x-www-form-urlencoded",
            "Connection": "Keep-Alive",
            "Accept-Encoding": "gzip",
        }

    def _find_first(self, obj, key):
        if isinstance(obj, dict):
            if key in obj and obj[key] not in (None, ""):
                return str(obj[key])
            for v in obj.values():
                r = self._find_first(v, key)
                if r is not None:
                    return r
        elif isinstance(obj, list):
            for x in obj:
                r = self._find_first(x, key)
                if r is not None:
                    return r
        return None

    def _find_all(self, obj, key, out=None):
        if out is None:
            out = []
        if isinstance(obj, dict):
            if key in obj and obj[key] not in (None, ""):
                out.append(str(obj[key]))
            for v in obj.values():
                self._find_all(v, key, out)
        elif isinstance(obj, list):
            for x in obj:
                self._find_all(x, key, out)
        return out

    def _fix_pic(self, pic):
        if not pic:
            return ""
        if pic.startswith("//"):
            pic = "https:" + pic
        elif pic.startswith("/") and not pic.startswith("//"):
            pic = self._race_bases() + pic
        return self._proxy_img_url(pic, referer=self._race_bases() + "/")

    # ========== 本地代理 ==========
    def _proxy_base(self):
        fn = getattr(self, "getProxyUrl", None)
        if callable(fn):
            try:
                u = fn(True)
                if u:
                    return str(u)
            except Exception:
                pass
        return "http://127.0.0.1:18080/proxy?do=py&key=%s" % self.PLATFORM_KEY

    def _proxy_img_url(self, url, referer=None):
        if not url:
            return ""
        base = self._proxy_base()
        sep = "&" if "?" in base else "?"
        u = base + sep + "type=img&u=" + urllib.parse.quote(str(url), safe="")
        if referer:
            u += "&r=" + urllib.parse.quote(referer, safe="")
        return u

    def _serve_img(self, url, referer=None):
        try:
            headers = {"User-Agent": self._ua()}
            if referer:
                headers["Referer"] = referer
            req = urllib.request.Request(url, headers=headers)
            with urllib.request.urlopen(req, timeout=15, context=_SSL_CTX) as resp:
                raw = resp.read()
                ct = (resp.headers.get("Content-Type") or "image/jpeg").split(";")[0].strip()
            if raw[:4] == b"\x89PNG":
                ct = "image/png"
            elif raw[:3] == b"GIF":
                ct = "image/gif"
            elif raw[:2] == b"\xff\xd8":
                ct = "image/jpeg"
            elif raw[:4] == b"RIFF":
                ct = "image/webp"
            return [200, ct, raw]
        except Exception:
            return [502, "text/plain", b"proxy fetch failed"]

    # ========== 内容提取 ==========
    def _collect_items(self, obj, out=None):
        if out is None:
            out = []
        if isinstance(obj, dict):
            if "vod_id" in obj and obj["vod_id"] not in (None, ""):
                pic = self._find_first(obj, "vod_pic") or ""
                if not pic:
                    pic = self._find_first(obj, "vod_img") or ""
                if not pic:
                    pic = self._find_first(obj, "pic") or ""
                if not pic:
                    pic = self._find_first(obj, "cover") or ""
                if not pic:
                    pic = self._find_first(obj, "image") or ""

                item_pic = ""
                if pic:
                    item_pic = self._fix_pic(pic)

                out.append({
                    "vod_id": str(obj["vod_id"]),
                    "vod_name": str(obj.get("vod_name") or obj.get("name") or ""),
                    "vod_pic": item_pic,
                    "vod_remarks": str(obj.get("vod_remarks") or obj.get("remarks") or obj.get("status") or "")
                })
            else:
                for v in obj.values():
                    self._collect_items(v, out)
        elif isinstance(obj, list):
            for x in obj:
                self._collect_items(x, out)
        return out

    def _collect_detail(self, obj):
        result = {
            "vod_id": "",
            "vod_name": "",
            "vod_pic": "",
            "vod_content": "",
            "vod_play_url": "",
            "vod_actor": "",
            "vod_director": "",
            "type_name": "",
        }

        result["vod_id"] = self._find_first(obj, "vod_id") or ""
        result["vod_name"] = self._find_first(obj, "vod_name") or self._find_first(obj, "name") or ""

        pic = self._find_first(obj, "vod_pic") or ""
        if not pic:
            pic = self._find_first(obj, "vod_img") or ""
        if not pic:
            pic = self._find_first(obj, "pic") or ""
        if not pic:
            pic = self._find_first(obj, "cover") or ""
        if not pic:
            pic = self._find_first(obj, "image") or ""
        if not pic:
            pic = self._find_first(obj, "poster") or ""

        result["vod_pic"] = self._fix_pic(pic)

        result["vod_content"] = self._find_first(obj, "vod_content") or self._find_first(obj, "description") or self._find_first(obj, "desc") or ""
        result["vod_actor"] = self._find_first(obj, "vod_actor") or self._find_first(obj, "actor") or ""
        result["vod_director"] = self._find_first(obj, "vod_director") or self._find_first(obj, "director") or ""
        result["type_name"] = self._find_first(obj, "type_name") or self._find_first(obj, "type") or self._find_first(obj, "vod_class") or ""

        raw_urls = self._find_all(obj, "vod_play_url")
        play_urls = []
        for raw in raw_urls:
            play_urls.extend(self._extract_play_urls(raw))
        play_urls = list(dict.fromkeys(play_urls))
        result["vod_play_url"] = "#".join([f"第{i+1}集${url}" for i, url in enumerate(play_urls)])

        return result

    def _rate_limited(self, body):
        if not isinstance(body, dict):
            return False
        msg = str(body.get("msg", ""))
        return "频繁" in msg or "太快" in msg or "频率" in msg

    def _extract_play_urls(self, raw):
        if not raw:
            return []
        s = str(raw).strip()
        if not s or s.lower() in ("null", "none", "undefined"):
            return []
        parts = [p for p in s.split("#") if p.strip()]
        out = []
        for part in parts:
            part = part.strip()
            if "$" in part:
                part = part.split("$")[-1].strip()
            if self._ok_url(part) and part not in out:
                out.append(part)
        return out

    def _ok_url(self, u):
        if not u:
            return False
        s = u.strip()
        if not s or s.lower() in ("null", "none", "undefined"):
            return False
        if "$" in s:
            s = s.split("$")[-1].strip()
        return s.startswith(("http://", "https://", "magnet:")) or "http://" in s or "https://" in s

    # ========== Token 管理 ==========
    def _newreg_once(self):
        try:
            text, code = self._post_form(self._race_bases() + '/api/newreg.php',
                "device=android&ntoken=&channel_code=vbtQg9D8")
        except Exception:
            return None, False

        body = self._parse_json(text)
        if body is None:
            return None, False

        # 注册渠道已关闭 (403 该渠道暂停注册 等) -> 标记死, 后续不再重试
        if isinstance(body, dict):
            bcode = str(body.get("code", ""))
            bmsg = str(body.get("msg", ""))
            if bcode == "403" or ("暂停" in bmsg) or ("禁止" in bmsg) or ("关闭" in bmsg):
                self._reg_dead = True
                return None, True

        if self._rate_limited(body):
            return None, True

        t = None
        if isinstance(body, dict):
            u = body.get("user")
            if isinstance(u, dict) and u.get("token"):
                t = str(u["token"])
        if not t:
            t = self._find_first(body, "token")
        return t, False

    def _refresh_token(self):
        if self._reg_dead:
            return ""
        for i in range(self.REG_TRY):
            gap = self.REG_GAP - (time.time() - self.last_reg)
            if gap > 0:
                time.sleep(gap)
            t, limited = self._newreg_once()
            if t:
                self.token = t
                self.last_reg = time.time()
                return t
            if self._reg_dead:
                return ""
            if limited:
                wait = min(30.0, 2.0 * (2**i) + random.uniform(0.2, 1.0))
                time.sleep(wait)
            else:
                time.sleep(self.REG_GAP)
        return None

    def _get_token(self, force=False):
        if force or not self.token:
            return self._refresh_token()
        return self.token

    # ========== API 调用 ==========
    def _api_vlist(self, vodclass, num):
        data = {
            "num": str(num),
            "pid": "4",
            "area": "全部",
            "vodclass": vodclass,
            "vodyear": "全部",
            "sort": "1",
            "type": "undefined",
        }
        return self._request_api('/api/vlist.php', 'post', data=data)

    def _api_detail(self, vod_id, tok):
        data = f"id={vod_id}&token={tok}&channel="
        return self._request_api('/api/Get_vod_list.php', 'post', data=data)

    # ========== 核心方法 ==========
    def homeContent(self, filter):
        cats = []
        for cls in self.VOD_CLASSES:
            cats.append({"type_name": cls, "type_id": cls})
        if not cats:
            cats = [{"type_name": "三年高考·全部", "type_id": "最新热点"}]
        return {"class": cats, "filters": {}}

    def homeVideoContent(self):
        if self.VOD_CLASSES:
            return self.categoryContent(self.VOD_CLASSES[0], "1", None, {})
        return {"list": []}

    def categoryContent(self, tid, pg, filter, extend):
        try:
            tok = self._get_token() or ""

            page_num = int(pg) if str(pg).isdigit() else 1
            offset = (page_num - 1) * 30

            text = self._api_vlist(tid, offset)
            body = self._parse_json(text)
            if body is None:
                return {"list": []}

            items = self._collect_items(body)

            vlist = []
            for item in items:
                vlist.append({
                    "vod_id": item["vod_id"],
                    "vod_name": item["vod_name"],
                    "vod_pic": item.get("vod_pic", ""),
                    "vod_remarks": item.get("vod_remarks", "")
                })

            return {
                "list": vlist,
                "page": page_num,
                "pagecount": 999,
                "limit": 30,
                "total": 99999
            }
        except Exception:
            return {"list": []}

    def detailContent(self, ids):
        vid = ids[0]

        cache_key = f"detail_{vid}"
        if cache_key in self.cache:
            return {"list": [self.cache[cache_key]]}

        try:
            tok = self._get_token() or ""

            text = self._api_detail(vid, tok)
            body = self._parse_json(text)
            if body is None:
                return {"list": []}

            detail = self._collect_detail(body)

            result = {
                "vod_id": vid,
                "vod_name": detail["vod_name"] or "未知",
                "vod_pic": detail["vod_pic"],
                "type_name": detail["type_name"] or "课程",
                "vod_content": detail["vod_content"],
                "vod_actor": detail["vod_actor"],
                "vod_director": detail["vod_director"],
                "vod_play_from": "三年高考",
                "vod_play_url": detail["vod_play_url"]
            }

            self.cache[cache_key] = result

            return {"list": [result]}
        except Exception:
            return {"list": []}

    def searchContent(self, key, quick, pg="1"):
        """搜索: 52分类并发抓取 (限12并发, 首个 30 条即返回)"""
        tok = None
        results = []
        seen = set()

        def _search_class(cls):
            try:
                t = self._get_token() or ""
                text = self._api_vlist(cls, 0)
                body = self._parse_json(text)
                if body is None:
                    return []
                items = self._collect_items(body)
                return [it for it in items if str(key).lower() in it["vod_name"].lower()]
            except Exception:
                return []

        with ThreadPoolExecutor(max_workers=12) as pool:
            futures = [pool.submit(_search_class, cls) for cls in self.VOD_CLASSES]
            for fut in futures:
                for item in fut.result():
                    k = item["vod_id"]
                    if k in seen:
                        continue
                    seen.add(k)
                    results.append({
                        "vod_id": item["vod_id"],
                        "vod_name": item["vod_name"],
                        "vod_pic": item.get("vod_pic", ""),
                        "vod_remarks": item.get("vod_remarks", "")
                    })
                    if len(results) >= 30:
                        break
                if len(results) >= 30:
                    break

        return {"list": results[:30]}

    def playerContent(self, flag, id, vipFlags):
        if id.startswith(("http://", "https://")):
            return {
                "parse": 0,
                "playUrl": "",
                "url": id,
                "header": {
                    "User-Agent": self._ua(),
                    "Referer": self._race_bases()
                }
            }

        try:
            detail = self.detailContent([id])
            if detail.get("list"):
                play_url = detail["list"][0].get("vod_play_url", "")
                if play_url:
                    parts = play_url.split("#")
                    if parts:
                        first = parts[0]
                        if "$" in first:
                            url = first.split("$")[-1]
                        else:
                            url = first
                        if url.startswith(("http://", "https://")):
                            return {
                                "parse": 0,
                                "playUrl": "",
                                "url": url,
                                "header": {
                                    "User-Agent": self._ua(),
                                    "Referer": self._race_bases()
                                }
                            }
        except Exception:
            pass

        return {
            "parse": 0,
            "playUrl": "",
            "url": "",
            "header": {}
        }

    def localProxy(self, param):
        p = {}
        if isinstance(param, dict):
            p = param
        elif isinstance(param, str):
            s = param.strip()
            if s.startswith("{"):
                try:
                    p = json.loads(s)
                except Exception:
                    p = {}
            elif "=" in s:
                try:
                    qs = urllib.parse.parse_qs(s.lstrip("?"))
                    p = {k: v[0] for k, v in qs.items()}
                except Exception:
                    p = {}
        t = str(p.get("type") or "")
        u = urllib.parse.unquote(str(p.get("u") or p.get("url") or ""))
        r = urllib.parse.unquote(str(p.get("r") or "")) or None
        if t == "img" and u:
            return self._serve_img(u, referer=r)
        return [404, "text/plain", b""]
