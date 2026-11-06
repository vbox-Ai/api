#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""看片视频（kpsp）— vbox 自包含适配器

协议来源：libapp.so blutter 反汇编（package:avbox/module/kpsp/*）
────────────────────────────────────────────────────────────
响应加密（CryptoUtil::ksSpDecrypt @0x8f2484）
    响应体为 {"x-data": "<密文>"}，密文是 Fernet 结构：
        base64url → bytes：version(1B) + timestamp(8B) + IV(16B) + ciphertext + HMAC-SHA256(32B)
    客户端只取 IV 和密文，跳过 HMAC 校验：
        hex = base64url_decode(x-data) 转 hex
        iv  = hex[18:50]                 # 9 字节头之后 16 字节
        ct  = hex[50 : len-64]           # 去掉尾部 32 字节 HMAC
        AES-128-CBC(key=7af630c7e06ccecfa70d5a085f189c06)
    图片走 CryptoUtil::ksSpDecryptImg（split("@@@") 后同法解密再按 ',' 取 [1]）；
    但 /hjstore 那类 .image 资源实测可直接取，无需解密。

接口（信封 {"code":0,"data":{...}}，已解密后）
    GET api/vod/video          列表   qp: page / per_page(≤100) / site_id / tag
    GET api/vod/video/{id}     详情
    GET api/vod/tag            标签   qp: page / per_page（全站 6628 个）
    GET search/vod             搜索   qp: search / page / per_page / site_id

资源
    MEDIA = https://hm-img.hdstfb.com   （splash 的 kpsp_media）
    播放   MEDIA + play_url            → HLS m3u8 + AES-128，enc.key 同目录可取
    下载   MEDIA + down_url            → mp4
    封面   MEDIA + pic                 → .image（实为普通图片，直取 200）

坑位
    tag 过滤必须传 **tag id**，传中文名会被忽略（返回全站基线数据）
"""

import base64
import binascii
import json
import os
import sys
import time
import urllib.error
import urllib.parse
import urllib.parse
import urllib.request

try:
    from base.spider import Spider as SpiderBase
except ImportError:
    class SpiderBase(object):
        def getCache(self, key):
            return None

        def setCache(self, key, value):
            return "fail"

        def delCache(self, key):
            return "fail"


# ============================================================ 常量
BASE_DEFAULT = "https://sm-api.wieuc.com"
MEDIA_DEFAULT = "https://hm-img.hdstfb.com"
AES_KEY_HEX = "7af630c7e06ccecfa70d5a085f189c06"
HDR_LEN = 18          # hex 长度：version(1) + timestamp(8) = 9 字节
IV_LEN = 32           # hex 长度：16 字节
MAC_LEN = 64          # hex 长度：32 字节

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

# 常用分类（tag id 已通过 api/vod/tag 全量索引核对）
COMMON_TAGS = [
    ("", "最新"),
    ("2194", "热门"),
    ("2294", "推荐"),
    ("1534", "精品"),
    ("295", "网黄"),
    ("431", "探花"),
    ("1527", "传媒"),
    ("2124", "吃瓜"),
    ("524", "直播"),
    ("30", "乱伦"),
    ("351", "自拍"),
    ("407", "偷拍"),
    ("2387", "私拍"),
    ("2845", "换脸"),
    ("1862", "泄密"),
    ("2196", "三级"),
    ("296", "动漫"),
    ("293", "欧美"),
    ("300", "国产"),
    ("95", "无码"),
    ("68", "中文字幕"),
    ("123", "萝莉"),
    ("121", "御姐"),
    ("87", "制服"),
]


# ============================================================ AES（三档后端，兼容 vbox 运行时）
def _aes_cbc(key, iv, data, encrypt=False):
    try:
        from Crypto.Cipher import AES as _A
        from Crypto.Util.Padding import pad as _p, unpad as _up
        if encrypt:
            return _A.new(key, _A.MODE_CBC, iv).encrypt(_p(data, 16))
        raw = _A.new(key, _A.MODE_CBC, iv).decrypt(data)
        try:
            return _up(raw, 16)
        except Exception:
            return raw
    except ImportError:
        pass
    try:
        from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
        c = Cipher(algorithms.AES(key), modes.CBC(iv))
        if encrypt:
            e = c.encryptor()
            return e.update(data) + e.finalize()
        d = c.decryptor()
        raw = d.update(data) + d.finalize()
        if raw and 1 <= raw[-1] <= 16:
            raw = raw[:-raw[-1]]
        return raw
    except ImportError:
        pass
    import pyaes
    m = pyaes.AESModeOfOperationCBC(key, iv=iv)
    if encrypt:
        return b"".join(m.encrypt(data[i:i + 16]) for i in range(0, len(data), 16))
    raw = b"".join(m.decrypt(data[i:i + 16]) for i in range(0, len(data), 16))
    if raw and 1 <= raw[-1] <= 16:
        raw = raw[:-raw[-1]]
    return raw


def b64url_to_hex(s):
    """CryptoUtil::_decode64ToHex —— '-'→'+'、'_'→'/'，补 '=' 后解码再转 hex。"""
    s = s.replace("-", "+").replace("_", "/").strip()
    s += "=" * ((4 - len(s) % 4) % 4)
    return binascii.hexlify(base64.b64decode(s, validate=False)).decode()


def decrypt_xdata(xdata):
    """ksSpDecrypt —— 按 Fernet 结构取 IV/密文做 AES-128-CBC。"""
    h = b64url_to_hex(xdata)
    if len(h) < HDR_LEN + IV_LEN + MAC_LEN + 32:
        raise ValueError("x-data 长度异常: %d" % len(h))
    iv = bytes.fromhex(h[HDR_LEN:HDR_LEN + IV_LEN])
    ct = bytes.fromhex(h[HDR_LEN + IV_LEN:len(h) - MAC_LEN])
    return _aes_cbc(bytes.fromhex(AES_KEY_HEX), iv, ct, encrypt=False)


# ============================================================ 主体
class Spider(SpiderBase):
    MODULE = "kpsp"

    def __init__(self):
        self.base = BASE_DEFAULT
        self.media = MEDIA_DEFAULT
        self.site_id = 1
        self.per_page = 20
        self.timeout = 20

    # ---------------- 生命周期 ----------------
    def getName(self):
        return "看片视频"

    def getDependence(self):
        return []

    def init(self, extend=""):
        cfg = {}
        if extend:
            try:
                cfg = json.loads(extend) if isinstance(extend, str) else dict(extend)
            except Exception:
                cfg = {}
        self.base = (cfg.get("host") or BASE_DEFAULT).rstrip("/")
        self.media = (cfg.get("media") or MEDIA_DEFAULT).rstrip("/")
        try:
            self.site_id = int(cfg.get("site_id") or 1)
        except Exception:
            self.site_id = 1
        try:
            self.per_page = int(cfg.get("per_page") or 20)
        except Exception:
            self.per_page = 20
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
        return u.split("?")[0].endswith((".m3u8", ".mp4", ".ts", ".flv", ".mkv"))

    def manualVideoCheck(self):
        return False

    def liveContent(self):
        return ""

    def action(self, action):
        return {"msg": "看片视频 · %s" % self.base}

    # ---------------- HTTP ----------------
    def _headers(self):
        return {
            "User-Agent": UA,
            "Accept": "application/json, text/plain, */*",
            "Referer": self.base + "/",
        }

    def _open(self, req, timeout=None):
        t = timeout if timeout is not None else getattr(self, "timeout", 20)
        return _vbox_opener(getattr(self, "sp", None)).open(req, timeout=t)

    def _raw_get(self, path, qp=None):
        url = path if path.startswith("http") else self.base + "/" + path.lstrip("/")
        if qp:
            clean = {k: v for k, v in qp.items() if v is not None and v != ""}
            if clean:
                url += ("&" if "?" in url else "?") + urllib.parse.urlencode(clean)
        req = urllib.request.Request(url, headers=self._headers())
        try:
            with self._open(req) as r:
                return r.read()
        except urllib.error.HTTPError as e:
            raise RuntimeError("HTTP %s @ %s" % (e.code, url))
        except Exception as e:
            raise RuntimeError("%s: %s" % (type(e).__name__, e))

    def _get(self, path, qp=None):
        """自动解密 envelope，返回解密后的 dict。"""
        body = self._raw_get(path, qp)
        try:
            wrap = json.loads(body.decode("utf-8", "replace"))
        except Exception:
            raise RuntimeError("响应非 JSON: %s" % body[:80])
        if not isinstance(wrap, dict):
            raise RuntimeError("响应非 dict")
        xd = wrap.get("x-data") or wrap.get("xData")
        if isinstance(xd, str):
            plain = decrypt_xdata(xd)
            return json.loads(plain.decode("utf-8", "replace"))
        # 少数端点可能不加密
        return wrap

    def _abs_media(self, p):
        p = (p or "").strip()
        if not p:
            return ""
        if p.startswith("//"):
            return "https:" + p
        if p.startswith("http"):
            return p
        return self.media + ("" if p.startswith("/") else "/") + p

    # ---------------- 工具 ----------------
    @staticmethod
    def _dur(sec):
        try:
            s = int(sec)
        except Exception:
            return ""
        if s <= 0:
            return ""
        h, rem = divmod(s, 3600)
        m, ss = divmod(rem, 60)
        return ("%d:%02d:%02d" % (h, m, ss)) if h else ("%d:%02d" % (m, ss))

    def _item(self, it):
        tags = [t.get("name") for t in (it.get("tag") or []) if t.get("name")]
        remarks = []
        d = self._dur(it.get("duration"))
        if d:
            remarks.append(d)
        if int(it.get("is_paid") or 0) == 1:
            remarks.append("付费")
        if it.get("hits"):
            remarks.append("%s 播放" % it.get("hits"))
        if tags:
            remarks.append("/".join(tags[:2]))
        return {
            "vod_id": str(it.get("id")),
            "vod_name": (it.get("name") or "").strip() or "无标题",
            "vod_pic": self._px(self._abs_media(it.get("pic") or it.get("preview_url"))),
            "vod_remarks": " · ".join(remarks),
            "style": {"type": "rect", "ratio": 0.75},
        }

    # ---------------- 首页 ----------------
    def homeContent(self, filter):
        classes = [{"type_id": tid or "all", "type_name": nm} for tid, nm in COMMON_TAGS]
        # 动态补充官方标签（失败不影响主流程）
        try:
            j = self._get("api/vod/tag", {"page": 1, "per_page": 60})
            dd = j.get("data") or {}
            items = dd.get("items") if isinstance(dd, dict) else dd
            exist = {nm for _, nm in COMMON_TAGS}
            for it in (items or []):
                tid = it.get("id")
                nm = (it.get("name") or "").strip()
                if tid is None or not nm or nm in exist:
                    continue
                exist.add(nm)
                classes.append({"type_id": str(tid), "type_name": nm})
                if len(classes) >= 90:
                    break
        except Exception:
            pass
        return {"class": classes, "filters": {}}

    def homeVideoContent(self):
        try:
            r = self.categoryContent("all", "1", False, {})
            return {"list": r.get("list") or []}
        except Exception:
            return {"list": []}

    # ---------------- 列表 ----------------
    def categoryContent(self, tid, pg, filter, extend):
        tid = str(tid or "").strip()
        try:
            page = int(pg)
        except Exception:
            page = 1
        extend = extend if isinstance(extend, dict) else {}
        tag = extend.get("tag") or ("" if tid in ("", "all") else tid)

        qp = {"page": page, "per_page": self.per_page, "site_id": self.site_id}
        if tag:
            qp["tag"] = tag

        try:
            j = self._get("api/vod/video", qp)
        except Exception:
            return {"page": page, "pagecount": page, "limit": self.per_page,
                    "total": 0, "list": []}

        d = j.get("data") or {}
        items = d.get("items") or []
        total = d.get("total") or 0
        pages = d.get("pages") or 0
        return {
            "page": page,
            "pagecount": min(int(pages) or page, 9999),
            "limit": d.get("per_page") or self.per_page,
            "total": total,
            "list": [self._item(it) for it in items if it.get("id")],
        }

    # ---------------- 详情 ----------------
    def detailContent(self, ids):
        vid = ids[0] if isinstance(ids, (list, tuple)) else ids
        vid = str(vid).strip().rstrip("/").split("/")[-1]
        try:
            j = self._get("api/vod/video/%s" % vid)
        except Exception:
            return {"list": []}
        d = j.get("data") or {}
        if not d:
            return {"list": []}

        title = (d.get("name") or "").strip() or ("看片 #%s" % vid)
        cover = self._abs_media(d.get("pic") or d.get("preview_url"))

        plays = []
        pu = d.get("play_url")
        if pu:
            plays.append("正片$%s" % self._abs_media(pu))
        ppu = d.get("preview_play_url")
        if ppu and ppu != pu:
            plays.append("预览$%s" % self._abs_media(ppu))
        du = d.get("down_url")
        if du and not plays:
            plays.append("正片$%s" % self._abs_media(du))
        if not plays and du:
            plays.append("下载$%s" % self._abs_media(du))

        meta = []
        dur = self._dur(d.get("duration"))
        if dur:
            meta.append("时长：%s" % dur)
        if d.get("pubdate"):
            meta.append("发布：%s" % d.get("pubdate"))
        if d.get("hits"):
            meta.append("播放：%s" % d.get("hits"))
        if d.get("score"):
            meta.append("评分：%s" % d.get("score"))
        if int(d.get("is_paid") or 0) == 1:
            meta.append("⚠ 付费内容（%s）" % (d.get("price") or "?"))
        tags = [t.get("name") for t in (d.get("tag") or []) if t.get("name")]
        if tags:
            meta.append("标签：%s" % " / ".join(tags))
        if d.get("created_user_name"):
            meta.append("来源：%s" % d.get("created_user_name"))

        desc = "\n".join(meta)
        body = (d.get("description") or "").strip()
        if body:
            desc += "\n" + "─" * 18 + "\n" + body
        desc = desc.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")

        return {
            "list": [{
                "vod_id": vid,
                "vod_name": title,
                "vod_pic": self._px(cover),
                "vod_year": (d.get("pubdate") or "")[:4],
                "vod_area": "看片视频",
                "vod_remarks": dur or ("付费" if int(d.get("is_paid") or 0) == 1 else "高清"),
                "vod_content": desc,
                "vod_play_from": "看片直链",
                "vod_play_url": "#".join(plays),
            }]
        }

    # ---------------- 播放 ----------------
    def playerContent(self, flag, id, vipFlags):
        return {
            "parse": 0,
            "url": str(id or "").strip(),
            "header": {"User-Agent": UA, "Referer": self.media + "/"},
        }

    # ---------------- 搜索 ----------------
    def searchContent(self, key, quick, pg="1"):
        kw = str(key or "").strip()
        if not kw:
            return {"page": 1, "pagecount": 1, "limit": self.per_page, "total": 0, "list": []}
        try:
            page = int(pg)
        except Exception:
            page = 1
        try:
            j = self._get("search/vod", {"search": kw, "page": page,
                                         "per_page": self.per_page, "site_id": self.site_id})
        except Exception:
            return {"page": page, "pagecount": page, "limit": self.per_page,
                    "total": 0, "list": []}
        d = j.get("data") or {}
        items = d.get("items") or []
        return {
            "page": page,
            "pagecount": min(int(d.get("pages") or page), 9999),
            "limit": d.get("per_page") or self.per_page,
            "total": d.get("total") or 0,
            "list": [self._item(it) for it in items if it.get("id")],
        }


    # ---------------- 封面走客户端本地代理 ----------------
    def _px(self, url):
        u = (url or "").strip()
        if not u:
            return ""
        if u.startswith("//"):
            u = "https:" + u
        if not u.startswith("http"):
            return u
        base = ""
        try:
            base = self.getProxyUrl()
        except Exception:
            base = ""
        if not base:
            base = "http://127.0.0.1:18080/proxy?do=py&key=%s" % getattr(self, "MODULE", "kpsp")
        # Flutter 客户端没有实现 /proxy?do=py 路由（只有 iOS 有），代理 URL 在 App 内必 404
        return u

    # ---------------- 本地代理（媒体/封面直取） ----------------
    def localProxy(self, param):
        p = param or {}
        if isinstance(p, str):
            p = dict(urllib.parse.parse_qsl(p.lstrip("?")))
        target = p.get("url") or p.get("u") or ""
        if not target:
            return [400, "text/plain; charset=utf-8", b"missing url", {}]
        try:
            req = urllib.request.Request(target, headers={
                "User-Agent": UA, "Referer": self.media + "/"})
            with self._open(req) as r:
                raw = r.read()
                ct = (r.headers.get("Content-Type") or "").lower()
                if raw[:3] == b"\xff\xd8\xff":
                    ct = "image/jpeg"
                elif raw[:8] == b"\x89PNG\r\n\x1a\n":
                    ct = "image/png"
                elif raw[:4] == b"GIF8":
                    ct = "image/gif"
                elif raw[:4] == b"RIFF" and raw[8:12] == b"WEBP":
                    ct = "image/webp"
                elif not ct.startswith(("image/", "video/", "application/vnd.apple")):
                    ct = "image/jpeg"
                return [200, ct, raw, {"Cache-Control": "max-age=86400"}]
        except Exception as e:
            return [500, "text/plain; charset=utf-8", str(e).encode("utf-8"), {}]
