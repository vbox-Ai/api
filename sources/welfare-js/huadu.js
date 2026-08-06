/**
 * 花都影视 JavaScript Spider（修复版 v2.1）
 *
 * 适配 vbox iOS 福利专区 WelfareJSSpiderService。
 *
 * v2.1 在远程基线上叠加的增强（不破坏原有 pubUrls/hdfby 回退链路）：
 *  1) 域名探测：单 host 5s 超时，整体最多 6s，探测只取首部 4KB 做签名
 *  2) CF 5 秒盾检测 + 5s 等待 + 一次重试（仓库侧能做，无 WASM）
 *  3) Cookie 透传：模块作用域 cookieJar，自动注入 Cookie 头并提取 Set-Cookie
 *  4) UA 一致性：get 接受 opts.ua 覆盖；探测/业务用 ua，播放用 mobileUA
 *  5) playerContent 多模式解析：player_xxx={} / 字符串对 / iframe src?url= / 宽松 m3u8
 *  6) b64Decode 强化：URL-safe（-/_）+ 缺 = 补齐 + 套娃 base64
 *  7) m3u8 正则宽松匹配（允许空白、换行、属性分隔）
 *  8) categoryCache 模块级 LRU，Tab 切回即时返回；动态 pagecount 避免无限加载
 *  9) playerContent 失败时返回 url: '' 而非 url: id，让客户端走错误态
 * 10) playerContent header.Referer 改为播放页 URL 自身，贴合 m3u8 CDN 校验
 */

