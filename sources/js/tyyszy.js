/*
 * TY影视 JS 蜘蛛 v1.0
 * 适配 vbox-ios JSSpiderEngine (type:3 独立引擎)
 * 目标站: https://www.tyyszy.com  /  API: https://tyyszyapi.com
 *
 * 背景：TY影视原为 .api 采集源，其 ac=home/list 返回的 class[].type_id 为数字，
 * vbox-ios 的 VodCategory.typeId 为 String，JSON 解码失败后客户端降级抓取域名首页 HTML，
 * 并为每条结果强制添加 "☁️" 前缀到 vod_remarks，导致详情页被误判为网盘资源。
 * 改为 JS 蜘蛛后由脚本控制字段类型与 vod_remarks，从根上规避该问题。
 *
 * 实现策略：
 *   - class / 首页列表：走 API（ac=list 取分类，ac=detail 取带封面的最新列表），type_id 统一转字符串。
 *   - 分类 / 搜索：走站点 HTML（/index.php/vod/type|search/...），支持父分类，解析 movie-card。
 *   - 详情：走 API ac=detail&ids=，vod_play_url 直接返回标准 CMS 格式（第N集$m3u8直链），可直连播放。
 *   - vod_remarks 保持原始值（如“更新第12集”），绝不添加 "☁️"。
 */

