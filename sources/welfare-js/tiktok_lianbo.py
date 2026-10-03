# -*- coding: utf-8 -*-
"""
TikTok连播 — vbox 福利专区「直播」栏目适配版
数据源: porntok.io (PornTok 短视频连播流)
  - 抓页内嵌 JSON 的 mp4 直链 (R2 存储桶 pub-9e425fd7f7a04b7aa301eafe26f84f84.r2.dev)
  - detailContent 把相关视频池拼成一条 # 分隔的连播 vod_play_url
  - playerContent 直回 mp4 直链 (parse=0, header 为 dict)
  - vod_id = "ptok@@" + base64(JSON payload)

vbox 契约修复:
  1. playerContent header → dict (不能 json.dumps 字符串)
  2. localProxy 返回 → bytes (b"Proxy inactive", 不能 str)
  3. __init__ 的 super().__init__() 包 try/except (iSH 无 base.spider 时兜底)
  4. init() 先调 super().init(extend) 再返回 (vbox 需拿域名注入)
"""
import sys, re, json, base64, ssl, time, warnings
from urllib.request import Request, urlopen
from urllib.parse import quote

warnings.filterwarnings("ignore")
sys.path.append('..')
try:
    from base.spider import Spider as BaseSpider
except ImportError:
    class BaseSpider:
        def __init__(self, *a, **k):
            self.options = {}
        def init(self, extend=""):
            return {}

UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36")

BASE = "https://porntok.io"
R2_HOST = "pub-9e425fd7f7a04b7aa301eafe26f84f84.r2.dev"
MP4_RE = re.compile(r'(https?://[^"\\\s\x00-\x1f]*?\.mp4)', re.I)

# 12 个硬编码 tag (第 0 个走首页, 其余走 /tag/{tag})
CLASSES = [
    "全部", "Girls", "Boys", "Girls & Boys", "POV", "Solo Girl",
    "Solo Boy", "Couple", "Threesome", "MILF", "Blowjob", "Anal",
]
POOL_LIMIT = 20  # 连播池上限


