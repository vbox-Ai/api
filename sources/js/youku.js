/*
 * 优酷 JS 蜘蛛
 * 适配 vbox-ios JSSpiderEngine / QJSSpiderEngine（type:3 独立引擎）
 * 说明：直接返回优酷页面URL，parse:1 交给App解析器处理
 */

var spider = {
    __jsEvalReturn: function() {
        var HOST = 'https://www.youku.com';
        var UA = 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36';
        var HEADERS = {
            'User-Agent': UA,
            'Referer': HOST + '/',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            'Accept-Language': 'zh-CN,zh;q=0.9'
        };

        var CHANNELS = {
            '1': { name: '电视剧', cid: '97' },
            '2': { name: '电影', cid: '96' },
            '3': { name: '综艺', cid: '85' },
            '4': { name: '动漫', cid: '100' },
            '5': { name: '少儿', cid: '87' },
            '6': { name: '纪录片', cid: '98' },
            '7': { name: '体育', cid: '91' }
        };

        function firstValid(obj, keys) {
            if (!obj) return '';
            for (var i = 0; i < keys.length; i++) {
                var v = obj[keys[i]];
                if (v !== undefined && v !== null && v !== '') return v;
            }
            return '';
        }

        function normalizePic(url) {
            if (!url) return '';
            url = String(url).trim();
            if (!url) return '';
            if (url.indexOf('//') === 0) return 'https:' + url;
            if (url.indexOf('http://') === 0) return 'https://' + url.substring(7);
            if (url.indexOf('https://') === 0) return url;
            return url;
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

        function httpGet(url) {
            try {
                var resp = req(url, { method: 'GET', headers: HEADERS, timeout: 15000 });
                if (!resp) return '';
                if (typeof resp === 'string') return resp;
                return resp.content || resp.data || resp.body || '';
            } catch (e) {
                print('>>> youku httpGet ERROR: ' + e);
                return '';
            }
        }

        function extractIdFromUrl(url) {
            if (!url) return '';
            var m = url.match(/id_([a-zA-Z0-9=]+)\.html/);
            if (m && m[1]) return m[1];
            m = url.match(/\/show\/([a-zA-Z0-9=]+)\.html/);
            if (m && m[1]) return m[1];
            return url;
        }

        function homeContent(filter) {
            var classes = [];
            for (var k in CHANNELS) {
                if (CHANNELS.hasOwnProperty(k)) {
                    classes.push({ type_id: k, type_name: CHANNELS[k].name });
                }
            }
            return { class: classes, list: [], filters: {} };
        }

        function homeVideoContent() {
            var videos = [];
            try {
                for (var cid in CHANNELS) {
                    if (!CHANNELS.hasOwnProperty(cid)) continue;
                    var data = categoryContent(cid, '1', false, {});
                    if (data && data.list) {
                        for (var i = 0; i < data.list.length && i < 6; i++) {
                            videos.push(data.list[i]);
                        }
                    }
                    if (videos.length >= 24) break;
                }
            } catch (e) {
                print('>>> youku homeVideoContent ERROR: ' + e);
            }
            return { list: videos };
        }

        function categoryContent(tid, pg, filter, extend) {
            var page = Math.max(parseInt(pg) || 1, 1);
            var channel = CHANNELS[tid] || CHANNELS['1'];
            var pageSize = 20;
            var results = [];

            try {
                var listUrl = 'https://list.youku.com/category/show/c_' + channel.cid + '_s_1_d_1_p_' + page + '.html';
                var html = httpGet(listUrl);

                // 尝试从script标签提取JSON数据
                var scriptMatch = html.match(/var\s+__INITIAL_DATA__\s*=\s*({[\s\S]*?});\s*<\/script>/);
                if (scriptMatch) {
                    try {
                        var initialData = JSON.parse(scriptMatch[1]);
                        var items = [];
                        if (initialData.data) {
                            if (initialData.data.show) items = initialData.data.show;
                            else if (initialData.data.list) items = initialData.data.list;
                        } else if (initialData.show) items = initialData.show;
                        else if (initialData.list) items = initialData.list;

                        if (!Array.isArray(items) && items.items) items = items.items;

                        for (var i = 0; i < items.length; i++) {
                            var item = items[i] || {};
                            var picUrl = firstValid(item, ['img', 'imgUrl', 'poster', 'vthumburl', 'thumburl', 'cover', 'bigthumburl', 'logo', 'pic']);
                            var id = firstValid(item, ['showid', 'id', 'videoId', 'encodeId', 'aid']);
                            if (!id && item.link) {
                                id = extractIdFromUrl(item.link);
                            }
                            if (!id && item.url) {
                                id = extractIdFromUrl(item.url);
                            }

                            if (id) {
                                results.push({
                                    vod_id: String(id),
                                    vod_name: item.title || item.name || item.subtitle || item.showname || '',
                                    vod_pic: normalizePic(picUrl),
                                    vod_remarks: item.subtitle || item.episodeTotal || item.updateInfo || item.quality || item.point || '',
                                    vod_year: item.year || ''
                                });
                            }
                        }
                    } catch (e) {}
                }

                // 正则兜底提取
                if (results.length === 0) {
                    var liRegex = /<li[^>]*class="[^"]*card[^"]*"[^>]*>[\s\S]*?<\/li>/g;
                    var liMatches = html.match(liRegex);
                    if (liMatches) {
                        for (var j = 0; j < liMatches.length; j++) {
                            var liHtml = liMatches[j];
                            var idMatch = liHtml.match(/href="[^"]*id_([a-zA-Z0-9=]+)\.html/);
                            var titleMatch = liHtml.match(/title="([^"]+)"/);
                            var imgMatch = liHtml.match(/src="([^"]+)"/) || liHtml.match(/data-src="([^"]+)"/);
                            var remarkMatch = liHtml.match(/<span[^>]*class="[^"]*tag[^"]*"[^>]*>([^<]+)<\/span>/);

                            if (idMatch && titleMatch) {
                                results.push({
                                    vod_id: idMatch[1],
                                    vod_name: titleMatch[1],
                                    vod_pic: imgMatch ? normalizePic(imgMatch[1]) : '',
                                    vod_remarks: remarkMatch ? remarkMatch[1].trim() : '',
                                    vod_year: ''
                                });
                            }
                        }
                    }
                }

                // 去重
                var unique = [];
                var seen = {};
                for (var k = 0; k < results.length; k++) {
                    if (results[k].vod_id && !seen[results[k].vod_id]) {
                        seen[results[k].vod_id] = true;
                        unique.push(results[k]);
                    }
                }

                return {
                    page: page,
                    pagecount: page + 1,
                    limit: pageSize,
                    total: pageSize * (page + 1),
                    list: unique
                };
            } catch (e) {
                print('>>> youku categoryContent ERROR: ' + e);
                return { page: page, pagecount: page, limit: pageSize, total: 0, list: [] };
            }
        }

        function detailContent(ids) {
            var result = { list: [] };
            try {
                var id = Array.isArray(ids) ? String(ids[0]) : String(ids);
                if (!id) return result;

                // 从URL中提取ID
                id = extractIdFromUrl(id);

                var detailUrl = 'https://v.youku.com/v_show/id_' + id + '.html';
                var html = httpGet(detailUrl);

                var title = '';
                var picUrl = '';
                var desc = '';
                var playUrls = [];

                // 提取标题
                var titleMatch = html.match(/<h1[^>]*class="[^"]*title[^"]*"[^>]*>([^<]+)<\/h1>/) ||
                               html.match(/<title>([^<_]+)[_-]优酷<\/title>/);
                if (titleMatch) title = titleMatch[1].trim();

                // 提取封面图
                var picMatch = html.match(/<img[^>]*class="[^"]*poster[^"]*"[^>]*src="([^"]+)"/) ||
                              html.match(/"poster":"([^"]+)"/) ||
                              html.match(/"img":"([^"]+)"/) ||
                              html.match(/og:image[^>]*content="([^"]+)"/);
                if (picMatch) picUrl = normalizePic(picMatch[1]);

                // 提取描述
                var descMatch = html.match(/<p[^>]*class="[^"]*desc[^"]*"[^>]*>([\s\S]*?)<\/p>/);
                if (descMatch) desc = descMatch[1].replace(/<[^>]+>/g, '').trim();

                // 尝试提取分集链接
                var epRegex = /<a[^>]*href="(\/v_show\/id_[^"]+)"[^>]*>([^<]+)<\/a>/g;
                var epMatches;
                var seenEps = {};
                var eps = [];

                while ((epMatches = epRegex.exec(html)) !== null) {
                    var epUrl = epMatches[1];
                    var epTitle = epMatches[2].trim();
                    if (epUrl && epTitle && epTitle.match(/^第?\d+[集话期]?$/) && !seenEps[epUrl]) {
                        seenEps[epUrl] = true;
                        if (epUrl.indexOf('http') !== 0) {
                            epUrl = 'https:' + epUrl;
                        }
                        eps.push({ title: epTitle, url: epUrl });
                    }
                }

                if (eps.length > 0) {
                    for (var i = 0; i < eps.length; i++) {
                        playUrls.push(eps[i].title + '$' + eps[i].url);
                    }
                } else {
                    playUrls.push((title || '正片') + '$' + detailUrl);
                }

                result.list.push({
                    vod_id: id,
                    vod_name: title || '优酷视频',
                    vod_pic: picUrl,
                    vod_content: desc,
                    vod_play_from: '优酷',
                    vod_play_url: playUrls.join('#'),
                    vod_director: '',
                    vod_actor: ''
                });
            } catch (e) {
                print('>>> youku detailContent ERROR: ' + e);
                // 兜底返回
                var id = Array.isArray(ids) ? String(ids[0]) : String(ids);
                id = extractIdFromUrl(id);
                var fallbackUrl = 'https://v.youku.com/v_show/id_' + id + '.html';
                result.list.push({
                    vod_id: id,
                    vod_name: '优酷视频',
                    vod_pic: '',
                    vod_content: '',
                    vod_play_from: '优酷',
                    vod_play_url: '正片$' + fallbackUrl
                });
            }
            return result;
        }

        function searchContent(key, quick, pg) {
            if (pg === undefined && quick !== undefined) pg = quick;
            var page = Math.max(parseInt(pg) || 1, 1);
            var pageSize = 20;
            var results = [];

            if (!key) return { list: results, page: page, pagecount: page, limit: pageSize, total: 0 };

            try {
                var searchUrl = 'https://search.youku.com/searchpc/search?keyword=' + encodeURIComponent(key) + '&pn=' + page + '&ccat=';
                var html = httpGet(searchUrl);

                // 尝试提取INITIAL_DATA
                var scriptMatch = html.match(/window\.__INITIAL_DATA__\s*=\s*({[\s\S]*?});\s*<\/script>/);
                if (scriptMatch) {
                    try {
                        var searchData = JSON.parse(scriptMatch[1]);
                        var items = [];
                        if (searchData.data) {
                            if (searchData.data.result) items = searchData.data.result;
                            else if (searchData.data.video) items = searchData.data.video;
                            else if (searchData.data.list) items = searchData.data.list;
                        } else if (searchData.result) items = searchData.result;
                        else if (searchData.items) items = searchData.items;

                        if (!Array.isArray(items) && items.video) items = items.video;
                        if (!Array.isArray(items) && items.list) items = items.list;

                        for (var i = 0; i < items.length; i++) {
                            var item = items[i] || {};
                            var picUrl = firstValid(item, ['img', 'imgUrl', 'poster', 'vthumburl', 'thumburl', 'cover', 'bigthumburl']);
                            var id = firstValid(item, ['showid', 'id', 'encodeId', 'videoId', 'aid']);
                            if (!id && item.url) id = extractIdFromUrl(item.url);
                            if (!id && item.link) id = extractIdFromUrl(item.link);

                            if (id) {
                                results.push({
                                    vod_id: String(id),
                                    vod_name: item.title || item.name || item.subtitle || item.keyword || '',
                                    vod_pic: normalizePic(picUrl),
                                    vod_remarks: item.category || item.area || item.year || item.desc || ''
                                });
                            }
                        }
                    } catch (e) {}
                }

                // 正则兜底提取
                if (results.length === 0) {
                    var itemRegex = /<div[^>]*class="[^"]*pack-cover[^"]*"[^>]*>[\s\S]*?<\/div>/g;
                    var matches = html.match(itemRegex);
                    if (matches) {
                        for (var j = 0; j < matches.length; j++) {
                            var itemHtml = matches[j];
                            var idMatch = itemHtml.match(/href="[^"]*id_([a-zA-Z0-9=]+)\.html/);
                            var titleMatch = itemHtml.match(/title="([^"]+)"/);
                            var imgMatch = itemHtml.match(/src="([^"]+)"/) || itemHtml.match(/data-src="([^"]+)"/);

                            if (idMatch && titleMatch) {
                                results.push({
                                    vod_id: idMatch[1],
                                    vod_name: titleMatch[1],
                                    vod_pic: imgMatch ? normalizePic(imgMatch[1]) : '',
                                    vod_remarks: ''
                                });
                            }
                        }
                    }
                }

                // 去重
                var unique = [];
                var seen = {};
                for (var k = 0; k < results.length; k++) {
                    if (results[k].vod_id && !seen[results[k].vod_id]) {
                        seen[results[k].vod_id] = true;
                        unique.push(results[k]);
                    }
                }

                return {
                    page: page,
                    pagecount: page + 1,
                    limit: pageSize,
                    total: pageSize * (page + 1),
                    list: unique
                };
            } catch (e) {
                print('>>> youku searchContent ERROR: ' + e);
                return { page: page, pagecount: page, limit: pageSize, total: 0, list: [] };
            }
        }

        function playerContent(flag, id, vipFlags) {
            var playUrl = vipFlags || id || flag || '';
            if (playUrl.indexOf('$') >= 0) {
                var parts = playUrl.split('$');
                playUrl = parts[parts.length - 1];
            }
            playUrl = String(playUrl).trim();

            if (!playUrl) {
                playUrl = HOST;
            } else if (playUrl.indexOf('http') !== 0) {
                // 从ID构造URL
                var vid = extractIdFromUrl(playUrl);
                playUrl = 'https://v.youku.com/v_show/id_' + vid + '.html';
            }

            if (playUrl.indexOf('http://') === 0) {
                playUrl = 'https://' + playUrl.substring(7);
            }

            var direct = isVideoFormat(playUrl);
            return {
                parse: direct ? 0 : 1,
                jx: direct ? 0 : 1,
                playUrl: playUrl,
                url: playUrl,
                header: JSON.stringify(HEADERS)
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
