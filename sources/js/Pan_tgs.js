/*
 * TG搜索 JS 蜘蛛 v1.0
 * 适配 vbox-ios JSSpiderEngine (type:3 独立引擎)
 * 目标站: Telegram 频道 Web 预览页 (t.me/s/{channel})
 * 特点: 多频道并行搜索，通过 vbox.ltd 代理访问，自动提取网盘直链
 * 支持网盘：夸克网盘、百度网盘、阿里云盘、UC网盘、115网盘、123云盘、天翼云盘、迅雷云盘、BT磁力
 * 无需登录，无需 Telegram 客户端
 *
 * 网盘蜘蛛源约定：
 *   - vod_remarks 以 "☁️" 开头 → 标识为网盘资源，激活网盘UI
 *   - detailContent 的 vod_play_url 返回 JSON 数组 [{"url":"网盘链接","name":"网盘名"}]
 *   - vod_id 编码格式:
 *     搜索/浏览结果: {title}|||tg|||{channel}_{messageId}|||{encodeURIComponent(JSON.stringify(links))}
 *     links 格式: [{"url":"网盘链接","name":"网盘名","pwd":"提取码"}, ...]
 *
 * 频道配置（通过 ext 字段）:
 *   - 留空: 使用默认频道
 *   - "ch1,ch2,ch3": 逗号分隔的频道名
 *   - "名称1@ch1&名称2@ch2": 名称@频道 格式（&分隔）
 */