var spider = {
    __jsEvalReturn: function() {
        var API = 'https://tyyszyapi.com/api.php/provide/vod';
        var SITE = 'https://www.tyyszy.com';

        var UA = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36';
        var HEADERS = {
            'User-Agent': UA,
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
            'Referer': SITE + '/'
        };

        // ===================== 工具函数 =====================

        function httpGet(url, headers) {
            try {
                var resp = req(url, { method: 'GET', headers: headers || HEADERS });
                if (!resp) { print('>>> tyyszy fetch null: ' + url); return ''; }
                var content = resp.content || resp.data || '';
                if (typeof content === 'object') content = JSON.stringify(content);
                return content;
            } catch (e) {
                print('>>> tyyszy fetch ERROR: ' + e + ' url=' + url);
                return '';
            }
        }

        function getJSON(url) {
            var text = httpGet(url);
            if (!text) return null;
            try {
                return JSON.parse(text);
            } catch (e) {
                print('>>> tyyszy JSON ERROR: ' + e + ' url=' + url);
                return null;
            }
        }

        function stripHtml(s) {
            if (!s) return '';
            s = String(s).replace(/<br\s*\/?>/gi, '\n');
            s = s.replace(/<[^>]+>/g, '');
            s = s.replace(/&nbsp;/gi, ' ').replace(/&amp;/gi, '&')
                 .replace(/&lt;/gi, '<').replace(/&gt;/gi, '>').replace(/&quot;/gi, '"');
            return s.trim();
        }

        function absUrl(u) {
            if (!u) return '';
            u = String(u).trim();
            if (u.indexOf('http') === 0) return u;
            if (u.indexOf('//') === 0) return 'https:' + u;
            if (u.indexOf('/') === 0) return SITE + u;
            return u;
        }

        // 归一化 API 返回的列表项（type_id 等数字字段统一转字符串，vod_remarks 原样保留）
        function normApiItem(it) {
            return {
                vod_id: String(it.vod_id),
                vod_name: String(it.vod_name || ''),
                vod_pic: absUrl(it.vod_pic || ''),
                vod_remarks: it.vod_remarks ? String(it.vod_remarks) : '',
                vod_year: it.vod_year != null ? String(it.vod_year) : '',
                vod_area: it.vod_area ? String(it.vod_area) : ''
            };
        }

        // 解析站点 HTML 中的 movie-card 列表（首页/分类/搜索通用）
        function parseCards(html) {
            var out = [];
            if (!html) return out;
            var re = /<a\s+href="\/index\.php\/vod\/detail\/id\/(\d+)\.html"\s+class="movie-card"[^>]*>([\s\S]*?)<\/a>/gi;
            var m;
            while ((m = re.exec(html)) !== null) {
                var vid = m[1];
                var block = m[2];
                var name = '';
                var nameM = block.match(/<span>\s*([^<]+?)\s*<\/span>/);
                if (nameM) name = nameM[1].trim();
                var picM = block.match(/data-src="([^"]+)"/) || block.match(/\bsrc="([^"]+)"/);
                var pic = picM ? picM[1] : '';
                if (pic && pic.indexOf('loading.') >= 0) pic = '';
                var remark = '';
                var remM = block.match(/episode-status"[^>]*>([\s\S]*?)<\/div>/);
                if (remM) remark = stripHtml(remM[1]);
                out.push({
                    vod_id: vid,
                    vod_name: name || vid,
                    vod_pic: absUrl(pic),
                    vod_remarks: remark
                });
            }
            return out;
        }

        // 从分页链接推断总页数
        function parsePageCount(html, type) {
            if (!html) return 1;
            var max = 1;
            var prefix = type === 'search' ? '/index.php/vod/search/page/(\\d+)/' : '/index.php/vod/type/id/\\d+/page/(\\d+)\\.html';
            var re = new RegExp(prefix, 'gi');
            var m;
            while ((m = re.exec(html)) !== null) {
                var n = parseInt(m[1], 10);
                if (n > max) max = n;
            }
            return max;
        }

        // 站点成人/擦边分类，列表与浏览均过滤
        var BLOCKED_TIDS = { '55': 1, '56': 1, '57': 1, '58': 1, '59': 1, '60': 1, '61': 1, '73': 1 };

        // API 分类列表（type_id 转字符串，缓存一次）
        var classCache = null;
        function getClasses() {
            if (classCache && classCache.length) return classCache;
            var data = getJSON(API + '?ac=list&pg=1');
            if (!data || !data['class']) return [];
            var classes = [];
            var arr = data['class'];
            for (var i = 0; i < arr.length; i++) {
                if (!arr[i] || arr[i].type_id == null) continue;
                var cid = String(arr[i].type_id);
                if (BLOCKED_TIDS[cid]) continue;
                classes.push({
                    type_id: cid,
                    type_name: String(arr[i].type_name || '')
                });
            }
            classCache = classes;
            return classes;
        }

        // ===================== 首页 =====================

        function homeContent(filter) {
            var classes = [];
            var list = [];
            try {
                classes = getClasses();
                var data = getJSON(API + '?ac=detail&pg=1');
                if (data && data.list) {
                    for (var i = 0; i < data.list.length; i++) {
                        list.push(normApiItem(data.list[i]));
                    }
                }
            } catch (e) {
                print('>>> tyyszy homeContent ERROR: ' + e);
            }
            // 分类为空时兜底：用站点 HTML 首页的分类
            if (!classes.length) {
                var homeHtml = httpGet(SITE + '/');
                var re = /<a href="\/index\.php\/vod\/type\/id\/(\d+)\.html"[^>]*class="cat-link[^"]*"[^>]*>([\s\S]{0,120}?)<\/a>/gi;
                var m;
                while ((m = re.exec(homeHtml)) !== null) {
                    var cname = stripHtml(m[2]);
                    var cid = m[1];
                    if (cid === '55') continue; // 过滤成人分类
                    classes.push({ type_id: cid, type_name: cname });
                }
            }
            print('>>> tyyszy homeContent: class=' + classes.length + ' list=' + list.length);
            return { 'class': classes, list: list };
        }

        // ===================== 分类 =====================

        function categoryContent(tid, pg, extend) {
            pg = parseInt(pg, 10) || 1;
            var list = [];
            var pagecount = 1;
            if (BLOCKED_TIDS[String(tid)]) {
                return { page: pg, pagecount: 1, limit: 0, total: 0, list: [] };
            }
            try {
                var url = SITE + '/index.php/vod/type/id/' + tid + (pg > 1 ? '/page/' + pg + '.html' : '.html');
                var html = httpGet(url);
                list = parseCards(html);
                pagecount = parsePageCount(html, 'type');
                // 站点 HTML 失败时回退 API（仅叶子分类有效）
                if (list.length === 0) {
                    var data = getJSON(API + '?ac=detail&t=' + tid + '&pg=' + pg);
                    if (data && data.list) {
                        for (var i = 0; i < data.list.length; i++) {
                            list.push(normApiItem(data.list[i]));
                        }
                        pagecount = parseInt(data.pagecount, 10) || 1;
                    }
                }
            } catch (e) {
                print('>>> tyyszy categoryContent ERROR: ' + e);
            }
            print('>>> tyyszy categoryContent: tid=' + tid + ' pg=' + pg + ' count=' + list.length);
            return {
                page: pg,
                pagecount: pagecount,
                limit: list.length,
                total: pagecount * 30,
                list: list
            };
        }

        // ===================== 搜索 =====================

        function searchContent(key, quick, pg) {
            pg = parseInt(pg, 10) || 1;
            var list = [];
            var pagecount = 1;
            try {
                var enc = encodeURIComponent(key);
                var url = pg > 1
                    ? SITE + '/index.php/vod/search/page/' + pg + '/wd/' + enc + '.html'
                    : SITE + '/index.php/vod/search.html?wd=' + enc;
                var html = httpGet(url);
                list = parseCards(html);
                pagecount = parsePageCount(html, 'search');
            } catch (e) {
                print('>>> tyyszy searchContent ERROR: ' + e);
            }
            print('>>> tyyszy searchContent: key=' + key + ' pg=' + pg + ' count=' + list.length);
            return { page: pg, pagecount: pagecount, limit: list.length, list: list };
        }

        // ===================== 详情 =====================

        function detailContent(ids) {
            var result = { list: [] };
            if (!ids) return result;

            // vbox 传入的是字符串 vod_id（可能是逗号分隔），TVBox 标准为数组
            var vid;
            if (typeof ids === 'string') {
                vid = ids.split(',')[0].trim();
            } else if (Array.isArray(ids) && ids.length > 0) {
                vid = String(ids[0]).trim();
            } else {
                return result;
            }
            if (!vid) return result;

            print('>>> tyyszy detailContent vid=' + vid);
            var data = getJSON(API + '?ac=detail&ids=' + encodeURIComponent(vid));
            var it = data && data.list && data.list.length > 0 ? data.list[0] : null;
            if (!it) {
                print('>>> tyyszy detailContent empty for vid=' + vid);
                return result;
            }

            var playFrom = it.vod_play_from ? String(it.vod_play_from) : 'TY影视';
            var playUrl = it.vod_play_url ? String(it.vod_play_url) : '';

            result.list.push({
                vod_id: String(it.vod_id),
                vod_name: String(it.vod_name || vid),
                vod_pic: absUrl(it.vod_pic || ''),
                vod_remarks: it.vod_remarks ? String(it.vod_remarks) : '',
                vod_year: it.vod_year != null ? String(it.vod_year) : '',
                vod_area: it.vod_area ? String(it.vod_area) : '',
                vod_actor: it.vod_actor ? String(it.vod_actor) : '',
                vod_director: it.vod_director ? String(it.vod_director) : '',
                vod_content: stripHtml(it.vod_content || it.vod_blurb || ''),
                vod_play_from: playFrom,
                vod_play_url: playUrl
            });

            print('>>> tyyszy detailContent ok: ' + result.list[0].vod_name + ' from=' + playFrom);
            return result;
        }

        // ===================== 播放 =====================

        function playerContent(vodId, flag, url) {
            // 详情页已返回 m3u8 直链，客户端会直连播放；此处作为兜底解析入口。
            if (url && url.indexOf('http') === 0) {
                return {
                    parse: 0,
                    url: url,
                    header: { 'User-Agent': UA, 'Referer': SITE + '/' }
                };
            }
            return { parse: 0, url: url || '', header: { 'User-Agent': UA, 'Referer': SITE + '/' } };
        }

        // ===================== 初始化 =====================

        function init(config) {
            print('>>> tyyszy init: TY影视 JS蜘蛛 v1.0');
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