class Spider(BaseSpider):

    def __init__(self, *args, **kwargs):
        try:
            super().__init__(*args, **kwargs)
        except Exception:
            pass
        self._timeout = 20
        self._ctx = ssl.create_default_context()
        self._ctx.check_hostname = False
        self._ctx.verify_mode = ssl.CERT_NONE

    # ---------------- 基础 ----------------
    def getName(self):
        return "TikTok连播"

    def init(self, extend=""):
        try:
            super().init(extend)
        except Exception:
            pass
        # 对齐仓库主流源 (getav/18av/xiaohetang): init 返回 True
        return True

    def _http(self, url):
        """GET, 返回 (status, text). 失败返回 (0, '')."""
        req = Request(url, headers={"User-Agent": UA})
        try:
            resp = urlopen(req, timeout=self._timeout, context=self._ctx)
            raw = resp.read()
            return resp.status, raw.decode("utf-8", "ignore")
        except Exception:
            return 0, ""

    @staticmethod
    def _b64e(s):
        return base64.b64encode(s.encode("utf-8")).decode("ascii")

    @staticmethod
    def _b64d(s):
        return base64.b64decode(s.encode("ascii")).decode("utf-8", "ignore")

    def _pack(self, payload):
        """vod_id = ptok@@ + base64(json)"""
        return "ptok@@" + self._b64e(json.dumps(payload, ensure_ascii=False))

    def _unpack(self, vod_id):
        if isinstance(vod_id, list):
            vod_id = vod_id[0] if vod_id else ""
        if isinstance(vod_id, str) and vod_id.startswith("ptok@@"):
            try:
                return json.loads(self._b64d(vod_id[len("ptok@@"):]))
            except Exception:
                return {}
        return {}

    def _is_video_url(self, u):
        u = (u or "").lower()
        return u.endswith(".mp4") or u.endswith(".m4v") or ".mp4?" in u

    def _scrape_page(self, page_url):
        """抓页内嵌 JSON / 全页文本里的 mp4 直链与标题"""
        status, text = self._http(page_url)
        if not text:
            return []
        found = []
        # 优先解析 JSON 结构: {"url": "...mp4", "title": ...} 形式
        for m in re.finditer(r'\{[^{}]*?"(?:url|file|src|video)[^{}]*\}', text):
            blob = m.group(0)
            urls = MP4_RE.findall(blob)
            if urls:
                title = ""
                tm = re.search(r'"title"\s*:\s*"([^"]*)"', blob)
                if tm:
                    title = tm.group(1)
                am = re.search(r'"(?:author|username|user)"\s*:\s*"([^"]*)"', blob)
                author = am.group(1) if am else ""
                um = re.search(r'"(?:id|uuid)"\s*:\s*"?([0-9a-fA-F-]{6,})"?', blob)
                vid = um.group(1) if um else ""
                for u in urls:
                    found.append({
                        "url": u, "title": title or u.rsplit("/", 1)[-1],
                        "author": author, "vid": vid,
                        "page": page_url,
                    })
        # 兜底: 全页扫 mp4
        if not found:
            for u in MP4_RE.findall(text):
                found.append({"url": u, "title": u.rsplit("/", 1)[-1],
                              "author": "", "vid": "", "page": page_url})
        # 去重保序
        seen, out = set(), []
        for it in found:
            if it["url"] not in seen:
                seen.add(it["url"])
                out.append(it)
        return out[:POOL_LIMIT]

    # ---------------- TVBox 标准接口 ----------------
    def homeContent(self, filter):
        # class 必须为 dict 列表 (type_name/type_id), 设备端按 dict 解析分类
        return {
            "class": [{"type_name": c, "type_id": str(i)} for i, c in enumerate(CLASSES)],
            "list": [],
            "filters": {},
        }

    def categoryContent(self, tid, pg, filter, extend):
        items = []
        # tid 兼容: "0".."11" (homeContent 的 type_id) 或 tag 名本身
        try:
            tid = int(tid)
        except Exception:
            name = str(tid).strip()
            tid = CLASSES.index(name) if name in CLASSES else 0
        if tid >= len(CLASSES) or tid < 0:
            tid = 0
        page_url = BASE + "/" if tid == 0 else BASE + "/tag/" + quote(CLASSES[tid].lower())
        videos = self._scrape_page(page_url)
        for v in videos:
            pic = ""
            payload = {
                "url": v["url"], "title": v["title"], "author": v["author"],
                "vid": v["vid"], "page": page_url, "tag": CLASSES[tid],
                "pool": [x["url"] for x in videos if x["url"] != v["url"]][:POOL_LIMIT],
            }
            items.append({
                "vod_id": self._pack(payload),
                "vod_name": v["title"],
                "vod_pic": pic,
                "vod_remarks": (v["author"] or "mp4 直链"),
                "vod_class": CLASSES[tid],
                "vod_content": "PornTok 连播池: %d 条" % (len(payload["pool"]) + 1),
                "vod_year": "",
                "vod_area": "",
                "vod_from": "",
                "vod_actor": "",
                "vod_blurb": "",
            })
        total = max(len(items), 1)
        return {
            "page": pg,
            "pagecount": 1,
            "limit": len(items),
            "total": total,
            "list": items,
        }

    def detailContent(self, ids):
        detail = {}
        pool_urls = []
        for vod_id in (ids if isinstance(ids, list) else [ids]):
            p = self._unpack(vod_id)
            if not p:
                continue
            mp4 = p.get("url", "")
            if mp4:
                pool_urls.append(mp4)
            if p.get("pool"):
                for u in p["pool"]:
                    if u not in pool_urls:
                        pool_urls.append(u)
            # 若池为空且 payload 有 page, 现场再抓一次连播池
            if len(pool_urls) <= 1 and p.get("page"):
                fresh = [x["url"] for x in self._scrape_page(p["page"])]
                for u in fresh:
                    if u not in pool_urls:
                        pool_urls.append(u)
            detail = {
                "vod_id": vod_id if isinstance(vod_id, str) else str(vod_id),
                "vod_name": p.get("title", "") or "TikTok连播",
                "vod_pic": "",
                "vod_remarks": "连播 %d 条" % max(len(pool_urls), 1),
                "vod_class": p.get("tag", ""),
                "vod_content": ("作者: " + p["author"]) if p.get("author") else "",
                "vod_play_from": "m4direct",
                "vod_play_url": "#".join(pool_urls[:POOL_LIMIT]),
            }
            break
        if not detail:
            detail = {
                "vod_id": (ids[0] if isinstance(ids, list) and ids else str(ids)),
                "vod_name": "TikTok连播", "vod_pic": "", "vod_remarks": "",
                "vod_class": "", "vod_content": "",
                "vod_play_from": "m4direct", "vod_play_url": "",
            }
        return [detail]

    def playerContent(self, flag, id, vipFlags=None):
        """直回 mp4 直链, parse=0. header 必须 dict (vbox 硬性要求)."""
        if isinstance(id, list):
            id = id[0] if id else ""
        play_url = id
        # 若传入的是 vod_id, 解包出 mp4
        if not self._is_video_url(play_url):
            p = self._unpack(play_url)
            if p.get("url"):
                play_url = p["url"]
        body = {
            "parse": 0,
            "play_url": [play_url],
            "header": {"User-Agent": UA},
            "support_mime": "video/mp4",
            "play解析": 0,
            "url": play_url,
        }
        return json.dumps(body, ensure_ascii=False)

    def searchContent(self, key, quick=False, pg=1):
        return {"page": 1, "pagecount": 1, "limit": 0, "total": 0, "list": []}

    def localProxy(self, param):
        """本源 mp4 走 R2 公共桶直链, 无需代理. 返回必须 bytes."""
        return b"Proxy inactive"

    # ---------------- 可选钩子 ----------------
    def manualVideoCheck(self, url):
        return self._is_video_url(url)

    def isVideoFormat(self, url):
        return self._is_video_url(url)
