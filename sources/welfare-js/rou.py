# -*- coding: utf-8 -*-
"""
肉视频 - vbox 远程源适配版
站点: rou.video 等多主机 (TSR blob + DOM 双解析, ev XOR 解密, PNG 封装 m3u8/mp4)
适配: 继承 SpiderBase + super().init(extend) + localProxy三元组
     + 多主机并发竞速(首个响应的主机缓存10分钟) + 封面走本地代理
"""
import base64
import html as htmlmod
import json
import re
import struct
import threading
import time
import urllib.request
import urllib.parse
import urllib.error
import ssl
import zlib
from urllib.parse import quote, unquote

sys_path_hack = None
try:
    import sys
    sys.path.append('..')
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
    PLATFORM_KEY = "rou_py"
    HOSTS = [
        "https://rou.video",
        "https://rouvb1.xyz",
        "https://rouva8.xyz",
        "https://rou-video.zproxy.org",
    ]
    PUB_PAGE_URL = "https://rdz3.xyz/dizhi"
    HOST_TTL = 600  # 竞速胜者主机缓存 10 分钟

    def __init__(self):
        try:
            super(Spider, self).__init__()
        except Exception:
            pass
        self._current_host_idx = 0
        self._fetched_pub_hosts = False
        self.host = self.HOSTS[0]
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Referer": self.HOSTS[0] + "/",
            "Accept-Language": "zh-CN,zh;q=0.9",
        }
        self._timeout = 20
        # 主机竞速缓存
        self._host_winner = None
        self._host_winner_ts = 0.0
        self._host_lock = threading.Lock()

    def getDependence(self):
        return []

    def getName(self):
        return "肉视频"

    def _ext_cfg(self, extend):
        cfg = {}
        if isinstance(extend, dict):
            cfg = dict(extend)
        elif isinstance(extend, str):
            text = extend.strip()
            if text.startswith("{"):
                try:
                    parsed = json.loads(text)
                    if isinstance(parsed, dict):
                        cfg = parsed
                except Exception:
                    cfg = {}
            elif text.startswith("http"):
                cfg = {"site": text}
            elif text:
                cfg = {"site": text}
        return cfg

    def init(self, extend=""):
        try:
            super().init(extend)
        except AttributeError:
            pass
        # vbox 注入主机池合并 (优先竞速候选)
        injected = getattr(self, "_vbox_effective_hosts", None) or []
        inj = [str(h).rstrip("/") for h in injected if str(h).startswith("http")]
        if inj:
            self.HOSTS = inj + [h for h in self.HOSTS if h not in inj]
            self._current_host_idx = 0
        cfg = self._ext_cfg(extend)
        site = str(cfg.get("site", "") or "").strip().rstrip("/")
        if site.startswith("http"):
            self._set_host(site)
        hosts = cfg.get("hosts", "")
        if isinstance(hosts, str) and hosts.strip():
            for h in re.split(r"[,\s;|]+", hosts.strip()):
                h = h.strip().rstrip("/")
                if h.startswith("http") and h not in self.HOSTS:
                    self.HOSTS.append(h)
        elif isinstance(hosts, list):
            for h in hosts:
                h = str(h or "").strip().rstrip("/")
                if h.startswith("http") and h not in self.HOSTS:
                    self.HOSTS.append(h)
        ua = str(cfg.get("ua", "") or "").strip()
        if ua:
            self.headers["User-Agent"] = ua
        timeout = cfg.get("timeout", "")
        try:
            timeout = int(timeout) if str(timeout).strip() else 20
        except Exception:
            timeout = 20
        if timeout < 5:
            timeout = 5
        if timeout > 60:
            timeout = 60
        self._timeout = timeout
        pub = str(cfg.get("pub", "") or "").strip().rstrip("/")
        if pub.startswith("http"):
            self.PUB_PAGE_URL = pub

    def _set_host(self, host):
        host = (host or "").rstrip("/")
        if not host:
            return
        if host not in self.HOSTS:
            self.HOSTS.append(host)
            self._current_host_idx = len(self.HOSTS) - 1
        else:
            self._current_host_idx = self.HOSTS.index(host)
        self.host = self.HOSTS[self._current_host_idx]
        self.headers["Referer"] = self.host + "/"

    @property
    def HOST(self):
        if self._host_winner:
            return self._host_winner
        return self.HOSTS[self._current_host_idx]

    def _timeout_value(self):
        return getattr(self, "_timeout", 20)

    def _clean(self, text):
        if not text:
            return ""
        return htmlmod.unescape(re.sub(r"<[^>]+>", "", str(text))).strip()

    def _fix(self, u):
        if not u:
            return ""
        u = u.strip()
        if u.startswith("//"):
            return "https:" + u
        if u.startswith("/"):
            return self.HOST + u
        return u

    def _http_get(self, url, headers=None, timeout=None):
        """GET 返回 (text, content, status_code)"""
        hdrs = dict(headers or self.headers)
        timeout = timeout or self._timeout_value()
        try:
            req = urllib.request.Request(url, headers=hdrs)
            with urllib.request.urlopen(req, timeout=timeout, context=_SSL_CTX) as resp:
                raw = resp.read()
                code = resp.getcode()
                try:
                    text = raw.decode("utf-8")
                except Exception:
                    text = raw.decode("gbk", "ignore")
                return text, raw, code
        except urllib.error.HTTPError as e:
            try:
                raw = e.read()
            except Exception:
                raw = b""
            return None, raw, e.code
        except Exception:
            return None, b"", -1

    def _get(self, url, headers=None):
        text, _, code = self._http_get(url, headers=headers)
        if code == 200 and text:
            return text
        return ""

    def _get_bytes(self, url, headers=None):
        _, raw, code = self._http_get(url, headers=headers)
        if code == 200 and raw:
            return raw
        return b""

    # ================= 多主机并发竞速 =================
    def _refresh_hosts_from_pub(self):
        if self._fetched_pub_hosts:
            return
        self._fetched_pub_hosts = True
        try:
            html = self._get(self.PUB_PAGE_URL, headers={
                "User-Agent": self.headers["User-Agent"],
                "Referer": "https://rdz3.xyz/",
            })
            if not html:
                return
            found = []
            for sec in re.split(r"<section", html):
                if ("肉視頻" in sec or "肉视频" in sec) and ("科学地址" in sec or "永久地址" in sec):
                    for m in re.finditer(r'href="(https?://[^"]+)"', sec):
                        href = m.group(1).strip().rstrip("/")
                        if href and href not in found:
                            found.append(href)
                    for m in re.finditer(r'<span class="url">(https?://[^<]+)</span>', sec):
                        href = m.group(1).strip().rstrip("/")
                        if href and href not in found:
                            found.append(href)
            for href in found:
                if href not in self.HOSTS:
                    self.HOSTS.append(href)
        except Exception:
            pass

    def _probe_host(self, host, path):
        """探测单个主机指定路径是否可用 (200)"""
        url = "%s%s" % (host, path)
        headers = dict(self.headers)
        headers["Referer"] = host + "/"
        text, _, code = self._http_get(url, headers=headers, timeout=8)
        return code == 200 and bool(text)

    def _req(self, path):
        """请求页面: 竞速胜者主机直接命中, 失效则全主机并发竞速 (首个响应缓存10分钟)"""
        now = time.time()
        if self._host_winner and (now - self._host_winner_ts) < self.HOST_TTL:
            host = self._host_winner
            headers = dict(self.headers)
            headers["Referer"] = host + "/"
            html = self._get(host + path, headers=headers)
            if html:
                return html
            # 胜者失效, 转全量竞速
            self._host_winner = None

        winner = {"host": None, "html": None}
        lock = threading.Lock()

        def _race(host):
            if winner["host"]:
                return
            url = "%s%s" % (host, path)
            headers = dict(self.headers)
            headers["Referer"] = host + "/"
            text, _, code = self._http_get(url, headers=headers, timeout=10)
            if code == 200 and text:
                with lock:
                    if winner["host"] is None:
                        winner["host"] = host
                        winner["html"] = text

        # 当前主机优先, 其余并发
        current = self.HOSTS[self._current_host_idx] if self._current_host_idx < len(self.HOSTS) else self.HOSTS[0]
        ordered = [current] + [h for h in self.HOSTS if h != current]
        threads = [threading.Thread(target=_race, args=(h,), daemon=True) for h in ordered]
        for t in threads:
            t.start()
        deadline = time.time() + 12
        while time.time() < deadline:
            with lock:
                if winner["host"] is not None:
                    break
            time.sleep(0.2)

        if winner["host"]:
            self._current_host_idx = self.HOSTS.index(winner["host"]) if winner["host"] in self.HOSTS else 0
            self.host = winner["host"]
            self._host_winner = winner["host"]
            self._host_winner_ts = time.time()
            return winner["html"]

        # 全失败: 刷新公开页域名池后二次竞速
        self._refresh_hosts_from_pub()
        for h in self.HOSTS:
            url = "%s%s" % (h, path)
            headers = dict(self.headers)
            headers["Referer"] = h + "/"
            html = self._get(url, headers=headers)
            if html:
                if h in self.HOSTS:
                    self._current_host_idx = self.HOSTS.index(h)
                self.host = h
                self._host_winner = h
                self._host_winner_ts = time.time()
                return html
        return ""

    # ================= ev 解密 / 视频提取 =================
    def _decrypt_ev(self, ev_d, ev_k=35):
        try:
            b = base64.b64decode(ev_d)
            k = int(ev_k)
            raw = bytes([(x - k) % 256 for x in b])
            return json.loads(raw.decode("utf-8", "replace"))
        except Exception:
            return {}

    def _extract_ev(self, html):
        if not html:
            return {}
        m = re.search(r'ev:\$R\[\d+\]=\{d:"([^"]+)",k:(\d+)\}', html)
        if m:
            return self._decrypt_ev(m.group(1), int(m.group(2)))
        m = re.search(r'"ev"\s*:\s*\{"d"\s*:\s*"([^"]+)"\s*,\s*"k"\s*:\s*(\d+)', html)
        if m:
            return self._decrypt_ev(m.group(1), int(m.group(2)))
        return {}

    def _extract_tsr_videos(self, html):
        if not html or "self.$R" not in html:
            return []
        try:
            blob = html[html.find("self.$R"):html.find("self.$R") + 400000]
            vids = []
            for m in re.finditer(r'\{id:"([A-Za-z0-9]+)",vid:(?:"([^"]*)"|null),name:"((?:[^"\\]|\\.)*)"', blob):
                vid = m.group(1)
                name = m.group(3).encode().decode("unicode_escape", "ignore") if "\\u" in m.group(3) else m.group(3)
                name = name.replace('\\"', '"').strip()
                if not vid or not name or len(vid) > 60:
                    continue
                vids.append((vid, name))
            if not vids:
                return []
            covers = {}
            for m in re.finditer(r'id:"([A-Za-z0-9]+)".{0,2500}?coverImageUrl:"([^"]+)"', blob):
                covers[m.group(1)] = m.group(2)
            tags_map = {}
            for m in re.finditer(r'id:"([A-Za-z0-9]+)".{0,1200}?tags:\$R\[\d+\]=\["([^"\]]+)"', blob):
                try:
                    tags_map[m.group(1)] = m.group(2)
                except Exception:
                    pass
            out, seen = [], set()
            for vid, name in vids:
                if vid in seen:
                    continue
                seen.add(vid)
                pic = covers.get(vid, "")
                item = {"vod_id": vid, "vod_name": self._clean(name), "vod_pic": self._proxy_img_url(self._fix(pic), referer=self.HOST + "/") if pic else ""}
                if tags_map.get(vid):
                    item["vod_remarks"] = self._clean(tags_map[vid])
                out.append(item)
            return out
        except Exception:
            return []

    def _parse_dom_list(self, html):
        out, seen = [], set()
        if not html:
            return out
        for m in re.finditer(r'<a[^>]+href="(/v/[^"]+)"[^>]*>(.*?)</a>', html, re.S):
            try:
                href = m.group(1)
                inner = m.group(2)
                vid = href.replace("/v/", "").strip().strip("/")
                if not vid or "/" in vid or vid in seen:
                    continue
                h = re.search(r"<h3[^>]*>(.*?)</h3>", inner, re.S)
                name = self._clean(h.group(1)) if h else ""
                if not name:
                    am = re.search(r'alt="([^"]+)"', inner)
                    name = self._clean(am.group(1)) if am else ""
                if not name:
                    continue
                pics = re.findall(r'src="([^"]+)"', inner)
                pic = ""
                for cand in pics:
                    if cand and "data:image" not in cand:
                        pic = cand
                seen.add(vid)
                item = {"vod_id": vid, "vod_name": name, "vod_pic": self._proxy_img_url(self._fix(pic), referer=self.HOST + "/") if pic else ""}
                rm = re.search(r'<span[^>]*>(720P|1080P|\d+分\d+秒|\d+:\d+)</span>', inner)
                if rm:
                    item["vod_remarks"] = rm.group(1)
                out.append(item)
            except Exception:
                continue
        return out

    def _parse_video_list(self, html, page="1"):
        videos = self._extract_tsr_videos(html)
        if not videos:
            videos = self._parse_dom_list(html)
        try:
            p_num = int(str(page)) if str(page).isdigit() else 1
        except Exception:
            p_num = 1
        return {
            "page": p_num,
            "pagecount": p_num + 1 if len(videos) >= 24 else p_num,
            "limit": len(videos),
            "total": 9999,
            "list": videos
        }

    def _norm_extend(self, extend):
        if isinstance(extend, dict):
            return dict(extend)
        if isinstance(extend, str):
            try:
                return json.loads(extend) if extend.strip().startswith("{") else {}
            except Exception:
                return {}
        return {}

    def _first(self, value, default=""):
        if isinstance(value, list):
            return str(value[0]) if value else default
        return str(value) if value not in (None, "") else default

    def _order_value(self, extend):
        extend = self._norm_extend(extend)
        return self._first(extend.get("order", "createdAt"), "createdAt") or "createdAt"

    def _sub_cate_value(self, extend):
        extend = self._norm_extend(extend)
        return self._first(extend.get("sub_cate", ""), "")

    # ================= 本地代理 =================
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
        u = base + sep + "type=img&u=" + quote(str(url), safe="")
        if referer:
            u += "&r=" + quote(referer, safe="")
        return u

    def _serve_img(self, url, referer=None):
        try:
            headers = dict(self.headers)
            if referer:
                headers["Referer"] = referer
            raw = self._get_bytes(url, headers=headers)
            if not raw:
                return [404, "text/plain", b"not found"]
            ct = "image/jpeg"
            if raw[:4] == b"\x89PNG":
                ct = "image/png"
            elif raw[:3] == b"GIF":
                ct = "image/gif"
            elif raw[:4] == b"RIFF":
                ct = "image/webp"
            return [200, ct, raw]
        except Exception:
            return [502, "text/plain", b"proxy fetch failed"]

    def _png_extract_m3u8(self, data):
        if not data or len(data) < 8:
            return ""
        if list(data[:8]) != [137, 80, 78, 71, 13, 10, 26, 10]:
            try:
                text = data.decode("utf-8", "ignore")
                if "#EXTM3U" in text:
                    return text
            except Exception:
                pass
            return ""
        off = 8
        while off + 8 <= len(data):
            try:
                ln = struct.unpack(">I", data[off:off + 4])[0]
                typ = data[off + 4:off + 8]
                payload = data[off + 8:off + 8 + ln]
            except Exception:
                break
            if typ == b"roUd" and len(payload) > 1:
                try:
                    return zlib.decompress(payload[1:]).decode("utf-8", "ignore")
                except Exception:
                    pass
            off += 8 + ln + 4
            if off > 800000:
                break
        return ""

    def _png_extract_mp4(self, data):
        if not data or len(data) < 8:
            return b""
        if list(data[:8]) != [137, 80, 78, 71, 13, 10, 26, 10]:
            return data if data[:4] == b"\x00\x00\x00 " or b"ftyp" in data[:32] else b""
        off = 8
        while off + 8 <= len(data):
            try:
                ln = struct.unpack(">I", data[off:off + 4])[0]
                typ = data[off + 4:off + 8]
                payload = data[off + 8:off + 8 + ln]
            except Exception:
                break
            if typ == b"roUd" and len(payload) > 1:
                return payload[1:]
            off += 8 + ln + 4
            if off > 2000000:
                break
        return b""

    def _proxy_url(self, vid, target):
        base = self._proxy_base()
        sep = "&" if "?" in base else "?"
        return base + sep + "type=rou_hls&vid=%s&u=%s" % (quote(vid), quote(str(target), safe=""))

    # ================= 标准接口 =================
    def homeContent(self, filter=None):
        classes = [
            {"type_id": "國產AV", "type_name": "國產AV"},
            {"type_id": "麻豆傳媒", "type_name": "麻豆傳媒"},
            {"type_id": "探花", "type_name": "探花"},
            {"type_id": "自拍流出", "type_name": "自拍流出"},
            {"type_id": "OnlyFans", "type_name": "OnlyFans"},
            {"type_id": "日本", "type_name": "日本"},
            {"type_id": "全部视频", "type_name": "全部视频"},
            {"type_id": "视频分类", "type_name": "视频分类"},
        ]
        if not classes:
            classes = [{"type_id": "全部视频", "type_name": "肉视频·全部"}]
        order_filter = {"key": "order", "name": "排序", "value": [
            {"n": "最新发布", "v": "createdAt"},
            {"n": "最多观看", "v": "viewCount"},
            {"n": "最多点赞", "v": "likeCount"},
        ]}
        filters = {}
        for c in classes:
            filters[c["type_id"]] = [order_filter]
        return {"class": classes, "filters": filters}

    def homeVideoContent(self):
        try:
            return self.categoryContent("全部视频", "1", False, {})
        except Exception:
            return {"list": []}

    def categoryContent(self, tid, pg=1, filter=None, extend=None):
        extend = self._norm_extend(extend)
        page = str(pg or "1")
        order = self._order_value(extend)
        tid = str(tid or "").strip()
        if tid.startswith("cat_tag:"):
            real_tag = tid.replace("cat_tag:", "").strip()
            return self._parse_video_list(self._req("/t/%s?order=%s&page=%s" % (quote(real_tag), order, page)), page)
        if tid == "视频分类":
            return self._parse_three_level_categories()
        if tid == "全部视频":
            return self._parse_video_list(self._req("/v?order=%s&page=%s" % (order, page)), page)
        cate_id = self._sub_cate_value(extend) or tid
        return self._parse_video_list(self._req("/t/%s?order=%s&page=%s" % (quote(cate_id), order, page)), page)

    def _parse_three_level_categories(self):
        tag_items, seen = [], set()
        try:
            html = self._req("/cat")
            if html:
                for m in re.finditer(r'href="(/t/[^"]+)"[^>]*>(.*?)</a>', html, re.S):
                    try:
                        href = m.group(1)
                        tag_name = unquote(href.replace("/t/", "").strip())
                        if not tag_name or tag_name in seen or len(tag_name) > 40:
                            continue
                        seen.add(tag_name)
                        tag_items.append({"vod_id": "cat_tag:%s" % tag_name, "vod_name": tag_name, "vod_pic": self.HOST + "/favicon.ico", "vod_remarks": "分类目录", "vod_tag": "folder"})
                    except Exception:
                        continue
        except Exception:
            pass
        return {"page": 1, "pagecount": 1, "limit": len(tag_items), "total": len(tag_items), "list": tag_items}

    def searchContent(self, key, quick=False, pg="1"):
        try:
            page = str(pg or "1")
        except Exception:
            page = "1"
        return self._parse_video_list(self._req("/search?q=%s&t=&sort=&page=%s" % (quote(str(key or "")), page)), page)

    def detailContent(self, ids):
        if isinstance(ids, (list, tuple)):
            vid = str(ids[0]) if ids else ""
        else:
            vid = str(ids or "")
        clean_id = re.sub(r"^https?://[^/]+/v/", "", vid).replace("/v/", "").strip().strip("/")
        html = self._req("/v/%s" % clean_id)
        if not html:
            return {"list": []}
        vod_name = clean_id
        m = re.search(r"<h1[^>]*>(.*?)</h1>", html, re.S)
        if m:
            vod_name = self._clean(m.group(1)) or vod_name
        vod_pic = ""
        m = re.search(r'<video[^>]+poster="([^"]+)"', html)
        if m:
            vod_pic = self._proxy_img_url(self._fix(m.group(1)), referer=self.HOST + "/")
        if not vod_pic:
            m = re.search(r'coverImageUrl:"([^"]+)"', html)
            if m:
                vod_pic = self._proxy_img_url(self._fix(m.group(1)), referer=self.HOST + "/")
        tags = []
        for m in re.finditer(r'href="(/t/[^"]+)"[^>]*>([^<]{1,30})<', html):
            try:
                name = self._clean(m.group(2))
                if name and name not in tags and len(tags) < 10:
                    tags.append(name)
            except Exception:
                continue
        type_name = " • ".join(tags) if tags else "肉视频"
        desc = ""
        m = re.search(r'<meta[^>]+name="description"[^>]+content="([^"]+)"', html)
        if m:
            desc = self._clean(m.group(1))
        main_name = ""
        main_vid = ""
        main_tags = []
        try:
            j = html.find('id:"%s"' % clean_id)
            if j >= 0:
                seg = html[j:j + 6000]
                m2 = re.search(r'name:"((?:[^"\\]|\\.)*)"', seg)
                if m2:
                    raw_name = m2.group(1)
                    try:
                        main_name = raw_name.encode().decode("unicode_escape", "ignore") if "\\u" in raw_name else raw_name
                    except Exception:
                        main_name = raw_name
                    main_name = self._clean(main_name.replace('\\"', '"'))
                m2 = re.search(r'vid:(?:"([^"]*)"|null)', seg)
                if m2 and m2.group(1) and m2.group(1) != "null":
                    main_vid = m2.group(1)
                m2 = re.search(r'tags:\$R\[\d+\]=\["([^"\]]+)"', seg)
                if m2:
                    main_tags = [self._clean(m2.group(1))]
        except Exception:
            pass
        if main_name:
            vod_name = main_name
        if main_tags:
            type_name = " • ".join(main_tags)
        vid_label = main_vid
        vod_content = desc
        if vid_label:
            vod_content = ("【番号】：%s\n%s" % (vid_label, desc)) if desc else ("【番号】：%s" % vid_label)
        vod = {"vod_id": clean_id, "vod_name": vod_name, "vod_remarks": vid_label, "vod_pic": vod_pic, "type_name": type_name, "vod_content": vod_content, "vod_play_from": self.getName(), "vod_play_url": "正片播放$%s" % clean_id}
        return {"list": [vod]}

    def playerContent(self, flag, id, vipFlags=None):
        if isinstance(id, (list, tuple)):
            id = str(id[0]) if id else ""
        else:
            id = str(id or "")
        if isinstance(flag, (list, tuple)):
            flag = str(flag[0]) if flag else ""
        else:
            flag = str(flag or "")
        clean_id = re.sub(r"^https?://[^/]+/v/", "", id).replace("/v/", "").strip().strip("/")
        if clean_id.startswith("http"):
            return {"parse": 0, "jx": 0, "playUrl": "", "url": clean_id, "header": {"User-Agent": self.headers["User-Agent"], "Referer": self.HOST + "/"}, "format": "application/x-mpegURL"}
        html = self._req("/v/%s" % clean_id)
        if not html:
            return {"parse": 1, "jx": 0, "playUrl": "", "url": "%s/v/%s" % (self.HOST, clean_id), "header": {}}
        ev = self._extract_ev(html)
        video_path = ev.get("videoUrl", "")
        if not video_path:
            return {"parse": 1, "jx": 0, "playUrl": "", "url": "%s/v/%s" % (self.HOST, clean_id), "header": {}}
        if video_path.startswith("http"):
            full = video_path
        else:
            full = self.HOST + video_path
        raw = self._get_bytes(full, headers={"User-Agent": self.headers["User-Agent"], "Referer": "%s/v/%s" % (self.HOST, clean_id)})
        m3u8 = self._png_extract_m3u8(raw)
        if "#EXTM3U" not in m3u8:
            return {"parse": 1, "jx": 0, "playUrl": "", "url": "%s/v/%s" % (self.HOST, clean_id), "header": {}}
        proxy_m3u8 = self._proxy_url(clean_id, full)
        return {"parse": 0, "jx": 0, "playUrl": "", "url": proxy_m3u8, "header": {"User-Agent": self.headers["User-Agent"], "Referer": self.HOST + "/"}, "format": "application/x-mpegURL"}

    def localProxy(self, param):
        p = {}
        if isinstance(param, dict):
            p = dict(param)
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
        else:
            p = {}
        try:
            ptype = str(p.get("type", ""))
            if ptype == "img" and p.get("u"):
                target = unquote(str(p.get("u")))
                r = unquote(str(p.get("r") or "")) or None
                return self._serve_img(target, referer=r)
            if ptype == "rou_hls" and p.get("u"):
                target = unquote(str(p.get("u")))
                vid = str(p.get("vid", ""))
                if target.startswith("/"):
                    target = self.HOST + target
                if "/api/hls/" in target and "?" not in target and ".png" not in target:
                    raw = self._get_bytes(target, headers={"User-Agent": self.headers["User-Agent"], "Referer": self.HOST + "/"})
                    m3u8 = self._png_extract_m3u8(raw)
                    if "#EXTM3U" not in m3u8:
                        # 非 PNG 封装: 直接取明文 m3u8
                        m3u8 = raw.decode("utf-8", "ignore") if raw else ""
                        if "#EXTM3U" not in m3u8:
                            return [500, "text/plain", b"empty m3u8"]
                else:
                    raw = self._get_bytes(target, headers={"User-Agent": self.headers["User-Agent"], "Referer": self.HOST + "/"})
                    m3u8 = raw.decode("utf-8", "ignore")
                    if "#EXTM3U" not in m3u8:
                        m3u8 = self._png_extract_m3u8(raw)
                if "#EXTM3U" in m3u8:
                    base = target.rsplit("/", 1)[0] + "/"
                    lines = []
                    for line in m3u8.splitlines():
                        s = line.strip()
                        if s.startswith("http"):
                            lines.append(self._proxy_url(vid, s))
                        elif s and not s.startswith("#"):
                            lines.append(self._proxy_url(vid, urllib.parse.urljoin(base, s)))
                        else:
                            lines.append(line)
                    body = "\n".join(lines)
                    return [200, "application/vnd.apple.mpegurl", body.encode("utf-8")]
                # m3u8 取失败: 尝试 PNG 封装 mp4 直出
                raw = self._get_bytes(target, headers={"User-Agent": self.headers["User-Agent"], "Referer": self.HOST + "/"})
                mp4 = self._png_extract_mp4(raw)
                if not mp4:
                    return [404, "text/plain", b"Not Found"]
                return [200, "video/mp2t", mp4]
        except Exception:
            pass
        return [404, "text/plain", b"Not Found"]

    def isVideoFormat(self, url):
        if not url:
            return False
        u = str(url).lower()
        return ".m3u8" in u or ".mp4" in u or ".flv" in u or ".ts" in u or "type=rou_hls" in u

    def manualVideoCheck(self):
        return False

    def action(self, action):
        return {}

    def destroy(self):
        self._host_winner = None
