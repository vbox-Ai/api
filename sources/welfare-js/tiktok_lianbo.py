# -*- coding: utf-8 -*-
"""
TikTok连播 — vbox 福利专区「直播」栏目适配版
数据源: porntok.io (PornTok 短视频连播流)
  - 真实页面为 Next.js RSC: 视频对象内嵌于 __next_f 推流的 initialVideos
    字段: id/path(R2 mp4 直链)/hls_url/thumbnail_url/preview_url/title/
          category/post_id/view_count/author/profile_picture_url/...
    R2 桶: pub-9e425fd7f7a04b7aa301eafe26f84f84.r2.dev/videos/<cat>/<id>.mp4
  - 分类真实路径: /category/{slug} (不是 /tag/{slug})
  - detailContent 把同分类视频池拼成一条 # 分隔的连播 vod_play_url
  - playerContent 直回 mp4 直链 (parse=0, header 为 dict)
  - vod_id = "ptok@@" + base64(JSON payload)

vbox 契约修复:
  1. playerContent header → dict (不能 json.dumps 字符串)
  2. localProxy 返回 → bytes (b"Proxy inactive", 不能 str)
  3. __init__ 的 super().__init__() 包 try/except (iSH 无 base.spider 时兜底)
  4. init() 先调 super().init(extend) 再返回 True (对齐 getav/18av/xiaohetang)
  5. homeContent 的 class 必须是 [{"type_name","type_id"}] dict 列表
     (纯字符串列表会导致设备端「未能解析到分类」)
"""
import sys, re, json, base64, ssl, warnings
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
MP4_RE = re.compile(r'(https?://[^"\\\s\x00-\x1f]+?\.mp4)', re.I)

