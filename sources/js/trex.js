/*
 * T-Rex JS 蜘蛛 v1.0
 * 适配 vbox-ios JSSpiderEngine (type:3 独立引擎)
 * 目标站: https://trex.tzfile.com
 * 特点: WordPress REST API + JWT 令牌链路获取真实网盘链接
 * 支持网盘：夸克网盘、百度网盘、迅雷云盘、阿里云盘等
 * 无需登录，无需加密签名
 *
 * 网盘蜘蛛源约定：
 *   - vod_remarks 以 "☁️" 开头 → 标识为网盘资源，激活网盘UI
 *   - detailContent 的 vod_play_url 返回 JSON 数组 [{"url":"网盘链接","name":"网盘名"}]
 *   - vod_id 编码格式: {post_id}|||{title}
 */

var spider = {
    __jsEvalReturn: function() {

        var BASE_URL = 'https://trex.tzfile.com';
        var UA = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36';
        var HEADER = {
            'User-Agent': UA,
            'Referer': BASE_URL + '/'
        };

        // ===================== 工具函数 =====================

        function fetch(url, headers) {
            try {
                var resp = req(url, { headers: headers || HEADER, timeout: 20000 });
                if (resp && resp.ok) {
                    return resp.content || '';
                }
                print('>>> trex fetch FAIL: status=' + (resp ? resp.status : 'null') + ' url=' + url.substring(0, 80));
                return '';
            } catch (e) {
                print('>>> trex fetch ERROR: ' + e);
                return '';
            }
        }

        function fetchJSON(url, headers) {
            var html = fetch(url, headers);
            if (!html) return null;
            try {
                return JSON.parse(html);
            } catch (e) {
                print('>>> trex JSON parse ERROR: ' + e);
                return null;
            }
        }

        function postJSON(url, body, headers) {
            try {
                var h = {};
                for (var k in (headers || HEADER)) { h[k] = HEADER[k]; }
                h['Content-Type'] = 'application/json';
                var resp = req(url, { method: 'POST', headers: h, body: JSON.stringify(body), timeout: 15000 });
                if (resp && resp.ok) {
                    var content = resp.content || '';
                    if (typeof content === 'object') return content;
                    try { return JSON.parse(content); } catch (e) { return null; }
                }
                print('>>> trex POST FAIL: status=' + (resp ? resp.status : 'null'));
                return null;
            } catch (e) {
                print('>>> trex POST ERROR: ' + e);
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

        function inferCloudFromUrl(url) {
            if (!url) return '网盘';
            if (url.indexOf('pan.quark.cn') !== -1) return '夸克网盘';
            if (url.indexOf('pan.baidu.com') !== -1) return '百度网盘';
            if (url.indexOf('pan.xunlei.com') !== -1) return '迅雷云盘';
            if (url.indexOf('115.com') !== -1) return '115网盘';
            if (url.indexOf('aliyundrive.com') !== -1 || url.indexOf('alipan.com') !== -1) return '阿里云盘';
            if (url.indexOf('drive.uc.cn') !== -1 || url.indexOf('uc.cn') !== -1) return 'UC网盘';
            return '网盘';
        }

        // ===================== 首页内容 =====================

        function homeContent(filter) {
            var result = { class: [], list: [] };

            try {
                var url = BASE_URL + '/wp-json/wp/v2/posts?per_page=24&page=1';
                var posts = fetchJSON(url);
                if (posts && Array.isArray(posts)) {
                    result.list = parsePosts(posts);
                }
            } catch (e) {
                print('>>> trex homeContent ERROR: ' + e);
            }

            return result;
        }

        function parsePosts(posts) {
            var list = [];
            if (!posts) return list;

            for (var i = 0; i < posts.length; i++) {
                var p = posts[i];
                var title = stripTags(p.title && p.title.rendered ? p.title.rendered : '未知资源');
                var id = p.id;

                if (!id || !title) continue;

                list.push({
                    vod_id: encodeVodId(id, title),
                    vod_name: title,
                    vod_pic: p.featured_media_url || '',
                    vod_remarks: '☁️网盘'
                });
            }

            return list;
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
                var url = BASE_URL + '/wp-json/wp/v2/posts?search=' + encode(key) + '&per_page=20&page=' + page;
                var headers = Object.assign({}, HEADER);
                var resp = req(url, { headers: headers, timeout: 20000 });

                if (!resp || !resp.ok) {
                    print('>>> trex searchContent FAIL: status=' + (resp ? resp.status : 'null'));
                    return result;
                }

                var posts = [];
                try {
                    posts = JSON.parse(resp.content || '');
                } catch (e) {
                    print('>>> trex searchContent parse ERROR: ' + e);
                    return result;
                }

                if (!Array.isArray(posts) || posts.length === 0) {
                    print('>>> trex searchContent: no data for key=' + key);
                    return result;
                }

                result.list = parsePosts(posts);

                // WordPress REST API 返回 X-WP-Total 总数
                var total = resp.headers['X-WP-Total'] || resp.headers['x-wp-total'] || '0';
                var totalPages = resp.headers['X-WP-TotalPages'] || resp.headers['x-wp-totalpages'] || '1';
                result.pagecount = parseInt(totalPages) || page;

                print('>>> trex searchContent: key=' + key + ' pg=' + page + ' count=' + result.list.length);
            } catch (e) {
                print('>>> trex searchContent ERROR: ' + e);
            }

            return result;
        }

        // ===================== 详情内容 =====================

        function detailContent(ids) {
            var result = { list: [] };

            if (!ids) {
                print('>>> trex detailContent: empty ids');
                return result;
            }

            var id = String(ids);
            var decoded = decodeVodId(id);
            print('>>> trex detailContent: id=' + id.substring(0, 80));

            if (!decoded.postId) {
                result.list.push({
                    vod_id: id,
                    vod_name: decoded.title || '网盘资源',
                    vod_pic: '',
                    vod_remarks: '☁️网盘',
                    vod_play_from: 'T-Rex',
                    vod_play_url: JSON.stringify([{ url: '', name: '网盘资源' }])
                });
                return result;
            }

            try {
                var postId = decoded.postId;
                var postUrl = BASE_URL + '/' + postId + '.html';
                var refererHeader = Object.assign({}, HEADER, { 'Referer': postUrl });

                // 步骤1：获取下载信息
                var dlData = postJSON(
                    BASE_URL + '/wp-json/b2/v1/getDownloadData',
                    { post_id: String(postId) },
                    refererHeader
                );

                if (!dlData || !Array.isArray(dlData) || dlData.length === 0) {
                    print('>>> trex detailContent: no download data');
                    result.list.push({
                        vod_id: id,
                        vod_name: decoded.title || '网盘资源',
                        vod_pic: '',
                        vod_remarks: '☁️网盘',
                        vod_play_from: 'T-Rex',
                        vod_play_url: JSON.stringify([{ url: '', name: '无下载信息' }])
                    });
                    return result;
                }

                var allLinks = [];

                for (var g = 0; g < dlData.length; g++) {
                    var group = dlData[g];
                    var buttons = group.button || [];

                    for (var i = 0; i < buttons.length; i++) {
                        var btn = buttons[i];
                        var btnLink = btn.link || '';

                        if (!btnLink) continue;

                        // 步骤2：获取 JWT 令牌
                        var tokenData = postJSON(
                            BASE_URL + '/wp-json/b2/v1/getDownloadPageData',
                            { post_id: String(postId), index: 0, i: i },
                            Object.assign({}, HEADER, { 'Referer': btnLink })
                        );

                        if (!tokenData || !tokenData.button || !tokenData.button.url) {
                            print('>>> trex detailContent: no token for button ' + i);
                            continue;
                        }

                        var jwt = tokenData.button.url;

                        // 步骤3：获取真实链接
                        var redirectHtml = fetch(
                            BASE_URL + '/redirect?token=' + encode(jwt),
                            Object.assign({}, HEADER, { 'Referer': btnLink })
                        );

                        var urlMatch = redirectHtml.match(/https?:\/\/[^\s"'<>]+/);
                        if (urlMatch && urlMatch[0]) {
                            var realUrl = urlMatch[0];
                            var platform = inferCloudFromUrl(realUrl);
                            var pwd = btn.attr && btn.attr.tq ? btn.attr.tq : '';
                            var urlWithPwd = realUrl + (pwd ? '|' + pwd : '');

                            allLinks.push({
                                name: (btn.name || platform) + (pwd ? ' 密码:' + pwd : ''),
                                url: urlWithPwd,
                                platform: platform
                            });
                            print('>>> trex detailContent SUCCESS: ' + realUrl.substring(0, 60));
                        }
                    }
                }

                if (allLinks.length > 0) {
                    // 按平台分组
                    var groups = {};
                    var order = [];
                    for (var j = 0; j < allLinks.length; j++) {
                        var link = allLinks[j];
                        if (!groups[link.platform]) {
                            groups[link.platform] = [];
                            order.push(link.platform);
                        }
                        groups[link.platform].push({ url: link.url, name: link.name });
                    }

                    var playFromParts = [];
                    var playUrlParts = [];
                    for (var k = 0; k < order.length; k++) {
                        playFromParts.push(order[k]);
                        playUrlParts.push(JSON.stringify(groups[order[k]]));
                    }

                    result.list.push({
                        vod_id: id,
                        vod_name: decoded.title || '网盘资源',
                        vod_pic: '',
                        vod_remarks: '☁️' + order.join('/'),
                        vod_play_from: playFromParts.join('$$$'),
                        vod_play_url: playUrlParts.join('$$$')
                    });
                } else {
                    result.list.push({
                        vod_id: id,
                        vod_name: decoded.title || '网盘资源',
                        vod_pic: '',
                        vod_remarks: '☁️网盘',
                        vod_play_from: 'T-Rex',
                        vod_play_url: JSON.stringify([{ url: '', name: '未获取到链接' }])
                    });
                }
            } catch (e) {
                print('>>> trex detailContent ERROR: ' + e);
                result.list.push({
                    vod_id: id,
                    vod_name: decoded.title || '网盘资源',
                    vod_pic: '',
                    vod_remarks: '☁️网盘',
                    vod_play_from: 'T-Rex',
                    vod_play_url: JSON.stringify([{ url: '', name: '请求异常' }])
                });
            }

            return result;
        }

        // ===================== 播放内容 =====================

        function playerContent(vodId, flag, url) {
            print('>>> trex playerContent: vodId=' + vodId.substring(0, 40));

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
            print('>>> trex init: T-Rex JS蜘蛛 v1.0');
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
