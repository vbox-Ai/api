/*
 * GG盘 JS 蜘蛛 v1.0
 * 适配 vbox-ios JSSpiderEngine (type:3 独立引擎)
 * 目标站: https://ggpan.com
 * 特点: REST API 网盘资源搜索，302 跳转获取直链
 * 支持网盘：夸克网盘
 * 无需登录，无需加密签名
 *
 * 网盘蜘蛛源约定：
 *   - vod_remarks 以 "☁️" 开头 → 标识为网盘资源，激活网盘UI
 *   - detailContent 的 vod_play_url 返回 JSON 数组 [{"url":"网盘链接","name":"网盘名"}]
 *   - vod_id 编码格式: {resource_id}|||{title}|||{pan_type_name}
 */

var spider = {
    __jsEvalReturn: function() {

        var BASE_URL = 'https://ggpan.com';
        var UA = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36';
        var HEADER = { 'User-Agent': UA, 'Referer': BASE_URL + '/' };

        // ===================== 工具函数 =====================

        function fetch(url, headers, opts) {
            try {
                var options = opts || {};
                options.headers = headers || HEADER;
                var resp = req(url, options);
                if (resp && resp.ok) {
                    return resp.content || '';
                }
                print('>>> ggpan fetch FAIL: status=' + (resp ? resp.status : 'null') + ' url=' + url.substring(0, 80));
                return '';
            } catch (e) {
                print('>>> ggpan fetch ERROR: ' + e);
                return '';
            }
        }

        function fetchJSON(url, headers, opts) {
            var html = fetch(url, headers, opts);
            if (!html) return null;
            try {
                return JSON.parse(html);
            } catch (e) {
                print('>>> ggpan JSON parse ERROR: ' + e);
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

        function encodeVodId(id, title, panTypeName) {
            return String(id) + '|||' + encodeURIComponent(title || '') + '|||' + encodeURIComponent(panTypeName || '网盘');
        }

        function decodeVodId(vodId) {
            var parts = String(vodId).split('|||');
            return {
                id: parts[0] || '',
                title: parts[1] ? decodeURIComponent(parts[1]) : '',
                panTypeName: parts[2] ? decodeURIComponent(parts[2]) : '网盘'
            };
        }

        // ===================== 首页内容 =====================
        // GG盘无分类体系，首页返回热门搜索推荐

        function homeContent(filter) {
            var result = { class: [], list: [] };
            var hotKeywords = ['庆余年', '凡人修仙传', '九门', '斩神', '完美世界'];

            try {
                var url = BASE_URL + '/api/public/resources?q=' + encode(hotKeywords[0]) + '&page=1';
                var data = fetchJSON(url);
                if (data && data.items) {
                    result.list = parseSearchResults(data.items);
                }
            } catch (e) {
                print('>>> ggpan homeContent ERROR: ' + e);
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
                var url = BASE_URL + '/api/public/resources?q=' + encode(key) + '&page=' + page;
                var data = fetchJSON(url);

                if (!data || !data.items || data.items.length === 0) {
                    print('>>> ggpan searchContent: no data for key=' + key);
                    return result;
                }

                result.list = parseSearchResults(data.items);

                // 判断是否还有下一页
                var hasMore = data.page * data.page_size < data.total;
                result.pagecount = hasMore ? page + 1 : page;

                print('>>> ggpan searchContent: key=' + key + ' pg=' + page + ' count=' + result.list.length);
            } catch (e) {
                print('>>> ggpan searchContent ERROR: ' + e);
            }

            return result;
        }

        // 解析搜索结果
        function parseSearchResults(items) {
            var list = [];
            if (!items) return list;

            for (var i = 0; i < items.length; i++) {
                var item = items[i];
                var title = stripTags(item.title || '未知资源');
                var id = item.id;

                if (!id || !title) continue;

                var qualities = [];
                if (item.metadata && item.metadata.qualities) {
                    qualities = item.metadata.qualities;
                }
                var remark = '☁️夸克网盘';
                if (qualities.length > 0) {
                    remark += ' ' + qualities.join('/');
                }

                list.push({
                    vod_id: encodeVodId(id, title, '夸克网盘'),
                    vod_name: title,
                    vod_pic: item.cover_url || '',
                    vod_remarks: remark
                });
            }

            return list;
        }

        // ===================== 详情内容 =====================

        function detailContent(ids) {
            var result = { list: [] };

            if (!ids) {
                print('>>> ggpan detailContent: empty ids');
                return result;
            }

            var id = String(ids);
            var decoded = decodeVodId(id);
            print('>>> ggpan detailContent: id=' + id.substring(0, 80));

            if (!decoded.id) {
                result.list.push({
                    vod_id: id,
                    vod_name: decoded.title || '网盘资源',
                    vod_pic: '',
                    vod_remarks: '☁️网盘',
                    vod_play_from: 'GG盘',
                    vod_play_url: JSON.stringify([{ url: '', name: '网盘资源' }])
                });
                return result;
            }

            try {
                // 302 跳转获取真实网盘链接
                var redirectUrl = BASE_URL + '/api/public/resources/' + decoded.id + '/redirect?visitor_id=vbox';
                var resp = req(redirectUrl, { headers: HEADER, redirect: 'manual', timeout: 15000 });
                var realUrl = '';

                if (resp && resp.headers && resp.headers.location) {
                    realUrl = resp.headers.location;
                } else if (resp && resp.headers && resp.headers.Location) {
                    realUrl = resp.headers.Location;
                } else if (resp && resp.ok && resp.content) {
                    try {
                        var json = JSON.parse(resp.content);
                        realUrl = json.url || json.data || '';
                    } catch (e) {}
                }

                if (realUrl) {
                    result.list.push({
                        vod_id: id,
                        vod_name: decoded.title || '网盘资源',
                        vod_pic: '',
                        vod_remarks: '☁️' + decoded.panTypeName,
                        vod_play_from: 'GG盘',
                        vod_play_url: JSON.stringify([{ url: realUrl, name: decoded.panTypeName }])
                    });
                    print('>>> ggpan detailContent SUCCESS: ' + realUrl.substring(0, 60));
                } else {
                    result.list.push({
                        vod_id: id,
                        vod_name: decoded.title || '网盘资源',
                        vod_pic: '',
                        vod_remarks: '☁️网盘',
                        vod_play_from: 'GG盘',
                        vod_play_url: JSON.stringify([{ url: '', name: '未获取到链接' }])
                    });
                }
            } catch (e) {
                print('>>> ggpan detailContent ERROR: ' + e);
                result.list.push({
                    vod_id: id,
                    vod_name: decoded.title || '网盘资源',
                    vod_pic: '',
                    vod_remarks: '☁️网盘',
                    vod_play_from: 'GG盘',
                    vod_play_url: JSON.stringify([{ url: '', name: '请求异常' }])
                });
            }

            return result;
        }

        // ===================== 播放内容 =====================

        function playerContent(vodId, flag, url) {
            print('>>> ggpan playerContent: vodId=' + vodId.substring(0, 40));

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
            print('>>> ggpan init: GG盘 JS蜘蛛 v1.0');
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
