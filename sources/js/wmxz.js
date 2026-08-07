/*
 * 无名小站 JS 蜘蛛 v1.0
 * 适配 vbox-ios JSSpiderEngine (type:3 独立引擎)
 * 目标站: https://wmxz.click
 * 特点: SSE 流式网盘搜索，加密 URL 需服务端解码，支持多种网盘
 * 支持网盘：夸克网盘、百度网盘、UC网盘、迅雷云盘、115网盘、光鸭网盘、移动网盘、BT磁力
 * 无需登录，无需加密签名
 *
 * 网盘蜘蛛源约定：
 *   - vod_remarks 以 "☁️" 开头 → 标识为网盘资源，激活网盘UI
 *   - detailContent 的 vod_play_url 返回 JSON 数组 [{"url":"网盘链接","name":"网盘名"}]
 *   - vod_id 编码格式: {title}|||{url_or_token}|||{pan_type_name}|||{is_token}
 */

var spider = {
    __jsEvalReturn: function() {

        var BASE_URL = 'https://wmxz.click';
        var UA = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36';
        var HEADER = {
            'User-Agent': UA,
            'Referer': BASE_URL + '/',
            'Accept': 'text/event-stream'
        };

        // 网盘类型映射（API is_type 数字 → 名称）
        var PAN_TYPE_MAP = {
            0: '夸克网盘',
            2: '百度网盘',
            3: 'UC网盘',
            4: '迅雷云盘',
            6: '115网盘',
            8: '移动网盘',
            9: 'BT磁力',
            10: '光鸭网盘'
        };

        // 搜索优先级：夸克 > 百度 > 迅雷（速度快、结果多）
        var SEARCH_TYPES = [0, 2, 4];

        // ===================== 工具函数 =====================

        function fetch(url, headers, opts) {
            try {
                var options = opts || {};
                options.headers = headers || HEADER;
                options.timeout = options.timeout || 20000;
                var resp = req(url, options);
                if (resp && resp.ok) {
                    return resp.content || '';
                }
                print('>>> wmxz fetch FAIL: status=' + (resp ? resp.status : 'null') + ' url=' + url.substring(0, 80));
                return '';
            } catch (e) {
                print('>>> wmxz fetch ERROR: ' + e);
                return '';
            }
        }

        function fetchJSON(url, headers) {
            var html = fetch(url, headers);
            if (!html) return null;
            try {
                return JSON.parse(html);
            } catch (e) {
                print('>>> wmxz JSON parse ERROR: ' + e);
                return null;
            }
        }

        function postForm(url, formData, headers) {
            try {
                var h = {};
                for (var k in (headers || HEADER)) { h[k] = HEADER[k]; }
                h['Content-Type'] = 'application/x-www-form-urlencoded';
                var resp = req(url, { method: 'POST', headers: h, body: formData, data: formData, timeout: 10000 });
                if (resp && resp.ok) {
                    var content = resp.content || '';
                    if (typeof content === 'object') return content;
                    try { return JSON.parse(content); } catch (e) { return null; }
                }
                print('>>> wmxz POST FAIL: status=' + (resp ? resp.status : 'null'));
                return null;
            } catch (e) {
                print('>>> wmxz POST ERROR: ' + e);
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

        function inferCloudFromUrl(url) {
            if (!url) return '网盘';
            if (url.indexOf('pan.quark.cn') !== -1) return '夸克网盘';
            if (url.indexOf('pan.baidu.com') !== -1) return '百度网盘';
            if (url.indexOf('pan.xunlei.com') !== -1) return '迅雷云盘';
            if (url.indexOf('115.com') !== -1) return '115网盘';
            if (url.indexOf('aliyundrive.com') !== -1 || url.indexOf('alipan.com') !== -1) return '阿里云盘';
            if (url.indexOf('drive.uc.cn') !== -1 || url.indexOf('uc.cn') !== -1) return 'UC网盘';
            if (url.indexOf('magnet:') !== -1) return 'BT磁力';
            return '网盘';
        }

        function isDirectUrl(url) {
            if (!url) return false;
            return url.indexOf('http') === 0 || url.indexOf('magnet:') === 0;
        }

        function encodeVodId(title, urlOrToken, panTypeName, isToken) {
            return encodeURIComponent(title || '') + '|||' + encodeURIComponent(urlOrToken || '') + '|||' + encodeURIComponent(panTypeName || '网盘') + '|||' + (isToken ? '1' : '0');
        }

        function decodeVodId(vodId) {
            var parts = String(vodId).split('|||');
            return {
                title: parts[0] ? decodeURIComponent(parts[0]) : '',
                urlOrToken: parts[1] ? decodeURIComponent(parts[1]) : '',
                panTypeName: parts[2] ? decodeURIComponent(parts[2]) : '网盘',
                isToken: parts[3] === '1'
            };
        }

        // 解析 SSE 格式响应文本，提取搜索结果
        function parseSSEResponse(text) {
            var results = [];
            if (!text) return results;

            var lines = text.split('\n');
            var seen = {};

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

        // 加密 URL 解码
        function decodeUrl(token, title) {
            if (isDirectUrl(token)) {
                return token;
            }

            var formData = 'url=' + encode(token) + '&title=' + encode(title || 'resource');
            var data = postForm(BASE_URL + '/api/other/save_url', formData);

            if (data && data.code === 200 && data.data && data.data.url) {
                print('>>> wmxz decodeUrl SUCCESS: ' + data.data.url.substring(0, 60));
                return data.data.url;
            }

            print('>>> wmxz decodeUrl FAIL: ' + (data ? data.message : 'null response'));
            return '';
        }

        // ===================== 首页内容 =====================

        function homeContent(filter) {
            var result = { class: [], list: [] };
            var hotKeywords = ['庆余年', '凡人修仙传', '九门', '斩神', '完美世界'];

            try {
                var url = BASE_URL + '/api/other/local_search_check?title=' + encode(hotKeywords[0]);
                var checkData = fetchJSON(url);

                if (checkData && checkData.code === 200 && checkData.data && checkData.data.hasData && checkData.data.items) {
                    var items = checkData.data.items;
                    for (var i = 0; i < items.length && i < 24; i++) {
                        var item = items[i];
                        var title = stripTags(item.title || '');
                        var url = item.url || '';
                        if (!title || !url) continue;

                        var panName = PAN_TYPE_MAP[item.is_type] || inferCloudFromUrl(url);
                        list.push({
                            vod_id: encodeVodId(title, url, panName, !isDirectUrl(url)),
                            vod_name: title,
                            vod_pic: '',
                            vod_remarks: '☁️' + panName
                        });
                    }
                }

                if (result.list.length === 0) {
                    var sseUrl = BASE_URL + '/api/other/web_search?title=' + encode(hotKeywords[0]) + '&is_type=0';
                    var sseText = fetch(sseUrl);
                    var sseResults = parseSSEResponse(sseText);
                    for (var j = 0; j < sseResults.length && j < 24; j++) {
                        var sr = sseResults[j];
                        result.list.push({
                            vod_id: encodeVodId(sr.title, sr.url, sr.panName, !sr.isDirect),
                            vod_name: sr.title,
                            vod_pic: '',
                            vod_remarks: '☁️' + sr.panName
                        });
                    }
                }
            } catch (e) {
                print('>>> wmxz homeContent ERROR: ' + e);
            }

            return result;
        }

        // ===================== 分类内容 =====================
        // 不支持分类浏览

        function categoryContent(tid, pg, filter, extend) {
            return { list: [], page: 1, pagecount: 0, limit: 20, total: 0 };
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

                if (checkData && checkData.code === 200 && checkData.data && checkData.data.hasData && checkData.data.items) {
                    var cachedItems = checkData.data.items || [];
                    for (var i = 0; i < cachedItems.length; i++) {
                        var ci = cachedItems[i];
                        var cTitle = stripTags(ci.title || '');
                        var cUrl = ci.url || '';
                        if (!cTitle || !cUrl) continue;

                        var cPanName = PAN_TYPE_MAP[ci.is_type] || inferCloudFromUrl(cUrl);
                        result.list.push({
                            vod_id: encodeVodId(cTitle, cUrl, cPanName, !isDirectUrl(cUrl)),
                            vod_name: cTitle,
                            vod_pic: '',
                            vod_remarks: '☁️' + cPanName
                        });
                    }
                    print('>>> wmxz searchContent: local cache count=' + result.list.length);
                    if (result.list.length > 0) return result;
                }

                // 无缓存，走 SSE 搜索（优先夸克）
                for (var t = 0; t < SEARCH_TYPES.length && result.list.length === 0; t++) {
                    var isType = SEARCH_TYPES[t];
                    var sseUrl = BASE_URL + '/api/other/web_search?title=' + encode(key) + '&is_type=' + isType;
                    var sseText = fetch(sseUrl);
                    var sseResults = parseSSEResponse(sseText);

                    for (var j = 0; j < sseResults.length; j++) {
                        var sr = sseResults[j];
                        result.list.push({
                            vod_id: encodeVodId(sr.title, sr.url, sr.panName, !sr.isDirect),
                            vod_name: sr.title,
                            vod_pic: '',
                            vod_remarks: '☁️' + sr.panName
                        });
                    }
                }

                result.pagecount = 1;
                print('>>> wmxz searchContent: key=' + key + ' count=' + result.list.length);
            } catch (e) {
                print('>>> wmxz searchContent ERROR: ' + e);
            }

            return result;
        }

        // ===================== 详情内容 =====================

        function detailContent(ids) {
            var result = { list: [] };

            if (!ids) {
                print('>>> wmxz detailContent: empty ids');
                return result;
            }

            var id = String(ids);
            var decoded = decodeVodId(id);
            print('>>> wmxz detailContent: title=' + decoded.title);

            if (decoded.urlOrToken) {
                var realUrl = decoded.urlOrToken;
                if (!isDirectUrl(realUrl)) {
                    realUrl = decodeUrl(realUrl, decoded.title);
                }

                if (realUrl) {
                    result.list.push({
                        vod_id: id,
                        vod_name: decoded.title || '网盘资源',
                        vod_pic: '',
                        vod_remarks: '☁️' + decoded.panTypeName,
                        vod_play_from: '无名小站',
                        vod_play_url: JSON.stringify([{ url: realUrl, name: decoded.panTypeName }])
                    });
                    print('>>> wmxz detailContent SUCCESS: ' + realUrl.substring(0, 60));
                } else {
                    result.list.push({
                        vod_id: id,
                        vod_name: decoded.title || '网盘资源',
                        vod_pic: '',
                        vod_remarks: '☁️网盘',
                        vod_play_from: '无名小站',
                        vod_play_url: JSON.stringify([{ url: '', name: '解码失败' }])
                    });
                }
            } else {
                result.list.push({
                    vod_id: id,
                    vod_name: decoded.title || '网盘资源',
                    vod_pic: '',
                    vod_remarks: '☁️网盘',
                    vod_play_from: '无名小站',
                    vod_play_url: JSON.stringify([{ url: '', name: '无链接' }])
                });
            }

            return result;
        }

        // ===================== 播放内容 =====================

        function playerContent(vodId, flag, url) {
            print('>>> wmxz playerContent: vodId=' + vodId.substring(0, 40));

            if (url && isDirectUrl(url)) {
                return {
                    parse: 0,
                    url: url,
                    header: { 'User-Agent': UA }
                };
            }

            var decoded = decodeVodId(vodId);
            if (decoded.urlOrToken) {
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
            print('>>> wmxz init: 无名小站 JS蜘蛛 v1.0');
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
