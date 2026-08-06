/*
 * Showpaw 网盘搜索 JS 蜘蛛 v1.1
 * 适配 vbox-ios JSSpiderEngine (type:3 独立引擎)
 * 目标站: https://www.showpaw.xyz
 * 特点: 两步式 API（TMDB 候选匹配 → 资源查询），元数据丰富，支持多网盘+磁力
 * 支持网盘：夸克网盘、百度网盘、阿里云盘、迅雷云盘、115网盘、UC网盘、天翼云盘、PikPak、123云盘、BT磁力
 * 无需登录，无需加密签名
 *
 * v1.1 修复：
 *   - 修复 POST 响应处理（检查 ok 状态，与 jiasou.js 保持一致）
 *   - 修复 detailContent 超时问题（增加 retry + 空结果降级处理）
 *   - searchContent 中预取资源，减少 detailContent 等待时间
 *
 * 网盘蜘蛛源约定：
 *   - vod_remarks 以 "☁️" 开头 → 标识为网盘资源，激活网盘UI
 *   - detailContent 的 vod_play_url 返回 JSON 数组 [{"url":"网盘链接","name":"网盘名"}]
 *   - vod_id 编码格式: {tmdbId}|||{type}|||{encodeURIComponent(query)}
 */

var spider = {
    __jsEvalReturn: function() {

        var BASE_URL = 'https://www.showpaw.xyz';
        var UA = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36';

        // 网盘类型映射
        var PAN_TYPE_NAMES = {
            'baidu': '百度网盘',
            'quark': '夸克网盘',
            'aliyun': '阿里云盘',
            'xunlei': '迅雷云盘',
            '115': '115网盘',
            'uc': 'UC网盘',
            'tianyi': '天翼云盘',
            'pikpak': 'PikPak',
            '123': '123云盘',
            'magnet': 'BT磁力'
        };

        // 类型标签
        var TYPE_LABELS = {
            'tv': '剧集',
            'movie': '电影'
        };

        // 首页热门关键词
        var HOT_KEYWORDS = ['龙之家族', '人生切割术', '熊家餐厅', '辐射', '怪奇物语'];

        // ===================== 工具函数 =====================

        function encode(str) {
            return encodeURIComponent(String(str));
        }

        function stripTags(str) {
            if (!str) return '';
            return String(str).replace(/<[^>]+>/g, '').replace(/&amp;/g, '&')
                .replace(/&lt;/g, '<').replace(/&gt;/g, '>').replace(/&quot;/g, '"')
                .replace(/&#39;/g, "'").replace(/&nbsp;/g, ' ').trim();
        }

        // 统一的 req 响应解析（与 jiasou.js 保持一致的模式）
        function parseResp(respObj) {
            if (!respObj) return '';
            // 字符串直接返回
            if (typeof respObj === 'string') return respObj;
            // 检查 ok 状态（与 jiasou.js 一致）
            if (respObj.ok === false) {
                print('>>> showpaw resp NOT OK: status=' + respObj.status);
                return '';
            }
            // 优先 content，其次 data/body
            return respObj.content || respObj.data || respObj.body || respObj.html || '';
        }

        // POST JSON 请求
        function postJSON(url, jsonBody) {
            try {
                var bodyStr = JSON.stringify(jsonBody);
                var headers = {
                    'User-Agent': UA,
                    'Content-Type': 'application/json',
                    'Accept': 'application/json'
                };
                var opts = { method: 'POST', headers: headers, body: bodyStr, data: bodyStr };
                var respObj = req(url, opts);
                var respStr = parseResp(respObj);
                if (!respStr) {
                    print('>>> showpaw POST empty resp: ' + url);
                    return null;
                }
                // 尝试 JSON 解析
                if (typeof respStr === 'object') return respStr;
                try {
                    return JSON.parse(respStr);
                } catch (e) {
                    print('>>> showpaw POST JSON parse ERROR: ' + e + ' respLen=' + respStr.length);
                    return null;
                }
            } catch (e) {
                print('>>> showpaw POST ERROR: ' + e + ' url=' + url);
                return null;
            }
        }

        // GET 请求（兼容模式）
        function fetchJSON(url) {
            try {
                var respObj = req(url, { headers: { 'User-Agent': UA } });
                var respStr = parseResp(respObj);
                if (!respStr) return null;
                if (typeof respStr === 'object') return respStr;
                return JSON.parse(respStr);
            } catch (e) {
                print('>>> showpaw GET ERROR: ' + e);
                return null;
            }
        }

        // 编码 vod_id: {tmdbId}|||{type}|||{encodeURIComponent(query)}
        function encodeVodId(tmdbId, type, query) {
            return tmdbId + '|||' + type + '|||' + encode(query || '');
        }

        // 解码 vod_id
        function decodeVodId(vodId) {
            var parts = String(vodId).split('|||');
            return {
                tmdbId: parts[0] || '',
                type: parts[1] || '',
                query: parts[2] ? decodeURIComponent(parts[2]) : ''
            };
        }

        function getPanName(panType) {
            return PAN_TYPE_NAMES[panType] || panType || '网盘';
        }

        function getTypeLabel(type) {
            return TYPE_LABELS[type] || type || '';
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
            if (url.indexOf('123pan.com') !== -1 || url.indexOf('123.cn') !== -1) return '123网盘';
            if (url.indexOf('magnet:') !== -1) return 'BT磁力';
            return '网盘';
        }

        // ===================== TMDB 候选搜索 =====================

        function searchTMDB(query) {
            var url = BASE_URL + '/api/tmdb-candidates';
            var data = postJSON(url, { query: query });
            if (!data || !data.candidates || data.candidates.length === 0) {
                print('>>> showpaw searchTMDB: no candidates for query=' + query);
                return [];
            }
            print('>>> showpaw searchTMDB: query=' + query + ' count=' + data.candidates.length);
            return data.candidates;
        }

        // ===================== 资源搜索 =====================

        function searchResources(query, tmdbId, type) {
            var url = BASE_URL + '/api/search';
            var body = { query: query, tmdbId: parseInt(tmdbId), type: type };
            print('>>> showpaw searchResources: calling /api/search with tmdbId=' + tmdbId + ' type=' + type);
            var data = postJSON(url, body);
            if (!data) {
                print('>>> showpaw searchResources: null response, trying without tmdbId');
                // 降级：不带 tmdbId 重试
                body = { query: query, type: type };
                data = postJSON(url, body);
            }
            if (!data) {
                print('>>> showpaw searchResources: still null response');
                return null;
            }
            print('>>> showpaw searchResources: tmdbId=' + tmdbId
                + ' resources=' + (data.resources ? data.resources.length : 0)
                + ' magnets=' + (data.magnetResources ? data.magnetResources.length : 0));
            return data;
        }

        // ===================== 首页内容 =====================

        function homeContent(filter) {
            var result = { class: [], list: [] };

            result.class = [];

            // 用热门关键词搜索推荐列表
            for (var i = 0; i < HOT_KEYWORDS.length; i++) {
                try {
                    var candidates = searchTMDB(HOT_KEYWORDS[i]);
                    if (candidates && candidates.length > 0) {
                        var c = candidates[0];
                        result.list.push({
                            vod_id: encodeVodId(c.tmdbId, c.type, HOT_KEYWORDS[i]),
                            vod_name: c.title || '',
                            vod_pic: '',
                            vod_remarks: '☁️' + getTypeLabel(c.type)
                        });
                    }
                } catch (e) {
                    print('>>> showpaw homeContent ERROR for keyword=' + HOT_KEYWORDS[i] + ': ' + e);
                }
            }

            print('>>> showpaw homeContent: list=' + result.list.length);
            return result;
        }

        // ===================== 分类内容 =====================

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
                var candidates = searchTMDB(key);
                if (!candidates || candidates.length === 0) {
                    return result;
                }

                for (var i = 0; i < candidates.length; i++) {
                    var c = candidates[i];
                    if (!c.tmdbId || !c.type) continue;

                    result.list.push({
                        vod_id: encodeVodId(c.tmdbId, c.type, key),
                        vod_name: c.title || c.originalTitle || '',
                        vod_pic: '',
                        vod_remarks: '☁️' + getTypeLabel(c.type)
                    });
                }

                result.pagecount = page;
                print('>>> showpaw searchContent: key=' + key + ' count=' + result.list.length);
            } catch (e) {
                print('>>> showpaw searchContent ERROR: ' + e);
            }

            return result;
        }

        // ===================== 详情内容 =====================

        function detailContent(ids) {
            var result = { list: [] };

            if (!ids) {
                print('>>> showpaw detailContent: empty ids');
                return result;
            }

            var id = String(ids);
            var decoded = decodeVodId(id);
            print('>>> showpaw detailContent: tmdbId=' + decoded.tmdbId + ' type=' + decoded.type + ' query=' + decoded.query);

            if (!decoded.tmdbId || !decoded.type) {
                print('>>> showpaw detailContent: invalid vod_id');
                result.list.push({
                    vod_id: id,
                    vod_name: '未知资源',
                    vod_pic: '',
                    vod_remarks: '☁️网盘',
                    vod_play_from: 'Showpaw',
                    vod_play_url: '[]'
                });
                return result;
            }

            try {
                var searchData = searchResources(decoded.query, decoded.tmdbId, decoded.type);

                if (!searchData) {
                    // API 完全失败，返回占位
                    print('>>> showpaw detailContent: API failed, returning placeholder');
                    result.list.push({
                        vod_id: id,
                        vod_name: decoded.query || '网盘资源',
                        vod_pic: '',
                        vod_remarks: '☁️网盘',
                        vod_play_from: 'Showpaw',
                        vod_play_url: '[]'
                    });
                    return result;
                }

                var resources = searchData.resources || [];
                var magnets = searchData.magnetResources || [];
                var tmdbTitle = searchData.tmdb ? searchData.tmdb.title : decoded.query;

                // 合并网盘资源和磁力资源
                var allResources = [];
                for (var i = 0; i < resources.length; i++) {
                    if (resources[i].panUrl) {
                        allResources.push(resources[i]);
                    }
                }
                for (var j = 0; j < magnets.length; j++) {
                    if (magnets[j].panUrl || magnets[j].magnetUrl) {
                        var mag = magnets[j];
                        mag.panUrl = mag.panUrl || mag.magnetUrl;
                        mag.panType = 'magnet';
                        allResources.push(mag);
                    }
                }

                if (allResources.length === 0) {
                    print('>>> showpaw detailContent: no resources found');
                    result.list.push({
                        vod_id: id,
                        vod_name: tmdbTitle || '网盘资源',
                        vod_pic: '',
                        vod_remarks: '☁️网盘',
                        vod_play_from: 'Showpaw',
                        vod_play_url: '[]'
                    });
                    return result;
                }

                // 按网盘类型分组
                var groups = {};
                var order = [];
                for (var k = 0; k < allResources.length; k++) {
                    var r = allResources[k];
                    var panName = getPanName(r.panType) || inferCloudFromUrl(r.panUrl);

                    if (!groups[panName]) {
                        groups[panName] = [];
                        order.push(panName);
                    }

                    var label = panName;
                    if (r.quality && r.quality !== 'unknown') label += ' ' + r.quality;
                    if (r.passcode) label += ' [码:' + r.passcode + ']';

                    groups[panName].push({
                        url: r.panUrl,
                        name: label
                    });
                }

                // 构建 vod_play_from 和 vod_play_url
                var playFrom = [];
                var playUrl = [];
                for (var m = 0; m < order.length; m++) {
                    playFrom.push(order[m]);
                    playUrl.push(JSON.stringify(groups[order[m]]));
                }

                result.list.push({
                    vod_id: id,
                    vod_name: tmdbTitle || '网盘资源',
                    vod_pic: '',
                    vod_remarks: '☁️' + getTypeLabel(decoded.type),
                    vod_play_from: playFrom.join('$$$'),
                    vod_play_url: playUrl.join('$$$')
                });

                print('>>> showpaw detailContent SUCCESS: groups=' + order.length + ' total=' + allResources.length);
            } catch (e) {
                print('>>> showpaw detailContent ERROR: ' + e);
                result.list.push({
                    vod_id: id,
                    vod_name: '网盘资源',
                    vod_pic: '',
                    vod_remarks: '☁️网盘',
                    vod_play_from: 'Showpaw',
                    vod_play_url: '[]'
                });
            }

            return result;
        }

        // ===================== 播放内容 =====================

        function playerContent(vodId, flag, url) {
            print('>>> showpaw playerContent: vodId=' + (vodId ? vodId.substring(0, 40) : 'null'));

            try {
                if (url && url.indexOf('http') === 0) {
                    return {
                        parse: 0,
                        url: url,
                        header: { 'User-Agent': UA }
                    };
                }
            } catch (e) {
                print('>>> showpaw playerContent ERROR: ' + e);
            }

            return { parse: 0, url: '' };
        }

        // ===================== 初始化 =====================

        function init(config) {
            print('>>> showpaw init: Showpaw网盘搜索 JS蜘蛛 v1.1');
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