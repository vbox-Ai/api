// 特推蜘蛛 — TVBox 标准蜘蛛接口
// 基于 Python 爬虫逆向翻译为 JS，使用 crypto.AES.decrypt / crypto.MD5 桥接

var _ = {
    // 5个域名后缀（fallback）
    domainSuffixes: ['wcyfhknomg', 'pdcqllfomw', 'alxhzjvean', 'bqeaaxzplt', 'hfbtpixjso'],
    ua: 'Mozilla/5.0 (Linux; Android 11; M2012K10C Build/RP1A.200720.011; wv) AppleWebKit/537.36 (KHTML, like Gecko) Version/4.0 Chrome/87.0.4280.141 Mobile Safari/537.36;SuiRui/twitter/ver=1.4.4',
    aesKey: 'SmhiR2NpT2lKSVV6STFOaQ==',
    host: '',
    phost: '',
    token: '',
    did: '',
    cache: {},

    // 随机字符串
    randomStr: function(len) {
        var chars = 'abcdefghijklmnopqrstuvwxyz0123456789';
        var result = '';
        for (var i = 0; i < len; i++) {
            result += chars.charAt(Math.floor(Math.random() * chars.length));
        }
        return result;
    },

    // 获取当前时间戳(毫秒)
    now: function() {
        return Math.floor(Date.now());
    },

    // 计算签名
    getsign: function() {
        var t = String(_.now());
        var sign = crypto.MD5(t);
        return { sign: sign, t: t };
    },

    // 构建请求头
    headers: function() {
        var s = _.getsign();
        return {
            'User-Agent': _.ua,
            'deviceid': _.did,
            't': s.t,
            's': s.sign,
            'aut': _.token
        };
    },

    // AES解密
    aesDecrypt: function(encData) {
        return crypto.AES.decrypt(encData, _.aesKey);
    },

    // 时间格式化
    dtim: function(seconds) {
        try {
            var s = parseInt(seconds);
            var h = Math.floor(s / 3600);
            var m = Math.floor((s % 3600) / 60);
            var sec = s % 60;
            var fm = m < 10 ? '0' + m : String(m);
            var fs = sec < 10 ? '0' + sec : String(sec);
            if (h > 0) {
                var fh = h < 10 ? '0' + h : String(h);
                return fh + ':' + fm + ':' + fs;
            }
            return fm + ':' + fs;
        } catch(e) {
            return '666';
        }
    },

    // 获取设备ID
    getdid: function() {
        if (_.did) return _.did;
        _.did = crypto.MD5(String(_.now()));
        return _.did;
    },

    // 获取token（域名fallback）
    gettoken: function() {
        _.getdid();
        for (var i = 0; i < _.domainSuffixes.length; i++) {
            var suffix = _.domainSuffixes[i];
            var subdomain = _.randomStr(Math.floor(Math.random() * 6) + 5);
            var currentHost = 'https://' + subdomain + '.' + suffix + '.work';
            try {
                var url = currentHost + '/api/user/traveler';
                var s = _.getsign();
                var reqHeaders = {
                    'User-Agent': _.ua,
                    'Accept': 'application/json',
                    'deviceid': _.did,
                    't': s.t,
                    's': s.sign,
                    'Content-Type': 'application/json'
                };
                var body = JSON.stringify({
                    'deviceId': _.did,
                    'tt': 'U',
                    'code': '##X-4m6Goo4zzPi1hF##',
                    'chCode': 'tt09'
                });
                var resp = http(url, {
                    headers: reqHeaders,
                    method: 'POST',
                    data: body,
                    timeout: 10
                });
                if (resp.ok) {
                    var data = JSON.parse(resp.content);
                    if (data.data) {
                        _.token = data.data.token;
                        _.phost = data.data.imgDomain;
                        _.host = currentHost;
                        return;
                    }
                }
            } catch(e) {
                // 继续尝试下一个域名
            }
        }
    },

    // 确保已初始化
    ensureInit: function() {
        if (!_.host) {
            _.gettoken();
        }
    },

    // 发起API请求
    apiRequest: function(path) {
        _.ensureInit();
        var url = _.host + path;
        var resp = http(url, { headers: _.headers(), timeout: 15 });
        if (!resp.ok) return null;
        var data = JSON.parse(resp.content);
        if (!data.encData) return null;
        var decrypted = _.aesDecrypt(data.encData);
        return JSON.parse(decrypted);
    },

    // 图片代理URL
    getProxyUrl: function() {
        return 'http://127.0.0.1:9978/proxy?do=tk';
    }
};

// ====== TVBox 蜘蛛接口 ======

var rule = {
    title: '特推',
    host: 'https://wcyfhknomg.work',
    homeUrl: '/api/video/classifyList',
    searchUrl: '/api/search/keyWord?pageSize=20&page=1&searchWord=**&searchType=1',
    searchable: 1,
    quickSearch: 1,
    filterable: 1,
    headers: {
        'User-Agent': _.ua
    }
};

