# -*- coding: utf-8 -*-
"""
暮色（com.look.avbox / avbox）后端聚合 Spider — vbox 福利区适配版
================================================================
证据来源：
  · IPA 逆向：app-暮色-1.0.1(开发模式安装).ipa
      BundleID com.look.avbox / Flutter AOT / 37 个 module 包
  · 真机抓包：Stream 抓包 2026-10-28（用户提供）
      明文请求头只有 5 行：
        GET /box/api/home?versionCode=101 HTTP/1.1
        user-agent: Dart/3.12 (dart:io)
        time: <13 位毫秒时间戳>
        accept-encoding: gzip
        uuid: <32 位 hex 设备号>
        host: 38.46.10.6:6868
      响应：HTTP/1.1 200 + chunked + JSON 字符串 "'<base64>'"（AES 密文）
  · 探针实测：
      /box/api/ping          → 200 明文，固定 44 字符 base64（32 字节）
      /box/api/home 及所有业务路径 → 200 {"code":400,"msg":"违规请求"}
      缺 time  → {"code":400,"msg":"缺少请求头:time"}
      缺 uuid  → {"code":400,"msg":"缺少请求头:uuid"}
      time 过旧 → {"code":400,"msg":"请求已过期"}

本脚本实现：
  1) 双通道：6868 明文通道（真实）+ api.* 四件套通道（兼容旧版本）
  2) 真实鉴权头 time/uuid，uuid 可由 extend 注入
  3) 响应自动识别：明文 JSON / base64 JSON 字符串 / base64+AES 密文
  4) 37 模块 → 分类映射，封面/详情/播放统一映射成 vbox 结构

extend 示例：
  {"host": "http://38.46.10.6:6868",
   "uuid": "78f92bcb27bdc20181ff7642c55c60e5",
   "versionCode": "101",
   "aesKey": "", "aesIv": "", "timeout": 15}
"""
import sys
import os
import json
import time
import ssl
import base64
import hashlib
import random
import urllib.parse
import urllib.request
import urllib.error
import threading

sys.path.append('..')
try:
    from base.spider import Spider as _B
except Exception:
    class _B(object):
        pass

# ============================================================ 常量
UA_DART = "Dart/3.12 (dart:io)"
UA_H5 = ('Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) '
         'AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Mobile/15E148 Safari/604.1')

# 真实后端（抓包实证：明文 HTTP / 6868）
HOSTS_BOX = [
    "http://38.46.10.6:6868",
    "http://38.46.10.2:6868",
    "http://38.46.10.3:6868",
    "http://38.46.10.4:6868",
    "http://38.46.10.5:6868",
    "http://202.95.22.200:6868",
    "http://202.95.22.201:6868",
    "http://202.95.22.202:6868",
    "http://202.95.22.203:6868",
    "http://202.95.22.204:6868",
    "http://198.44.248.101:6868",
    "http://198.44.248.102:6868",
    "http://122.10.20.249:6868",
]

# 旧通道（IPA 内 api.* 域名，X-Auth 四件套，留作兼容）
HOSTS_API = [
    "https://api.3459381.com",
    "https://api.c6dd5cc.com",
    "https://api.61c76a0.com",
    "https://api.87735d5.com",
    "https://api.em1oifd0.com",
]
APP_KEY = "368480924a6c78e2e8681551a7cf4c21"

# 响应解密密钥（Blutter 反编译 libapp.so 实证，2026-10-30）
# 混淆真相：切罗基字母 XOR 0x1395 → 见 interceptor.dart onResponse
# 数据流：base64 → AES-128-CBC 解密 → gzip 解压 → JSON
AES_KEY = b"8992d27bceae2962"   # 16 字节 = AES-128
AES_IV = b"62233532ac9029c6"    # 16 字节

