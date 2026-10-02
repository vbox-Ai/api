#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
蝴蝶影视·小荷塘 - vbox 远程源适配版
站点: https://y5b1.tllp166.xyz (macCMS 风格)
适配: 继承 SpiderBase + super().init(extend) + localProxy三元组 + 封面走本地代理
"""
import sys
sys.path.append('..')
import os
import re
import json
import base64
import html as html_lib
import urllib.request
import urllib.parse
from urllib.parse import urlparse, quote, unquote
import http.cookiejar
import gzip
import zlib
import ssl

try:
    from base.spider import Spider as SpiderBase
except ImportError:
    class SpiderBase(object):
        def __init__(self):
            self._vbox_effective_hosts = []
        def getCache(self, key): return None
        def setCache(self, key, value): return "fail"
        def delCache(self, key): return "fail"


def format_remarks(brand="蝴蝶影视", meta=""):
    clean_meta = str(meta or "").strip()
    clean_meta = re.sub(r"[\r\n\t]+", " ", clean_meta).strip()
    if clean_meta:
        return "%s | %s" % (brand, clean_meta)
    return brand


class Spider(SpiderBase):
    PLATFORM_KEY = "xiaohetang_py"

    def __init__(self):
        try:
            super(Spider, self).__init__()
        except Exception:
            pass
        self.siteUrl = "https://y5b1.tllp166.xyz"
        # 多域池: 站点会轮换域名 (2026-10-03 实测 v3s6 活, y5b1 已连不上)
        # 并发竞速取首个真页域名, 缓存 600s
        self._pool = [
            "https://v3s6.tllp169.xyz",
            "https://y5b1.tllp166.xyz",
        ]
        self._live_host = None
        self._live_ts = 0.0
        self._home_cache = {}
        self.tgGroup = "https://t.me/tvshare23"
        self.brandActor = "🦋 TG群: @tvshare23"
        self.brandDirector = "🦋 蝴蝶影视"
        self._ua = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36"
        self.options = {}

        self.ctx = ssl.create_default_context()
        self.ctx.check_hostname = False
        self.ctx.verify_mode = ssl.CERT_NONE

        self.cj = http.cookiejar.CookieJar()
        self.opener = urllib.request.build_opener(
            urllib.request.HTTPCookieProcessor(self.cj),
            urllib.request.HTTPSHandler(context=self.ctx)
        )

    def init(self, extend=""):
        try:
            super().init(extend)
        except AttributeError:
            pass
        if isinstance(extend, dict):
            self.options = extend
        elif extend:
            try:
                self.options = json.loads(extend)
            except Exception:
                self.options = {}
        # 域池合并: extend 自定义 > vbox 注入 _vbox_effective_hosts > 内置池
        custom = []
        if isinstance(self.options, dict):
            hs = self.options.get("hosts")
            if isinstance(hs, list):
                custom = [str(h).rstrip("/") for h in hs if str(h).startswith("http")]
            if self.options.get("site"):
                custom.insert(0, str(self.options.get("site")).rstrip("/"))
        injected = [str(h).rstrip("/") for h in (getattr(self, "_vbox_effective_hosts", None) or []) if str(h).startswith("http")]
        merged = []
        for u in custom + injected + self._pool:
            if u and u not in merged:
                merged.append(u)
        self._pool = merged
        return True

    # ================= 多域并发竞速 =================
    def _probe_host(self, host):
        """轻量探测: 分类页9 真页判定 (脱壳后含 play 链接且长度达标)"""
        try:
            url = host + "/index.php/vod/type/id/9.html"
            req = urllib.request.Request(url, headers={
                "User-Agent": self._ua,
                "Referer": host + "/",
                "Accept-Encoding": "gzip",
            })
            with self.opener.open(req, timeout=12) as resp:
                raw = resp.read()
            if raw.startswith(b"\x1f\x8b"):
                raw = gzip.decompress(raw)
            t = raw.decode("utf-8", "ignore")
            m = re.search(r'decodeURIComponent\s*\(\s*atob\s*\(\s*["\']([A-Za-z0-9+/=]+)["\']\s*\)\s*\)', t)
            if m:
                try:
                    t = urllib.parse.unquote(base64.b64decode(m.group(1)).decode("latin1"))
                except Exception:
                    pass
            return len(t) > 100000 and "/index.php/vod/play" in t
        except Exception:
            return False

    def _race_live(self):
        """全候选并发探测, 按池内优先级取首个成功者"""
        import threading
        pool = list(self._pool)
        results = {}
        barrier = threading.Barrier(len(pool))
        def worker(idx, host):
            try:
                results[idx] = self._probe_host(host)
            finally:
                barrier.wait()
        threads = [threading.Thread(target=worker, args=(i, h), daemon=True) for i, h in enumerate(pool)]
        for t in threads:
            t.start()
        for i in range(len(pool)):
            threads[i].join(timeout=20)
        for i, h in enumerate(pool):
            if results.get(i):
                return h
        return None

    def _resolve_live(self):
        """活域解析: 缓存 600s, 过期则重新竞速; 全死时回退 siteUrl"""
        import time as _time
        now = _time.time()
        if self._live_host and now - self._live_ts < 600:
            return self._live_host
        winner = self._race_live()
        if winner:
            self._live_host = winner
            self._live_ts = now
            return winner
        return self.siteUrl

    def _rewrap_host(self, url):
        """把池内旧域 host 重写到当前活域 (封面/播放地址用)"""
        if not url:
            return url
        live = self._live_host or self.siteUrl
        for h in self._pool:
            if url.startswith(h):
                return live + url[len(h):]
        return url

    def getName(self):
        return "蝴蝶影视·小荷塘"

    def isVideoFormat(self, url):
        if not url:
            return False
        low = url.lower()
        if any(bad in low for bad in ("preview.mp4", "sample.mp4", "trailer.mp4", "loading", "stat")):
            return False
        if "/proxy?" in low or "type=stream" in low:
            return True
        return any(k in low for k in (".m3u8", ".mp4", ".flv", ".mkv", ".avi", ".ts", ".mpd", "index.png"))

    def manualVideoCheck(self):
        return False

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
            headers = {"User-Agent": self._ua}
            if referer:
                headers["Referer"] = referer
            req = urllib.request.Request(url, headers=headers)
            with self.opener.open(req, timeout=15) as resp:
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

    # ============ HLS 流代理 (播放修复) ============
    def _unshell(self, text):
        """脱壳: decodeURIComponent(atob(b64)) -> 真 HTML"""
        m = re.search(r'decodeURIComponent\s*\(\s*atob\s*\(\s*["\']([A-Za-z0-9+/=]+)["\']\s*\)\s*\)', text)
        if m:
            try:
                return urllib.parse.unquote(base64.b64decode(m.group(1)).decode("latin1"))
            except Exception:
                return text
        return text

    def _parse_player_aaaa(self, text):
        """解析脱壳后页面的 player_aaaa JS 对象 -> dict, 无则 {}"""
        m = re.search(r'\bplayer_aaaa\s*[:=]\s*\{', text)
        if not m:
            return {}
        i = m.end() - 1
        depth = 0
        while i < len(text):
            c = text[i]
            if c == '{':
                depth += 1
            elif c == '}':
                depth -= 1
                if depth == 0:
                    brace = text[m.end() - 1:i + 1]
                    try:
                        return json.loads(brace)
                    except Exception:
                        return {}
                    break
            i += 1
        return {}

    def _absolutize(self, u):
        u = (u or "").replace("\\/", "/").strip()
        if not u:
            return ""
        live = self._resolve_live()
        if u.startswith("http"):
            return u
        if u.startswith("//"):
            return "https:" + u
        if u.startswith("/"):
            return live + u
        return live + "/" + u

    def _m3u8_from_page(self, text):
        """当前页 player_aaaa.url"""
        return self._absolutize((self._parse_player_aaaa(text) or {}).get("url", ""))

    def _m3u8_by_link(self, text):
        """player_aaaa.link -> 跟到 sid 子页 -> 取其 player_aaaa.url"""
        link = self._absolutize((self._parse_player_aaaa(text) or {}).get("link", ""))
        if not link:
            return ""
        res = self._fetch(link, referer=self._resolve_live() + "/")
        return self._m3u8_from_page(self._unshell(res.get("text", "")))

    def _m3u8_by_regex(self, text):
        """兜底: 页内字面 .m3u8 (兼容 JSON 反斜杠转义)"""
        for x in re.findall(r'["\']((?:https?:)?\\?/\\?/?[^"\'\s]*?\.m3u8[^"\'\s]*)["\']', text):
            u = urllib.parse.unquote(x.replace("\\", ""))
            if u:
                return self._absolutize(u)
        return ""

    def _extract_m3u8(self, page_url):
        """抓播放页 -> 脱壳 -> 优先 player_aaaa.url(可跟 link) -> 正则兜底 -> 解 master 变体"""
        live = self._resolve_live() + "/"
        res = self._fetch(page_url, referer=live)
        text = self._unshell(res.get("text", ""))
        m3u8 = self._m3u8_from_page(text) or self._m3u8_by_link(text) or self._m3u8_by_regex(text)
        if not m3u8:
            return ""
        # master 播放列表 -> 取首个变体
        res2 = self._fetch(m3u8, referer=live)
        raw2 = res2.get("text", "")
        if "#EXT-X-STREAM-INF" in raw2:
            vm = re.search(r'#EXT-X-STREAM-INF[^\n]*\n\s*([^\s#][^\n]*)', raw2)
            if vm:
                u = vm.group(1).strip()
                m3u8 = u if u.startswith("http") else urllib.parse.urljoin(m3u8, u)
        return m3u8

    def _discover_play_lines(self, main_url):
        """从主播放页发现播放线路: 返回 [(label, target_page_url), ...]
        仅取与当前视频同 id 的 sid 线路(排除侧栏推荐视频); 单 sid 标"专线", 多 sid 标"线路N"; 无则兜底主播放页"""
        try:
            res = self._fetch(main_url, referer=self._resolve_live() + "/")
            text = self._unshell(res.get("text", ""))
        except Exception:
            return [("小荷塘专线", main_url)]
        # 当前视频 id (从 main_url 提取), 用于过滤同 id 的线路
        idm = re.search(r'/vod/play/id/(\d+)', main_url)
        target_id = idm.group(1) if idm else None
        links = sorted(set(re.findall(r'href=["\'](/index\.php/vod/play/id/\d+/sid/\d+/nid/\d+\.html)["\']', text)))
        if target_id:
            filtered = [l for l in links if ("/id/%s/" % target_id) in l]
            if filtered:
                links = filtered
        seen_sids = []
        for ln in links:
            sm = re.search(r'/sid/(\d+)/', ln)
            if sm and sm.group(1) not in seen_sids:
                seen_sids.append(sm.group(1))
        lines = []
        if seen_sids:
            multi = len(seen_sids) > 1
            for idx, sid in enumerate(seen_sids[:3], 1):
                tgt = next((l for l in links if ("/sid/%s/" % sid) in l), main_url)
                lab = "小荷塘专线" if not multi else ("小荷塘线路%d" % idx)
                lines.append((lab, self._resolve_live() + tgt))
        if not lines:
            lines.append(("小荷塘专线", main_url))
        return lines

    def _stream_proxy_url(self, m3u8_url):
        base = self._proxy_base()
        enc = base64.b64encode(m3u8_url.encode("utf-8")).decode("ascii")
        sep = "&" if "?" in base else "?"
        return base + sep + "type=stream&url=" + quote(enc, safe="")

    def _serve_stream(self, m3u8_url, referer=None):
        """抓 m3u8, 分片绝对化, 返回播放列表"""
        try:
            res = self._fetch(m3u8_url, referer=(referer or self._resolve_live() + "/"))
            raw = res.get("text", "")
            base = m3u8_url.rsplit("/", 1)[0] + "/"
            out_lines = []
            for l in raw.splitlines():
                s = l.strip()
                if s and not s.startswith("#"):
                    out_lines.append(s if s.startswith("http") else urllib.parse.urljoin(base, s))
                else:
                    out_lines.append(l)
            body = ("\n".join(out_lines) + "\n").encode("utf-8")
            return [200, "application/vnd.apple.mpegurl", body]
        except Exception:
            return [502, "text/plain", b"stream fetch failed"]

    def _fetch(self, target_url, data=None, referer="", headers_custom=None):
        if not target_url:
            return {"code": 0, "text": "", "bytes": b"", "err": "", "final_url": ""}
        live = self._resolve_live()
        if target_url.startswith("//"):
            target_url = "https:" + target_url
        elif target_url.startswith("/"):
            target_url = live + target_url
        else:
            target_url = self._rewrap_host(target_url)
        if not referer:
            referer = live + "/"

        headers = {
            "User-Agent": self._ua,
            "Referer": referer if referer else (self.siteUrl + "/"),
            "Accept": "*/*",
            "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
            "Accept-Encoding": "gzip, deflate",
            "Connection": "keep-alive"
        }
        if headers_custom:
            headers.update(headers_custom)

        req_data = None
        if data is not None:
            if isinstance(data, dict):
                req_data = urllib.parse.urlencode(data).encode("utf-8")
                headers["Content-Type"] = "application/x-www-form-urlencoded; charset=UTF-8"
                headers["X-Requested-With"] = "XMLHttpRequest"
            elif isinstance(data, (bytes, str)):
                req_data = data.encode("utf-8") if isinstance(data, str) else data

        last_err = ""
        for attempt in range(2):
            try:
                req = urllib.request.Request(target_url, data=req_data, headers=headers)
                with self.opener.open(req, timeout=12) as resp:
                    code = resp.getcode()
                    final_url = resp.geturl()
                    raw = resp.read()
                    enc = getattr(resp, "headers", {}).get("Content-Encoding", "")
                    if raw.startswith(b"\x1f\x8b") or enc == "gzip":
                        raw = gzip.decompress(raw)
                    elif enc == "deflate":
                        try:
                            raw = zlib.decompress(raw)
                        except Exception:
                            raw = zlib.decompress(raw, -zlib.MAX_WBITS)
                    try:
                        text = raw.decode("utf-8")
                    except Exception:
                        text = raw.decode("latin1", errors="ignore")

                    shell_m = re.search(r'decodeURIComponent\s*\(\s*atob\s*\(\s*["\']([A-Za-z0-9+/=]+)["\']\s*\)\s*\)', text)
                    if shell_m:
                        try:
                            b64_str = shell_m.group(1)
                            decoded_raw = base64.b64decode(b64_str).decode("latin1")
                            unquoted_html = urllib.parse.unquote(decoded_raw)
                            try:
                                text = unquoted_html.encode("latin1").decode("utf-8")
                            except Exception:
                                text = unquoted_html
                        except Exception:
                            pass

                    return {"code": code, "text": text, "bytes": raw, "err": "", "final_url": final_url}
            except urllib.error.HTTPError as e:
                last_err = "HTTP %s" % e.code
                if e.code in (451, 403, 429) and attempt == 0:
                    continue
                err_raw = ""
                try:
                    err_raw = e.read().decode("utf-8", errors="ignore")
                except Exception:
                    pass
                return {"code": e.code, "text": err_raw, "bytes": b"", "err": str(e), "final_url": target_url}
            except Exception as e:
                last_err = str(e)
                if attempt == 0:
                    continue
                return {"code": -1, "text": "", "bytes": b"", "err": str(e), "final_url": target_url}

        return {"code": -1, "text": "", "bytes": b"", "err": last_err, "final_url": target_url}

    def homeContent(self, filter):
        classes = [
            {"type_name": "🇨🇳 国内视频", "type_id": "/index.php/vod/type/id/9.html"},
            {"type_name": "🌸 系列全集", "type_id": "/index.php/vod/type/id/1.html"},
            {"type_name": "🌐 国外精选", "type_id": "/index.php/vod/type/id/12.html"},
            {"type_name": "🔥 猎奇专区", "type_id": "/index.php/vod/type/id/15.html"},
            {"type_name": "🎀 次元萝莉", "type_id": "/index.php/vod/type/id/2.html"},
            {"type_name": "👄 欧美口舌", "type_id": "/index.php/vod/type/id/3.html"}
        ]
        if not classes:
            classes = [{"type_name": "小荷塘·全部", "type_id": "/index.php/vod/type/id/9.html"}]
        result = {"class": classes}
        if filter:
            filter_items = [
                {
                    "key": "by",
                    "name": "排序",
                    "init": "time",
                    "value": [
                        {"n": "最新发布", "v": "time"},
                        {"n": "本周最热", "v": "hits_week"},
                        {"n": "最赞影片", "v": "up"}
                    ]
                }
            ]
            result["filters"] = {c["type_id"]: filter_items for c in classes}
        return result

    def homeVideoContent(self):
        return {"list": []}

    def _extract_pic(self, block_content):
        """从卡片块中提取封面并转本地代理 URL"""
        pic = ""
        cand_pics = re.findall(r'["\'](https?://[^"\']+\.(?:jpg|jpeg|png|webp)[^"\']*)["\']', block_content, re.I)
        if not cand_pics:
            cand_pics = re.findall(r'["\'](/[^"\']+\.(?:jpg|jpeg|png|webp)[^"\']*)["\']', block_content, re.I)
        for cp in cand_pics:
            low_cp = cp.lower()
            if any(bad in low_cp for bad in ("loading.png", "load", "default", "logo", "touxiang", "favicon")):
                continue
            pic = cp
            break
        if not pic:
            for attr in ("data-original", "data-src", "data-bg", "data-cover", "data-thumb"):
                attr_m = re.search(r'%s=["\']([^"\']+)["\']' % attr, block_content, re.I)
                if attr_m and "loading" not in attr_m.group(1).lower():
                    pic = attr_m.group(1).strip()
                    break
        if not pic:
            bg_m = re.search(r'url\s*\(\s*["\']?([^"\'\)\s]+)["\']?\s*\)', block_content)
            if bg_m and "loading" not in bg_m.group(1).lower() and not bg_m.group(1).endswith((".svg", ".ico")):
                pic = bg_m.group(1).strip()
        if pic.startswith("//"):
            pic = "https:" + pic
        elif pic.startswith("/"):
            pic = self._resolve_live() + pic
        pic = self._rewrap_host(pic)
        return self._proxy_img_url(pic, referer=self._resolve_live() + "/") if pic else ""

    def categoryContent(self, tid, pg, filter, extend):
        del filter
        slug = str(tid).strip()
        pg_num = int(pg) if str(pg).isdigit() else 1

        extend = extend if isinstance(extend, dict) else {}
        by_val = extend.get("by", "")

        target_path = slug
        if by_val:
            id_m = re.search(r'id/(\d+)', slug)
            type_id = id_m.group(1) if id_m else "9"
            if pg_num > 1:
                target_path = "/index.php/vod/show/by/%s/id/%s/page/%d.html" % (by_val, type_id, pg_num)
            else:
                target_path = "/index.php/vod/show/by/%s/id/%s.html" % (by_val, type_id)
        else:
            if pg_num > 1:
                target_path = re.sub(r'\.html$', '/page/%d.html' % pg_num, target_path)

        res = self._fetch(target_path)
        html_text = res.get("text", "")

        blocks = re.split(r'<a\s+[^>]*href=["\'](/index\.php/vod/play/id/\d+[^"\']*)["\']', html_text, flags=re.I)

        videos = []
        seen_ids = set()

        for i in range(1, len(blocks), 2):
            play_href = blocks[i].strip()
            block_content = blocks[i + 1] if i + 1 < len(blocks) else ""

            if play_href in seen_ids:
                continue

            title = ""
            title_m = re.search(r'class=["\']?[^"\'>]*(?:title|name|text)[^"\'>]*["\']?[^>]*>([\s\S]*?)<', block_content, re.I)
            if title_m:
                title = re.sub(r'<[^>]+>', '', title_m.group(1)).strip()
            if not title:
                title_alt = re.search(r'(?:title|alt)=["\']([^"\']+)["\']', block_content, re.I)
                if title_alt:
                    title = title_alt.group(1).strip()

            pic = self._extract_pic(block_content)

            meta_str = ""
            dur_m = re.search(r'(\d+:\d+|\d+集)', block_content)
            if dur_m:
                meta_str = dur_m.group(1).strip()

            remarks = format_remarks("蝴蝶影视", meta_str if meta_str else "超清")

            if not title:
                id_match = re.search(r'id/(\d+)', play_href)
                title = "精彩视频 %s" % (id_match.group(1) if id_match else "")

            seen_ids.add(play_href)
            videos.append({
                "vod_id": play_href,
                "vod_name": html_lib.unescape(title),
                "vod_pic": pic if pic else "https://dummyimage.com/600x338/1a1a1a/ffffff.png&text=No+Pic",
                "vod_remarks": remarks,
                "style": {"type": "rect", "ratio": 1.78}
            })

        return {
            "page": pg_num,
            "pagecount": pg_num + 1 if len(videos) >= 15 else 1,
            "limit": len(videos),
            "total": 9999 if len(videos) >= 15 else len(videos),
            "list": videos
        }

    def detailContent(self, ids):
        raw_id = ids[0] if isinstance(ids, (list, tuple)) else str(ids)
        detail_path = raw_id if raw_id.startswith("http") else self.siteUrl + raw_id

        res = self._fetch(detail_path)
        html_text = res.get("text", "")

        title_m = re.search(r'<title[^>]*>(.*?)</title>', html_text, re.I)
        raw_title = title_m.group(1).strip() if title_m else "精彩影视"
        clean_title = raw_title.split("-")[0].split("_")[0].strip()

        # 封面: 绝对/相对都取, 再重映射到活域
        pic_src = ""
        pic_m = re.search(r'<img[^>]+(?:data-original|data-src|src)=["\']([^"\']+\.(?:jpg|jpeg|png|webp))["\']', html_text, re.I)
        if pic_m:
            pic_src = pic_m.group(1)
        if pic_src.startswith("//"):
            pic_src = "https:" + pic_src
        elif pic_src.startswith("/"):
            pic_src = self._resolve_live() + pic_src
        pic_src = self._rewrap_host(pic_src)
        pic = self._proxy_img_url(pic_src, referer=self._resolve_live() + "/") if pic_src else ""

        # 播放地址: 存活域绝对 URL, 客户端"已有地址"可直接播放
        if raw_id.startswith("http"):
            _p = urlparse(raw_id)
            _play_path = _p.path + (_p.query if _p.query else "")
        else:
            _play_path = raw_id if raw_id.startswith("/") else "/" + raw_id
        live_play_url = self._resolve_live() + _play_path

        # 多线路发现: 免费单线(专线) / 付费多线(线路1/线路2), 每条指向 playerContent 可解析的页面
        try:
            play_lines = self._discover_play_lines(live_play_url)
        except Exception:
            play_lines = [("小荷塘专线", live_play_url)]

        desc_lines = [
            "【🔥 官方交流群: %s】" % self.tgGroup,
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━━",
            "• 影片名称: %s" % clean_title,
            "• 活跃节点: %s" % self._resolve_live(),
            "• 播放模式: 蝴蝶影视专属动态极速硬解",
            "• 本接口已启用页面脱壳与动态鉴权防护。"
        ]
        escaped_desc = "\n".join(desc_lines).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")

        safe_title = clean_title.replace("$", "＄").replace("#", "＃")
        segs = ["%s$%s" % (lab, url) for lab, url in play_lines]
        vod_play_url = safe_title + "$" + "#".join(segs) if segs else ("%s$%s" % (safe_title, live_play_url))

        return {
            "list": [{
                "vod_id": raw_id,
                "vod_name": html_lib.unescape(clean_title),
                "vod_pic": pic,
                "vod_actor": self.brandActor,
                "vod_director": self.brandDirector,
                "vod_remarks": format_remarks("蝴蝶影视", "正片"),
                "vod_content": escaped_desc,
                "vod_play_from": "🦋蝴蝶极速专线",
                "vod_play_url": vod_play_url
            }]
        }

    def playerContent(self, flag, id, vipFlags):
        raw_id = str(id).strip()
        # 已是可直接播放的 m3u8(http 且 .m3u8) -> 直接包流代理, 不重映射到活域
        if raw_id.startswith("http") and ".m3u8" in raw_id.lower():
            _h = {"User-Agent": self._ua, "Referer": self._resolve_live() + "/"}
            return {"parse": 0, "jx": 0, "url": self._stream_proxy_url(raw_id), "header": _h}
        # 归一化: 完整 URL(可能含旧域) / 相对路径 -> 活域播放页路径
        if raw_id.startswith("http"):
            p = urlparse(raw_id)
            path = p.path + (p.query if p.query else "")
        else:
            path = raw_id if raw_id.startswith("/") else "/" + raw_id
        play_url = self._resolve_live() + path

        # 抓播放页脱壳取 m3u8, 包成本地代理流地址 (修复播放)
        m3u8 = ""
        try:
            m3u8 = self._extract_m3u8(play_url)
        except Exception:
            m3u8 = ""

        headers = {
            "User-Agent": self._ua,
            "Referer": self._resolve_live() + "/"
        }

        if m3u8:
            return {
                "parse": 0,
                "jx": 0,
                "url": self._stream_proxy_url(m3u8),
                "header": headers
            }
        # 兜底: 旧逻辑 (交给内置解析器)
        return {
            "parse": 1,
            "jx": 0,
            "url": play_url,
            "header": headers
        }

    def searchContent(self, key, quick, pg="1"):
        pg_num = int(pg) if str(pg).isdigit() else 1
        search_path = "/index.php/vod/search/page/%d/wd/%s.html" % (pg_num, urllib.parse.quote(key))

        res = self._fetch(search_path)
        html_text = res.get("text", "")

        blocks = re.split(r'<a\s+[^>]*href=["\'](/index\.php/vod/play/id/\d+[^"\']*)["\']', html_text, flags=re.I)

        videos = []
        seen_ids = set()

        for i in range(1, len(blocks), 2):
            play_href = blocks[i].strip()
            block_content = blocks[i + 1] if i + 1 < len(blocks) else ""

            if play_href in seen_ids:
                continue

            title = ""
            title_m = re.search(r'class=["\']?[^"\'>]*(?:title|name|text)[^"\'>]*["\']?[^>]*>([\s\S]*?)<', block_content, re.I)
            if title_m:
                title = re.sub(r'<[^>]+>', '', title_m.group(1)).strip()
            if not title:
                title_alt = re.search(r'(?:title|alt)=["\']([^"\']+)["\']', block_content, re.I)
                if title_alt:
                    title = title_alt.group(1).strip()

            pic = self._extract_pic(block_content)

            remarks = format_remarks("蝴蝶影视", "搜索")

            if not title:
                id_match = re.search(r'id/(\d+)', play_href)
                title = "%s 相关视频 %s" % (key, id_match.group(1) if id_match else "")

            seen_ids.add(play_href)
            videos.append({
                "vod_id": play_href,
                "vod_name": html_lib.unescape(title),
                "vod_pic": pic if pic else "https://dummyimage.com/600x338/1a1a1a/ffffff.png&text=Search",
                "vod_remarks": remarks,
                "style": {"type": "rect", "ratio": 1.78}
            })

        return {
            "page": pg_num,
            "pagecount": pg_num + 1 if len(videos) >= 15 else 1,
            "limit": len(videos),
            "total": 9999 if len(videos) >= 15 else len(videos),
            "list": videos
        }

    def action(self, action):
        if action == "toast":
            return {"msg": "🦋 蝴蝶影视正在为您极速解析"}
        return {"msg": "ok"}

    def liveContent(self):
        return ""

    def localProxy(self, params):
        p = {}
        if isinstance(params, dict):
            p = params
        elif isinstance(params, str):
            s = params.strip()
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
        u = unquote(str(p.get("u") or p.get("url") or ""))
        r = unquote(str(p.get("r") or "")) or None
        if t == "stream":
            # url 参数可能是 b64(m3u8) 或明文字符串
            cand = u
            if "://" not in cand:
                try:
                    cand = base64.b64decode(cand).decode("utf-8")
                except Exception:
                    cand = ""
            if cand:
                return self._serve_stream(cand, referer=r)
            return [404, "text/plain", b"no stream url"]
        if t == "img" and u:
            return self._serve_img(self._rewrap_host(u), referer=r)
        return [404, "text/plain", b""]

    def destroy(self):
        self.options = {}
        try:
            self.cj.clear()
        except Exception:
            pass
