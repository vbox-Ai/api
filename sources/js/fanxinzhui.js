/*
 * 追新番 JS 蜘蛛 v1.0
 * 适配 vbox-ios JSSpiderEngine (type:3 独立引擎)
 * 目标站: https://www.fanxinzhui.com
 * 特点: 字幕组发布站，HTML 明文解析，支持迅雷/百度/微云多网盘
 * 支持网盘：迅雷云盘、百度网盘、腾讯微云
 * 无需登录，无需加密签名
 *
 * 网盘蜘蛛源约定：
 *   - vod_remarks 以 "☁️" 开头 → 标识为网盘资源，激活网盘UI
 *   - detailContent 的 vod_play_url 返回 JSON 数组 [{"url":"网盘链接","name":"网盘名"}]
 *   - vod_id 编码格式: {resource_id}|||{title}
 */

var spider = {
    __jsEvalReturn: function() {

        var BASE_URL = 'https://www.fanxinzhui.com';
        var UA = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36';
        var HEADER = { 'User-Agent': UA, 'Referer': BASE_URL + '/' };

        // 分类映射
        var CATEGORIES = [
            { type_id: 'all', type_name: '最新影视' },
            { type_id: 'tv', type_name: '日剧' },
            { type_id: 'movie', type_name: '电影' }
        ];

        // ===================== 工具函数 =====================

        function fetch(url, headers) {
            try {
                var resp = req(url, { headers: headers || HEADER, timeout: 20000 });
                if (resp && resp.ok) {
                    return resp.content || '';
                }
                print('>>> fanxinzhui fetch FAIL: status=' + (resp ? resp.status : 'null') + ' url=' + url.substring(0, 80));
                return '';
            } catch (e) {
                print('>>> fanxinzhui fetch ERROR: ' + e);
                return '';
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

        function encodeVodId(resourceId, title) {
            return String(resourceId) + '|||' + encodeURIComponent(title || '');
        }

        function decodeVodId(vodId) {
            var parts = String(vodId).split('|||');
            return {
                resourceId: parts[0] || '',
                title: parts[1] ? decodeURIComponent(parts[1]) : ''
            };
        }

        // 从网盘 URL 推断网盘名称
        function inferCloudFromUrl(url) {
            if (!url) return '网盘';
            if (url.indexOf('pan.xunlei.com') !== -1) return '迅雷云盘';
            if (url.indexOf('pan.baidu.com') !== -1) return '百度网盘';
            if (url.indexOf('share.weiyun.com') !== -1) return '腾讯微云';
            return '网盘';
        }

        // 从列表页 HTML 提取资源 ID 和标题
        function extractResourceList(html) {
            var results = [];
            if (!html) return results;

            var seen = {};
            // 匹配包含 /rr/{id} 链接的 <a> 标签，同时捕获链接文本作为标题
            var regex = /<a[^>]*href=["']\/rr\/(\d+)["'][^>]*>([\s\S]*?)<\/a>/g;
            var match;
            while ((match = regex.exec(html)) !== null) {
                var id = match[1];
                var titleHtml = match[2] || '';
                var title = stripTags(titleHtml).trim();

                if (id && !seen[id]) {
                    seen[id] = true;
                    results.push({ id: id, title: title });
                }
            }

            // 回退：仅提取 ID
            if (results.length === 0) {
                regex = /href=["']\/rr\/(\d+)["']/g;
                while ((match = regex.exec(html)) !== null) {
                    var rid = match[1];
                    if (!seen[rid]) {
                        seen[rid] = true;
                        results.push({ id: rid, title: '' });
                    }
                }
            }
            return results;
        }

        // 从详情页提取标题
        function extractTitle(html) {
            if (!html) return '未知资源';
            var match = html.match(/<h2>(.*?)<span class="year">/);
            if (match && match[1]) {
                return stripTags(match[1]).trim();
            }
            match = html.match(/<title>(.*?)<\/title>/);
            if (match && match[1]) {
                return stripTags(match[1]).replace(/_追新番$/, '').trim();
            }
            return '未知资源';
        }

        // 从详情页提取所有网盘链接
        function extractLinks(html) {
            var links = [];
            if (!html) return links;

            // 截取下载资源区域
            var sectionMatch = html.match(/<div class="resource_item[^"]*">[\s\S]*?<\/div>\s*<\/div>\s*<\/div>/);
            var section = sectionMatch ? sectionMatch[0] : html;

            // 按 <li> 拆分每集
            var liRegex = /<li>([\s\S]*?)<\/li>/g;
            var liMatch;
            var episodeIndex = 0;

            while ((liMatch = liRegex.exec(section)) !== null) {
                episodeIndex++;
                var liHtml = liMatch[1];

                // 提取集数标识
                var seasonMatch = liHtml.match(/<span class="season">(.*?)<\/span>/);
                var episodeName = seasonMatch ? stripTags(seasonMatch[1]) : ('第' + episodeIndex + '集');

                // 提取所有 <span> 内的网盘链接
                var spanRegex = /<span>([\s\S]*?)<\/span>/g;
                var spanMatch;
                while ((spanMatch = spanRegex.exec(liHtml)) !== null) {
                    var spanHtml = spanMatch[1];

                    // 匹配链接
                    var urlMatch = spanHtml.match(/href=["']([^"']+)["']/);
                    if (!urlMatch || !urlMatch[1]) continue;

                    var url = urlMatch[1];
                    if (url.indexOf('javascript:') === 0) continue;

                    // 处理迅雷磁力链（可能带 # 后缀）
                    url = url.replace(/#+$/, '');

                    var platform = inferCloudFromUrl(url);
                    if (platform === '网盘') continue;

                    var password = '';

                    // 迅雷：从 URL ?pwd= 提取密码
                    if (platform === '迅雷云盘') {
                        var pwdMatch = url.match(/\?pwd=(\w+)/);
                        if (pwdMatch && pwdMatch[1]) {
                            password = pwdMatch[1];
                            url = url.replace(/\?pwd=\w+/, '');
                        }
                    }

                    // 百度：从相邻 password 元素提取
                    if (platform === '百度网盘') {
                        // 在当前 span 后面查找 password
                        var pwdRegex = new RegExp(url.replace(/[.*+?^${}()|[\]\\]/g, '\\$&') + '[\s\S]*?<a[^>]*class=\'password\'[^>]*>([^<]*)<', 'i');
                        var pwdMatch2 = liHtml.match(pwdRegex);
                        if (pwdMatch2 && pwdMatch2[1]) {
                            password = stripTags(pwdMatch2[1]);
                        }
                    }

                    links.push({
                        name: episodeName + ' ' + platform,
                        url: url,
                        platform: platform,
                        password: password
                    });
                }
            }

            // 回退方案：如果结构化解析没有找到链接，扫描整个 HTML 中的网盘链接
            if (links.length === 0) {
                var panPatterns = [
                    /https?:\/\/pan\.xunlei\.com\/s\/[^\s"'<>()\\]+/g,
                    /https?:\/\/pan\.baidu\.com\/s\/[^\s"'<>()\\]+/g,
                    /https?:\/\/share\.weiyun\.com\/[^\s"'<>()\\]+/g
                ];

                var seenUrls = {};
                for (var p = 0; p < panPatterns.length; p++) {
                    var pMatch;
                    while ((pMatch = panPatterns[p].exec(html)) !== null) {
                        var panUrl = pMatch[0].replace(/\\\//g, '/').replace(/#+$/, '');
                        if (seenUrls[panUrl]) continue;
                        seenUrls[panUrl] = true;

                        var panPlatform = inferCloudFromUrl(panUrl);
                        var panPwd = '';

                        if (panPlatform === '迅雷云盘') {
                            var xPwdMatch = panUrl.match(/\?pwd=(\w+)/);
                            if (xPwdMatch && xPwdMatch[1]) {
                                panPwd = xPwdMatch[1];
                                panUrl = panUrl.replace(/\?pwd=\w+/, '');
                            }
                        }

                        // 尝试从 URL 附近提取密码
                        if (!panPwd) {
                            var nearbyPwd = html.substring(pMatch.index, pMatch.index + 500);
                            var pwdNearbyMatch = nearbyPwd.match(/(?:密码|提取码)[：:\s]*([a-zA-Z0-9]{4})/);
                            if (pwdNearbyMatch && pwdNearbyMatch[1]) {
                                panPwd = pwdNearbyMatch[1];
                            }
                        }

                        links.push({
                            name: panPlatform,
                            url: panUrl,
                            platform: panPlatform,
                            password: panPwd
                        });
                    }
                }
            }

            return links;
        }

        // ===================== 首页内容 =====================

        function homeContent(filter) {
            var result = { class: CATEGORIES, list: [] };

            try {
                var html = fetch(BASE_URL + '/list');
                var resources = extractResourceList(html);

                for (var i = 0; i < resources.length && i < 18; i++) {
                    result.list.push({
                        vod_id: encodeVodId(resources[i].id, resources[i].title),
                        vod_name: resources[i].title || ('追新番-' + resources[i].id),
                        vod_pic: '',
                        vod_remarks: '☁️多网盘'
                    });
                }
            } catch (e) {
                print('>>> fanxinzhui homeContent ERROR: ' + e);
            }

            return result;
        }

        // ===================== 分类内容 =====================

        function categoryContent(tid, pg, filter, extend) {
            var page = parseInt(pg) || 1;
            var result = { list: [], page: page, pagecount: 1, limit: 20, total: 0 };

            try {
                var url = BASE_URL + '/list';
                if (tid && tid !== 'all') {
                    url += '?channel=' + encode(tid);
                }
                if (page > 1) {
                    url += (url.indexOf('?') > -1 ? '&' : '?') + 'p=' + page;
                }

                var html = fetch(url);
                var resources = extractResourceList(html);

                for (var i = 0; i < resources.length; i++) {
                    result.list.push({
                        vod_id: encodeVodId(resources[i].id, resources[i].title),
                        vod_name: resources[i].title || ('追新番-' + resources[i].id),
                        vod_pic: '',
                        vod_remarks: '☁️多网盘'
                    });
                }

                result.pagecount = resources.length >= 20 ? page + 1 : page;
            } catch (e) {
                print('>>> fanxinzhui categoryContent ERROR: ' + e);
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
                var url = BASE_URL + '/list?k=' + encode(key) + '&p=' + page;
                var html = fetch(url);
                var resources = extractResourceList(html);

                if (resources.length === 0) {
                    print('>>> fanxinzhui searchContent: no data for key=' + key);
                    return result;
                }

                for (var i = 0; i < resources.length; i++) {
                    result.list.push({
                        vod_id: encodeVodId(resources[i].id, resources[i].title),
                        vod_name: resources[i].title || ('追新番-' + resources[i].id),
                        vod_pic: '',
                        vod_remarks: '☁️多网盘'
                    });
                }

                result.pagecount = resources.length >= 20 ? page + 1 : page;
                print('>>> fanxinzhui searchContent: key=' + key + ' pg=' + page + ' count=' + result.list.length);
            } catch (e) {
                print('>>> fanxinzhui searchContent ERROR: ' + e);
            }

            return result;
        }

        // ===================== 详情内容 =====================

        function detailContent(ids) {
            var result = { list: [] };

            if (!ids) {
                print('>>> fanxinzhui detailContent: empty ids');
                return result;
            }

            var id = String(ids);
            var decoded = decodeVodId(id);
            print('>>> fanxinzhui detailContent: id=' + id.substring(0, 80));

            if (!decoded.resourceId) {
                result.list.push({
                    vod_id: id,
                    vod_name: decoded.title || '网盘资源',
                    vod_pic: '',
                    vod_remarks: '☁️网盘',
                    vod_play_from: '追新番',
                    vod_play_url: JSON.stringify([{ url: '', name: '网盘资源' }])
                });
                return result;
            }

            try {
                var html = fetch(BASE_URL + '/rr/' + decoded.resourceId);
                var title = decoded.title;
                if (!title || title.indexOf('追新番-') === 0) {
                    title = extractTitle(html);
                }

                var links = extractLinks(html);

                if (links.length > 0) {
                    // 按平台分组
                    var groups = {};
                    var order = [];
                    for (var i = 0; i < links.length; i++) {
                        var link = links[i];
                        if (!groups[link.platform]) {
                            groups[link.platform] = [];
                            order.push(link.platform);
                        }
                        var urlWithPwd = link.url;
                        if (link.password) {
                            urlWithPwd += '|' + link.password;
                        }
                        groups[link.platform].push({ url: urlWithPwd, name: link.name });
                    }

                    var playFromParts = [];
                    var playUrlParts = [];
                    for (var j = 0; j < order.length; j++) {
                        playFromParts.push(order[j]);
                        playUrlParts.push(JSON.stringify(groups[order[j]]));
                    }

                    result.list.push({
                        vod_id: id,
                        vod_name: title,
                        vod_pic: '',
                        vod_remarks: '☁️' + order.join('/'),
                        vod_play_from: playFromParts.join('$$$'),
                        vod_play_url: playUrlParts.join('$$$')
                    });
                    print('>>> fanxinzhui detailContent SUCCESS: ' + links.length + ' links');
                } else {
                    result.list.push({
                        vod_id: id,
                        vod_name: title,
                        vod_pic: '',
                        vod_remarks: '☁️网盘',
                        vod_play_from: '追新番',
                        vod_play_url: JSON.stringify([{ url: '', name: '未获取到链接' }])
                    });
                }
            } catch (e) {
                print('>>> fanxinzhui detailContent ERROR: ' + e);
                result.list.push({
                    vod_id: id,
                    vod_name: decoded.title || '网盘资源',
                    vod_pic: '',
                    vod_remarks: '☁️网盘',
                    vod_play_from: '追新番',
                    vod_play_url: JSON.stringify([{ url: '', name: '请求异常' }])
                });
            }

            return result;
        }

        // ===================== 播放内容 =====================

        function playerContent(vodId, flag, url) {
            print('>>> fanxinzhui playerContent: vodId=' + vodId.substring(0, 40));

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
            print('>>> fanxinzhui init: 追新番 JS蜘蛛 v1.0');
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
