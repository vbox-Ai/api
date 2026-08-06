/*
 * KK小站 JS 蜘蛛 v1.0
 * 适配 vbox-ios JSSpiderEngine (type:3 独立引擎)
 * 目标站: https://www.pioz.cn
 * 特点: SSR 分类页 + deep-search API + transfer API 获取网盘链接
 * 仅展示"影视短剧"分类（其余分类为音乐/学习/设计/文学，非视频资源）
 * 无需登录，无需加密签名
 */

var spider = {
    __jsEvalReturn: function() {

        var BASE_URL = 'https://www.pioz.cn';
        var UA = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36';
        var HEADER = { 'User-Agent': UA };

        // 网盘类型映射
        var CLOUD_MAP = {
            'quark': '夸克网盘',
            'baidu': '百度网盘',
            'xunlei': '迅雷云盘',
            '115': '115网盘',
            'aliyun': '阿里云盘',
            'uc': 'UC网盘'
        };

        // ===================== 工具函数 =====================

        function fetch(url, headers) {
            try {
                var resp = req(url, { headers: headers || HEADER });
                if (resp && resp.ok) {
                    return resp.content || '';
                }
                print('>>> pioz fetch FAIL: status=' + (resp ? resp.status : 'null') + ' url=' + url.substring(0, 80));
                return '';
            } catch (e) {
                print('>>> pioz fetch ERROR: ' + e);
                return '';
            }
        }

        function fetchJSON(url, headers) {
            var html = fetch(url, headers);
            if (!html) return null;
            try {
                return JSON.parse(html);
            } catch (e) {
                print('>>> pioz JSON parse ERROR: ' + e);
                return null;
            }
        }

        // 去除 HTML 标签
        function stripTags(str) {
            if (!str) return '';
            return String(str).replace(/<[^>]+>/g, '').replace(/&amp;/g, '&')
                .replace(/&lt;/g, '<').replace(/&gt;/g, '>').replace(/&quot;/g, '"')
                .replace(/&#39;/g, "'").replace(/&nbsp;/g, ' ').trim();
        }

        // URL 编码（兼容中文）
        function encode(str) {
            return encodeURIComponent(String(str));
        }

        // ===================== 首页内容 =====================

        function homeContent(filter) {
            var result = { class: [], list: [] };

            // 只返回"影视短剧"分类（其余为非视频资源）
            result.class.push({
                type_id: '影视短剧',
                type_name: '影视短剧'
            });

            // 获取影视短剧分类第一页作为推荐列表
            try {
                var html = fetch(BASE_URL + '/category/' + encode('影视短剧') + '?p=1');
                var items = parseCategoryHTML(html);
                if (items.length > 0) {
                    result.list = items;
                }
            } catch (e) {
                print('>>> pioz homeContent list ERROR: ' + e);
            }

            return result;
        }

        // ===================== 分类内容 =====================

        function categoryContent(tid, pg, filter, extend) {
            var page = parseInt(pg) || 1;
            var result = { list: [], page: page, pagecount: 1, limit: 20, total: 0 };

            try {
                var url = BASE_URL + '/category/' + encode(tid) + '?p=' + page;
                var html = fetch(url);

                if (!html) {
                    print('>>> pioz categoryContent: empty html for tid=' + tid + ' pg=' + page);
                    return result;
                }

                // 提取总资源数
                var totalMatch = html.match(/共\s*<span>(\d+)<\/span>\s*条资源/);
                if (totalMatch) {
                    result.total = parseInt(totalMatch[1]);
                    result.pagecount = Math.ceil(result.total / 20);
                }

                result.list = parseCategoryHTML(html);
                print('>>> pioz categoryContent: tid=' + tid + ' pg=' + page + ' count=' + result.list.length);
            } catch (e) {
                print('>>> pioz categoryContent ERROR: ' + e);
            }

            return result;
        }

        // 解析分类页 HTML，提取视频列表
        function parseCategoryHTML(html) {
            var items = [];
            if (!html) return items;

            // 匹配每个 file-item 块
            // 结构: <div class="file-item ..."> ... <a href="/detail/584941" ...> ... <span title="标题">标题</span> ... </a> ... 夸克网盘 ... </div>
            var blockRegex = /<div class="file-item[\s\S]*?<\/div>\s*<\/div>\s*<\/div>/g;
            var blocks = html.match(blockRegex);

            if (!blocks) {
                // 降级：用简单正则逐条提取
                var simpleRegex = /href="\/detail\/(\d+)"[\s\S]*?title="([^"]+)"/g;
                var match;
                while ((match = simpleRegex.exec(html)) !== null) {
                    var title = stripTags(match[2]);
                    if (title && title !== '分享' && title !== '加入群组') {
                        items.push({
                            vod_id: match[1],
                            vod_name: title,
                            vod_pic: '',
                            vod_remarks: ''
                        });
                    }
                }
                return items;
            }

            for (var i = 0; i < blocks.length; i++) {
                var block = blocks[i];

                // 提取详情页 ID 和标题
                var idMatch = block.match(/href="\/detail\/(\d+)"/);
                var titleMatch = block.match(/title="([^"]+)"/);

                if (!idMatch || !titleMatch) continue;

                var title = stripTags(titleMatch[1]);
                // 跳过非资源标题
                if (!title || title === '分享' || title === '加入群组') continue;

                // 提取网盘来源
                var cloudMatch = block.match(/text-center text-sm text-gray-400">([^<]+)<\/div>/);
                var remarks = '';
                if (cloudMatch) {
                    remarks = cloudMatch[1].trim();
                }

                items.push({
                    vod_id: idMatch[1],
                    vod_name: title,
                    vod_pic: '',
                    vod_remarks: remarks
                });
            }

            return items;
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
                var url = BASE_URL + '/api/deep-search?kw=' + encode(key);
                var data = fetchJSON(url);

                if (!data || data.code !== 0 || !data.results) {
                    print('>>> pioz searchContent: no data for key=' + key);
                    return result;
                }

                var results = data.results;
                for (var i = 0; i < results.length; i++) {
                    var r = results[i];
                    // 跳过已知失效资源（status=1 表示失效）
                    if (r.status === 1) continue;

                    var cloudName = CLOUD_MAP[r.cloud_type] || r.cloud_type || '网盘';

                    result.list.push({
                        vod_id: r.id,
                        vod_name: stripTags(r.title),
                        vod_pic: '',
                        vod_remarks: cloudName
                    });
                }

                result.pagecount = Math.ceil(result.list.length / 20);
                print('>>> pioz searchContent: key=' + key + ' count=' + result.list.length);
            } catch (e) {
                print('>>> pioz searchContent ERROR: ' + e);
            }

            return result;
        }

        // ===================== 详情内容 =====================

        function detailContent(ids) {
            var result = { list: [] };

            if (!ids) {
                print('>>> pioz detailContent: empty ids');
                return result;
            }

            var id = String(ids);
            print('>>> pioz detailContent: id=' + id);

            // 复合 ID（来自搜索，含 "_"）：无详情页可访问，返回最小信息
            if (id.indexOf('_') !== -1) {
                result.list.push({
                    vod_id: id,
                    vod_name: '搜索资源',
                    vod_pic: '',
                    vod_play_from: 'KK小站',
                    vod_play_url: '获取链接$' + id
                });
                return result;
            }

            // 数字 ID（来自分类页）：请求详情页 HTML
            try {
                var html = fetch(BASE_URL + '/detail/' + id);
                if (!html) {
                    print('>>> pioz detailContent: empty html for id=' + id);
                    result.list.push({
                        vod_id: id,
                        vod_name: '资源详情',
                        vod_pic: '',
                        vod_play_from: 'KK小站',
                        vod_play_url: '获取链接$' + id
                    });
                    return result;
                }

                // 提取标题
                var titleMatch = html.match(/<h1[^>]*>([^<]+)<\/h1>/);
                var title = titleMatch ? stripTags(titleMatch[1]) : '资源详情';

                // 提取网盘来源
                var cloudMatch = html.match(/<span>(夸克网盘|百度网盘|迅雷云盘|115网盘|阿里云盘|UC网盘)<\/span>/);
                var cloud = cloudMatch ? cloudMatch[1] : '网盘';

                // 提取分类标签
                var catMatch = html.match(/<span class="px-2 py-0\.5 bg-gray-700 rounded-full text-xs[^"]*">([^<]+)<\/span>/);
                var category = catMatch ? stripTags(catMatch[1]) : '';

                // 提取日期
                var dateMatch = html.match(/<span>(\d{4}-\d{2}-\d{2}\s+\d{2}:\d{2})<\/span>/);
                var date = dateMatch ? dateMatch[1] : '';

                var remarks = cloud;
                if (date) remarks += ' · ' + date;

                result.list.push({
                    vod_id: id,
                    vod_name: title,
                    vod_pic: '',
                    vod_remarks: remarks,
                    vod_area: category,
                    vod_play_from: 'KK小站',
                    vod_play_url: '获取链接$' + id
                });

                print('>>> pioz detailContent SUCCESS: title=' + title.substring(0, 40));
            } catch (e) {
                print('>>> pioz detailContent ERROR: ' + e);
                // 降级：返回最小信息，确保播放流程可用
                result.list.push({
                    vod_id: id,
                    vod_name: '资源详情',
                    vod_pic: '',
                    vod_play_from: 'KK小站',
                    vod_play_url: '获取链接$' + id
                });
            }

            return result;
        }

        // ===================== 播放内容 =====================

        function playerContent(vodId, flag, url) {
            print('>>> pioz playerContent: vodId=' + vodId + ' flag=' + flag + ' url=' + url);

            // url 参数是 vod_play_url 中 "$" 后面的部分，即资源 ID
            var resourceId = url || vodId;

            try {
                var apiurl = BASE_URL + '/api/transfer?id=' + encode(resourceId);
                var data = fetchJSON(apiurl, {
                    'User-Agent': UA,
                    'Referer': BASE_URL + '/detail/' + resourceId
                });

                if (!data) {
                    print('>>> pioz playerContent: no response data');
                    return { parse: 0, url: '' };
                }

                if (data.success && data.data && data.data.url) {
                    var panUrl = data.data.url;
                    print('>>> pioz playerContent SUCCESS: ' + panUrl.substring(0, 60));
                    return {
                        parse: 0,
                        url: panUrl,
                        header: { 'User-Agent': UA }
                    };
                }

                // 资源已过期或其他错误
                var errMsg = data.error || '获取链接失败';
                print('>>> pioz playerContent FAIL: ' + errMsg);
                return { parse: 0, url: '' };
            } catch (e) {
                print('>>> pioz playerContent ERROR: ' + e);
                return { parse: 0, url: '' };
            }
        }

        // ===================== 初始化 =====================

        function init(config) {
            print('>>> pioz init: KK小站 JS蜘蛛 v1.0');
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
