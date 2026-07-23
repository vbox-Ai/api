/*
 * 腾讯视频 JS 蜘蛛
 * 适配 vbox-ios JSSpiderEngine (type:3 独立引擎)
 * 纯 JSON API 交互 / 无加密 / 播放走 App 解析器 (parse:1)
 * 
 * 修复记录:
 * - 搜索结果：normalList + areaBoxList 双源合并，按 viewType 精确过滤（25=正片, 1=子系列, 100=剪辑）
 * - playerContent：保持 parse: 1（走用户自定义解析器），与 Python 原版一致
 * - detailContent：vod_play_url 改为完整 v.qq.com URL，解析器可直接识别
 * - HEADER：统一添加 Content-Type: application/json，修复 getPageData/getDetailData 返回空数据
 * - homeContent：新增首页视频列表，调用电视剧频道 API 获取推荐数据
 * - playerContent：兼容 title$url 格式，防止 App 传入完整 play_url 时解析失败
 */

// ===================== 工具函数 =====================

// 简易 UUID v4
function uuid() {
    var s = 'xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx';
    return s.replace(/[xy]/g, function(c) {
        var r = Math.random() * 16 | 0;
        var v = c === 'x' ? r : (r & 0x3 | 0x8);
        return v.toString(16);
    });
}

// 去除 HTML 标签
function removeHtmlTags(str) {
    return str.replace(/<[^>]+>/g, '');
}

