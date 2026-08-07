/*
 * TVSO JS 蜘蛛 v1.1
 * 适配 vbox-ios JSSpiderEngine (type:3 独立引擎)
 * 目标站: https://www.tvso.uk
 * API站: https://api.tvso.uk
 * 特点: Vue/Vite SPA，API 响应 AES-256-CBC 加密，需客户端解密
 * 支持网盘：夸克网盘、百度网盘
 * 无需登录，无需加密签名
 *
 * 网盘蜘蛛源约定：
 *   - vod_remarks 以 "☁️" 开头 → 标识为网盘资源，激活网盘UI
 *   - detailContent 的 vod_play_url 返回 JSON 数组 [{"url":"网盘链接","name":"网盘名"}]
 *   - vod_id 编码格式: {item_id}|||{title}|||{url}
 */

var spider = {
    __jsEvalReturn: function() {

        var BASE_URL = 'https://www.tvso.uk';
        var API_BASE_URL = 'https://api.tvso.uk';
        var UA = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36';
        var HEADER = {
            'User-Agent': UA,
            'Referer': BASE_URL + '/',
            'Accept': 'application/json'
        };

        // AES-256-CBC 密钥（如站点更新密钥，需同步修改）
        var AES_KEY = 'vb7n4xRMYFXEFfQdMuaUYrEBkK5Qx5Mc';

        // ===================== AES 解密工具函数 =====================

        // Base64 解码为字节数组
        function base64ToBytes(base64) {
            var chars = 'ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789+/';
            var lookup = {};
            for (var i = 0; i < chars.length; i++) {
                lookup[chars.charAt(i)] = i;
            }

            var len = base64.length;
            var bytes = [];
            for (var j = 0; j < len; j += 4) {
                var encoded1 = lookup[base64.charAt(j)];
                var encoded2 = lookup[base64.charAt(j + 1)];
                var encoded3 = lookup[base64.charAt(j + 2)];
                var encoded4 = lookup[base64.charAt(j + 3)];

                bytes.push((encoded1 << 2) | (encoded2 >> 4));
                if (base64.charAt(j + 2) !== '=') {
                    bytes.push(((encoded2 & 15) << 4) | (encoded3 >> 2));
                }
                if (base64.charAt(j + 3) !== '=') {
                    bytes.push(((encoded3 & 3) << 6) | encoded4);
                }
            }
            return bytes;
        }

        // UTF-8 字节数组转字符串
        function utf8BytesToString(bytes) {
            var result = '';
            var i = 0;
            while (i < bytes.length) {
                var c = bytes[i];
                if (c < 128) {
                    result += String.fromCharCode(c);
                    i++;
                } else if ((c & 0xE0) === 0xC0) {
                    result += String.fromCharCode(((c & 0x1F) << 6) | (bytes[i + 1] & 0x3F));
                    i += 2;
                } else {
                    result += String.fromCharCode(((c & 0x0F) << 12) | ((bytes[i + 1] & 0x3F) << 6) | (bytes[i + 2] & 0x3F));
                    i += 3;
                }
            }
            return result;
        }

        // 字符串转 UTF-8 字节数组
        function stringToUtf8Bytes(str) {
            var bytes = [];
            for (var i = 0; i < str.length; i++) {
                var c = str.charCodeAt(i);
                if (c < 128) {
                    bytes.push(c);
                } else if (c < 2048) {
                    bytes.push((c >> 6) | 192);
                    bytes.push((c & 63) | 128);
                } else {
                    bytes.push((c >> 12) | 224);
                    bytes.push(((c >> 6) & 63) | 128);
                    bytes.push((c & 63) | 128);
                }
            }
            return bytes;
        }

        // ===================== 纯 JS AES-256-CBC 实现 =====================
        // 由于 vbox 引擎的 crypto.AES.decrypt 使用 IV=key，而 TVSO API 返回独立 IV，
        // 此处实现完整的 AES-256-CBC 解密以支持自定义 IV

        // AES S-box 及逆 S-box（程序化生成，避免硬编码 512 字节表）
        var _SBOX = new Array(256);
        var _INVSBOX = new Array(256);
        (function() {
            var p = 1, q = 1;
            do {
                // p *= 3 (GF(2^8) 原根)
                p = p ^ (p << 1) ^ (p & 0x80 ? 0x1b : 0);
                p &= 0xff;
                // q /= 3
                q ^= q << 1; q ^= q << 2; q ^= q << 4;
                q ^= q & 0x80 ? 0x09 : 0;
                q &= 0xff;
                // 仿射变换
                var x = q ^ ((q << 1) | (q >> 7)) ^ ((q << 2) | (q >> 6)) ^
                        ((q << 3) | (q >> 5)) ^ ((q << 4) | (q >> 4));
                _SBOX[p] = (x ^ 0x63) & 0xff;
            } while (p !== 1);
            _SBOX[0] = 0x63;
            for (var i = 0; i < 256; i++) _INVSBOX[_SBOX[i]] = i;
        })();

        // GF(2^8) 乘法
        function _gmul(a, b) {
            var r = 0;
            for (var i = 0; i < 8; i++) {
                if (b & 1) r ^= a;
                var hi = a & 0x80;
                a = (a << 1) & 0xff;
                if (hi) a ^= 0x1b;
                b >>= 1;
            }
            return r;
        }

        // AES-256 密钥扩展（32 字节密钥 → 240 字节扩展密钥 = 60 个 4 字节字）
        function _keyExpansion(key) {
            var Nk = 8, Nr = 14;
            var w = [];
            for (var i = 0; i < Nk; i++) {
                w[i] = [key[4 * i], key[4 * i + 1], key[4 * i + 2], key[4 * i + 3]];
            }
            var rcon = [0x01, 0x02, 0x04, 0x08, 0x10, 0x20, 0x40];
            for (var i = Nk; i < 4 * (Nr + 1); i++) {
                var t = w[i - 1].slice();
                if (i % Nk === 0) {
                    t = [t[1], t[2], t[3], t[0]]; // RotWord
                    for (var j = 0; j < 4; j++) t[j] = _SBOX[t[j]]; // SubWord
                    t[0] ^= rcon[i / Nk - 1];
                } else if (i % Nk === 4) {
                    for (var j = 0; j < 4; j++) t[j] = _SBOX[t[j]]; // SubWord (AES-256 only)
                }
                w[i] = [w[i - Nk][0] ^ t[0], w[i - Nk][1] ^ t[1],
                        w[i - Nk][2] ^ t[2], w[i - Nk][3] ^ t[3]];
            }
            return w;
        }

        // AES-256 逆密码（解密单个 16 字节块）
        function _decryptBlock(input, w) {
            var s = input.slice();
            var Nr = 14;
            var t, i, c;

            // AddRoundKey（最后一轮）
            for (i = 0; i < 16; i++) s[i] ^= w[Nr * 4 + (i >> 2)][i % 4];

            for (var round = Nr - 1; round >= 1; round--) {
                // InvShiftRows
                t = s[13]; s[13] = s[9]; s[9] = s[5]; s[5] = s[1]; s[1] = t;
                t = s[2]; s[2] = s[10]; s[10] = t; t = s[6]; s[6] = s[14]; s[14] = t;
                t = s[3]; s[3] = s[7]; s[7] = s[11]; s[11] = s[15]; s[15] = t;
                // InvSubBytes
                for (i = 0; i < 16; i++) s[i] = _INVSBOX[s[i]];
                // AddRoundKey
                for (i = 0; i < 16; i++) s[i] ^= w[round * 4 + (i >> 2)][i % 4];
                // InvMixColumns
                for (c = 0; c < 4; c++) {
                    var a0 = s[c * 4], a1 = s[c * 4 + 1], a2 = s[c * 4 + 2], a3 = s[c * 4 + 3];
                    s[c * 4]     = _gmul(a0, 0x0e) ^ _gmul(a1, 0x0b) ^ _gmul(a2, 0x0d) ^ _gmul(a3, 0x09);
                    s[c * 4 + 1] = _gmul(a0, 0x09) ^ _gmul(a1, 0x0e) ^ _gmul(a2, 0x0b) ^ _gmul(a3, 0x0d);
                    s[c * 4 + 2] = _gmul(a0, 0x0d) ^ _gmul(a1, 0x09) ^ _gmul(a2, 0x0e) ^ _gmul(a3, 0x0b);
                    s[c * 4 + 3] = _gmul(a0, 0x0b) ^ _gmul(a1, 0x0d) ^ _gmul(a2, 0x09) ^ _gmul(a3, 0x0e);
                }
            }

            // 最后一轮（无 InvMixColumns）
            t = s[13]; s[13] = s[9]; s[9] = s[5]; s[5] = s[1]; s[1] = t;
            t = s[2]; s[2] = s[10]; s[10] = t; t = s[6]; s[6] = s[14]; s[14] = t;
            t = s[3]; s[3] = s[7]; s[7] = s[11]; s[11] = s[15]; s[15] = t;
            for (i = 0; i < 16; i++) s[i] = _INVSBOX[s[i]];
            for (i = 0; i < 16; i++) s[i] ^= w[i >> 2][i % 4];

            return s;
        }

        // AES-256-CBC 解密 + PKCS7 去填充
        function _aesCbcDecrypt(ciphertext, key, iv) {
            var w = _keyExpansion(key);
            var plaintext = [];

            for (var i = 0; i < ciphertext.length; i += 16) {
                var block = ciphertext.slice(i, i + 16);
                var dec = _decryptBlock(block, w);
                for (var j = 0; j < 16; j++) dec[j] ^= iv[j];
                plaintext = plaintext.concat(dec);
                iv = block;
            }

            // PKCS7 去填充
            var padLen = plaintext[plaintext.length - 1];
            if (padLen > 0 && padLen <= 16) {
                plaintext = plaintext.slice(0, plaintext.length - padLen);
            }
            return plaintext;
        }

        // AES-256-CBC 解密入口
        // ciphertext: Base64 编码的密文
        // key: UTF-8 字符串密钥（32 字节 = AES-256）
        // iv: Base64 编码的初始化向量
        function aesDecrypt(ciphertext, key, iv) {
            // 策略1：优先使用全局 CryptoJS（如果引擎注入了的话）
            if (typeof CryptoJS !== 'undefined' && CryptoJS.AES && CryptoJS.enc && CryptoJS.mode && CryptoJS.pad) {
                try {
                    var keyWA = CryptoJS.enc.Utf8.parse(key);
                    var ivWA = CryptoJS.enc.Base64.parse(iv);
                    var cipherWA = CryptoJS.enc.Base64.parse(ciphertext);
                    var decrypted = CryptoJS.AES.decrypt(
                        { ciphertext: cipherWA },
                        keyWA,
                        { iv: ivWA, mode: CryptoJS.mode.CBC, padding: CryptoJS.pad.Pkcs7 }
                    );
                    var result = decrypted.toString(CryptoJS.enc.Utf8);
                    if (result) return result;
                } catch (e) {
                    print('>>> tvso CryptoJS decrypt ERROR: ' + e);
                }
            }

            // 策略2：纯 JS AES-256-CBC 实现（支持自定义 IV）
            try {
                var keyBytes = stringToUtf8Bytes(key);
                var ivBytes = base64ToBytes(iv);
                var cipherBytes = base64ToBytes(ciphertext);

                if (keyBytes.length !== 32) {
                    print('>>> tvso aesDecrypt: key length=' + keyBytes.length + ' (expected 32)');
                    return '';
                }
                if (ivBytes.length !== 16) {
                    print('>>> tvso aesDecrypt: iv length=' + ivBytes.length + ' (expected 16)');
                    return '';
                }

                var plainBytes = _aesCbcDecrypt(cipherBytes, keyBytes, ivBytes);
                var plaintext = utf8BytesToString(plainBytes);
                print('>>> tvso aesDecrypt (pure JS): success, length=' + plaintext.length);
                return plaintext;
            } catch (e) {
                print('>>> tvso aesDecrypt (pure JS) ERROR: ' + e);
                return '';
            }
        }

        // ===================== 工具函数 =====================

        // GET 请求 API（TVSO API 使用 GET + query params）
        function fetchAPI(path, params) {
            try {
                var url = API_BASE_URL + path;
                if (params) {
                    var qs = [];
                    for (var k in params) {
                        if (params[k] !== null && params[k] !== undefined) {
                            qs.push(encodeURIComponent(k) + '=' + encodeURIComponent(params[k]));
                        }
                    }
                    if (qs.length > 0) {
                        url += '?' + qs.join('&');
                    }
                }

                var resp = req(url, { method: 'GET', headers: HEADER, timeout: 15000 });
                if (resp && resp.ok) {
                    var content = resp.content || '';
                    if (typeof content === 'object') return content;
                    try { return JSON.parse(content); } catch (e) {
                        print('>>> tvso fetchAPI JSON parse ERROR: ' + e);
                        return null;
                    }
                }
                print('>>> tvso fetchAPI FAIL: status=' + (resp ? resp.status : 'null') + ' url=' + url.substring(0, 80));
                return null;
            } catch (e) {
                print('>>> tvso fetchAPI ERROR: ' + e);
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

        function encodeVodId(id, title, url) {
            return String(id) + '|||' + encodeURIComponent(title || '') + '|||' + encodeURIComponent(url || '');
        }

        function decodeVodId(vodId) {
            var parts = String(vodId).split('|||');
            return {
                id: parts[0] || '',
                title: parts[1] ? decodeURIComponent(parts[1]) : '',
                url: parts[2] ? decodeURIComponent(parts[2]) : ''
            };
        }

        // 获取当前时间戳（毫秒）
        function timestamp() {
            return String(Date.now());
        }

        // 解密 API 响应
        // API 响应结构: {"code":200,"message":"...","data":{"data":"<base64密文>","iv":"<base64 IV>"}}
        function decryptResponse(apiResp) {
            if (!apiResp || apiResp.code !== 200 || !apiResp.data) {
                print('>>> tvso decryptResponse: invalid API response, code=' + (apiResp ? apiResp.code : 'null'));
                return null;
            }

            var encrypted = apiResp.data;
            if (!encrypted.data || !encrypted.iv) {
                print('>>> tvso decryptResponse: missing data/iv fields');
                return null;
            }

            try {
                var plaintext = aesDecrypt(encrypted.data, AES_KEY, encrypted.iv);
                if (!plaintext) return null;
                return JSON.parse(plaintext);
            } catch (e) {
                print('>>> tvso decryptResponse ERROR: ' + e);
                return null;
            }
        }

        // 从网盘链接推断网盘名称
        function inferPanName(url) {
            if (!url) return '网盘';
            if (url.indexOf('pan.quark.cn') !== -1) return '夸克网盘';
            if (url.indexOf('pan.baidu.com') !== -1) return '百度网盘';
            if (url.indexOf('pan.xunlei.com') !== -1) return '迅雷云盘';
            if (url.indexOf('share.weiyun.com') !== -1) return '腾讯微云';
            return '网盘';
        }

        // ===================== 首页内容 =====================

        function homeContent(filter) {
            var result = { class: [], list: [] };
            var hotKeywords = ['庆余年', '凡人修仙传', '九门', '斩神', '完美世界'];

            try {
                var apiResp = fetchAPI('/api/v2/resource/paginate', {
                    key: hotKeywords[0],
                    page: 1,
                    limit: 24,
                    t: timestamp()
                });

                var decrypted = decryptResponse(apiResp);
                if (decrypted && decrypted.list) {
                    result.list = parseSearchResults(decrypted.list);
                }
            } catch (e) {
                print('>>> tvso homeContent ERROR: ' + e);
            }

            return result;
        }

        function parseSearchResults(items) {
            var list = [];
            if (!items) return list;

            var seen = {};

            for (var i = 0; i < items.length; i++) {
                var item = items[i];
                var title = stripTags(item.title || '未知资源');
                var id = item.id || ('idx_' + i);
                var url = item.quarkLink || item.url || '';

                if (!title) continue;

                var dedupKey = title + '_' + url;
                if (seen[dedupKey]) continue;
                seen[dedupKey] = true;

                var panName = inferPanName(url);

                list.push({
                    vod_id: encodeVodId(id, title, url),
                    vod_name: title,
                    vod_pic: item.cover || '',
                    vod_remarks: '☁️' + panName
                });
            }

            return list;
        }

        // ===================== 分类内容 =====================
        // 不支持分类浏览

        function categoryContent(tid, pg, filter, extend) {
            return { list: [], page: 1, pagecount: 0, limit: 20, total: 0 };
        }

        // ===================== 搜索内容 =====================

        function searchContent(key, quick, pg) {
            var page = parseInt(pg) || 1;
            var result = { list: [], page: page, pagecount: 1 };

            if (typeof quick === 'number') {
                page = quick;
            }

            try {
                var apiResp = fetchAPI('/api/v2/resource/paginate', {
                    key: key,
                    page: page,
                    limit: 20,
                    t: timestamp()
                });

                var decrypted = decryptResponse(apiResp);
                if (!decrypted || !decrypted.list || decrypted.list.length === 0) {
                    print('>>> tvso searchContent: no data for key=' + key);
                    return result;
                }

                result.list = parseSearchResults(decrypted.list);

                var hasMore = page * 20 < (decrypted.total || 0);
                result.pagecount = hasMore ? page + 1 : page;

                print('>>> tvso searchContent: key=' + key + ' pg=' + page + ' count=' + result.list.length);
            } catch (e) {
                print('>>> tvso searchContent ERROR: ' + e);
            }

            return result;
        }

        // ===================== 详情内容 =====================

        function detailContent(ids) {
            var result = { list: [] };

            if (!ids) {
                print('>>> tvso detailContent: empty ids');
                return result;
            }

            var id = String(ids);
            var decoded = decodeVodId(id);
            print('>>> tvso detailContent: id=' + id.substring(0, 80));

            var realUrl = decoded.url;

            // 如果 vod_id 中没有 URL，尝试重新搜索获取
            if (!realUrl && decoded.title) {
                try {
                    var apiResp = fetchAPI('/api/v2/resource/paginate', {
                        key: decoded.title,
                        page: 1,
                        limit: 10,
                        t: timestamp()
                    });
                    var decrypted = decryptResponse(apiResp);
                    if (decrypted && decrypted.list) {
                        for (var i = 0; i < decrypted.list.length; i++) {
                            if (String(decrypted.list[i].id) === String(decoded.id) ||
                                decrypted.list[i].title === decoded.title) {
                                realUrl = decrypted.list[i].quarkLink || decrypted.list[i].url || '';
                                break;
                            }
                        }
                    }
                } catch (e) {
                    print('>>> tvso detailContent search ERROR: ' + e);
                }
            }

            var panName = inferPanName(realUrl);

            if (realUrl) {
                result.list.push({
                    vod_id: id,
                    vod_name: decoded.title || '网盘资源',
                    vod_pic: '',
                    vod_remarks: '☁️' + panName,
                    vod_play_from: 'TVSO',
                    vod_play_url: JSON.stringify([{ url: realUrl, name: panName }])
                });
                print('>>> tvso detailContent SUCCESS: ' + realUrl.substring(0, 60));
            } else {
                result.list.push({
                    vod_id: id,
                    vod_name: decoded.title || '网盘资源',
                    vod_pic: '',
                    vod_remarks: '☁️网盘',
                    vod_play_from: 'TVSO',
                    vod_play_url: JSON.stringify([{ url: '', name: '未获取到链接' }])
                });
                print('>>> tvso detailContent: no URL found for id=' + decoded.id);
            }

            return result;
        }

        // ===================== 播放内容 =====================

        function playerContent(vodId, flag, url) {
            print('>>> tvso playerContent: vodId=' + vodId.substring(0, 40));

            if (url && url.indexOf('http') === 0) {
                return {
                    parse: 0,
                    url: url,
                    header: { 'User-Agent': UA }
                };
            }

            var decoded = decodeVodId(vodId);
            if (decoded.url && decoded.url.indexOf('http') === 0) {
                return {
                    parse: 0,
                    url: decoded.url,
                    header: { 'User-Agent': UA }
                };
            }

            return { parse: 0, url: '' };
        }

        // ===================== 初始化 =====================

        function init(config) {
            print('>>> tvso init: TVSO JS蜘蛛 v1.1');
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
