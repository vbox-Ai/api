/*
 * 剧迷 JS 蜘蛛 v2.0
 * 适配 vbox-ios JSSpiderEngine (type:3 独立引擎)
 * 目标站: https://gimytw.cc
 * 修复: 字符串ids处理、playerContent参数顺序、多线路支持
 */

// ===================== 工具函数 =====================

function reMatch(pattern, html, group) {
    group = group || 1;
    var m = html.match(pattern);
    return m ? (m[group] || '') : '';
}

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

        function fetchURL(url) {
            if (url.indexOf('http') !== 0) {
                url = HOST + url;
            }
            try {
                print('>>> jumi fetch start: ' + url);
                var resp = req(url, { method: 'GET', headers: HEADERS });
                if (!resp) { print('>>> jumi fetch null: ' + url); return ''; }
                var status = resp.status || resp.code || 0;
                var content = resp.content || resp.data || '';
                if (typeof content === 'object') content = JSON.stringify(content);
                print('>>> jumi fetch done: ' + url + ' status=' + status + ' len=' + content.length);
                return content;
            } catch (e) {
                print('>>> jumi fetch ERROR: ' + e + ' url=' + url);
                return '';
            }
        }

        function parseVideoList(html) {
            var videos = [];
            if (!html) return videos;

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

        // 从 episode 页面提取所有线路名和对应的 _watch URL（用于 playerContent）
        function extractSourcesFromEpPage(html) {
            var sources = [];
            if (!html) return sources;
            var tabPattern = /<a[^>]*href="([^"]*\/_watch\/[^"]*)"[^>]*>([^<]*)<\/a>/gi;
            var tm;
            while ((tm = tabPattern.exec(html)) !== null) {
                var href = tm[1];
                var name = tm[2].trim();
                if (href.indexOf('http') !== 0) href = HOST + href;
                sources.push({ name: name, href: href });
            }
            return sources;
        }

        // 从 /_watch/ 页面提取真实视频地址
        function extractVideoUrl(html) {
            if (!html) return null;

            var varUrl = reMatch(/var\s+url\s*=\s*['"]([^'"]+)['"]/, html);
            if (varUrl && (varUrl.indexOf('.m3u8') >= 0 || varUrl.indexOf('.mp4') >= 0)) {
                return varUrl;
            }

            var videoSrc = reMatch(/<video[^>]*src="([^"]+)"/, html);
            if (videoSrc) return videoSrc;

            var iframeSrc = reMatch(/<iframe[^>]*src="([^"]+)"/, html);
            if (iframeSrc) return iframeSrc;

            var m3u8Match = html.match(/https?:\/\/[^\s"'<>]+\.m3u8[^\s"'<>]*/);
            if (m3u8Match) return m3u8Match[0];

            var mp4Match = html.match(/https?:\/\/[^\s"'<>]+\.mp4[^\s"'<>]*/);
            if (mp4Match) return mp4Match[0];

            var dpUrl = reMatch(/url\s*:\s*['"]([^'"]+)['"]/, html);
            if (dpUrl && (dpUrl.indexOf('.m3u8') >= 0 || dpUrl.indexOf('.mp4') >= 0)) {
                return dpUrl;
            }

            var playerMatch = html.match(/player\s*=\s*(\{[^;]+\})/);
            if (playerMatch) {
                try {
                    var config = JSON.parse(playerMatch[1]);
                    if (config.url) return config.url;
                    if (config.src) return config.src;
                } catch(e) {}
            }

            var dataUrl = reMatch(/data-url="([^"]+)"/, html);
            if (dataUrl) return dataUrl;
            var dataSrc = reMatch(/data-src="([^"]+)"/, html);
            if (dataSrc) return dataSrc;
            var dataVideo = reMatch(/data-video="([^"]+)"/, html);
            if (dataVideo) return dataVideo;

            return null;
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

                // vbox 传入的是字符串 vod_id，TVBox 标准是数组
                var vid;
                if (typeof ids === 'string') {
                    vid = ids.split(',')[0].split('/')[0].trim();
                } else if (Array.isArray(ids) && ids.length > 0) {
                    vid = String(ids[0]).trim();
                } else {
                    print('>>> jumi detailContent invalid ids: ' + JSON.stringify(ids));
                    return result;
                }

                print('>>> jumi detailContent vid=' + vid);
                var url = '/voddetail2/' + vid + '.html';
                var html = fetchURL(url);
                if (!html) {
                    print('>>> jumi detailContent empty html for vid=' + vid);
                    return result;
                }
                print('>>> jumi detailContent html len=' + html.length);

                // 标题
                var vod_name = reMatch(/<h1[^>]*>([^<]+)<\/h1>/, html);
                if (!vod_name) {
                    vod_name = reMatch(/<title>([^<]+)/, html);
                    if (vod_name) vod_name = vod_name.replace(/\s*-\s*剧迷.*$/, '').trim();
                }

                // 封面图
                var vod_pic = '';
                var picStyle = reMatch(/class="[^"]*video-pic[^"]*"[^>]*style="[^"]*url\(([^)]+)\)/, html);
                if (picStyle) {
                    vod_pic = picStyle.replace(/["']/g, '');
                    if (vod_pic.indexOf('//') === 0) vod_pic = 'https:' + vod_pic;
                    else if (vod_pic.indexOf('/') === 0) vod_pic = HOST + vod_pic;
                }
                if (!vod_pic) {
                    vod_pic = reMatch(/<meta[^>]*property="og:image"[^>]*content="([^"]+)"/, html);
                    if (vod_pic && vod_pic.indexOf('//') === 0) vod_pic = 'https:' + vod_pic;
                }
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

                // ========== 提取剧集列表 ==========
                var episodes = [];
                var epPattern = /<a[^>]*href="\/eps\/(\d+)-([^"]+)\.html"[^>]*>([^<]*)<\/a>/gi;
                var em;
                while ((em = epPattern.exec(html)) !== null) {
                    var ep_vid = em[1];
                    var ep_id = em[2];
                    var ep_name = em[3].trim();
                    if (ep_vid === vid) {
                        episodes.push({ name: ep_name, vid: vid, ep_id: ep_id });
                    }
                }
                print('>>> jumi detailContent episodes count=' + episodes.length);

                // 如果当前页没提取到，尝试从页面中其他可能的剧集链接提取（兼容老站结构）
                if (episodes.length === 0) {
                    var altPattern = /<a[^>]*href="\/eps\/([^"]+)\.html"[^>]*>([^<]*)<\/a>/gi;
                    while ((em = altPattern.exec(html)) !== null) {
                        var altHref = em[1];
                        var altName = em[2].trim();
                        var altParts = altHref.split('-');
                        if (altParts.length >= 2 && altParts[0] === vid && altName) {
                            episodes.push({ name: altName, vid: vid, ep_id: altParts.slice(1).join('-') });
                        }
                    }
                    print('>>> jumi detailContent alt episodes count=' + episodes.length);
                }

                // 兜底：尝试从第一集播放页获取
                if (episodes.length === 0) {
                    var firstEpUrl = '/eps/' + vid + '-1.html';
                    var epHtml = fetchURL(firstEpUrl);
                    if (epHtml) {
                        while ((em = epPattern.exec(epHtml)) !== null) {
                            var ep_vid2 = em[1];
                            var ep_id2 = em[2];
                            var ep_name2 = em[3].trim();
                            episodes.push({ name: ep_name2, vid: ep_vid2, ep_id: ep_id2 });
                        }
                    }
                    print('>>> jumi detailContent fallback episodes count=' + episodes.length);
                }

                // ========== 构建 play_from 和 play_url ==========
                var play_from = [];
                var play_url = [];

                if (episodes.length > 0) {
                    // 只请求一次第一集页面，获取线路名称列表
                    var firstEpHtml = fetchURL('/eps/' + episodes[0].vid + '-' + episodes[0].ep_id + '.html');
                    var sourceNames = [];
                    if (firstEpHtml) {
                        var srcPattern = /<a[^>]*href="[^"]*\/_watch\/[^"]*"[^>]*>([^<]*)<\/a>/gi;
                        var sm;
                        while ((sm = srcPattern.exec(firstEpHtml)) !== null) {
                            var sname = sm[1].trim();
                            if (sname && sourceNames.indexOf(sname) < 0) {
                                sourceNames.push(sname);
                            }
                        }
                    }
                    print('>>> jumi detailContent sourceNames=' + JSON.stringify(sourceNames));

                    // 构建单集标识字符串: vid-ep_id
                    var epIdList = [];
                    for (var i = 0; i < episodes.length; i++) {
                        epIdList.push(episodes[i].name + '$' + episodes[i].vid + '-' + episodes[i].ep_id);
                    }
                    var epIdStr = epIdList.join('#');

                    if (sourceNames.length > 1) {
                        // 多线路：每个线路用同样的剧集ID列表
                        play_from = sourceNames;
                        for (var i = 0; i < sourceNames.length; i++) {
                            play_url.push(epIdStr);
                        }
                    } else {
                        // 单线路
                        play_from = ['在线播放'];
                        play_url.push(epIdStr);
                    }
                } else {
                    play_from = ['在线播放'];
                    play_url = [''];
                }

                var finalPlayFrom = play_from.join('$$$');
                var finalPlayUrl = play_url.join('$$$');
                print('>>> jumi detailContent play_from=' + finalPlayFrom);
                print('>>> jumi detailContent play_url=' + finalPlayUrl);

                result.list.push({
                    vod_id: vid,
                    vod_name: vod_name || vid,
                    vod_pic: vod_pic,
                    vod_director: vod_director,
                    vod_actor: vod_actor,
                    vod_content: vod_content,
                    vod_play_from: finalPlayFrom,
                    vod_play_url: finalPlayUrl
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
                 * vbox 调用: playerContent(vodId, sourceName, episodeId)
                 * 在 JS 中映射为: playerContent(flag, id, vipFlags)
                 * 所以: flag=vodId, id=sourceName(线路名), vipFlags=episodeId
                 * TVBox 标准可能只传两个参数 (flag, id): flag=线路名, id=episodeId
                 */
                print('>>> jumi playerContent raw args: flag=' + flag + ' id=' + id + ' vipFlags=' + vipFlags);
                var sourceName = id;
                var episodeId = vipFlags;

                // 兼容 TVBox 标准 2 参数调用
                if ((episodeId === undefined || episodeId === null || episodeId === '') && sourceName) {
                    sourceName = flag;
                    episodeId = id;
                }

                // 如果 episodeId 含 $ 分割符，取最后一段
                if (episodeId && episodeId.indexOf('$') >= 0) {
                    var parts = episodeId.split('$');
                    episodeId = parts[parts.length - 1];
                }

                print('>>> jumi playerContent parsed: sourceName=' + sourceName + ' episodeId=' + episodeId);

                if (!episodeId) {
                    print('>>> jumi playerContent empty episodeId');
                    return { parse: 1, url: '' };
                }

                // 情况1: episodeId 已经是完整 watch URL（多线路模式下）
                if (episodeId.indexOf('/_watch/') >= 0) {
                    var watchUrl = episodeId;
                    if (watchUrl.indexOf('http') !== 0) watchUrl = HOST + watchUrl;
                    var watchHtml = fetchURL(watchUrl);
                    if (watchHtml) {
                        var realUrl = extractVideoUrl(watchHtml);
                        if (realUrl) {
                            print('>>> jumi playerContent watchUrl=' + watchUrl + ' realUrl=' + realUrl);
                            return { parse: 0, url: realUrl };
                        }
                    }
                    print('>>> jumi playerContent fallback watchUrl=' + watchUrl);
                    return { parse: 1, url: watchUrl };
                }

                // 情况2: episodeId 是 vid-ep_id 格式
                var idParts = episodeId.split('-');
                if (idParts.length < 2) {
                    print('>>> jumi playerContent invalid episodeId format: ' + episodeId);
                    return { parse: 1, url: '' };
                }
                var vid = idParts[0];
                var ep_id = idParts.slice(1).join('-');
                var epUrl = '/eps/' + vid + '-' + ep_id + '.html';
                print('>>> jumi playerContent epUrl=' + epUrl);
                var html = fetchURL(epUrl);
                if (!html) {
                    print('>>> jumi playerContent empty epHtml');
                    return { parse: 1, url: '' };
                }

                // 提取该集所有线路
                var sources = extractSourcesFromEpPage(html);
                print('>>> jumi playerContent sources=' + JSON.stringify(sources));

                // 如果指定了 sourceName 且能匹配到对应线路
                if (sourceName && sourceName !== 'play' && sources.length > 0) {
                    for (var i = 0; i < sources.length; i++) {
                        if (sources[i].name === sourceName) {
                            var watchHtml = fetchURL(sources[i].href);
                            if (watchHtml) {
                                var realUrl = extractVideoUrl(watchHtml);
                                if (realUrl) return { parse: 0, url: realUrl };
                            }
                            return { parse: 1, url: sources[i].href };
                        }
                    }
                }

                // 默认取第一个线路
                if (sources.length > 0) {
                    var watchHtml = fetchURL(sources[0].href);
                    if (watchHtml) {
                        var realUrl = extractVideoUrl(watchHtml);
                        if (realUrl) {
                            print('>>> jumi playerContent first source realUrl=' + realUrl);
                            return { parse: 0, url: realUrl };
                        }
                    }
                    print('>>> jumi playerContent first source fallback=' + sources[0].href);
                    return { parse: 1, url: sources[0].href };
                }

                // 兜底：直接找 iframe
                var iframeSrc = reMatch(/<iframe[^>]*name="p-frame"[^>]*src="([^"]+)"/, html);
                if (!iframeSrc) {
                    iframeSrc = reMatch(/<iframe[^>]*src="([^"]+)"/, html);
                }
                if (iframeSrc) {
                    print('>>> jumi playerContent iframe fallback=' + iframeSrc);
                    return { parse: 1, url: iframeSrc };
                }

                print('>>> jumi playerContent final fallback epUrl=' + epUrl);
                return { parse: 1, url: epUrl };
            }
        };
    }
};
