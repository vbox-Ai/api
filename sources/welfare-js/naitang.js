/**
 * 奶糖视频 JavaScript Spider
 * 适配 vbox iOS 福利专区 WelfareJSSpiderService。
 */

var spider = (function () {
    var domainList = [
        'https://ewrzka4.naitang8.top'
    ];

    var host = '';
    var hostReady = false;
    var cache = {};
    var ua = 'Mozilla/5.0 (Linux; Android 11; SAMSUNG SM-G973U) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/87.0.4280.141 Mobile Safari/537.36';
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

    function get(url) {
        if (!url) return '';
        if (cache[url]) return cache[url];
        try {
            var resp = req(url, { headers: headers });
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
        if (u.charAt(0) === '/') return trimSlash(host) + u;
        return u;
    }

    function okDomain(u) {
        var base = trimSlash(u);
        var text = get(base + '/');
        return text.length > 200 && /(奶糖视频|naitang|vod\/detail|vod\/type|player_aaaa)/i.test(text);
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

    function unescapeHTML(s) {
        return String(s || '')
            .replace(/&nbsp;/g, ' ')
            .replace(/&amp;/g, '&')
            .replace(/&quot;/g, '"')
            .replace(/&#39;/g, "'")
            .replace(/&lt;/g, '<')
            .replace(/&gt;/g, '>');
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

    function decodeUrl(u) {
        u = String(u || '').replace(/\\\//g, '/');
        if (!u) return '';
        try { return decodeURIComponent(u); } catch (e) { return u; }
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

        categoryContent: function (tid, pg) {
            ensureHost();
            pg = parseInt(pg || '1', 10);
            if (!pg || pg < 1) pg = 1;
            if (!hostReady) return { page: pg, pagecount: 1, limit: 24, total: 0, list: [] };
            return { page: pg, pagecount: 999, limit: 24, total: 999999, list: parseList(get(categoryUrl(tid, pg))) };
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

        playerContent: function (flag, id) {
            ensureHost();
            if (!hostReady) return { parse: 1, playUrl: '', url: id, header: headers };
            var html = get(id);
            var url = '';
            var m = /player_aaaa\s*=\s*(\{[\s\S]*?\})\s*</i.exec(html);
            if (m) {
                try {
                    var data = JSON.parse(m[1].replace(/\\\//g, '/'));
                    url = data.url || '';
                } catch (e) {
                    url = '';
                }
            }
            if (!url) {
                url = match(html, /"url"\s*:\s*"([^"]+)"/i) || match(html, /'url'\s*:\s*'([^']+)'/i);
            }
            url = decodeUrl(url) || id;
            return {
                parse: isVideoFormat(url) ? 0 : 1,
                playUrl: '',
                url: url,
                header: headers
            };
        }
    };
})();