// ===================== 蜘蛛主体 =====================
var spider = {
    __jsEvalReturn: function() {
        var HOST = 'https://v.qq.com';
        var API_HOST = 'https://pbaccess.video.qq.com';
        var BASE_URL = API_HOST + '/trpc.universal_backend_service.page_server_rpc.PageServer/GetPageData';
        var BASE_PARAMS = '?video_appid=1000005&vplatform=2&vversion_name=8.9.10&new_mark_label_enabled=1';
        var DETAIL_PARAMS = '?video_appid=3000010&vplatform=2&vversion_name=8.2.96';
        var HEADER = {
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/109.0.5410.0 Safari/537.36',
            'origin': HOST,
            'referer': HOST + '/',
            'Content-Type': 'application/json'
        };

        var defaultBody = {
            page_params: {
                channel_id: '',
                filter_params: 'sort=75',
                page_type: 'channel_operation',
                page_id: 'channel_list_second_page'
            }
        };
        var pageBody = JSON.parse(JSON.stringify(defaultBody));

        // 合并 headers
        function mergeHeaders(extra) {
            var h = {};
            for (var k in HEADER) h[k] = HEADER[k];
            if (extra) for (var k2 in extra) h[k2] = extra[k2];
            return h;
        }

        // POST JSON 请求（返回 JS 对象）
        function postJson(url, jsonBody, extraHeaders) {
            try {
                var h = mergeHeaders(extraHeaders);
                var bodyStr = JSON.stringify(jsonBody);
                // JSON body 同时传 body 和 data 兼容不同 req() 实现
                var opts = { method: 'POST', headers: h, body: bodyStr, data: bodyStr };
                var respObj = req(url, opts);
                if (!respObj) { print('>>> tx req null'); return null; }
                var respStr = (typeof respObj === 'string') ? respObj : (respObj.data || respObj.content || '');
                if (!respStr) { print('>>> tx empty resp'); return null; }
                return (typeof respStr === 'object') ? respStr : JSON.parse(respStr);
            } catch (e) {
                print('>>> tx postJson ERROR: ' + e);
                return null;
            }
        }

        // 安全解析 JSON 字符串
        function safeJsonParse(str) {
            try { return JSON.parse(str); } catch(e) { return {}; }
        }

        // 从 item_params 提取 tag 信息
        function getTags(p) {
            var raw = (p.uni_imgtag || p.imgtag || '{}');
            return safeJsonParse(raw);
        }

        // 提取视频列表条目
        function extractVodItem(p, id) {
            var tag = getTags(p);
            var name = p.mz_title || p.title;
            if (!name || (id && id.indexOf('http') >= 0)) return null;
            return {
                vod_id: id || p.cid,
                vod_name: name,
                vod_pic: p.new_pic_hz || p.new_pic_vt || p.image_url,
                vod_year: tag.tag_2 ? tag.tag_2.text : '',
                vod_remarks: tag.tag_4 ? tag.tag_4.text : ''
            };
        }

        // 参数对象转字符串 (key=val&key2=val2)
        function paramsToStr(params) {
            var parts = [];
            for (var k in params) {
                if (params.hasOwnProperty(k)) parts.push(k + '=' + params[k]);
            }
            return parts.join('&');
        }

        // 获取频道页面数据
        function getPageData(body, params) {
            var url = BASE_URL + (params || BASE_PARAMS);
            return postJson(url, body);
        }

        // 获取详情页面数据
        function getDetailData(body) {
            var url = BASE_URL + DETAIL_PARAMS;
            return postJson(url, body);
        }

        return {
            init: function(config) { return true; },

            homeContent: function(filter) {
                var cdata = {
                    '电视剧': '100113', '电影': '100173', '综艺': '100109',
                    '纪录片': '100105', '动漫': '100119', '少儿': '100150', '短剧': '110755'
                };
                var classes = [];
                var filters = {};
                var cids = [];

                for (var name in cdata) {
                    if (cdata.hasOwnProperty(name)) {
                        classes.push({ type_name: name, type_id: cdata[name] });
                        cids.push(cdata[name]);
                    }
                }

                // 串行获取每个分类的筛选数据
                for (var i = 0; i < cids.length; i++) {
                    var cid = cids[i];
                    var hbody = JSON.parse(JSON.stringify(defaultBody));
                    hbody.page_params.channel_id = cid;
                    var data = getPageData(hbody);
                    if (!data || !data.data || !data.data.module_list_datas) continue;

                    try {
                        var modules = data.data.module_list_datas;
                        var items = modules[modules.length - 1].module_datas[modules[modules.length - 1].module_datas.length - 1].item_data_lists.item_datas;
                        var filterDict = {};
                        for (var j = 0; j < items.length; j++) {
                            var item = items[j];
                            var params = item.item_params || {};
                            var filterKey = params.index_item_key;
                            if (!filterKey) continue;
                            if (!filterDict[filterKey]) {
                                filterDict[filterKey] = { key: filterKey, name: params.index_name, value: [] };
                            }
                            filterDict[filterKey].value.push({ n: params.option_name, v: params.option_value });
                        }
                        filters[cid] = [];
                        for (var fk in filterDict) {
                            if (filterDict.hasOwnProperty(fk)) filters[cid].push(filterDict[fk]);
                        }
                    } catch(e) { continue; }
                }

                // 获取首页视频列表：取第一个分类（电视剧）的数据
                var vlist = [];
                try {
                    var homeBody = JSON.parse(JSON.stringify(defaultBody));
                    homeBody.page_params.channel_id = '100113';
                    homeBody.page_params.filter_params = 'sort=75';
                    var homeData = getPageData(homeBody);
                    if (homeData && homeData.data && homeData.data.module_list_datas) {
                        var hModules = homeData.data.module_list_datas;
                        var hItems = hModules[hModules.length - 1].module_datas[hModules[hModules.length - 1].module_datas.length - 1].item_data_lists.item_datas;
                        for (var k = 0; k < hItems.length; k++) {
                            var hItem = hItems[k];
                            var hId = (hItem.item_params || {}).cid;
                            if (!hId) continue;
                            var vod = extractVodItem(hItem.item_params, hId);
                            if (vod) vlist.push(vod);
                        }
                    }
                } catch(e) {
                    print('>>> tx homeContent list ERROR: ' + e);
                }

                return { class: classes, filters: filters, list: vlist };
            },

            homeVideoContent: function() {
                try {
                    var json_data = {
                        page_context: null,
                        page_params: { page_id: '100101', page_type: 'channel', skip_privacy_types: '0', support_click_scan: '1', new_mark_label_enabled: '1', ams_cookies: '' },
                        page_bypass_params: { params: { caller_id: '', data_mode: 'default', page_id: '', page_type: 'channel', platform_id: '2', user_mode: 'default' }, scene: 'channel', abtest_bypass_id: '' }
                    };
                    var url = API_HOST + '/trpc.vector_layout.page_view.PageService/getPage';
                    var data = postJson(url, json_data);
                    if (!data || !data.data) return { list: [] };

                    var vlist = [];
                    var cards = data.data.CardList[0].children_list.list.cards;
                    for (var i = 0; i < cards.length; i++) {
                        var it = cards[i];
                        if (!it.params) continue;
                        var p = it.params;
                        var id = it.id || p.cid;
                        var vod = extractVodItem(p, id);
                        if (vod) vlist.push(vod);
                    }
                    return { list: vlist };
                } catch(e) {
                    print('>>> tx homeVideoContent ERROR: ' + e);
                    return { list: [] };
                }
            },

            categoryContent: function(tid, pg, extend) {
                try {
                    var ext = {};
                    try { ext = typeof extend === 'string' ? JSON.parse(extend) : (extend || {}); } catch(e) {}

                    var params = {
                        sort: ext.sort || '75',
                        attr: ext.attr || '-1',
                        itype: ext.itype || '-1',
                        ipay: ext.ipay || '-1',
                        iarea: ext.iarea || '-1',
                        iyear: ext.iyear || '-1',
                        theater: ext.theater || '-1',
                        award: ext.award || '-1',
                        recommend: ext.recommend || '-1'
                    };

                    if (pg == '1') pageBody = JSON.parse(JSON.stringify(defaultBody));
                    pageBody.page_params.channel_id = tid;
                    pageBody.page_params.filter_params = paramsToStr(params);

                    var data = getPageData(pageBody);
                    if (!data || !data.data) return { page: pg, pagecount: 1, limit: 90, total: 0, list: [] };

                    var ndata = data.data;
                    var result = {};
                    if (ndata.has_next_page) {
                        result.pagecount = 9999;
                        pageBody.page_context = ndata.next_page_context;
                    } else {
                        result.pagecount = parseInt(pg);
                    }

                    var vlist = [];
                    var modules = ndata.module_list_datas;
                    var items = modules[modules.length - 1].module_datas[modules[modules.length - 1].module_datas.length - 1].item_data_lists.item_datas;
                    for (var i = 0; i < items.length; i++) {
                        var its = items[i];
                        var id = (its.item_params || {}).cid;
                        if (!id) continue;
                        var vod = extractVodItem(its.item_params, id);
                        if (vod) vlist.push(vod);
                    }
                    result.list = vlist;
                    result.page = pg;
                    result.limit = 90;
                    result.total = 999999;
                    return result;
                } catch(e) {
                    print('>>> tx categoryContent ERROR: ' + e);
                    return { page: pg, pagecount: 1, limit: 90, total: 0, list: [] };
                }
            },

            detailContent: function(ids) {
                try {
                    var cid = ids[0];
                    print('>>> tx detailContent cid=' + cid);

                    var vbody = { page_params: { req_from: 'web', cid: cid, vid: '', lid: '', page_type: 'detail_operation', page_id: 'detail_page_introduction' }, has_cache: 1 };
                    var ebody = { page_params: { req_from: 'web_vsite', page_id: 'vsite_episode_list', page_type: 'detail_operation', id_type: '1', page_size: '', cid: cid, vid: '', lid: '', page_num: '', page_context: '', detail_page_type: '1' }, has_cache: 1 };

                    var vdata = getDetailData(vbody);
                    print('>>> tx vdata=' + (vdata ? 'ok' : 'null'));
                    if (!vdata || !vdata.data || !vdata.data.module_list_datas) {
                        print('>>> tx vdata structure invalid');
                        return { list: [{ vod_play_from: '暂无资源', vod_play_url: '' }] };
                    }

                    var data = getDetailData(ebody);
                    print('>>> tx edata=' + (data ? 'ok' : 'null'));

                    // 从详情接口安全提取基础信息
                    var d = {};
                    try {
                        d = vdata.data.module_list_datas[0].module_datas[0].item_data_lists.item_datas[0].item_params || {};
                    } catch(ee) { print('>>> tx extract d ERROR: ' + ee); }

                    // 提取演员（容错）
                    var actors = [];
                    try {
                        var starList = vdata.data.module_list_datas[0].module_datas[0].item_data_lists.item_datas[0].sub_items.star_list.item_datas;
                        for (var a = 0; a < starList.length; a++) actors.push(starList[a].item_params.name);
                    } catch(e) {}

                    // 提取选集列表
                    var pdata = [];
                    try {
                        pdata = processTabs(data, ebody, ids);
                    } catch(e) {
                        print('>>> tx processTabs ERROR: ' + e);
                    }
                    print('>>> tx pdata count=' + pdata.length);

                    if (!pdata || pdata.length === 0) {
                        return {
                            list: [{
                                vod_id: cid,
                                vod_name: d.title || '',
                                vod_pic: d.image_url || d.new_pic_hz || '',
                                vod_content: d.cover_description || '',
                                vod_play_from: '暂无资源',
                                vod_play_url: ''
                            }]
                        };
                    }

                    // 分离正片和预告
                    var names = ['腾讯视频', '预告片'];
                    var plist = [], ylist = [];
                    for (var i = 0; i < pdata.length; i++) {
                        var k = pdata[i];
                        var itemId = k.item_id;
                        var title = (k.item_params || {}).union_title || '';
                        if (!itemId && !title) continue;
                        if (!itemId) itemId = '';
                        var pid = title + '$' + 'https://v.qq.com/x/cover/' + cid + '/' + itemId + '.html';
                        if (title.indexOf('预告') >= 0) {
                            ylist.push(pid);
                        } else {
                            plist.push(pid);
                        }
                    }

                    var finalNames = [];
                    var urls = [];
                    if (plist.length > 0) { finalNames.push(names[0]); urls.push(plist.join('#')); }
                    if (ylist.length > 0) { finalNames.push(names[1]); urls.push(ylist.join('#')); }

                    print('>>> tx episodes: ' + plist.length + ' main, ' + ylist.length + ' preview');
                    return {
                        list: [{
                            vod_id: cid,
                            vod_name: d.title || '',
                            vod_pic: d.image_url || d.new_pic_hz || '',
                            vod_year: d.year || '',
                            vod_area: d.area_name || '',
                            vod_actor: actors.join(','),
                            vod_content: d.cover_description || '',
                            vod_remarks: d.holly_online_time || d.hotval || '',
                            vod_play_from: finalNames.join('$$$'),
                            vod_play_url: urls.join('$$$')
                        }]
                    };
                } catch(e) {
                    print('>>> tx detailContent ERROR: ' + e);
                    return { list: [{ vod_play_from: '暂无资源', vod_play_url: '' }] };
                }
            },

            searchContent: function(key, pg) {
                try {
                    var searchHeader = mergeHeaders({ 'Content-Type': 'application/json' });
                    var body = {
                        version: '25021101',
                        clientType: 1,
                        filterValue: '',
                        uuid: uuid(),
                        retry: 0,
                        query: key,
                        pagenum: parseInt(pg) - 1,
                        pagesize: 30,
                        queryFrom: 0,
                        searchDatakey: '',
                        transInfo: '',
                        isneedQc: true,
                        preQid: '',
                        adClientInfo: '',
                        extraInfo: { isNewMarkLabel: '1', multi_terminal_pc: '1', themeType: '1' }
                    };
                    var url = API_HOST + '/trpc.videosearch.mobile_search.MultiTerminalSearch/MbSearch?vplatform=2';
                    var data = postJson(url, body, searchHeader);
                    if (!data || !data.data) return { list: [], page: pg };

                    var vlist = [];
                    var seen = {};
                    var validTypes = ['电视剧', '电影', '综艺', '纪录片', '动漫', '少儿', '短剧'];

                    // 辅助函数：从搜索结果条目构建 vod 对象
                    function buildItem(k) {
                        var doc = k.doc || {};
                        var vi = k.videoInfo || {};
                        if (!doc.id || !vi.title) return null;
                        if (vi.subTitle && vi.subTitle.indexOf('外站') >= 0) return null;
                        if (!vi.typeName || validTypes.indexOf(vi.typeName) < 0) return null;
                        var tag = {};
                        if (typeof vi.imgTag === 'string') tag = safeJsonParse(vi.imgTag);
                        return {
                            vod_id: doc.id,
                            vod_name: removeHtmlTags(vi.title),
                            vod_pic: vi.imgUrl || '',
                            vod_year: (vi.typeName || '') + ' ' + (tag.tag_2 ? tag.tag_2.text : ''),
                            vod_remarks: tag.tag_4 ? tag.tag_4.text : ''
                        };
                    }

                    // 来源1: normalList（实际搜索结果），只取正片 viewType=25
                    var nl = data.data.normalList.itemList || [];
                    for (var i = 0; i < nl.length; i++) {
                        var nk = nl[i];
                        if (!nk.doc || !nk.videoInfo) continue;
                        // 只保留正片，过滤剪辑/花絮（viewType=100）
                        if (nk.videoInfo.viewType !== 25) continue;
                        var item = buildItem(nk);
                        if (item && !seen[item.vod_id]) {
                            seen[item.vod_id] = true;
                            vlist.push(item);
                        }
                    }

                    // 来源2: areaBoxList（推荐/聚合框），正片 viewType=25 或子系列 viewType=1
                    var ab = (data.data.areaBoxList || [])[0];
                    if (ab && ab.itemList) {
                        var abItems = ab.itemList;
                        for (var j = 0; j < abItems.length; j++) {
                            var ak = abItems[j];
                            if (!ak.doc || !ak.videoInfo) continue;
                            var avt = ak.videoInfo.viewType;
                            // viewType=25 正片，viewType=1 子系列/合集（均有播放地址）
                            if (avt !== 25 && avt !== 1) continue;
                            var aitem = buildItem(ak);
                            if (aitem && !seen[aitem.vod_id]) {
                                seen[aitem.vod_id] = true;
                                vlist.push(aitem);
                            }
                        }
                    }

                    return { list: vlist, page: pg };
                } catch(e) {
                    print('>>> tx searchContent ERROR: ' + e);
                    return { list: [], page: pg };
                }
            },

            playerContent: function(flag, id, vipFlags) {
                // 兼容 title$url 格式：提取 URL 部分
                if (id.indexOf('$') >= 0) {
                    var dollarParts = id.split('$');
                    id = dollarParts[dollarParts.length - 1];
                }
                // id 格式: 新版为完整 v.qq.com URL，旧版为 cid@item_id
                if (id.indexOf('http') === 0) {
                    return { jx: 1, parse: 1, url: id, header: '' };
                }
                var parts = id.split('@');
                if (parts.length < 2) return { jx: 1, parse: 1, url: '', header: '' };
                var url = HOST + '/x/cover/' + parts[0] + '/' + parts[1] + '.html';
                return { jx: 1, parse: 1, url: url, header: '' };
            }
        };

        // 处理多 tab 选集（串行替代 Python 的 ThreadPoolExecutor）
        function processTabs(data, body, ids) {
            try {
                var modules = data.data.module_list_datas;
                var lastModule = modules[modules.length - 1];
                var lastData = lastModule.module_datas[lastModule.module_datas.length - 1];
                var pdata = lastData.item_data_lists.item_datas;
                var tabsStr = lastData.module_params ? lastData.module_params.tabs : null;

                if (!tabsStr) return pdata;
                var tabs = safeJsonParse(tabsStr);
                if (!tabs || tabs.length <= 1) return pdata;

                // 从第 2 个 tab 开始串行获取
                var remainingTabs = tabs.slice(1);
                for (var i = 0; i < remainingTabs.length; i++) {
                    var tab = remainingTabs[i];
                    var nbody = JSON.parse(JSON.stringify(body));
                    nbody.page_params.page_context = tab.page_context;
                    var result = getDetailData(nbody);
                    if (result && result.data && result.data.module_list_datas) {
                        var rm = result.data.module_list_datas;
                        var rd = rm[rm.length - 1].module_datas[rm[rm.length - 1].module_datas.length - 1];
                        var extraItems = rd.item_data_lists.item_datas;
                        for (var j = 0; j < extraItems.length; j++) pdata.push(extraItems[j]);
                    }
                }
                return pdata;
            } catch(e) {
                print('>>> tx processTabs ERROR: ' + e);
                return [];
            }
        }
    }
};