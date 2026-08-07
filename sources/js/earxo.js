/*
 * 清欢短剧 JS 蜘蛛 v1.0
 * 适配 vbox-ios JSSpiderEngine (type:3 独立引擎)
 * 目标站: https://www.earxo.com
 * 特点: Z-BlogPHP 短剧站，热榜 API 直接返回夸克直链，详情页明文解析
 * 支持网盘：夸克网盘
 * 无需登录，无需加密签名
 *
 * 网盘蜘蛛源约定：
 *   - vod_remarks 以 "☁️" 开头 → 标识为网盘资源，激活网盘UI
 *   - detailContent 的 vod_play_url 返回 JSON 数组 [{"url":"网盘链接","name":"网盘名"}]
 *   - vod_id 编码格式: {post_id}|||{title}
 */

var spider = {
    __jsEvalReturn: function() {

        var BASE_URL = 'https://www.earxo.com';
        var UA = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36';
        var HEADER = { 'User-Agent': UA, 'Referer': BASE_URL + '/' };

        // 热榜类型映射
        var HOT_TYPES = [
            { type_id: '', type_name: '短剧' },
            { type_id: 'movie', type_name: '电影' },
            { type_id: 'tv', type_name: '电视剧' },
            { type_id: 'variety', type_name: '综艺' }
        ];

        // ===================== 工具函数 =====================

        function fetch(url, headers) {
            try {
                var resp = req(url, { headers: headers || HEADER, timeout: 15000 });
                if (resp && resp.ok) {
                    return resp.content || '';
                }
                print('>>> earxo fetch FAIL: status=' + (resp ? resp.status : 'null') + ' url=' + url.substring(0, 80));
                return '';
            } catch (e) {
                print('>>> earxo fetch ERROR: ' + e);
                return '';
            }
        }

        function fetchJSON(url, headers) {
            var html = fetch(url, headers);
            if (!html) return null;
            try {
                return JSON.parse(html);
            } catch (e) {
                print('>>> earxo JSON parse ERROR: ' + e);
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

        function encodeVodId(postId, title) {
            return String(postId) + '|||' + encodeURIComponent(title || '');
        }

        function decodeVodId(vodId) {
            var parts = String(vodId).split('|||');
            return {
                postId: parts[0] || '',
                title: parts[1] ? decodeURIComponent(parts[1]) : ''
            };
        }

        // 从详情页 HTML 提取夸克链接
        function extractQuarkUrl(html) {
            if (!html) return '';

            // 方式1: window.quarkFirstUrl
            var match1 = html.match(/window\.quarkFirstUrl\s*=\s*["']([^"']+)["']/);
            if (match1 && match1[1]) {
                var url1 = match1[1].replace(/\\\//g, '/');
                if (url1.indexOf('pan.quark.cn') !== -1) return url1;
            }

            // 方式2: resource-btn href
            var match2 = html.match(/<a[^>]*class=["'][^"']*resource-btn[^"']*["'][^>]*href=["']([^"']+)["']/);
            if (match2 && match2[1]) {
                var url2 = match2[1];
                if (url2.indexOf('pan.quark.cn') !== -1) return url2;
            }

            // 方式3: 任意夸克链接
            var match3 = html.match(/https?:\\\/\\\/pan\.quark\.cn\/s\/[^"'\s\\]+/);
            if (match3 && match3[0]) {
                return match3[0].replace(/\\\//g, '/');
            }

            return '';
        }

        // 从搜索结果 HTML 提取 post id 和标题
        function extractSearchResults(html) {
            var results = [];
            if (!html) return results;

            var seen = {}; // postId → results 数组索引
            // 匹配包含 post 链接的 <a> 标签，同时捕获链接文本作为标题
            var regex = /<a[^>]*href=["'](?:https?:\/\/www\.earxo\.com)?\/post\/(\d+)\.html["'][^>]*>([\s\S]*?)<\/a>/g;
            var match;
            while ((match = regex.exec(html)) !== null) {
                var postId = match[1];
                var titleHtml = match[2] || '';
                var title = stripTags(titleHtml).trim();

                // 清理 img alt 属性中嵌套 HTML 标签导致的尾部残留 ">
                if (title && title.indexOf('">') !== -1) {
                    title = title.replace(/">/g, '').trim();
                }

                if (!postId) continue;

                // 同一个 postId 可能出现多次（缩略图链接 + 标题链接）
                // 优先保留更长、更完整的标题（标题链接在 <h2> 中，通常比缩略图 alt 更准确）
                if (seen[postId] !== undefined) {
                    if (title && title.length > results[seen[postId]].title.length) {
                        results[seen[postId]].title = title;
                    }
                    continue;
                }

                seen[postId] = results.length;
                results.push({ id: postId, title: title });
            }

            // 如果上面没匹配到，回退到仅提取 ID
            if (results.length === 0) {
                regex = /href=["'](?:https?:\/\/www\.earxo\.com)?\/post\/(\d+)\.html["']/g;
                while ((match = regex.exec(html)) !== null) {
                    var id = match[1];
                    if (seen[id] === undefined) {
                        seen[id] = results.length;
                        results.push({ id: id, title: '' });
                    }
                }
            }

            return results;
        }

        function extractTitleFromHtml(html, postId) {
            if (!html) return '未知资源';
            var match = html.match(/<h1[^>]*class=["'][^"']*resource-title[^"']*["'][^>]*>(.*?)<\/h1>/);
            if (match && match[1]) {
                return stripTags(match[1]);
            }
            match = html.match(/<title>(.*?)<\/title>/);
            if (match && match[1]) {
                return stripTags(match[1]).replace(/_清欢短剧$/, '').trim();
            }
            return '未知资源';
        }

        // ===================== 首页内容 =====================

        function homeContent(filter) {
            var result = { class: HOT_TYPES, list: [] };

            try {
                var data = fetchJSON(BASE_URL + '/remen.php');
                if (data && data.data && data.data.hits && data.data.hits.hit && data.data.hits.hit.item) {
                    var items = data.data.hits.hit.item;
                    for (var i = 0; i < items.length && i < 24; i++) {
                        var item = items[i];
                        var title = stripTags(item.title || '');
                        if (!title) continue;

                        var postId = '';
                        if (item.content_id && String(item.content_id).match(/^\d+$/)) {
                            postId = String(item.content_id);
                        }

                        result.list.push({
                            vod_id: encodeVodId(postId || ('rank_' + i), title),
                            vod_name: title,
                            vod_pic: item.src || '',
                            vod_remarks: '☁️夸克网盘 ' + (item.channel || '短剧')
                        });
                    }
                }
            } catch (e) {
                print('>>> earxo homeContent ERROR: ' + e);
            }

            return result;
        }

        // ===================== 分类内容 =====================
        // 使用热榜类型作为分类

        function categoryContent(tid, pg, filter, extend) {
            var page = parseInt(pg) || 1;
            var result = { list: [], page: page, pagecount: 1, limit: 24, total: 0 };

            try {
                var type = tid === '短剧' ? '' : tid;
                var url = BASE_URL + '/remen.php' + (type ? '?type=' + encode(type) : '');
                var data = fetchJSON(url);

                if (data && data.data && data.data.hits && data.data.hits.hit && data.data.hits.hit.item) {
                    var items = data.data.hits.hit.item;
                    result.total = items.length;

                    var pageSize = 24;
                    var startIdx = (page - 1) * pageSize;
                    var endIdx = Math.min(startIdx + pageSize, items.length);

                    for (var i = startIdx; i < endIdx; i++) {
                        var item = items[i];
                        var title = stripTags(item.title || '');
                        if (!title) continue;

                        var postId = '';
                        if (item.content_id && String(item.content_id).match(/^\d+$/)) {
                            postId = String(item.content_id);
                        }

                        result.list.push({
                            vod_id: encodeVodId(postId || ('rank_' + i), title),
                            vod_name: title,
                            vod_pic: item.src || '',
                            vod_remarks: '☁️夸克网盘 ' + (item.channel || tid)
                        });
                    }

                    result.pagecount = Math.ceil(items.length / pageSize) || 1;
                }
            } catch (e) {
                print('>>> earxo categoryContent ERROR: ' + e);
            }

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
                var url = BASE_URL + '/search/' + encode(key);
                var html = fetch(url);
                var searchResults = extractSearchResults(html);

                if (searchResults.length === 0) {
                    print('>>> earxo searchContent: no data for key=' + key);
                    return result;
                }

                var pageSize = 20;
                var startIdx = (page - 1) * pageSize;
                var pageResults = searchResults.slice(startIdx, startIdx + pageSize);

                for (var i = 0; i < pageResults.length; i++) {
                    var item = pageResults[i];
                    result.list.push({
                        vod_id: encodeVodId(item.id, item.title),
                        vod_name: item.title || ('清欢短剧 #' + item.id),
                        vod_pic: '',
                        vod_remarks: '☁️夸克网盘'
                    });
                }

                result.pagecount = (startIdx + pageSize) < searchResults.length ? page + 1 : page;
                print('>>> earxo searchContent: key=' + key + ' pg=' + page + ' count=' + result.list.length);
            } catch (e) {
                print('>>> earxo searchContent ERROR: ' + e);
            }

            return result;
        }

        // ===================== 详情内容 =====================

        function detailContent(ids) {
            var result = { list: [] };

            if (!ids) {
                print('>>> earxo detailContent: empty ids');
                return result;
            }

            var id = String(ids);
            var decoded = decodeVodId(id);
            print('>>> earxo detailContent: id=' + id.substring(0, 80));

            var title = decoded.title;
            var realUrl = '';
            var postId = '';

            try {
                // 情况1：有 postId，进入详情页提取链接
                if (decoded.postId && String(decoded.postId).match(/^\d+$/)) {
                    postId = decoded.postId;
                    var detailHtml = fetch(BASE_URL + '/post/' + postId + '.html');
                    if (!title || title.indexOf('earxo-') === 0) {
                        title = extractTitleFromHtml(detailHtml, postId);
                    }
                    realUrl = extractQuarkUrl(detailHtml);
                }

                // 情况2：没有 postId（来自热榜 content_id 为空），尝试从热榜搜索匹配
                if (!realUrl && title) {
                    var data = fetchJSON(BASE_URL + '/remen.php');
                    if (data && data.data && data.data.hits && data.data.hits.hit && data.data.hits.hit.item) {
                        var items = data.data.hits.hit.item;
                        for (var i = 0; i < items.length; i++) {
                            if (items[i].title === title && items[i].play_link) {
                                realUrl = items[i].play_link;
                                break;
                            }
                        }
                    }
                }

                if (realUrl) {
                    result.list.push({
                        vod_id: id,
                        vod_name: title || '网盘资源',
                        vod_pic: '',
                        vod_remarks: '☁️夸克网盘',
                        vod_play_from: '清欢短剧',
                        vod_play_url: JSON.stringify([{ url: realUrl, name: '夸克网盘' }])
                    });
                    print('>>> earxo detailContent SUCCESS: ' + realUrl.substring(0, 60));
                } else {
                    result.list.push({
                        vod_id: id,
                        vod_name: title || '网盘资源',
                        vod_pic: '',
                        vod_remarks: '☁️网盘',
                        vod_play_from: '清欢短剧',
                        vod_play_url: JSON.stringify([{ url: '', name: '未获取到链接' }])
                    });
                }
            } catch (e) {
                print('>>> earxo detailContent ERROR: ' + e);
                result.list.push({
                    vod_id: id,
                    vod_name: title || '网盘资源',
                    vod_pic: '',
                    vod_remarks: '☁️网盘',
                    vod_play_from: '清欢短剧',
                    vod_play_url: JSON.stringify([{ url: '', name: '请求异常' }])
                });
            }

            return result;
        }

        // ===================== 播放内容 =====================

        function playerContent(vodId, flag, url) {
            print('>>> earxo playerContent: vodId=' + vodId.substring(0, 40));

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
            print('>>> earxo init: 清欢短剧 JS蜘蛛 v1.0');
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