# 真实分类 (slug, 显示名) — 第 0 个走首页, 其余走 /category/{slug}
CATS = [
    (None, "全部"),
    ("amateur", "Amateur"),
    ("trans", "Trans"),
    ("indian", "Indian"),
    ("teen-18plus", "Teen 18+"),
    ("milf", "MILF"),
    ("big-tits", "Big Tits"),
    ("latina", "Latina"),
    ("public-outdoor", "Public Outdoor"),
    ("porn-for-women", "Porn for Women"),
    ("fetish", "Fetish"),
    ("asian", "Asian"),
    ("bbw", "BBW"),
    ("teen", "Teen"),
    ("anal", "Anal"),
    ("ebony", "Ebony"),
    ("blonde", "Blonde"),
    ("gay", "Gay"),
    ("hentai-animated", "Hentai Animated"),
]
POOL_LIMIT = 19  # 连播池上限 (含自身)


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

    @staticmethod
    def _is_video_url(u):
        u = (u or "").lower()
        return u.endswith(".mp4") or u.endswith(".m4v") or ".mp4?" in u

    @staticmethod
    def _unesc(val):
        """JSON 字符串值去转义 (unicode 转义序列等), 失败原样返回"""
        try:
            return json.loads('"%s"' % val)
        except Exception:
            return val

    def _parse_rsc(self, html):
        """解析 RSC flight 数据中 initialVideos 的视频对象 (转义形态).

        原始 HTML 中对象形如:
        {\\"id\\":6127,\\"path\\":\\"https://...r2.dev/videos/gay/x.mp4\\",
         \\"hls_url\\":null,\\"thumbnail_url\\":\\"...\\",\\"title\\":\\"..\\",
         \\"category\\":\\"..\\",\\"post_id\\":\\"..\\",\\"view_count\\":204,
         \\"author\\":\\"..\\",...}
        """
        vids = []
        for chunk in html.split('{\\"id\\":')[1:]:
            head = re.match(r'(\d+),\\"path\\"', chunk)
            if not head:
                continue
            d = {"id": head.group(1), "mp4": "", "thumb": "", "title": "",
                 "author": "", "cat": "", "views": ""}
            pats = {
                "mp4": r'\\"path\\":\\"(https://[^"\\]+?\.mp4)',
                "thumb": r'\\"thumbnail_url\\":\\"([^"\\]+?)\\"',
                "title": r'\\"title\\":\\"((?:[^"\\]|\\.)*?)\\"',
                "cat": r'\\"category\\":\\"([^"\\]+?)\\"',
                "author": r'\\"author\\":\\"([^"\\]+?)\\"',
                "views": r'\\"view_count\\":(\d+)',
            }
            for k, pat in pats.items():
                mm = re.search(pat, chunk)
                if mm:
                    v = mm.group(1)
                    if k != "views":
                        v = self._unesc(v)
                    if v:
                        d[k] = v
            if d["mp4"] and len(vids) < POOL_LIMIT:
                vids.append(d)
            if len(vids) >= POOL_LIMIT:
                break
        return vids

    def _parse_ld(self, html):
        """JSON-LD ItemList 兜底 (contentUrl 可能为 null, 取 mp4 才有效)"""
        vids = []
        for block in re.findall(r'<script type="application/ld\+json">([\s\S]*?)</script>', html):
            try:
                data = json.loads(block)
            except Exception:
                continue
            if data.get("@type") != "ItemList":
                continue
            for it in data.get("itemListElement", []):
                item = (it or {}).get("item") or {}
                mp4 = item.get("contentUrl") or ""
                m = re.search(r'/videos/([^/]+)/([^.]+)\.mp4', mp4)
                if not mp4 or not self._is_video_url(mp4):
                    continue
                d = {
                    "id": (re.search(r'/video/(\d+)$', item.get("@id", "")) or [None, ""])[1],
                    "mp4": mp4,
                    "thumb": item.get("thumbnailUrl") or "",
                    "title": item.get("name") or "",
                    "author": "",
                    "cat": item.get("category", "") or (m.group(1) if m else ""),
                    "views": "",
                }
                if len(vids) < POOL_LIMIT:
                    vids.append(d)
            if vids:
                break
        return vids

    def _scrape_page(self, page_url):
        """抓页 → 视频对象列表. 优先 RSC initialVideos, 其次 JSON-LD, 最后全页扫 mp4."""
        status, text = self._http(page_url)
        if not text:
            return []
        vids = self._parse_rsc(text)
        if not vids:
            vids = self._parse_ld(text)
        if not vids:
            for u in MP4_RE.findall(text):
                vids.append({"id": "", "mp4": u, "thumb": "",
                             "title": u.rsplit("/", 1)[-1], "author": "",
                             "cat": "", "views": ""})
                if len(vids) >= POOL_LIMIT:
                    break
        # 去重保序
        seen, out = set(), []
        for d in vids:
            if d["mp4"] and d["mp4"] not in seen:
                seen.add(d["mp4"])
                out.append(d)
        return out[:POOL_LIMIT]

    # ---------------- TVBox 标准接口 ----------------
    def homeContent(self, filter):
        # class 必须为 dict 列表 (type_name/type_id), 设备端按 dict 解析分类
        return {
            "class": [{"type_name": name, "type_id": str(i)}
                      for i, (_slug, name) in enumerate(CATS)],
            "list": [],
            "filters": {},
        }

    def _cat_index(self, tid):
        """tid 兼容: "0".."18" (homeContent 的 type_id) 或 slug/tag 名"""
        try:
            idx = int(tid)
            if 0 <= idx < len(CATS):
                return idx
        except Exception:
            pass
        name = str(tid).strip()
        for i, (slug, nm) in enumerate(CATS):
            if name.lower() in (slug or "", nm.lower(), nm.lower().replace(" ", "-")):
                return i
        return 0

    def categoryContent(self, tid, pg, filter, extend):
        idx = self._cat_index(tid)
        slug, name = CATS[idx]
        page_url = BASE + "/" if slug is None else BASE + "/category/" + slug
        videos = self._scrape_page(page_url)
        items = []
        for v in videos:
            pool = [x["mp4"] for x in videos if x["mp4"] != v["mp4"]]
            payload = {
                "id": v["id"], "url": v["mp4"], "title": v["title"],
                "author": v["author"], "cat": name, "slug": slug,
                "views": v["views"], "thumb": v["thumb"],
                "page": page_url, "pool": pool,
            }
            remarks = []
            if v["author"]:
                remarks.append(v["author"])
            if v["views"]:
                remarks.append("%s次观看" % v["views"])
            items.append({
                "vod_id": self._pack(payload),
                "vod_name": v["title"] or ("视频 " + v["id"] if v["id"] else name),
                "vod_pic": v["thumb"],
                "vod_remarks": " · ".join(remarks),
                "vod_class": name,
                "vod_content": "PornTok 连播池 %d 条" % (len(pool) + 1),
            })
        return {
            "page": 1,
            "pagecount": 1,
            "limit": len(items),
            "total": len(items),
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
            # 池为空且有页面 → 现场再抓一次 (兜底)
            if len(pool_urls) <= 1 and p.get("page"):
                for x in self._scrape_page(p["page"]):
                    if x["mp4"] not in pool_urls:
                        pool_urls.append(x["mp4"])
                    if len(pool_urls) >= POOL_LIMIT:
                        break
            detail = {
                "vod_id": vod_id if isinstance(vod_id, str) else str(vod_id),
                "vod_name": p.get("title") or "TikTok连播",
                "vod_pic": p.get("thumb") or "",
                "vod_remarks": "连播 %d 条" % max(len(pool_urls), 1),
                "vod_class": p.get("cat") or "",
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
