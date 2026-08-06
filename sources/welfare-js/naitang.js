/**
 * 奶糖视频 JavaScript Spider（修复版 v2.1）
 *
 * 适配 vbox iOS 福利专区 WelfareJSSpiderService。
 *
 * v2.1 在远程基线上叠加的增强：
 *  1) CF 5 秒盾检测 + 5s 等待 + 一次重试
 *  2) Cookie 透传：cookieJar 自动注入 Cookie 头并提取 Set-Cookie
 *  3) 探测超时：单 host 5s 超时，避免卡死
 *  4) b64Decode 强化：URL-safe（-/_）+ 缺 = 补齐 + 套娃 base64
 *  5) playerContent 多模式：player_aaaa/MacPlayer/字符串对/iframe src?url=/宽松 m3u8
 *  6) playerContent 失败返回 url:'' 而非 url:id，避免客户端死循环
 *  7) playerContent header.Referer 改为播放页 URL 自身 + Cookie 透传
 *  8) categoryCache LRU + 动态 pagecount
 */

var spider = (function () {
    var domainList = [
        'https://ewrzka4.naitang8.top'
    ];

    var host = '';
    var hostReady = false;

    var ua = 'Mozilla/5.0 (Linux; Android 11; SAMSUNG SM-G973U) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/87.0.4280.141 Mobile Safari/537.36';

    // 单 host 探测超时（毫秒）
    var PROBE_TIMEOUT_MS = 5000;
    // CF 5秒盾等待时长（毫秒）
    var CF_WAIT_MS = 5000;
    // CF 5秒盾重试次数
    var CF_RETRY = 1;

    var cache = {};
    // 分类结果 LRU 缓存
    var categoryCache = {};
    var categoryCacheOrder = [];
    var CATEGORY_CACHE_MAX = 50;
    // ★ v2.1：cookieJar
    var cookieJar = {};

    var headers = {
        'User-Agent': ua,
        'Referer': 'https://ewrzka4.naitang8.top/',
        'Origin': 'https://ewrzka4.naitang8.top',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
        'Accept-Language': 'zh-CN,zh;q=0.9'
    };

    var fallback = [
        { type_id: '1', type_name: '中文字幕' },
        { type_id: '6', type_name: '日本有码' },
        { type_id: '2', type_name: 'cosplay' },
        { type_id: '7', type_name: '日本无码' },
        { type_id: '3', type_name: '黑丝诱惑' },
        { type_id: '8', type_name: '解说专区' }
    ];

    function log(msg) {
        try { if (typeof print === 'function') print('[naitang] ' + msg); } catch (e) {}
    }

    function trimSlash(u) {
        return String(u || '').replace(/\/+$/, '');
    }

    // ====== v2.1：CF / Cookie / sleep ======

    function isCloudflareChallenge(text) {
        if (!text || text.length < 100) return false;
        return /Just a moment|Checking your browser|cf-chl-bypass|cdn-cgi\/challenge-platform|Attention Required|Enable JavaScript and cookies|cf_clearance|__cf_bm/i.test(text);
    }

    function sleepSync(ms) {
        var t0 = Date.now();
        while (Date.now() - t0 < ms) {}
    }

    function extractSetCookie(headersObj) {
        if (!headersObj) return;
        var sc = headersObj['Set-Cookie'] || headersObj['set-cookie'] || '';
        if (!sc) return;
        var pairs = String(sc).split(/,(?=\s*[A-Za-z0-9_]+=)/);
        for (var i = 0; i < pairs.length; i++) {
            var kv = pairs[i].split(';')[0];
            var idx = kv.indexOf('=');
            if (idx > 0) {
                var name = kv.substring(0, idx).trim();
                var val = kv.substring(idx + 1).trim();
                if (name && val !== '' && val !== 'deleted') {
                    cookieJar[name] = val;
                }
            }
        }
    }

    function buildCookieHeader() {
        var arr = [];
        for (var k in cookieJar) {
            if (Object.prototype.hasOwnProperty.call(cookieJar, k) && cookieJar[k]) {
                arr.push(k + '=' + cookieJar[k]);
            }
        }
        return arr.join('; ');
    }

    // ★ v2.1：get 支持 Cookie 注入 + CF 检测
    function get(url) {
        if (!url) return '';
        if (cache[url]) return cache[url];

        var bizHeaders = {};
        for (var k in headers) {
            bizHeaders[k] = headers[k];
        }
        var ck = buildCookieHeader();
        if (ck) bizHeaders['Cookie'] = ck;

        var text = '';
        var resp;
        try {
            resp = req(url, { headers: bizHeaders });
            text = resp && resp.content ? String(resp.content) : '';
            if (resp && resp.headers) extractSetCookie(resp.headers);
        } catch (e) {
            log('请求失败: ' + url + ' ' + e);
            cache[url] = '';
            return '';
        }

        // CF 5秒盾等待 + 重试
        if (isCloudflareChallenge(text)) {
            for (var attempt = 0; attempt < CF_RETRY; attempt++) {
                log('CF 5秒盾触发，等待 ' + (CF_WAIT_MS / 1000) + 's 后重试: ' + url);
                sleepSync(CF_WAIT_MS);
                try {
                    resp = req(url, { headers: bizHeaders });
                    text = resp && resp.content ? String(resp.content) : '';
                    if (resp && resp.headers) extractSetCookie(resp.headers);
                } catch (e2) {
                    log('CF 重试请求失败: ' + e2);
                    continue;
                }
                if (!isCloudflareChallenge(text)) {
                    log('CF 重试通过');
                    break;
                }
            }
            if (isCloudflareChallenge(text)) {
                log('CF 重试仍失败: ' + url);
                cache[url] = '';
                return '';
            }
        }

        cache[url] = text;
        return text;
    }

    function fixUrl(u) {
        u = String(u || '').trim();
        if (!u) return '';
        if (u.indexOf('//') === 0) return 'https:' + u;
        if (/^https?:\/\//i.test(u)) return u;
        if (u.charAt(0) === '/') return trimSlash(host) + u;
        return u;
    }

    function okDomain(u) {
        var base = trimSlash(u);
        try {
            var probeHeaders = {};
            for (var k in headers) {
                probeHeaders[k] = headers[k];
            }
            probeHeaders['Range'] = 'bytes=0-4095';
            var ck = buildCookieHeader();
            if (ck) probeHeaders['Cookie'] = ck;
            var resp = req(base + '/', { headers: probeHeaders, timeout: PROBE_TIMEOUT_MS });
            var text = resp && resp.content ? String(resp.content) : '';
            if (resp && resp.headers) extractSetCookie(resp.headers);
            if (isCloudflareChallenge(text)) return false;
            return text.length > 200 && /(奶糖视频|naitang|vod\/detail|vod\/type|player_aaaa)/i.test(text);
        } catch (e) {
            log('探测失败: ' + u + ' ' + e);
        }
        return false;
    }

    function pickDomain() {
        for (var i = 0; i < domainList.length; i++) {
            if (okDomain(domainList[i])) return trimSlash(domainList[i]);
        }
        return '';
    }

    function ensureHost() {
        if (!host) {
            host = pickDomain();
            hostReady = !!host;
            if (hostReady) {
                headers.Referer = host + '/';
                headers.Origin = host;
                log('当前域名: ' + host);
            } else {
                log('未找到可用域名');
            }
        }
        return host;
    }

    // ====== 工具函数 ======

    function decodeEscapes(s) {
        s = String(s || '');
        try {
            s = s.replace(/\\u([0-9a-fA-F]{4})/g, function (_, hex) {
                return String.fromCharCode(parseInt(hex, 16));
            });
            s = s.replace(/\\x([0-9a-fA-F]{2})/g, function (_, hex) {
                return String.fromCharCode(parseInt(hex, 16));
            });
        } catch (e) {}
        return s;
    }

    function unescapeHTML(s) {
        return decodeEscapes(String(s || ''))
            .replace(/&nbsp;/gi, ' ')
            .replace(/&amp;/gi, '&')
            .replace(/&quot;/gi, '"')
            .replace(/&#39;/g, "'")
            .replace(/&apos;/gi, "'")
            .replace(/&lt;/gi, '<')
            .replace(/&gt;/gi, '>')
            .replace(/&#x([0-9a-fA-F]+);/g, function (_, hex) {
                return String.fromCharCode(parseInt(hex, 16));
            })
            .replace(/&#(\d+);/g, function (_, dec) {
                return String.fromCharCode(parseInt(dec, 10));
            });
    }

    // ★ v2.1：b64Decode 强化（URL-safe + 缺 = 补齐）
    function b64Decode(s) {
        if (!s) return '';
        var str = String(s).replace(/-/g, '+').replace(/_/g, '/');
        while (str.length % 4 !== 0) str += '=';
        try {
            if (typeof crypto !== 'undefined' && crypto.base64 && crypto.base64.decode) {
                var d = crypto.base64.decode(str);
                if (d) return d;
            }
        } catch (e) {}
        var chars = 'ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789+/=';
        str = str.replace(/[^A-Za-z0-9+/=]/g, '');
        var output = '';
        for (var bc = 0, bs, buffer, idx = 0; (buffer = str.charAt(idx++)); ) {
            buffer = chars.indexOf(buffer);
            if (buffer < 0) continue;
            bs = bc % 4 ? bs * 64 + buffer : buffer;
            if (bc++ % 4) output += String.fromCharCode(255 & (bs >> ((-2 * bc) & 6)));
        }
        return output;
    }

    function decodePlayUrl(value) {
        value = String(value || '').replace(/\\/g, '');
        if (!value) return '';
        if (/^https?:\/\//i.test(value)) return value;
        try {
            var decoded = b64Decode(value);
            decoded = decodeEscapes(decoded).replace(/\\\//g, '/');
            try { decoded = decodeURIComponent(decoded); } catch (e0) {}
            if (/^https?:\/\//i.test(decoded)) return decoded;
            // ★ v2.1：套娃 base64
            if (decoded && !/^https?:\/\//i.test(decoded) && /^[A-Za-z0-9+/_=\-]{20,}$/.test(decoded.trim())) {
                var d2 = b64Decode(decoded.trim());
                d2 = decodeEscapes(d2).replace(/\\\//g, '/');
                try { d2 = decodeURIComponent(d2); } catch (e1) {}
                if (/^https?:\/\//i.test(d2)) return d2;
            }
        } catch (e1) {}
        try { value = decodeURIComponent(value); } catch (e2) {}
        return decodeEscapes(value).replace(/\\\//g, '/');
    }

    function txt(s) {
        return unescapeHTML(String(s || '').replace(/<[^>]+>/g, '')).replace(/\s+/g, ' ').trim();
    }

    function match(text, rule) {
        var m = rule.exec(String(text || ''));
        return m ? (m[1] || '') : '';
    }

    function isVideoFormat(url) {
        return /\.(m3u8|mp4|flv|avi|mkv|mov|ts)(\?|$)/i.test(String(url || ''));
    }

    function cleanName(name) {
        return txt(name)
            .replace(/在线观看/g, '')
            .replace(/奶糖视频/g, '')
            .replace(/《/g, '')
            .replace(/》/g, '')
            .trim();
    }

    function pickPic(block) {
        var regs = [
            /(?:data-original|data-src|data-lazyload|data-lazy-src)=["']([^"']+\.(?:jpg|jpeg|png|webp|gif)[^"']*)["']/ig,
            /src=["']([^"']+\.(?:jpg|jpeg|png|webp|gif)[^"']*)["']/ig
        ];
        for (var r = 0; r < regs.length; r++) {
            var m;
            while ((m = regs[r].exec(block)) !== null) {
                var p = String(m[1] || '');
                var lower = p.toLowerCase();
                if (lower.indexOf('load.gif') < 0 && lower.indexOf('nopic') < 0 && lower.indexOf('logo') < 0 && lower.indexOf('template') < 0) {
                    return fixUrl(p);
                }
            }
        }
        return '';
    }

    function parseList(html) {
        var res = [];
        var seen = {};
        var text = String(html || '');
        var reg = /<a[^>]+class=["'][^"']*video-img[^"']*["'][^>]+href=["']\/index\.php\/vod\/detail\/id\/(\d+)\.html["'][^>]*([\s\S]{0,1600}?)<\/a>[\s\S]{0,500}?<p[^>]+class=["'][^"']*video-name[^"']*["'][^>]*>\s*<a[^>]+[^>]*title=["']([^"']+)["']/ig;
        var m;
        while ((m = reg.exec(text)) !== null) {
            var vid = m[1];
            if (seen[vid]) continue;
            seen[vid] = true;
            var item = m[0] + (m[2] || '');
            var name = txt(m[3]);
            if (!name) continue;
            res.push({
                vod_id: vid,
                vod_name: name,
                vod_pic: pickPic(item),
                vod_remarks: txt(match(item, /<span[^>]+class=["'][^"']*voddate[^"']*["'][^>]*>([\s\S]*?)<\/span>/i) || match(item, /<span[^>]+class=["'][^"']*note[^"']*["'][^>]*>([\s\S]*?)<\/span>/i))
            });
        }

        if (res.length) return res;

        var reg2 = /href=["']\/index\.php\/vod\/detail\/id\/(\d+)\.html["'][^>]*[\s\S]{0,1000}?title=["']([^"']+)["'][\s\S]{0,1200}?<img[^>]+([^>]+)>/ig;
        while ((m = reg2.exec(text)) !== null) {
            var id = m[1];
            if (seen[id]) continue;
            seen[id] = true;
            var img = m[3] || '';
            var pic = match(img, /(?:data-original|data-src|data-lazyload|data-lazy-src)=["']([^"']+)["']/i) || match(img, /src=["']([^"']+)["']/i);
            var lower = String(pic || '').toLowerCase();
            if (lower.indexOf('load.gif') >= 0 || lower.indexOf('template') >= 0) pic = '';
            res.push({
                vod_id: id,
                vod_name: txt(m[2]),
                vod_pic: fixUrl(pic),
                vod_remarks: ''
            });
        }

        if (res.length) return res;

        var blocks = text.match(/<article[^>]+class=["'][^"']*post-list[^"']*["'][\s\S]*?<\/article>/ig) || [];
        for (var i = 0; i < blocks.length; i++) {
            var b = blocks[i];
            var hm = /href=["']\/index\.php\/vod\/detail\/id\/(\d+)\.html["'][^>]*title=["']([^"']+)["']/i.exec(b);
            if (!hm) {
                hm = /href=["']\/index\.php\/vod\/detail\/id\/(\d+)\.html["'][^>]*>([\s\S]*?)<\/a>/i.exec(b);
            }
            if (!hm) continue;
            var bid = hm[1];
            if (seen[bid]) continue;
            seen[bid] = true;
            var bpic = pickPic(b);
            var bname = txt(hm[2]);
            var br = txt(match(b, /<em[^>]+class=["'][^"']*voddate[^"']*["'][^>]*>([\s\S]*?)<\/em>/i));
            if (bname) {
                res.push({
                    vod_id: bid,
                    vod_name: bname,
                    vod_pic: bpic,
                    vod_remarks: br
                });
            }
        }
        return res;
    }

    function categoryUrl(tid, pg) {
        pg = parseInt(pg || '1', 10);
        if (!pg || pg < 1) pg = 1;
        tid = String(tid || '1');
        if (pg === 1) return host + '/index.php/vod/type/id/' + tid + '.html';
        return host + '/index.php/vod/show/id/' + tid + '/page/' + pg + '.html';
    }

    function detailUrl(id) {
        return host + '/index.php/vod/detail/id/' + String(id || '') + '.html';
    }

    function playUrl(path) {
        return fixUrl(path);
    }

    // ★ v2.1：分类 LRU 缓存
    function categoryCacheGet(tid, pg) {
        return categoryCache[tid + '_' + pg];
    }
    function categoryCachePut(tid, pg, result) {
        var key = tid + '_' + pg;
        if (!categoryCache[key]) {
            categoryCacheOrder.push(key);
            if (categoryCacheOrder.length > CATEGORY_CACHE_MAX) {
                var oldKey = categoryCacheOrder.shift();
                delete categoryCache[oldKey];
            }
        }
        categoryCache[key] = result;
    }

    return {
        init: function (config) {
            if (config && config.hosts && config.hosts.length) {
                domainList = config.hosts;
            }
            ensureHost();
            return true;
        },

        homeContent: function () {
            ensureHost();
            if (!hostReady) return { class: fallback, list: [] };
            return { class: fallback, filters: {}, list: parseList(get(host + '/')) };
        },

        homeVideoContent: function () {
            ensureHost();
            if (!hostReady) return { list: [] };
            return { list: parseList(get(host + '/')) };
        },

        // ★ v2.1：categoryContent 加 LRU + 动态 pagecount
        categoryContent: function (tid, pg) {
            ensureHost();
            pg = parseInt(pg || '1', 10);
            if (!pg || pg < 1) pg = 1;
            if (!hostReady) return { page: pg, pagecount: 1, limit: 24, total: 0, list: [] };
            var cached = categoryCacheGet(tid, pg);
            if (cached) return cached;

            var items = parseList(get(categoryUrl(tid, pg)));
            var pagecount = items.length === 0 ? (pg > 1 ? pg - 1 : 1) : 999;
            var result = {
                page: pg,
                pagecount: pagecount,
                limit: 24,
                total: pagecount === 999 ? 999999 : (pagecount * 24),
                list: items
            };
            categoryCachePut(tid, pg, result);
            return result;
        },

        detailContent: function (ids) {
            ensureHost();
            if (!hostReady) return { list: [] };
            var vid = Array.isArray(ids) ? ids[0] : ids;
            vid = String(vid || '');
            var html = get(detailUrl(vid));
            var name = cleanName(match(html, /<h1[^>]*>([\s\S]*?)<\/h1>/i) || match(html, /<meta property=["']og:title["'] content=["']([^"']+)/i));
            var pic = fixUrl(
                match(html, /<meta property=["']og:image["'] content=["']([^"']+)/i)
                || match(html, /<a[^>]+class=["'][^"']*video-img[^"']*["'][^>]+(?:data-original|data-src)=["']([^"']+)/i)
                || match(html, /<img[^>]+(?:data-original|data-src)=["']([^"']+)/i)
            );
            var desc = txt(match(html, /剧情：([\s\S]*?)</i) || match(html, /<meta property=["']og:description["'] content=["']([^"']+)/i));
            var actor = txt(match(html, /演员：<\/span>([\s\S]*?)<\/p>/i) || match(html, /主演：<\/span>([\s\S]*?)<\/p>/i));
            var director = txt(match(html, /导演：<\/span>([\s\S]*?)<\/p>/i));
            var year = txt(match(html, /年份：<\/span>([^<]+)/i));
            var area = txt(match(html, /地区：<\/span>([^<]+)/i));
            var lang = txt(match(html, /语言：<\/span>([^<]+)/i));
            var cate = txt(match(html, /类型：<\/span>([\s\S]*?)<\/p>/i));
            var remarks = txt(match(html, /<span[^>]+class=["'][^"']*voddate[^"']*["'][^>]*>([\s\S]*?)<\/span>/i) || match(html, /状态：<\/span>([^<]+)/i));

            var tabs = [];
            var tm;
            var tabReg = /<li[^>]+class=["'][^"']*ewave-tab[^"']*["'][^>]*[\s\S]*?<a[^>]*>([\s\S]*?)<\/a>/ig;
            while ((tm = tabReg.exec(html)) !== null) tabs.push(txt(tm[1]));

            var panels = [];
            var pm;
            var panelReg = /<ul[^>]+class=["'][^"']*playlist[^"']*["'][^>]*>([\s\S]*?)<\/ul>/ig;
            while ((pm = panelReg.exec(html)) !== null) panels.push(pm[1]);

            var playFrom = [];
            var playUrls = [];
            for (var i = 0; i < panels.length; i++) {
                var eps = [];
                var epReg = new RegExp("<a[^>]+href=[\"']([^\"']*?/index\\\\.php/vod/play/id/" + vid + "/sid/\\\\d+/nid/\\\\d+\\\\.html)[\"'][^>]*>([\\\\s\\\\S]*?)</a>", 'ig');
                var em;
                while ((em = epReg.exec(panels[i])) !== null) {
                    var title = txt(em[2]) || '播放';
                    var url = playUrl(em[1]);
                    if (title && url) eps.push(title + '$' + url);
                }
                if (!eps.length) {
                    var epReg2 = /<a[^>]+href=["']([^"']*?\/index\.php\/vod\/play\/[^"']+)["'][^>]*>([\s\S]*?)<\/a>/ig;
                    while ((em = epReg2.exec(panels[i])) !== null) {
                        var t2 = txt(em[2]) || '播放';
                        var u2 = playUrl(em[1]);
                        if (t2 && u2) eps.push(t2 + '$' + u2);
                    }
                }
                if (eps.length) {
                    var key = (i < tabs.length && tabs[i]) ? tabs[i] : '线路' + (i + 1);
                    if (playFrom.indexOf(key) < 0) {
                        playFrom.push(key);
                        playUrls.push(eps.join('#'));
                    }
                }
            }

            if (!playUrls.length) {
                var all = [];
                var allReg = new RegExp("<a[^>]+href=[\"']([^\"']*?/index\\\\.php/vod/play/id/" + vid + "/sid/\\\\d+/nid/\\\\d+\\\\.html)[\"'][^>]*>([\\\\s\\\\S]*?)</a>", 'ig');
                var am;
                while ((am = allReg.exec(html)) !== null) {
                    var at = txt(am[2]) || '高清';
                    var au = playUrl(am[1]);
                    if (at && au) all.push(at + '$' + au);
                }
                if (all.length) {
                    playFrom.push('默认');
                    playUrls.push(all.join('#'));
                }
            }

            return {
                list: [{
                    vod_id: vid,
                    vod_name: name,
                    vod_pic: pic,
                    vod_remarks: remarks,
                    type_name: cate,
                    vod_year: year,
                    vod_area: area,
                    vod_lang: lang,
                    vod_actor: actor,
                    vod_director: director,
                    vod_content: desc,
                    vod_play_from: playFrom.join('$$$'),
                    vod_play_url: playUrls.join('$$$')
                }]
            };
        },

        searchContent: function (key, quick, pg) {
            ensureHost();
            pg = parseInt(pg || '1', 10);
            if (!pg || pg < 1) pg = 1;
            if (!hostReady) return { list: [], page: pg, pagecount: 1, limit: 24, total: 0 };
            var url = host + '/index.php/vod/search.html?wd=' + encodeURIComponent(key || '') + '&page=' + pg;
            return { list: parseList(get(url)), page: pg, pagecount: 999, limit: 24, total: 999999 };
        },

        // ★ v2.2：playerContent 强化 + 失败返回空 url + Cookie 透传
        playerContent: function (flag, id) {
            ensureHost();
            var baseHost = host ? (host + '/') : 'https://ewrzka4.naitang8.top/';
            // ★ v2.2：Referer 用 host（站点域名），不是播放页 URL
            //         m3u8 CDN 防盗链校验 Referer 必须是站点域名，用播放页 URL 会被 403
            var ck = buildCookieHeader();
            var videoHeaders = {
                'User-Agent': ua,
                'Referer': baseHost,
                'Origin': baseHost.replace(/\/+$/, '')
            };
            if (ck) videoHeaders['Cookie'] = ck;

            if (!hostReady) {
                return { parse: 1, playUrl: '', url: '', header: videoHeaders };
            }
            var html = get(id);
            var url = '';

            // 1. 尝试 player_aaaa / MacPlayer / player_data 等播放器变量
            var playerVars = ['player_aaaa', 'MacPlayer', 'player_data', 'mac_player_data', 'player_config'];
            for (var vi = 0; vi < playerVars.length; vi++) {
                var vname = playerVars[vi];
                var vreg = new RegExp(vname + '\\s*=\\s*(\\{[\\s\\S]*?\\})\\s*[;<\\n]', 'i');
                var vm = vreg.exec(html);
                if (!vm) continue;
                try {
                    var raw = vm[1].replace(/\\\//g, '/').replace(/'/g, '"');
                    var data = JSON.parse(raw);
                    url = data.url || data.link || data.video || data.src || '';
                    if (url) break;
                } catch (e) {
                    var um = /["']?url["']?\s*:\s*["']([^"']+)["']/i.exec(vm[1]);
                    if (um) { url = um[1]; break; }
                }
            }

            // 2. 尝试直接匹配 JSON 中的 url 字段
            if (!url) {
                url = match(html, /"url"\s*:\s*"([^"]+)"/i)
                   || match(html, /'url'\s*:\s*'([^']+)'/i)
                   || match(html, /"link"\s*:\s*"([^"]+)"/i);
            }

            // 3. ★ v2.1：iframe 第三方播放器 src 携带 ?url=
            if (!url) {
                var ifm = /<iframe[^>]+src=["']([^"']+)["']/i.exec(html);
                if (ifm) {
                    var qm = /[?&]url=([^&"']+)/.exec(ifm[1]);
                    if (qm) {
                        try { url = decodeURIComponent(qm[1]); } catch (e0) { url = qm[1]; }
                    }
                }
            }

            // 4. ★ v2.1：宽松 m3u8 / mp4 匹配
            if (!url) {
                var dm = /https?:\/\/[^\s"'<>\\]+?\.(?:m3u8|mp4)(?:\?[^\s"'<>\\]*)?/i.exec(String(html || ''));
                url = dm ? dm[0] : '';
            }

            url = decodePlayUrl(url);
            if (url) url = fixUrl(url);

            // ★ v2.1：失败返回 url:'' 让客户端走错误态（而非回传 id 导致死循环）
            return {
                parse: url ? 0 : 1,
                playUrl: '',
                url: url || '',
                header: videoHeaders
            };
        }
    };
})();
