# -*- coding: utf-8 -*-
"""
暮色（com.look.avbox / avbox）后端聚合 Spider — vbox 福利区适配版
================================================================
来源：逆向 app-暮色-1.0.1(开发模式安装).ipa
  · Payload/Runner.app 为 Flutter AOT（libapp 内嵌 37 个资源模块）
  · App 为薄客户端，所有平台数据统一走自建 Swoft 后端 api.* 域
  · 鉴权：X-Auth-Key / X-Auth-TimeStamp / X-Auth-Nonce / X-Auth-Sign 四件套
  · 后端错误统一返回 {"code":500,"message":"系统繁忙，请稍后重试","data":null}

本脚本做三件事：
  1) 内置 IPA 里提取到的后端域名池 + 37 模块 → 接口路由表
  2) 用四件套签名访问后端，把返回映射成 vbox 的 分类/列表/详情/播放 结构
  3) 签名算法/密钥可通过 extend 注入，不写死在代码里

extend 示例：
  {"host": "https://api.3459381.com", "key": "368480924a6c78e2e8681551a7cf4c21",
   "secret": "", "signMode": "md5_k_t_n", "timeout": 15}
"""
import sys
import json
import time
import ssl
import base64
import hashlib
import hmac
import urllib.parse
import urllib.request
import urllib.error
import random

sys.path.append('..')
try:
    from base.spider import Spider as _B
except Exception:
    class _B(object):
        pass

# ============================================================ 常量
UA = ('Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) AppleWebKit/605.1.15 '
      '(KHTML, like Gecko) Version/17.0 Mobile/15E148 Safari/604.1')

APP_KEY = "368480924a6c78e2e8681551a7cf4c21"      # IPA 内 &X-Auth-Key= 常量
DEFAULT_HOSTS = [
    "https://api.3459381.com",
    "https://api.c6dd5cc.com",
    "https://api.61c76a0.com",
    "https://api.87735d5.com",
    "https://api.em1oifd0.com",
    "https://api.6b18726.com",
    "https://api.7d87e17.com",
    "https://api.b3d530f.com",
    "https://api.b7f3192.com",
    "https://api.c9wgdr.com",
    "https://api.he0jys.com",
]

# 37 个资源模块（IPA: package:avbox/module/<key>/...）
MODULES = [
    {"key": "av91",   "name": "91AV",       "cat": "video", "icon": "play.rectangle.fill"},
    {"key": "pron91", "name": "91Pron",     "cat": "video", "icon": "play.rectangle.fill"},
    {"key": "sp91",   "name": "91视频",      "cat": "video", "icon": "play.rectangle.fill"},
    {"key": "4hu",    "name": "四虎影库",     "cat": "video", "icon": "film.fill"},
    {"key": "cg51",   "name": "51吃瓜",      "cat": "video", "icon": "eye.fill"},
    {"key": "missav", "name": "MissAV",     "cat": "video", "icon": "film.fill"},
    {"key": "javdb",  "name": "JavDB",      "cat": "video", "icon": "film.fill"},
    {"key": "aijav",  "name": "AIJAV",      "cat": "video", "icon": "sparkles"},
    {"key": "mmav",   "name": "猫咪AV",      "cat": "video", "icon": "film.fill"},
    {"key": "one",    "name": "One",        "cat": "video", "icon": "play.circle.fill"},
    {"key": "box",    "name": "资源盒",       "cat": "video", "icon": "shippingbox.fill"},
    {"key": "hjsq",   "name": "海角社区",     "cat": "video", "icon": "bubble.left.and.bubble.right.fill"},
    {"key": "cgw",    "name": "吃瓜网",       "cat": "video", "icon": "eye.fill"},
    {"key": "hxsp",   "name": "红杏视频",     "cat": "video", "icon": "flame.fill"},
    {"key": "hgsp",   "name": "黄瓜视频",     "cat": "video", "icon": "leaf.fill"},
    {"key": "hsck",   "name": "黄色仓库",     "cat": "video", "icon": "archivebox.fill"},
    {"key": "qysq",   "name": "青衣社区",     "cat": "video", "icon": "person.3.fill"},
    {"key": "hdb",    "name": "红豆包",       "cat": "video", "icon": "film.fill"},
    {"key": "kpsp",   "name": "快片视频",     "cat": "video", "icon": "play.rectangle.fill"},
    {"key": "lclf",   "name": "楼风",         "cat": "video", "icon": "location.fill"},
    {"key": "ltb",    "name": "Ltb",         "cat": "video", "icon": "film.fill"},
    {"key": "lxs",    "name": "撸先生",       "cat": "video", "icon": "flame.fill"},
    {"key": "mdtv",   "name": "美杜莎TV",     "cat": "video", "icon": "tv.fill"},
    {"key": "rryy",   "name": "日日影院",     "cat": "video", "icon": "film.fill"},
    {"key": "zlt",    "name": "Zlt",         "cat": "video", "icon": "film.fill"},
    {"key": "insav",  "name": "InSav",       "cat": "video", "icon": "photo.fill"},
    {"key": "djr",    "name": "DJR",         "cat": "video", "icon": "music.note"},
    {"key": "fl2",    "name": "FL2",         "cat": "video", "icon": "film.fill"},
    {"key": "txvlog", "name": "糖心Vlog",     "cat": "video", "icon": "video.fill"},
    {"key": "km",     "name": "看美",         "cat": "video", "icon": "eye.fill"},
    {"key": "live",   "name": "直播",         "cat": "live",  "icon": "antenna.radiowaves.left.and.right"},
    {"key": "mmmh",   "name": "猫咪漫画",     "cat": "comic", "icon": "books.vertical.fill"},
    {"key": "akmh",   "name": "爱看漫画",     "cat": "comic", "icon": "books.vertical.fill"},
    {"key": "hhlz",   "name": "黄鹤楼",       "cat": "comic", "icon": "books.vertical.fill"},
    {"key": "jmtt",   "name": "姐妹图",       "cat": "comic", "icon": "photo.stack.fill"},
    {"key": "mw",     "name": "美图",         "cat": "comic", "icon": "photo.fill"},
]

