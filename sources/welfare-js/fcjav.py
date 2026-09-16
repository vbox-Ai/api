# -*- coding: utf-8 -*-
"""FCJAV — vbox 适配版（并发域名探测 + 10分钟缓存 + 协议修正）"""

import base64
import html
import json
import re
import time
import unicodedata
from urllib.parse import quote, urlencode, urljoin, urlparse

try:
    import requests
except ImportError:
    requests = None

try:
    from Crypto.Cipher import AES as _CryptoAES
except ImportError:
    _CryptoAES = None

try:
    from cryptography.hazmat.primitives.ciphers import Cipher as _Cipher, algorithms as _algorithms, modes as _modes
except ImportError:
    _Cipher = _algorithms = _modes = None

try:
    from base.spider import Spider as _BaseSpider
except Exception:
    class _BaseSpider(object):
        pass

# ============================================================
# 并发域名探测 + 10 分钟 TTL 缓存
# ============================================================
from concurrent.futures import ThreadPoolExecutor, as_completed

_DOMAIN_CACHE = {"domain": None, "timestamp": 0}
_CACHE_TTL = 600
_PROBE_TIMEOUT = 8

DEFAULT_HOSTS = [
    "https://fcjav.com",
    "https://fcjav.tv",
    "https://fcjav.club",
]


def _probe_domain(domain, path, headers, timeout=_PROBE_TIMEOUT):
    try:
        url = domain.rstrip('/') + '/' + path.lstrip('/')
        if requests is not None:
            rsp = requests.get(url, headers=headers, timeout=timeout, verify=False, allow_redirects=True)
            if rsp.status_code == 200:
                text = rsp.text
                low = text.lower()
                if ("just a moment" not in low and "cf-chl-" not in low and
                        "performing security verification" not in low and
                        "verify you are human" not in low):
                    return text, domain
    except Exception:
        pass
    return None


class _DomainProbeMixin:
    def _fetch_best(self, path, headers=None, timeout=_PROBE_TIMEOUT):
        headers = headers or {}
        domains = getattr(self, '_probe_domains', DEFAULT_HOSTS)
        if not domains:
            return "", ""

        now = time.time()
        cached = _DOMAIN_CACHE["domain"]
        if cached and (now - _DOMAIN_CACHE["timestamp"]) < _CACHE_TTL:
            result = _probe_domain(cached, path, headers, timeout)
            if result:
                return result

        with ThreadPoolExecutor(max_workers=len(domains)) as executor:
            futures = {
                executor.submit(_probe_domain, d, path, headers, timeout): d
                for d in domains
            }
            for future in as_completed(futures):
                result = future.result()
                if result:
                    _DOMAIN_CACHE["domain"] = result[1]
                    _DOMAIN_CACHE["timestamp"] = time.time()
                    return result

        return "", domains[0] if domains else ""


# ============================================================
# 常量定义
# ============================================================
BASE = "https://fcjav.com"
PAGE_SIZE = 24
UA = "Mozilla/5.0 (Linux; Android 10; TV) AppleWebKit/537.36 Chrome/124 Safari/537.36"
UPN_KEY = bytes((107, 105, 101, 109, 116, 105, 101, 110, 109, 117, 97, 57, 49, 49, 99, 97))
UPN_IV = bytes((49, 50, 51, 52, 53, 54, 55, 56, 57, 48, 111, 105, 117, 121, 116, 114))

HOME_CLASSES = [
    {"type_id": "movies", "type_name": "最近更新"},
    {"type_id": "cat_amateur", "type_name": "素人"},
    {"type_id": "cat_censored", "type_name": "有码"},
    {"type_id": "cat_uncensored", "type_name": "无码"},
    {"type_id": "genre_reducing_mosaic", "type_name": "无码破解"},
    {"type_id": "genre_uncensored_leaked", "type_name": "无码流出"},
]

CATALOG_FILTERS = [
    {"key": "genre", "name": "类型", "value": [
        {"n": "全部", "v": ""}, {"n": "无码破解", "v": "genre_reducing_mosaic"},
        {"n": "无码流出", "v": "genre_uncensored_leaked"}, {"n": "素人", "v": "genre_amateur"},
        {"n": "肛交", "v": "genre_anal"}, {"n": "偶像", "v": "genre_av_idol"},
        {"n": "巨乳", "v": "genre_big_tits"}, {"n": "角色扮演", "v": "genre_cosplay"},
        {"n": "中出", "v": "genre_creampie"},
    ]},
    {"key": "actor", "name": "演员", "value": [
        {"n": "全部", "v": ""}, {"n": "Yui Hatano", "v": "actor_yui_hatano"},
        {"n": "Yu Shinoda", "v": "actor_yu_shinoda"}, {"n": "Julia", "v": "actor_julia"},
        {"n": "Aika", "v": "actor_aika"},
    ]},
    {"key": "studio", "name": "片商", "value": [
        {"n": "全部", "v": ""}, {"n": "FC2PPV", "v": "studio_fc2ppv"},
        {"n": "MADONNA", "v": "studio_madonna"}, {"n": "MOODYZ", "v": "studio_moodyz"},
        {"n": "S1", "v": "studio_s1_no_1_style"}, {"n": "SOD", "v": "studio_sod_create"},
    ]},
    {"key": "label", "name": "厂牌", "value": [
        {"n": "全部", "v": ""}, {"n": "Madonna", "v": "label_madonna"},
        {"n": "S1", "v": "label_s1_no_1_style"}, {"n": "MOODYZ DIVA", "v": "label_moodyz_diva"},
    ]},
    {"key": "director", "name": "导演", "value": [
        {"n": "全部", "v": ""}, {"n": "TAKE-D", "v": "director_take_d"},
        {"n": "Goemon", "v": "director_goemon"}, {"n": "Masaki Nao", "v": "director_masaki_nao"},
    ]},
]

