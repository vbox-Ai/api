/*
 * 星空4K JS 蜘蛛
 * 适配 vbox-ios JSSpiderEngine (type:3 独立引擎)
 * AES-128-CBC 解密 / 无需翻墙
 */

// ===================== Base64 解码 =====================
function b64decode(s) {
    var chars = 'ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789+/';
    s = s.replace(/[\s\r\n]/g, '');
    var pad = (4 - s.length % 4) % 4;
    s += '===='.slice(0, pad);
    var result = [], buf = 0, bits = 0;
    for (var i = 0; i < s.length; i++) {
        var idx = chars.indexOf(s[i]);
        if (idx < 0) continue;
        buf = (buf << 6) | idx;
        bits += 6;
        if (bits >= 8) { bits -= 8; result.push((buf >> bits) & 0xFF); }
    }
    return result;
}

// ===================== AES-128-CBC 解密 =====================
var AES = (function() {
    var SBOX = [0x63,0x7c,0x77,0x7b,0xf2,0x6b,0x6f,0xc5,0x30,0x01,0x67,0x2b,0xfe,0xd7,0xab,0x76,0xca,0x82,0xc9,0x7d,0xfa,0x59,0x47,0xf0,0xad,0xd4,0xa2,0xaf,0x9c,0xa4,0x72,0xc0,0xb7,0xfd,0x93,0x26,0x36,0x3f,0xf7,0xcc,0x34,0xa5,0xe5,0xf1,0x71,0xd8,0x31,0x15,0x04,0xc7,0x23,0xc3,0x18,0x96,0x05,0x9a,0x07,0x12,0x80,0xe2,0xeb,0x27,0xb2,0x75,0x09,0x83,0x2c,0x1a,0x1b,0x6e,0x5a,0xa0,0x52,0x3b,0xd6,0xb3,0x29,0xe3,0x2f,0x84,0x53,0xd1,0x00,0xed,0x20,0xfc,0xb1,0x5b,0x6a,0xcb,0xbe,0x39,0x4a,0x4c,0x58,0xcf,0xd0,0xef,0xaa,0xfb,0x43,0x4d,0x33,0x85,0x45,0xf9,0x02,0x7f,0x50,0x3c,0x9f,0xa8,0x51,0xa3,0x40,0x8f,0x92,0x9d,0x38,0xf5,0xbc,0xb6,0xda,0x21,0x10,0xff,0xf3,0xd2,0xcd,0x0c,0x13,0xec,0x5f,0x97,0x44,0x17,0xc4,0xa7,0x7e,0x3d,0x64,0x5d,0x19,0x73,0x60,0x81,0x4f,0xdc,0x22,0x2a,0x90,0x88,0x46,0xee,0xb8,0x14,0xde,0x5e,0x0b,0xdb,0xe0,0x32,0x3a,0x0a,0x49,0x06,0x24,0x5c,0xc2,0xd3,0xac,0x62,0x91,0x95,0xe4,0x79,0xe7,0xc8,0x37,0x6d,0x8d,0xd5,0x4e,0xa9,0x6c,0x56,0xf4,0xea,0x65,0x7a,0xae,0x08,0xba,0x78,0x25,0x2e,0x1c,0xa6,0xb4,0xc6,0xe8,0xdd,0x74,0x1f,0x4b,0xbd,0x8b,0x8a,0x70,0x3e,0xb5,0x66,0x48,0x03,0xf6,0x0e,0x61,0x35,0x57,0xb9,0x86,0xc1,0x1d,0x9e,0xe1,0xf8,0x98,0x11,0x69,0xd9,0x8e,0x94,0x9b,0x1e,0x87,0xe9,0xce,0x55,0x28,0xdf,0x8c,0xa1,0x89,0x0d,0xbf,0xe6,0x42,0x68,0x41,0x99,0x2d,0x0f,0xb0,0x54,0xbb,0x16];
    var INV_SBOX = [0x52,0x09,0x6a,0xd5,0x30,0x36,0xa5,0x38,0xbf,0x40,0xa3,0x9e,0x81,0xf3,0xd7,0xfb,0x7c,0xe3,0x39,0x82,0x9b,0x2f,0xff,0x87,0x34,0x8e,0x43,0x44,0xc4,0xde,0xe9,0xcb,0x54,0x7b,0x94,0x32,0xa6,0xc2,0x23,0x3d,0xee,0x4c,0x95,0x0b,0x42,0xfa,0xc3,0x4e,0x08,0x2e,0xa1,0x66,0x28,0xd9,0x24,0xb2,0x76,0x5b,0xa2,0x49,0x6d,0x8b,0xd1,0x25,0x72,0xf8,0xf6,0x64,0x86,0x68,0x98,0x16,0xd4,0xa4,0x5c,0xcc,0x5d,0x65,0xb6,0x92,0x6c,0x70,0x48,0x50,0xfd,0xed,0xb9,0xda,0x5e,0x15,0x46,0x57,0xa7,0x8d,0x9d,0x84,0x90,0xd8,0xab,0x00,0x8c,0xbc,0xd3,0x0a,0xf7,0xe4,0x58,0x05,0xb8,0xb3,0x45,0x06,0xd0,0x2c,0x1e,0x8f,0xca,0x3f,0x0f,0x02,0xc1,0xaf,0xbd,0x03,0x01,0x13,0x8a,0x6b,0x3a,0x91,0x11,0x41,0x4f,0x67,0xdc,0xea,0x97,0xf2,0xcf,0xce,0xf0,0xb4,0xe6,0x73,0x96,0xac,0x74,0x22,0xe7,0xad,0x35,0x85,0xe2,0xf9,0x37,0xe8,0x1c,0x75,0xdf,0x6e,0x47,0xf1,0x1a,0x71,0x1d,0x29,0xc5,0x89,0x6f,0xb7,0x62,0x0e,0xaa,0x18,0xbe,0x1b,0xfc,0x56,0x3e,0x4b,0xc6,0xd2,0x79,0x20,0x9a,0xdb,0xc0,0xfe,0x78,0xcd,0x5a,0xf4,0x1f,0xdd,0xa8,0x33,0x88,0x07,0xc7,0x31,0xb1,0x12,0x10,0x59,0x27,0x80,0xec,0x5f,0x60,0x51,0x7f,0xa9,0x19,0xb5,0x4a,0x0d,0x2d,0xe5,0x7a,0x9f,0x93,0xc9,0x9c,0xef,0xa0,0xe0,0x3b,0x4d,0xae,0x2a,0xf5,0xb0,0xc8,0xeb,0xbb,0x3c,0x83,0x53,0x99,0x61,0x17,0x2b,0x04,0x7e,0xba,0x77,0xd6,0x26,0xe1,0x69,0x14,0x63,0x55,0x21,0x0c,0x7d];
    var RCON = [0x01,0x02,0x04,0x08,0x10,0x20,0x40,0x80,0x1b,0x36];
    function xtime(a){return((a<<1)^(a>>7)&0xFF)&0xFF;}
    function mul(a,b){var r=0;for(var i=0;i<8;i++){if(b&1)r^=a;var hi=a&0x80;a=(a<<1)&0xFF;if(hi)a^=0x1b;b>>=1;}return r;}
    function keyExpansion(key){var nk=key.length/4,nb=4,nr=nk+6,w=[];for(var i=0;i<nk;i++)w[i]=(key[i*4]<<24)|(key[i*4+1]<<16)|(key[i*4+2]<<8)|key[i*4+3];for(i=nk;i<nb*(nr+1);i++){var t=w[i-1];if(i%nk===0){t=((SBOX[(t>>16)&0xFF]<<24)|(SBOX[(t>>8)&0xFF]<<16)|(SBOX[t&0xFF]<<8)|SBOX[(t>>24)&0xFF])^(RCON[i/nk-1]<<24);}else if(nk>6&&i%nk===4){t=(SBOX[(t>>24)&0xFF]<<24)|(SBOX[(t>>16)&0xFF]<<16)|(SBOX[(t>>8)&0xFF]<<8)|SBOX[t&0xFF];}w[i]=w[i-nk]^t;}return w;}
    function addRoundKey(s,w,r){for(var i=0;i<4;i++)for(var j=0;j<4;j++)s[i][j]^=w[r*4+j]>>(24-8*i)&0xFF;}
    function invSubBytes(s){for(var i=0;i<4;i++)for(var j=0;j<4;j++)s[i][j]=INV_SBOX[s[i][j]];}
    function invShiftRows(s){var t;t=s[1][3];s[1][3]=s[1][2];s[1][2]=s[1][1];s[1][1]=s[1][0];s[1][0]=t;t=s[2][0];s[2][0]=s[2][2];s[2][2]=t;t=s[2][1];s[2][1]=s[2][3];s[2][3]=t;t=s[3][0];s[3][0]=s[3][1];s[3][1]=s[3][2];s[3][2]=s[3][3];s[3][3]=t;}
    function invMixColumns(s){for(var i=0;i<4;i++){var a=s[i][0],b=s[i][1],c=s[i][2],d=s[i][3];s[i][0]=mul(a,14)^mul(b,11)^mul(c,13)^mul(d,9);s[i][1]=mul(a,9)^mul(b,14)^mul(c,11)^mul(d,13);s[i][2]=mul(a,13)^mul(b,9)^mul(c,14)^mul(d,11);s[i][3]=mul(a,11)^mul(b,13)^mul(c,9)^mul(d,14);}}
    function bytesToState(b){var s=[[0,0,0,0],[0,0,0,0],[0,0,0,0],[0,0,0,0]];for(var i=0;i<16;i++)s[i%4][Math.floor(i/4)]=b[i];return s;}
    function stateToBytes(s){var b=[];for(var i=0;i<4;i++)for(var j=0;j<4;j++)b.push(s[i][j]);return b;}
    function decryptBlock(input,w){var s=bytesToState(input),nr=w.length/4-1;addRoundKey(s,w,nr);for(var r=nr-1;r>0;r--){invShiftRows(s);invSubBytes(s);addRoundKey(s,w,r);invMixColumns(s);}invShiftRows(s);invSubBytes(s);addRoundKey(s,w,0);return stateToBytes(s);}
    function xorBlocks(a,b){var r=[];for(var i=0;i<a.length;i++)r[i]=a[i]^b[i];return r;}
    return{
        decrypt:function(hexStr,keyStr,ivStr){
            var key=[],iv=[];
            for(var i=0;i<keyStr.length&&i<16;i++)key.push(keyStr.charCodeAt(i));
            for(i=0;i<16-key.length;i++)key.push(0);
            for(i=0;i<ivStr.length&&i<16;i++)iv.push(ivStr.charCodeAt(i));
            for(i=0;i<16-iv.length;i++)iv.push(0);
            var w=keyExpansion(key);
            var ct=[];for(i=0;i<hexStr.length;i+=2)ct.push(parseInt(hexStr.substr(i,2),16));
            var pt=[];for(i=0;i<ct.length;i+=16){var dec=decryptBlock(ct.slice(i,i+16),w);var xored=xorBlocks(dec,i===0?iv:ct.slice(i-16,i));pt=pt.concat(xored);}
            var pad=pt[pt.length-1];if(pad<1||pad>16)pad=0;pt=pt.slice(0,pt.length-pad);
            var str='';for(i=0;i<pt.length;i++)str+=String.fromCharCode(pt[i]);return str;
        }
    };
})();

