/*
 * 优酷 JS 蜘蛛
 * 适配 vbox-ios JSSpiderEngine / QJSSpiderEngine（type:3 独立引擎）
 * 来源：由 Python 版优酷蜘蛛移植
 * 说明：分类/搜索走公开 JSON，详情剧集走 mtop，播放返回优酷页面 URL，parse:1 交给 App 解析器处理。
 */

var spider = {
    __jsEvalReturn: function() {
        var HOST = 'https://www.youku.com';
        var SHOST = 'https://search.youku.com';
        var H5HOST = 'https://acs.youku.com';
        var IHOST = 'https://v.youku.com';
        var APP_KEY = '24679788';
        var UTDID = 'ZYmGMAAAACkDAMU8hbiMmYdd';
        var UA = 'Mozilla/5.0 (; Windows 10.0.26100.3194_64 ) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/93.0.4577.82 Electron/14.2.0 Safari/537.36 Node/14.17.0 YoukuDesktop/9.2.60 UOSYouku (2.0.1)-Electron(UTDID ZYmGMAAAACkDAMU8hbiMmYdd;CHANNEL official;ZREAL 0;BTYPE TM2013;BRAND TIMI;BUILDVER 9.2.60.1001)';
        var cookieText = '__ysuid=17416134165380iB; __aysid=1741613416541WbD; xlly_s=1; isI18n=false; cna=bNdVIKmmsHgCAXW9W6yrQ1/s';
        var mtopToken = '';
        var typeSession = {};

        var CATEGORIES = ['电视剧', '电影', '综艺', '动漫', '少儿', '纪录片', '文化', '亲子', '教育', '搞笑', '生活', '体育', '音乐', '游戏'];

        function encode(str) {
            return encodeURIComponent(str == null ? '' : String(str));
        }

        function buildUrl(url, params) {
            var parts = [];
            for (var k in params) {
                if (params.hasOwnProperty(k) && params[k] !== undefined && params[k] !== null && params[k] !== '') {
                    parts.push(encode(k) + '=' + encode(params[k]));
                }
            }
            return url + (url.indexOf('?') >= 0 ? '&' : '?') + parts.join('&');
        }

        function buildHeaders(extra) {
            var h = {
                'User-Agent': UA,
                'Referer': HOST + '/',
                'Accept': 'application/json,text/plain,*/*',
                'Accept-Language': 'zh-CN,zh;q=0.9'
            };
            if (cookieText) h.Cookie = cookieText;
            if (extra) {
                for (var k in extra) if (extra.hasOwnProperty(k)) h[k] = extra[k];
            }
            return h;
        }

        function respText(resp) {
            if (!resp) return '';
            if (typeof resp === 'string') return resp;
            if (typeof resp === 'object') {
                if (typeof resp.content === 'string') return resp.content;
                if (typeof resp.data === 'string') return resp.data;
                if (typeof resp.body === 'string') return resp.body;
                if (typeof resp.content === 'object') return JSON.stringify(resp.content);
                if (typeof resp.data === 'object') return JSON.stringify(resp.data);
            }
            return '';
        }

        function headerValue(headers, key) {
            if (!headers) return '';
            if (headers[key]) return headers[key];
            var lower = key.toLowerCase();
            for (var k in headers) {
                if (headers.hasOwnProperty(k) && String(k).toLowerCase() === lower) return headers[k];
            }
            return '';
        }

        function mergeCookie(oldCookie, setCookie) {
            var map = {};
            function putPair(pair) {
                if (!pair) return;
                var p = String(pair).split(';')[0];
                var idx = p.indexOf('=');
                if (idx <= 0) return;
                var k = p.substring(0, idx).trim();
                var v = p.substring(idx + 1).trim();
                if (k && v !== '') map[k] = v;
            }
            if (oldCookie) {
                var arr = String(oldCookie).split(';');
                for (var i = 0; i < arr.length; i++) putPair(arr[i]);
            }
            if (setCookie) {
                if (setCookie.join) setCookie = setCookie.join('\n');
                var text = String(setCookie).replace(/\r/g, '\n');
                var parts = text.split(/\n|,(?=\s*[^;,=\s]+=[^;,]+)/);
                for (var j = 0; j < parts.length; j++) putPair(parts[j]);
            }
            var out = [];
            for (var name in map) if (map.hasOwnProperty(name)) out.push(name + '=' + map[name]);
            return out.join('; ');
        }

        function saveSetCookie(resp) {
            try {
                if (!resp || typeof resp !== 'object') return;
                var headers = resp.headers || resp.header || {};
                var setCookie = headerValue(headers, 'set-cookie') || resp.setCookie || resp.cookie || '';
                if (!setCookie) return;
                cookieText = mergeCookie(cookieText, setCookie);
                var m = cookieText.match(/(?:^|;\s*)_m_h5_tk=([^;]+)/);
                if (m && m[1]) mtopToken = String(m[1]).split('_')[0];
            } catch (e) {
                print('>>> youku saveSetCookie ERROR: ' + e);
            }
        }

        function fetchJson(url, params, extraHeaders) {
            try {
                var fullUrl = params ? buildUrl(url, params) : url;
                var resp = req(fullUrl, { method: 'GET', headers: buildHeaders(extraHeaders), timeout: 15000 });
                saveSetCookie(resp);
                var text = respText(resp);
                if (!text) {
                    print('>>> youku fetch empty: ' + fullUrl.substring(0, 120));
                    return null;
                }
                return JSON.parse(text);
            } catch (e) {
                print('>>> youku fetchJson ERROR: ' + e);
                return null;
            }
        }

        function parseExtend(extend) {
            if (!extend) return {};
            if (typeof extend === 'object') return extend;
            try { return JSON.parse(extend); } catch (e) { return {}; }
        }

        function normalizePic(url) {
            if (!url) return '';
            url = String(url);
            if (url.indexOf('//') === 0) return 'https:' + url;
            if (url.indexOf('http://') === 0) return 'https://' + url.substring(7);
            return url;
        }

        function normalizePlayUrl(url) {
            if (!url) return '';
            url = String(url);
            if (url.indexOf('$') >= 0) {
                var parts = url.split('$');
                url = parts[parts.length - 1];
            }
            if (url.indexOf('//') === 0) return 'https:' + url;
            if (url.indexOf('http') === 0) return url;
            return IHOST + '/v_show/id_' + String(url).trim() + '.html';
        }

        function normalizeIds(ids) {
            if (!ids) return '';
            var raw = '';
            if (typeof ids === 'string') raw = ids.split(',')[0];
            else if (ids.length) raw = String(ids[0]);
            raw = String(raw || '').trim();
            if (raw.indexOf('$') >= 0) {
                var parts = raw.split('$');
                raw = parts[parts.length - 1];
            }
            var m = raw.match(/[?&]s=([^&]+)/);
            if (m && m[1]) return m[1];
            m = raw.match(/\/id_([^./?]+)\.html/);
            if (m && m[1]) return m[1];
            return raw.trim();
        }

        function cleanTitle(title, fallback) {
            title = String(title || fallback || '播放').replace(/[\r\n\t]+/g, ' ').replace(/\s+/g, ' ').trim();
            return title.replace(/\$/g, ' ');
        }

        function isVideoFormat(url) {
            if (!url || String(url).indexOf('http') !== 0) return false;
            var lower = String(url).toLowerCase();
            var exts = ['.mp4', '.m3u8', '.ts', '.mkv', '.avi', '.flv', '.webm'];
            for (var i = 0; i < exts.length; i++) {
                if (lower.indexOf(exts[i]) >= 0) return true;
            }
            return false;
        }

        function processKey(key) {
            if (!key || String(key).indexOf('_') < 0) return key;
            var parts = String(key).split('_');
            var out = parts[0];
            for (var i = 1; i < parts.length; i++) {
                if (parts[i]) out += parts[i].charAt(0).toUpperCase() + parts[i].substring(1);
            }
            return out;
        }

        function getFilterData(data) {
            var result = [];
            try {
                data = data || [];
                for (var i = 0; i < data.length; i++) {
                    var item = data[i] || {};
                    var subFilter = item.subFilter || [];
                    if (!subFilter.length || !subFilter[0].filterType) continue;
                    var filterItem = {
                        key: processKey(subFilter[0].filterType),
                        name: subFilter[0].title || '',
                        value: []
                    };
                    for (var j = 0; j < subFilter.length; j++) {
                        var sub = subFilter[j] || {};
                        if (sub.value !== undefined && sub.title) {
                            filterItem.value.push({ n: sub.title, v: String(sub.value) });
                        }
                    }
                    if (filterItem.key && filterItem.name && filterItem.value.length) result.push(filterItem);
                }
            } catch (e) {
                print('>>> youku getFilterData ERROR: ' + e);
            }
            return result;
        }

        function categorySession(params, withFilter) {
            var data = fetchJson(HOST + '/category/data', {
                params: JSON.stringify(params),
                optionRefresh: '1',
                pageNo: '1'
            });
            var filterData = data && data.data ? data.data.filterData : null;
            if (!filterData) return withFilter ? { session: '', filters: [] } : '';
            var session = JSON.stringify(filterData.session || {});
            if (withFilter) {
                var filters = filterData.filter && filterData.filter.filterData ? filterData.filter.filterData.slice(1) : [];
                return { session: session, filters: getFilterData(filters) };
            }
            return session;
        }

        function getCToken() {
            try {
                var url = H5HOST + '/h5/mtop.ykrec.recommendservice.recommend/1.0/?jsv=2.6.1&appKey=' + APP_KEY;
                var resp = req(url, { method: 'GET', headers: buildHeaders(), timeout: 15000 });
                saveSetCookie(resp);
                return !!mtopToken;
            } catch (e) {
                print('>>> youku getCToken ERROR: ' + e);
                return false;
            }
        }

        function mtopRequest(url, params, retry) {
            retry = retry || 0;
            try {
                if (!mtopToken && !getCToken()) return null;
                var data = JSON.stringify(params);
                var t = String(Date.now());
                var sign = md5(mtopToken + '&' + t + '&' + APP_KEY + '&' + data);
                var fullUrl = buildUrl(url, {
                    appKey: APP_KEY,
                    t: t,
                    sign: sign,
                    data: data
                });
                var resp = req(fullUrl, { method: 'GET', headers: buildHeaders(), timeout: 15000 });
                saveSetCookie(resp);
                var text = respText(resp);
                if (!text) return null;
                if (text.indexOf('令牌过期') >= 0 || text.indexOf('FAIL_SYS_TOKEN_EXOIRED') >= 0 || text.indexOf('FAIL_SYS_ILLEGAL_ACCESS') >= 0) {
                    if (retry >= 2) return null;
                    mtopToken = '';
                    getCToken();
                    return mtopRequest(url, params, retry + 1);
                }
                return JSON.parse(text);
            } catch (e) {
                print('>>> youku mtopRequest ERROR: ' + e);
                return null;
            }
        }

        function getVInfo(params) {
            var body = {
                ms_codes: '2019030100',
                params: JSON.stringify(params),
                system_info: '{"os":"iku","device":"iku","ver":"9.2.9","appPackageKey":"com.youku.iku","appPackageId":"pcweb"}'
            };
            var data = mtopRequest(H5HOST + '/h5/mtop.youku.columbus.gateway.new.execute/1.0/', body);
            if (!data || !data.data) return null;
            for (var k in data.data) {
                if (data.data.hasOwnProperty(k) && data.data[k] && data.data[k].data) return data.data[k].data;
            }
            return null;
        }

        function getInfo(params) {
            var i = getVInfo(params);
            if (!i) return null;
            var nodes = i.nodes && i.nodes[0] ? (i.nodes[0].nodes || []) : [];
            var extra = i.data ? (i.data.extra || {}) : {};
            var jdata = nodes[3] || { nodes: [] };
            if (extra.showCategory === '电影' || extra.showCategory === '游戏') jdata = nodes[4] || jdata;
            var director = '';
            try {
                for (var n = 0; n < nodes.length; n++) {
                    var node = nodes[n] || {};
                    if (node.type === 20009 && node.nodes) {
                        var persons = [];
                        for (var s = 0; s < node.nodes.length; s++) {
                            var sub = node.nodes[s] || {};
                            var title = sub.data ? sub.data.title : '';
                            if (sub.type === 10011 && title) persons.push(title);
                        }
                        if (persons.length) director = persons[0];
                        break;
                    }
                }
            } catch (e) {}
            return {
                node: jdata,
                total: parseInt(extra.episodeTotal || 0) || 0,
                director: director
            };
        }

        function homeContent(filter) {
            var classes = [];
            var filters = {};
            for (var i = 0; i < CATEGORIES.length; i++) {
                var name = CATEGORIES[i];
                classes.push({ type_name: name, type_id: name });
                if (filter) {
                    var info = categorySession({ type: name }, true);
                    typeSession[name] = info.session;
                    filters[name] = info.filters;
                }
            }
            var result = { class: classes, list: [] };
            if (filter) result.filters = filters;
            return result;
        }

        function homeVideoContent() {
            var vlist = [];
            try {
                var params = {
                    ms_codes: '2019061000',
                    params: '{"debug":0,"gray":0,"pageNo":1,"utdid":"' + UTDID + '","userId":"","bizKey":"YOUKU_WEB","appPackageKey":"com.youku.YouKu","showNodeList":0,"reqSubNode":0,"nodeKey":"WEBHOME","bizContext":"{\\"spmA\\":\\"a2hja\\"}"}',
                    system_info: '{"device":"pcweb","os":"pcweb","ver":"1.0.0.0","userAgent":"' + UA.replace(/"/g, '\\"') + '","guid":"1590141704165YXe","appPackageKey":"com.youku.pcweb","young":0,"brand":"","network":"","ouid":"","idfa":"","scale":"","operator":"","resolution":"","pid":"","childGender":0,"zx":0}'
                };
                var data = mtopRequest(H5HOST + '/h5/mtop.youku.columbus.home.query/1.0/', params);
                if (!data || !data.data) return { list: vlist };
                var root = null;
                for (var k in data.data) {
                    if (data.data.hasOwnProperty(k) && data.data[k] && data.data[k].data) {
                        root = data.data[k].data;
                        break;
                    }
                }
                var blocks = root && root.nodes && root.nodes[0] && root.nodes[0].nodes ? root.nodes[0].nodes : [];
                var last = blocks.length ? blocks[blocks.length - 1] : null;
                var items = last && last.nodes && last.nodes[0] ? (last.nodes[0].nodes || []) : [];
                for (var i = 0; i < items.length; i++) {
                    var item = items[i];
                    var d = item && item.nodes && item.nodes[0] ? item.nodes[0].data : null;
                    if (d && d.assignId) {
                        vlist.push({
                            vod_id: String(d.assignId),
                            vod_name: d.title || '',
                            vod_pic: normalizePic(d.vImg || d.img || ''),
                            vod_year: d.mark && d.mark.data ? (d.mark.data.text || '') : '',
                            vod_remarks: d.summary || ''
                        });
                    }
                    if (vlist.length >= 36) break;
                }
            } catch (e) {
                print('>>> youku homeVideoContent ERROR: ' + e);
            }
            return { list: vlist };
        }

        function categoryContent(tid, pg, filter, extend) {
            var page = Math.max(parseInt(pg) || 1, 1);
            var ext = parseExtend(extend === undefined ? filter : extend);
            var params = { type: tid };
            for (var k in ext) {
                if (ext.hasOwnProperty(k) && ext[k] !== undefined && ext[k] !== null && ext[k] !== '') params[k] = ext[k];
            }
            var session = typeSession[tid] || '';
            if (page === 1 || !session) session = categorySession(params, false);
            var vlist = [];
            var pagecount = page;
            try {
                var query = {
                    params: JSON.stringify(params),
                    pageNo: String(page)
                };
                if (page === 1) {
                    query.optionRefresh = '1';
                } else if (session) {
                    query.session = session;
                }
                var data = fetchJson(HOST + '/category/data', query);
                var fdata = data && data.data ? data.data.filterData : null;
                var listData = fdata ? (fdata.listData || []) : [];
                for (var i = 0; i < listData.length; i++) {
                    var item = listData[i] || {};
                    var link = item.videoLink || '';
                    var id = '';
                    var m = String(link).match(/[?&]s=([^&]+)/);
                    if (m && m[1]) id = m[1];
                    if (!id && item.showId) id = item.showId;
                    if (!id) continue;
                    vlist.push({
                        vod_id: String(id),
                        vod_name: item.title || '',
                        vod_pic: normalizePic(item.img || ''),
                        vod_year: item.rightTagText || '',
                        vod_remarks: item.summary || ''
                    });
                }
                if (fdata && fdata.session) typeSession[tid] = JSON.stringify(fdata.session);
                pagecount = vlist.length ? page + 1 : page;
            } catch (e) {
                print('>>> youku categoryContent ERROR: ' + e);
            }
            return { list: vlist, page: page, pagecount: pagecount, limit: 90, total: vlist.length * page };
        }

        function detailContent(ids) {
            var result = { list: [] };
            try {
                var showId = normalizeIds(ids);
                if (!showId) return result;
                var data = fetchJson(IHOST + '/v_getvideo_info/', { showId: showId });
                var v = data && data.data ? data.data : {};
                var year = '';
                if (v.lastUpdate && String(v.lastUpdate).length >= 4) year = String(v.lastUpdate).substring(0, 4);
                else if (v.publishTime && String(v.publishTime).length >= 4) year = String(v.publishTime).substring(0, 4);

                var vid = v.vid || showId;
                var vod = {
                    vod_id: showId,
                    vod_name: v.showname || '',
                    type_name: v.showcategory || v.showVideotype || '',
                    vod_year: year,
                    vod_remarks: v.rc_title || '',
                    vod_actor: v._personNameStr || '',
                    vod_director: '',
                    vod_content: v.showdesc || '',
                    vod_play_from: '优酷',
                    vod_play_url: ''
                };

                var params = {
                    biz: 'new_detail_web2',
                    videoId: vid,
                    scene: 'web_page',
                    componentVersion: '3',
                    ip: data ? data.ip : '',
                    debug: 0,
                    utdid: UTDID,
                    userId: 0,
                    platform: 'pc',
                    nextSession: '',
                    gray: 0,
                    source: 'pcNoPrev',
                    showId: showId
                };
                var info = getInfo(params);
                var playUrls = [];
                if (info && info.node) {
                    vod.vod_director = info.director || '';
                    var pdata = info.node.nodes || [];
                    var total = info.total || pdata.length;
                    if (total > pdata.length && pdata.length) {
                        var batchSize = pdata.length;
                        var sessionObj = {};
                        try { sessionObj = JSON.parse((info.node.data && info.node.data.session) || '{}'); } catch (e) { sessionObj = {}; }
                        var maxBatch = Math.min(Math.ceil(total / batchSize) - 1, 8);
                        for (var b = 0; b < maxBatch; b++) {
                            var start = batchSize + 1 + b * batchSize;
                            var end = Math.min(start + batchSize - 1, total);
                            var nextSession = {};
                            for (var sk in sessionObj) if (sessionObj.hasOwnProperty(sk)) nextSession[sk] = sessionObj[sk];
                            nextSession.itemStartStage = start;
                            nextSession.itemEndStage = end;
                            var nextParams = {};
                            for (var pk in params) if (params.hasOwnProperty(pk)) nextParams[pk] = params[pk];
                            nextParams.nextSession = JSON.stringify(nextSession);
                            var next = getVInfo(nextParams);
                            if (next && next.nodes) pdata = pdata.concat(next.nodes);
                        }
                    }
                    for (var i = 0; i < pdata.length; i++) {
                        var ep = pdata[i] || {};
                        var epData = ep.data || {};
                        var title = cleanTitle(epData.title, '第' + (i + 1) + '集');
                        var value = epData.action ? epData.action.value : '';
                        if (value) playUrls.push(title + '$' + normalizePlayUrl(value));
                    }
                }

                if (!playUrls.length) {
                    playUrls.push((vod.vod_name || '正片') + '$' + vid);
                }
                vod.vod_play_url = playUrls.join('#');
                result.list.push(vod);
            } catch (e) {
                print('>>> youku detailContent ERROR: ' + e);
            }
            return result;
        }

        function searchContent(key, quick, pg) {
            if (pg === undefined && quick !== undefined) pg = quick;
            var page = Math.max(parseInt(pg) || 1, 1);
            var vlist = [];
            if (!key) return { list: vlist, page: page, pagecount: page, limit: 20, total: 0 };
            try {
                var data = fetchJson(SHOST + '/api/search', {
                    pg: String(page),
                    keyword: key
                });
                var list = data ? (data.pageComponentList || []) : [];
                var seen = {};
                for (var i = 0; i < list.length; i++) {
                    var common = list[i] ? list[i].commonData : null;
                    if (!common) continue;
                    var id = common.showId || common.realShowId || '';
                    if (!id || seen[id]) continue;
                    seen[id] = true;
                    vlist.push({
                        vod_id: String(id),
                        vod_name: common.titleDTO ? (common.titleDTO.displayName || '') : '',
                        vod_pic: normalizePic(common.posterDTO ? (common.posterDTO.vThumbUrl || '') : ''),
                        vod_year: common.feature || '',
                        vod_remarks: common.updateNotice || ''
                    });
                }
            } catch (e) {
                print('>>> youku searchContent ERROR: ' + e);
            }
            return { list: vlist, page: page, pagecount: vlist.length ? page + 1 : page, limit: 20, total: vlist.length };
        }

        function playerContent(flag, id, vipFlags) {
            var playUrl = vipFlags || id || flag || '';
            playUrl = normalizePlayUrl(playUrl);
            var direct = isVideoFormat(playUrl);
            return {
                parse: direct ? 0 : 1,
                jx: direct ? 0 : 1,
                url: playUrl,
                header: direct ? buildHeaders() : ''
            };
        }

        return {
            init: function(config) { getCToken(); return true; },
            homeContent: homeContent,
            homeVideoContent: homeVideoContent,
            categoryContent: categoryContent,
            detailContent: detailContent,
            searchContent: searchContent,
            searchContentPage: searchContent,
            playerContent: playerContent
        };
    }
};

function md5cycle(x, k) {
    var a = x[0], b = x[1], c = x[2], d = x[3];
    a = ff(a, b, c, d, k[0], 7, -680876936);
    d = ff(d, a, b, c, k[1], 12, -389564586);
    c = ff(c, d, a, b, k[2], 17, 606105819);
    b = ff(b, c, d, a, k[3], 22, -1044525330);
    a = ff(a, b, c, d, k[4], 7, -176418897);
    d = ff(d, a, b, c, k[5], 12, 1200080426);
    c = ff(c, d, a, b, k[6], 17, -1473231341);
    b = ff(b, c, d, a, k[7], 22, -45705983);
    a = ff(a, b, c, d, k[8], 7, 1770035416);
    d = ff(d, a, b, c, k[9], 12, -1958414417);
    c = ff(c, d, a, b, k[10], 17, -42063);
    b = ff(b, c, d, a, k[11], 22, -1990404162);
    a = ff(a, b, c, d, k[12], 7, 1804603682);
    d = ff(d, a, b, c, k[13], 12, -40341101);
    c = ff(c, d, a, b, k[14], 17, -1502002290);
    b = ff(b, c, d, a, k[15], 22, 1236535329);
    a = gg(a, b, c, d, k[1], 5, -165796510);
    d = gg(d, a, b, c, k[6], 9, -1069501632);
    c = gg(c, d, a, b, k[11], 14, 643717713);
    b = gg(b, c, d, a, k[0], 20, -373897302);
    a = gg(a, b, c, d, k[5], 5, -701558691);
    d = gg(d, a, b, c, k[10], 9, 38016083);
    c = gg(c, d, a, b, k[15], 14, -660478335);
    b = gg(b, c, d, a, k[4], 20, -405537848);
    a = gg(a, b, c, d, k[9], 5, 568446438);
    d = gg(d, a, b, c, k[14], 9, -1019803690);
    c = gg(c, d, a, b, k[3], 14, -187363961);
    b = gg(b, c, d, a, k[8], 20, 1163531501);
    a = gg(a, b, c, d, k[13], 5, -1444681467);
    d = gg(d, a, b, c, k[2], 9, -51403784);
    c = gg(c, d, a, b, k[7], 14, 1735328473);
    b = gg(b, c, d, a, k[12], 20, -1926607734);
    a = hh(a, b, c, d, k[5], 4, -378558);
    d = hh(d, a, b, c, k[8], 11, -2022574463);
    c = hh(c, d, a, b, k[11], 16, 1839030562);
    b = hh(b, c, d, a, k[14], 23, -35309556);
    a = hh(a, b, c, d, k[1], 4, -1530992060);
    d = hh(d, a, b, c, k[4], 11, 1272893353);
    c = hh(c, d, a, b, k[7], 16, -155497632);
    b = hh(b, c, d, a, k[10], 23, -1094730640);
    a = hh(a, b, c, d, k[13], 4, 681279174);
    d = hh(d, a, b, c, k[0], 11, -358537222);
    c = hh(c, d, a, b, k[3], 16, -722521979);
    b = hh(b, c, d, a, k[6], 23, 76029189);
    a = hh(a, b, c, d, k[9], 4, -640364487);
    d = hh(d, a, b, c, k[12], 11, -421815835);
    c = hh(c, d, a, b, k[15], 16, 530742520);
    b = hh(b, c, d, a, k[2], 23, -995338651);
    a = ii(a, b, c, d, k[0], 6, -198630844);
    d = ii(d, a, b, c, k[7], 10, 1126891415);
    c = ii(c, d, a, b, k[14], 15, -1416354905);
    b = ii(b, c, d, a, k[5], 21, -57434055);
    a = ii(a, b, c, d, k[12], 6, 1700485571);
    d = ii(d, a, b, c, k[3], 10, -1894986606);
    c = ii(c, d, a, b, k[10], 15, -1051523);
    b = ii(b, c, d, a, k[1], 21, -2054922799);
    a = ii(a, b, c, d, k[8], 6, 1873313359);
    d = ii(d, a, b, c, k[15], 10, -30611744);
    c = ii(c, d, a, b, k[6], 15, -1560198380);
    b = ii(b, c, d, a, k[13], 21, 1309151649);
    a = ii(a, b, c, d, k[4], 6, -145523070);
    d = ii(d, a, b, c, k[11], 10, -1120210379);
    c = ii(c, d, a, b, k[2], 15, 718787259);
    b = ii(b, c, d, a, k[9], 21, -343485551);
    x[0] = add32(a, x[0]);
    x[1] = add32(b, x[1]);
    x[2] = add32(c, x[2]);
    x[3] = add32(d, x[3]);
}
function cmn(q, a, b, x, s, t) {
    a = add32(add32(a, q), add32(x, t));
    return add32((a << s) | (a >>> (32 - s)), b);
}
function ff(a, b, c, d, x, s, t) { return cmn((b & c) | ((~b) & d), a, b, x, s, t); }
function gg(a, b, c, d, x, s, t) { return cmn((b & d) | (c & (~d)), a, b, x, s, t); }
function hh(a, b, c, d, x, s, t) { return cmn(b ^ c ^ d, a, b, x, s, t); }
function ii(a, b, c, d, x, s, t) { return cmn(c ^ (b | (~d)), a, b, x, s, t); }
function md51(s) {
    var n = s.length;
    var state = [1732584193, -271733879, -1732584194, 271733878];
    var i;
    for (i = 64; i <= s.length; i += 64) {
        md5cycle(state, md5blk(s.substring(i - 64, i)));
    }
    s = s.substring(i - 64);
    var tail = new Array(16);
    for (i = 0; i < 16; i++) tail[i] = 0;
    for (i = 0; i < s.length; i++) tail[i >> 2] |= s.charCodeAt(i) << ((i % 4) << 3);
    tail[i >> 2] |= 0x80 << ((i % 4) << 3);
    if (i > 55) {
        md5cycle(state, tail);
        for (i = 0; i < 16; i++) tail[i] = 0;
    }
    tail[14] = n * 8;
    md5cycle(state, tail);
    return state;
}
function md5blk(s) {
    var md5blks = [];
    for (var i = 0; i < 64; i += 4) {
        md5blks[i >> 2] = s.charCodeAt(i) + (s.charCodeAt(i + 1) << 8) + (s.charCodeAt(i + 2) << 16) + (s.charCodeAt(i + 3) << 24);
    }
    return md5blks;
}
var hex_chr = '0123456789abcdef'.split('');
function rhex(n) {
    var s = '', j = 0;
    for (; j < 4; j++) s += hex_chr[(n >> (j * 8 + 4)) & 0x0F] + hex_chr[(n >> (j * 8)) & 0x0F];
    return s;
}
function hex(x) {
    for (var i = 0; i < x.length; i++) x[i] = rhex(x[i]);
    return x.join('');
}
function md5(s) {
    return hex(md51(unescape(encodeURIComponent(s))));
}
function add32(a, b) {
    return (a + b) & 0xFFFFFFFF;
}