# 37 个资源模块（IPA: package:avbox/module/<key>/...）
MODULES = [
    {"key": "av91",   "name": "91AV",     "cat": "video"},
    {"key": "pron91", "name": "91Pron",   "cat": "video"},
    {"key": "sp91",   "name": "91视频",    "cat": "video"},
    {"key": "4hu",    "name": "四虎影库",   "cat": "video"},
    {"key": "cg51",   "name": "51吃瓜",    "cat": "video"},
    {"key": "missav", "name": "MissAV",   "cat": "video"},
    {"key": "javdb",  "name": "JavDB",    "cat": "video"},
    {"key": "aijav",  "name": "AIJAV",    "cat": "video"},
    {"key": "mmav",   "name": "猫咪AV",    "cat": "video"},
    {"key": "one",    "name": "One",      "cat": "video"},
    {"key": "box",    "name": "资源盒",     "cat": "video"},
    {"key": "hjsq",   "name": "海角社区",   "cat": "video"},
    {"key": "cgw",    "name": "吃瓜网",     "cat": "video"},
    {"key": "hxsp",   "name": "红杏视频",   "cat": "video"},
    {"key": "hgsp",   "name": "黄瓜视频",   "cat": "video"},
    {"key": "hsck",   "name": "黄色仓库",   "cat": "video"},
    {"key": "qysq",   "name": "青衣社区",   "cat": "video"},
    {"key": "hdb",    "name": "红豆包",     "cat": "video"},
    {"key": "kpsp",   "name": "快片视频",   "cat": "video"},
    {"key": "lclf",   "name": "楼风",       "cat": "video"},
    {"key": "ltb",    "name": "Ltb",      "cat": "video"},
    {"key": "lxs",    "name": "撸先生",     "cat": "video"},
    {"key": "mdtv",   "name": "美杜莎TV",   "cat": "video"},
    {"key": "rryy",   "name": "日日影院",   "cat": "video"},
    {"key": "zlt",    "name": "Zlt",      "cat": "video"},
    {"key": "insav",  "name": "InSav",    "cat": "video"},
    {"key": "djr",    "name": "DJR",      "cat": "video"},
    {"key": "fl2",    "name": "FL2",      "cat": "video"},
    {"key": "txvlog", "name": "糖心Vlog",   "cat": "video"},
    {"key": "km",     "name": "看美",       "cat": "video"},
    {"key": "live",   "name": "直播",       "cat": "live"},
    {"key": "mmmh",   "name": "猫咪漫画",   "cat": "comic"},
    {"key": "akmh",   "name": "爱看漫画",   "cat": "comic"},
    {"key": "hhlz",   "name": "黄鹤楼",     "cat": "comic"},
    {"key": "jmtt",   "name": "姐妹图",     "cat": "comic"},
    {"key": "mw",     "name": "美图",       "cat": "comic"},
]

# 模块 → 后端路径（IPA 字符串池实证）
MODULE_PATHS = {
    "javdb": ["/api/v1/movies/", "/api/v2/query/result"],
    "box":   ["/box/api/home"],
    "live":  ["/api/app/live/home", "/api/v2/index_items"],
}
DEFAULT_PATHS = ["/api/v2/index_items", "/api/v1/video"]

# 模块 → 探测地址（连通性探测用，来自 muse_endpoints.json hosts 的"主域名"）
# 仅覆盖能明确映射到平台主 API 的模块；未列出的模块默认显示（不探测）
MODULE_HOSTS = {
    "av91":   "https://api3.lmqtqhiho.cc/",
    "pron91": "https://we.killcovid2020.com/",
    "4hu":    "https://portal.instruno.com/",
    "missav": "https://missav.ws/",
    "javdb":  "https://jdforrepam.com/",
    "aijav":  "https://newavapi.9xyrp3kg4b86.com/",
    "mmav":   "https://bvbvbvssu.a63qv1sy.com/",
    "one":    "https://api.3459381.com/",
    "hjsq":   "http://23.225.145.74/",
    "hxsp":   "https://hxapi.ruueyek.com/",
    "hgsp":   "https://api55.nmrgqb.com/",
    "hsck":   "https://hsck3.u0u0.cc/",
    "qysq":   "https://d1kmvkv4iwtiup.cloudfront.net/",
    "hdb":    "https://api.b7f3192.com/",
    "kpsp":   "https://sm-api.wieuc.com/",
    "lclf":   "https://lclf.lol/",
    "lxs":    "https://api.hichatapi.info/",
    "mdtv":   "https://spi.d5c4a712.com/",
    "rryy":   "https://yy.swgongshui.com/",
    "zlt":    "https://apjk85sd.q2ngx58.com/",
    "insav":  "https://snen24.com/",
    "djr":    "https://tokyohot-api-bo92ps.mtqztc.com/",
    "fl2":    "https://prja.website/v1/host",
    "txvlog": "https://api.0yhxyky2v099lb9.com/",
    "km":     "https://icef4vn.xyz/",
    "live":   "https://17s.bj-steel.com.cn/",
    "mmmh":   "https://public.mino02.live/host_pwa.txt",
    "akmh":   "https://www.18akmanhua.com/",
    "mw":     "https://manwaqr.cc/",
}


