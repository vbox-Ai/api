/*
 * 奇点搜索 JS 蜘蛛 v1.0
 * 适配 vbox-ios JSSpiderEngine (type:3 独立引擎)
 * 目标站: https://duanjutv.top
 * 特点: 网盘资源全文检索，API 一步返回直链（无需二次解析）
 * 支持网盘：夸克网盘、百度网盘、UC网盘
 * 无需登录，无需加密签名
 *
 * 网盘蜘蛛源约定：
 *   - vod_remarks 以 "☁️" 开头 → 标识为网盘资源，激活网盘UI
 *   - detailContent 的 vod_play_url 返回 JSON 数组 [{"url":"网盘链接","name":"网盘名"}]
 *   - vod_id 编码格式: {item_id}|||{pan_url}|||{pan_type_name}
 */

var spider = {
    __jsEvalReturn: function() {

        var BASE_URL = 'https://duanjutv.top';
        var UA = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36';
        var HEADER = { 'User-Agent': UA };

        // 网盘类型映射（API is_type 数字 → 名称）
        var PAN_TYPE_MAP = {
            0: '夸克网盘',
            2: '百度网盘',
            3: 'UC网盘'
        };

        // 首页推荐搜索关键词
        var HOT_KEYWORDS = ['庆余年', '凡人修仙传', '斗破苍穹', '仙逆', '完美世界'];

        // ===================== 工具函数 =====================

        function fetch(url, headers) {
            try {
                var resp = req(url, { headers: headers || HEADER });
                if (resp && resp.ok) {
                    return resp.content || '';
                }
                print('>>> duanjutv fetch FAIL: status=' + (resp ? resp.status : 'null') + ' url=' + url.substring(0, 80));
                return '';
            } catch (e) {
                print('>>> duanjutv fetch ERROR: ' + e);
                return '';
            }
        }

        function fetchJSON(url, headers) {
            var html = fetch(url, headers);
            if (!html) return null;
            try {
                return JSON.parse(html);
            } catch (e) {
                print('>>> duanjutv JSON parse ERROR: ' + e);
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
            if (url.indexOf('123pan.com') !== -1 || url.indexOf('123.cn') !== -1) return '123网盘';
            return '网盘';
        }

        // 编码 vod_id: {item_id}|||{pan_url}|||{pan_type_name}
        function encodeVodId(itemId, panUrl, panTypeName) {
            return itemId + '|||' + encodeURIComponent(panUrl || '') + '|||' + encodeURIComponent(panTypeName || '网盘');
        }

        // 解码 vod_id
        function decodeVodId(vodId) {
            var parts = String(vodId).split('|||');
            return {
                itemId: parts[0] || '',
                panUrl: parts[1] ? decodeURIComponent(parts[1]) : '',
                panTypeName: parts[2] ? decodeURIComponent(parts[2]) : '网盘'
            };
        }

        // ===================== 首页内容 =====================
        // 奇点搜索是纯搜索引擎，无分类体系
        // 首页返回热门搜索词作为推荐

        function homeContent(filter) {
            var result = { class: [], list: [] };

            result.class = [];

            // 用第一个热门关键词搜索作为推荐列表
            try {
                var url = BASE_URL + '/api/search?title=' + encode(HOT_KEYWORDS[0]);
                var data = fetchJSON(url);
                if (data && data.code === 200 && data.data && data.data.items) {
                    result.list = parseSearchResults(data.data.items);
                }
            } catch (e) {
                print('>>> duanjutv homeContent ERROR: ' + e);
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

            // 兼容 searchContent(key, pg) 和 searchContent(key, quick, pg) 两种调用
            if (typeof quick === 'number') {
                page = quick;
            }

            try {
                // 搜索 API 不支持真分页，固定返回前 40 条
                var url = BASE_URL + '/api/search?title=' + encode(key);
                var data = fetchJSON(url);

                if (!data || data.code !== 200 || !data.data || !data.data.items || data.data.items.length === 0) {
                    print('>>> duanjutv searchContent: no data for key=' + key);
                    return result;
                }

                result.list = parseSearchResults(data.data.items);

                // API 不支持分页，只有1页
                result.pagecount = 1;

                print('>>> duanjutv searchContent: key=' + key + ' pg=' + page + ' count=' + result.list.length);
            } catch (e) {
                print('>>> duanjutv searchContent ERROR: ' + e);
            }

            return result;
        }

        // 解析搜索结果
        function parseSearchResults(items) {
            var list = [];
            if (!items) return list;

            // 用于去重（按 id + url）
            var seen = {};

            for (var i = 0; i < items.length; i++) {
                var item = items[i];

                var title = stripTags(item.title || item.name || '未知资源');
                var isType = item.is_type;
                var panTypeName = PAN_TYPE_MAP[isType] || inferCloudFromUrl(item.url || '');
                var rawUrl = item.url || '';

                // 跳过无效条目
                if (!rawUrl || !title) continue;

                // URL 可能包含多个链接（用 \n 分隔），拆分为多个条目
                var urls = String(rawUrl).split(/\n/);
                for (var j = 0; j < urls.length; j++) {
                    var panUrl = urls[j].trim();
                    if (!panUrl) continue;

                    // 去重
                    var dedupKey = item.id + '_' + panUrl;
                    if (seen[dedupKey]) continue;
                    seen[dedupKey] = true;

                    // 如果是多链接条目，根据 URL 重新推断网盘类型
                    var panName = panTypeName;
                    if (urls.length > 1) {
                        panName = inferCloudFromUrl(panUrl);
                    }

                    var itemId = item.id ? String(item.id) : ('idx_' + i + '_' + j);
                    var vodId = encodeVodId(itemId, panUrl, panName);

                    list.push({
                        vod_id: vodId,
                        vod_name: title,
                        vod_pic: '',
                        vod_remarks: '☁️' + panName
                    });
                }
            }

            return list;
        }

        // ===================== 详情内容 =====================
        // 网盘蜘蛛源约定：
        //   vod_remarks 以 "☁️" 开头 → 标识为网盘资源
        //   vod_play_url 返回 JSON 数组 [{"url":"网盘链接","name":"网盘名"}]

        function detailContent(ids) {
            var result = { list: [] };

            if (!ids) {
                print('>>> duanjutv detailContent: empty ids');
                return result;
            }

            var id = String(ids);
            print('>>> duanjutv detailContent: id=' + id.substring(0, 80));

            var decoded = decodeVodId(id);

            if (decoded.panUrl) {
                // 从 vod_id 中成功解码出网盘链接
                result.list.push({
                    vod_id: id,
                    vod_name: '网盘资源',
                    vod_pic: '',
                    vod_remarks: '☁️' + decoded.panTypeName,
                    vod_play_from: '奇点搜索',
                    vod_play_url: JSON.stringify([{ url: decoded.panUrl, name: decoded.panTypeName }])
                });
                print('>>> duanjutv detailContent SUCCESS: ' + decoded.panUrl.substring(0, 60));
            } else {
                // 无法解码，返回占位数据
                print('>>> duanjutv detailContent: failed to decode pan url');
                result.list.push({
                    vod_id: id,
                    vod_name: '网盘资源',
                    vod_pic: '',
                    vod_remarks: '☁️网盘',
                    vod_play_from: '奇点搜索',
                    vod_play_url: JSON.stringify([{ url: '', name: '网盘资源' }])
                });
            }

            return result;
        }

        // ===================== 播放内容 =====================
        // 保留作为播放降级路径

        function playerContent(vodId, flag, url) {
            print('>>> duanjutv playerContent: vodId=' + vodId.substring(0, 40));

            var decoded = decodeVodId(vodId);
            if (decoded.panUrl) {
                return {
                    parse: 0,
                    url: decoded.panUrl,
                    header: { 'User-Agent': UA }
                };
            }

            // 如果 url 参数本身是网盘链接，直接使用
            if (url && (url.indexOf('pan.') !== -1 || url.indexOf('115.com') !== -1 || url.indexOf('drive.uc') !== -1)) {
                return {
                    parse: 0,
                    url: url,
                    header: { 'User-Agent': UA }
                };
            }

            return { parse: 0, url: '' };
        }

        // ===================== 初始化 =====================

        function init(config) {
            print('>>> duanjutv init: 奇点搜索 JS蜘蛛 v1.0');
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
