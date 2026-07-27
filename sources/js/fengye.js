/**
 * 枫叶影院 JS 蜘蛛
 * 适配 vbox-ios JSSpiderEngine (JavaScriptCore / type:3 独立引擎)
 * 基于 Python 版 枫叶影院.py 移植
 *
 * 功能：
 *  - 首页分类 + 筛选
 *  - 分类列表（含 /label VIP精选 和 /cupfox-list 常规分类）
 *  - 搜索
 *  - 详情页 + 多线路剧集列表
 *  - 播放页：提取 player_aaaa -> 请求解析接口 -> 返回 m3u8 直链
 */

var spider = {};

var HOST = 'https://maihaolian.com';
var UA = 'Mozilla/5.0 (iPhone; CPU iPhone OS 16_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.0 Mobile/15E148 Safari/604.1';

// ===================== 通用 HTTP 请求（兼容多种引擎注入的函数）=====================
function httpRequest(url, options) {
    options = options || {};
    try {
        if (typeof req !== 'undefined') {
            return req(url, options);
        }
        if (typeof fetch !== 'undefined') {
            return fetch(url, options);
        }
        if (typeof http !== 'undefined') {
            return http(url, options);
        }
        print('[枫叶影院] 无可用 HTTP 函数');
        return null;
    } catch (e) {
        print('[枫叶影院] httpRequest error: ' + e);
        return null;
    }
}

// 提取响应文本（兼容不同返回结构）
function getRespText(resp) {
    if (!resp) return '';
    if (typeof resp === 'string') return resp;
    if (resp.content) return resp.content;
    if (resp.data) return resp.data;
    if (resp.body) return resp.body;
    if (resp.text) return resp.text;
    return '';
}

// 获取 HTML
function fetchHtml(url) {
    try {
        if (!url || url.indexOf('http') !== 0) {
            url = HOST + url;
        }
        var resp = httpRequest(url, {
            headers: {
                'User-Agent': UA,
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
                'Accept-Language': 'zh-CN,zh;q=0.9'
            },
            timeout: 15
        });
        return getRespText(resp);
    } catch (e) {
        print('[枫叶影院] fetchHtml error: ' + e);
        return '';
    }
}

// POST 请求（返回 JSON）
function postJson(url, data, headers) {
    try {
        var hdr = headers || {};
        hdr['User-Agent'] = hdr['User-Agent'] || UA;
        hdr['Content-Type'] = hdr['Content-Type'] || 'application/x-www-form-urlencoded';

        var bodyStr = '';
        if (typeof data === 'object') {
            var pairs = [];
            for (var k in data) {
                pairs.push(encodeURIComponent(k) + '=' + encodeURIComponent(data[k]));
            }
            bodyStr = pairs.join('&');
        } else {
            bodyStr = String(data);
        }

        var resp = httpRequest(url, {
            method: 'POST',
            headers: hdr,
            data: bodyStr,
            timeout: 15
        });
        var text = getRespText(resp);
        return JSON.parse(text);
    } catch (e) {
        print('[枫叶影院] postJson error: ' + e);
        return null;
    }
}

// 修复图片 URL
function fixPic(url) {
    if (!url) return '';
    if (url.indexOf('//') === 0) return 'https:' + url;
    return url.replace(/&amp;/g, '&');
}

// 去除 HTML 标签，提取纯文本
function stripHtml(html) {
    if (!html) return '';
    return html.replace(/<[^>]+>/g, ' ').replace(/\s+/g, ' ').trim();
}

// 规范化播放 id，兼容历史缓存里可能存在的重复拼接 id：73809-73809-8-1 -> 73809-8-1
function normalizePlayId(id) {
    id = String(id || '').trim();
    var duplicateMatch = id.match(/^(\d+)-\1-(.+)$/);
    if (duplicateMatch) {
        return duplicateMatch[1] + '-' + duplicateMatch[2];
    }
    return id;
}

// ===================== HTML 解析辅助 =====================