# 模块 → 后端相对路径（来自 IPA 字符串池，如 /api/v1/video、api.php/api/videos/list_contents）
MODULE_PATHS = {
    "av91":   ["/api/v1/video", "/api/v2/index_items"],
    "pron91": ["/api/v1/video", "/api/v2/index_items"],
    "sp91":   ["/api/v1/video", "/api/v2/index_items"],
    "4hu":    ["/api/v2/index_items", "/api/v1/video"],
    "cg51":   ["/api/v2/index_items", "/api/v1/video"],
    "missav": ["/api/v2/index_items", "/api/v1/video"],
    "javdb":  ["/api/v1/movies/", "/api/v2/query/result"],
    "aijav":  ["/api/v1/video", "/api/v1/movies/"],
    "mmav":   ["/api/v1/video"],
    "one":    ["/api/v2/index_items"],
    "box":    ["/box/api/home", "/box/api/ping"],
    "hjsq":   ["/api/v2/index_items", "/api/v2/query/result"],
    "cgw":    ["/api/v2/index_items"],
    "hxsp":   ["/api/v2/index_items"],
    "hgsp":   ["/api/v2/index_items"],
    "hsck":   ["/api/v2/index_items"],
    "qysq":   ["/api/v2/index_items"],
    "hdb":    ["/api/v2/index_items"],
    "kpsp":   ["/api/v2/index_items"],
    "lclf":   ["/api/v2/index_items"],
    "ltb":    ["/api/v2/index_items"],
    "lxs":    ["/api/v2/index_items"],
    "mdtv":   ["/api/v2/index_items"],
    "rryy":   ["/api/v2/index_items"],
    "zlt":    ["/api/v2/index_items"],
    "insav":  ["/api/v2/index_items"],
    "djr":    ["/api/v2/index_items"],
    "fl2":    ["/api/v2/index_items"],
    "txvlog": ["/api/v2/index_items"],
    "km":     ["/api/v2/index_items"],
    "live":   ["/api/app/live/home", "/api/v2/index_items"],
    "mmmh":   ["/api/v2/index_items"],
    "akmh":   ["/api/v2/index_items"],
    "hhlz":   ["/api/v2/index_items"],
    "jmtt":   ["/api/v2/index_items"],
    "mw":     ["/api/v2/index_items"],
}

SIGN_MODES = ["md5_k_t_n", "md5_k_n_t", "md5_k_s_t_n", "md5_t_n_k",
              "hmac_md5_s_ktn", "hmac_sha256_s_ktn"]