class Spider(_B):
    def __init__(self):
        super(Spider, self).__init__()
        self.hosts_box = list(HOSTS_BOX)
        self.hosts_api = list(HOSTS_API)
        self.host = HOSTS_BOX[0]
        self.uuid = ""
        self.version_code = "101"
        self.aes_key = AES_KEY
        self.aes_iv = AES_IV
        self.timeout = 3
        self.ctx = ssl.create_default_context()
        self.ctx.check_hostname = False
        self.ctx.verify_mode = ssl.CERT_NONE
        self._legacy = False
        self._ping_key = ""

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
            h = str(ext["host"]).rstrip("/")
            self.host = h
            if h not in self.hosts_box:
                self.hosts_box.insert(0, h)
        if ext.get("uuid"):
            self.uuid = str(ext["uuid"]).strip()
        if ext.get("versionCode"):
            self.version_code = str(ext["versionCode"])
        if ext.get("aesKey"):
            self.aes_key = self._to_key(ext["aesKey"])
        if ext.get("aesIv"):
            self.aes_iv = self._to_key(ext["aesIv"])
        if ext.get("timeout"):
            self.timeout = int(ext["timeout"])
        if not self.uuid:
            self.uuid = self._gen_uuid()
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

    # ---------------- 工具 ----------------
    @staticmethod
    def _to_key(v):
        if isinstance(v, bytes):
            return v
        s = str(v)
        try:
            return base64.b64decode(s, validate=True)
        except Exception:
            return s.encode()

    @staticmethod
    def _gen_uuid():
        return "%032x" % random.getrandbits(128)

    @staticmethod
    def _pick(d, *keys, **kw):
        for k in keys:
            if isinstance(d, dict) and d.get(k) not in (None, "", [], {}):
                return d[k]
        return kw.get("default", "")

    # ---------------- 响应解码 ----------------
    def _decode_body(self, raw, content_encoding=""):
        if content_encoding and "gzip" in content_encoding.lower():
            try:
                import gzip
                raw = gzip.decompress(raw)
            except Exception:
                pass
        text = raw.decode("utf-8", "replace").strip()
        # 1) 明文 JSON
        if text[:1] in ("{", "["):
            try:
                return json.loads(text)
            except Exception:
                pass
        # 2) JSON 字符串包裹的 base64
        s = text.strip('"').strip("'").strip()
        if len(s) > 16 and all(c in "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789+/=" for c in s):
            try:
                dec = base64.b64decode(s + "=" * (-len(s) % 4))
            except Exception:
                return None
            # 2a) 直接是 JSON
            try:
                return json.loads(dec.decode("utf-8"))
            except Exception:
                pass
            # 2b) AES 解密（配置了 key 才做）
            if self.aes_key:
                pt = self._aes_decrypt(dec)
                if pt:
                    try:
                        return json.loads(pt.decode("utf-8", "replace"))
                    except Exception:
                        pass
            return {"_cipher": True, "len": len(dec)}
        return None

    def _aes_decrypt(self, data):
        """AES-128-CBC 解密 + PKCS7 unpad + gzip 解压，返回明文字节。

        数据流（Blutter 实证）：base64 → AES-128-CBC → gzip → JSON
        """
        key = self.aes_key
        if len(key) not in (16, 24, 32):
            return None
        iv = self.aes_iv or bytes(16)
        if len(iv) != 16:
            return None
        body = data
        if len(body) % 16:
            return None
        out = self._aes_cbc_raw(key, iv, body)
        if out is None:
            return None
        # PKCS7 unpad
        pad = out[-1] if out else 0
        if 1 <= pad <= 16 and out[-pad:] == bytes([pad]) * pad:
            out = out[:-pad]
        # gzip 解压（响应明文是 gzip(JSON)）
        try:
            import gzip
            return gzip.decompress(out)
        except Exception:
            return out

    @staticmethod
    def _aes_cbc_raw(key, iv, body):
        """优先 vbox 内置 Crypto（pyaes），fallback cryptography"""
        try:
            from Crypto.Cipher import AES as _AES
            return _AES.new(key, _AES.MODE_CBC, iv).decrypt(body)
        except Exception:
            pass
        try:
            from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
            c = Cipher(algorithms.AES(key), modes.CBC(iv))
            d = c.decryptor()
            return d.update(body) + d.finalize()
        except Exception:
            return None

    # ---------------- 网络 ----------------
    def _http_get(self, url, headers):
        req = urllib.request.Request(url, headers=headers)
        try:
            with urllib.request.urlopen(req, timeout=self.timeout, context=self.ctx) as r:
                return r.status, r.read(), dict(r.headers)
        except urllib.error.HTTPError as e:
            return e.code, e.read(), dict(e.headers or {})
        except Exception as e:
            return "ERR", str(e).encode(), {}

    def _box_headers(self):
        return {
            "user-agent": UA_DART,
            "time": str(int(time.time() * 1000)),
            "accept-encoding": "gzip",
            "uuid": self.uuid,
        }

    def _box_get(self, path, params=None):
        """6868 明文通道：time + uuid 鉴权"""
        q = dict(params or {})
        if "versionCode" not in q:
            q["versionCode"] = self.version_code
        qs = urllib.parse.urlencode(q)
        url = "%s%s%s" % (self.host.rstrip("/"), path, ("?" + qs) if qs else "")
        st, raw, hdr = self._http_get(url, self._box_headers())
        if st != 200:
            return False, None
        obj = self._decode_body(raw, hdr.get("Content-Encoding", ""))
        if isinstance(obj, dict) and obj.get("code") in (0, 200):
            return True, obj.get("data", obj)
        return False, obj

    def _api_get(self, path, params=None):
        """api.* 通道：X-Auth 四件套（兼容旧版）"""
        ts = str(int(time.time()))
        nonce = self._gen_uuid()[:16]
        sign = hashlib.md5((APP_KEY + ts + nonce).encode()).hexdigest()
        q = {
            "X-Auth-Key": APP_KEY,
            "X-Auth-TimeStamp": ts,
            "X-Auth-Nonce": nonce,
            "X-Auth-Sign": sign,
        }
        q.update({k: v for k, v in (params or {}).items() if v is not None})
        qs = urllib.parse.urlencode(q)
        for h in self.hosts_api:
            st, raw, hdr = self._http_get(h + path + "?" + qs,
                                          {"user-agent": UA_H5, "Accept": "application/json"})
            if st != 200:
                continue
            obj = self._decode_body(raw, hdr.get("Content-Encoding", ""))
            if isinstance(obj, dict) and obj.get("code") in (0, 200):
                self._legacy = True
                return True, obj.get("data", obj)
        return False, None

    def _ping(self):
        if self._ping_key:
            return self._ping_key
        st, raw, _ = self._http_get(self.host + "/box/api/ping", self._box_headers())
        if st == 200:
            self._ping_key = raw.decode("utf-8", "replace").strip()
        return self._ping_key

    def _get(self, path, params=None):
        # 只走 6868 主通道；api.* 旧通道已废弃(全 500/404)，不再 fallback 拖 75s
        return self._box_get(path, params)

    def _probe_modules(self):
        """并发探测各平台主域名连通性，返回存活模块 key 集合。

        目的：动态自适应分类——只有能连通的平台才显示为分类，
        域名失效/被墙/反爬的平台自动隐藏，不再硬编码一屏死链接。
        """
        alive = set()
        lock = threading.Lock()

        def worker(key, url):
            st, _, _ = self._http_get(url, {"user-agent": UA_H5})
            if st == 200:
                with lock:
                    alive.add(key)

        threads = []
        for m in MODULES:
            url = MODULE_HOSTS.get(m["key"])
            if not url:
                continue
            t = threading.Thread(target=worker, args=(m["key"], url))
            t.daemon = True
            threads.append(t)
            t.start()
        for t in threads:
            t.join(timeout=self.timeout + 2)
        return alive

    # ---------------- 映射 ----------------
    def _list_of(self, data):
        if isinstance(data, list):
            return data
        if isinstance(data, dict):
            for k in ("list", "items", "data", "rows", "videos", "records", "result", "menus"):
                v = data.get(k)
                if isinstance(v, list):
                    return v
            for v in data.values():
                if isinstance(v, dict):
                    got = self._list_of(v)
                    if got:
                        return got
        return []

    def _to_vod(self, item, module=""):
        v = {
            "vod_id": str(self._pick(item, "vod_id", "id", "video_id", "vid", "contentId")),
            "vod_name": self._pick(item, "vod_name", "title", "name", "caption", "contentTitle"),
            "vod_pic": self._pick(item, "vod_pic", "cover", "pic", "image", "img", "coverUrl"),
            "vod_remarks": self._pick(item, "vod_remarks", "remarks", "duration", "time", "updated"),
            "vod_play_from": module or self._pick(item, "source", "platform", default="muse"),
        }
        if module:
            v["vod_id"] = "%s@%s" % (v["vod_id"], module)
        return v

    # ---------------- 基类方法 ----------------
    def homeContent(self, filter):
        # 动态自适应分类：并发探测各平台连通性，只显示"活着"的平台；
        # 无探测地址的模块默认保留；探测全灭(疑似网络异常)时回退全量
        alive = self._probe_modules()
        classes = []
        for m in MODULES:
            key = m["key"]
            if key in MODULE_HOSTS and key not in alive:
                continue
            classes.append({"type_id": key, "type_name": m["name"]})
        if not classes:
            classes = [{"type_id": m["key"], "type_name": m["name"]} for m in MODULES]
        result = {"class": classes}
        if filter:
            result["filters"] = {m["key"]: [] for m in MODULES}
        for path in ("/box/api/home", "/api/v2/index_items"):
            ok, data = self._get(path, {"versionCode": self.version_code} if "box" in path else {"page": 1, "size": 24})
            if ok:
                items = [self._to_vod(x) for x in self._list_of(data)]
                if items:
                    result["list"] = items
                    break
        result.setdefault("list", [])
        return result

    def homeVideoContent(self):
        return {"list": self.homeContent(False).get("list", [])}

    def categoryContent(self, tid, pg, filter, extend):
        page = int(pg or 1)
        q = {"page": page, "size": 24, "module": tid, "type": tid}
        if extend:
            q.update({k: v for k, v in extend.items() if v not in (None, "")})
        for path in MODULE_PATHS.get(tid, DEFAULT_PATHS):
            ok, data = self._get(path, q)
            if ok:
                items = [self._to_vod(x, tid) for x in self._list_of(data)]
                if items:
                    total = self._pick(data, "total", "count", default=0) if isinstance(data, dict) else 0
                    return {"list": items, "page": page, "pagecount": page + 1,
                            "limit": 24, "total": total or 9999}
        return {"list": [], "page": page, "pagecount": page + 1, "limit": 24, "total": 0}

    def detailContent(self, array):
        raw_id = array[0] if array else ""
        parts = str(raw_id).split("@")
        vid = parts[0]
        module = parts[1] if len(parts) > 1 else "one"
        cands = []
        for p in MODULE_PATHS.get(module, DEFAULT_PATHS):
            cands.append(p)
            cands.append(p.rstrip("/") + "/" + urllib.parse.quote(vid))
        cands.append("/api/v2/video/details/" + urllib.parse.quote(vid))
        for path in cands:
            ok, data = self._get(path, {"id": vid, "module": module})
            if not ok:
                continue
            item = data.get("detail") or data.get("video") or data if isinstance(data, dict) else None
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
            return {"list": [{
                "vod_id": str(raw_id),
                "vod_name": name,
                "vod_pic": self._pick(item, "vod_pic", "cover", "pic", "image"),
                "vod_content": self._pick(item, "vod_content", "description", "desc", "intro"),
                "vod_play_from": module,
                "vod_play_url": "%s$%s" % (name or "播放", play),
            }]}
        return {"list": []}

    def searchContent(self, key, quick, pg="1"):
        page = int(pg or 1)
        for path in ("/api/v2/query/result", "/api/v2/search", "/api/v1/video"):
            ok, data = self._get(path, {"keyword": key, "wd": key, "q": key, "page": page})
            if ok:
                items = [self._to_vod(x) for x in self._list_of(data)]
                if items:
                    return {"list": items, "page": page, "pagecount": page + 1,
                            "limit": 24, "total": len(items)}
        return {"list": [], "page": page, "pagecount": page + 1, "limit": 24, "total": 0}

    def playerContent(self, flag, id, vipFlags):
        url = str(id)
        if url.startswith("http"):
            return {"parse": 0, "url": url, "header": {"User-Agent": UA_H5}}
        return {"parse": 1, "url": url, "header": {"User-Agent": UA_H5}, "jx": 1}
