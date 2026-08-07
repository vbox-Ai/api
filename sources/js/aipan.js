/*
 * 爱盼 JS 蜘蛛 v1.0
 * 适配 vbox-ios JSSpiderEngine (type:3 独立引擎)
 * 目标站: https://www.aipan.me
 * 特点: 4源并行聚合搜索(本地+pansou+外部盘+小库盘)，豆瓣分类浏览，直接返回多网盘直链
 * 支持网盘：夸克网盘、百度网盘、阿里云盘、UC网盘、115网盘、123云盘、天翼云盘、迅雷云盘、移动云盘、磁力
 * 无需登录，无需加密签名
 *
 * 网盘蜘蛛源约定：
 *   - vod_remarks 以 "☁️" 开头 → 标识为网盘资源，激活网盘UI
 *   - detailContent 的 vod_play_url 返回 JSON 数组 [{"url":"网盘链接","name":"网盘名"}]
 *   - vod_id 编码格式:
 *     搜索结果: {title}|||{url}|||{pan_name}|||{pwd}|||1
 *     豆瓣结果: {title}|||douban|||0
 */

var spider = {
    __jsEvalReturn: function() {

        var BASE_URL = 'https://www.aipan.me';
        var UA = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36';
        var HEADER = {
            'User-Agent': UA,
            'Referer': BASE_URL + '/',
            'Accept': 'application/json'
        };

        // service 类型 → 网盘名称映射
        var SERVICE_MAP = {
            'QUARK': '夸克网盘',
            'BAIDU': '百度网盘',
            'ALIYUN': '阿里云盘',
            'UC': 'UC网盘',
            '115': '115网盘',
            '123': '123云盘',
            'TIANYI': '天翼云盘',
            'XUNLEI': '迅雷云盘',
            'MOBILE': '移动云盘',
            'MAGNET': 'BT磁力',
            'OTHER': '网盘'
        };

        // 4 个搜索源（按速度排序）
        var SEARCH_SOURCES = [
            '/api/sources/local',
            '/api/sources/pansou',
            '/api/sources/external-pan',
            '/api/sources/xiaokupan'
        ];

        // ===================== 工具函数 =====================

        function fetch(url, headers) {
            try {
                var resp = req(url, { headers: headers || HEADER, timeout: 15000 });
                if (resp && resp.ok) {
                    return resp.content || '';
                }
                print('>>> aipan fetch FAIL: status=' + (resp ? resp.status : 'null') + ' url=' + url.substring(0, 80));
                return '';
            } catch (e) {
                print('>>> aipan fetch ERROR: ' + e);
                return '';
            }
        }

        function fetchJSON(url, headers) {
            var html = fetch(url, headers);
            if (!html) return null;
            try {
                return JSON.parse(html);
            } catch (e) {
                print('>>> aipan JSON parse ERROR: ' + e);
                return null;
            }
        }

        function postJSON(url, body, headers) {
            try {
                var h = {};
                var src = headers || HEADER;
                for (var k in src) { h[k] = src[k]; }
                h['Content-Type'] = 'application/json';
                var jsonBody = JSON.stringify(body);
                var resp = req(url, { method: 'POST', headers: h, body: jsonBody, data: jsonBody, timeout: 15000 });
                if (resp && resp.ok) {
                    var content = resp.content || '';
                    if (typeof content === 'object') return content;
                    try { return JSON.parse(content); } catch (e) { return null; }
                }
                print('>>> aipan POST FAIL: status=' + (resp ? resp.status : 'null') + ' url=' + url);
                return null;
            } catch (e) {
                print('>>> aipan POST ERROR: ' + e);
                return null;
            }
        }

        function stripTags(str) {
            if (!str) return '';
            return String(str).replace(/<[^>]+>/g, '').replace(/&amp;/g, '&')
                .replace(/&lt;/g, '<').replace(/&gt;/g, '>').replace(/&quot;/g, '"')
                .replace(/&#39;/g, "'").replace(/&nbsp;/g, ' ').trim();
        }

        function encode(str) {
            return encodeURIComponent(String(str));
        }

        // 从 service 类型获取网盘名称
        function getPanName(service) {
            return SERVICE_MAP[service] || '网盘';
        }

        // 从 URL 推断网盘名称（备用）
        function inferCloudFromUrl(url) {
            if (!url) return '网盘';
            if (url.indexOf('pan.quark.cn') !== -1) return '夸克网盘';
            if (url.indexOf('pan.baidu.com') !== -1) return '百度网盘';
            if (url.indexOf('alipan.com') !== -1 || url.indexOf('aliyundrive.com') !== -1) return '阿里云盘';
            if (url.indexOf('drive.uc.cn') !== -1 || url.indexOf('uc.cn') !== -1) return 'UC网盘';
            if (url.indexOf('115.com') !== -1 || url.indexOf('115cdn.com') !== -1) return '115网盘';
            if (url.indexOf('123pan.com') !== -1 || url.indexOf('123684.com') !== -1 || url.indexOf('123912.com') !== -1) return '123云盘';
            if (url.indexOf('cloud.189.cn') !== -1) return '天翼云盘';
            if (url.indexOf('pan.xunlei.com') !== -1) return '迅雷云盘';
            if (url.indexOf('magnet:') !== -1) return 'BT磁力';
            return '网盘';
        }

        // 判断 URL 是否为直链
        function isDirectUrl(url) {
            if (!url) return false;
            return url.indexOf('http') === 0 || url.indexOf('magnet:') === 0;
        }

        // 编码 vod_id（搜索结果）: {title}|||{url}|||{pan_name}|||{pwd}|||1
        function encodeSearchVodId(title, url, panName, pwd) {
            return title + '|||' + encodeURIComponent(url || '') + '|||' + encodeURIComponent(panName || '网盘') + '|||' + encodeURIComponent(pwd || '') + '|||1';
        }

        // 编码 vod_id（豆瓣结果）: {title}|||douban|||0
        function encodeDoubanVodId(title, cover) {
            return title + '|||douban|||' + encodeURIComponent(cover || '') + '|||0';
        }

        // 解码 vod_id
        function decodeVodId(vodId) {
            var parts = String(vodId).split('|||');
            return {
                title: parts[0] || '',
                urlOrType: parts[1] ? decodeURIComponent(parts[1]) : '',
                panNameOrCover: parts[2] ? decodeURIComponent(parts[2]) : '',
                pwd: parts[3] ? decodeURIComponent(parts[3]) : '',
                isSearch: parts[4] === '1'
            };
        }

        // 构建带提取码的完整网盘链接
        function buildUrlWithPwd(url, pwd) {
            if (!url) return '';
            if (!pwd) return url;
            // 已有查询参数用 & 否则用 ?
            if (url.indexOf('?') !== -1) {
                return url + '&pwd=' + pwd;
            }
            return url + '?pwd=' + pwd;
        }

        // ===================== 搜索源请求 =====================

        // 请求单个搜索源，返回结果列表
        function searchFromSource(apiPath, keyword) {
            var data = postJSON(BASE_URL + apiPath, { name: keyword });
            if (!data || !data.list || !Array.isArray(data.list)) {
                return [];
            }
            return data.list;
        }

        // 合并多个搜索源的结果，按标题+链接去重
        function mergeSearchResults(keyword) {
            var allItems = [];
            var seen = {};

            for (var s = 0; s < SEARCH_SOURCES.length; s++) {
                try {
                    var items = searchFromSource(SEARCH_SOURCES[s], keyword);
                    for (var i = 0; i < items.length; i++) {
                        var item = items[i];
                        var title = stripTags(item.name || '');
                        if (!title) continue;

                        var links = item.links || [];
                        for (var j = 0; j < links.length; j++) {
                            var link = links[j];
                            var url = link.link || '';
                            if (!url || !isDirectUrl(url)) continue;

                            var service = link.service || '';
                            var panName = getPanName(service);
                            if (panName === '网盘') {
                                panName = inferCloudFromUrl(url);
                            }
                            var pwd = link.pwd || '';

                            // 去重：按 title + url
                            var dedupKey = title + '_' + url;
                            if (seen[dedupKey]) continue;
                            seen[dedupKey] = true;

                            allItems.push({
                                title: title,
                                url: url,
                                panName: panName,
                                pwd: pwd,
                                service: service
                            });
                        }
                    }
                } catch (e) {
                    print('>>> aipan searchFromSource ERROR (' + SEARCH_SOURCES[s] + '): ' + e);
                }
            }

            return allItems;
        }

        // ===================== 首页内容 =====================

        function homeContent(filter) {
            var result = { class: [], list: [] };

            // 8 个豆瓣分类
            result.class = [
                { type_id: '0', type_name: '豆瓣热映' },
                { type_id: '1', type_name: '热门电视' },
                { type_id: '2', type_name: '国产剧' },
                { type_id: '3', type_name: '美剧' },
                { type_id: '4', type_name: '日剧' },
                { type_id: '5', type_name: '韩剧' },
                { type_id: '6', type_name: '日本动画' },
                { type_id: '7', type_name: '纪录片' }
            ];

            // 首页推荐：豆瓣热映
            try {
                var data = fetchJSON(BASE_URL + '/api/douban/new');
                if (data && data.data && Array.isArray(data.data) && data.data.length > 0) {
                    var hotItems = data.data[0].data || [];
                    for (var i = 0; i < hotItems.length && i < 24; i++) {
                        var item = hotItems[i];
                        var title = stripTags(item.title || '');
                        if (!title) continue;

                        var remarks = '';
                        if (item.rate && item.rate !== '0' && item.rate !== '') {
                            remarks = ' ⭐' + item.rate;
                        }

                        result.list.push({
                            vod_id: encodeDoubanVodId(title, item.cover || ''),
                            vod_name: title,
                            vod_pic: item.cover || '',
                            vod_remarks: '☁️' + remarks
                        });
                    }
                }
            } catch (e) {
                print('>>> aipan homeContent ERROR: ' + e);
            }

            print('>>> aipan homeContent: list=' + result.list.length);
            return result;
        }

        // ===================== 分类内容 =====================

        function categoryContent(tid, pg, filter, extend) {
            var page = parseInt(pg) || 1;
            var result = { list: [], page: page, pagecount: 1, limit: 24, total: 0 };

            try {
                var catIndex = parseInt(tid) || 0;
                if (catIndex < 0) catIndex = 0;

                var data = fetchJSON(BASE_URL + '/api/douban/new');
                if (!data || !data.data || !Array.isArray(data.data)) {
                    return result;
                }

                if (catIndex >= data.data.length) {
                    return result;
                }

                var catData = data.data[catIndex].data || [];
                result.total = catData.length;

                // 客户端侧分页，每页 24 条
                var pageSize = 24;
                var startIdx = (page - 1) * pageSize;
                var endIdx = Math.min(startIdx + pageSize, catData.length);

                for (var i = startIdx; i < endIdx; i++) {
                    var item = catData[i];
                    var title = stripTags(item.title || '');
                    if (!title) continue;

                    var remarks = '';
                    if (item.rate && item.rate !== '0' && item.rate !== '') {
                        remarks = ' ⭐' + item.rate;
                    }

                    result.list.push({
                        vod_id: encodeDoubanVodId(title, item.cover || ''),
                        vod_name: title,
                        vod_pic: item.cover || '',
                        vod_remarks: '☁️' + remarks
                    });
                }

                result.pagecount = Math.ceil(catData.length / pageSize) || 1;
            } catch (e) {
                print('>>> aipan categoryContent ERROR: ' + e);
            }

            print('>>> aipan categoryContent: tid=' + tid + ' pg=' + page + ' count=' + result.list.length);
            return result;
        }

        // ===================== 搜索内容 =====================

        function searchContent(key, quick, pg) {
            var page = parseInt(pg) || 1;
            var result = { list: [], page: page, pagecount: 1 };

            if (typeof quick === 'number') {
                page = quick;
            }

            if (!key) {
                return result;
            }

            try {
                var allItems = mergeSearchResults(key);

                if (allItems.length === 0) {
                    print('>>> aipan searchContent: no results for key=' + key);
                    return result;
                }

                // 客户端侧分页，每页 20 条
                var pageSize = 20;
                var startIdx = (page - 1) * pageSize;
                var endIdx = Math.min(startIdx + pageSize, allItems.length);

                for (var i = startIdx; i < endIdx; i++) {
                    var item = allItems[i];
                    result.list.push({
                        vod_id: encodeSearchVodId(item.title, item.url, item.panName, item.pwd),
                        vod_name: item.title,
                        vod_pic: '',
                        vod_remarks: '☁️' + item.panName
                    });
                }

                result.pagecount = Math.ceil(allItems.length / pageSize) || 1;
                print('>>> aipan searchContent: key=' + key + ' pg=' + page + ' total=' + allItems.length + ' pageItems=' + result.list.length);
            } catch (e) {
                print('>>> aipan searchContent ERROR: ' + e);
            }

            return result;
        }

        // ===================== 详情内容 =====================

        function detailContent(ids) {
            var result = { list: [] };

            if (!ids) {
                print('>>> aipan detailContent: empty ids');
                return result;
            }

            var id = String(ids);
            var decoded = decodeVodId(id);
            print('>>> aipan detailContent: title=' + decoded.title + ' isSearch=' + decoded.isSearch);

            // 情况1：来自搜索结果，已有网盘直链
            if (decoded.isSearch && decoded.urlOrType && isDirectUrl(decoded.urlOrType)) {
                var realUrl = buildUrlWithPwd(decoded.urlOrType, decoded.pwd);
                var panName = decoded.panNameOrCover || '网盘';

                result.list.push({
                    vod_id: id,
                    vod_name: decoded.title,
                    vod_pic: '',
                    vod_remarks: '☁️' + panName,
                    vod_play_from: '爱盼',
                    vod_play_url: JSON.stringify([{ url: realUrl, name: panName }])
                });
                print('>>> aipan detailContent SUCCESS (search): ' + realUrl.substring(0, 60));
                return result;
            }

            // 情况2：来自豆瓣分类，需要搜索获取网盘链接
            if (!decoded.isSearch && decoded.urlOrType === 'douban' && decoded.title) {
                print('>>> aipan detailContent: searching douban title=' + decoded.title);
                var cover = decoded.panNameOrCover || '';
                var searchItems = mergeSearchResults(decoded.title);

                if (searchItems.length > 0) {
                    // 按网盘类型分组
                    var groups = {};
                    var order = [];
                    for (var i = 0; i < searchItems.length; i++) {
                        var si = searchItems[i];
                        var pn = si.panName;

                        if (!groups[pn]) {
                            groups[pn] = [];
                            order.push(pn);
                        }
                        var url = buildUrlWithPwd(si.url, si.pwd);
                        groups[pn].push({ url: url, name: pn });
                    }

                    // 构建 play_from 和 play_url
                    var playFromParts = [];
                    var playUrlParts = [];
                    for (var j = 0; j < order.length; j++) {
                        var panName = order[j];
                        playFromParts.push(panName);
                        playUrlParts.push(JSON.stringify(groups[panName]));
                    }

                    result.list.push({
                        vod_id: id,
                        vod_name: decoded.title,
                        vod_pic: cover,
                        vod_remarks: '☁️' + order[0],
                        vod_play_from: playFromParts.join('$$$'),
                        vod_play_url: playUrlParts.join('$$$')
                    });
                    print('>>> aipan detailContent: found ' + searchItems.length + ' resources for ' + decoded.title);
                } else {
                    result.list.push({
                        vod_id: id,
                        vod_name: decoded.title,
                        vod_pic: cover,
                        vod_remarks: '☁️网盘',
                        vod_play_from: '爱盼',
                        vod_play_url: JSON.stringify([{ url: '', name: '未找到资源' }])
                    });
                    print('>>> aipan detailContent: no resources found for ' + decoded.title);
                }
                return result;
            }

            // 兜底
            result.list.push({
                vod_id: id,
                vod_name: decoded.title || '网盘资源',
                vod_pic: '',
                vod_remarks: '☁️网盘',
                vod_play_from: '爱盼',
                vod_play_url: JSON.stringify([{ url: '', name: '网盘资源' }])
            });
            return result;
        }

        // ===================== 播放内容 =====================

        function playerContent(vodId, flag, url) {
            print('>>> aipan playerContent: vodId=' + vodId.substring(0, 40));

            // 如果 url 参数本身就是网盘链接
            if (url && isDirectUrl(url)) {
                return {
                    parse: 0,
                    url: url,
                    header: { 'User-Agent': UA }
                };
            }

            // 从 vod_id 解码
            var decoded = decodeVodId(vodId);
            if (decoded.isSearch && decoded.urlOrType && isDirectUrl(decoded.urlOrType)) {
                var realUrl = buildUrlWithPwd(decoded.urlOrType, decoded.pwd);
                return {
                    parse: 0,
                    url: realUrl,
                    header: { 'User-Agent': UA }
                };
            }

            return { parse: 0, url: '' };
        }

        // ===================== 初始化 =====================

        function init(config) {
            print('>>> aipan init: 爱盼 JS蜘蛛 v1.0');
            return true;
        }

        return {
            init: init,
            homeContent: homeContent,
            categoryContent: categoryContent,
            detailContent: detailContent,
            searchContent: searchContent,
            playerContent: playerContent
        };
    }
};