SHELL_ROUTES = {
    "movies": "movies",
    "cat_amateur": "movies?genre=amateur",
    "cat_censored": "movies?genre=censored",
    "cat_uncensored": "movies?genre=uncensored",
    "genre_reducing_mosaic": "genre/reducing-mosaic",
    "genre_uncensored_leaked": "genre/uncensored-leaked",
    "genre_amateur": "genre/amateur", "genre_anal": "genre/anal",
    "genre_av_idol": "genre/av-idol", "genre_big_tits": "genre/big-tits",
    "genre_cosplay": "genre/cosplay", "genre_creampie": "genre/creampie",
    "actor_yui_hatano": "actor/yui-hatano", "actor_yu_shinoda": "actor/yu-shinoda",
    "actor_julia": "actor/julia", "actor_aika": "actor/aika",
    "studio_fc2ppv": "studio/fc2ppv", "studio_madonna": "studio/madonna",
    "studio_moodyz": "studio/moodyz", "studio_s1_no_1_style": "studio/s1-no-1-style",
    "studio_sod_create": "studio/sod-create",
    "label_madonna": "label/madonna", "label_s1_no_1_style": "label/s1-no-1-style",
    "label_moodyz_diva": "label/moodyz-diva",
    "director_take_d": "director/take-d", "director_goemon": "director/goemon",
    "director_masaki_nao": "director/masaki-nao",
}


# ============================================================
# AES 工具函数（从原脚本保留）
# ============================================================
def normalize_slug(value):
    value = unicodedata.normalize("NFKC", str(value or "")).strip().lower()
    value = re.sub(r"[^a-z0-9]+", "-", value)
    return value.strip("-")


def _clean(value):
    return re.sub(r"\s+", " ", html.unescape(value or "")).strip()


def _aes_mul(a, b):
    result = 0
    for _ in range(8):
        if b & 1:
            result ^= a
        a = ((a << 1) ^ (0x11B if a & 0x80 else 0)) & 0xFF
        b >>= 1
    return result


def _aes_sbox_tables():
    sbox = []
    inverse = [0] * 256
    for value in range(256):
        inv = 0 if value == 0 else 1
        if value:
            for _ in range(254):
                inv = _aes_mul(inv, value)
        transformed = inv
        for shift in range(1, 5):
            transformed ^= ((inv << shift) | (inv >> (8 - shift))) & 0xFF
        transformed ^= 0x63
        sbox.append(transformed)
        inverse[transformed] = value
    return sbox, inverse


_AES_SBOX, _AES_INV_SBOX = _aes_sbox_tables()


def _aes128_round_keys(key):
    expanded = bytearray(key)
    rcon = 1
    while len(expanded) < 176:
        temp = list(expanded[-4:])
        if len(expanded) % 16 == 0:
            temp = temp[1:] + temp[:1]
            temp = [_AES_SBOX[x] for x in temp]
            temp[0] ^= rcon
            rcon = _aes_mul(rcon, 2)
        start = len(expanded) - 16
        for value in temp:
            expanded.append(expanded[start] ^ value)
            start += 1
    return [expanded[i:i + 16] for i in range(0, 176, 16)]


def _aes128_decrypt_block(block, key):
    state = list(block)
    keys = _aes128_round_keys(key)

    def add_round(rk):
        for i in range(16):
            state[i] ^= rk[i]

    def inv_shift_rows():
        for row in range(1, 4):
            values = [state[row + 4 * col] for col in range(4)]
            values = values[-row:] + values[:-row]
            for col, value in enumerate(values):
                state[row + 4 * col] = value

    def inv_sub_bytes():
        for i, value in enumerate(state):
            state[i] = _AES_INV_SBOX[value]

    def inv_mix_columns():
        for col in range(4):
            i = col * 4
            a, b, c, d = state[i:i + 4]
            state[i:i + 4] = (
                _aes_mul(a, 14) ^ _aes_mul(b, 11) ^ _aes_mul(c, 13) ^ _aes_mul(d, 9),
                _aes_mul(a, 9) ^ _aes_mul(b, 14) ^ _aes_mul(c, 11) ^ _aes_mul(d, 13),
                _aes_mul(a, 13) ^ _aes_mul(b, 9) ^ _aes_mul(c, 14) ^ _aes_mul(d, 11),
                _aes_mul(a, 11) ^ _aes_mul(b, 13) ^ _aes_mul(c, 9) ^ _aes_mul(d, 14),
            )

    add_round(keys[10])
    for round_index in range(9, 0, -1):
        inv_shift_rows()
        inv_sub_bytes()
        add_round(keys[round_index])
        inv_mix_columns()
    inv_shift_rows()
    inv_sub_bytes()
    add_round(keys[0])
    return bytes(state)


def _aes128_cbc_decrypt(ciphertext, key, iv):
    previous = bytes(iv)
    output = bytearray()
    for offset in range(0, len(ciphertext), 16):
        block = bytes(ciphertext[offset:offset + 16])
        decrypted = _aes128_decrypt_block(block, key)
        output.extend(a ^ b for a, b in zip(decrypted, previous))
        previous = block
    return bytes(output)


