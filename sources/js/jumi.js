/*
 * 剧迷 JS 蜘蛛 v1.0
 * 适配 vbox-ios JSSpiderEngine (type:3 独立引擎)
 * 从 Python drpy 脚本转换，纯 HTML 解析（正则匹配）
 * 目标站: https://gimytw.cc
 */

// ===================== 工具函数 =====================

// 正则匹配辅助：从 HTML 中提取第一个匹配组
function reMatch(pattern, html, group) {
    group = group || 1;
    var m = html.match(pattern);
    return m ? (m[group] || '') : '';
}

// 正则匹配辅助：返回所有匹配
function reMatchAll(pattern, html, group) {
    group = group || 1;
    var results = [];
    var m;
    var re = new RegExp(pattern.source, pattern.flags || 'g');
    while ((m = re.exec(html)) !== null) {
        results.push(m[group] || '');
    }
    return results;
}

// URL 编码
function urlEncode(str) {
    return encodeURIComponent(str);
}

// ===================== 蜘蛛主体 =====================
var spider = {
    __jsEvalReturn: function() {
        var HOST = 'https://gimytw.cc';
        var HEADERS = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'zh-TW,zh;q=0.9,en;q=0.8',
            'Referer': HOST + '/'
        };

        // 发起 HTTP 请求
        function fetchURL(url) {
            if (url.indexOf('http') !== 0) {
                url = HOST + url;
            }
            try {
                var resp = req(url, { method: 'GET', headers: HEADERS });
                if (!resp) { print('>>> jumi fetch null: ' + url); return ''; }
                var content = resp.content || resp.data || '';
                if (typeof content === 'object') content = JSON.stringify(content);
                return content;
            } catch (e) {
                print('>>> jumi fetch ERROR: ' + e + ' url=' + url);
                return '';
            }
        }

        // 解析视频列表（从 HTML 中提取）
        function parseVideoList(html) {
            var videos = [];
            if (!html) return videos;

            // 匹配视频卡片块：<a class="video-pic" href="/voddetail2/12345.html" title="...">
            // 或 <div class="video-pic"> 内含 <a href="/voddetail2/...">
            var cardPattern = /<a[^>]*class="[^"]*video-pic[^"]*"[^>]*href="([^"]*)"[^>]*title="([^"]*)"[^>]*>/gi;
            var m;
            while ((m = cardPattern.exec(html)) !== null) {
                var href = m[1];
                var title = m[2];
                var vid = reMatch(/\/voddetail2\/(\d+)\.html/, href);
                if (!vid) {
                    vid = reMatch(/\/eps\/(\d+)-/, href);
                }
                if (!vid) continue;

                var pic = '';
                // 尝试从同块中提取图片
                var imgMatch = html.substring(Math.max(0, m.index - 200), m.index + 500).match(/data-original="([^"]+)"/);
                if (imgMatch) pic = imgMatch[1];
                if (!pic) {
                    imgMatch = html.substring(Math.max(0, m.index - 200), m.index + 500).match(/<img[^>]*src="([^"]+)"/);
                    if (imgMatch) pic = imgMatch[1];
                }
                if (pic && pic.indexOf('http') !== 0) {
                    if (pic.indexOf('//') === 0) pic = 'https:' + pic;
                    else if (pic.indexOf('/') === 0) pic = HOST + pic;
                }

                // 备注
                var remark = '';
                var noteMatch = html.substring(m.index, m.index + 500).match(/class="[^"]*note[^"]*"[^>]*>([^<]*)</);
                if (noteMatch) remark = noteMatch[1].trim();

                videos.push({
                    vod_id: vid,
                    vod_name: title,
                    vod_pic: pic,
                    vod_remarks: remark
                });
            }

            // 备用：匹配 .col-md-2 内的链接
            if (videos.length === 0) {
                var colPattern = /<div[^>]*class="[^"]*col-md-2[^"]*"[^>]*>([\s\S]*?)<\/div>\s*<\/div>\s*<\/div>/gi;
                while ((m = colPattern.exec(html)) !== null) {
                    var block = m[1];
                    var vid2 = reMatch(/\/voddetail2\/(\d+)\.html/, block);
                    if (!vid2) continue;
                    var title2 = reMatch(/title="([^"]+)"/, block);
                    if (!title2) {
                        var altMatch = block.match(/alt="([^"]+)"/);
                        if (altMatch) title2 = altMatch[1];
                    }
                    if (!title2) title2 = vid2;
                    var pic2 = reMatch(/data-original="([^"]+)"/, block);
                    if (!pic2) pic2 = reMatch(/src="([^"]+)"/, block);
                    if (pic2 && pic2.indexOf('http') !== 0) {
                        if (pic2.indexOf('//') === 0) pic2 = 'https:' + pic2;
                        else if (pic2.indexOf('/') === 0) pic2 = HOST + pic2;
                    }
                    videos.push({
                        vod_id: vid2,
                        vod_name: title2,
                        vod_pic: pic2,
                        vod_remarks: ''
                    });
                }
            }

            return videos;
        }

        return {
            init: function(config) { return true; },

            homeContent: function(filter) {
                var classes = [
                    { type_id: 'drama0', type_name: '电视剧' },
                    { type_id: 'movie0', type_name: '电影' },
                    { type_id: 'variety0', type_name: '综艺' },
                    { type_id: 'anime0', type_name: '动漫' }
                ];
                var html = fetchURL('/');
                var videos = parseVideoList(html);
                return { class: classes, list: videos.slice(0, 24) };
            },

            categoryContent: function(tid, pg, extend) {
                pg = parseInt(pg) || 1;
                var url = '/' + tid + '?page=' + pg;
                var html = fetchURL(url);
                var videos = parseVideoList(html);
                return {
                    page: pg,
                    pagecount: 999,
                    limit: 24,
                    total: 9999,
                    list: videos
                };
            },

            detailContent: function(ids) {
                var result = { list: [] };
                var vid = ids[0];
                var url = '/voddetail2/' + vid + '.html';
                var html = fetchURL(url);

                if (!html) return result;

                // 标题
                var vod_name = reMatch(/<h1[^>]*>([^<]+)<\/h1>/, html);
                if (!vod_name) {
                    vod_name = reMatch(/<title>([^<]+)/, html);
                    if (vod_name) vod_name = vod_name.replace(/\s*-\s*剧迷.*$/, '').trim();
                }

                // 封面图（3种方法）
                var vod_pic = '';
                // 方法1: .details-pic .video-pic 的 style 背景
                var picStyle = reMatch(/class="[^"]*video-pic[^"]*"[^>]*style="[^"]*url\(([^)]+)\)/, html);
                if (picStyle) {
                    vod_pic = picStyle.replace(/["']/g, '');
                    if (vod_pic.indexOf('//') === 0) vod_pic = 'https:' + vod_pic;
                    else if (vod_pic.indexOf('/') === 0) vod_pic = HOST + vod_pic;
                }
                // 方法2: meta og:image
                if (!vod_pic) {
                    vod_pic = reMatch(/<meta[^>]*property="og:image"[^>]*content="([^"]+)"/, html);
                    if (vod_pic && vod_pic.indexOf('//') === 0) vod_pic = 'https:' + vod_pic;
                }
                // 方法3: .my-blur 背景
                if (!vod_pic) {
                    var blurStyle = reMatch(/class="[^"]*my-blur[^"]*"[^>]*style="[^"]*url\(([^)]+)\)/, html);
                    if (blurStyle) {
                        vod_pic = blurStyle.replace(/["']/g, '');
                        if (vod_pic.indexOf('//') === 0) vod_pic = 'https:' + vod_pic;
                    }
                }

                // 导演
                var vod_director = '';
                var dirMatch = html.match(/<li[^>]*>导演[：:]\s*([^<]*)<\/li>/);
                if (dirMatch) vod_director = dirMatch[1].trim();

                // 演员
                var vod_actor = '';
                var actMatch = html.match(/<li[^>]*>主演[：:]\s*([^<]*)<\/li>/);
                if (actMatch) vod_actor = actMatch[1].trim();

                // 简介
                var vod_content = '';
                var descMatch = html.match(/class="[^"]*details-content-all[^"]*"[^>]*>[\s\S]*?<p[^>]*>([\s\S]*?)<\/p>/);
                if (descMatch) vod_content = descMatch[1].replace(/<[^>]+>/g, '').trim();

                // 剧集列表
                var ep_list = [];
                // 从 .playlist ul li a 提取
                var epPattern = /<a[^>]*href="\/eps\/(\d+)-([^"]+)\.html"[^>]*>([^<]*)<\/a>/gi;
                var em;
                while ((em = epPattern.exec(html)) !== null) {
                    var ep_vid = em[1];
                    var ep_id = em[2];
                    var ep_name = em[3].trim();
                    if (ep_vid === vid) {
                        ep_list.push(ep_name + '$' + vid + '-' + ep_id);
                    }
                }

                // 如果当前页没提取到，尝试从第一集播放页获取
                if (ep_list.length === 0) {
                    var firstEpUrl = '/eps/' + vid + '-1.html';
                    var epHtml = fetchURL(firstEpUrl);
                    if (epHtml) {
                        while ((em = epPattern.exec(epHtml)) !== null) {
                            var ep_vid2 = em[1];
                            var ep_id2 = em[2];
                            var ep_name2 = em[3].trim();
                            ep_list.push(ep_name2 + '$' + ep_vid2 + '-' + ep_id2);
                        }
                    }
                }

                var play_from = ['在线播放'];
                var play_url = ep_list.length > 0 ? [ep_list.join('#')] : [''];

                result.list.push({
                    vod_id: vid,
                    vod_name: vod_name || vid,
                    vod_pic: vod_pic,
                    vod_director: vod_director,
                    vod_actor: vod_actor,
                    vod_content: vod_content,
                    vod_play_from: play_from.join('$$$'),
                    vod_play_url: play_url.join('$$$')
                });

                return result;
            },

            searchContent: function(key, quick, pg) {
                pg = pg || '1';
                var encodedKey = urlEncode(key);
                var url = '/search?q=' + encodedKey + '&page=' + pg;
                var html = fetchURL(url);
                var videos = parseVideoList(html);
                return {
                    list: videos,
                    page: parseInt(pg),
                    pagecount: 1,
                    limit: 36,
                    total: videos.length
                };
            },

            playerContent: function(flag, id, vipFlags) {
                /*
                 * id 格式: ep_name$vid-ep_id  例如: 20260724下$202664450-2026072-xia
                 * 先按 $ 分割取最后一段得到 vid-ep_id，再按 - 分割取 vid 和 ep_id（ep_id 可能含 -）
                 */
                // 兼容 ep_name$vid-ep_id 格式
                if (id.indexOf('$') >= 0) {
                    var dollarParts = id.split('$');
                    id = dollarParts[dollarParts.length - 1];
                }
                var parts = id.split('-');
                if (parts.length < 2) {
                    return { parse: 1, url: '' };
                }

                var vid = parts[0];
                var ep_id = parts.slice(1).join('-');  // ep_id 可能含多个 -，如 2026072-xia
                var url = '/eps/' + vid + '-' + ep_id + '.html';
                var html = fetchURL(url);

                if (!html) {
                    return { parse: 1, url: '' };
                }

                // 提取播放线路标签
                var tabLinks = [];
                var tabPattern = /<a[^>]*href="([^"]*\/_watch\/[^"]*)"[^>]*>([^<]*)<\/a>/gi;
                var tm;
                while ((tm = tabPattern.exec(html)) !== null) {
                    tabLinks.push({ href: tm[1], name: tm[2].trim() });
                }

                // 如果指定了 flag，匹配对应线路
                if (flag && tabLinks.length > 0) {
                    for (var i = 0; i < tabLinks.length; i++) {
                        if (tabLinks[i].name === flag) {
                            var watchUrl = tabLinks[i].href;
                            if (watchUrl.indexOf('http') !== 0) watchUrl = HOST + watchUrl;
                            var watchHtml = fetchURL(watchUrl);
                            if (watchHtml) {
                                var realUrl = extractVideoUrl(watchHtml);
                                if (realUrl) {
                                    return { parse: 0, url: realUrl };
                                }
                            }
                            return { parse: 1, url: watchUrl };
                        }
                    }
                }

                // 默认取第一个线路
                if (tabLinks.length > 0) {
                    var watchUrl = tabLinks[0].href;
                    if (watchUrl.indexOf('http') !== 0) watchUrl = HOST + watchUrl;
                    var watchHtml = fetchURL(watchUrl);
                    if (watchHtml) {
                        var realUrl = extractVideoUrl(watchHtml);
                        if (realUrl) {
                            return { parse: 0, url: realUrl };
                        }
                    }
                    return { parse: 1, url: watchUrl };
                }

                // 直接找 iframe
                var iframeSrc = reMatch(/<iframe[^>]*name="p-frame"[^>]*src="([^"]+)"/, html);
                if (!iframeSrc) {
                    iframeSrc = reMatch(/<iframe[^>]*src="([^"]+)"/, html);
                }
                if (iframeSrc) {
                    return { parse: 1, url: iframeSrc };
                }

                return { parse: 1, url: url };
            }
        };

        // 从 /_watch/ 页面提取真实视频地址
        function extractVideoUrl(html) {
            if (!html) return null;

            // 1. var url = '...' 或 var url = "..."（DPlayer / Hls.js 配置）
            var varUrl = reMatch(/var\s+url\s*=\s*['"]([^'"]+)['"]/, html);
            if (varUrl && (varUrl.indexOf('.m3u8') >= 0 || varUrl.indexOf('.mp4') >= 0)) {
                return varUrl;
            }

            // 2. video 标签
            var videoSrc = reMatch(/<video[^>]*src="([^"]+)"/, html);
            if (videoSrc) return videoSrc;

            // 3. iframe
            var iframeSrc = reMatch(/<iframe[^>]*src="([^"]+)"/, html);
            if (iframeSrc) return iframeSrc;

            // 4. 从 script 中提取 m3u8/mp4
            var m3u8Match = html.match(/https?:\/\/[^\s"'<>]+\.m3u8[^\s"'<>]*/);
            if (m3u8Match) return m3u8Match[0];

            var mp4Match = html.match(/https?:\/\/[^\s"'<>]+\.mp4[^\s"'<>]*/);
            if (mp4Match) return mp4Match[0];

            // 5. DPlayer 配置中的 url
            var dpUrl = reMatch(/url\s*:\s*['"]([^'"]+)['"]/, html);
            if (dpUrl && (dpUrl.indexOf('.m3u8') >= 0 || dpUrl.indexOf('.mp4') >= 0)) {
                return dpUrl;
            }

            // 6. player 配置 JSON
            var playerMatch = html.match(/player\s*=\s*(\{[^;]+\})/);
            if (playerMatch) {
                try {
                    var config = JSON.parse(playerMatch[1]);
                    if (config.url) return config.url;
                    if (config.src) return config.src;
                } catch(e) {}
            }

            // 7. data-url / data-src / data-video 属性
            var dataUrl = reMatch(/data-url="([^"]+)"/, html);
            if (dataUrl) return dataUrl;
            var dataSrc = reMatch(/data-src="([^"]+)"/, html);
            if (dataSrc) return dataSrc;
            var dataVideo = reMatch(/data-video="([^"]+)"/, html);
            if (dataVideo) return dataVideo;

            return null;
        }
    }
};