/*
 * 爱奇艺 JS 蜘蛛
 * 适配 vbox-ios JSSpiderEngine / QJSSpiderEngine (type:3 独立引擎)
 * 来源：由 Python 版爱奇艺蜘蛛移植
 * 说明：播放返回爱奇艺移动端页面 URL，parse:1 交给 App 解析器处理。
 */

var spider = {
    __jsEvalReturn: function() {
        var HOST = 'https://m.iqiyi.com';
        var PCW_API = 'https://pcw-api.iqiyi.com';
        var SEARCH_API = 'https://search.video.iqiyi.com/o';
        var UA = 'Mozilla/5.0 (iPhone; CPU iPhone OS 16_6 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.6 Mobile/15E148 Safari/604.1';
        var HEADERS = {
            'User-Agent': UA,
            'Referer': HOST,
            'Accept': 'application/json, text/plain, */*',
            'Accept-Language': 'zh-CN,zh;q=0.9'
        };

        var CHANNELS = {
            '1': { name: '电影', channel_id: '1' },
            '2': { name: '电视剧', channel_id: '2' },
            '3': { name: '动漫', channel_id: '3' },
            '4': { name: '综艺', channel_id: '4' },
            '6': { name: '纪录片', channel_id: '6' },
            '7': { name: '短片', channel_id: '7' },
            '8': { name: '少儿', channel_id: '8' }
        };

        var FILTERS = {
            '1': commonFilters([
                ['全部类型', '0'], ['动作', '1'], ['喜剧', '2'], ['爱情', '3'], ['科幻', '4'], ['恐怖', '5'], ['剧情', '6'], ['战争', '7'], ['悬疑', '8'], ['动画', '9'], ['奇幻', '10'], ['冒险', '11'], ['犯罪', '12'], ['惊悚', '13']
            ]),
            '2': commonFilters([
                ['全部类型', '0'], ['自制', '1'], ['古装', '2'], ['言情', '3'], ['武侠', '4'], ['偶像', '5'], ['家庭', '6'], ['青春', '7'], ['都市', '8'], ['喜剧', '9'], ['战争', '10'], ['军旅', '11'], ['谍战', '12'], ['悬疑', '13'], ['罪案', '14'], ['穿越', '15'], ['宫廷', '16'], ['历史', '17'], ['神话', '18'], ['科幻', '19'], ['年代', '20'], ['农村', '21'], ['商战', '22'], ['剧情', '23'], ['奇幻', '24'], ['网剧', '25'], ['竖短片', '26']
            ]),
            '3': commonFilters([
                ['全部类型', '0'], ['热血', '1'], ['恋爱', '2'], ['科幻', '3'], ['奇幻', '4'], ['冒险', '5'], ['搞笑', '6'], ['战斗', '7'], ['神魔', '8'], ['竞技', '9'], ['日常', '10'], ['校园', '11'], ['治愈', '12'], ['悬疑', '13']
            ]),
            '4': commonFilters([
                ['全部类型', '0'], ['真人秀', '1'], ['脱口秀', '2'], ['选秀', '3'], ['访谈', '4'], ['情感', '5'], ['生活', '6'], ['美食', '7'], ['旅游', '8'], ['游戏', '9'], ['音乐', '10'], ['时尚', '11'], ['文化', '12'], ['搞笑', '13']
            ]),
            '6': commonFilters([
                ['全部类型', '0'], ['自然', '1'], ['历史', '2'], ['人文', '3'], ['社会', '4'], ['科技', '5'], ['探险', '6'], ['军事', '7'], ['传记', '8']
            ]),
            '7': [
                makeFilter('mode', '排序', [['综合排序', '24'], ['热播榜', '11'], ['新上线', '8']]),
                makeFilter('year', '年份', [['全部年份', '0'], ['2026', '2026'], ['2025', '2025'], ['2024', '2024'], ['2023', '2023'], ['2022', '2022']]),
                makeFilter('pay', '资费', [['全部资费', '0'], ['免费', '1'], ['付费', '2']])
            ],
            '8': commonFilters([
                ['全部类型', '0'], ['动画', '1'], ['儿歌', '2'], ['早教', '3'], ['益智', '4'], ['故事', '5'], ['科普', '6']
            ])
        };

        function makeFilter(key, name, values) {
            var value = [];
            for (var i = 0; i < values.length; i++) {
                value.push({ n: values[i][0], v: values[i][1] });
            }
            return { key: key, name: name, value: value };
        }

        function commonFilters(typeValues) {
            return [
                makeFilter('mode', '排序', [['综合排序', '24'], ['热播榜', '11'], ['新上线', '8']]),
                makeFilter('area', '地区', [['全部地区', '0'], ['内地', '1'], ['香港/港台', '2'], ['台湾地区', '3'], ['美国/欧美', '4'], ['韩国', '5'], ['日本', '6'], ['泰国', '7'], ['英国', '8'], ['其它', '9']]),
                makeFilter('type', '类型', typeValues),
                makeFilter('year', '年份', [['全部年份', '0'], ['2026', '2026'], ['2025', '2025'], ['2024', '2024'], ['2023', '2023'], ['2022', '2022'], ['2021', '2021'], ['2020', '2020'], ['2019', '2019'], ['2018', '2018'], ['2017', '2017'], ['2016', '2016'], ['2015', '2015'], ['更早', '-2015']]),
                makeFilter('pay', '资费', [['全部资费', '0'], ['免费', '1'], ['付费', '2']])
            ];
        }

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
                    print('>>> iqiyi fetch null: ' + fullUrl.substring(0, 120));
                    return null;
                }
                var text = (typeof resp === 'string') ? resp : (resp.content || resp.data || '');
                if (typeof text === 'object') return text;
                if (!text) {
                    print('>>> iqiyi fetch empty: ' + fullUrl.substring(0, 120));
                    return null;
                }
                return JSON.parse(text);
            } catch (e) {
                print('>>> iqiyi fetchJson ERROR: ' + e);
                return null;
            }
        }

        function normalizePlayUrl(url) {
            if (!url) return '';
            return String(url)
                .replace('http://m.iqiyi.com/', 'https://www.iqiyi.com/')
                .replace('https://m.iqiyi.com/', 'https://www.iqiyi.com/')
                .replace('http://www.iqiyi.com/', 'https://www.iqiyi.com/');
        }

        function normalizePic(url) {
            if (!url) return '';
            url = String(url);
            if (url.indexOf('//') === 0) return 'https:' + url;
            if (url.indexOf('http://') === 0) return 'https://' + url.substring(7);
            return url;
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
            return raw.trim();
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

        function parseVideoItem(item) {
            item = item || {};
            return {
                vod_id: String(item.albumId || item.qipuId || ''),
                vod_name: item.name || item.title || '',
                vod_pic: normalizePic(item.imageUrl || item.albumImageUrl || ''),
                vod_remarks: item.focus || (item.latestOrder ? ('更新至' + item.latestOrder + '集') : ''),
                vod_year: item.period ? String(item.period).substring(0, 4) : '',
                vod_area: item.categories && item.categories.join ? item.categories.join(',') : ''
            };
        }

        function extractAlbumName(name, shortTitle) {
            var text = name || shortTitle || '';
            if (!text) return '';
            var m = text.match(/^(.*?)(第\d+集|第[一二三四五六七八九十百]+集|预告|片花|花絮|特辑)/);
            if (m && m[1]) return m[1].trim();
            return text.indexOf('第') === 0 ? text : text.trim();
        }

        function parseExtend(extend) {
            if (!extend) return {};
            if (typeof extend === 'object') return extend;
            try { return JSON.parse(extend); } catch (e) { return {}; }
        }

        function homeContent(filter) {
            var classes = [];
            for (var k in CHANNELS) {
                if (CHANNELS.hasOwnProperty(k)) {
                    classes.push({ type_id: k, type_name: CHANNELS[k].name });
                }
            }
            var result = { class: classes, list: [] };
            if (filter) result.filters = FILTERS;
            return result;
        }

        function homeVideoContent() {
            var videos = [];
            var channelIds = ['2', '1', '3', '4'];
            try {
                for (var i = 0; i < channelIds.length; i++) {
                    var cid = channelIds[i];
                    var data = fetchJson(PCW_API + '/search/recommend/list', {
                        channel_id: CHANNELS[cid].channel_id,
                        data_type: '1',
                        mode: '11',
                        page_id: '1',
                        ret_num: '12',
                        session: ''
                    });
                    var list = data && data.code === 'A00000' && data.data ? (data.data.list || []) : [];
                    for (var j = 0; j < list.length && j < 6; j++) {
                        var vod = parseVideoItem(list[j]);
                        if (vod.vod_id && vod.vod_name) videos.push(vod);
                    }
                    if (videos.length >= 24) break;
                }
            } catch (e) {
                print('>>> iqiyi homeVideoContent ERROR: ' + e);
            }
            return { list: videos };
        }

        function categoryContent(tid, pg, extend) {
            var page = Math.max(parseInt(pg) || 1, 1);
            var ext = parseExtend(extend);
            var channel = CHANNELS[tid] || CHANNELS['2'];
            var videos = [];
            var pagecount = page;
            var total = 0;
            try {
                var data = fetchJson(PCW_API + '/search/recommend/list', {
                    channel_id: channel.channel_id,
                    data_type: '1',
                    mode: ext.mode || '24',
                    area: ext.area || '',
                    type: ext.type || '',
                    year: ext.year || '',
                    pay: ext.pay || '',
                    page_id: String(page),
                    ret_num: '48',
                    session: ''
                });
                var list = data && data.code === 'A00000' && data.data ? (data.data.list || []) : [];
                for (var i = 0; i < list.length; i++) {
                    var vod = parseVideoItem(list[i]);
                    if (vod.vod_id && vod.vod_name) videos.push(vod);
                }
                var hasNext = data && data.data ? (data.data.has_next || data.data.hasMore || 0) : 0;
                pagecount = hasNext ? page + 1 : page;
                total = videos.length * page;
            } catch (e) {
                print('>>> iqiyi categoryContent ERROR: ' + e);
            }
            return { list: videos, page: page, pagecount: pagecount, limit: 48, total: total };
        }

        function detailContent(ids) {
            var result = { list: [] };
            try {
                var videoId = normalizeIds(ids);
                if (!videoId) return result;
                var albumId = videoId.indexOf('_') >= 0 ? videoId.split('_')[0] : videoId;
                var episodes = [];
                var firstEp = {};
                var albumName = '', albumPic = '', albumDesc = '';
                var directors = [], actors = [];
                var total = 0;

                for (var p = 1; p <= 10; p++) {
                    var data = fetchJson(PCW_API + '/albums/album/avlistinfo', {
                        aid: albumId,
                        page: String(p),
                        size: '30'
                    });
                    if (!data || data.code !== 'A00000' || !data.data) break;
                    var eps = data.data.epsodelist || [];
                    if (p === 1) {
                        total = parseInt(data.data.total || data.data.videoCount || eps.length) || eps.length;
                    }
                    for (var i = 0; i < eps.length; i++) episodes.push(eps[i]);
                    if (!data.data.hasMore && episodes.length >= total) break;
                    if (eps.length === 0) break;
                }

                firstEp = episodes.length ? episodes[0] : {};
                var tvId = firstEp.tvId || albumId;
                if (tvId) {
                    var baseData = fetchJson(PCW_API + '/video/video/baseinfo/' + tvId);
                    if (baseData && baseData.code === 'A00000' && baseData.data) {
                        var base = baseData.data;
                        albumName = base.albumName || '';
                        albumPic = base.albumImageUrl || base.imageUrl || '';
                        albumDesc = base.description || '';
                        var people = base.people || {};
                        var ds = people.director || [];
                        for (var d = 0; d < ds.length; d++) if (ds[d].name) directors.push(ds[d].name);
                        var as = people.main_charactor || [];
                        for (var a = 0; a < as.length; a++) if (as[a].name) actors.push(as[a].name);
                        if (episodes.length === 0 && base.playUrl) {
                            episodes.push({
                                shortTitle: base.name || albumName,
                                name: base.name || albumName,
                                playUrl: base.playUrl,
                                imageUrl: base.imageUrl || '',
                                duration: base.duration || '',
                                description: base.description || ''
                            });
                            firstEp = episodes[0];
                        }
                    }
                }

                if (!albumName && firstEp) albumName = extractAlbumName(firstEp.name, firstEp.shortTitle);
                if (!albumPic && firstEp) albumPic = firstEp.imageUrl || '';
                if (!albumDesc && firstEp) albumDesc = firstEp.description || '';

                var playUrls = [];
                for (var e = 0; e < episodes.length; e++) {
                    var ep = episodes[e] || {};
                    var epName = ep.shortTitle || ep.name || ('第' + (e + 1) + '集');
                    var epUrl = normalizePlayUrl(ep.playUrl || '');
                    if (epUrl) playUrls.push(epName + '$' + epUrl);
                }

                result.list.push({
                    vod_id: videoId,
                    vod_name: albumName || '爱奇艺资源',
                    vod_pic: albumPic || '',
                    vod_remarks: episodes.length > 1 ? ('共' + episodes.length + '集') : ((firstEp && firstEp.duration) || '电影'),
                    vod_actor: actors.slice(0, 8).join(' '),
                    vod_director: directors.slice(0, 3).join(' '),
                    vod_content: albumDesc ? String(albumDesc).replace(/\n\n/g, '\n').trim() : '',
                    vod_play_from: '爱奇艺',
                    vod_play_url: playUrls.join('#')
                });
            } catch (e) {
                print('>>> iqiyi detailContent ERROR: ' + e);
            }
            return result;
        }

        function searchContent(key, quick, pg) {
            if (pg === undefined && quick !== undefined) pg = quick;
            var page = Math.max(parseInt(pg) || 1, 1);
            var videos = [];
            if (!key) return { list: videos, page: page, pagecount: page, limit: 25, total: 0 };
            try {
                var data = fetchJson(SEARCH_API, {
                    'if': 'html5',
                    key: key,
                    pageNum: String(page),
                    pageSize: '25'
                });
                var docs = data && data.data ? (data.data.docinfos || []) : [];
                var seen = {};
                for (var i = 0; i < docs.length; i++) {
                    var album = docs[i].albumDocInfo || {};
                    var siteId = album.siteId || '';
                    var albumId = album.albumId || album.qipu_id || '';
                    var title = album.albumTitle || '';
                    if (siteId && siteId !== 'iqiyi') continue;
                    if (!albumId || !title) continue;
                    albumId = String(albumId);
                    if (seen[albumId]) continue;
                    seen[albumId] = true;
                    videos.push({
                        vod_id: albumId,
                        vod_name: title,
                    vod_pic: normalizePic(album.albumVImage || album.albumImg || ''),
                        vod_remarks: album.tvFocus || (album.itemTotalNumber ? (album.itemTotalNumber + '集') : '')
                    });
                }
            } catch (e) {
                print('>>> iqiyi searchContent ERROR: ' + e);
            }
            return { list: videos, page: page, pagecount: videos.length >= 25 ? page + 1 : page, limit: 25, total: videos.length };
        }

        function playerContent(flag, id, vipFlags) {
            var playUrl = vipFlags || id || flag || '';
            if (playUrl.indexOf('$') >= 0) {
                var parts = playUrl.split('$');
                playUrl = parts[parts.length - 1];
            }
            playUrl = normalizePlayUrl(playUrl);
            var direct = isVideoFormat(playUrl);
            return {
                parse: direct ? 0 : 1,
                jx: direct ? 0 : 1,
                url: playUrl,
                header: HEADERS
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
