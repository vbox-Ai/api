/*
 * 袋鼠影视 JS 蜘蛛 v1.0
 * 适配 vbox-ios JSSpiderEngine (type:3 独立引擎)
 * 目标站: dsystv.com (HTML 页面抓取)
 * 流程: 首页/分类/搜索 → HTML正则提取 → 详情页解析播放线路 → 播放页提取m3u8直链
 */

var spider = {
    __jsEvalReturn: function() {
        var HOST = 'https://dsystv.com';
        var UA = 'Mozilla/5.0 (Linux; Android 11; SAMSUNG SM-G973U) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/87.0.4280.141 Mobile Safari/537.36';

        function getHeaders() {
            return {
                'User-Agent': UA,
                'Referer': HOST + '/',
                'Origin': HOST
            };
        }

        // HTTP 请求
        function fetch(url, options) {
            try {
                if (!options) options = {};
                if (!options.headers) options.headers = getHeaders();
                if (!options.method) options.method = 'GET';
                var resp = req(url, options);
                if (!resp) return '';
                var content = resp.content || '';
                return content;
            } catch (e) {
                print('>>> daishu fetch error: ' + e);
                return '';
            }
        }

        // 正则匹配（返回第一个捕获组）
        function match(text, rule) {
            var re = new RegExp(rule, 's');
            var m = re.exec(text || '');
            return m ? m[1] : '';
        }

        // 清理 HTML 标签和空白
        function clean(text) {
            return String(text || '')
                .replace(/<.*?>/g, ' ')
                .replace(/&nbsp;/g, ' ')
                .replace(/\s+/g, ' ')
                .trim();
        }

        // URL 补全
        function fixUrl(url) {
            if (!url) return '';
            if (url.indexOf('//') === 0) return 'https:' + url;
            if (url.indexOf('/') === 0) return HOST + url;
            return url;
        }

        // 判断是否为视频格式
        function isVideoFormat(url) {
            return /\.(m3u8|mp4|flv|avi|mkv|mov|ts)(\?|$|#)/i.test(url || '');
        }

        // 从首页导航栏动态提取分类列表
        // 匹配 <a href="/frim/index{id}.html">{name}</a>
        function parseCategories(html) {
            var classes = [];
            if (!html) return classes;
            var re = /<a[^>]+href=["']\/frim\/index(\d+)\.html["'][^>]*>(.*?)<\/a>/gi;
            var m;
            var seen = {};
            while ((m = re.exec(html)) !== null) {
                var tid = m[1];
                if (seen[tid]) continue;
                seen[tid] = true;
                var name = clean(m[2]);
                if (name) {
                    classes.push({ type_id: tid, type_name: name });
                }
            }
            return classes;
        }

        // 解析视频列表（首页/分类/搜索通用）
        function parseList(html) {
            var res = [];
            var seen = {};
            if (!html) return res;

            // 主正则: 匹配 videopic 链接
            var re = /<a[^>]+class=["'][^"']*videopic[^"']*["'][^>]+href=["']\/movie\/index(\d+)\.html["'][^>]*title=["']([^"']+)["']([\s\S]{0,1200}?)<\/a>/g;
            var m;
            while ((m = re.exec(html)) !== null) {
                var vid = m[1];
                if (seen[vid]) continue;
                seen[vid] = true;

                var itemHtml = m[0] + m[3];
                var name = clean(m[2]);

                // 提取封面图
                var pics = itemHtml.match(/(?:data-original|data-src)=["']([^"']+\.(?:jpg|jpeg|png|webp|gif)[^"']*)["']/i);
                if (!pics) {
                    pics = itemHtml.match(/src=["']([^"']+\.(?:jpg|jpeg|png|webp|gif)[^"']*)["']/i);
                }
                var pic = '';
                if (pics) {
                    var p = pics[1];
                    if (p.indexOf('load.gif') < 0 && p.indexOf('nopic') < 0 &&
                        p.indexOf('logo') < 0 && p.indexOf('templets') < 0) {
                        pic = fixUrl(p);
                    }
                }

                // 提取备注（更新状态）
                var remarks = clean(match(itemHtml, '<span[^>]+class=["\'][^"\']*note[^"\']*["\'][^>]*>(.*?)<\/span>') ||
                    match(itemHtml, '<span[^>]+class=["\'][^"\']*textbg[^"\']*["\'][^>]*>(.*?)<\/span>'));

                if (name) {
                    res.push({
                        vod_id: String(vid),
                        vod_name: name,
                        vod_pic: pic,
                        vod_remarks: remarks,
                        vod_year: '',
                        vod_area: ''
                    });
                }
            }

            // 回退正则: 无 videopic 的链接
            if (res.length === 0) {
                var re2 = /href=["']\/movie\/index(\d+)\.html["'][^>]*title=["']([^"']+)["'][\s\S]{0,1200}?<img[^>]+([^>]+)>/g;
                while ((m = re2.exec(html)) !== null) {
                    var vid2 = m[1];
                    if (seen[vid2]) continue;
                    seen[vid2] = true;

                    var imgAttr = m[3];
                    var pic2 = match(imgAttr, '(?:data-original|data-src)=["\']([^"\']+)["\']') ||
                        match(imgAttr, 'src=["\']([^"\']+)["\']');
                    if (pic2.indexOf('load.gif') >= 0 || pic2.indexOf('templets') >= 0) {
                        pic2 = '';
                    }

                    res.push({
                        vod_id: String(vid2),
                        vod_name: clean(m[2]),
                        vod_pic: fixUrl(pic2),
                        vod_remarks: '',
                        vod_year: '',
                        vod_area: ''
                    });
                }
            }

            return res;
        }

        return {
            init: function(config) {
                print('>>> daishu init: HOST=' + HOST);
                return true;
            },

            homeContent: function(filter) {
                var result = { class: [], list: [], filters: {} };

                // 先抓取首页 HTML
                var html = fetch(HOST + '/');

                // 动态提取导航栏分类，失败时回退到默认分类
                result.class = parseCategories(html);
                if (result.class.length === 0) {
                    print('>>> daishu homeContent: 动态提取分类失败，回退默认');
                    result.class = [
                        { type_id: '1', type_name: '电影' },
                        { type_id: '2', type_name: '电视剧' },
                        { type_id: '3', type_name: '综艺' },
                        { type_id: '4', type_name: '动漫' },
                        { type_id: '44', type_name: '短剧' }
                    ];
                }
                print('>>> daishu homeContent: class=' + result.class.length + '个分类');

                result.list = parseList(html);
                print('>>> daishu homeContent: list=' + result.list.length);

                result.page = 1;
                result.pagecount = 1;
                result.limit = 20;
                result.total = result.list.length;
                return result;
            },

            homeVideoContent: function() {
                return { list: [] };
            },

            categoryContent: function(tid, pg, extend) {
                var page = parseInt(pg) || 1;
                var url;
                if (page === 1) {
                    url = HOST + '/frim/index' + tid + '.html';
                } else {
                    url = HOST + '/search.php?searchtype=5&tid=' + tid + '&page=' + page;
                }

                var html = fetch(url);
                var list = parseList(html);
                print('>>> daishu categoryContent: tid=' + tid + ' page=' + page + ' list=' + list.length);

                return {
                    list: list,
                    page: page,
                    pagecount: 999,
                    limit: 24,
                    total: 999999
                };
            },

            detailContent: function(ids) {
                var vid = String(ids).split(',')[0].trim();
                print('>>> daishu detailContent: vid=' + vid);

                var html = fetch(HOST + '/movie/index' + vid + '.html');
                if (!html) {
                    print('>>> daishu detailContent: empty html');
                    return { list: [] };
                }

                // 提取标题
                var name = clean(match(html, '<h1[^>]*>(.*?)<\/h1>') ||
                    match(html, '<meta property="og:title" content="(.*?)"'));
                name = name.replace('全集在线观看 - 国产剧 | 袋鼠影视', '')
                    .replace('全集在线观看 - 袋鼠影视', '')
                    .replace('《', '').replace('》', '').trim();

                // 提取封面
                var pic = fixUrl(match(html, '<meta property="og:image" content="(.*?)"') ||
                    match(html, '<a[^>]+class="[^"]*videopic[^"]*"[\s\S]*?<img[^>]+(?:data-original|data-src)=["\']([^"\']+)') ||
                    match(html, '<a[^>]+class="[^"]*videopic[^"]*"[\s\S]*?<img[^>]+src=["\']([^"\']+)'));

                // 提取简介
                var desc = clean(match(html, '<div class="plot"[^>]*>\s*<p>(.*?)<\/p>') ||
                    match(html, '<meta property="og:description" content="(.*?)"'));

                // 提取演员、导演
                var actor = match(html, '<li[^>]+data-video-meta=["\']([^"\']*)["\'][^>]*><span class="text-muted">主演：');
                var director = match(html, '<li[^>]+data-video-meta=["\']([^"\']*)["\'][^>]*><span class="text-muted">导演：');

                // 提取年份、地区、语言、类型
                var year = clean(match(html, '年份：</span>([^<]+)'));
                var area = clean(match(html, '地区：</span>([^<]+)'));
                var lang = clean(match(html, '语言：</span>([^<]+)'));
                var cate = clean(match(html, '类型：</span><a[^>]*>(.*?)<\/a>'));

                // 提取备注
                var remarks = clean(match(html, '<span class="note textbg">(.*?)<\/span>'));

                // 解析播放线路
                var tabs = [];
                var tabRe = /<a class="option"[\s\S]*?title=["']([^"']+)["'][\s\S]*?<\/a>/g;
                var tabMatch;
                while ((tabMatch = tabRe.exec(html)) !== null) {
                    tabs.push(clean(tabMatch[1]));
                }

                var panels = [];
                var panelRe = /<div[^>]+class=["']playlist[^"']*["'][^>]*>\s*<ul[^>]*>([\s\S]*?)<\/ul>/g;
                var panelMatch;
                while ((panelMatch = panelRe.exec(html)) !== null) {
                    panels.push(panelMatch[1]);
                }

                var playFrom = [];
                var playUrl = [];

                for (var i = 0; i < panels.length; i++) {
                    var eps = [];
                    var p = panels[i];

                    // 先匹配带 title 的链接
                    var epRe = /<a[^>]+title=["']([^"']+)["'][^>]+href=["']([^"']*?\/play\/[^"']+)["']/g;
                    var epMatch;
                    while ((epMatch = epRe.exec(p)) !== null) {
                        var t = clean(epMatch[1]);
                        var u = fixUrl(epMatch[2]);
                        if (t && u) eps.push(t + '$' + u);
                    }

                    // 回退: 匹配不带 title 的链接
                    if (eps.length === 0) {
                        var epRe2 = /<a[^>]+href=["']([^"']*?\/play\/[^"']+)["'][^>]*>(.*?)<\/a>/g;
                        while ((epMatch = epRe2.exec(p)) !== null) {
                            var t2 = clean(epMatch[2]);
                            var u2 = fixUrl(epMatch[1]);
                            if (t2 && u2) eps.push(t2 + '$' + u2);
                        }
                    }

                    if (eps.length > 0) {
                        var key = (i < tabs.length) ? tabs[i] : ('线路' + (i + 1));
                        if (playFrom.indexOf(key) < 0) {
                            playFrom.push(key);
                            playUrl.push(eps.join('#'));
                        }
                    }
                }

                // 回退: 全局搜索 play 链接
                if (playUrl.length === 0) {
                    var eps2 = [];
                    var fallbackRe = new RegExp('<a[^>]+href=["\']([^"\']*?\\/play\\/' + vid + '-[^"\']+)["\'][^>]*>(.*?)<\\/a>', 'g');
                    var fbMatch;
                    while ((fbMatch = fallbackRe.exec(html)) !== null) {
                        var t3 = clean(fbMatch[2]) || '播放';
                        var u3 = fixUrl(fbMatch[1]);
                        if (t3 && u3) eps2.push(t3 + '$' + u3);
                    }
                    if (eps2.length > 0) {
                        playFrom.push('默认');
                        playUrl.push(eps2.join('#'));
                    }
                }

                print('>>> daishu detailContent: ' + playFrom.length + '条线路, name=' + name);

                return {
                    list: [{
                        vod_id: String(vid),
                        vod_name: name,
                        vod_pic: pic,
                        vod_remarks: remarks,
                        type_name: cate,
                        vod_year: year,
                        vod_area: area,
                        vod_lang: lang,
                        vod_actor: actor,
                        vod_director: director,
                        vod_content: desc,
                        vod_play_from: playFrom.join('$$$'),
                        vod_play_url: playUrl.join('$$$')
                    }]
                };
            },

            searchContent: function(key, quick, pg) {
                var keyword = String(key || '');
                var pageNum = parseInt(pg) || 1;

                // 兼容iOS引擎2参数调用: searchContent(keyword, pg)
                if (pageNum === 1 && quick !== undefined && typeof quick !== 'undefined') {
                    // 3参数模式: searchContent(key, quick, pg)
                }

                // 先 POST 搜索
                var html = '';
                try {
                    var resp = req(HOST + '/search.php', {
                        method: 'POST',
                        headers: getHeaders(),
                        data: 'searchword=' + encodeURIComponent(keyword)
                    });
                    if (resp && resp.content) {
                        html = typeof resp.content === 'object' ? JSON.stringify(resp.content) : resp.content;
                    }
                } catch (e) {
                    print('>>> daishu search POST error: ' + e);
                }

                var data = parseList(html);

                // 回退 GET 搜索
                if (data.length === 0) {
                    html = fetch(HOST + '/search.php?searchword=' + encodeURIComponent(keyword) + '&page=' + pageNum);
                    data = parseList(html);
                }

                print('>>> daishu searchContent: keyword=' + keyword + ' results=' + data.length);
                return {
                    list: data,
                    page: pageNum
                };
            },

            playerContent: function(vodId, flag, url) {
                try {
                    print('>>> daishu playerContent: url=' + (url || '').substring(0, 80));

                    // 请求播放页
                    var html = fetch(url);
                    if (!html) {
                        print('>>> daishu playerContent: empty html');
                        return { parse: 0, playUrl: null, url: url, header: { 'User-Agent': UA } };
                    }

                    // 提取 var now = "xxx"
                    var playUrl = match(html, 'var\\s+now\\s*=\\s*["\']([^"\']+)["\']');
                    print('>>> daishu playerContent: var now=' + (playUrl || '').substring(0, 80));

                    if (playUrl) {
                        // URL 解码
                        playUrl = decodeURIComponent(playUrl);
                        print('>>> daishu playerContent: decoded=' + playUrl.substring(0, 80));
                    } else {
                        // 回退: 尝试其他正则
                        playUrl = match(html, '(https?://[^"\'<>\\s]+\\.m3u8[^"\'<>\\s]*)') ||
                            match(html, '(https?://[^"\'<>\\s]+\\.mp4[^"\'<>\\s]*)') ||
                            match(html, 'source\\s*:\\s*["\']([^"\']+)');
                        if (playUrl) {
                            print('>>> daishu playerContent: 备用正则=' + playUrl.substring(0, 80));
                        }
                    }

                    if (!playUrl) {
                        playUrl = url; // 回退到原始URL
                    }

                    // 判断是否直链
                    var isDirect = isVideoFormat(playUrl);
                    print('>>> daishu playerContent: isDirect=' + isDirect + ' finalUrl=' + playUrl.substring(0, 80));

                    return {
                        parse: isDirect ? 0 : 1,
                        playUrl: null,
                        url: playUrl,
                        header: { 'User-Agent': UA }
                    };
                } catch (e) {
                    print('>>> daishu playerContent ERROR: ' + e);
                    return { parse: 0, playUrl: null, url: url, header: { 'User-Agent': UA } };
                }
            }
        };
    }
};
