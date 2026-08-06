/*
 * KK小站 JS 蜘蛛 v2.0
 * 适配 vbox-ios JSSpiderEngine (type:3 独立引擎)
 * 目标站: https://www.pioz.cn
 * 特点: SSR 分类页 + deep-search API + transfer API 获取网盘链接
 * 仅展示"影视短剧"分类（其余分类为音乐/学习/设计/文学，非视频资源）
 * 无需登录，无需加密签名
 *
 * v2.0: 网盘蜘蛛源约定适配
 *   - vod_remarks 以 "☁️" 开头 → 标识为网盘资源，激活网盘UI
 *   - detailContent 的 vod_play_url 返回 JSON 数组 [{"url":"网盘链接","name":"网盘名"}]
 *     → Swift 端 resolveCloudPlayFromSpider 解析后填充网盘UI
 *   - playerContent 保留作为播放降级路径
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
                            vod_remarks: '☁️网盘'
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
                var cloudName = '网盘';
                if (cloudMatch) {
                    cloudName = cloudMatch[1].trim();
                }

                items.push({
                    vod_id: idMatch[1],
                    vod_name: title,
                    vod_pic: '',
                    vod_remarks: '☁️' + cloudName
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
                        vod_remarks: '☁️' + cloudName
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
        // 网盘蜘蛛源约定：
        //   vod_remarks 以 "☁️" 开头 → 标识为网盘资源
        //   vod_play_url 返回 JSON 数组 [{"url":"网盘链接","name":"网盘名"}]
        //   → Swift resolveCloudPlayFromSpider 解析后填充网盘UI

        function detailContent(ids) {
            var result = { list: [] };

            if (!ids) {
                print('>>> pioz detailContent: empty ids');
                return result;
            }

            var id = String(ids);
            print('>>> pioz detailContent: id=' + id);

            // 复合 ID（来自搜索，含 "_"）：无详情页可访问，直接调 transfer API
            if (id.indexOf('_') !== -1) {
                var panLinks1 = getPanLinks(id);
                if (panLinks1.length > 0) {
                    result.list.push({
                        vod_id: id,
                        vod_name: '搜索资源',
                        vod_pic: '',
                        vod_remarks: '☁️' + (panLinks1[0].name || '网盘'),
                        vod_play_from: 'KK小站',
                        vod_play_url: JSON.stringify(panLinks1)
                    });
                } else {
                    result.list.push({
                        vod_id: id,
                        vod_name: '搜索资源',
                        vod_pic: '',
                        vod_remarks: '☁️网盘',
                        vod_play_from: 'KK小站',
                        vod_play_url: JSON.stringify([{ url: '', name: '网盘资源' }])
                    });
                }
                return result;
            }

            // 数字 ID（来自分类页）：请求详情页 HTML 获取标题等信息
            try {
                var html = fetch(BASE_URL + '/detail/' + id);
                var title = '资源详情';
                var cloud = '网盘';

                if (html) {
                    // 提取标题
                    var titleMatch = html.match(/<h1[^>]*>([^<]+)<\/h1>/);
                    title = titleMatch ? stripTags(titleMatch[1]) : '资源详情';

                    // 提取网盘来源
                    var cloudMatch = html.match(/<span>(夸克网盘|百度网盘|迅雷云盘|115网盘|阿里云盘|UC网盘)<\/span>/);
                    cloud = cloudMatch ? cloudMatch[1] : '网盘';
                }

                // 提取分类标签
                var category = '';
                if (html) {
                    var catMatch = html.match(/<span class="px-2 py-0\.5 bg-gray-700 rounded-full text-xs[^"]*">([^<]+)<\/span>/);
                    category = catMatch ? stripTags(catMatch[1]) : '';
                }

                // 提取日期
                var date = '';
                if (html) {
                    var dateMatch = html.match(/<span>(\d{4}-\d{2}-\d{2}\s+\d{2}:\d{2})<\/span>/);
                    date = dateMatch ? dateMatch[1] : '';
                }

                // 调用 transfer API 获取真实网盘链接
                var panLinks = getPanLinks(id);

                if (panLinks.length > 0) {
                    result.list.push({
                        vod_id: id,
                        vod_name: title,
                        vod_pic: '',
                        vod_remarks: '☁️' + cloud,
                        vod_area: category,
                        vod_play_from: 'KK小站',
                        vod_play_url: JSON.stringify(panLinks)
                    });
                    print('>>> pioz detailContent SUCCESS: title=' + title.substring(0, 40) + ' links=' + panLinks.length);
                } else {
                    // transfer API 失败，返回占位数据（仍保持网盘标识）
                    print('>>> pioz detailContent: transfer API returned no links for id=' + id);
                    result.list.push({
                        vod_id: id,
                        vod_name: title,
                        vod_pic: '',
                        vod_remarks: '☁️' + cloud,
                        vod_area: category,
                        vod_play_from: 'KK小站',
                        vod_play_url: JSON.stringify([{ url: '', name: cloud }])
                    });
                }
            } catch (e) {
                print('>>> pioz detailContent ERROR: ' + e);
                // 降级：返回带网盘标识的占位数据
                result.list.push({
                    vod_id: id,
                    vod_name: '资源详情',
                    vod_pic: '',
                    vod_remarks: '☁️网盘',
                    vod_play_from: 'KK小站',
                    vod_play_url: JSON.stringify([{ url: '', name: '网盘资源' }])
                });
            }

            return result;
        }

        // 调用 transfer API 获取网盘链接
        // 返回 [{"url":"网盘链接","name":"网盘名"}] 格式的数组
        function getPanLinks(resourceId) {
            var links = [];
            try {
                var apiurl = BASE_URL + '/api/transfer?id=' + encode(resourceId);
                var data = fetchJSON(apiurl, {
                    'User-Agent': UA,
                    'Referer': BASE_URL + '/detail/' + resourceId
                });

                if (!data) {
                    print('>>> pioz getPanLinks: no response data for id=' + resourceId);
                    return links;
                }

                if (data.success && data.data && data.data.url) {
                    var panUrl = data.data.url;
                    // 从详情页或 API 推断网盘名称
                    var panName = '网盘';
                    if (data.data.cloud_type) {
                        panName = CLOUD_MAP[data.data.cloud_type] || data.data.cloud_type;
                    } else {
                        // 从 URL 推断网盘类型
                        if (panUrl.indexOf('pan.quark.cn') !== -1) panName = '夸克网盘';
                        else if (panUrl.indexOf('pan.baidu.com') !== -1) panName = '百度网盘';
                        else if (panUrl.indexOf('pan.xunlei.com') !== -1) panName = '迅雷云盘';
                        else if (panUrl.indexOf('115.com') !== -1) panName = '115网盘';
                        else if (panUrl.indexOf('aliyundrive.com') !== -1 || panUrl.indexOf('alipan.com') !== -1) panName = '阿里云盘';
                        else if (panUrl.indexOf('uc.cn') !== -1 || panUrl.indexOf('ucloud.cn') !== -1) panName = 'UC网盘';
                    }
                    links.push({ url: panUrl, name: panName });
                    print('>>> pioz getPanLinks SUCCESS: ' + panUrl.substring(0, 60));
                } else {
                    print('>>> pioz getPanLinks FAIL: ' + (data.error || 'no url'));
                }
            } catch (e) {
                print('>>> pioz getPanLinks ERROR: ' + e);
            }
            return links;
        }

        // ===================== 播放内容 =====================
        // 保留作为播放降级路径（网盘UI不直接调用 playerContent，
        // 但如果走普通播放流程时仍可使用）

        function playerContent(vodId, flag, url) {
            print('>>> pioz playerContent: vodId=' + vodId + ' flag=' + flag + ' url=' + url);

            var resourceId = vodId;
            // 如果 url 是数字ID，用作 resourceId
            if (url && /^\d+$/.test(url)) {
                resourceId = url;
            }

            try {
                var links = getPanLinks(resourceId);
                if (links.length > 0 && links[0].url) {
                    return {
                        parse: 0,
                        url: links[0].url,
                        header: { 'User-Agent': UA }
                    };
                }
                return { parse: 0, url: '' };
            } catch (e) {
                print('>>> pioz playerContent ERROR: ' + e);
                return { parse: 0, url: '' };
            }
        }

        // ===================== 初始化 =====================

        function init(config) {
            print('>>> pioz init: KK小站 JS蜘蛛 v2.0');
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
