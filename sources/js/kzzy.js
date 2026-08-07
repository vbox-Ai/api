/*
 * 库库光影 JS 蜘蛛 v1.0
 * 适配 vbox-ios JSSpiderEngine (type:3 独立引擎)
 * 目标站: https://m.kzzy.fun
 * 特点: 网盘资源搜索聚合，支持分类榜单浏览 + SSE 搜索 + 加密URL解码
 * 支持网盘：夸克网盘、百度网盘、迅雷云盘、UC网盘、115网盘、磁力
 * 无需登录，无需加密签名
 *
 * 网盘蜘蛛源约定：
 *   - vod_remarks 以 "☁️" 开头 → 标识为网盘资源，激活网盘UI
 *   - detailContent 的 vod_play_url 返回 JSON 数组 [{"url":"网盘链接","name":"网盘名"}]
 *   - vod_id 编码格式:
 *     搜索结果: {item_title}|||{pan_url_or_token}|||{pan_type_name}|||1
 *     榜单结果: {item_title}|||rank|||{ranking_type}|||0
 */

var spider = {
    __jsEvalReturn: function() {

        var BASE_URL = 'https://m.kzzy.fun';
        var UA = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36';
        var HEADER = {
            'User-Agent': UA,
            'Referer': BASE_URL + '/'
        };

        // 网盘类型映射（API is_type 数字 → 名称）
        var PAN_TYPE_MAP = {
            0: '夸克网盘',
            2: '百度网盘',
            3: 'UC网盘',
            4: '迅雷云盘',
            6: '115网盘',
            9: 'BT磁力',
            10: '光鸭网盘',
            8: '移动网盘'
        };

        // 搜索优先级：夸克 > 百度 > 迅雷（速度快、结果多）
        var SEARCH_TYPES = [0, 2, 4];

        // ===================== 工具函数 =====================

        function fetch(url, headers) {
            try {
                var resp = req(url, { headers: headers || HEADER, timeout: 15000 });
                if (resp && resp.ok) {
                    return resp.content || '';
                }
                print('>>> kzzy fetch FAIL: status=' + (resp ? resp.status : 'null') + ' url=' + url.substring(0, 80));
                return '';
            } catch (e) {
                print('>>> kzzy fetch ERROR: ' + e);
                return '';
            }
        }

        function fetchJSON(url, headers) {
            var html = fetch(url, headers);
            if (!html) return null;
            try {
                return JSON.parse(html);
            } catch (e) {
                print('>>> kzzy JSON parse ERROR: ' + e);
                return null;
            }
        }

        function postForm(url, formData, headers) {
            try {
                var h = {};
                var src = headers || HEADER;
                for (var k in src) { h[k] = src[k]; }
                h['Content-Type'] = 'application/x-www-form-urlencoded';
                var resp = req(url, { method: 'POST', headers: h, body: formData, data: formData, timeout: 10000 });
                if (resp && resp.ok) {
                    var content = resp.content || '';
                    if (typeof content === 'object') return content;
                    try { return JSON.parse(content); } catch (e) { return null; }
                }
                print('>>> kzzy POST FAIL: status=' + (resp ? resp.status : 'null'));
                return null;
            } catch (e) {
                print('>>> kzzy POST ERROR: ' + e);
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

        // 从网盘 URL 推断网盘名称
        function inferCloudFromUrl(url) {
            if (!url) return '网盘';
            if (url.indexOf('pan.quark.cn') !== -1) return '夸克网盘';
            if (url.indexOf('pan.baidu.com') !== -1) return '百度网盘';
            if (url.indexOf('pan.xunlei.com') !== -1) return '迅雷云盘';
            if (url.indexOf('115.com') !== -1) return '115网盘';
            if (url.indexOf('aliyundrive.com') !== -1 || url.indexOf('alipan.com') !== -1) return '阿里云盘';
            if (url.indexOf('uc.cn') !== -1 || url.indexOf('ucloud.cn') !== -1) return 'UC网盘';
            if (url.indexOf('magnet:') !== -1) return 'BT磁力';
            return '网盘';
        }

        // 判断 URL 是否为直链
        function isDirectUrl(url) {
            if (!url) return false;
            return url.indexOf('http') === 0 || url.indexOf('magnet:') === 0;
        }

        // 编码 vod_id（搜索结果）: {title}|||{url_or_token}|||{pan_name}|||1
        function encodeSearchVodId(title, urlOrToken, panName) {
            return title + '|||' + encodeURIComponent(urlOrToken || '') + '|||' + encodeURIComponent(panName || '网盘') + '|||1';
        }

        // 编码 vod_id（榜单结果）: {title}|||rank|||{ranking_type}|||0
        function encodeRankVodId(title, rankingType) {
            return title + '|||rank|||' + rankingType + '|||0';
        }

        // 解码 vod_id
        function decodeVodId(vodId) {
            var parts = String(vodId).split('|||');
            return {
                title: parts[0] || '',
                urlOrToken: parts[1] ? decodeURIComponent(parts[1]) : '',
                panName: parts[2] ? decodeURIComponent(parts[2]) : '',
                isSearch: parts[3] === '1',
                rankingType: parts[2] || ''
            };
        }

        // ===================== SSE 搜索解析 =====================

        // 解析 SSE 格式响应文本，提取搜索结果
        function parseSSEResponse(text) {
            var results = [];
            if (!text) return results;

            var lines = text.split('\n');
            var seen = {}; // 去重

            for (var i = 0; i < lines.length; i++) {
                var line = lines[i].trim();
                if (line.indexOf('data: ') !== 0) continue;
                if (line === 'data: [DONE]') break;

                var jsonStr = line.substring(6);
                try {
                    var item = JSON.parse(jsonStr);
                    var title = stripTags(item.title || '');
                    var url = item.url || '';
                    var isType = item.is_type;

                    if (!title || !url) continue;

                    // 去重（按 title + url）
                    var dedupKey = title + '_' + url;
                    if (seen[dedupKey]) continue;
                    seen[dedupKey] = true;

                    var panName = PAN_TYPE_MAP[isType] || inferCloudFromUrl(url);

                    results.push({
                        title: title,
                        url: url,
                        isType: isType,
                        panName: panName,
                        isDirect: isDirectUrl(url)
                    });
                } catch (e) {
                    // 跳过解析失败的行
                }
            }

            return results;
        }

        // ===================== 加密 URL 解码 =====================

        function decodeUrl(token, title) {
            // 直链直接返回
            if (isDirectUrl(token)) {
                return token;
            }

            var safeTitle = title || 'resource';

            // 策略1: POST 方式调用 save_url
            var formData = 'url=' + encode(token) + '&title=' + encode(safeTitle);
            var data = postForm(BASE_URL + '/api/other/save_url', formData);

            if (data && data.code === 200 && data.data && data.data.url) {
                print('>>> kzzy decodeUrl SUCCESS (POST): ' + data.data.url.substring(0, 60));
                return data.data.url;
            }

            print('>>> kzzy decodeUrl POST result: ' + (data ? data.message : 'null response'));

            // 策略2: GET 方式调用 save_url（兼容性更好，部分 bridge 不支持 POST body）
            var getUrl = BASE_URL + '/api/other/save_url?url=' + encode(token) + '&title=' + encode(safeTitle);
            data = fetchJSON(getUrl);

            if (data && data.code === 200 && data.data && data.data.url) {
                print('>>> kzzy decodeUrl SUCCESS (GET): ' + data.data.url.substring(0, 60));
                return data.data.url;
            }

            print('>>> kzzy decodeUrl GET result: ' + (data ? data.message : 'null response'));
            return '';
        }

        // ===================== 首页内容 =====================

        function homeContent(filter) {
            var result = { class: [], list: [] };

            // 5 个分类
            result.class = [
                { type_id: 'dianying', type_name: '电影' },
                { type_id: 'dianshiju', type_name: '电视剧' },
                { type_id: 'dongman', type_name: '动漫' },
                { type_id: 'zongyi', type_name: '综艺' },
                { type_id: 'duanju', type_name: '短剧' }
            ];

            // 用热播榜数据作为推荐列表
            try {
                var url = BASE_URL + '/api/tool/ranking?type=hot&page=1';
                var data = fetchJSON(url);
                if (data && data.code === 200 && data.data && data.data.data) {
                    var items = data.data.data;
                    for (var i = 0; i < items.length; i++) {
                        var item = items[i];
                        var title = stripTags(item.title || '');
                        if (!title) continue;

                        var remarks = item.year || '';
                        if (item.score_avg && item.score_avg !== '0.0') {
                            remarks += ' ⭐' + item.score_avg;
                        }

                        result.list.push({
                            vod_id: encodeRankVodId(title, 'hot'),
                            vod_name: title,
                            vod_pic: item.src || '',
                            vod_remarks: '☁️' + remarks
                        });
                    }
                }
            } catch (e) {
                print('>>> kzzy homeContent ERROR: ' + e);
            }

            print('>>> kzzy homeContent: list=' + result.list.length);
            return result;
        }

        // ===================== 分类内容 =====================

        function categoryContent(tid, pg, filter, extend) {
            var page = parseInt(pg) || 1;
            var result = { list: [], page: page, pagecount: 1, limit: 24, total: 0 };

            try {
                // 排行榜类型映射
                var rankingTypes = ['hot', 'new', 'good'];
                var rankingType = rankingTypes[(page - 1) % 3] || 'hot';

                var url = BASE_URL + '/api/tool/ranking?type=' + rankingType + '&page=1';
                var data = fetchJSON(url);

                if (data && data.code === 200 && data.data && data.data.data) {
                    var items = data.data.data;
                    result.total = items.length;

                    // 分页：每页 8 条
                    var pageSize = 8;
                    var startIdx = ((page - 1) * pageSize) % items.length;
                    var count = Math.min(pageSize, items.length);

                    for (var i = 0; i < count; i++) {
                        var idx = (startIdx + i) % items.length;
                        var item = items[idx];
                        var title = stripTags(item.title || '');
                        if (!title) continue;

                        var remarks = item.year || '';
                        if (item.score_avg && item.score_avg !== '0.0') {
                            remarks += ' ⭐' + item.score_avg;
                        }

                        result.list.push({
                            vod_id: encodeRankVodId(title, rankingType),
                            vod_name: title,
                            vod_pic: item.src || '',
                            vod_remarks: '☁️' + remarks
                        });
                    }

                    // 循环分页，最多 3 页
                    result.pagecount = 3;
                }
            } catch (e) {
                print('>>> kzzy categoryContent ERROR: ' + e);
            }

            print('>>> kzzy categoryContent: tid=' + tid + ' pg=' + page + ' count=' + result.list.length);
            return result;
        }

        // ===================== 搜索内容 =====================

        function searchContent(key, quick, pg) {
            var page = parseInt(pg) || 1;
            var result = { list: [], page: page, pagecount: 1 };

            if (typeof quick === 'number') {
                page = quick;
            }

            try {
                // 先查本地缓存
                var checkUrl = BASE_URL + '/api/other/local_search_check?title=' + encode(key);
                var checkData = fetchJSON(checkUrl);

                if (checkData && checkData.code === 200 && checkData.data && checkData.data.hasData) {
                    // 有本地缓存，直接用缓存结果
                    var cachedItems = checkData.data.items || [];
                    for (var i = 0; i < cachedItems.length; i++) {
                        var ci = cachedItems[i];
                        var cTitle = stripTags(ci.title || '');
                        var cUrl = ci.url || '';
                        if (!cTitle || !cUrl) continue;

                        var cPanName = PAN_TYPE_MAP[ci.is_type] || inferCloudFromUrl(cUrl);
                        var cIsDirect = isDirectUrl(cUrl);

                        result.list.push({
                            vod_id: encodeSearchVodId(cTitle, cUrl, cPanName),
                            vod_name: cTitle,
                            vod_pic: '',
                            vod_remarks: '☁️' + cPanName
                        });
                    }
                    print('>>> kzzy searchContent: local cache count=' + result.list.length);
                    if (result.list.length > 0) return result;
                }

                // 无缓存，走 SSE 搜索（搜夸克网盘，速度快结果多）
                var sseUrl = BASE_URL + '/api/other/web_search?title=' + encode(key) + '&is_type=0';
                var sseText = fetch(sseUrl);
                var sseResults = parseSSEResponse(sseText);

                for (var j = 0; j < sseResults.length; j++) {
                    var sr = sseResults[j];
                    result.list.push({
                        vod_id: encodeSearchVodId(sr.title, sr.url, sr.panName),
                        vod_name: sr.title,
                        vod_pic: '',
                        vod_remarks: '☁️' + sr.panName
                    });
                }

                // 如果夸克没结果，再搜百度
                if (result.list.length === 0) {
                    var baiduUrl = BASE_URL + '/api/other/web_search?title=' + encode(key) + '&is_type=2';
                    var baiduText = fetch(baiduUrl);
                    var baiduResults = parseSSEResponse(baiduText);

                    for (var k = 0; k < baiduResults.length; k++) {
                        var br = baiduResults[k];
                        result.list.push({
                            vod_id: encodeSearchVodId(br.title, br.url, br.panName),
                            vod_name: br.title,
                            vod_pic: '',
                            vod_remarks: '☁️' + br.panName
                        });
                    }
                }

                result.pagecount = 1;
                print('>>> kzzy searchContent: key=' + key + ' count=' + result.list.length);
            } catch (e) {
                print('>>> kzzy searchContent ERROR: ' + e);
            }

            return result;
        }

        // ===================== 详情内容 =====================

        function detailContent(ids) {
            var result = { list: [] };

            if (!ids) {
                print('>>> kzzy detailContent: empty ids');
                return result;
            }

            var id = String(ids);
            var decoded = decodeVodId(id);
            print('>>> kzzy detailContent: title=' + decoded.title + ' isSearch=' + decoded.isSearch);

            // 情况1：来自搜索结果，有 URL 或 token
            if (decoded.isSearch && decoded.urlOrToken) {
                var realUrl = decoded.urlOrToken;

                // 如果是 token，需要解码
                if (!isDirectUrl(realUrl)) {
                    realUrl = decodeUrl(realUrl, decoded.title);
                }

                if (realUrl) {
                    result.list.push({
                        vod_id: id,
                        vod_name: decoded.title,
                        vod_pic: '',
                        vod_remarks: '☁️' + decoded.panName,
                        vod_play_from: '库库光影',
                        vod_play_url: JSON.stringify([{ url: realUrl, name: decoded.panName }])
                    });
                    print('>>> kzzy detailContent SUCCESS: ' + realUrl.substring(0, 60));
                } else {
                    result.list.push({
                        vod_id: id,
                        vod_name: decoded.title,
                        vod_pic: '',
                        vod_remarks: '☁️网盘',
                        vod_play_from: '库库光影',
                        vod_play_url: JSON.stringify([{ url: '', name: decoded.panName || '网盘资源' }])
                    });
                }
                return result;
            }

            // 情况2：来自榜单，需要搜索标题获取网盘链接
            if (!decoded.isSearch && decoded.title) {
                print('>>> kzzy detailContent: searching for rank title=' + decoded.title);
                var searchResults = doSearchForDetail(decoded.title);

                if (searchResults && searchResults.length > 0) {
                    // 按网盘类型分组
                    var groups = {};
                    var order = [];
                    for (var i = 0; i < searchResults.length; i++) {
                        var sr = searchResults[i];
                        var panName = sr.panName;

                        if (!groups[panName]) {
                            groups[panName] = [];
                            order.push(panName);
                        }
                        groups[panName].push({ url: sr.realUrl, name: panName });
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
                        vod_pic: '',
                        vod_remarks: '☁️' + order[0],
                        vod_play_from: playFromParts.join('$$$'),
                        vod_play_url: playUrlParts.join('$$$')
                    });
                    print('>>> kzzy detailContent: found ' + searchResults.length + ' resources for ' + decoded.title);
                } else {
                    // 搜索不到，返回占位
                    result.list.push({
                        vod_id: id,
                        vod_name: decoded.title,
                        vod_pic: '',
                        vod_remarks: '☁️网盘',
                        vod_play_from: '库库光影',
                        vod_play_url: JSON.stringify([{ url: '', name: '未找到资源' }])
                    });
                    print('>>> kzzy detailContent: no resources found for ' + decoded.title);
                }
                return result;
            }

            // 兜底
            result.list.push({
                vod_id: id,
                vod_name: decoded.title || '网盘资源',
                vod_pic: '',
                vod_remarks: '☁️网盘',
                vod_play_from: '库库光影',
                vod_play_url: JSON.stringify([{ url: '', name: '网盘资源' }])
            });
            return result;
        }

        // 详情页内部搜索：搜索多个网盘类型并解码
        function doSearchForDetail(title) {
            var allResults = [];

            for (var t = 0; t < SEARCH_TYPES.length; t++) {
                var isType = SEARCH_TYPES[t];
                var sseUrl = BASE_URL + '/api/other/web_search?title=' + encode(title) + '&is_type=' + isType;
                var sseText = fetch(sseUrl);
                var parsed = parseSSEResponse(sseText);

                for (var i = 0; i < parsed.length; i++) {
                    var item = parsed[i];
                    var realUrl = item.url;

                    // token 需要解码
                    if (!item.isDirect) {
                        realUrl = decodeUrl(item.url, item.title);
                    }

                    if (realUrl) {
                        allResults.push({
                            title: item.title,
                            realUrl: realUrl,
                            panName: item.panName
                        });
                    }
                }

                // 找到足够结果就停止
                if (allResults.length >= 5) break;
            }

            return allResults;
        }

        // ===================== 播放内容 =====================

        function playerContent(vodId, flag, url) {
            print('>>> kzzy playerContent: vodId=' + vodId.substring(0, 40));

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
            if (decoded.isSearch && decoded.urlOrToken) {
                var realUrl = decoded.urlOrToken;
                if (!isDirectUrl(realUrl)) {
                    realUrl = decodeUrl(realUrl, decoded.title);
                }
                if (realUrl) {
                    return {
                        parse: 0,
                        url: realUrl,
                        header: { 'User-Agent': UA }
                    };
                }
            }

            return { parse: 0, url: '' };
        }

        // ===================== 初始化 =====================

        function init(config) {
            print('>>> kzzy init: 库库光影 JS蜘蛛 v1.0');
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