var spider = (function () {
    // ★ hdfby 发布页回退链路（init 时由 config.hosts 中的 hdfby 域名覆盖）
    var pubUrls = [
        'https://abc.hdfby.com',
        'https://b.hdfby.com',
        'https://b.hdfby.net',
        'https://b.hdfby.org'
    ];

    // ★ 主域名（init 时由 config.hosts 中的非 hdfby 域名覆盖）
    var domainList = [
        'https://hd28.huadutx.com/',
        'https://rb.huaduys.org/'
    ];

    var ua = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/129.0.0.0 Safari/537.36 Edg/129.0.0.0';
    var mobileUA = 'Mozilla/5.0 (Linux; Android 12; Pixel 3 XL) AppleWebKit/537.36 Chrome/98.0.4758.101 Mobile Safari/537.36';

    var host = '';
    var hostReady = false;

    // 单 host 探测超时（毫秒）
    var PROBE_TIMEOUT_MS = 5000;
    // 域名探测总体上限（毫秒）
    var PROBE_TOTAL_TIMEOUT_MS = 6000;
    // CF 5秒盾等待时长（毫秒）
    var CF_WAIT_MS = 5000;
    // CF 5秒盾重试次数
    var CF_RETRY = 1;

    // HTML 内容缓存（按 URL）
    var cache = {};
    // 分类结果 LRU 缓存（按 cid + pg）
    var categoryCache = {};
    var categoryCacheOrder = [];
    var CATEGORY_CACHE_MAX = 50;
    // ★ v2.1：模块作用域 cookieJar（key=name, value=value）
    var cookieJar = {};

    var headers = {
        'User-Agent': ua,
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
        'Referer': 'https://hd28.huadutx.com/',
        'Accept-Language': 'zh-CN,zh;q=0.9'
    };

    var fallback = [
        { type_id: '/vodshow/1-----------.html', type_name: '中文字幕' },
        { type_id: '/vodshow/2-----------.html', type_name: '无字幕' },
        { type_id: '/vodshow/3-----------.html', type_name: '国产' },
        { type_id: '/vodshow/4-----------.html', type_name: '动漫' },
        { type_id: '/vodshow/5-----------.html', type_name: '欧美' },
        { type_id: '/vodshow/6-----------.html', type_name: '中字无码' },
        { type_id: '/vodshow/7-----------.html', type_name: '中字有码' },
        { type_id: '/vodshow/8-----------.html', type_name: '步兵无码' },
        { type_id: '/vodshow/9-----------.html', type_name: '骑兵有码' },
        { type_id: '/vodshow/10-----------.html', type_name: '国产精品' },
        { type_id: '/vodshow/11-----------.html', type_name: '国产传媒' },
        { type_id: '/vodshow/12-----------.html', type_name: '糖心Vlog' },
        { type_id: '/vodshow/13-----------.html', type_name: '欧美中字' },
        { type_id: '/vodshow/14-----------.html', type_name: '中字里番' },
        { type_id: '/vodshow/15-----------.html', type_name: '3D动漫' },
        { type_id: '/vodshow/16-----------.html', type_name: 'AI短剧' }
    ];

    function log(msg) {
        try { if (typeof print === 'function') print('[huadu] ' + msg); } catch (e) {}
    }

    // ====== v2.1：CF 5秒盾 / Cookie / sleep ======

    // ★ v2.1：CF 5秒盾检测
    function isCloudflareChallenge(text) {
        if (!text || text.length < 100) return false;
        return /Just a moment|Checking your browser|cf-chl-bypass|cdn-cgi\/challenge-platform|Attention Required|Enable JavaScript and cookies|cf_clearance|__cf_bm/i.test(text);
    }

    // ★ v2.1：JS 同步 sleep（无 setTimeout）
    function sleepSync(ms) {
        var t0 = Date.now();
        while (Date.now() - t0 < ms) {
            // 忙等
        }
    }

    // ★ v2.1：cookieJar 维护
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

    // ★ v2.1：get 支持 opts.ua 覆盖 UA + Cookie 注入 + CF 检测
    function get(url, opts) {
        opts = opts || {};
        if (!url) return '';
        if (cache[url]) return cache[url];

        // 选 UA：mobile > 默认 ua
        var useUA = opts.ua === 'mobile' ? mobileUA : ua;

        // 业务 headers（不带 Range，保留所有自定义头）
        var bizHeaders = {};
        for (var k in headers) {
            bizHeaders[k] = headers[k];
        }
        bizHeaders['User-Agent'] = useUA;
        // ★ v2.1：注入 cookieJar
        var ck = buildCookieHeader();
        if (ck) bizHeaders['Cookie'] = ck;

        var text = '';
        var resp;
        try {
            resp = req(url, { headers: bizHeaders });
            text = resp && resp.content ? String(resp.content) : '';
            // ★ v2.1：记录 Set-Cookie
            if (resp && resp.headers) extractSetCookie(resp.headers);
        } catch (e) {
            log('请求失败: ' + url + ' ' + e);
            cache[url] = '';
            return '';
        }

        // ★ v2.1：CF 5秒盾等待 + 重试
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
        if (u.charAt(0) === '/') return host.replace(/\/+$/, '') + u;
        return u;
    }

    // ★ v2.1：探测单 host，5s 超时即放弃；探测只取首部 4KB 做签名
    function probeOne(u) {
        var url = /\/$/.test(u) ? u : u + '/';
        try {
            // 探测 headers：带 Range 只取首部 4KB，缩短首字节时间
            var probeHeaders = {};
            for (var k in headers) {
                probeHeaders[k] = headers[k];
            }
            probeHeaders['Range'] = 'bytes=0-4095';
            var ck = buildCookieHeader();
            if (ck) probeHeaders['Cookie'] = ck;
            var resp = req(url, { headers: probeHeaders, timeout: PROBE_TIMEOUT_MS });
            var text = resp && resp.content ? String(resp.content) : '';
            if (resp && resp.headers) extractSetCookie(resp.headers);
            // CF 盾：探测阶段直接判失败（不在此等待，交给后续业务 get 处理）
            if (isCloudflareChallenge(text)) return '';
            if (text.length > 200 && /(花都|huadu|vodtype|voddetail|stui)/i.test(text)) {
                return u;
            }
        } catch (e) {
            log('探测失败: ' + u + ' ' + e);
        }
        return '';
    }

    // ★ v2.1：域名探测（主域名 + 发布页回退，带总体超时）
    function pickDomain() {
        var startTs = Date.now();

        // 1) 主域名顺序探测（带单 host 超时 + 总体超时）
        for (var i = 0; i < domainList.length; i++) {
            if (Date.now() - startTs > PROBE_TOTAL_TIMEOUT_MS) {
                log('域名探测总体超时，停止');
                break;
            }
            var ok = probeOne(domainList[i]);
            if (ok) return ok;
        }

        // 2) 发布页回退（保留原 hdfby 链路）
        for (var p = 0; p < pubUrls.length; p++) {
            if (Date.now() - startTs > PROBE_TOTAL_TIMEOUT_MS) {
                log('发布页探测总体超时，停止');
                break;
            }
            var text = get(pubUrls[p]);
            var found = text.match(/https?:\/\/[a-zA-Z0-9.-]+\.(?:com|net|org|top|cc|vip)\/?/g) || [];
            var seen = {};
            for (var j = 0; j < found.length; j++) {
                var u = found[j];
                if (!/\/$/.test(u)) u += '/';
                if (seen[u]) continue;
                seen[u] = true;
                if (Date.now() - startTs > PROBE_TOTAL_TIMEOUT_MS) break;
                var ok2 = probeOne(u);
                if (ok2) return ok2;
            }
        }
        return '';
    }

    function ensureHost() {
        if (!host) {
            host = pickDomain();
            hostReady = !!host;
            if (hostReady) {
                headers.Referer = host;
                log('当前域名: ' + host);
            } else {
                log('未找到可用域名');
            }
        }
        return host;
    }

    // ====== 工具函数 ======

    function mid(text, a, b) {
        text = String(text || '');
        var i = text.indexOf(a);
        if (i < 0) return '';
        var j = text.indexOf(b, i + a.length);
        if (j < 0) return '';
        return text.substring(i + a.length, j).replace(/\\/g, '');
    }

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

    function txt(s) {
        return unescapeHTML(String(s || '').replace(/<[^>]+>/g, '')).replace(/\s+/g, ' ').trim();
    }

    function pic(block) {
        var keys = ['data-original', 'data-src', 'data-lazyload', 'data-lazy-src', 'src'];
        for (var i = 0; i < keys.length; i++) {
            var reg = new RegExp('<img[^>]+(?:' + keys[i] + ')=["\\\']([^"\\\']+)', 'i');
            var m = reg.exec(block);
            if (!m) continue;
            var u = String(m[1] || '').trim();
            var lower = u.toLowerCase();
            if (u && lower.indexOf('blank') < 0 && lower.indexOf('loading') < 0 && lower.indexOf('default') < 0) {
                return fixUrl(u);
            }
        }
        return '';
    }

    function videos(text) {
        var out = [];
        var seen = {};
        var blocks = String(text || '').match(/<li[\s\S]*?<\/li>/ig) || [];
        for (var i = 0; i < blocks.length; i++) {
            var b = blocks[i];
            if (b.indexOf('stui-vodlist__thumb') < 0 && b.indexOf('voddetail') < 0) continue;
            if (/(广告点赞|开元棋牌|澳门新葡京|好色直播|注册送|棋牌|赌场|葡京|博彩)/.test(b)) continue;

            var hm = /<h4[^>]*class=["'][^"']*title[^"']*["'][\s\S]*?<a[^>]+href=["']([^"']+)["'][^>]*>([\s\S]*?)<\/a>/i.exec(b);
            var am = /<a[^>]+class=["'][^"']*stui-vodlist__thumb[^"']*["'][^>]+href=["']([^"']+)["']/i.exec(b);
            var href = hm ? hm[1] : (am ? am[1] : '');
            if (href.indexOf('voddetail') < 0) continue;

            var name = hm ? txt(hm[2]) : '';
            if (!name) {
                var tm = /title=["']([^"']+)["']/i.exec(b);
                name = tm ? txt(tm[1]) : '';
            }
            if (!href || !name || seen[href] || name.length < 2) continue;

            var image = pic(b);
            if (!image) continue;
            seen[href] = true;

            var rm = /<span[^>]+class=["'][^"']*pic-text[^"']*["'][^>]*>([\s\S]*?)<\/span>/i.exec(b);
            var remark = rm ? txt(rm[1]) : '';
            out.push({
                vod_id: href,
                vod_name: name,
                vod_pic: image,
                vod_remarks: remark
            });
        }
        return out;
    }

    function buildCategoryUrl(cid, pg) {
        pg = parseInt(pg || '1', 10);
        if (!pg || pg < 1) pg = 1;
        cid = String(cid || '');
        if (pg === 1) return fixUrl(cid);
        var base = cid.indexOf('---.html') >= 0 ? cid.split('---.html')[0] : cid.replace(/\.html$/, '');
        return fixUrl(base + pg + '---.html');
    }

    function isDirectVideoUrl(u) {
        return /\.(m3u8|mp4|flv|ts)(?:\?|#|$)/i.test(String(u || ''));
    }

    // ★ v2.1：b64Decode 强化（URL-safe + 缺 = 补齐 + 套娃 base64）
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
            // ★ v2.1：套娃 base64（解码后仍是纯 base64 串则再解一次）
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

    function extractJsonPlayer(text) {
        text = String(text || '');
        var m = /(player_[a-zA-Z0-9_]+|mac_player_data|player_data)\s*=\s*(\{[\s\S]*?\})\s*(?:;|<\/script>)/i.exec(text);
        if (!m) return {};
        try {
            return JSON.parse(m[2].replace(/'/g, '"'));
        } catch (e1) {
            try {
                var obj = {};
                var body = m[2];
                var kv;
                var reg = /["']?([a-zA-Z0-9_]+)["']?\s*:\s*["']([\s\S]*?)["']\s*(?:,|})/g;
                while ((kv = reg.exec(body)) !== null) obj[kv[1]] = kv[2];
                return obj;
            } catch (e2) {
                return {};
            }
        }
    }

    // ★ v2.1：extractPlayUrl 多模式 + 宽松 m3u8 匹配
    function extractPlayUrl(text) {
        text = String(text || '');
        // 1) JSON player
        var data = extractJsonPlayer(text);
        var u = data.url || data.link || data.video || data.src || '';
        // 2) 字符串对
        if (!u) {
            u = mid(text, '"url":"', '"')
                || mid(text, "'url':'", "'")
                || mid(text, 'url: "', '"')
                || mid(text, "url: '", "'");
        }
        // 3) iframe 第三方播放器 src 携带 ?url=
        if (!u) {
            var ifm = /<iframe[^>]+src=["']([^"']+)["']/i.exec(text);
            if (ifm) {
                var qm = /[?&]url=([^&"']+)/.exec(ifm[1]);
                if (qm) {
                    try { u = decodeURIComponent(qm[1]); } catch (e0) { u = qm[1]; }
                }
            }
        }
        // 4) ★ v2.1：宽松 m3u8 / mp4 匹配（允许空白、换行、属性分隔）
        if (!u) {
            var re = /https?:\/\/[^\s"'<>\\]+?\.(?:m3u8|mp4)(?:\?[^\s"'<>\\]*)?/i;
            var m = re.exec(text);
            if (m) u = m[0];
        }
        u = decodePlayUrl(u);
        return fixUrl(u);
    }

    // ★ v2.1：分类结果 LRU 缓存
    function categoryCacheGet(cid, pg) {
        var key = cid + '_' + pg;
        return categoryCache[key];
    }
    function categoryCachePut(cid, pg, result) {
        var key = cid + '_' + pg;
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
                var sites = [];
                var pubs = [];
                for (var i = 0; i < config.hosts.length; i++) {
                    var h = String(config.hosts[i] || '');
                    if (/hdfby\.(com|net|org)/i.test(h)) pubs.push(h);
                    else sites.push(h);
                }
                if (sites.length) domainList = sites;
                if (pubs.length) pubUrls = pubs;
            }
            ensureHost();
            return true;
        },

        homeContent: function () {
            ensureHost();
            if (!hostReady) {
                return { class: fallback, list: [] };
            }
            var text = get(host);
            var arr = [];
            var seen = {};
            var reg = /<a[^>]+href=["']([^"']*(?:vodtype|vodshow)[^"']+)["'][^>]*>([\s\S]*?)<\/a>/ig;
            var m;
            while ((m = reg.exec(text)) !== null) {
                var name = txt(m[2]);
                if (!name || name === '首页' || name === '发布页' || name === 'VPN下载') continue;
                var href = String(m[1]).replace('vodtype', 'vodshow');
                var cid;
                if (href.indexOf('.html') >= 0 && href.indexOf('-----------') < 0) cid = href.split('.html')[0] + '-----------.html';
                else if (href.indexOf('.html') < 0) cid = href.replace(/\/+$/, '') + '-----------.html';
                else cid = href;
                if (!seen[cid]) {
                    seen[cid] = true;
                    arr.push({ type_id: cid, type_name: name });
                }
            }
            var reg2 = /<a[^>]+href=["'](\/vodshow\/\d+-----------\.html)["'][^>]*>([\s\S]*?)<\/a>/ig;
            while ((m = reg2.exec(text)) !== null) {
                var n = txt(m[2]);
                if (n && !seen[m[1]]) {
                    seen[m[1]] = true;
                    arr.push({ type_id: m[1], type_name: n });
                }
            }
            return { class: arr.length ? arr : fallback, list: videos(text) };
        },

        homeVideoContent: function () {
            ensureHost();
            if (!hostReady) return { list: [] };
            return { list: videos(get(host)) };
        },

        // ★ v2.1：categoryContent 加 LRU 缓存 + 动态 pagecount
        categoryContent: function (cid, pg) {
            ensureHost();
            pg = parseInt(pg || '1', 10);
            if (!pg || pg < 1) pg = 1;
            if (!hostReady) {
                return { page: pg, pagecount: 1, limit: 90, total: 0, list: [] };
            }
            // 命中缓存直接返回
            var cached = categoryCacheGet(cid, pg);
            if (cached) return cached;

            var items = videos(get(buildCategoryUrl(cid, pg)));
            // 动态 pagecount：当前页有内容则至少还有下一页；空则到尾
            var pagecount;
            if (items.length === 0) {
                pagecount = pg > 1 ? pg - 1 : 1;
            } else {
                pagecount = 9999;
            }
            var result = {
                page: pg,
                pagecount: pagecount,
                limit: 90,
                total: pagecount === 9999 ? 999999 : (pagecount * 90),
                list: items
            };
            categoryCachePut(cid, pg, result);
            return result;
        },

        detailContent: function (ids) {
            ensureHost();
            if (!hostReady) return { list: [] };
            var did = fixUrl(Array.isArray(ids) ? ids[0] : ids);
            var text = unescapeHTML(get(did));
            var name = txt(mid(text, '<h1', '</h1>')) || txt(mid(text, '标题：', '</span>'));
            var image = pic(text);
            var director = [];
            var actor = [];
            var remarks = [];
            var m;
            var regDirector = /分类：[\s\S]*?target=["'][^"']*["']>(.*?)<\/a>/ig;
            while ((m = regDirector.exec(text)) !== null) director.push(txt(m[1]));
            var regActor = /演员：[\s\S]*?target=["'][^"']*["']>(.*?)<\/a>/ig;
            while ((m = regActor.exec(text)) !== null) actor.push(txt(m[1]));
            var regRemark = /类别：[\s\S]*?target=["'][^"']*["']>(.*?)<\/a>/ig;
            while ((m = regRemark.exec(text)) !== null) remarks.push(txt(m[1]));
            var year = txt(mid(text, '日期：', 'p>'));
            var area = txt(mid(text, '时长：', 'p>'));
            var pm = /class=["']btn btn-primary["'][^>]+href=["']([^"']+)["']/i.exec(text);
            var play = pm ? fixUrl(pm[1]) : did;
            return {
                list: [{
                    vod_id: did,
                    vod_name: name,
                    vod_pic: image,
                    vod_director: director.join(' '),
                    vod_actor: actor.join(' '),
                    vod_remarks: remarks.join(' '),
                    vod_year: year,
                    vod_area: area,
                    vod_content: name || '',
                    vod_play_from: '花都专线',
                    vod_play_url: '播放$' + play
                }]
            };
        },

        searchContent: function (key, quick, pg) {
            ensureHost();
            if (!hostReady) return { list: [], page: parseInt(pg || '1', 10) || 1, pagecount: 1, limit: 90, total: 0 };
            pg = parseInt(pg || '1', 10);
            var url = fixUrl('/vodsearch/-------------.html?wd=' + encodeURIComponent(key || ''));
            return { list: videos(get(url)), page: pg, pagecount: 9999, limit: 90, total: 999999 };
        },

        // ★ v2.1：playerContent 强化解析 + 失败返回空 url + Referer 改为播放页自身
        playerContent: function (flag, id) {
            ensureHost();
            if (!hostReady) {
                return { parse: 1, playUrl: '', url: '', header: { 'User-Agent': mobileUA } };
            }
            var text = get(id, { ua: 'mobile' });
            var u = extractPlayUrl(text);
            // ★ v2.1：解析失败返回 url: '' 让客户端走错误态（而非回传 id 导致死循环）
            var ck = buildCookieHeader();
            var header = {
                'User-Agent': mobileUA,
                // ★ v2.1：Referer 改为播放页 URL 自身，贴合 m3u8 CDN 校验
                'Referer': id,
                'Origin': host.replace(/\/+$/, '')
            };
            if (ck) header['Cookie'] = ck;
            return {
                parse: u ? 0 : 1,
                playUrl: '',
                url: u || '',
                header: header
            };
        }
    };
})();
