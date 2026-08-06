/*
 * 泽索搜 JS 蜘蛛 v1.0
 * 适配 vbox-ios JSSpiderEngine (type:3 独立引擎)
 * 目标站: https://zreso.cn
 * 特点: SSR 分类页 + JSON 搜索 API + wash API 获取网盘链接
 * 仅展示视频分类（短剧、影视专区）
 * 网盘类型：夸克网盘、百度网盘、UC网盘、迅雷云盘
 * 无需登录，无需加密签名
 *
 * 网盘蜘蛛源约定：
 *   - vod_remarks 以 "☁️" 开头 → 标识为网盘资源，激活网盘UI
 *   - detailContent 的 vod_play_url 返回 JSON 数组 [{"url":"网盘链接","name":"网盘名"}]
 *   - vod_id 为非 URL 的纯数字或 wash_xxx 格式
 */

var spider = {
    __jsEvalReturn: function() {

        var BASE_URL = 'https://zreso.cn';
        var UA = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36';
        var HEADER = { 'User-Agent': UA };

        // 网盘图标到名称映射
        var CLOUD_ICON_MAP = {
            'quark.png': '夸克网盘',
            'baidu.ico': '百度网盘',
            'uc-logo': 'UC网盘',
            'xunlei': '迅雷云盘'
        };

        // 网盘类型名称映射（搜索API返回的 cloud_type_name）
        var CLOUD_NAME_MAP = {
            '夸克网盘': '夸克网盘',
            '百度网盘': '百度网盘',
            'UC网盘': 'UC网盘',
            '迅雷云盘': '迅雷云盘'
        };

        // 视频分类
        var VIDEO_CATEGORIES = [
            { type_id: '短剧', type_name: '短剧' },
            { type_id: '影视专区', type_name: '影视专区' }
        ];

        // ===================== 工具函数 =====================

        function fetch(url, headers) {
            try {
                var resp = req(url, { headers: headers || HEADER });
                if (resp && resp.ok) {
                    return resp.content || '';
                }
                print('>>> zreso fetch FAIL: status=' + (resp ? resp.status : 'null') + ' url=' + url.substring(0, 80));
                return '';
            } catch (e) {
                print('>>> zreso fetch ERROR: ' + e);
                return '';
            }
        }

        function fetchJSON(url, headers) {
            var html = fetch(url, headers);
            if (!html) return null;
            try {
                return JSON.parse(html);
            } catch (e) {
                print('>>> zreso JSON parse ERROR: ' + e);
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
        function inferCloudName(url) {
            if (!url) return '网盘';
            if (url.indexOf('pan.quark.cn') !== -1 || url.indexOf('pan.quarks.cn') !== -1) return '夸克网盘';
            if (url.indexOf('pan.baidu.com') !== -1) return '百度网盘';
            if (url.indexOf('pan.xunlei.com') !== -1) return '迅雷云盘';
            if (url.indexOf('115.com') !== -1) return '115网盘';
            if (url.indexOf('aliyundrive.com') !== -1 || url.indexOf('alipan.com') !== -1) return '阿里云盘';
            if (url.indexOf('uc.cn') !== -1 || url.indexOf('ucloud.cn') !== -1) return 'UC网盘';
            return '网盘';
        }

        // 修复 quarks.cn → quark.cn（详情页 HTML 中的域名有误）
        function fixPanUrl(url) {
            if (!url) return url;
            return url.replace('pan.quarks.cn', 'pan.quark.cn');
        }

        // 从图标文件名推断网盘名称
        function inferCloudFromIcon(html, blockStart, blockEnd) {
            var block = html.substring(blockStart, blockEnd);
            for (var icon in CLOUD_ICON_MAP) {
                if (block.indexOf(icon) !== -1) {
                    return CLOUD_ICON_MAP[icon];
                }
            }
            return '网盘';
        }

        // ===================== 首页内容 =====================

        function homeContent(filter) {
            var result = { class: [], list: [] };

            // 返回视频分类
            for (var i = 0; i < VIDEO_CATEGORIES.length; i++) {
                result.class.push(VIDEO_CATEGORIES[i]);
            }

            // 获取短剧分类第一页作为推荐列表
            try {
                var html = fetch(BASE_URL + '/category/' + encode('短剧'));
                var items = parseCategoryHTML(html);
                if (items.length > 0) {
                    result.list = items;
                }
            } catch (e) {
                print('>>> zreso homeContent list ERROR: ' + e);
            }

            return result;
        }

        // ===================== 分类内容 =====================

        function categoryContent(tid, pg, filter, extend) {
            var page = parseInt(pg) || 1;
            var result = { list: [], page: page, pagecount: 1, limit: 20, total: 0 };

            try {
                // 分页 URL：第1页 /category/短剧，第2页 /category/短剧/2
                var url;
                if (page <= 1) {
                    url = BASE_URL + '/category/' + encode(tid);
                } else {
                    url = BASE_URL + '/category/' + encode(tid) + '/' + page;
                }

                var html = fetch(url);
                if (!html) {
                    print('>>> zreso categoryContent: empty html for tid=' + tid + ' pg=' + page);
                    return result;
                }

                // 提取总资源数
                var totalMatch = html.match(/共(\d+)条/);
                if (totalMatch) {
                    result.total = parseInt(totalMatch[1]);
                    result.pagecount = Math.ceil(result.total / 20);
                }

                result.list = parseCategoryHTML(html);
                print('>>> zreso categoryContent: tid=' + tid + ' pg=' + page + ' count=' + result.list.length);
            } catch (e) {
                print('>>> zreso categoryContent ERROR: ' + e);
            }

            return result;
        }

        // 解析分类页 HTML，提取资源列表
        function parseCategoryHTML(html) {
            var items = [];
            if (!html) return items;

            // 匹配 detail 链接和标题
            // 结构: <a href="/detail/129182">标题</a>
            var linkRegex = /href="\/detail\/(\d+)"[^>]*>([^<]+)/g;
            var match;
            while ((match = linkRegex.exec(html)) !== null) {
                var id = match[1];
                var title = stripTags(match[2]);

                if (!title || title.length < 2) continue;

                // 尝试提取附近的网盘图标
                var cloudName = '网盘';
                var searchStart = Math.max(0, match.index - 200);
                var searchEnd = Math.min(html.length, match.index + 200);
                var block = html.substring(searchStart, searchEnd);
                for (var icon in CLOUD_ICON_MAP) {
                    if (block.indexOf(icon) !== -1) {
                        cloudName = CLOUD_ICON_MAP[icon];
                        break;
                    }
                }

                items.push({
                    vod_id: id,
                    vod_name: title,
                    vod_pic: '',
                    vod_remarks: '☁️' + cloudName
                });
            }

            // 去重（同ID只保留第一条）
            var seen = {};
            var unique = [];
            for (var i = 0; i < items.length; i++) {
                if (!seen[items[i].vod_id]) {
                    seen[items[i].vod_id] = true;
                    unique.push(items[i]);
                }
            }

            return unique;
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
                var url = BASE_URL + '/api/search?q=' + encode(key) + '&page=' + page;
                var data = fetchJSON(url);

                if (!data || !data.ok || !data.data || !data.data.results) {
                    print('>>> zreso searchContent: no data for key=' + key);
                    return result;
                }

                var results = data.data.results;
                for (var i = 0; i < results.length; i++) {
                    var r = results[i];

                    // 跳过失效资源
                    if (r.status === 'invalid' || r.status === 'dead') continue;

                    var cloudName = r.cloud_type_name || '网盘';
                    if (CLOUD_NAME_MAP[cloudName]) {
                        cloudName = CLOUD_NAME_MAP[cloudName];
                    }

                    // 从 first_url 提取 wash token
                    // first_url = "/api/wash?t=8cfd0b74-415e-44a5-bf9f-3da1f3c20b7a"
                    var washToken = '';
                    if (r.first_url) {
                        var tokenMatch = r.first_url.match(/wash\?t=([a-f0-9-]+)/);
                        if (tokenMatch) {
                            washToken = tokenMatch[1];
                        }
                    }

                    // vod_id 用 wash_ 前缀标识搜索来源
                    var vodId = washToken ? ('wash_' + washToken) : ('search_' + i);

                    result.list.push({
                        vod_id: vodId,
                        vod_name: stripTags(r.title),
                        vod_pic: '',
                        vod_remarks: '☁️' + cloudName
                    });
                }

                result.pagecount = Math.ceil(result.list.length / 20);
                if (result.pagecount < 1) result.pagecount = 1;
                print('>>> zreso searchContent: key=' + key + ' count=' + result.list.length);
            } catch (e) {
                print('>>> zreso searchContent ERROR: ' + e);
            }

            return result;
        }

        // ===================== 详情内容 =====================
        // 网盘蜘蛛源约定：
        //   vod_remarks 以 "☁️" 开头 → 标识为网盘资源
        //   vod_play_url 返回 JSON 数组 [{"url":"网盘链接","name":"网盘名"}]

        function detailContent(ids) {
            var result = { list: [] };

            if (!ids) {
                print('>>> zreso detailContent: empty ids');
                return result;
            }

            var id = String(ids);
            print('>>> zreso detailContent: id=' + id);

            // wash_ 前缀（来自搜索）：调用 wash API 获取真实网盘链接
            if (id.indexOf('wash_') === 0) {
                var token = id.substring(5);
                var panLinks = getPanLinksByWash(token);

                if (panLinks.length > 0) {
                    result.list.push({
                        vod_id: id,
                        vod_name: '搜索资源',
                        vod_pic: '',
                        vod_remarks: '☁️' + (panLinks[0].name || '网盘'),
                        vod_play_from: '泽索搜',
                        vod_play_url: JSON.stringify(panLinks)
                    });
                    print('>>> zreso detailContent(wash) SUCCESS: links=' + panLinks.length);
                } else {
                    result.list.push({
                        vod_id: id,
                        vod_name: '搜索资源',
                        vod_pic: '',
                        vod_remarks: '☁️网盘',
                        vod_play_from: '泽索搜',
                        vod_play_url: JSON.stringify([{ url: '', name: '网盘资源' }])
                    });
                }
                return result;
            }

            // search_ 前缀（搜索结果无 wash token）：返回占位数据
            if (id.indexOf('search_') === 0) {
                result.list.push({
                    vod_id: id,
                    vod_name: '搜索资源',
                    vod_pic: '',
                    vod_remarks: '☁️网盘',
                    vod_play_from: '泽索搜',
                    vod_play_url: JSON.stringify([{ url: '', name: '网盘资源' }])
                });
                return result;
            }

            // 数字 ID（来自分类页）：请求详情页 HTML 提取网盘链接
            try {
                var html = fetch(BASE_URL + '/detail/' + id);
                var title = '资源详情';
                var cloudName = '网盘';

                if (html) {
                    // 提取标题
                    var titleMatch = html.match(/class="detail-title">([^<]+)/);
                    title = titleMatch ? stripTags(titleMatch[1]) : '资源详情';

                    // 提取网盘类型图标
                    for (var icon in CLOUD_ICON_MAP) {
                        if (html.indexOf(icon) !== -1) {
                            cloudName = CLOUD_ICON_MAP[icon];
                            break;
                        }
                    }
                }

                // 从详情页 HTML 提取网盘链接
                var panLinks = getPanLinksFromDetailHTML(html);

                if (panLinks.length > 0) {
                    result.list.push({
                        vod_id: id,
                        vod_name: title,
                        vod_pic: '',
                        vod_remarks: '☁️' + (panLinks[0].name || cloudName),
                        vod_play_from: '泽索搜',
                        vod_play_url: JSON.stringify(panLinks)
                    });
                    print('>>> zreso detailContent(detail) SUCCESS: title=' + title.substring(0, 40) + ' links=' + panLinks.length);
                } else {
                    // 详情页未找到链接，返回占位数据
                    print('>>> zreso detailContent: no pan links found for id=' + id);
                    result.list.push({
                        vod_id: id,
                        vod_name: title,
                        vod_pic: '',
                        vod_remarks: '☁️' + cloudName,
                        vod_play_from: '泽索搜',
                        vod_play_url: JSON.stringify([{ url: '', name: cloudName }])
                    });
                }
            } catch (e) {
                print('>>> zreso detailContent ERROR: ' + e);
                result.list.push({
                    vod_id: id,
                    vod_name: '资源详情',
                    vod_pic: '',
                    vod_remarks: '☁️网盘',
                    vod_play_from: '泽索搜',
                    vod_play_url: JSON.stringify([{ url: '', name: '网盘资源' }])
                });
            }

            return result;
        }

        // 通过 wash API 获取网盘链接
        // 返回 [{"url":"网盘链接","name":"网盘名"}]
        function getPanLinksByWash(token) {
            var links = [];
            try {
                var url = BASE_URL + '/api/wash?t=' + encode(token);
                var data = fetchJSON(url, {
                    'User-Agent': UA,
                    'Referer': BASE_URL + '/search'
                });

                if (!data) {
                    print('>>> zreso getPanLinksByWash: no response for token=' + token);
                    return links;
                }

                if (data.ok && data.raw_url) {
                    var panUrl = fixPanUrl(data.raw_url);
                    var panName = inferCloudName(panUrl);
                    links.push({ url: panUrl, name: panName });
                    print('>>> zreso getPanLinksByWash SUCCESS: ' + panUrl.substring(0, 60));
                } else {
                    print('>>> zreso getPanLinksByWash FAIL: ok=' + data.ok);
                }
            } catch (e) {
                print('>>> zreso getPanLinksByWash ERROR: ' + e);
            }
            return links;
        }

        // 从详情页 HTML 提取网盘链接
        // 结构: <a href="https://pan.quarks.cn/s/xxx" ... class="btn-download">
        function getPanLinksFromDetailHTML(html) {
            var links = [];
            if (!html) return links;

            try {
                // 匹配 btn-download 链接中的网盘 URL
                var linkRegex = /href="(https?:\/\/pan\.[a-z.]+\/s\/[a-zA-Z0-9_]+)"[^>]*class="[^"]*btn-download/g;
                var match;
                while ((match = linkRegex.exec(html)) !== null) {
                    var panUrl = fixPanUrl(match[1]);
                    var panName = inferCloudName(panUrl);
                    links.push({ url: panUrl, name: panName });
                    print('>>> zreso getPanLinksFromDetailHTML: found ' + panUrl.substring(0, 60));
                }

                // 降级：匹配任意网盘分享链接
                if (links.length === 0) {
                    var fallbackRegex = /https?:\/\/(pan\.(?:quark|baidu|xunlei|uc|115|aliyundrive|alipan)\.[a-z]+\/s\/[a-zA-Z0-9_]+)/g;
                    while ((match = fallbackRegex.exec(html)) !== null) {
                        var url = fixPanUrl(match[1]);
                        var name = inferCloudName(url);
                        links.push({ url: url, name: name });
                    }
                }

                // 去重
                var seen = {};
                var unique = [];
                for (var i = 0; i < links.length; i++) {
                    if (!seen[links[i].url]) {
                        seen[links[i].url] = true;
                        unique.push(links[i]);
                    }
                }
                links = unique;
            } catch (e) {
                print('>>> zreso getPanLinksFromDetailHTML ERROR: ' + e);
            }
            return links;
        }

        // ===================== 播放内容 =====================
        // 保留作为播放降级路径

        function playerContent(vodId, flag, url) {
            print('>>> zreso playerContent: vodId=' + vodId + ' flag=' + flag + ' url=' + url);

            var id = vodId;
            // 如果 url 是 wash_token 或数字ID，用作 id
            if (url && (url.indexOf('wash_') === 0 || /^\d+$/.test(url))) {
                id = url;
            }

            try {
                var panLinks = [];

                if (id.indexOf('wash_') === 0) {
                    var token = id.substring(5);
                    panLinks = getPanLinksByWash(token);
                } else if (/^\d+$/.test(id)) {
                    var html = fetch(BASE_URL + '/detail/' + id);
                    panLinks = getPanLinksFromDetailHTML(html);
                }

                if (panLinks.length > 0 && panLinks[0].url) {
                    return {
                        parse: 0,
                        url: panLinks[0].url,
                        header: { 'User-Agent': UA }
                    };
                }
                return { parse: 0, url: '' };
            } catch (e) {
                print('>>> zreso playerContent ERROR: ' + e);
                return { parse: 0, url: '' };
            }
        }

        // ===================== 初始化 =====================

        function init(config) {
            print('>>> zreso init: 泽索搜 JS蜘蛛 v1.0');
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
