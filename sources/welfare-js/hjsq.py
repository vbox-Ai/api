#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""海角社区（hjsq / haijiao）— vbox 自包含适配器

协议来源：libapp.so blutter 反汇编（package:avbox/module/hjsq/*）
────────────────────────────────────────────────────────────
鉴权头
    X-User-Id    : 171299991201                 （HjSqInterceptor 硬编码）
    X-User-Token : SpUtil["token_hjsq"]         （游客 token，可读全站帖子）
响应信封
    {"errorCode":0,"message":"","success":true,"data":…}
接口
    GET  api2/topic/nodes              节点树（137 条扁平，靠 parentId 组层级）
    GET  api2/topic/node/topics        节点帖子  qp: page / nodeId / type
    GET  api2/topic/hot/topics         热帖
    GET  api2/topic/node/news          新闻
    GET  api2/topic/{topicId}          帖子详情
    GET  api2/topic/search             搜索      qp: node_id / keyword
    GET  api2/video/node_list          视频流    （需真实登录态，游客 token 不可用）
    POST api2/attachment               播放解析  （图片帖恒 errorCode=1，视频直链已在详情里）
资源
    视频  attachments[category=video].remoteUrl  → m3u8（HLS + AES-128，key 同目录可取）
    图片  attachments[category=images].remoteUrl → *.jpg.txt
          自定义字母表 base64 → 得 "data:image/jpeg;base64,…" → 标准 base64 → 真 JPEG
"""

import base64
import binascii
import json
import os
import sys
import time
import urllib.error
import urllib.parse
import urllib.request

try:
    from base.spider import Spider as SpiderBase
except ImportError:  # 本地/离线兜底
    class SpiderBase(object):
        def getCache(self, key):
            return None

        def setCache(self, key, value):
            return "fail"

        def delCache(self, key):
            return "fail"


# ============================================================ 常量
BASE_DEFAULT = "http://23.225.145.74"
USER_ID_DEFAULT = "171299991201"
TOKEN_DEFAULT = "b2dc730bf54441f18492061ce80659b3"

# 自定义 base64 字母表（libapp.so 内字面量，64 字符互不重复）
ALPH64 = "ABCD*EFGHIJKLMNOPQRSTUVWX#YZabcdefghijklmnopqrstuvwxyz1234567890"
_IDX64 = {c: i for i, c in enumerate(ALPH64)}

# 平台固定栏目（forum_page.dart 的 6 个 tab + 详情型入口）
SPECIAL_GROUPS = [
    ("hot", "热帖"),
    ("news", "新闻"),
    ("new", "最新"),
    ("cream", "精华"),
    ("original", "原创"),
]
_TYPE_MAP = {"new": 1, "cream": 3, "original": 7}

# ============================================================ vbox 运行时适配
# 客户端 base.spider 只给 requests 打了「代理 + verify=False」补丁，裸 urllib 不走；
# 而 iOS CPython 无系统 CA 证书包 —— urllib 的 HTTPS 会全部 SSLError。
# 现象即「分类能显示（本地静态），点进去没有数据（联网失败）」。
try:
    import ssl as _ssl
    _SSL_CTX = _ssl.create_default_context()
    _SSL_CTX.check_hostname = False
    _SSL_CTX.verify_mode = _ssl.CERT_NONE
except Exception:
    _SSL_CTX = None


def _vbox_cfg(sp, name, default=None):
    v = getattr(sp, name, None)
    if v is None:
        v = globals().get(name)
    return default if v is None else v


def _vbox_proxy(sp=None):
    if sp is not None and not _vbox_cfg(sp, "_vbox_proxy_enabled", False):
        return {}
    if sp is None and not globals().get("_vbox_proxy_enabled", False):
        return {}
    u = (getattr(sp, "_vbox_proxy_url", None) if sp is not None else None) \
        or globals().get("_vbox_proxy_url", "") or ""
    return {"http": u, "https": u} if u else {}


def _vbox_host(sp, default=""):
    hs = _vbox_cfg(sp, "_vbox_effective_hosts", None)
    if isinstance(hs, list) and hs:
        try:
            return str(hs[0]).rstrip("/")
        except Exception:
            pass
    return default


def _vbox_opener(sp=None):
    """带 SSL 放行 + 客户端代理 的 opener。"""
    handlers = [urllib.request.ProxyHandler(_vbox_proxy(sp))]
    if _SSL_CTX is not None:
        handlers.append(urllib.request.HTTPSHandler(context=_SSL_CTX))
    return urllib.request.build_opener(*handlers)


UA = ("Mozilla/5.0 (Linux; Android 12; SM-G998B) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/120.0.0.0 Mobile Safari/537.36")


# ============================================================ 解码器
def hj64decode(text):
    """自定义字母表 base64 解码（表外字符忽略）。"""
    buf = 0
    bits = 0
    out = bytearray()
    for ch in text:
        v = _IDX64.get(ch)
        if v is None:
            continue
        buf = (buf << 6) | v
        bits += 6
        if bits >= 8:
            bits -= 8
            out.append((buf >> bits) & 0xFF)
    return bytes(out)


def decode_img_bytes(raw):
    """把 /hjstore/images/**.jpg.txt 的正文还原成图片二进制。

    链路：自定义字母表 base64 → "data:image/jpeg;base64,XXXX" → 标准 base64
    兼容：万一远端已改成明文 data URI 或裸图片，直接原样返回。
    """
    if not raw:
        return b""
    if raw[:3] == b"\xff\xd8\xff" or raw[:4] == b"\x89PNG":
        return raw
    try:
        inner = hj64decode(raw.decode("latin-1")).decode("latin-1")
    except Exception:
        return b""
    if inner.startswith("data:"):
        _, _, b64 = inner.partition(",")
    elif inner[:2] == "/9":
        b64 = inner
    else:
        return b""
    b64 = b64.strip()
    b64 += "=" * ((4 - len(b64) % 4) % 4)
    try:
        return base64.b64decode(b64, validate=False)
    except Exception:
        return b""


# ============================================================ 主体
class Spider(SpiderBase):
    MODULE = "hjsq"

    def __init__(self):
        self.base = BASE_DEFAULT
        self.uid = USER_ID_DEFAULT
        self.token = TOKEN_DEFAULT
        # 客户端受控代理：端口 18080，参数是 key?platformKey（v7 起），不是 type=hjsq/9978
        try:
            self.proxy_base = self.getProxyUrl() + "&url="
        except Exception:
            self.proxy_base = "http://127.0.0.1:18080/proxy?do=py&key=hjsq_py&url="
        self.pic_mode = "proxy"        # proxy | raw | none
        self.timeout = 20
        self._nodes = None
        self._nodes_ts = 0

    # ---------------- 生命周期 ----------------
    def getName(self):
        return "海角社区"

    def getDependence(self):
        return []

    def init(self, extend=""):
        cfg = {}
        if extend:
            try:
                cfg = json.loads(extend) if isinstance(extend, str) else dict(extend)
            except Exception:
                cfg = {}
        self.base = (cfg.get("host") or cfg.get("base") or BASE_DEFAULT).rstrip("/")
        self.uid = str(cfg.get("user_id") or USER_ID_DEFAULT)
        self.token = cfg.get("token") or TOKEN_DEFAULT
        self.pic_mode = cfg.get("pic") or "proxy"
        if cfg.get("proxy_base"):
            self.proxy_base = cfg["proxy_base"]
        try:
            self.timeout = int(cfg.get("timeout") or 20)
        except Exception:
            self.timeout = 20
        # 客户端注入的自定义域名优先于脚本内置默认值
        try:
            _inj = _vbox_host(self, "")
            if _inj:
                for _attr in ("base", "host"):
                    if hasattr(self, _inj if False else _attr):
                        setattr(self, _attr, _inj)
                _core = getattr(self, "_core", None)
                if _core is not None:
                    for _attr in ("base", "host"):
                        if hasattr(_core, _attr):
                            setattr(_core, _attr, _inj)
        except Exception:
            pass

        return None

    def destroy(self):
        return None

    def isVideoFormat(self, url):
        u = (url or "").lower()
        return any(u.split("?")[0].endswith(x) for x in
                   (".m3u8", ".mp4", ".ts", ".flv", ".mkv"))

    def manualVideoCheck(self):
        return False

    def liveContent(self):
        return ""

    def action(self, action):
        return {"msg": "海角社区 · 节点 %s" % self.base}

    # ---------------- HTTP ----------------
    def _headers(self, extra=None):
        h = {
            "X-User-Id": self.uid,
            "X-User-Token": self.token,
            "User-Agent": UA,
            "Accept": "application/json, text/plain, */*",
            "Referer": self.base + "/",
        }
        if extra:
            h.update(extra)
        return h

    def _open(self, req, timeout=None):
        t = timeout if timeout is not None else getattr(self, "timeout", 20)
        return _vbox_opener(getattr(self, "sp", None)).open(req, timeout=t)

    def _get(self, path, qp=None):
        url = path if path.startswith("http") else self.base + "/" + path.lstrip("/")
        if qp:
            clean = {k: v for k, v in qp.items() if v is not None and v != ""}
            if clean:
                url += ("&" if "?" in url else "?") + urllib.parse.urlencode(clean)
        req = urllib.request.Request(url, headers=self._headers())
        try:
            with self._open(req) as r:
                raw = r.read()
        except urllib.error.HTTPError as e:
            return {"errorCode": -1, "message": "HTTP %s" % e.code, "data": None}
        except Exception as e:
            return {"errorCode": -1, "message": "%s: %s" % (type(e).__name__, e), "data": None}
        if raw[:2] == b"\x1f\x8b":
            import gzip
            try:
                raw = gzip.decompress(raw)
            except Exception:
                pass
        try:
            return json.loads(raw.decode("utf-8", "replace"))
        except Exception:
            return {"errorCode": -1, "message": "非 JSON 响应", "data": None}

    def _post(self, path, body):
        url = path if path.startswith("http") else self.base + "/" + path.lstrip("/")
        data = json.dumps(body, ensure_ascii=False).encode("utf-8")
        req = urllib.request.Request(
            url, data=data, headers=self._headers({"Content-Type": "application/json; charset=utf-8"}),
            method="POST")
        try:
            with self._open(req) as r:
                return json.loads(r.read().decode("utf-8", "replace"))
        except Exception as e:
            return {"errorCode": -1, "message": str(e), "data": None}

    def _fetch_bytes(self, url):
        if url.startswith("//"):
            url = "http:" + url
        req = urllib.request.Request(url, headers={
            "User-Agent": UA, "Referer": self.base + "/"})
        with self._open(req) as r:
            return r.read()

    # ---------------- 节点树 ----------------
    def _load_nodes(self, force=False):
        now = time.time()
        if self._nodes is not None and not force and (now - self._nodes_ts) < 1800:
            return self._nodes
        j = self._get("api2/topic/nodes")
        nodes = j.get("data") if j.get("errorCode") == 0 else None
        self._nodes = nodes or []
        self._nodes_ts = now
        return self._nodes

    # ---------------- 图片地址 ----------------
    def _pic(self, txt_url):
        """.jpg.txt 是加密容器，客户端直连渲染不了 → 走本地代理实时解码。"""
        if not txt_url:
            return ""
        if self.pic_mode == "none" or not txt_url.endswith(".txt"):
            return txt_url if self.pic_mode != "none" else ""
        if self.pic_mode == "raw":
            return txt_url
        return self.proxy_base + urllib.parse.quote(txt_url, safe="")

    def _video_url(self, att):
        u = (att.get("remoteUrl") or "").strip()
        if not u:
            return ""
        if u.startswith("//"):
            u = "http:" + u
        return u

    # ---------------- 首页 ----------------
    def homeContent(self, filter):
        classes = [{"type_id": k, "type_name": n} for k, n in SPECIAL_GROUPS]
        filters = {}
        nodes = self._load_nodes()
        tops = [n for n in nodes if int(n.get("parentId") or 0) == 0]

        for n in tops:
            nid = str(n.get("nodeId"))
            classes.append({"type_id": nid, "type_name": n.get("name") or ("节点" + nid)})
            kids = [c for c in nodes if int(c.get("parentId") or 0) == int(n.get("nodeId") or -1)]
            if kids:
                vals = [{"n": "全部", "v": nid}]
                vals += [{"n": c.get("name") or str(c.get("nodeId")),
                          "v": str(c.get("nodeId"))} for c in kids]
                filters[nid] = [{"key": "node", "name": "子版块",
                                 "value": [{"n": v["n"], "v": v["v"]} for v in vals]}]

        # 未挂到父节点的孤立节点也放出来，避免漏内容
        listed = set()
        for n in nodes:
            pid = int(n.get("parentId") or 0)
            if pid == 0 or any(int(t.get("nodeId") or -2) == pid for t in tops):
                listed.add(str(n.get("nodeId")))
        for n in nodes:
            nid = str(n.get("nodeId"))
            if nid not in listed:
                classes.append({"type_id": nid, "type_name": n.get("name") or ("节点" + nid)})

        return {"class": classes, "filters": filters if filter else {}}

    def homeVideoContent(self):
        return {"list": []}

    # ---------------- 列表 ----------------
    def _item(self, t):
        pic = ""
        node = t.get("node") or {}
        for att in (t.get("attachments") or []):
            if (att.get("category") or "") == "images":
                pic = self._pic(att.get("remoteUrl") or "")
                break
        if not pic:
            for c in (t.get("content") or []):
                if c.get("imgUrl"):
                    pic = self._pic(c["imgUrl"])
                    break
        if not pic:
            pic = node.get("icon") or ""

        remarks = []
        if t.get("hasVideo"):
            remarks.append("视频")
        if int(t.get("money_type") or 0) > 0:
            remarks.append("付费")
        if t.get("viewCount"):
            remarks.append("%s 浏览" % t.get("viewCount"))
        if node.get("name"):
            remarks.append(str(node.get("name")))

        return {
            "vod_id": str(t.get("topicId")),
            "vod_name": (t.get("title") or "").strip() or "无标题",
            "vod_pic": pic,
            "vod_remarks": " · ".join(remarks),
            "vod_tag": "video" if t.get("hasVideo") else "pic",
            "style": {"type": "rect", "ratio": 0.75},
        }

    def categoryContent(self, tid, pg, filter, extend):
        tid = str(tid or "").strip()
        try:
            page = int(pg)
        except Exception:
            page = 1
        extend = extend if isinstance(extend, dict) else {}
        node_override = extend.get("node")

        if tid == "hot":
            j = self._get("api2/topic/hot/topics", {"page": page})
        elif tid == "news":
            j = self._get("api2/topic/node/news", {"page": page})
        elif tid in _TYPE_MAP:
            j = self._get("api2/topic/node/topics", {"page": page, "type": _TYPE_MAP[tid]})
        else:
            nid = node_override or tid
            j = self._get("api2/topic/node/topics",
                          {"page": page, "nodeId": nid, "type": 0})

        data = j.get("data") or {}
        results = data.get("results") or []
        pageinfo = data.get("page") or {}
        total = pageinfo.get("total") or 0
        limit = pageinfo.get("limit") or 20

        lst = [self._item(t) for t in results if t.get("topicId")]
        pagecount = max(1, (int(total) + int(limit) - 1) // int(limit)) if total else (page if lst else 1)
        return {
            "page": page,
            "pagecount": min(pagecount, 9999),
            "limit": limit,
            "total": total,
            "list": lst,
        }

    # ---------------- 详情 ----------------
    def detailContent(self, ids):
        tid = ids[0] if isinstance(ids, (list, tuple)) else ids
        tid = str(tid).strip().rstrip("/").split("/")[-1]
        j = self._get("api2/topic/%s" % tid)
        d = j.get("data") or {}
        if not d:
            return {"list": []}

        title = (d.get("title") or "").strip() or "海角帖 #%s" % tid

        # 正文
        texts = []
        for c in (d.get("content") or []):
            tx = (c.get("text") or "").strip()
            if tx:
                texts.append(tx)
        body = "\n".join(texts)[:600]

        # 资源
        imgs, vids = [], []
        for att in (d.get("attachments") or []):
            cat = att.get("category") or ""
            u = att.get("remoteUrl") or ""
            if cat == "images":
                imgs.append((att.get("id"), u))
            elif cat == "video":
                vids.append(att)

        # 封面
        cover = ""
        if imgs:
            cover = self._pic(imgs[0][1])
        if not cover:
            for c in (d.get("content") or []):
                if c.get("imgUrl"):
                    cover = self._pic(c["imgUrl"])
                    break
        if not cover:
            cover = (d.get("node") or {}).get("icon") or ""

        # 播放/资源列表
        plays = []
        for v in vids:
            u = self._video_url(v)
            if not u:
                continue
            dur = v.get("video_time_length") or 0
            label = "正片"
            if dur:
                try:
                    sec = int(dur)
                    label = "正片 %d:%02d" % (sec // 60, sec % 60)
                except Exception:
                    pass
            plays.append("%s$%s" % (label, u))
        if not plays and imgs:
            # 纯图帖：把图片作为可播资源，走本地代理解码
            for i, (aid, u) in enumerate(imgs[:20], 1):
                plays.append("图%d$%s" % (i, self._pic(u)))

        # 描述
        meta = []
        node = d.get("node") or {}
        if node.get("name"):
            meta.append("版块：%s" % node.get("name"))
        if d.get("viewCount"):
            meta.append("浏览：%s" % d.get("viewCount"))
        if d.get("likeCount"):
            meta.append("点赞：%s" % d.get("likeCount"))
        if d.get("createTime"):
            meta.append("发布：%s" % d.get("createTime"))
        tags = [t.get("tagName") for t in (d.get("tags") or []) if t.get("tagName")]
        if tags:
            meta.append("标签：%s" % " / ".join(tags))
        if int(d.get("money_type") or 0) > 0:
            meta.append("⚠ 该帖为付费内容，直链可能仅为预览片段")
        doors = d.get("doors") or []
        if doors:
            meta.append("付费门：%d 个" % len(doors))
        if imgs:
            meta.append("图片：%d 张" % len(imgs))
        if vids:
            meta.append("视频：%d 个" % len(vids))
        if d.get("is_original"):
            meta.append("原创")
        if d.get("is_cream"):
            meta.append("精华")

        desc = "\n".join(meta)
        if body:
            desc += "\n" + "─" * 18 + "\n" + body
        desc = desc.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")

        return {
            "list": [{
                "vod_id": tid,
                "vod_name": title,
                "vod_pic": cover,
                "vod_year": (d.get("createTime") or "")[:4],
                "vod_area": "海角社区",
                "vod_remarks": "视频帖" if vids else ("图帖 %d 张" % len(imgs) if imgs else "帖子"),
                "vod_content": desc,
                "vod_play_from": "海角直链",
                "vod_play_url": "#".join(plays),
            }]
        }

    # ---------------- 播放 ----------------
    def playerContent(self, flag, id, vipFlags):
        url = str(id or "").strip()
        # 图帖走本地代理解码后输出
        if url.startswith(self.proxy_base):
            return {"parse": 0, "url": url, "header": {"User-Agent": UA}}
        return {
            "parse": 0,
            "url": url,
            "header": {"User-Agent": UA, "Referer": self.base + "/"},
        }

    # ---------------- 搜索 ----------------
    def searchContent(self, key, quick, pg="1"):
        kw = str(key or "").strip()
        if not kw:
            return {"page": 1, "pagecount": 1, "limit": 20, "total": 0, "list": []}
        try:
            page = int(pg)
        except Exception:
            page = 1
        j = self._get("api2/topic/search", {"node_id": 0, "keyword": kw})
        data = j.get("data")
        if isinstance(data, dict):
            results = data.get("results") or []
        elif isinstance(data, list):
            results = data
        else:
            results = []

        lst = [self._item(t) for t in results if isinstance(t, dict) and t.get("topicId")]
        # 搜索接口不分页：本地切片，第二页起返回空，避免客户端无限翻页
        limit = 20
        if page > 1:
            lst = []
        return {
            "page": page,
            "pagecount": 1,
            "limit": limit,
            "total": len(lst),
            "list": lst,
        }

    # ---------------- 本地代理：图片实时解码 ----------------
    def localProxy(self, param):
        p = param or {}
        if isinstance(p, str):
            p = dict(urllib.parse.parse_qsl(p.lstrip("?")))
        target = p.get("url") or p.get("u") or ""
        if not target:
            return [400, "text/plain; charset=utf-8", b"missing url", {}]
        if target.startswith("//"):
            target = "http:" + target
        try:
            raw = self._fetch_bytes(target)
            img = decode_img_bytes(raw)
            if not img:
                return [502, "text/plain; charset=utf-8", b"decode failed", {}]
            if img[:3] == b"\xff\xd8\xff":
                ctype = "image/jpeg"
            elif img[:4] == b"\x89PNG":
                ctype = "image/png"
            elif img[:4] == b"GIF8":
                ctype = "image/gif"
            else:
                ctype = "application/octet-stream"
            return [200, ctype, img, {"Cache-Control": "max-age=86400"}]
        except Exception as e:
            return [500, "text/plain; charset=utf-8", str(e).encode("utf-8"), {}]
