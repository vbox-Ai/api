/*
 * 韩小圈 JS 蜘蛛 v2.0
 * 适配 vbox-ios JSSpiderEngine (type:3 独立引擎)
 * 目标站: https://www.jennyhow.com
 * 来源: 韩剧/韩影/韩综/韩漫
 * v2.0: 基于实际HTML验证修复 - 详情页信息提取、剧集列表、搜索URL
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
        var HOST = 'https://www.jennyhow.com';
        var UA = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36';
        var HEADERS = {
            'User-Agent': UA,
            'Referer': HOST + '/'
        };

        var CLASS_MAP = {
            '/hxq/1.html': '最新韩剧',
            '/hxq/2.html': '韩国电影',
            '/hxq/3.html': '韩国综艺',
            '/hxq/4.html': '韩国动漫'
        };

        function fetchHTML(url) {
            if (url.indexOf('http') !== 0) {
                url = HOST + url;
            }
            try {
                print('>>> hxq fetch start: ' + url);
                var resp = req(url, { method: 'GET', headers: HEADERS });
                if (!resp) { print('>>> hxq fetch null: ' + url); return ''; }
                var status = resp.status || resp.code || 0;
                var content = resp.content || resp.data || '';
                if (typeof content === 'object') content = JSON.stringify(content);
                print('>>> hxq fetch done: ' + url + ' status=' + status + ' len=' + content.length);
                return content;
            } catch (e) {
                print('>>> hxq fetch ERROR: ' + e + ' url=' + url);
                return '';
            }
        }

        function formatPic(picUrl) {
            if (!picUrl) return '';
            if (picUrl.indexOf('//') === 0) return 'https:' + picUrl;
            if (picUrl.indexOf('/') === 0) return HOST + picUrl;
            return picUrl;
        }

        // 解析 module-item 卡片列表（分类页/搜索页通用）
        function parseModuleItems(html) {
            var videos = [];
            if (!html) return videos;

            // 按 <div class="module-item 分割（注意后面有空格或>，避免匹配到 module-item-cover 等）
            var parts = html.split(/<div[^>]*class="module-item[\s"][^>]*>/);
            for (var i = 1; i < parts.length; i++) {
                var block = parts[i];

                // 提取 module-item-titlebox 中的链接
                var titleBox = block.match(/<div[^>]*class="[^"]*module-item-titlebox[^"]*"[^>]*>([\s\S]*?)<\/div>/);
                var aHref = '', aTitle = '';
                if (titleBox) {
                    aHref = reMatch(/<a[^>]*href="([^"]*)"/, titleBox[1]);
                    aTitle = reMatch(/<a[^>]*title="([^"]*)"/, titleBox[1]);
                }

                // 备用：从 module-item-pic 中提取
                if (!aHref) {
                    var picBlock = block.match(/<div[^>]*class="[^"]*module-item-pic[^"]*"[^>]*>([\s\S]*?)<\/div>/);
                    if (picBlock) {
                        aHref = reMatch(/<a[^>]*href="([^"]*)"/, picBlock[1]);
                        if (!aTitle) aTitle = reMatch(/<a[^>]*title="([^"]*)"/, picBlock[1]);
                    }
                }

                if (!aHref || aHref.indexOf('/hanxiaoquan/') < 0) continue;

                // 提取名称
                var name = aTitle;
                if (!name) {
                    name = reMatch(/<img[^>]*alt="([^"]*)"/, block);
                }
                if (!name) name = aHref;

                // 提取封面
                var pic = reMatch(/data-src="([^"]*)"/, block);
                if (!pic) pic = reMatch(/data-original="([^"]*)"/, block);
                if (!pic) pic = reMatch(/<img[^>]*src="([^"]*)"/, block);

                // 提取备注（日期）
                var remark = reMatch(/<div[^>]*class="[^"]*module-item-text[^"]*"[^>]*>([^<]*)</, block);

                videos.push({
                    vod_id: aHref,
                    vod_name: name.trim(),
                    vod_pic: formatPic(pic),
                    vod_remarks: remark.trim()
                });
            }

            print('>>> hxq parseModuleItems count=' + videos.length);
            return videos;
        }

        // 获取播放页 headers（透传给播放器，用于 Referer/UA 校验）
        function getPlayHeaders() {
            return {
                'Referer': HOST + '/',
                'User-Agent': UA
            };
        }

        return {
            init: function(config) { return true; },

            // ========== 首页分类 ==========
            homeContent: function(filter) {
                var classes = [];
                for (var tid in CLASS_MAP) {
                    if (CLASS_MAP.hasOwnProperty(tid)) {
                        classes.push({ type_id: tid, type_name: CLASS_MAP[tid] });
                    }
                }
                // 也返回首页推荐视频
                var html = fetchHTML('/');
                var videos = parseModuleItems(html);
                return { class: classes, list: videos.slice(0, 24) };
            },

            // ========== 分类页面 ==========
            categoryContent: function(tid, pg, extend) {
                pg = parseInt(pg) || 1;

                // 兼容 tid 格式
                var url = tid;
                if (url.indexOf('/hxq/') < 0) {
                    // 数字格式 → 映射
                    var map = {
                        '1': '/hxq/1.html', '20': '/hxq/1.html',
                        '2': '/hxq/2.html', '21': '/hxq/2.html',
                        '3': '/hxq/3.html', '22': '/hxq/3.html',
                        '4': '/hxq/4.html', '23': '/hxq/4.html'
                    };
                    url = map[tid] || '/hxq/1.html';
                }

                // 翻页: /hxq/1.html → /hxq/1-2.html（第1页是 /hxq/1.html，第2页起是 /hxq/1-N.html）
                if (pg > 1 && url.indexOf('.html') >= 0) {
                    url = url.replace('.html', '-' + pg + '.html');
                }

                print('>>> hxq categoryContent url=' + url + ' pg=' + pg);
                var html = fetchHTML(url);
                var videos = parseModuleItems(html);

                return {
                    list: videos,
                    page: pg,
                    pagecount: pg + 1,
                    limit: 24,
                    total: 0
                };
            },

            // ========== 详情页 ==========
            detailContent: function(ids) {
                var result = { list: [] };

                // vbox 传入的是字符串 vod_id
                var vid;
                if (typeof ids === 'string') {
                    vid = ids.split(',')[0].split('/')[0].trim();
                } else if (Array.isArray(ids) && ids.length > 0) {
                    vid = String(ids[0]).trim();
                } else {
                    print('>>> hxq detailContent invalid ids: ' + JSON.stringify(ids));
                    return result;
                }

                // 如果 vid 不是完整 URL，拼接
                var detailUrl = vid;
                if (detailUrl.indexOf('http') !== 0) {
                    if (detailUrl.indexOf('/hanxiaoquan/') < 0) {
                        detailUrl = '/hanxiaoquan/' + detailUrl + '.html';
                    }
                    detailUrl = HOST + detailUrl;
                }

                print('>>> hxq detailContent url=' + detailUrl);
                var html = fetchHTML(detailUrl);
                if (!html) {
                    print('>>> hxq detailContent empty html');
                    return result;
                }
                print('>>> hxq detailContent html len=' + html.length);

                // ===== 标题 =====
                var vod_name = reMatch(/<h1[^>]*class="[^"]*page-title[^"]*"[^>]*>([^<]+)<\/h1>/i, html);
                if (!vod_name) vod_name = reMatch(/<h1[^>]*>([^<]+)<\/h1>/i, html);
                if (!vod_name) vod_name = reMatch(/<meta[^>]*property="og:title"[^>]*content="([^"]+)"/, html);
                if (!vod_name) vod_name = reMatch(/<title>([^<]+)/, html);
                if (vod_name) vod_name = vod_name.replace(/\s*-\s*韩小圈.*$/, '').replace(/\s*-.*$/, '').trim();

                // ===== 封面 =====
                var vod_pic = '';
                var ogImg = reMatch(/<meta[^>]*property="og:image"[^>]*content="([^"]+)"/, html);
                if (ogImg) vod_pic = formatPic(ogImg);
                if (!vod_pic) {
                    var picMatch = html.match(/<img[^>]*class="[^"]*lazyload[^"]*"[^>]*data-src="([^"]*)"/);
                    if (picMatch) vod_pic = formatPic(picMatch[1]);
                }

                // ===== 导演/主演/年份/简介 =====
                var vod_director = '';
                var vod_actor = '';
                var vod_year = '';
                var vod_content = '';

                // 优先从 meta 标签提取
                var metaDirector = reMatch(/<meta[^>]*property="og:video:director"[^>]*content="([^"]+)"/, html);
                if (metaDirector) vod_director = metaDirector.trim();

                var metaActor = reMatch(/<meta[^>]*property="og:video:actor"[^>]*content="([^"]+)"/, html);
                if (metaActor) vod_actor = metaActor.trim();

                var metaDate = reMatch(/<meta[^>]*property="og:video:update_date"[^>]*content="([^"]+)"/, html);
                if (metaDate) vod_year = metaDate.split('-')[0];

                // 从 video-info-items 中提取（备用/补充）
                if (!vod_director) {
                    var dirMatch = html.match(/<span[^>]*class="[^"]*video-info-itemtitle[^"]*"[^>]*>导演[：:]<\/span>([\s\S]*?)<\/div>/);
                    if (dirMatch) vod_director = dirMatch[1].replace(/<[^>]+>/g, '').replace(/&nbsp;/g, '').trim();
                }
                if (!vod_actor) {
                    var actMatch = html.match(/<span[^>]*class="[^"]*video-info-itemtitle[^"]*"[^>]*>主演[：:]<\/span>([\s\S]*?)<\/div>/);
                    if (actMatch) vod_actor = actMatch[1].replace(/<[^>]+>/g, '').replace(/&nbsp;/g, '').replace(/\/$/, '').trim();
                }
                if (!vod_year) {
                    var yearMatch = html.match(/<span[^>]*class="[^"]*video-info-itemtitle[^"]*"[^>]*>上映[：:]<\/span>[\s\S]*?<div[^>]*class="[^"]*video-info-item[^"]*"[^>]*>([^<]*)</);
                    if (yearMatch) vod_year = yearMatch[1].trim();
                }

                // 简介
                var descMatch = html.match(/<span[^>]*class="[^"]*video-info-itemtitle[^"]*"[^>]*>剧情[：:]<\/span>[\s\S]*?<div[^>]*class="[^"]*video-info-content[^"]*"[^>]*>([\s\S]*?)<\/div>/);
                if (descMatch) vod_content = descMatch[1].replace(/<[^>]+>/g, '').trim();
                if (!vod_content) {
                    var metaDesc = reMatch(/<meta[^>]*property="og:description"[^>]*content="([^"]+)"/, html);
                    if (metaDesc) vod_content = metaDesc.trim();
                }

                print('>>> hxq detailContent name=' + vod_name + ' director=' + vod_director + ' actor=' + vod_actor);

                // ========== 提取播放列表 ==========
                var play_from = [];
                var play_url = [];

                // 匹配 nav-tabs 中的线路名（<li><a href="#playlist2" data-toggle="tab"><i class="icon-play"></i> 云播资源</a> <small>(83)</small></li>）
                var tabPattern = /<li[^>]*>\s*<a[^>]*href="#(playlist\d+)"[^>]*>([\s\S]*?)<\/a>\s*(?:<small>[^<]*<\/small>)?\s*<\/li>/gi;
                var tabMap = {}; // playlistId -> name
                var tm;
                while ((tm = tabPattern.exec(html)) !== null) {
                    var playlistId = tm[1];
                    var tabName = tm[2].replace(/<[^>]+>/g, '').replace(/&nbsp;/g, '').trim();
                    if (tabName && playlistId) {
                        tabMap[playlistId] = tabName;
                    }
                }
                print('>>> hxq detailContent tabMap=' + JSON.stringify(tabMap));

                // 匹配每个 tab-pane 中的剧集列表
                // 使用字符串索引方式提取 pane 内容，避免大 HTML 中正则回溯问题
                var tabPaneStartRe = /<div[^>]*id="(playlist\d+)"[^>]*class="[^"]*tab-pane[^"]*"[^>]*>/gi;
                var panePositions = [];
                var pm;
                while ((pm = tabPaneStartRe.exec(html)) !== null) {
                    panePositions.push({ id: pm[1], start: pm.index, end: pm.index + pm[0].length });
                }

                for (var pi = 0; pi < panePositions.length; pi++) {
                    var pp = panePositions[pi];
                    var pid = pp.id;
                    if (!tabMap[pid]) continue;

                    // pane 内容从 div 结束到下一个 playlist div 开始，或到 </div></div><script
                    var contentStart = pp.end;
                    var contentEnd;
                    if (pi + 1 < panePositions.length) {
                        contentEnd = panePositions[pi + 1].start;
                    } else {
                        // 最后一个 pane: 找到 </div>\s*</div>\s*<script
                        var endMarker = html.indexOf('</div>', contentStart);
                        // 跳过嵌套的 </div>，找到双 </div> 后跟 <script
                        var searchFrom = contentStart;
                        for (var di = 0; di < 3; di++) {
                            var divEnd = html.indexOf('</div>', searchFrom);
                            if (divEnd < 0) break;
                            searchFrom = divEnd + 6;
                        }
                        // 回退到倒数第二个 </div>
                        var lastDivEnd = html.lastIndexOf('</div>', searchFrom);
                        var prevDivEnd = html.lastIndexOf('</div>', lastDivEnd - 1);
                        contentEnd = prevDivEnd > contentStart ? prevDivEnd : searchFrom;
                    }
                    var paneContent = html.substring(contentStart, contentEnd);
                    var episodes = [];

                    // 提取每集：<li id="10"><a title="第01集" href="/play/4394-1-0.html" target="_self">第01集</a></li>
                    var epPattern = /<a[^>]*title="([^"]*)"[^>]*href="(\/play\/[^"]*)"[^>]*>/gi;
                    var em;
                    while ((em = epPattern.exec(paneContent)) !== null) {
                        var epName = em[1].trim();
                        var epHref = em[2];
                        if (epHref && epName) {
                            episodes.push(epName + '$' + epHref);
                        }
                    }

                    if (episodes.length > 0) {
                        play_from.push(tabMap[pid]);
                        play_url.push(episodes.join('#'));
                        print('>>> hxq detailContent line=' + tabMap[pid] + ' eps=' + episodes.length);
                    }
                }

                print('>>> hxq detailContent play_from=' + JSON.stringify(play_from));
                print('>>> hxq detailContent play_url count=' + play_url.length);

                result.list.push({
                    vod_id: vid,
                    vod_name: vod_name || vid,
                    vod_pic: vod_pic,
                    vod_director: vod_director,
                    vod_actor: vod_actor,
                    vod_year: vod_year,
                    vod_content: vod_content,
                    vod_play_from: play_from.join('$$$'),
                    vod_play_url: play_url.join('$$$')
                });

                return result;
            },

            // ========== 播放页 ==========
            playerContent: function(flag, id, vipFlags) {
                /*
                 * vbox 调用: playerContent(vodId, flag, playUrl)
                 * 映射: flag=vodId, id=flag名称, vipFlags=播放页URL
                 *
                 * 韩小圈播放页格式: /play/{vid}-{line}-{ep}.html
                 * 从页面提取: var now="m3u8_url";
                 */
                print('>>> hxq playerContent raw args: flag=' + flag + ' id=' + id + ' vipFlags=' + vipFlags);

                // 实际播放页 URL：优先取 vipFlags，其次 id，最后 flag
                var playUrl = vipFlags;
                if ((playUrl === undefined || playUrl === null || playUrl === '') && id) {
                    playUrl = id;
                }
                if (!playUrl || playUrl.indexOf('/play/') < 0) {
                    if (flag && flag.indexOf('/play/') >= 0) {
                        playUrl = flag;
                    } else if (id && id.indexOf('/play/') >= 0) {
                        playUrl = id;
                    }
                }

                print('>>> hxq playerContent playUrl=' + playUrl);

                if (!playUrl || playUrl.indexOf('/play/') < 0) {
                    print('>>> hxq playerContent invalid playUrl');
                    return { parse: 1, url: '', header: getPlayHeaders() };
                }

                if (playUrl.indexOf('http') !== 0) {
                    playUrl = HOST + playUrl;
                }

                var html = fetchHTML(playUrl);
                if (!html) {
                    print('>>> hxq playerContent empty html');
                    return { parse: 1, url: '', header: getPlayHeaders() };
                }

                // 提取 m3u8: var now="https://cdn.xxx/index.m3u8";
                var m3u8Match = html.match(/var\s+now\s*=\s*["']([^"']+)["']/);
                if (m3u8Match) {
                    var m3u8Url = m3u8Match[1];
                    print('>>> hxq playerContent m3u8=' + m3u8Url);
                    return { parse: 0, url: m3u8Url, header: getPlayHeaders() };
                }

                // 备用：player_aaaa 配置
                var playerMatch = html.match(/player_aaaa\s*=\s*(\{[^}]+\})/);
                if (playerMatch) {
                    try {
                        var config = JSON.parse(playerMatch[1]);
                        if (config.url) {
                            print('>>> hxq playerContent player_aaaa.url=' + config.url);
                            return { parse: 0, url: config.url, header: getPlayHeaders() };
                        }
                    } catch(e) {
                        print('>>> hxq playerContent player_aaaa parse error: ' + e);
                    }
                }

                // 兜底：直接搜索 m3u8 链接
                var fallbackM3u8 = html.match(/https?:\/\/[^\s"'<>]+\.m3u8[^\s"'<>]*/);
                if (fallbackM3u8) {
                    print('>>> hxq playerContent fallback m3u8=' + fallbackM3u8[0]);
                    return { parse: 0, url: fallbackM3u8[0], header: getPlayHeaders() };
                }

                print('>>> hxq playerContent no m3u8 found');
                return { parse: 1, url: '', header: getPlayHeaders() };
            },

            // ========== 搜索 ==========
            searchContent: function(key, quick, pg) {
                pg = pg || '1';
                var encodedKey = urlEncode(key);
                // 韩小圈实际搜索 URL: /search.php?searchword=KEYWORD
                var url = '/search.php?searchword=' + encodedKey + '&page=' + pg;
                print('>>> hxq searchContent url=' + url + ' key=' + key);

                var html = fetchHTML(url);
                if (!html) {
                    print('>>> hxq searchContent empty html');
                    return { list: [], page: parseInt(pg), pagecount: 1, limit: 36, total: 0 };
                }

                // 搜索页也是 module-item 结构，复用 parseModuleItems
                var videos = parseModuleItems(html);

                print('>>> hxq searchContent count=' + videos.length);
                return {
                    list: videos,
                    page: parseInt(pg),
                    pagecount: 1,
                    limit: 36,
                    total: videos.length
                };
            }
        };
    }
};