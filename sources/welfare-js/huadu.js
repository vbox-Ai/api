/**
 * 花都影视 JavaScript Spider
 * 适配 vbox iOS 福利专区 WelfareJSSpiderService。
 */

var spider = (function () {
    var pubUrls = [
        'https://abc.hdfby.com',
        'https://b.hdfby.com',
        'https://b.hdfby.net',
        'https://b.hdfby.org'
    ];

    var domainList = [
        'https://hd28.huadutx.com/',
        'https://rb.huaduys.org/'
    ];

    var ua = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/129.0.0.0 Safari/537.36 Edg/129.0.0.0';
    var mobileUA = 'Mozilla/5.0 (Linux; Android 12; Pixel 3 XL) AppleWebKit/537.36 Chrome/98.0.4758.101 Mobile Safari/537.36';
    var host = '';
    var hostReady = false;
    var cache = {};
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

    function get(url) {
        if (!url) return '';
        if (cache[url]) return cache[url];
        var resp;
        try {
            resp = req(url, { headers: headers });
            var text = resp && resp.content ? String(resp.content) : '';
            cache[url] = text;
            return text;
        } catch (e) {
            log('请求失败: ' + url + ' ' + e);
            cache[url] = '';
            return '';
        }
    }

    function fixUrl(u) {
        u = String(u || '').trim();
        if (!u) return '';
        if (u.indexOf('//') === 0) return 'https:' + u;
        if (/^https?:\/\//i.test(u)) return u;
        if (u.charAt(0) === '/') return host.replace(/\/+$/, '') + u;
        return u;
    }

    function okDomain(u) {
        var url = /\/$/.test(u) ? u : u + '/';
        var text = get(url);
        return text.length > 200 && /(花都|huadu|vodtype|voddetail|stui)/i.test(text);
    }

    function pickDomain() {
        for (var i = 0; i < domainList.length; i++) {
            if (okDomain(domainList[i])) return domainList[i];
        }

        for (var p = 0; p < pubUrls.length; p++) {
            var text = get(pubUrls[p]);
            var found = text.match(/https?:\/\/[a-zA-Z0-9.-]+\.(?:com|net|org|top|cc|vip)\/?/g) || [];
            var seen = {};
            for (var j = 0; j < found.length; j++) {
                var u = found[j];
                if (!/\/$/.test(u)) u += '/';
                if (seen[u]) continue;
                seen[u] = true;
                if (okDomain(u)) return u;
            }
        }
        return '';
    }

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

    function b64Decode(s) {
        try {
            if (typeof crypto !== 'undefined' && crypto.base64 && crypto.base64.decode) {
                return crypto.base64.decode(s);
            }
        } catch (e) {}
        var chars = 'ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789+/=';
        var str = String(s || '').replace(/[^A-Za-z0-9+/=]/g, '');
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
        try {
            var decoded = b64Decode(value);
            decoded = decodeEscapes(decoded).replace(/\\\//g, '/');
            try { decoded = decodeURIComponent(decoded); } catch (e0) {}
            if (/^https?:\/\//i.test(decoded)) return decoded;
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

    function extractPlayUrl(text) {
        var data = extractJsonPlayer(text);
        var u = data.url || data.link || data.video || data.src || '';
        if (!u) {
            u = mid(text, '"url":"', '"')
                || mid(text, "'url':'", "'")
                || mid(text, 'url: "', '"')
                || mid(text, "url: '", "'");
        }
        if (!u) {
            var m = /https?:\\?\/\\?\/[^"'<>\s]+?\.(?:m3u8|mp4)(?:\?[^"'<>\s]*)?/i.exec(String(text || ''));
            u = m ? m[0] : '';
        }
        u = decodePlayUrl(u);
        return fixUrl(u);
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

        categoryContent: function (cid, pg) {
            ensureHost();
            if (!hostReady) return { page: parseInt(pg || '1', 10) || 1, pagecount: 1, limit: 90, total: 0, list: [] };
            pg = parseInt(pg || '1', 10);
            var items = videos(get(buildCategoryUrl(cid, pg)));
            return { page: pg, pagecount: 9999, limit: 90, total: 999999, list: items };
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

        playerContent: function (flag, id) {
            ensureHost();
            if (!hostReady) {
                return { parse: 1, playUrl: '', url: id, header: { 'User-Agent': mobileUA } };
            }
            var text = get(id);
            var u = extractPlayUrl(text);
            var direct = isDirectVideoUrl(u);
            return {
                parse: direct ? 0 : 1,
                playUrl: '',
                url: u || id,
                header: { 'User-Agent': mobileUA, 'Referer': host, 'Origin': host.replace(/\/+$/, '') }
            };
        }
    };
})();