function init(config) {
    _.getdid();
    _.gettoken();
    return { ok: true };
}

function homeContent(filter) {
    _.ensureInit();
    var data = _.apiRequest('/api/video/classifyList');
    var result = {
        class: [{ type_name: '精选', type_id: 'jx' }],
        filters: {}
    };
    if (data && data.data) {
        for (var i = 0; i < data.data.length; i++) {
            var item = data.data[i];
            result.class.push({
                type_name: item.classifyTitle,
                type_id: String(item.classifyId)
            });
        }
    }
    // 筛选配置
    var filterValues = [
        { n: '最近更新', v: '1' },
        { n: '最多播放', v: '2' },
        { n: '好评榜', v: '3' }
    ];
    if (result.class.length > 0) {
        for (var j = 0; j < result.class.length; j++) {
            var tid = result.class[j].type_id;
            result.filters[tid] = [{ key: 'fl', name: '分类', value: filterValues }];
        }
    }
    // 精选特殊筛选
    result.filters['jx'] = [{
        key: 'type',
        name: '精选',
        value: [
            { n: '日榜', v: '1' },
            { n: '周榜', v: '2' },
            { n: '月榜', v: '3' },
            { n: '总榜', v: '4' }
        ]
    }];
    return JSON.stringify(result);
}

function categoryContent(tid, pg, filter, extend) {
    _.ensureInit();
    pg = pg || '1';
    var fl = '1';
    var type = '1';
    try {
        var ext = JSON.parse(extend || '{}');
        fl = ext.fl || '1';
        type = ext.type || '1';
    } catch(e) {}
    
    var path = '/api/video/queryVideoByClassifyId?pageSize=20&page=' + pg + '&classifyId=' + tid + '&sortType=' + fl;
    if (tid.indexOf('click') >= 0) {
        path = '/api/video/queryPersonVideoByType?pageSize=20&page=' + pg + '&userId=' + tid.replace('click', '');
    }
    if (tid === 'jx') {
        path = '/api/video/getRankVideos?pageSize=20&page=' + pg + '&type=' + type;
    }
    
    var data = _.apiRequest(path);
    var videos = [];
    if (data && data.data) {
        for (var i = 0; i < data.data.length; i++) {
            var k = data.data[i];
            var id = (k.videoId || '') + '?' + (k.userId || '') + '?' + (k.nickName || '');
            if (tid.indexOf('click') >= 0) {
                id = id + 'click';
            }
            videos.push({
                vod_id: id,
                vod_name: k.title || '',
                vod_pic: _.getProxyUrl() + '&url=' + (k.coverImg && k.coverImg[0] ? k.coverImg[0] : ''),
                vod_remarks: _.dtim(k.playTime || 0),
                style: { type: 'rect', ratio: 1.33 }
            });
        }
    }
    return JSON.stringify({
        list: videos,
        page: parseInt(pg),
        pagecount: 9999,
        limit: 90,
        total: 999999
    });
}

function detailContent(ids) {
    _.ensureInit();
    var parts = ids.replace('click', '').split('?');
    var vid = parts[0];
    var path = '/api/video/can/watch?videoId=' + vid;
    var data = _.apiRequest(path);
    var playUrl = '';
    if (data && data.playPath) {
        playUrl = data.playPath;
    }
    var clj = '[a=cr:' + JSON.stringify({ id: parts[1] + 'click', name: parts[2] }) + '/]' + parts[2] + '[/a]';
    if (ids.indexOf('click') >= 0) {
        clj = parts[2];
    }
    return JSON.stringify({
        list: [{
            vod_director: clj,
            vod_play_from: '特推',
            vod_play_url: parts[2] + '$' + playUrl
        }]
    });
}

function searchContent(key, quick, pg) {
    _.ensureInit();
    pg = pg || '1';
    var path = '/api/search/keyWord?pageSize=20&page=' + pg + '&searchWord=' + encodeURIComponent(key) + '&searchType=1';
    var data = _.apiRequest(path);
    var videos = [];
    if (data && data.videoList) {
        for (var i = 0; i < data.videoList.length; i++) {
            var k = data.videoList[i];
            var id = (k.videoId || '') + '?' + (k.userId || '') + '?' + (k.nickName || '');
            videos.push({
                vod_id: id,
                vod_name: k.title || '',
                vod_pic: _.getProxyUrl() + '&url=' + (k.coverImg && k.coverImg[0] ? k.coverImg[0] : ''),
                vod_remarks: _.dtim(k.playTime || 0),
                style: { type: 'rect', ratio: 1.33 }
            });
        }
    }
    return JSON.stringify({
        list: videos,
        page: parseInt(pg),
        pagecount: 9999,
        limit: 90,
        total: 999999
    });
}

function playerContent(flag, id, vipFlags) {
    return JSON.stringify({
        parse: 0,
        url: id,
        header: JSON.stringify(_.headers())
    });
}