# ============================================================ 签名
def sign_payload(mode, key, secret, ts, nonce, path):
    base = {
        "md5_k_t_n":     (key + ts + nonce),
        "md5_k_n_t":     (key + nonce + ts),
        "md5_k_s_t_n":   (key + secret + ts + nonce),
        "md5_t_n_k":     (ts + nonce + key),
        "md5_k_p_t_n":   (key + path + ts + nonce),
        "md5_s_k_t_n":   (secret + key + ts + nonce),
    }.get(mode)
    if base is not None:
        return hashlib.md5(base.encode()).hexdigest()
    if mode == "hmac_md5_s_ktn":
        return hmac.new(secret.encode(), (key + ts + nonce).encode(), hashlib.md5).hexdigest()
    if mode == "hmac_sha256_s_ktn":
        return hmac.new(secret.encode(), (key + ts + nonce).encode(), hashlib.sha256).hexdigest()
    raise ValueError("unknown sign mode: %s" % mode)


class Spider(_B):
    headers = {"User-Agent": UA, "Accept": "application/json"}

    def __init__(self):
        super(Spider, self).__init__()
        self.hosts = list(DEFAULT_HOSTS)
        self.host = DEFAULT_HOSTS[0]
        self.key = APP_KEY
        self.secret = ""
        self.sign_mode = "md5_k_t_n"
        self.timeout = 15
        self.ctx = ssl.create_default_context()
        self.ctx.check_hostname = False
        self.ctx.verify_mode = ssl.CERT_NONE
        self._alive = None

    # ---------------- 基类接口 ----------------
    def getName(self):
        return "暮色聚合(avbox)"

    def getDependence(self):
        return []

    def init(self, extend=""):
        ext = {}
        if extend:
            try:
                ext = json.loads(extend) if isinstance(extend, str) else dict(extend)
            except Exception:
                ext = {}
        if ext.get("host"):
            self.host = str(ext["host"]).rstrip("/")
            if self.host not in self.hosts:
                self.hosts.insert(0, self.host)
        if ext.get("key"):
            self.key = str(ext["key"])
        if ext.get("secret"):
            self.secret = str(ext["secret"])
        if ext.get("signMode"):
            self.sign_mode = str(ext["signMode"])
        if ext.get("timeout"):
            self.timeout = int(ext["timeout"])
        return None

    def isVideoFormat(self, url):
        low = (url or "").lower()
        return any(k in low for k in (".m3u8", ".mp4", ".flv", ".mkv", ".ts", ".mpd"))

    def manualVideoCheck(self):
        return False

    def destroy(self):
        pass

    def action(self, action):
        pass

    # ---------------- 网络 ----------------
    def _now(self):
        return str(int(time.time()))

    def _nonce(self):
        return "%016x" % random.getrandbits(64)

    def _auth_query(self, path, extra=None):
        ts = self._now()
        nonce = self._nonce()
        sign = sign_payload(self.sign_mode, self.key, self.secret, ts, nonce, path)
        q = {
            "X-Auth-Key": self.key,
            "X-Auth-TimeStamp": ts,
            "X-Auth-Nonce": nonce,
            "X-Auth-Sign": sign,
        }
        if extra:
            q.update({k: v for k, v in extra.items() if v is not None})
        return urllib.parse.urlencode(q)

    def _raw_get(self, url):
        req = urllib.request.Request(url, headers=self.headers)
        try:
            with urllib.request.urlopen(req, timeout=self.timeout, context=self.ctx) as r:
                return r.status, r.read()
        except urllib.error.HTTPError as e:
            return e.code, e.read()
        except Exception as e:
            return "ERR", str(e).encode()

    def _api(self, path, params=None):
        """带签名请求，返回 (ok, data)。自动在域名池 + 签名模式间回退。"""
        order = [self.host] + [h for h in self.hosts if h != self.host]
        for host in order:
            for mode in [self.sign_mode] + [m for m in SIGN_MODES if m != self.sign_mode]:
                qs = self._auth_query(path, params)
                status, body = self._raw_get("%s%s?%s" % (host, path, qs))
                if status != 200:
                    continue
                try:
                    obj = json.loads(body.decode("utf-8", "replace"))
                except Exception:
                    continue
                if isinstance(obj, dict) and obj.get("code") in (0, 200):
                    self.host = host
                    self.sign_mode = mode
                    return True, obj.get("data")
            # 该域名全部签名模式失败 → 换下一个域名
        return False, None

    # ---------------- 数据映射 ----------------
    @staticmethod
    def _pick(d, *keys, **kw):
        for k in keys:
            if isinstance(d, dict) and d.get(k) not in (None, "", []):
                return d[k]
        return kw.get("default", "")

    def _to_vod(self, item):
        vod_id = self._pick(item, "vod_id", "id", "video_id", "vid")
        return {
            "vod_id": str(vod_id),
            "vod_name": self._pick(item, "vod_name", "title", "name", "caption"),
            "vod_pic": self._pick(item, "vod_pic", "cover", "pic", "image", "img"),
            "vod_remarks": self._pick(item, "vod_remarks", "remarks", "duration", "time", "updated"),
            "vod_play_from": self._pick(item, "vod_play_from", "source", "platform", default="muse"),
        }

    def _list_of(self, data):
        if isinstance(data, list):
            return data
        if isinstance(data, dict):
            for k in ("list", "items", "data", "rows", "videos", "records", "result"):
                v = data.get(k)
                if isinstance(v, list):
                    return v
            # 一层嵌套
            for v in data.values():
                if isinstance(v, dict):
                    got = self._list_of(v)
                    if got:
                        return got
        return []

    # ---------------- 基类方法 ----------------
    def homeContent(self, filter):
        classes = [{"type_id": m["key"], "type_name": m["name"]} for m in MODULES]
        result = {"class": classes}
        if filter:
            result["filters"] = {m["key"]: [] for m in MODULES}
        try:
            ok, data = self._api(MODULE_PATHS["one"][0], {"page": 1, "size": 24})
            result["list"] = [self._to_vod(x) for x in self._list_of(data)] if ok else []
        except Exception as e:
            print("[暮色] homeContent err: %s" % e)
            result["list"] = []
        return result

    def homeVideoContent(self):
        return {"list": self.homeContent(False).get("list", [])}

    def categoryContent(self, tid, pg, filter, extend):
        page = int(pg or 1)
        ex = {"page": page, "size": 24, "module": tid, "type": tid}
        if extend:
            for k, v in extend.items():
                if v not in (None, ""):
                    ex[k] = v
        paths = MODULE_PATHS.get(tid, ["/api/v2/index_items"])
        for path in paths:
            ok, data = self._api(path, ex)
            if ok:
                items = [self._to_vod(x) for x in self._list_of(data)]
                total = self._pick(data, "total", "count", default=0) if isinstance(data, dict) else 0
                if items:
                    return {"list": items, "page": page, "pagecount": page + 1,
                            "limit": 24, "total": total or 9999}
        return {"list": [], "page": page, "pagecount": page + 1, "limit": 24, "total": 0}

    def detailContent(self, array):
        vod_id = array[0] if array else ""
        parts = str(vod_id).split("@")
        module = parts[1] if len(parts) > 1 else "one"
        real_id = parts[0]
        paths = MODULE_PATHS.get(module, ["/api/v2/index_items"])
        detail_paths = []
        for p in paths:
            detail_paths.append(p)
            detail_paths.append(p.rstrip("/") + "/" + urllib.parse.quote(str(real_id)))
        for path in detail_paths:
            ok, data = self._api(path, {"id": real_id, "module": module})
            if not ok or not isinstance(data, dict):
                continue
            item = data.get("detail") or data.get("video") or data
            if not isinstance(item, dict):
                continue
            play = self._pick(item, "play_url", "url", "m3u8", "video_url", "playUrl")
            if not play:
                plist = self._pick(item, "play_list", "lines", "sources", default=[])
                if isinstance(plist, list) and plist:
                    play = self._pick(plist[0], "url", "play_url", "m3u8")
            if not play:
                continue
            name = self._pick(item, "vod_name", "title", "name")
            return {
                "list": [{
                    "vod_id": str(vod_id),
                    "vod_name": name,
                    "vod_pic": self._pick(item, "vod_pic", "cover", "pic", "image"),
                    "vod_content": self._pick(item, "vod_content", "description", "desc", "intro"),
                    "vod_play_from": module,
                    "vod_play_url": "%s$%s" % (name or "播放", play),
                }]
            }
        return {"list": []}

    def searchContent(self, key, quick, pg="1"):
        page = int(pg or 1)
        for path in ["/api/v2/query/result", "/api/v2/search", "/api/v1/video"]:
            ok, data = self._api(path, {"keyword": key, "wd": key, "q": key, "page": page})
            if ok:
                items = [self._to_vod(x) for x in self._list_of(data)]
                if items:
                    return {"list": items, "page": page, "pagecount": page + 1,
                            "limit": 24, "total": len(items)}
        return {"list": [], "page": page, "pagecount": page + 1, "limit": 24, "total": 0}

    def playerContent(self, flag, id, vipFlags):
        url = id
        if isinstance(url, str) and url.startswith("http"):
            return {"parse": 0, "url": url, "header": {"User-Agent": UA}}
        return {"parse": 1, "url": url, "header": {"User-Agent": UA}, "jx": 1}