var spider = {
    __jsEvalReturn: function() {

        // 代理地址（vbox.ltd URL 转发代理）
        var PROXY_URL = 'https://vbox.ltd/?token=199114&url=';

        // 默认频道列表
        var DEFAULT_CHANNELS = [
            { name: 'UC夸克资源', id: 'ucquark' },
            { name: '夸克分享', id: 'quarkshare' },
            { name: '阿里分享', id: 'shareAliyun' },
            { name: '豆儿盘', id: 'douerpan' }
        ];

        // 运行时频道列表（可被 init 覆盖）
        var CHANNELS = DEFAULT_CHANNELS.slice();

        var UA = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36';
        var HEADER = {
            'User-Agent': UA
        };

        // ===================== 工具函数 =====================

        function fetch(url, headers) {
            try {
                var resp = req(url, { headers: headers || HEADER, timeout: 15000 });
                if (resp && resp.ok) {
                    return resp.content || '';
                }
                print('>>> tgs fetch FAIL: status=' + (resp ? resp.status : 'null') + ' url=' + url.substring(0, 80));
                return '';
            } catch (e) {
                print('>>> tgs fetch ERROR: ' + e);
                return '';
            }
        }

        function stripTags(str) {
            if (!str) return '';
            return String(str)
                .replace(/<[^>]+>/g, '')
                .replace(/&amp;/g, '&')
                .replace(/&lt;/g, '<')
                .replace(/&gt;/g, '>')
                .replace(/&quot;/g, '"')
                .replace(/&#39;/g, "'")
                .replace(/&nbsp;/g, ' ')
                .trim();
        }

        // 构建代理 URL
        function buildProxyUrl(targetUrl) {
            return PROXY_URL + encodeURIComponent(targetUrl);
        }

        // 构建 Telegram 频道搜索 URL
        function buildTgSearchUrl(channelId, keyword) {
            return 'https://t.me/s/' + channelId + '?q=' + encodeURIComponent(keyword);
        }

        // 构建 Telegram 频道浏览 URL
        function buildTgBrowseUrl(channelId) {
            return 'https://t.me/s/' + channelId;
        }

        // 从 URL 推断网盘名称
        function inferPanName(url) {
            if (!url) return '';
            if (url.indexOf('pan.quark.cn') !== -1) return '夸克网盘';
            if (url.indexOf('pan.baidu.com') !== -1) return '百度网盘';
            if (url.indexOf('alipan.com') !== -1 || url.indexOf('aliyundrive.com') !== -1) return '阿里云盘';
            if (url.indexOf('drive.uc.cn') !== -1 || url.indexOf('uc.cn') !== -1) return 'UC网盘';
            if (url.indexOf('115.com') !== -1) return '115网盘';
            if (url.indexOf('123pan.com') !== -1 || url.indexOf('123684.com') !== -1 || url.indexOf('123912.com') !== -1) return '123云盘';
            if (url.indexOf('cloud.189.cn') !== -1) return '天翼云盘';
            if (url.indexOf('pan.xunlei.com') !== -1) return '迅雷云盘';
            if (url.indexOf('caiyun.139.com') !== -1 || url.indexOf('yun.139.com') !== -1) return '移动云盘';
            if (url.indexOf('magnet:') !== -1) return 'BT磁力';
            return '';
        }

        // 判断 URL 是否为网盘直链
        function isCloudDriveUrl(url) {
            return inferPanName(url) !== '';
        }

        // 从 URL 中提取密码
        function extractPwd(url) {
            if (!url) return '';
            // ?pwd=xxx 或 ?password=xxx
            var pwdMatch = url.match(/[?&](?:pwd|password)=([^&]+)/);
            if (pwdMatch) return decodeURIComponent(pwdMatch[1]);
            return '';
        }

        // 清理 URL（去掉密码参数，因为密码单独存储）
        function cleanUrl(url) {
            if (!url) return url;
            return url.replace(/([?&])(?:pwd|password)=[^&]*/g, function(match, prefix) {
                // 如果是 ?pwd=xxx 且后面有其他参数，需要把 & 改为 ?
                return '';
            }).replace(/[?&]$/, '').replace(/\?&/, '?').replace(/&&/g, '&');
        }

        // ===================== HTML 解析 =====================

        // 从 HTML 中提取所有消息块
        // 返回数组: [{ messageId, channel, textHtml }]
        function parseMessageBlocks(html) {
            var messages = [];
            if (!html) return messages;

            // 按 tgme_widget_message_wrap 分割消息块
            var blocks = html.split('tgme_widget_message_wrap');
            for (var i = 1; i < blocks.length; i++) {
                var block = blocks[i];

                // 提取 data-post="channel/messageId"
                var postMatch = block.match(/data-post="([^"]+)"/);
                var postInfo = postMatch ? postMatch[1] : '';
                var channelId = '';
                var messageId = '';
                if (postInfo) {
                    var parts = postInfo.split('/');
                    channelId = parts[0] || '';
                    messageId = parts[1] || '';
                }

                // 提取消息文本 div 内容
                // <div class="tgme_widget_message_text js-message_text" dir="auto">...content...</div>
                var textMatch = block.match(/tgme_widget_message_text[^"]*"[^>]*>([\s\S]*?)<\/div>/);
                var textHtml = textMatch ? textMatch[1] : '';

                if (textHtml && textHtml.indexOf('Channel created') === -1) {
                    messages.push({
                        messageId: messageId,
                        channel: channelId,
                        textHtml: textHtml
                    });
                }
            }

            return messages;
        }

        // 从消息 HTML 中提取标题
        function extractTitle(textHtml) {
            if (!textHtml) return '';

            // 取第一个 <br/> 之前的内容作为标题行
            var firstLine = textHtml.split(/<br\s*\/?>/i)[0] || textHtml;

            // 去掉 "名称：" 前缀
            firstLine = firstLine.replace(/^[\s]*名称[：:]\s*/i, '');

            // 去掉 HTML 标签（包括 <mark> 高亮标签）
            var title = stripTags(firstLine);

            // 清理多余空格
            title = title.replace(/\s+/g, ' ').trim();

            return title;
        }

        // 从消息 HTML 中提取所有网盘链接
        // 返回数组: [{ url, name, pwd }]
        function extractCloudLinks(textHtml) {
            var links = [];
            if (!textHtml) return links;

            var seen = {};

            // 匹配所有 <a href="..." ...> 标签
            var linkRegex = /<a\s+[^>]*href="([^"]+)"[^>]*>/gi;
            var match;
            while ((match = linkRegex.exec(textHtml)) !== null) {
                var url = match[1];

                // 跳过非网盘链接（t.me 链接、telegram.org 链接等）
                if (!isCloudDriveUrl(url)) continue;

                var panName = inferPanName(url);
                var pwd = extractPwd(url);
                var cleanLinkUrl = cleanUrl(url);

                // 去重：按 URL
                if (seen[cleanLinkUrl]) continue;
                seen[cleanLinkUrl] = true;

                links.push({
                    url: cleanLinkUrl,
                    name: panName,
                    pwd: pwd
                });
            }

            return links;
        }

        // 解析单个频道搜索结果
        function searchChannel(channelId, keyword) {
            var results = [];
            var targetUrl = buildTgSearchUrl(channelId, keyword);
            var proxyUrl = buildProxyUrl(targetUrl);
            var html = fetch(proxyUrl);

            if (!html) {
                print('>>> tgs searchChannel: empty response for ' + channelId);
                return results;
            }

            var messages = parseMessageBlocks(html);
            print('>>> tgs searchChannel: ' + channelId + ' keyword=' + keyword + ' messages=' + messages.length);

            for (var i = 0; i < messages.length; i++) {
                var msg = messages[i];
                var title = extractTitle(msg.textHtml);
                if (!title) continue;

                var links = extractCloudLinks(msg.textHtml);
                if (links.length === 0) continue;

                results.push({
                    title: title,
                    channel: msg.channel || channelId,
                    messageId: msg.messageId,
                    links: links
                });
            }

            return results;
        }

        // 解析单个频道浏览结果
        function browseChannel(channelId) {
            var results = [];
            var targetUrl = buildTgBrowseUrl(channelId);
            var proxyUrl = buildProxyUrl(targetUrl);
            var html = fetch(proxyUrl);

            if (!html) {
                print('>>> tgs browseChannel: empty response for ' + channelId);
                return results;
            }

            var messages = parseMessageBlocks(html);
            print('>>> tgs browseChannel: ' + channelId + ' messages=' + messages.length);

            for (var i = 0; i < messages.length; i++) {
                var msg = messages[i];
                var title = extractTitle(msg.textHtml);
                if (!title) continue;

                var links = extractCloudLinks(msg.textHtml);
                if (links.length === 0) continue;

                results.push({
                    title: title,
                    channel: msg.channel || channelId,
                    messageId: msg.messageId,
                    links: links
                });
            }

            return results;
        }

        // 多频道搜索，合并去重
        function searchAllChannels(keyword) {
            var allResults = [];
            var seen = {};

            for (var i = 0; i < CHANNELS.length; i++) {
                try {
                    var channelResults = searchChannel(CHANNELS[i].id, keyword);
                    for (var j = 0; j < channelResults.length; j++) {
                        var item = channelResults[j];

                        // 去重：按标题 + 第一个链接 URL
                        var dedupKey = item.title + '_' + (item.links[0] ? item.links[0].url : '');
                        if (seen[dedupKey]) continue;
                        seen[dedupKey] = true;

                        allResults.push(item);
                    }
                } catch (e) {
                    print('>>> tgs searchAllChannels ERROR (' + CHANNELS[i].id + '): ' + e);
                }
            }

            return allResults;
        }

        // ===================== vod_id 编解码 =====================

        // 编码 vod_id: {title}|||tg|||{channel}_{messageId}|||{encodeURIComponent(JSON.stringify(links))}
        function encodeVodId(item) {
            var channelMsgId = (item.channel || '') + '_' + (item.messageId || '');
            var linksJson = JSON.stringify(item.links || []);
            return item.title + '|||tg|||' + channelMsgId + '|||' + encodeURIComponent(linksJson);
        }

        // 解码 vod_id
        function decodeVodId(vodId) {
            var parts = String(vodId).split('|||');
            var title = parts[0] || '';
            var type = parts[1] || '';
            var channelMsgId = parts[2] || '';
            var linksJson = parts[3] ? decodeURIComponent(parts[3]) : '[]';
            var links = [];
            try {
                links = JSON.parse(linksJson);
            } catch (e) {
                print('>>> tgs decodeVodId ERROR: ' + e);
            }

            var cmParts = channelMsgId.split('_');
            return {
                title: title,
                type: type,
                channel: cmParts[0] || '',
                messageId: cmParts.slice(1).join('_') || '',
                links: links
            };
        }

        // ===================== 首页内容 =====================

        function homeContent(filter) {
            var result = { class: [], list: [] };

            // 每个频道作为一个分类
            for (var i = 0; i < CHANNELS.length; i++) {
                result.class.push({
                    type_id: String(i),
                    type_name: CHANNELS[i].name
                });
            }

            // 首页推荐：从第一个频道获取最新消息
            try {
                var items = browseChannel(CHANNELS[0].id);
                for (var j = 0; j < items.length && j < 20; j++) {
                    var item = items[j];
                    var panNames = [];
                    for (var k = 0; k < item.links.length; k++) {
                        if (panNames.indexOf(item.links[k].name) === -1) {
                            panNames.push(item.links[k].name);
                        }
                    }
                    var remarks = '☁️' + panNames.join('/');

                    result.list.push({
                        vod_id: encodeVodId(item),
                        vod_name: item.title,
                        vod_pic: '',
                        vod_remarks: remarks
                    });
                }
            } catch (e) {
                print('>>> tgs homeContent ERROR: ' + e);
            }

            print('>>> tgs homeContent: list=' + result.list.length);
            return result;
        }

        // ===================== 分类内容 =====================

        function categoryContent(tid, pg, filter, extend) {
            var page = parseInt(pg) || 1;
            var result = { list: [], page: page, pagecount: 1, limit: 20, total: 0 };

            try {
                var catIndex = parseInt(tid) || 0;
                if (catIndex < 0 || catIndex >= CHANNELS.length) {
                    return result;
                }

                var channelId = CHANNELS[catIndex].id;
                var items = browseChannel(channelId);

                result.total = items.length;

                // 客户端侧分页，每页 20 条
                var pageSize = 20;
                var startIdx = (page - 1) * pageSize;
                var endIdx = Math.min(startIdx + pageSize, items.length);

                for (var i = startIdx; i < endIdx; i++) {
                    var item = items[i];
                    var panNames = [];
                    for (var k = 0; k < item.links.length; k++) {
                        if (panNames.indexOf(item.links[k].name) === -1) {
                            panNames.push(item.links[k].name);
                        }
                    }
                    var remarks = '☁️' + panNames.join('/');

                    result.list.push({
                        vod_id: encodeVodId(item),
                        vod_name: item.title,
                        vod_pic: '',
                        vod_remarks: remarks
                    });
                }

                result.pagecount = Math.ceil(items.length / pageSize) || 1;
            } catch (e) {
                print('>>> tgs categoryContent ERROR: ' + e);
            }

            print('>>> tgs categoryContent: tid=' + tid + ' pg=' + page + ' count=' + result.list.length);
            return result;
        }

        // ===================== 搜索内容 =====================

        function searchContent(key, quick, pg) {
            var page = parseInt(pg) || 1;
            var result = { list: [], page: page, pagecount: 1 };

            if (typeof quick === 'number') {
                page = quick;
            }

            if (!key) {
                return result;
            }

            try {
                var allItems = searchAllChannels(key);

                if (allItems.length === 0) {
                    print('>>> tgs searchContent: no results for key=' + key);
                    return result;
                }

                // 客户端侧分页，每页 20 条
                var pageSize = 20;
                var startIdx = (page - 1) * pageSize;
                var endIdx = Math.min(startIdx + pageSize, allItems.length);

                for (var i = startIdx; i < endIdx; i++) {
                    var item = allItems[i];
                    var panNames = [];
                    for (var k = 0; k < item.links.length; k++) {
                        if (panNames.indexOf(item.links[k].name) === -1) {
                            panNames.push(item.links[k].name);
                        }
                    }
                    var remarks = '☁️' + panNames.join('/');

                    result.list.push({
                        vod_id: encodeVodId(item),
                        vod_name: item.title,
                        vod_pic: '',
                        vod_remarks: remarks
                    });
                }

                result.pagecount = Math.ceil(allItems.length / pageSize) || 1;
                print('>>> tgs searchContent: key=' + key + ' total=' + allItems.length + ' pageItems=' + result.list.length);
            } catch (e) {
                print('>>> tgs searchContent ERROR: ' + e);
            }

            return result;
        }

        // ===================== 详情内容 =====================

        function detailContent(ids) {
            var result = { list: [] };

            if (!ids) {
                print('>>> tgs detailContent: empty ids');
                return result;
            }

            var decoded = decodeVodId(String(ids));
            print('>>> tgs detailContent: title=' + decoded.title + ' links=' + decoded.links.length);

            if (decoded.links.length === 0) {
                result.list.push({
                    vod_id: ids,
                    vod_name: decoded.title || '网盘资源',
                    vod_pic: '',
                    vod_remarks: '☁️网盘',
                    vod_play_from: 'TG搜索',
                    vod_play_url: JSON.stringify([{ url: '', name: '未找到资源' }])
                });
                return result;
            }

            // 按网盘类型分组
            var groups = {};
            var order = [];
            for (var i = 0; i < decoded.links.length; i++) {
                var link = decoded.links[i];
                var panName = link.name || '网盘';
                var url = link.url;
                if (link.pwd) {
                    url = url + (url.indexOf('?') !== -1 ? '&' : '?') + 'pwd=' + link.pwd;
                }

                if (!groups[panName]) {
                    groups[panName] = [];
                    order.push(panName);
                }
                groups[panName].push({ url: url, name: panName });
            }

            // 构建 play_from 和 play_url
            var playFromParts = [];
            var playUrlParts = [];
            for (var j = 0; j < order.length; j++) {
                playFromParts.push(order[j]);
                playUrlParts.push(JSON.stringify(groups[order[j]]));
            }

            result.list.push({
                vod_id: ids,
                vod_name: decoded.title,
                vod_pic: '',
                vod_remarks: '☁️' + order.join('/'),
                vod_play_from: playFromParts.join('$$$'),
                vod_play_url: playUrlParts.join('$$$')
            });

            print('>>> tgs detailContent SUCCESS: ' + decoded.links.length + ' links');
            return result;
        }

        // ===================== 播放内容 =====================

        function playerContent(vodId, flag, url) {
            print('>>> tgs playerContent: flag=' + flag + ' url=' + (url || '').substring(0, 60));

            // url 参数就是网盘链接
            if (url && (url.indexOf('http') === 0 || url.indexOf('magnet:') === 0)) {
                return {
                    parse: 0,
                    url: url,
                    header: { 'User-Agent': UA }
                };
            }

            // 从 vod_id 解码
            var decoded = decodeVodId(vodId);
            if (decoded.links.length > 0) {
                var link = decoded.links[0];
                var realUrl = link.url;
                if (link.pwd) {
                    realUrl = realUrl + (realUrl.indexOf('?') !== -1 ? '&' : '?') + 'pwd=' + link.pwd;
                }
                return {
                    parse: 0,
                    url: realUrl,
                    header: { 'User-Agent': UA }
                };
            }

            return { parse: 0, url: '' };
        }

        // ===================== 初始化 =====================

        function init(config) {
            print('>>> tgs init: TG搜索 JS蜘蛛 v1.0');

            // 尝试从 config.ext 解析自定义频道列表
            try {
                var ext = '';
                if (config && typeof config === 'object') {
                    ext = config.ext || '';
                } else if (typeof config === 'string') {
                    ext = config;
                }

                if (ext && ext.length > 0) {
                    var customChannels = [];

                    // 格式1: "名称1@ch1&名称2@ch2" （&分隔）
                    if (ext.indexOf('@') !== -1) {
                        var pairs = ext.split('&');
                        for (var i = 0; i < pairs.length; i++) {
                            var pair = pairs[i].trim();
                            if (!pair) continue;
                            var atIdx = pair.indexOf('@');
                            if (atIdx > 0) {
                                customChannels.push({
                                    name: pair.substring(0, atIdx).trim(),
                                    id: pair.substring(atIdx + 1).trim()
                                });
                            } else {
                                customChannels.push({ name: pair, id: pair });
                            }
                        }
                    }
                    // 格式2: "ch1,ch2,ch3" （逗号分隔）
                    else if (ext.indexOf(',') !== -1) {
                        var ids = ext.split(',');
                        for (var j = 0; j < ids.length; j++) {
                            var id = ids[j].trim();
                            if (id) {
                                customChannels.push({ name: id, id: id });
                            }
                        }
                    }
                    // 格式3: 单个频道名
                    else {
                        customChannels.push({ name: ext, id: ext });
                    }

                    if (customChannels.length > 0) {
                        CHANNELS = customChannels;
                        print('>>> tgs init: 自定义频道 ' + CHANNELS.length + ' 个');
                    }
                }
            } catch (e) {
                print('>>> tgs init: 解析 ext 失败: ' + e + '，使用默认频道');
            }

            print('>>> tgs init: 频道列表: ' + CHANNELS.map(function(c) { return c.id; }).join(', '));
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
