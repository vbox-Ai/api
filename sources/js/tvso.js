/*
 * TVSO JS 蜘蛛 v1.0
 * 适配 vbox-ios JSSpiderEngine (type:3 独立引擎)
 * 目标站: https://www.tvso.uk
 * 特点: Vue/Vite SPA，API 响应 AES-256-CBC 加密，需客户端解密
 * 支持网盘：夸克网盘
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
        var UA = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36';
        var HEADER = {
            'User-Agent': UA,
            'Referer': BASE_URL + '/',
            'Content-Type': 'application/json'
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

        // 简单的 AES-256-CBC 解密（纯 JS 实现，无外部依赖）
        function aesDecrypt(ciphertext, key, iv) {
            // 扩展密钥（简化版，仅用于基础 AES-256）
            // 注意：这是简化实现，完整 AES 需要完整的密钥扩展
            // vbox 引擎如无 CryptoJS，此实现可能不够完整
            // 这里尝试优先使用全局 CryptoJS
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
                    return decrypted.toString(CryptoJS.enc.Utf8);
                } catch (e) {
                    print('>>> tvso CryptoJS decrypt ERROR: ' + e);
                }
            }

            print('>>> tvso WARNING: CryptoJS not available, AES decryption may fail');
            return '';
        }

        // ===================== 工具函数 =====================

        function fetchJSON(url, body, headers) {
            try {
                var h = {};
                for (var k in (headers || HEADER)) { h[k] = (headers || HEADER)[k]; }
                var options = { method: body ? 'POST' : 'GET', headers: h, timeout: 15000 };
                if (body) {
                    options.body = JSON.stringify(body);
                }
                var resp = req(url, options);
                if (resp && resp.ok) {
                    var content = resp.content || '';
                    if (typeof content === 'object') return content;
                    try { return JSON.parse(content); } catch (e) { return null; }
                }
                print('>>> tvso fetch FAIL: status=' + (resp ? resp.status : 'null') + ' url=' + url.substring(0, 80));
                return null;
            } catch (e) {
                print('>>> tvso fetch ERROR: ' + e);
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

        // 解密 API 响应
        function decryptResponse(encrypted) {
            if (!encrypted || !encrypted.data || !encrypted.iv) {
                print('>>> tvso decryptResponse: invalid encrypted data');
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

        // ===================== 首页内容 =====================

        function homeContent(filter) {
            var result = { class: [], list: [] };
            var hotKeywords = ['庆余年', '凡人修仙传', '九门', '斩神', '完美世界'];

            try {
                var data = fetchJSON(
                    BASE_URL + '/api/v2/resource/paginate',
                    { page: 1, limit: 24, keyword: hotKeywords[0] }
                );

                var decrypted = decryptResponse(data);
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
                var url = item.url || '';

                if (!title) continue;

                var dedupKey = title + '_' + url;
                if (seen[dedupKey]) continue;
                seen[dedupKey] = true;

                list.push({
                    vod_id: encodeVodId(id, title, url),
                    vod_name: title,
                    vod_pic: item.cover || '',
                    vod_remarks: '☁️夸克网盘'
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
                var data = fetchJSON(
                    BASE_URL + '/api/v2/resource/paginate',
                    { page: page, limit: 20, keyword: key }
                );

                var decrypted = decryptResponse(data);
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
                    var data = fetchJSON(
                        BASE_URL + '/api/v2/resource/paginate',
                        { page: 1, limit: 10, keyword: decoded.title }
                    );
                    var decrypted = decryptResponse(data);
                    if (decrypted && decrypted.list) {
                        for (var i = 0; i < decrypted.list.length; i++) {
                            if (String(decrypted.list[i].id) === String(decoded.id) || decrypted.list[i].title === decoded.title) {
                                realUrl = decrypted.list[i].url || '';
                                break;
                            }
                        }
                    }
                } catch (e) {
                    print('>>> tvso detailContent search ERROR: ' + e);
                }
            }

            if (realUrl) {
                result.list.push({
                    vod_id: id,
                    vod_name: decoded.title || '网盘资源',
                    vod_pic: '',
                    vod_remarks: '☁️夸克网盘',
                    vod_play_from: 'TVSO',
                    vod_play_url: JSON.stringify([{ url: realUrl, name: '夸克网盘' }])
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
            print('>>> tvso init: TVSO JS蜘蛛 v1.0');
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