# ============================================================
# DOM 解析器
# ============================================================
from html.parser import HTMLParser


class _DOM(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.stack = []
        self.items = []
        self.links = []
        self.images = []
        self.iframes = []
        self.text_parts = []
        self.title_parts = []
        self.h1_parts = []
        self.description_parts = []
        self._current_item = None
        self._current_link = None
        self._div_depth = 0

    @staticmethod
    def _attrs(attrs):
        return {str(k).lower(): (v or "") for k, v in attrs}

    def handle_starttag(self, tag, attrs):
        tag = tag.lower()
        a = self._attrs(attrs)
        classes = set(a.get("class", "").split())
        self.stack.append((tag, classes))
        if tag == "div":
            self._div_depth += 1
        if tag == "div" and "ml-item" in classes:
            self._current_item = {"href": "", "pic": "", "text": [], "depth": self._div_depth}
        if tag == "a":
            self._current_link = {"href": a.get("href", ""), "text": []}
            self.links.append(self._current_link)
            if self._current_item is not None and "/v/" in a.get("href", ""):
                self._current_item["href"] = a.get("href", "")
        if tag == "img":
            src = a.get("data-original") or a.get("data-src") or a.get("src", "")
            self.images.append(src)
            if self._current_item is not None and not self._current_item["pic"]:
                self._current_item["pic"] = src
        if tag == "iframe":
            self.iframes.append(a.get("src", ""))

    def handle_endtag(self, tag):
        tag = tag.lower()
        if (tag == "div" and self._current_item is not None and
                self._div_depth == self._current_item.get("depth")):
            if self._current_item.get("href"):
                self.items.append(self._current_item)
                self._current_item = None
        if tag == "div" and self._div_depth:
            self._div_depth -= 1
        if tag == "a":
            self._current_link = None
        if self.stack:
            self.stack.pop()

    def handle_data(self, data):
        if not data or not data.strip():
            return
        self.text_parts.append(data)
        if self._current_link is not None:
            self._current_link["text"].append(data)
        if self._current_item is not None:
            self._current_item["text"].append(data)
        tags = [x[0] for x in self.stack]
        classes = set().union(*(x[1] for x in self.stack)) if self.stack else set()
        if "title" in tags:
            self.title_parts.append(data)
        if "h1" in tags:
            self.h1_parts.append(data)
        if "description" in classes:
            self.description_parts.append(data)


# ============================================================
# Spider 主类
# ============================================================
class Spider(_DomainProbeMixin, _BaseSpider):
    image_hosts = {"cdn001.imggle.net", "cdn002.imggle.net", "pics.dmm.co.jp"}
    iframe_hosts = {"turboplays.click", "ryderjet.com", "hglink.to", "player.upn.one"}
    media_hosts = {"cdn3.turboviplay.com", "o5czhgnohwluyzcb.acek-cdn.com", "e07.etvp.cc"}

    def __init__(self):
        self.extend = {}
        self.last_error = ""
        self._play_cache = {}
        self._probe_domains = DEFAULT_HOSTS

    def getName(self):
        return "FCJAV"

    def getDependence(self):
        return ['requests']

    def init(self, extend=""):
        try:
            super().init(extend)
        except Exception:
            pass
        cfg = extend if isinstance(extend, dict) else (json.loads(extend) if extend else {})
        self.proxies = cfg.get("proxies") or {}
        injected = getattr(self, '_vbox_effective_hosts', None) or []
        if injected and str(injected[0]).startswith('http'):
            self.host = str(injected[0]).rstrip('/')
            self._probe_domains = [self.host]
        else:
            self.host = (cfg.get("host") or BASE).rstrip("/")
            self._probe_domains = DEFAULT_HOSTS
        self.extend = cfg
        return True

    def isVideoFormat(self, url):
        return False

    def manualVideoCheck(self):
        return False

    def destroy(self):
        return None

    # ---------------- URL 安全控制 ----------------

    def _allowed(self, url, image=False):
        try:
            p = urlparse(urljoin(BASE + "/", str(url or "")))
        except Exception:
            return False
        if p.scheme != "https" or p.username or p.password:
            return False
        allowed = self.image_hosts if image else {"fcjav.com", "www.fcjav.com"}
        return (p.hostname or "").lower() in allowed

    def _safe_media(self, url):
        try:
            parsed = urlparse(str(url or ""))
        except Exception:
            return False
        host = (parsed.hostname or "").lower()
        path = parsed.path.lower()
        if parsed.scheme != "https" or parsed.username or parsed.password:
            return False
        if any(word in path for word in ("preview", "trailer", "sample", "teaser")):
            return False
        if path.endswith(".m3u8"):
            return ((host == "player.upn.one" and path.startswith("/v4/pl/") and
                     re.search(r"/master\.[a-z0-9_-]+\.m3u8$", path) is not None) or
                     bool(re.fullmatch(r"cdn\d+\.turboviplay\.com", host)) or
                     host == "o5czhgnohwluyzcb.acek-cdn.com" or
                     bool(re.fullmatch(r"gs\d+\.turbosplayer\.com", host)))
        return (path.endswith(".mp4") and bool(re.fullmatch(r"e\d{2}\.etvp\.cc", host)) and
                path.startswith("/uploads/"))

    @staticmethod
    def _media_referer(url):
        host = (urlparse(str(url or "")).hostname or "").lower()
        if host == "player.upn.one":
            return "https://player.upn.one/"
        if host == "o5czhgnohwluyzcb.acek-cdn.com":
            return "https://ryderjet.com/"
        return "https://turboplays.click/"

    def _safe_iframe(self, url):
        try:
            parsed = urlparse(str(url or ""))
        except Exception:
            return False
        return (parsed.scheme == "https" and not parsed.username and not parsed.password and
                (parsed.hostname or "").lower() in self.iframe_hosts)

    # ---------------- HTTP ----------------

    def _fetch(self, url, timeout=6):
        if not self._allowed(url):
            raise ValueError("URL host is not allowed")
        req = Request(url, headers={"User-Agent": UA, "Accept": "text/html,application/xhtml+xml"})
        try:
            with urlopen(req, timeout=timeout) as r:
                ctype = (r.headers.get("Content-Type") or "").lower()
                raw = r.read(2 * 1024 * 1024 + 1)
                if len(raw) > 2 * 1024 * 1024:
                    raise ValueError("response too large")
                if "html" not in ctype:
                    raise ValueError("unexpected content type")
                text = raw.decode("utf-8", "replace")
        except (HTTPError, URLError, TimeoutError, OSError) as e:
            raise RuntimeError(type(e).__name__) from e
        if self._is_challenge(text):
            raise ValueError("Cloudflare challenge page")
        return text

    @staticmethod
    def _is_challenge(text):
        low = (text or "").lower()
        return ("just a moment" in low or "cf-chl-" in low or
                "performing security verification" in low or
                "verify you are human" in low)

    # ---------------- 列表解析 ----------------

    def _parse_list(self, text, page_url, page=None):
        if self._is_challenge(text):
            raise ValueError("Cloudflare challenge page")
        dom = _DOM()
        dom.feed(text)
        result = []
        seen = set()
        candidates = dom.items
        if not candidates:
            blocks = re.findall(r'<div[^>]+class=["\'][^"\']*ml-item[^"\']*["\'][^>]*>(.*?)</div>', text, re.I | re.S)
            for block in blocks:
                href_m = re.search(r'<a[^>]+href=["\']([^"\']*/v/[^"\']+)["\']', block, re.I)
                img_m = re.search(r'<img[^>]+(?:data-original|data-src|src)=["\']([^"\']+)["\']', block, re.I)
                title_m = re.search(r'<h2[^>]*>(.*?)</h2>', block, re.I | re.S)
                if href_m:
                    candidates.append({"href": href_m.group(1), "pic": img_m.group(1) if img_m else "", "text": [re.sub('<[^>]+>', ' ', title_m.group(1)) if title_m else ""]})
        for row in candidates:
            href = urljoin(page_url, row.get("href", ""))
            if not self._allowed(href) or "/v/" not in href:
                continue
            slug = normalize_slug(urlparse(href).path.split("/v/", 1)[1].split("/", 1)[0])
            if not slug or slug in seen:
                continue
            seen.add(slug)
            pic = urljoin(page_url, row.get("pic", "")) if row.get("pic") else ""
            if pic and not self._allowed(pic, image=True):
                pic = ""
            title = _clean(" ".join(row.get("text", []))) or slug.upper()
            result.append({"vod_id": slug, "vod_name": title, "vod_pic": pic, "vod_remarks": ""})
        current = 1
        m = re.search(r"/pg-(\d+)", urlparse(page_url).path)
        if m:
            current = int(m.group(1))
        page_numbers = [int(x) for x in re.findall(r'href=["\'][^"\']*/pg-(\d+)', text, re.I)]
        has_next = (current + 1) in page_numbers
        return result, (max(page_numbers + [current]) if page is not None else has_next)

    # ---------------- 播放器解析 ----------------

    @staticmethod
    def _parse_player_bootstrap(text):
        values = []
        for name in ("__pt", "__pk"):
            found = ""
            for pattern in (
                r"window\.%s\s*=\s*['\"]([^'\"]*)" % name,
                r"(?:var|let|const)\s+%s\s*=\s*['\"]([^'\"]*)" % name,
            ):
                match = re.search(pattern, text or "", re.I)
                if match:
                    found = match.group(1)
                    break
            values.append(found)
        return tuple(values)

    @staticmethod
    def _xor_decrypt(encoded, key):
        raw = base64.b64decode(encoded or "", validate=True)
        if not key:
            return raw.decode("utf-8", "replace")
        kb = key.encode("utf-8")
        return bytes(value ^ kb[i % len(kb)] for i, value in enumerate(raw)).decode("utf-8", "replace")

    def _parse_player_choices(self, text, vod_id):
        slug = normalize_slug(vod_id)
        if not slug:
            return []
        rows = []
        pattern = r'<(?:button|li)\b[^>]*\bswitch-source\b[^>]*>.*?</(?:button|li)>'
        for tag in re.findall(pattern, text or "", re.I | re.S):
            source = re.search(r'data-source=["\'](\d+)["\']', tag, re.I)
            episode = re.search(r'data-(?:id|episode)=["\'](\d+)["\']', tag, re.I)
            if not source or not episode:
                continue
            label = _clean(re.sub(r"<[^>]+>", " ", tag)) or "线路"
            play_id = "fcjav:%s:%s:%s" % (slug, source.group(1), episode.group(1))
            rows.append((label, play_id))
        return rows

    def _probe_media_playable(self, media):
        if requests is None or not self._safe_media(media):
            return False
        headers = {"User-Agent": UA, "Referer": self._media_referer(media)}
        try:
            path = urlparse(media).path.lower()
            if path.endswith(".mp4"):
                check = dict(headers)
                check["Range"] = "bytes=0-0"
                response = requests.get(media, headers=check, timeout=20, stream=True, allow_redirects=True)
                content_type = (response.headers.get("Content-Type") or "").lower()
                ok = response.status_code == 206 and content_type.startswith("video/")
                response.close()
                return ok
            response = requests.get(media, headers=headers, timeout=20, allow_redirects=True)
            if response.status_code != 200 or "#EXTM3U" not in response.text:
                return False
            playlist_url, text = response.url, response.text
            lines = [line.strip() for line in text.splitlines() if line.strip()]
            variants = [lines[index + 1] for index, line in enumerate(lines[:-1])
                        if line.startswith("#EXT-X-STREAM-INF") and not lines[index + 1].startswith("#")]
            if variants:
                response = requests.get(urljoin(playlist_url, variants[0]), headers=headers, timeout=20, allow_redirects=True)
                if response.status_code != 200 or "#EXTM3U" not in response.text:
                    return False
                playlist_url, text = response.url, response.text
                lines = [line.strip() for line in text.splitlines() if line.strip()]
            map_match = re.search(r'#EXT-X-MAP:URI="([^"]+)"', text)
            media_object = (map_match.group(1) if map_match else
                            next((line for line in lines if not line.startswith("#")), ""))
            if not media_object:
                return False
            check = dict(headers)
            check["Range"] = "bytes=0-0"
            response = requests.get(urljoin(playlist_url, media_object), headers=check, timeout=20, stream=True, allow_redirects=True)
            content_type = (response.headers.get("Content-Type") or "").lower()
            ok = (response.status_code == 206 and
                  not content_type.startswith("text/") and
                  "html" not in content_type)
            response.close()
            return ok
        except Exception:
            return False

    def _prioritize_playable(self, choices):
        choices = list(choices or [])
        by_label = {label.upper(): (label, play_id) for label, play_id in choices}
        for label in ("US", "TB", "FL", "PM", "DD"):
            row = by_label.get(label)
            if not row:
                continue
            try:
                media = self._discover_media(self._parse_play_id(row[1]))
                if self._probe_media_playable(media):
                    self._play_cache[row[1]] = (media, time.time() + 45)
                    return [row] + [item for item in choices if item != row]
            except Exception:
                continue
        return choices

    @staticmethod
    def _parse_play_id(value):
        match = re.fullmatch(r"fcjav:([a-z0-9]+(?:-[a-z0-9]+)*):(\d+):(\d+)", str(value or ""))
        return match.groups() if match else None

    @staticmethod
    def _parse_best_id(value):
        match = re.fullmatch(r"fcjav-best:([a-z0-9]+(?:-[a-z0-9]+)*)", str(value or ""))
        return match.group(1) if match else None

    def _discover_best_media(self, slug):
        detail = self._fetch(BASE + "/v/" + slug)
        choices = self._parse_player_choices(detail, slug)
        by_label = {label.upper(): play_id for label, play_id in choices if label.upper() != "SW"}
        attempted = set()
        ordered = []
        for label in ("TB", "US", "FL", "PM", "PP", "DD"):
            play_id = by_label.get(label)
            if play_id and play_id not in attempted:
                ordered.append(play_id)
                attempted.add(play_id)
        for label, play_id in choices:
            if label.upper() != "SW" and play_id not in attempted:
                ordered.append(play_id)
                attempted.add(play_id)
        for play_id in ordered:
            parts = self._parse_play_id(play_id)
            if not parts:
                continue
            try:
                try:
                    media = self._discover_media(parts)
                except ValueError as first_error:
                    if str(first_error) != "UPN response has no approved full media":
                        raise
                    media = self._discover_media(parts)
                if by_label.get("TB") == play_id and self._safe_media(media):
                    self._play_cache[play_id] = (media, time.time() + 45)
                    return media
                if self._probe_media_playable(media):
                    self._play_cache[play_id] = (media, time.time() + 45)
                    return media
            except Exception:
                continue
        raise ValueError("no verified full media line")

    def _upn_decrypt(self, ciphertext):
        ciphertext = bytes(ciphertext or b"")
        if not ciphertext or len(ciphertext) % 16:
            raise ValueError("invalid UPN ciphertext")
        if _CryptoAES is not None:
            plain = _CryptoAES.new(UPN_KEY, _CryptoAES.MODE_CBC, UPN_IV).decrypt(ciphertext)
        elif _Cipher is not None:
            decryptor = _Cipher(_algorithms.AES(UPN_KEY), _modes.CBC(UPN_IV)).decryptor()
            plain = decryptor.update(ciphertext) + decryptor.finalize()
        else:
            plain = _aes128_cbc_decrypt(ciphertext, UPN_KEY, UPN_IV)
        padding = plain[-1] if plain else 0
        if padding < 1 or padding > 16 or plain[-padding:] != bytes([padding]) * padding:
            raise ValueError("invalid UPN padding")
        return plain[:-padding]

    def _extract_upn_media(self, iframe, session):
        parsed = urlparse(str(iframe or ""))
        fragment = parsed.fragment
        if (parsed.scheme != "https" or (parsed.hostname or "").lower() != "player.upn.one" or
                parsed.path not in ("", "/") or not re.fullmatch(r"[A-Za-z0-9_-]{6}", fragment)):
            raise ValueError("invalid UPN player id")
        if session is None:
            raise RuntimeError("requests required for UPN")

        def get_once_retry(endpoint, headers):
            retryable = (requests.exceptions.Timeout, requests.exceptions.ConnectionError)
            try:
                return session.get(endpoint, headers=headers, timeout=20, allow_redirects=True)
            except retryable:
                return session.get(endpoint, headers=headers, timeout=20, allow_redirects=True)

        def fetch_encrypted(path, identifier):
            endpoint = "https://player.upn.one/api/v1/%s?id=%s" % (path, quote(identifier, safe=""))
            headers = {"User-Agent": UA, "Referer": "https://player.upn.one/", "Accept": "*/*"}
            response = get_once_retry(endpoint, headers)
            response.raise_for_status()
            final = urlparse(str(getattr(response, "url", endpoint)))
            if final.scheme != "https" or (final.hostname or "").lower() != "player.upn.one":
                raise ValueError("UPN API redirected off origin")
            encoded = str(getattr(response, "text", "") or "").strip()
            if (not encoded or len(encoded) > 2 * 1024 * 1024 or len(encoded) % 2 or
                    not re.fullmatch(r"[0-9a-fA-F]+", encoded)):
                raise ValueError("invalid UPN encrypted response")
            return json.loads(self._upn_decrypt(bytes.fromhex(encoded)).decode("utf-8"))

        info = fetch_encrypted("info", fragment)
        if not isinstance(info, dict):
            raise ValueError("invalid UPN info response")
        endpoint = "https://player.upn.one/api/v1/video?id=%s&w=800&h=600&r=" % quote(fragment, safe="")
        headers = {"User-Agent": UA, "Referer": "https://player.upn.one/", "Accept": "*/*"}
        response = get_once_retry(endpoint, headers)
        response.raise_for_status()
        final = urlparse(str(getattr(response, "url", endpoint)))
        if final.scheme != "https" or (final.hostname or "").lower() != "player.upn.one":
            raise ValueError("UPN API redirected off origin")
        encoded = str(getattr(response, "text", "") or "").strip()
        if (not encoded or len(encoded) > 2 * 1024 * 1024 or len(encoded) % 2 or
                not re.fullmatch(r"[0-9a-fA-F]+", encoded)):
            raise ValueError("invalid UPN encrypted response")
        payload = json.loads(self._upn_decrypt(bytes.fromhex(encoded)).decode("utf-8"))

        preferred = []
        fallback = []

        def walk(value, key=""):
            if isinstance(value, dict):
                for child_key, child in value.items():
                    walk(child, str(child_key).lower())
            elif isinstance(value, (list, tuple)):
                for child in value:
                    walk(child, key)
            elif isinstance(value, str) and self._safe_media(value):
                if key in ("source", "streammanifesturl", "manifest", "url", "file"):
                    preferred.append(value)
                else:
                    fallback.append(value)

        walk(payload)
        candidates = preferred + fallback
        if not candidates:
            raise ValueError("UPN response has no approved full media")
        return candidates[0]

    @staticmethod
    def _unpack_packer(text):
        match = re.search(
            r"eval\(function\(p,a,c,k,e,d\).*?\}\('(.*?)',(\d+),(\d+),'(.*?)'\.split\('\|'\)",
            text or "", re.S)
        if not match:
            return ""
        try:
            payload = bytes(match.group(1), "utf-8").decode("unicode_escape")
            radix, count = int(match.group(2)), int(match.group(3))
            words = match.group(4).split("|")
            alphabet = "0123456789abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ"
            if radix < 2 or radix > len(alphabet) or count > 10000:
                return ""

            def token(number):
                if number < radix:
                    return alphabet[number]
                return token(number // radix) + alphabet[number % radix]

            for index in range(count - 1, -1, -1):
                if index < len(words) and words[index]:
                    payload = re.sub(r"\b" + re.escape(token(index)) + r"\b", words[index], payload)
            return payload
        except Exception:
            return ""

    def _extract_media(self, iframe_html, iframe_host):
        if iframe_host == "hglink.to":
            raise ValueError("preview-only provider")
        searchable = str(iframe_html or "")
        if iframe_host == "ryderjet.com":
            searchable += "\n" + self._unpack_packer(searchable)
        candidates = re.findall(
            r"https?:\\?/\\?/[^\"'\s<>]+?\.(?:m3u8|mp4)(?:\?[^\"'\s<>]*)?",
            searchable, re.I)
        for candidate in candidates:
            media = html.unescape(candidate.replace("\\/", "/"))
            if self._safe_media(media):
                return media
        raise ValueError("no approved full media candidate")

    def _parse_detail(self, text, vod_id):
        if self._is_challenge(text):
            raise ValueError("Cloudflare challenge page")
        dom = _DOM()
        dom.feed(text)
        title = _clean(" ".join(dom.h1_parts))
        if not title:
            title = _clean(" ".join(dom.title_parts)).split("|", 1)[0].strip()
        pic = ""
        for src in dom.images:
            absolute = urljoin(BASE + "/", src)
            if self._allowed(absolute, image=True):
                pic = absolute
                break
        actors, genres = [], []
        for link in dom.links:
            href = urljoin(BASE + "/", link.get("href", ""))
            label = _clean(" ".join(link.get("text", [])))
            path = urlparse(href).path
            if label and path.startswith("/actors/"):
                actors.append(label)
            if label and path.startswith("/genres/"):
                genres.append(label)

        def field(name):
            match = re.search(r"<p[^>]*>\s*%s\s*:\s*(.*?)</p>" % re.escape(name), text, re.I | re.S)
            return _clean(re.sub(r"<[^>]+>", " ", match.group(1))) if match else ""

        if not actors and field("Actor(s)"):
            actors = [field("Actor(s)")]
        if not genres and field("Genre(s)"):
            genres = [field("Genre(s)")]
        director = field("Director")
        remarks = " / ".join(x for x in (field("Released Date"), field("Runtime"), field("Studio"), field("Label")) if x)
        desc = ""
        desc_match = re.search(r'<div[^>]+class=["\'][^"\']*mvic-desc[^"\']*["\'][^>]*>(.*?)</div>', text, re.I | re.S)
        if desc_match:
            desc = _clean(re.sub(r"<[^>]+>", " ", desc_match.group(1)))
        choices = self._parse_player_choices(text, vod_id)
        smart = [("智能择优", "fcjav-best:%s" % normalize_slug(vod_id))] if choices else []
        display_choices = smart + choices
        play_from = "$$$".join(label for label, _ in display_choices)
        play_url = "$$$".join(
            "%s$%s" % ("试看" if label.upper() == "SW" else "正片", play_id)
            for label, play_id in display_choices)
        return {
            "vod_id": normalize_slug(vod_id),
            "vod_name": title or str(vod_id).upper(),
            "vod_pic": pic,
            "type_name": ", ".join(dict.fromkeys(genres)),
            "vod_actor": ", ".join(dict.fromkeys(actors)),
            "vod_director": director,
            "vod_remarks": remarks,
            "vod_content": desc or _clean(" ".join(dom.description_parts)),
            "vod_play_from": play_from,
            "vod_play_url": play_url
        }

    # ---------------- 路由 ----------------

    def _page_url(self, tid, pg):
        page = max(1, int(pg or 1))
        if str(tid) == "movies":
            return BASE + "/movies" + ("" if page == 1 else "/pg-%d" % page)
        return BASE + "/movies" + ("" if page == 1 else "/pg-%d" % page)

    def _category_url(self, tid, pg):
        page = max(1, int(pg or 1))
        raw = SHELL_ROUTES.get(str(tid or "movies"), str(tid or "movies")).strip("/")
        clean, sep, query = raw.partition("?")
        if not (clean == "movies" or re.fullmatch(r"(?:genre|actor|studio|label|director)/[a-z0-9-]+", clean)):
            clean = "movies"
            query = ""
        if query and not re.fullmatch(r"genre=(?:amateur|censored|uncensored)", query):
            query = ""
        if clean == "movies" and query:
            return BASE + "/movies?" + query + (("&pg=%d" % page) if page > 1 else "")
        return BASE + "/" + clean + ("" if page == 1 else "/pg-%d" % page)

    def _search_url(self, key):
        return BASE + "/search/" + quote(str(key or "").strip(), safe="")

    @staticmethod
    def _diagnostic(message):
        return {"vod_id": "blocked", "vod_name": "FCJAV 暂不可用", "vod_pic": "", "vod_remarks": str(message)[:80]}

    # ---------------- 首页 ----------------

    def homeContent(self, filter=False):
        filters = {"movies": CATALOG_FILTERS} if filter else {}
        return {"class": list(HOME_CLASSES), "filters": filters}

    def homeVideoContent(self):
        try:
            items, _ = self._parse_list(self._fetch(BASE + "/movies"), BASE + "/movies")
            return {"list": items[:PAGE_SIZE]}
        except Exception as e:
            self.last_error = type(e).__name__
            return {"list": [self._diagnostic("Cloudflare/网络阻塞")]}

    # ---------------- 分类 ----------------

    def categoryContent(self, tid, pg, filter=False, extend=None):
        page = max(1, int(pg or 1))
        route = str(tid or "movies")
        if isinstance(extend, dict):
            for key in ("genre", "actor", "studio", "label", "director"):
                value = str(extend.get(key, "") or "")
                if value:
                    route = value
                    break
        url = self._category_url(route, page)
        try:
            items, has_next = self._parse_list(self._fetch(url), url)
            if SHELL_ROUTES.get(route, route).startswith("movies?genre=") and len(items) >= PAGE_SIZE:
                has_next = True
            return {"list": items, "page": page, "pagecount": page + (1 if has_next else 0), "limit": PAGE_SIZE, "total": len(items)}
        except Exception as e:
            self.last_error = type(e).__name__
            return {"list": [self._diagnostic("Cloudflare/网络阻塞")], "page": page, "pagecount": page, "limit": PAGE_SIZE, "total": 0}

    # ---------------- 搜索 ----------------

    def searchContent(self, key, quick=False, pg="1"):
        url = self._search_url(key)
        if url.endswith("/search/"):
            return {"list": []}
        try:
            items, _ = self._parse_list(self._fetch(url), url)
            return {"list": items, "page": 1, "pagecount": 1, "limit": PAGE_SIZE, "total": len(items)}
        except Exception as e:
            self.last_error = type(e).__name__
            return {"list": [self._diagnostic("Cloudflare/网络阻塞")]}

    # ---------------- 详情 ----------------

    def detailContent(self, ids):
        vod_id = ids[0] if isinstance(ids, (list, tuple)) and ids else ids
        slug = normalize_slug(vod_id)
        if not slug:
            return {"list": []}
        try:
            vod = self._parse_detail(self._fetch(BASE + "/v/" + slug), slug)
            return {"list": [vod]}
        except Exception as e:
            self.last_error = type(e).__name__
            return {"list": [self._diagnostic("详情受 Cloudflare/网络阻塞")]}

    # ---------------- 播放 ----------------

    def _discover_media(self, parts):
        slug, film_id, episode = parts
        detail_url = BASE + "/v/" + slug
        session = self._new_play_session()
        opener = build_opener(HTTPCookieProcessor(CookieJar()))

        def read(url, method="GET", data=None, headers=None, cap=2 * 1024 * 1024, use_session=False):
            headers = headers or {}
            if use_session and session is not None:
                if method == "POST":
                    response = session.post(url, data=data, headers=headers, timeout=20, allow_redirects=True)
                else:
                    response = session.get(url, headers=headers, timeout=20, allow_redirects=True)
                response.raise_for_status()
                raw = response.content
                final_url = response.url
                content_type = (response.headers.get("Content-Type") or "").lower()
            else:
                request = Request(url, data=data if method == "POST" else None, headers=headers)
                with opener.open(request, timeout=20) as response:
                    raw = response.read(cap + 1)
                    final_url = response.geturl()
                    content_type = (response.headers.get("Content-Type") or "").lower()
            if len(raw) > cap:
                raise ValueError("response too large")
            return raw, final_url, content_type

        detail_raw, _, detail_type = read(detail_url, headers={"User-Agent": UA, "Accept": "text/html"})
        if "html" not in detail_type:
            raise ValueError("unexpected detail content type")
        detail = detail_raw.decode("utf-8", "replace")
        if self._is_challenge(detail):
            raise ValueError("challenge")
        choices = self._parse_player_choices(detail, slug)
        selected = "fcjav:%s:%s:%s" % (slug, film_id, episode)
        if selected not in {row[1] for row in choices}:
            raise ValueError("source not present on detail page")
        pt, pk = self._parse_player_bootstrap(detail)
        if not pt or not pk:
            raise ValueError("missing fresh player bootstrap")
        post = urlencode({"episode": episode, "filmId": film_id, "pt": pt}).encode("ascii")
        ajax_headers = {
            "User-Agent": UA, "Referer": detail_url,
            "X-Requested-With": "XMLHttpRequest",
            "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8",
        }
        ajax_raw, _, _ = read(BASE + "/ajax/player", method="POST", data=post, headers=ajax_headers, cap=1024 * 1024)
        item = json.loads(ajax_raw.decode("utf-8", "replace"))
        if item.get("error"):
            raise ValueError("player endpoint rejected request")
        player_html = self._xor_decrypt(item.get("player_enc", ""), pk) if item.get("player_enc") else str(item.get("player", ""))
        iframe_match = re.search(r'<iframe[^>]+src=["\']([^"\']+)', player_html, re.I)
        if not iframe_match:
            raise ValueError("missing iframe")
        iframe = urljoin(detail_url, iframe_match.group(1))
        if not self._safe_iframe(iframe):
            raise ValueError("unapproved iframe")
        parsed_iframe = urlparse(iframe)
        if (parsed_iframe.hostname or "").lower() == "player.upn.one":
            return self._extract_upn_media(iframe, session)
        iframe_raw, iframe_final, iframe_type = read(iframe, headers={"User-Agent": UA, "Referer": detail_url, "Accept": "text/html"})
        if "html" not in iframe_type:
            raise ValueError("unexpected iframe content type")
        iframe_html = iframe_raw.decode("utf-8", "replace")
        return self._extract_media(iframe_html, (urlparse(iframe_final).hostname or parsed_iframe.hostname or "").lower())

    def _new_play_session(self):
        if requests is None:
            return None
        session = requests.Session()
        session.headers.update({"User-Agent": UA})
        return session

    def playerContent(self, flag, id, vipFlags=None):
        best_slug = self._parse_best_id(id)
        parts = self._parse_play_id(id)
        if not parts and not best_slug:
            return {"parse": 1, "url": "", "header": {"User-Agent": UA}}
        try:
            if best_slug:
                media = self._discover_best_media(best_slug)
            else:
                cached = self._play_cache.get(str(id))
                if cached and cached[1] > time.time():
                    media = cached[0]
                else:
                    self._play_cache.pop(str(id), None)
                    try:
                        media = self._discover_media(parts)
                    except ValueError as first_error:
                        if str(first_error) != "UPN response has no approved full media":
                            raise
                        media = self._discover_media(parts)
            if not self._safe_media(media):
                raise ValueError("unsafe media")
            return {"parse": 0, "url": media, "header": {"User-Agent": UA, "Referer": self._media_referer(media)}}
        except Exception as e:
            self.last_error = type(e).__name__
            return {"parse": 1, "url": "", "header": {"User-Agent": UA}}

    def localProxy(self, param):
        return [200, "text/plain; charset=utf-8", b"ok", {}]


# 兼容旧代码的 urllib import
from urllib.request import Request, urlopen, build_opener
from urllib.error import HTTPError, URLError
from http.cookiejar import CookieJar

if __name__ == "__main__":
    s = Spider()
    print(json.dumps(s.homeContent(False), ensure_ascii=False))