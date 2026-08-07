/*
 * PanSou盘搜 JS 蜘蛛 v1.0
 * 适配 vbox-ios JSSpiderEngine (type:3 独立引擎)
 * 目标站: https://pansou.top (实际 API 域名可能为 jnnsou.com)
 * 特点: REST API 网盘聚合搜索，直接返回多网盘直链
 * 支持网盘：夸克网盘、百度网盘、UC网盘、迅雷云盘
 * 无需登录，无需加密签名
 *
 * 网盘蜘蛛源约定：
 *   - vod_remarks 以 "☁️" 开头 → 标识为网盘资源，激活网盘UI
 *   - detailContent 的 vod_play_url 返回 JSON 数组 [{"url":"网盘链接","name":"网盘名"}]
 *   - vod_id 编码格式: {title}|||{url}|||{pan_type_name}
 */

var spider = {
    __jsEvalReturn: function() {

        var BASE_URL = 'https://pansou.top';
        var API_URL = 'https://jnnsou.com';
        var UA = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36';
        var HEADER = { 'User-Agent': UA, 'Referer': BASE_URL + '/' };

        // ===================== 工具函数 =====================

        function fetch(url, headers) {
            try {
                var resp = req(url, { headers: headers || HEADER, timeout: 15000 });
                if (resp && resp.ok) {
                    return resp.content || '';
                }
                print('>>> pansou fetch FAIL: status=' + (resp ? resp.status : 'null') + ' url=' + url.substring(0, 80));
                return '';
            } catch (e) {
                print('>>> pansou fetch ERROR: ' + e);
                return '';
            }
        }

        function fetchJSON(url, headers) {
            var html = fetch(url, headers);
            if (!html) return null;
            try {
                return JSON.parse(html);
            } catch (e) {
                print('>>> pansou JSON parse ERROR: ' + e);
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
            if (url.indexOf('drive.uc.cn') !== -1 || url.indexOf('uc.cn') !== -1) return 'UC网盘';
            if (url.indexOf('aliyundrive.com') !== -1 || url.indexOf('alipan.com') !== -1) return '阿里云盘';
            if (url.indexOf('115.com') !== -1) return '115网盘';
            return '网盘';
        }

        function encodeVodId(title, url, panTypeName) {
            return encodeURIComponent(title || '') + '|||' + encodeURIComponent(url || '') + '|||' + encodeURIComponent(panTypeName || '网盘');
        }

        function decodeVodId(vodId) {
            var parts = String(vodId).split('|||');
            return {
                title: parts[0] ? decodeURIComponent(parts[0]) : '',
                url: parts[1] ? decodeURIComponent(parts[1]) : '',
                panTypeName: parts[2] ? decodeURIComponent(parts[2]) : '网盘'
            };
        }

        // 解析搜索结果
        function parseSearchResults(data) {
            var list = [];
            if (!data) return list;

            var seen = {};

            // pansou 返回的是按网盘类型分组的数据
            // data.merged_by_type 或 data.data
            var groups = data.merged_by_type || data.data || data;

            for (var platform in groups) {
                if (!groups.hasOwnProperty(platform)) continue;

                var items = groups[platform];
                if (!Array.isArray(items)) continue;

                for (var i = 0; i < items.length; i++) {
                    var item = items[i];
                    var title = stripTags(item.note || item.title || '未知资源');
                    var url = item.url || '';
                    var panTypeName = inferCloudFromUrl(url);

                    if (!url || !title) continue;

                    var dedupKey = title + '_' + url;
                    if (seen[dedupKey]) continue;
                    seen[dedupKey] = true;

                    list.push({
                        vod_id: encodeVodId(title, url, panTypeName),
                        vod_name: title,
                        vod_pic: '',
                        vod_remarks: '☁️' + panTypeName
                    });
                }
            }

            return list;
        }

        // ===================== 首页内容 =====================

        function homeContent(filter) {
            var result = { class: [], list: [] };
            var hotKeywords = ['庆余年', '凡人修仙传', '九门', '斩神', '完美世界'];

            try {
                var url = API_URL + '/api/search?kw=' + encode(hotKeywords[0]);
                var data = fetchJSON(url);
                if (data) {
                    result.list = parseSearchResults(data);
                }
            } catch (e) {
                print('>>> pansou homeContent ERROR: ' + e);
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
                var url = API_URL + '/api/search?kw=' + encode(key) + '&page=' + page;
                var data = fetchJSON(url);

                if (!data) {
                    print('>>> pansou searchContent: no data for key=' + key);
                    return result;
                }

                result.list = parseSearchResults(data);

                // 假设返回数量等于每页大小时还有下一页
                result.pagecount = result.list.length >= 20 ? page + 1 : page;

                print('>>> pansou searchContent: key=' + key + ' pg=' + page + ' count=' + result.list.length);
            } catch (e) {
                print('>>> pansou searchContent ERROR: ' + e);
            }

            return result;
        }

        // ===================== 详情内容 =====================

        function detailContent(ids) {
            var result = { list: [] };

            if (!ids) {
                print('>>> pansou detailContent: empty ids');
                return result;
            }

            var id = String(ids);
            var decoded = decodeVodId(id);
            print('>>> pansou detailContent: id=' + id.substring(0, 80));

            if (decoded.url) {
                result.list.push({
                    vod_id: id,
                    vod_name: decoded.title || '网盘资源',
                    vod_pic: '',
                    vod_remarks: '☁️' + decoded.panTypeName,
                    vod_play_from: 'PanSou盘搜',
                    vod_play_url: JSON.stringify([{ url: decoded.url, name: decoded.panTypeName }])
                });
                print('>>> pansou detailContent SUCCESS: ' + decoded.url.substring(0, 60));
            } else {
                result.list.push({
                    vod_id: id,
                    vod_name: decoded.title || '网盘资源',
                    vod_pic: '',
                    vod_remarks: '☁️网盘',
                    vod_play_from: 'PanSou盘搜',
                    vod_play_url: JSON.stringify([{ url: '', name: '未获取到链接' }])
                });
            }

            return result;
        }

        // ===================== 播放内容 =====================

        function playerContent(vodId, flag, url) {
            print('>>> pansou playerContent: vodId=' + vodId.substring(0, 40));

            if (url && url.indexOf('http') === 0) {
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
            print('>>> pansou init: PanSou盘搜 JS蜘蛛 v1.0');
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
