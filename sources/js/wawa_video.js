/*
 * 哇哇影视 JS 蜘蛛 v1.0
 * 适配 vbox-ios JSSpiderEngine (type:3 独立引擎)
 * 目标站: MacCMS API (zjv6.vod)
 * 特点: AES-128-ECB 接口配置解密 + RSA-SHA256 请求签名 + Gitee 远程配置
 * 使用原生 crypto 桥接（需 vbox 3.1073+ 支持 AES.decryptECB / RSA.sign / uuid / hex.toBase64）
 * 流程: Gitee获取加密配置 → AES-ECB解密 → RSA签名请求API → 返回视频数据
 */

var spider = {
    __jsEvalReturn: function() {
        // ====== 常量 ======
        var AES_KEY = 'Crm4FXWkk5JItpYirFDpqg==';      // 配置解密密钥 (base64)
        var GITEE_TOKEN = '74d5879931b9774be10dee3d8c51008e';
        var GITEE_CONF_KEY = '3bbf7348cf314874883a18d6b6fcf67a';
        var GITEE_CONF_URL = 'https://gitee.com/api/v5/repos/aycapp/openapi/contents/wawaconf.txt?access_token=' + GITEE_TOKEN;
        var UA = 'okhttp/4.9.3';

        // ====== 配置缓存 ======
        var CONF = null;
        var HOST = '';
        var APP_KEY = '';
        var RSA_KEY = '';

        // ====== 工具函数 ======
        function getTimestamp() {
            return String(Date.now());
        }

        // 解密 Gitee 返回的配置数据
        // 流程: Gitee content (base64) → base64解码得到hex字符串 → hex转base64 → AES-ECB解密
        function decryptConfig(giteeContentB64) {
            try {
                var hexStr = crypto.base64.decode(giteeContentB64);
                var rawB64 = crypto.hex.toBase64(hexStr);
                return crypto.AES.decryptECB(rawB64, AES_KEY);
            } catch (e) {
                print('>>> wawa decryptConfig ERROR: ' + e);
                return '';
            }
        }

        // 从 Gitee 获取基础配置（带缓存）
        function getBaseInfo() {
            if (CONF) return CONF;
            try {
                var uid = crypto.uuid();
                var t = getTimestamp();
                var sign = crypto.MD5('appKey=' + GITEE_CONF_KEY + '&uid=' + uid + '&time=' + t);

                var resp = req(GITEE_CONF_URL, {
                    method: 'GET',
                    headers: {
                        'User-Agent': UA,
                        'uid': uid,
                        'time': t,
                        'sign': sign
                    }
                });

                if (!resp) { print('>>> wawa getBaseInfo: null resp'); return null; }
                var content = resp.content || '';
                if (typeof content === 'object') content = JSON.stringify(content);
                if (!content || content.length < 10) {
                    print('>>> wawa getBaseInfo: empty resp, status=' + (resp.status || 0));
                    return null;
                }

                var data = JSON.parse(content);
                if (!data || !data.content) {
                    print('>>> wawa getBaseInfo: no content field');
                    return null;
                }

                var decrypted = decryptConfig(data.content);
                if (!decrypted) { print('>>> wawa getBaseInfo: decrypt failed'); return null; }

                CONF = JSON.parse(decrypted);
                HOST = CONF.baseUrl || '';
                APP_KEY = CONF.appKey || '';
                RSA_KEY = CONF.appSecret || '';
                print('>>> wawa getBaseInfo OK: HOST=' + HOST);
                return CONF;
            } catch (e) {
                print('>>> wawa getBaseInfo ERROR: ' + e);
                return null;
            }
        }

        // 生成请求头（RSA-SHA256签名）
        function getHeaders() {
            getBaseInfo();
            var uid = crypto.uuid();
            var t = getTimestamp();
            var message = 'appKey=' + APP_KEY + '&time=' + t + '&uid=' + uid;
            var sign = crypto.RSA.sign(message, RSA_KEY);
            return {
                'User-Agent': UA,
                'uid': uid,
                'time': t,
                'appKey': APP_KEY,
                'sign': sign
            };
        }

        // 通用 API 请求
        function fetchApi(path) {
            getBaseInfo();
            if (!HOST) { print('>>> wawa fetchApi: no HOST'); return null; }
            try {
                var url = HOST + path;
                var resp = req(url, { method: 'GET', headers: getHeaders() });
                if (!resp) { print('>>> wawa fetchApi null: ' + path); return null; }
                var content = resp.content || '';
                if (typeof content === 'object') content = JSON.stringify(content);
                if (!content || content.length < 2) {
                    print('>>> wawa fetchApi empty: ' + path + ' status=' + (resp.status || 0));
                    return null;
                }
                return JSON.parse(content);
            } catch (e) {
                print('>>> wawa fetchApi ERROR (' + path + '): ' + e);
                return null;
            }
        }

        // Base64 编码 JSON 对象
        function b64encodeJson(obj) {
            return crypto.base64.encode(JSON.stringify(obj));
        }

        // ====== 蜘蛛 API ======
        return {
            init: function(config) {
                return true;
            },

            homeContent: function(filter) {
                var result = { class: [], list: [], filters: {} };

                // 获取分类列表
                var typeData = fetchApi('/api.php/zjv6.vod/types');
                if (!typeData || !typeData.data || !typeData.data.list) {
                    print('>>> wawa homeContent: no type data');
                    return result;
                }

                var dy = { class: '类型', area: '地区', lang: '语言', year: '年份', letter: '字母', by: '排序' };
                var sl = { '按更新': 'time', '按播放': 'hits', '按评分': 'score', '按收藏': 'store_num' };

                for (var i = 0; i < typeData.data.list.length; i++) {
                    var item = typeData.data.list[i];
                    var tid = String(item.type_id);
                    result.class.push({ type_id: item.type_id, type_name: item.type_name });

                    // 生成筛选器
                    result.filters[tid] = [];
                    var ext = item.type_extend || {};
                    ext.by = '按更新,按播放,按评分,按收藏';  // 强制注入排序选项

                    for (var key in dy) {
                        if (ext[key]) {
                            var values = ext[key].split(',');
                            var valueArray = [];
                            for (var j = 0; j < values.length; j++) {
                                if (!values[j]) continue;
                                valueArray.push({
                                    n: values[j],
                                    v: (key === 'by' ? (sl[values[j]] || values[j]) : values[j])
                                });
                            }
                            if (valueArray.length > 0) {
                                result.filters[tid].push({ key: key, name: dy[key], value: valueArray });
                            }
                        }
                    }
                }

                // 获取首页推荐列表
                var homeData = fetchApi('/api.php/zjv6.vod/vodPhbAll');
                if (homeData && homeData.data && homeData.data.list &&
                    homeData.data.list[0] && homeData.data.list[0].vod_list) {
                    result.list = homeData.data.list[0].vod_list;
                    print('>>> wawa homeContent: list=' + result.list.length);
                }

                result.page = 1;
                result.pagecount = 1;
                result.limit = 20;
                result.total = 20;
                return result;
            },

            homeVideoContent: function() {
                return { list: [] };
            },

            categoryContent: function(tid, pg, filter, extend) {
                var page = parseInt(pg) || 1;

                // 解析筛选扩展参数
                var ext = {};
                if (extend) {
                    try {
                        if (typeof extend === 'string' && extend !== '{}') {
                            ext = JSON.parse(extend);
                        } else if (typeof extend === 'object') {
                            ext = extend;
                        }
                    } catch (e) {}
                }

                var params = 'type=' + tid + '&page=' + page + '&limit=12';
                params += '&class=' + (ext.class || '');
                params += '&area=' + (ext.area || '');
                params += '&year=' + (ext.year || '');
                params += '&by=' + (ext.by || '');

                var data = fetchApi('/api.php/zjv6.vod?' + params);
                var list = (data && data.data && data.data.list) ? data.data.list : [];

                return {
                    list: list,
                    page: page,
                    pagecount: 999,
                    limit: 12,
                    total: 9999
                };
            },

            detailContent: function(ids) {
                var vodId = String(ids).split(',')[0].trim();
                print('>>> wawa detailContent: vodId=' + vodId);

                var data = fetchApi('/api.php/zjv6.vod/detail?vod_id=' + vodId + '&rel_limit=10');
                if (!data || !data.data) {
                    print('>>> wawa detailContent: no data');
                    return { list: [] };
                }

                var item = data.data;
                var playFrom = [];
                var playUrls = [];

                if (item.vod_play_list && item.vod_play_list.length > 0) {
                    for (var i = 0; i < item.vod_play_list.length; i++) {
                        var list = item.vod_play_list[i];
                        var show = (list.player_info && list.player_info.show) ? list.player_info.show : ('线路' + (i + 1));
                        playFrom.push(show);

                        var urls = [];
                        if (list.urls && list.urls.length > 0) {
                            for (var j = 0; j < list.urls.length; j++) {
                                var u = list.urls[j];
                                // 注入 parse 字段
                                if (list.player_info && list.player_info.parse2) {
                                    u.parse = list.player_info.parse2;
                                }
                                urls.push(u.name + '$' + b64encodeJson(u));
                            }
                        }
                        playUrls.push(urls.join('#'));
                    }
                }

                return {
                    list: [{
                        vod_id: item.vod_id,
                        vod_name: item.vod_name || '',
                        vod_pic: item.vod_pic || '',
                        vod_remarks: item.vod_remarks || '',
                        vod_year: item.vod_year || '',
                        vod_area: item.vod_area || '',
                        vod_content: item.vod_content || '',
                        vod_play_from: playFrom.join('$$$'),
                        vod_play_url: playUrls.join('$$$')
                    }]
                };
            },

            searchContent: function(key, quick, pg) {
                // 兼容两种调用方式: searchContent(key, pg) 或 searchContent(key, quick, pg)
                var keyword = String(key || '');
                var pageNum = 1;
                if (pg !== undefined) {
                    pageNum = parseInt(pg) || 1;
                } else if (quick !== undefined) {
                    pageNum = parseInt(quick) || 1;
                }

                var data = fetchApi('/api.php/zjv6.vod?page=' + pageNum + '&limit=20&wd=' + encodeURIComponent(keyword));
                var list = (data && data.data && data.data.list) ? data.data.list : [];

                return {
                    list: list,
                    page: pageNum,
                    pagecount: 9999,
                    limit: 20,
                    total: 999999
                };
            },

            playerContent: function(vodId, flag, url) {
                try {
                    print('>>> wawa playerContent: url=' + (url || '').substring(0, 60));
                    // url 格式: name$base64(json) 或 base64(json)
                    var b64Data = String(url || '');
                    if (b64Data.indexOf('$') >= 0) {
                        b64Data = b64Data.substring(b64Data.indexOf('$') + 1);
                    }

                    var jsonStr = crypto.base64.decode(b64Data);
                    var playData = JSON.parse(jsonStr);
                    var playUrl = playData.url || '';

                    print('>>> wawa playerContent: playUrl=' + (playUrl || '').substring(0, 80));

                    return {
                        parse: 0,
                        playUrl: '',
                        url: playUrl,
                        header: { 'User-Agent': 'dart:io' }
                    };
                } catch (e) {
                    print('>>> wawa playerContent ERROR: ' + e);
                    return { parse: 0, playUrl: '', url: '' };
                }
            }
        };
    }
};