// 匹配所有符合条件的标签块（非贪婪）
function matchAll(html, regex) {
    var results = [];
    var match;
    // 复制正则避免全局标记导致的问题
    var re = new RegExp(regex.source, regex.flags.indexOf('g') >= 0 ? regex.flags : regex.flags + 'g');
    while ((match = re.exec(html)) !== null) {
        results.push(match);
    }
    return results;
}

// ===================== 列表解析 =====================

function parseVideoList(html) {
    var videos = [];
    var seen = {};

    // 匹配所有 public-list-exp 卡片（从 <a 开始，跨行匹配到 </a>）
    var cardRe = /<a\s+[^>]*class=["'][^"']*public-list-exp[^"']*["'][^>]*>([\s\S]*?)<\/a>/gi;
    var cards = matchAll(html, cardRe);

    for (var i = 0; i < cards.length; i++) {
        var cardBlock = cards[i][1] || '';
        var fullTag = cards[i][0] || '';

        // 从完整标签提取 href
        var hrefMatch = fullTag.match(/href=["']([^"']+)["']/i);
        var href = hrefMatch ? hrefMatch[1] : '';

        var m = href.match(/\/detail\/(\d+)\.html/);
        if (!m) continue;
        var vodId = m[1];
        if (seen[vodId]) continue;
        seen[vodId] = true;

        // 提取 title（从 a 标签属性）
        var title = '';
        var titleMatch = fullTag.match(/title=["']([^"']*)["']/i);
        if (titleMatch) title = titleMatch[1];

        // 提取图片
        var pic = '';
        var picMatch = cardBlock.match(/<img[^>]*data-src=["']([^"']+)["']/i);
        if (picMatch) pic = fixPic(picMatch[1]);
        if (!pic) {
            var srcMatch = cardBlock.match(/<img[^>]*src=["']([^"']+)["']/i);
            if (srcMatch) pic = fixPic(srcMatch[1]);
        }

        // 如果没 title，取 img alt
        if (!title) {
            var altMatch = cardBlock.match(/<img[^>]*alt=["']([^"']*)["']/i);
            if (altMatch) title = altMatch[1];
        }

        // 提取年份标签
        var year = '';
        var yearMatches = matchAll(cardBlock, /<span[^>]*class=["'][^"']*public-prt[^"']*["'][^>]*>([^<]*)<\/span>/gi);
        var yearParts = [];
        for (var j = 0; j < yearMatches.length; j++) {
            yearParts.push(yearMatches[j][1].trim());
        }
        year = yearParts.join(',');

        // 提取备注
        var remark = '';
        var remarkMatch = cardBlock.match(/<[^>]*class=["'][^"']*(?:ft2|public-list-prb)[^"']*["'][^>]*>([^<]*)<\/[^>]*>/i);
        if (remarkMatch) remark = remarkMatch[1].trim();

        videos.push({
            vod_id: vodId,
            vod_name: title.trim(),
            vod_pic: pic,
            vod_remarks: remark,
            vod_year: year
        });
    }

    return videos;
}

function parseSearchList(html) {
    var videos = [];
    var seen = {};

    var cardRe = /<a\s+[^>]*class=["'][^"']*public-list-exp[^"']*["'][^>]*>([\s\S]*?)<\/a>/gi;
    var cards = matchAll(html, cardRe);

    for (var i = 0; i < cards.length; i++) {
        var cardBlock = cards[i][1] || '';
        var fullTag = cards[i][0] || '';

        var hrefMatch = fullTag.match(/href=["']([^"']+)["']/i);
        var href = hrefMatch ? hrefMatch[1] : '';

        var m = href.match(/\/detail\/(\d+)\.html/);
        if (!m) continue;
        var vodId = m[1];
        if (seen[vodId]) continue;
        seen[vodId] = true;

        var title = '';
        var titleMatch = fullTag.match(/title=["']([^"']*)["']/i);
        if (titleMatch) title = titleMatch[1];

        var pic = '';
        var picMatch = cardBlock.match(/<img[^>]*data-src=["']([^"']+)["']/i);
        if (picMatch) pic = fixPic(picMatch[1]);

        if (!title) {
            var altMatch = cardBlock.match(/<img[^>]*alt=["']([^"']*)["']/i);
            if (altMatch) title = altMatch[1];
        }

        var remark = '';
        var remarkMatch = cardBlock.match(/<[^>]*class=["'][^"']*(?:public-list-prb|ft2)[^"']*["'][^>]*>([^<]*)<\/[^>]*>/i);
        if (remarkMatch) remark = remarkMatch[1].trim();

        // 搜索页标题也可能在 thumb-txt 中（这里简化处理，用卡片内信息）
        videos.push({
            vod_id: vodId,
            vod_name: title.trim(),
            vod_pic: pic,
            vod_remarks: remark
        });
    }

    return videos;
}

// ===================== TVBox 标准蜘蛛接口 =====================

spider.init = function(config) {
    return true;
};

spider.homeContent = function(filter) {
    var classes = [
        { type_id: '/label/qq', type_name: '腾讯VIP精选' },
        { type_id: '/label/bli', type_name: 'B站VIP精选' },
        { type_id: '/label/youku', type_name: '优酷VIP精选' },
        { type_id: '5', type_name: '红果短剧' },
        { type_id: '2', type_name: '电视剧' },
        { type_id: '1', type_name: '电影' },
        { type_id: '4', type_name: '动漫' },
        { type_id: '3', type_name: '综艺' }
    ];

    var area = [{"n":"全部","v":""},{"n":"大陆","v":"大陆"},{"n":"香港","v":"香港"},{"n":"台湾","v":"台湾"},{"n":"美国","v":"美国"},{"n":"韩国","v":"韩国"},{"n":"日本","v":"日本"},{"n":"泰国","v":"泰国"},{"n":"新加坡","v":"新加坡"},{"n":"马来西亚","v":"马来西亚"},{"n":"印度","v":"印度"},{"n":"英国","v":"英国"},{"n":"法国","v":"法国"},{"n":"加拿大","v":"加拿大"},{"n":"西班牙","v":"西班牙"},{"n":"俄罗斯","v":"俄罗斯"},{"n":"其它","v":"其它"}];
    var year = [{"n":"全部","v":""},{"n":"2026","v":"2026"},{"n":"2025","v":"2025"},{"n":"2024","v":"2024"},{"n":"2023","v":"2023"},{"n":"2022","v":"2022"},{"n":"2021","v":"2021"},{"n":"2020","v":"2020"},{"n":"2019","v":"2019"},{"n":"2018","v":"2018"},{"n":"2017","v":"2017"},{"n":"2016","v":"2016"},{"n":"2015","v":"2015"},{"n":"2014","v":"2014"},{"n":"2013","v":"2013"},{"n":"2012","v":"2012"},{"n":"2011","v":"2011"},{"n":"2010","v":"2010"},{"n":"2009","v":"2009"},{"n":"2008","v":"2008"},{"n":"2007","v":"2007"},{"n":"2006","v":"2006"},{"n":"2005","v":"2005"},{"n":"2004","v":"2004"}];
    var lang = [{"n":"全部","v":""},{"n":"国语","v":"国语"},{"n":"英语","v":"英语"},{"n":"粤语","v":"粤语"},{"n":"闽南语","v":"闽南语"},{"n":"韩语","v":"韩语"},{"n":"日语","v":"日语"},{"n":"法语","v":"法语"},{"n":"德语","v":"德语"},{"n":"其它","v":"其它"}];
    var sort = [{"n":"时间","v":"time"},{"n":"人气","v":"hits"},{"n":"评分","v":"score"}];
    var letter = [{"n":"全部","v":""},{"n":"A","v":"A"},{"n":"B","v":"B"},{"n":"C","v":"C"},{"n":"D","v":"D"},{"n":"E","v":"E"},{"n":"F","v":"F"},{"n":"G","v":"G"},{"n":"H","v":"H"},{"n":"I","v":"I"},{"n":"J","v":"J"},{"n":"K","v":"K"},{"n":"L","v":"L"},{"n":"M","v":"M"},{"n":"N","v":"N"},{"n":"O","v":"O"},{"n":"P","v":"P"},{"n":"Q","v":"Q"},{"n":"R","v":"R"},{"n":"S","v":"S"},{"n":"T","v":"T"},{"n":"U","v":"U"},{"n":"V","v":"V"},{"n":"W","v":"W"},{"n":"X","v":"X"},{"n":"Y","v":"Y"},{"n":"Z","v":"Z"},{"n":"0-9","v":"0-9"}];

    var filters = {
        '2': [
            {key:'class',name:'类型',value:[{"n":"全部","v":"2"},{"n":"国产剧","v":"13"},{"n":"日韩剧","v":"15"},{"n":"海外剧","v":"16"}]},
            {key:'area',name:'地区',value:area},
            {key:'genre',name:'剧情',value:[{"n":"全部","v":""},{"n":"古装","v":"古装"},{"n":"战争","v":"战争"},{"n":"青春偶像","v":"青春偶像"},{"n":"喜剧","v":"喜剧"},{"n":"家庭","v":"家庭"},{"n":"犯罪","v":"犯罪"},{"n":"动作","v":"动作"},{"n":"奇幻","v":"奇幻"},{"n":"剧情","v":"剧情"},{"n":"历史","v":"历史"},{"n":"经典","v":"经典"},{"n":"乡村","v":"乡村"},{"n":"情景","v":"情景"},{"n":"商战","v":"商战"},{"n":"网剧","v":"网剧"},{"n":"其他","v":"其他"}]},
            {key:'year',name:'年份',value:year},
            {key:'lang',name:'语言',value:lang},
            {key:'letter',name:'字母',value:letter},
            {key:'sort',name:'排序',value:sort}
        ],
        '1': [
            {key:'class',name:'类型',value:[{"n":"全部","v":"1"},{"n":"动作片","v":"6"},{"n":"喜剧片","v":"7"},{"n":"恐怖片","v":"8"},{"n":"科幻片","v":"9"},{"n":"爱情片","v":"10"},{"n":"剧情片","v":"11"},{"n":"战争片","v":"12"},{"n":"纪录片","v":"20"}]},
            {key:'area',name:'地区',value:area},
            {key:'genre',name:'剧情',value:[{"n":"全部","v":""},{"n":"喜剧","v":"喜剧"},{"n":"爱情","v":"爱情"},{"n":"恐怖","v":"恐怖"},{"n":"动作","v":"动作"},{"n":"科幻","v":"科幻"},{"n":"剧情","v":"剧情"},{"n":"战争","v":"战争"},{"n":"警匪","v":"警匪"},{"n":"犯罪","v":"犯罪"},{"n":"动画","v":"动画"},{"n":"奇幻","v":"奇幻"},{"n":"武侠","v":"武侠"},{"n":"冒险","v":"冒险"},{"n":"枪战","v":"枪战"},{"n":"悬疑","v":"悬疑"},{"n":"惊悚","v":"惊悚"},{"n":"经典","v":"经典"},{"n":"青春","v":"青春"},{"n":"文艺","v":"文艺"},{"n":"微电影","v":"微电影"},{"n":"古装","v":"古装"},{"n":"历史","v":"历史"},{"n":"运动","v":"运动"},{"n":"农村","v":"农村"},{"n":"儿童","v":"儿童"},{"n":"网络电影","v":"网络电影"}]},
            {key:'year',name:'年份',value:year},
            {key:'lang',name:'语言',value:lang},
            {key:'letter',name:'字母',value:letter},
            {key:'sort',name:'排序',value:sort}
        ],
        '4': [
            {key:'class',name:'类型',value:[{"n":"全部","v":"4"},{"n":"国产动漫","v":"25"},{"n":"日韩动漫","v":"26"}]},
            {key:'genre',name:'剧情',value:[{"n":"全部","v":""},{"n":"情感","v":"情感"},{"n":"科幻","v":"科幻"},{"n":"热血","v":"热血"},{"n":"推理","v":"推理"},{"n":"搞笑","v":"搞笑"},{"n":"冒险","v":"冒险"},{"n":"奇幻","v":"奇幻"},{"n":"战斗","v":"战斗"},{"n":"校园","v":"校园"},{"n":"萝莉","v":"萝莉"},{"n":"治愈","v":"治愈"},{"n":"原创","v":"原创"},{"n":"亲子","v":"亲子"},{"n":"益智","v":"益智"},{"n":"励志","v":"励志"},{"n":"其他","v":"其他"}]},
            {key:'area',name:'地区',value:[{"n":"全部","v":""},{"n":"大陆","v":"大陆"},{"n":"香港","v":"香港"},{"n":"台湾","v":"台湾"},{"n":"美国","v":"美国"},{"n":"韩国","v":"韩国"},{"n":"日本","v":"日本"},{"n":"法国","v":"法国"},{"n":"英国","v":"英国"},{"n":"其它","v":"其它"}]},
            {key:'year',name:'年份',value:year},
            {key:'lang',name:'语言',value:lang},
            {key:'letter',name:'字母',value:letter},
            {key:'sort',name:'排序',value:sort}
        ],
        '3': [
            {key:'class',name:'类型',value:[{"n":"全部","v":"3"},{"n":"大陆综艺","v":"21"},{"n":"日韩综艺","v":"22"}]},
            {key:'genre',name:'剧情',value:[{"n":"全部","v":""},{"n":"选秀","v":"选秀"},{"n":"情感","v":"情感"},{"n":"访谈","v":"访谈"},{"n":"播报","v":"播报"},{"n":"音乐","v":"音乐"},{"n":"美食","v":"美食"},{"n":"旅游","v":"旅游"},{"n":"搞笑","v":"搞笑"},{"n":"游戏","v":"游戏"},{"n":"亲子","v":"亲子"},{"n":"其它","v":"其它"}]},
            {key:'area',name:'地区',value:[{"n":"全部","v":""},{"n":"大陆","v":"大陆"},{"n":"香港","v":"香港"},{"n":"台湾","v":"台湾"},{"n":"美国","v":"美国"},{"n":"韩国","v":"韩国"},{"n":"日本","v":"日本"},{"n":"英国","v":"英国"},{"n":"其它","v":"其它"}]},
            {key:'year',name:'年份',value:year},
            {key:'lang',name:'语言',value:lang},
            {key:'letter',name:'字母',value:letter},
            {key:'sort',name:'排序',value:sort}
        ]
    };

    return JSON.stringify({
        class: classes,
        filters: filters
    });
};

spider.homeVideoContent = function() {
    var html = fetchHtml('/');
    var list = parseVideoList(html);
    return JSON.stringify({ list: list });
};

spider.categoryContent = function(tid, pg, filter, extend) {
    pg = pg || 1;
    tid = tid || '';

    // /label 路径（VIP精选）
    if (tid.indexOf('/label') === 0) {
        var url = tid + '/page/' + pg + '.html';
        var html = fetchHtml(url);
        var items = parseVideoList(html);
        var page = parseInt(pg);
        var pageCount = items.length < 24 ? page : page + 2;
        return JSON.stringify({
            list: items,
            page: page,
            pagecount: pageCount,
            limit: 24,
            total: pageCount * 24
        });
    }

    // 解析筛选参数
    var args = {};
    if (extend && typeof extend === 'object') {
        for (var k in extend) {
            if (extend[k]) args[k] = String(extend[k]);
        }
    }
    if (filter && typeof filter === 'object') {
        for (var k in filter) {
            if (filter[k] && !args[k]) args[k] = String(filter[k]);
        }
    }

    var routeTid = args['class'] || args['tid'] || String(tid);
    var area = args['area'] || '';
    var genre = args['genre'] || '';
    var year = args['year'] || '';
    var lang = args['lang'] || '';
    var letter = args['letter'] || '';
    var sort = args['sort'] || '';

    // 无筛选走正常分页
    if (!area && !genre && !year && !lang && !letter && !sort) {
        var url2 = '/cupfox-list/' + routeTid + '--------' + pg + '---.html';
        var html2 = fetchHtml(url2);
        var items2 = parseVideoList(html2);
        var page2 = parseInt(pg);
        var pageCount2 = page2;

        // 提取尾页
        var lastPageMatch = html2.match(/<a[^>]*class=["'][^"']*page-link[^"']*["'][^>]*href=["'][^"']*---(\d+)---[^"']*["'][^>]*>尾页<\/a>/i);
        if (lastPageMatch) {
            pageCount2 = parseInt(lastPageMatch[1]);
        }
        if (!items2.length) pageCount2 = 0;

        return JSON.stringify({
            list: items2,
            page: page2,
            pagecount: pageCount2,
            limit: 36,
            total: 9999
        });
    }

    // 有筛选
    var segs = [routeTid, area, sort, genre, lang, letter, '', '', year];
    var url3 = '/cupfox-list/' + segs.join('-') + '.html';
    var html3 = fetchHtml(url3);
    var items3 = parseVideoList(html3);
    return JSON.stringify({
        list: items3,
        page: 1,
        pagecount: 1,
        limit: 36,
        total: 9999
    });
};

spider.detailContent = function(ids) {
    var result = { list: [] };
    try {
        var vid = String(ids).split(',')[0].trim();
        var html = fetchHtml('/detail/' + vid + '.html');
        if (!html) return JSON.stringify(result);

        // 标题
        var titleMatch = html.match(/<h3[^>]*class=["'][^"']*slide-info-title[^"']*["'][^>]*>([\s\S]*?)<\/h3>/i);
        var vodName = titleMatch ? stripHtml(titleMatch[1]) : '';

        // 图片
        var picMatch = html.match(/<img[^>]*class=["'][^"']*lazy[^"']*["'][^>]*data-src=["']([^"']+)["']/i);
        var vodPic = picMatch ? fixPic(picMatch[1]) : '';

        // 导演 / 演员
        var vodDirector = '';
        var vodActor = '';
        var infoRe = /<[^>]*class=["'][^"']*slide-info[^"']*["'][^>]*>([\s\S]*?)<\/[^>]*>/gi;
        var infoMatches = matchAll(html, infoRe);
        for (var i = 0; i < infoMatches.length; i++) {
            var text = stripHtml(infoMatches[i][1]);
            if (text.indexOf('导演：') === 0) {
                vodDirector = text.replace('导演：', '').trim();
            } else if (text.indexOf('演员：') === 0) {
                vodActor = text.replace('演员：', '').trim();
            }
        }

        // 简介
        var contentMatch = html.match(/<[^>]*id=["']height_limit["'][^>]*>([\s\S]*?)<\/[^>]*>/i);
        var vodContent = contentMatch ? stripHtml(contentMatch[1]) : '';

        // 播放源名称
        var playFrom = [];
        var tabRe = /<[^>]*class=["'][^"']*anthology-tab[^"']*["'][^>]*>[\s\S]*?<a[^>]*class=["'][^"']*swiper-slide[^"']*["'][^>]*>([\s\S]*?)<\/a>/gi;
        var tabMatches = matchAll(html, tabRe);
        // 上面正则跨标签匹配容易失效，换一种：先提取 anthology-tab 区域，再在区域内匹配 swiper-slide
        var tabAreaMatch = html.match(/<[^>]*class=["'][^"']*anthology-tab[^"']*["'][^>]*>([\s\S]*?)<\/div>/i);
        if (tabAreaMatch) {
            var tabArea = tabAreaMatch[1];
            var slideRe = /<a[^>]*class=["'][^"']*swiper-slide[^"']*["'][^>]*>([\s\S]*?)<\/a>/gi;
            var slideMatches = matchAll(tabArea, slideRe);
            for (var s = 0; s < slideMatches.length; s++) {
                var tabText = stripHtml(slideMatches[s][1]).trim();
                if (tabText) playFrom.push(tabText);
            }
        }

        // 剧集列表：提取所有 anthology-list-box
        var playUrl = [];
        var boxMatches = html.match(/<div[^>]*class=["'][^"']*anthology-list-box[^"']*["'][^>]*>[\s\S]*?<\/div>/gi);
        if (boxMatches) {
            for (var b = 0; b < boxMatches.length; b++) {
                var boxHtml = boxMatches[b];
                var epList = [];
                var epRe = /<li[^>]*>[\s\S]*?<a[^>]*href=["']([^"']+)["'][^>]*>([\s\S]*?)<\/a>[\s\S]*?<\/li>/gi;
                var epMatches = matchAll(boxHtml, epRe);
                for (var e = 0; e < epMatches.length; e++) {
                    var href = epMatches[e][1];
                    var epName = stripHtml(epMatches[e][2]).trim();
                    var playMatch = href.match(/\/play\/(.*?)\.html/);
                    if (playMatch) {
                        epList.push(epName + '$' + normalizePlayId(playMatch[1]));
                    }
                }
                epList.reverse();
                if (epList.length && b < playFrom.length) {
                    playUrl.push(epList.join('#'));
                }
            }
        }

        var validFrom = [];
        for (var f = 0; f < playFrom.length; f++) {
            if (f < playUrl.length) validFrom.push(playFrom[f]);
        }

        result.list.push({
            vod_id: vid,
            vod_name: vodName,
            vod_pic: vodPic,
            vod_director: vodDirector,
            vod_actor: vodActor,
            vod_content: vodContent,
            vod_play_from: validFrom.join('$$$'),
            vod_play_url: playUrl.join('$$$')
        });
    } catch (e) {
        print('[枫叶影院] detailContent error: ' + e);
    }
    return JSON.stringify(result);
};

spider.searchContent = function(key, quick, pg) {
    pg = pg || '1';
    try {
        var keyword = decodeURIComponent(key);
    } catch (e) {
        keyword = key;
    }
    var encoded = encodeURIComponent(keyword);
    var url = '/cupfox-search/' + encoded + '----------' + pg + '---.html';
    var html = fetchHtml(url);
    var items = parseSearchList(html);
    return JSON.stringify({
        list: items,
        page: parseInt(pg),
        pagecount: 1,
        limit: 36,
        total: items.length
    });
};

spider.playerContent = function(vodId, flag, urlParam) {
    var url = '';
    try {
        // vbox 调用顺序为 playerContent(vodId, flag, url)
        // 兼容 TVBox 常见顺序 playerContent(flag, id, vipFlags)
        var id = '';
        if (urlParam && typeof urlParam === 'string' && urlParam !== 'undefined' && urlParam !== 'null') {
            id = urlParam;
        } else if (flag && typeof flag === 'string' && flag !== 'play') {
            id = flag;
        } else {
            id = vodId;
        }
        id = normalizePlayId(id);

        url = (id.indexOf('http') === 0) ? id : HOST + '/play/' + id + '.html';
        var html = fetchHtml(url);
        if (!html) return JSON.stringify({ parse: 1, url: url });

        // 提取 player_aaaa JSON
        var m = html.match(/player_aaaa\s*=\s*({[\s\S]*?})<\/script>/i);
        if (!m) return JSON.stringify({ parse: 1, url: url });

        var pd;
        try {
            pd = JSON.parse(m[1]);
        } catch (e) {
            print('[枫叶影院] player_aaaa parse error: ' + e);
            pd = {};
        }

        var playUrl = pd.url || '';
        var playId = pd.from || '';

        var zzrsParser = 'https://zzrs.mfdyvip.com/player/';
        var fgsrgParser = 'https://fgsrg.hzqingshan.com/player/';
        var parserBaseMap = {
            'YYNB': [zzrsParser, fgsrgParser],
            'BBA': [zzrsParser, fgsrgParser],
            'co': [zzrsParser, fgsrgParser],
            'youku': [zzrsParser, fgsrgParser],
            'qq': [zzrsParser, fgsrgParser],
            'bilibili': [zzrsParser, fgsrgParser],
            'qiyi': [zzrsParser, fgsrgParser],
            'JD2K': [fgsrgParser, zzrsParser],
            'JD4K': [fgsrgParser, zzrsParser]
        };

        if (!playUrl) {
            return JSON.stringify({
                parse: 0,
                url: 'https://php.doube.eu.org/error.m3u8',
                header: { 'User-Agent': 'Mozilla/5.0' }
            });
        }

        // 已经是直链
        if (playUrl.indexOf('http') === 0 && (playUrl.indexOf('.m3u8') !== -1 || playUrl.indexOf('.mp4') !== -1)) {
            return JSON.stringify({
                parse: 0,
                url: playUrl,
                header: { 'User-Agent': 'Mozilla/5.0' }
            });
        }

        // 需要走解析接口
        var headers = {
            'User-Agent': 'Mozilla/5.0 (Linux; Android 10; K) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/137.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7',
            'accept-language': 'zh-CN,zh;q=0.9',
            'cache-control': 'no-cache',
            'pragma': 'no-cache',
            'priority': 'u=0, i',
            'referer': 'https://www.ht10010.com/',
            'Content-Type': 'application/x-www-form-urlencoded'
        };

        var parserBases = parserBaseMap[playId];
        if (!parserBases || !parserBases.length) {
            return JSON.stringify({
                parse: 0,
                url: 'https://php.doube.eu.org/error.m3u8',
                header: { 'User-Agent': 'Mozilla/5.0' }
            });
        }

        // 按播放线路尝试主解析和备用解析，只使用枫叶影院站点已有的两个解析域名
        for (var pi = 0; pi < parserBases.length; pi++) {
            var parserBase = parserBases[pi];
            try {
                var tokenUrl = parserBase + '?url=' + encodeURIComponent(playUrl);
                var tokenResp = httpRequest(tokenUrl, { headers: headers, timeout: 10 });
                var tokenText = getRespText(tokenResp);
                var tokenMatch = tokenText.match(/data-te=["']([^"']+)["']/i);
                if (!tokenMatch) {
                    print('[枫叶影院] parser token miss: ' + playId + ' -> ' + parserBase);
                    continue;
                }

                var token = tokenMatch[1];
                var payload = { url: playUrl, token: token };
                var apiUrl = parserBase + 'mplayer.php';
                var result = postJson(apiUrl, payload, headers);
                if (result && result.code === 200 && result.url && String(result.url).indexOf('http') === 0) {
                    return JSON.stringify({
                        parse: 0,
                        url: result.url,
                        header: {
                            'User-Agent': 'Mozilla/5.0 (iPhone; CPU iPhone OS 16_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.0 Mobile/15E148 Safari/604.1'
                        }
                    });
                }
                print('[枫叶影院] parser failed: ' + playId + ' -> ' + parserBase + ' result=' + JSON.stringify(result || {}));
            } catch (pe) {
                print('[枫叶影院] parser error: ' + playId + ' -> ' + parserBase + ' error=' + pe);
            }
        }
    } catch (e) {
        print('[枫叶影院] playerContent error: ' + e);
    }
    return JSON.stringify({
        parse: 0,
        url: 'https://php.doube.eu.org/error.m3u8',
        header: { 'User-Agent': 'Mozilla/5.0' }
    });
};

spider.localProxy = function(param) {
    return JSON.stringify({});
};