// ===================== 蜘蛛主体 =====================
var spider = {
    __jsEvalReturn: function() {
        var API = 'https://xk211.xkgzs.xyz/api/vod/';
        var AES_KEY = '11320jkjksdkxxaw';
        var PAGE_SIZE = 36;
        var HEADER = {
            'User-Agent': 'okhttp/4.12.0',
            'Content-Type': 'application/x-www-form-urlencoded',
            'App-Version-Code': '123',
            'App-Os-Type': 'android',
            'App-Ui-Mode': '2',
            'App-Device-Id': '1234567890abcdef1234567890abcdef'
        };

        var _initData = null;
        var _initTime = 0;

        // Base64 → Hex 转换（AES.decrypt 需要 hex 输入）
        function b64ToHex(s) {
            var bytes = b64decode(s);
            var hex = '';
            for (var i = 0; i < bytes.length; i++) hex += ('0' + bytes[i].toString(16)).slice(-2);
            return hex;
        }

        // 解密响应：Base64 → AES-CBC(key=IV) → JSON
        function decryptData(encrypted) {
            var hex = b64ToHex(encrypted);
            var str = AES.decrypt(hex, AES_KEY, AES_KEY);
            return JSON.parse(str);
        }

        // URL 编码参数
        function encodeParams(obj) {
            var parts = [];
            for (var k in obj) {
                if (obj.hasOwnProperty(k)) {
                    parts.push(encodeURIComponent(k) + '=' + encodeURIComponent(obj[k]));
                }
            }
            return parts.join('&');
        }

        // 通用 POST 请求
        function post(endpoint, data) {
            try {
                var body = data ? encodeParams(data) : '';
                var url = API + endpoint;
                var respObj = req(url, { method: 'POST', headers: HEADER, data: body });
                if (!respObj) { print('>>> xk req null: ' + endpoint); return {}; }
                var respStr = (typeof respObj === 'string') ? respObj : (respObj.data || respObj.content || '');
                if (!respStr) { print('>>> xk empty resp: ' + endpoint); return {}; }
                var respJson = JSON.parse(respStr);
                if (respJson.code !== 0) { print('>>> xk code=' + respJson.code + ': ' + endpoint); return {}; }
                var encrypted = respJson.data;
                if (!encrypted) return {};
                return decryptData(encrypted);
            } catch (e) {
                print('>>> xk ERROR (' + endpoint + '): ' + e);
                return {};
            }
        }

        // 带缓存的 init
        function getInit() {
            var now = Math.floor(Date.now() / 1000);
            if (_initData === null || now - _initTime > 600) {
                _initData = post('init', {});
                _initTime = now;
            }
            return _initData || {};
        }

        // 标准视频条目
        function vod(item) {
            return {
                vod_id: String(item.vod_id || ''),
                vod_name: item.vod_name || '',
                vod_pic: item.vod_pic || '',
                vod_remarks: item.vod_remarks || ''
            };
        }

        // 判断是否直链视频格式
        function isVideoFormat(url) {
            if (!url) return false;
            var u = url.toLowerCase();
            return u.indexOf('.m3u8') >= 0 || u.indexOf('.mp4') >= 0 || u.indexOf('.flv') >= 0 || u.indexOf('.mkv') >= 0 || u.indexOf('.mpd') >= 0;
        }

        return {
            init: function(config) { return true; },

            homeContent: function(filter) {
                try {
                    var data = getInit();
                    var classes = [];
                    var typeList = data.type_list || [];
                    for (var i = 0; i < typeList.length; i++) {
                        if (typeList[i].type_id) {
                            classes.push({
                                type_id: String(typeList[i].type_id),
                                type_name: typeList[i].type_name || ''
                            });
                        }
                    }
                    var videos = data.recommend_list || data.hot_search_list || [];
                    var vlist = [];
                    for (var j = 0; j < videos.length; j++) vlist.push(vod(videos[j]));
                    return { class: classes, list: vlist, filters: {} };
                } catch (e) {
                    print('>>> xk homeContent ERROR: ' + e);
                    return { class: [], list: [], filters: {} };
                }
            },

            homeVideoContent: function() {
                try {
                    var data = getInit();
                    var videos = data.recommend_list || data.hot_search_list || [];
                    var vlist = [];
                    for (var i = 0; i < videos.length; i++) vlist.push(vod(videos[i]));
                    return { list: vlist };
                } catch (e) {
                    print('>>> xk homeVideoContent ERROR: ' + e);
                    return { list: [] };
                }
            },

            categoryContent: function(tid, pg, extend) {
                try {
                    var ext = {};
                    try { ext = typeof extend === 'string' ? JSON.parse(extend) : (extend || {}); } catch(e) {}
                    var page = Math.max(parseInt(pg) || 1, 1);
                    var params = { type_id: tid, page: page };
                    var keys = ['class', 'area', 'lang', 'year', 'sort', 'by'];
                    for (var i = 0; i < keys.length; i++) {
                        if (ext[keys[i]]) params[keys[i]] = ext[keys[i]];
                    }
                    var data = post('typeFilterVodList', params);
                    var items = data.recommend_list || [];
                    var total = parseInt(data.total) || 0;
                    var pageSize = parseInt(data.page_size) || PAGE_SIZE;
                    var pagecount = total ? Math.ceil(total / pageSize) : (page + (items.length >= pageSize ? 1 : 0));
                    var vlist = [];
                    for (var j = 0; j < items.length; j++) vlist.push(vod(items[j]));
                    return { page: page, pagecount: Math.max(pagecount, page), limit: pageSize, total: total, list: vlist };
                } catch (e) {
                    print('>>> xk categoryContent ERROR: ' + e);
                    return { page: 1, pagecount: 1, limit: PAGE_SIZE, total: 0, list: [] };
                }
            },

            detailContent: function(ids) {
                try {
                    var data = post('vodDetail', { vod_id: ids[0] });
                    var vodData = data.vod || {};

                    // 构建播放源信息映射
                    var sourceInfo = {};
                    var playerSourceList = data.player_source_list || [];
                    for (var i = 0; i < playerSourceList.length; i++) {
                        var s = playerSourceList[i];
                        sourceInfo[s.player_code || ''] = s;
                    }

                    var playFrom = [];
                    var playUrls = [];
                    var vodPlayUrlList = data.vod_play_url_list || [];
                    for (var j = 0; j < vodPlayUrlList.length; j++) {
                        var source = vodPlayUrlList[j];
                        var code = source.player_code || '';
                        var player = sourceInfo[code] || {};
                        var sourceId = player.id;
                        if (sourceId === undefined || sourceId === null) continue;

                        var episodes = [];
                        var urls = source.urls || [];
                        for (var k = 0; k < urls.length; k++) {
                            var ep = urls[k];
                            var url = ep.url || '';
                            var playId;
                            if (url && isVideoFormat(url)) {
                                playId = url;
                            } else {
                                playId = 'xk://' + ids[0] + '/' + sourceId + '/' + (ep.episode_index || 0);
                            }
                            episodes.push((ep.name || '播放') + '$' + playId);
                        }
                        if (episodes.length > 0) {
                            playFrom.push(player.player_name || code || '播放');
                            playUrls.push(episodes.join('#'));
                        }
                    }

                    var item = vod(vodData);
                    item.vod_actor = vodData.vod_actor || '';
                    item.vod_director = vodData.vod_director || '';
                    item.vod_content = vodData.vod_content || vodData.vod_blurb || '';
                    item.vod_year = vodData.vod_year || '';
                    item.vod_area = vodData.vod_area || '';
                    item.vod_play_from = playFrom.join('$$$');
                    item.vod_play_url = playUrls.join('$$$');

                    return { list: [item] };
                } catch (e) {
                    print('>>> xk detailContent ERROR: ' + e);
                    return { list: [] };
                }
            },

            searchContent: function(key, quick, pg) {
                try {
                    var page = Math.max(parseInt(pg) || 1, 1);
                    var data = post('searchList', { keywords: key, page: page });
                    var items = data.search_list || [];
                    var vlist = [];
                    for (var i = 0; i < items.length; i++) vlist.push(vod(items[i]));
                    return { page: page, pagecount: page + (items.length >= PAGE_SIZE ? 1 : 0), list: vlist };
                } catch (e) {
                    print('>>> xk searchContent ERROR: ' + e);
                    return { page: 1, pagecount: 1, list: [] };
                }
            },

            playerContent: function(flag, id, vipFlags) {
                try {
                    var url = id;
                    if (id.indexOf('xk://') === 0) {
                        var parts = id.substring(5).split('/');
                        var vodId = parts[0];
                        var sourceId = parts[1];
                        var episodeIndex = parts[2];
                        var data = post('vodParse', {
                            vod_id: vodId,
                            player_source_id: sourceId,
                            episode_index: episodeIndex,
                            scene: '0'
                        });
                        url = data.play_url || '';
                    }
                    var direct = isVideoFormat(url);
                    return {
                        parse: direct ? 0 : 1,
                        url: url,
                        header: JSON.stringify({ 'User-Agent': 'okhttp/4.12.0' })
                    };
                } catch (e) {
                    print('>>> xk playerContent ERROR: ' + e);
                    return { parse: 0, url: '', header: '' };
                }
            }
        };
    }
};