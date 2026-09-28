/*
 * 君君盘搜 JS 蜘蛛 v1.0
 * 适配 vbox-ios JSSpiderEngine (type:3 独立引擎)
 * 站点: https://junso.top
 * 后端: https://zjsc.jnnsou.com/api/resources.php
 *
 * 说明:
 *   - 首页列表走 junso.top 自有接口 /api/daily-update
 *   - junso.top 的 /api/search 需要人机验证（need_captcha），
 *     因此搜索自动降级到同源的 zjsc 资源接口（结构一致、无验证码）
 *   - 无需登录、无需加密签名
 *
 * 网盘蜘蛛源约定:
 *   - 客户端按 manifest group == "cloud" 强制给结果打 "☁️" 标记
 *   - detailContent 的 vod_play_url 返回 JSON 数组 [{"url":"网盘链接","name":"网盘名"}]
 *   - vod_id 编码: encodeURIComponent(标题) + "|||" + encodeURIComponent(JSON(链接数组))
 */

var spider = {
    __jsEvalReturn: function() {

        var BASE_URL = 'https://junso.top';
        var API_BASE = 'https://zjsc.jnnsou.com/api/resources.php';
        var SOURCE_NAME = '君君盘搜';
        var UA = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36';
        var HEADER = { 'User-Agent': UA, 'Referer': BASE_URL + '/' };
        var PER_PAGE = 50;

        // ===================== 工具函数 =====================

        function fetch(url, headers) {
            try {
                var resp = req(url, { headers: headers || HEADER, timeout: 15000 });
                if (resp && resp.ok) return resp.content || '';
                print('>>> junso fetch FAIL: status=' + (resp ? resp.status : 'null') + ' url=' + url.substring(0, 90));
                return '';
            } catch (e) {
                print('>>> junso fetch ERROR: ' + e);
                return '';
            }
        }

        function fetchJSON(url, headers) {
            var html = fetch(url, headers);
            if (!html) return null;
            try {
                return JSON.parse(html);
            } catch (e) {
                print('>>> junso JSON parse ERROR: ' + e);
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

        function encodeVodId(title, links) {
            return encodeURIComponent(title || '') + '|||' + encodeURIComponent(JSON.stringify(links || []));
        }

        function decodeVodId(vodId) {
            var s = String(vodId);
            var idx = s.indexOf('|||');
            var title = '', links = [];
            try {
                if (idx >= 0) {
                    title = decodeURIComponent(s.substring(0, idx));
                    var raw = decodeURIComponent(s.substring(idx + 3));
                    if (raw) links = JSON.parse(raw) || [];
                } else {
                    title = decodeURIComponent(s);
                }
            } catch (e) {
                print('>>> junso decodeVodId ERROR: ' + e);
            }
            if (!Array.isArray(links)) links = [];
            return { title: title, links: links };
        }

        function cloudLabel(panType, url) {
            var t = String(panType || '').toLowerCase();
            if (t.indexOf('baidu') !== -1) return '百度网盘';
            if (t.indexOf('quark') !== -1 || t.indexOf('kuake') !== -1) return '夸克网盘';
            if (t.indexOf('xunlei') !== -1 || t.indexOf('thunder') !== -1) return '迅雷云盘';
            if (t === 'uc' || t.indexOf('uc') !== -1) return 'UC网盘';
            if (t.indexOf('ali') !== -1) return '阿里云盘';
            if (t.indexOf('115') !== -1) return '115网盘';
            if (t.indexOf('123') !== -1) return '123网盘';
            if (t.indexOf('tianyi') !== -1 || t.indexOf('189') !== -1) return '天翼云盘';
            var u = url || '';
            if (u.indexOf('pan.quark.cn') !== -1) return '夸克网盘';
            if (u.indexOf('pan.baidu.com') !== -1) return '百度网盘';
            if (u.indexOf('pan.xunlei.com') !== -1) return '迅雷云盘';
            if (u.indexOf('drive.uc.cn') !== -1 || u.indexOf('uc.cn') !== -1) return 'UC网盘';
            if (u.indexOf('alipan.com') !== -1 || u.indexOf('aliyundrive.com') !== -1) return '阿里云盘';
            if (u.indexOf('115.com') !== -1) return '115网盘';
            if (u.indexOf('123pan.com') !== -1) return '123网盘';
            if (u.indexOf('cloud.189.cn') !== -1) return '天翼云盘';
            return '网盘';
        }

        // junso.top /api/daily-update 的 links 是数组 [{pan_type,url,code,...}]
        function linksFromArray(arr) {
            var out = [];
            if (!arr) return out;
            for (var i = 0; i < arr.length; i++) {
                var it = arr[i];
                if (!it || !it.url) continue;
                out.push({ name: cloudLabel(it.pan_type, it.url), url: it.url });
            }
            return out;
        }

        // zjsc resources 的 links 是对象 {baidu:{name,url}, quark:{...}}
        function linksFromObject(obj) {
            var out = [];
            if (!obj) return out;
            for (var k in obj) {
                if (!obj.hasOwnProperty(k)) continue;
                var v = obj[k];
                if (!v) continue;
                var url = (typeof v === 'string') ? v : v.url;
                if (!url) continue;
                var name = (typeof v === 'object' && v.name) ? v.name : cloudLabel(k, url);
                out.push({ name: cloudLabel(name, url), url: url });
            }
            return out;
        }

        function remarksFromLinks(links) {
            var names = [];
            for (var i = 0; i < links.length; i++) {
                if (links[i].name && names.indexOf(links[i].name) === -1) names.push(links[i].name);
            }
            return names.join(' · ');
        }

        function buildItem(title, links) {
            var name = stripTags(title) || '网盘资源';
            return {
                vod_id: encodeVodId(name, links),
                vod_name: name,
                vod_pic: '',
                vod_remarks: remarksFromLinks(links)
            };
        }

        // zjsc 资源数组 → 列表项（首页/分类/搜索共用）
        function buildFromZjsc(resources) {
            var list = [];
            if (!resources || !resources.length) return list;
            var seen = {};
            for (var i = 0; i < resources.length; i++) {
                var it = resources[i];
                if (!it || !it.name) continue;
                var links = linksFromObject(it.links);
                if (!links.length) continue;
                var key = it.name + '|' + links[0].url;
                if (seen[key]) continue;
                seen[key] = true;
                list.push(buildItem(it.name, links));
            }
            return list;
        }

        // junso daily-update 数据数组 → 列表项
        function buildFromJunso(data) {
            var list = [];
            if (!data || !data.length) return list;
            var seen = {};
            for (var i = 0; i < data.length; i++) {
                var it = data[i];
                if (!it || !it.title) continue;
                var links = linksFromArray(it.links);
                if (!links.length) continue;
                var key = it.title + '|' + links[0].url;
                if (seen[key]) continue;
                seen[key] = true;
                list.push(buildItem(it.title, links));
            }
            return list;
        }

        function zjscListURL(type, page) {
            return API_BASE + '?all=1&type=' + encode(type) + '&page=' + page + '&per_page=' + PER_PAGE + '&_t=' + new Date().getTime();
        }

        // ===================== 首页内容 =====================

        function homeContent(filter) {
            var result = {
                class: [
                    { type_id: 'tv', type_name: '电视剧' },
                    { type_id: 'movie', type_name: '电影' },
                    { type_id: 'other', type_name: '综艺' }
                ],
                list: []
            };
            try {
                var data = fetchJSON(BASE_URL + '/api/daily-update?type=tv&page=1');
                if (data && data.data) {
                    result.list = buildFromJunso(data.data);
                }
                if (!result.list.length) {
                    // junso 接口不可用时回退后端
                    var fb = fetchJSON(zjscListURL('tv', 1));
                    if (fb && fb.data) result.list = buildFromZjsc(fb.data);
                }
                print('>>> junso homeContent: ' + result.list.length);
            } catch (e) {
                print('>>> junso homeContent ERROR: ' + e);
            }
            return result;
        }

        // ===================== 分类内容 =====================

        function categoryContent(tid, pg, filter, extend) {
            var page = parseInt(pg) || 1;
            var result = { list: [], page: page, pagecount: 1, limit: PER_PAGE, total: 0 };
            try {
                var data = fetchJSON(zjscListURL(tid || 'tv', page));
                if (data && data.data) {
                    result.list = buildFromZjsc(data.data);
                    result.total = data.data.length;
                    result.pagecount = data.data.length >= PER_PAGE ? page + 1 : page;
                }
                print('>>> junso categoryContent: tid=' + tid + ' pg=' + page + ' count=' + result.list.length);
            } catch (e) {
                print('>>> junso categoryContent ERROR: ' + e);
            }
            return result;
        }

        // ===================== 搜索内容 =====================

        function searchContent(key, quick, pg) {
            var page = parseInt(pg) || 1;
            if (typeof quick === 'number' && quick > 0) page = quick;
            var result = { list: [], page: page, pagecount: 1, limit: PER_PAGE, total: 0 };

            try {
                // 1. 优先走 junso 搜索（无验证码时）
                var d1 = fetchJSON(BASE_URL + '/api/search?keyword=' + encode(key) + '&page=' + page);
                if (d1 && !d1.need_captcha && d1.status !== 400) {
                    var arr = d1.data || [];
                    result.list = buildFromJunso(arr);
                }

                // 2. junso 需要验证码 / 无结果 → 降级到 zjsc 搜索
                if (!result.list.length) {
                    var d2 = fetchJSON(API_BASE + '?search=' + encode(key) + '&page=' + page + '&per_page=' + PER_PAGE + '&_t=' + new Date().getTime());
                    if (d2 && d2.data && d2.data.resources) {
                        result.list = buildFromZjsc(d2.data.resources);
                        var total = parseInt(d2.data.total) || result.list.length;
                        var per = parseInt(d2.data.per_page) || PER_PAGE;
                        result.total = total;
                        result.pagecount = per > 0 ? Math.max(page, Math.ceil(total / per)) : page;
                    }
                } else {
                    result.pagecount = result.list.length >= PER_PAGE ? page + 1 : page;
                }

                print('>>> junso searchContent: key=' + key + ' pg=' + page + ' count=' + result.list.length);
            } catch (e) {
                print('>>> junso searchContent ERROR: ' + e);
            }
            return result;
        }

        // ===================== 详情内容 =====================

        function detailContent(ids) {
            var result = { list: [] };
            if (!ids) return result;

            var decoded = decodeVodId(ids);
            var name = decoded.title || '网盘资源';
            var playUrl;
            if (decoded.links && decoded.links.length) {
                playUrl = JSON.stringify(decoded.links);
            } else {
                playUrl = JSON.stringify([{ url: '', name: '未获取到链接' }]);
            }

            result.list.push({
                vod_id: String(ids),
                vod_name: name,
                vod_pic: '',
                vod_content: '来源：' + SOURCE_NAME,
                vod_remarks: remarksFromLinks(decoded.links) || '网盘',
                vod_play_from: SOURCE_NAME,
                vod_play_url: playUrl
            });
            print('>>> junso detailContent: links=' + (decoded.links ? decoded.links.length : 0));
            return result;
        }

        // ===================== 播放内容 =====================

        function playerContent(vodId, flag, url) {
            if (url && url.indexOf('http') === 0) {
                return { parse: 0, url: url, header: { 'User-Agent': UA } };
            }
            return { parse: 0, url: '' };
        }

        // ===================== 初始化 =====================

        function init(config) {
            print('>>> junso init: 君君盘搜 JS蜘蛛 v1.0');
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