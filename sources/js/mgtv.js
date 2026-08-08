/*
 * 芒果 TV JS 蜘蛛
 * 适配 vbox-ios JSSpiderEngine / QJSSpiderEngine（type:3 独立引擎）
 * 来源：由 Python 版芒果蜘蛛移植
 * 说明：播放返回芒果 TV 页面 URL，parse:1 交给 App 解析器处理。
 */

var spider = {
    __jsEvalReturn: function() {
        var RHOST = 'https://www.mgtv.com';
        var HOST = 'https://pianku.api.mgtv.com';
        var VHOST = 'https://pcweb.api.mgtv.com';
        var MHOST = 'https://dc.bz.mgtv.com';
        var SHOST = 'https://mobileso.bz.mgtv.com';
        var UA = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36';
        var HEADERS = {
            'User-Agent': UA,
            'origin': RHOST,
            'referer': RHOST + '/',
            'Accept': 'application/json, text/plain, */*',
            'Accept-Language': 'zh-CN,zh;q=0.9'
        };

        var CHANNELS = {
            '3': '电影',
            '2': '电视剧',
            '1': '综艺',
            '50': '动画',
            '10': '少儿',
            '51': '纪录片',
            '115': '教育'
        };

        var filterCache = {};

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

        function fetchJson(url, params) {
            try {
                var fullUrl = params ? buildUrl(url, params) : url;
                var resp = req(fullUrl, { method: 'GET', headers: HEADERS, timeout: 15000 });
                if (!resp) {
                    print('>>> mgtv fetch null: ' + fullUrl.substring(0, 120));
                    return null;
                }
                var text = (typeof resp === 'string') ? resp : (resp.content || resp.data || '');
                if (typeof text === 'object') return text;
                if (!text) {
                    print('>>> mgtv fetch empty: ' + fullUrl.substring(0, 120));
                    return null;
                }
                return JSON.parse(text);
            } catch (e) {
                print('>>> mgtv fetchJson ERROR: ' + e);
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
            if (url.charAt(0) === '/') return RHOST + url;
            return RHOST + '/' + url;
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
            var m = raw.match(/\/(\d+)\.html/);
            if (m && m[1]) return m[1];
            return raw.trim();
        }

        function cleanTitle(title, fallback) {
            title = String(title || fallback || '播放').replace(/\\[rnt]/g, ' ').replace(/[\r\n\t]+/g, ' ').replace(/\s+/g, ' ').trim();
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

        function getFilters(tid) {
            if (filterCache[tid]) return filterCache[tid];
            var filters = [];
            try {
                var data = fetchJson(HOST + '/rider/config/channel/v1', {
                    allowedRC: '1',
                    channelId: tid,
                    platform: 'pcweb',
                    _support: '10000000'
                });
                var items = data && data.data ? (data.data.listItems || []) : [];
                for (var i = 0; i < items.length; i++) {
                    var item = items[i] || {};
                    var values = [];
                    var arr = item.items || [];
                    for (var j = 0; j < arr.length; j++) {
                        if (arr[j] && arr[j].tagName) {
                            values.push({ n: arr[j].tagName, v: String(arr[j].tagId || '') });
                        }
                    }
                    if (item.eName && item.typeName && values.length) {
                        filters.push({ key: item.eName, name: item.typeName, value: values });
                    }
                }
            } catch (e) {
                print('>>> mgtv getFilters ERROR: ' + e);
            }
            filterCache[tid] = filters;
            return filters;
        }

        function parseListItem(item) {
            item = item || {};
            var id = item.playPartId || item.videoId || item.vid || '';
            return {
                vod_id: String(id),
                vod_name: item.title || item.videoName || item.name || '',
                vod_pic: normalizePic(item.img || item.vImg || item.image || ''),
                vod_year: (item.rightCorner && item.rightCorner.text) || item.cornerTitle || item.year || '',
                vod_remarks: item.updateInfo || item.time || item.desc || ''
            };
        }

        function homeContent(filter) {
            var classes = [];
            var filters = {};
            for (var tid in CHANNELS) {
                if (CHANNELS.hasOwnProperty(tid)) {
                    classes.push({ type_id: tid, type_name: CHANNELS[tid] });
                    if (filter) filters[tid] = getFilters(tid);
                }
            }
            var result = { class: classes, list: [] };
            if (filter) result.filters = filters;
            return result;
        }

        function homeVideoContent() {
            var videos = [];
            try {
                var url = MHOST + '/dynamic/v1/channel/index/0/0/0/1000000/0/0/17/1354';
                var data = fetchJson(url, {
                    type: '17',
                    version: '5.0',
                    t: String(Date.now()),
                    _support: '10000000'
                });
                var rows = data && data.data ? data.data : [];
                for (var i = 0; i < rows.length; i++) {
                    var dsl = rows[i].DSLList || [];
                    for (var j = 0; j < dsl.length; j++) {
                        var items = dsl[j] && dsl[j].data ? (dsl[j].data.items || []) : [];
                        for (var k = 0; k < items.length; k++) {
                            var vod = parseListItem(items[k]);
                            if (vod.vod_id && vod.vod_name) videos.push(vod);
                            if (videos.length >= 36) return { list: videos };
                        }
                    }
                }
            } catch (e) {
                print('>>> mgtv homeVideoContent ERROR: ' + e);
            }
            return { list: videos };
        }

        function categoryContent(tid, pg, filter, extend) {
            var page = Math.max(parseInt(pg) || 1, 1);
            var ext = parseExtend(extend === undefined ? filter : extend);
            var params = {
                allowedRC: '1',
                platform: 'pcweb',
                channelId: tid,
                pn: String(page),
                pc: '80',
                hudong: '1',
                _support: '10000000'
            };
            for (var k in ext) {
                if (ext.hasOwnProperty(k) && ext[k] !== undefined && ext[k] !== null && ext[k] !== '') {
                    params[k] = ext[k];
                }
            }

            var videos = [];
            try {
                var data = fetchJson(HOST + '/rider/list/pcweb/v3', params);
                var docs = data && data.data ? (data.data.hitDocs || []) : [];
                for (var i = 0; i < docs.length; i++) {
                    var vod = parseListItem(docs[i]);
                    if (vod.vod_id && vod.vod_name) videos.push(vod);
                }
            } catch (e) {
                print('>>> mgtv categoryContent ERROR: ' + e);
            }
            return {
                list: videos,
                page: page,
                pagecount: videos.length >= 80 ? page + 1 : page,
                limit: 80,
                total: videos.length * page
            };
        }

        function fetchEpisodePage(page, id) {
            var result = { totalPage: 1, list: [] };
            try {
                var data = fetchJson(VHOST + '/episode/list', {
                    version: '5.5.35',
                    video_id: id,
                    page: String(page),
                    size: '30',
                    platform: '4',
                    src: 'mgtv',
                    allowedRC: '1',
                    _support: '10000000'
                });
                if (data && data.data) {
                    result.totalPage = parseInt(data.data.total_page || 1) || 1;
                    result.list = data.data.list || [];
                }
            } catch (e) {
                print('>>> mgtv fetchEpisodePage ERROR: ' + e);
            }
            return result;
        }

        function detailContent(ids) {
            var result = { list: [] };
            try {
                var id = normalizeIds(ids);
                if (!id) return result;
                var vdata = fetchJson(VHOST + '/video/info', {
                    allowedRC: '1',
                    vid: id,
                    type: 'b',
                    _support: '10000000'
                });
                var info = vdata && vdata.data ? (vdata.data.info || {}) : {};
                var detail = info.detail || {};
                var vod = {
                    vod_id: id,
                    vod_name: info.title || '',
                    type_name: detail.kind || '',
                    vod_year: detail.releaseTime || '',
                    vod_area: detail.area || '',
                    vod_lang: detail.language || '',
                    vod_remarks: detail.updateInfo || '',
                    vod_actor: detail.leader || '',
                    vod_director: detail.director || '',
                    vod_content: detail.story || '',
                    vod_play_from: '芒果TV',
                    vod_play_url: ''
                };

                var playUrls = [];
                var first = fetchEpisodePage(1, id);
                var totalPage = Math.min(parseInt(first.totalPage || 1) || 1, 10);
                var all = first.list || [];
                for (var p = 2; p <= totalPage; p++) {
                    var next = fetchEpisodePage(p, id);
                    all = all.concat(next.list || []);
                }
                for (var i = 0; i < all.length; i++) {
                    var ep = all[i] || {};
                    var title = cleanTitle(ep.t3 || ep.title, '第' + (i + 1) + '集');
                    var url = normalizePlayUrl(ep.url || '');
                    if (url) playUrls.push(title + '$' + url);
                }
                if (!playUrls.length) {
                    playUrls.push((vod.vod_name || '正片') + '$' + RHOST);
                }
                vod.vod_play_url = playUrls.join('#');
                result.list.push(vod);
            } catch (e) {
                print('>>> mgtv detailContent ERROR: ' + e);
            }
            return result;
        }

        function searchContent(key, quick, pg) {
            if (pg === undefined && quick !== undefined) pg = quick;
            var page = Math.max(parseInt(pg) || 1, 1);
            var videos = [];
            if (!key) return { list: videos, page: page, pagecount: page, limit: 10, total: 0 };
            try {
                var data = fetchJson(SHOST + '/applet/search/v1', {
                    channelCode: 'mobile-wxap',
                    q: key,
                    pn: String(page),
                    pc: '10',
                    _support: '10000000'
                });
                var contents = data && data.data ? (data.data.contents || []) : [];
                for (var i = 0; i < contents.length; i++) {
                    var row = contents[i] || {};
                    var arr = row.data || [];
                    if (!arr.length) continue;
                    var item = arr[0] || {};
                    if (!item.vid || !item.img) continue;
                    videos.push({
                        vod_id: String(item.vid),
                        vod_name: item.title || '',
                        vod_pic: normalizePic(item.img || ''),
                        vod_year: (row.rightTopCorner && row.rightTopCorner.text) || row.year || '',
                        vod_remarks: row.desc && row.desc.join ? row.desc.join('/') : ''
                    });
                }
            } catch (e) {
                print('>>> mgtv searchContent ERROR: ' + e);
            }
            return { list: videos, page: page, pagecount: videos.length >= 10 ? page + 1 : page, limit: 10, total: videos.length };
        }

        function playerContent(flag, id, vipFlags) {
            var playUrl = vipFlags || id || flag || '';
            playUrl = normalizePlayUrl(playUrl);
            var direct = isVideoFormat(playUrl);
            return {
                parse: direct ? 0 : 1,
                jx: direct ? 0 : 1,
                url: playUrl,
                header: direct ? HEADERS : ''
            };
        }

        return {
            init: function(config) { return true; },
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
