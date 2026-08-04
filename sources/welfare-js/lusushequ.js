/**
 * 六速社区 JavaScript Spider
 * 适配 vbox iOS 端 JSSpiderEngine 引擎
 *
 * 功能：
 * 1. 首页分类 + 推荐视频
 * 2. 分类视频列表（分页）
 * 3. 视频详情 + 播放线路
 * 4. 搜索
 * 5. 播放地址（cdnId=3 统一替换，消除 Brotli 压缩问题）
 *
 * 数据加密：base64(URL-safe) → XOR(key)
 * 封面加密：AES-256-CBC（由客户端 EncImageURLProtocol 自动解密）
 * SSL 绕过：由客户端 JSHTTPBridge.sslBypass 处理
 * m3u8 代理：由客户端 DoubanImageProxyServer 处理（Brotli 解压 + key/TS 重写）
 */

var API_HOST = "https://215.x89cneo.com:51111";

var HEADER = {
    'User-Agent': 'Mozilla/5.0 (Linux; Android 13) AppleWebKit/537.36',
    'Referer': 'https://3.3xlg40o.com/',
    'Accept': '*/*',
    'Accept-Language': 'zh-CN,zh;q=0.9',
};

var CATEGORIES = [
    {"type_id": "label_266", "type_name": "传媒"},
    {"type_id": "label_262", "type_name": "国产"},
    {"type_id": "label_263", "type_name": "日本AV"},
    {"type_id": "label_264", "type_name": "欧美"},
    {"type_id": "label_267", "type_name": "动漫"},
    {"type_id": "label_341", "type_name": "三级"},
    {"type_id": "label_342", "type_name": "AI换脸"},
    {"type_id": "label_343", "type_name": "AV无码"},
    {"type_id": "cate_130", "type_name": "黑料"},
    {"type_id": "cate_143", "type_name": "探花"},
    {"type_id": "cate_127", "type_name": "SM"},
    {"type_id": "cate_144", "type_name": "乱伦"},
    {"type_id": "cate_178", "type_name": "颜值"},
    {"type_id": "cate_153", "type_name": "人妻少妇"},
    {"type_id": "cate_133", "type_name": "自拍"},
    {"type_id": "cate_146", "type_name": "中文字幕"},
    {"type_id": "cate_246", "type_name": "多男一女"},
    {"type_id": "cate_247", "type_name": "多女一男"},
    {"type_id": "cate_142", "type_name": "主播大秀"},
];

// ========== 工具方法 ==========

/**
 * API 请求 + 解密
 * @param {string} path - API 路径
 * @param {object} params - 查询参数
 * @returns {object|null} 解密后的 JSON 对象
 */
function apiCall(path, params) {
    var url = API_HOST + path;
    if (params) {
        var qs = [];
        for (var k in params) {
            if (params[k] !== null && params[k] !== undefined) {
                qs.push(k + '=' + params[k]);
            }
        }
        if (qs.length > 0) url += '?' + qs.join('&');
    }

    var resp = http(url, {
        method: 'GET',
        headers: HEADER,
        timeout: 15000,
    });

    if (!resp || !resp.ok || !resp.content) {
        return null;
    }

    try {
        var json = JSON.parse(resp.content);
        if (json.code !== 200 || !json.data || !json.key) {
            return null;
        }
        return decryptData(json.data, json.key);
    } catch (e) {
        return null;
    }
}

/**
 * 解密 API 响应数据
 * 流程：URL-safe base64 → XOR(key) → JSON
 * @param {string} encData - 加密数据
 * @param {string} key - 解密密钥
 * @returns {object|null} 解密后的 JSON 对象
 */
function decryptData(encData, key) {
    try {
        // URL-safe base64 → 标准 base64
        var s = encData.replace(/[\r\n\s]/g, '').replace(/-/g, '+').replace(/_/g, '/');
        var pad = (4 - s.length % 4) % 4;
        s += new Array(pad + 1).join('=');

        // Base64 解码为二进制字符串
        var raw = atob(s);

        // XOR 解密
        var result = '';
        for (var i = 0; i < raw.length; i++) {
            result += String.fromCharCode(
                raw.charCodeAt(i) ^ key.charCodeAt(i % key.length)
            );
        }

        return JSON.parse(result);
    } catch (e) {
        return null;
    }
}

/**
 * 构建视频条目
 * @param {object} item - API 返回的视频对象
 * @returns {object} 标准 vod 对象
 */
function buildVod(item) {
    var vid = String(item.id || '');
    if (!vid) return null;

    var pic = item.upload_thumb || item.thumb || '';
    // .enc 封面由客户端 EncImageURLProtocol 自动解密，直接返回原始 URL

    return {
        vod_id: vid,
        vod_name: item.title || '',
        vod_pic: pic,
        vod_remarks: item.label || '',
    };
}

/**
 * 安全解析整数
 */
function parseIntSafe(v) {
    if (typeof v === 'number') return v;
    if (typeof v === 'string') return parseInt(v) || 0;
    return 0;
}

// ========== Spider 接口 ==========

var spider = {
    /**
     * 初始化
     * @param {object} config - 平台配置
     * @returns {boolean} 是否成功
     */
    init: function(config) {
        try {
            if (config && config.hosts && config.hosts.length > 0) {
                API_HOST = config.hosts[0];
            }
        } catch (e) {}
        return true;
    },

    /**
     * 首页分类
     * @returns {object} { class: [...] }
     */
    homeContent: function(filter) {
        return { class: CATEGORIES };
    },

    /**
     * 首页推荐视频
     * @returns {object} { list: [...] }
     */
    homeVideoContent: function() {
        var data = apiCall('/api/old_v3/video/home');
        if (!data || !Array.isArray(data)) {
            return { list: [] };
        }

        var videos = [];
        var seen = {};
        for (var i = 0; i < data.length; i++) {
            var section = data[i];
            if (!section.list) continue;
            for (var j = 0; j < section.list.length; j++) {
                var vod = buildVod(section.list[j]);
                if (vod && !seen[vod.vod_id]) {
                    seen[vod.vod_id] = true;
                    videos.push(vod);
                }
            }
        }
        return { list: videos.slice(0, 72) };
    },

    /**
     * 分类视频列表
     * @param {string} tid - 分类ID（格式：type_id，如 "label_266"）
     * @param {number} pg - 页码
     * @returns {object} { list, page, pagecount, limit }
     */
    categoryContent: function(tid, pg, filter, extend) {
        var page = parseIntSafe(pg) || 1;

        var parts = tid.split('_');
        if (parts.length !== 2) {
            return { list: [], page: page, pagecount: 1, limit: 20 };
        }
        var ctype = parts[0];
        var cid = parts[1];

        var data = apiCall('/api/old_v3/video/getList', {
            type: ctype,
            id: cid,
            page: page,
            page_size: 20,
        });

        if (!data) {
            return { list: [], page: page, pagecount: 1, limit: 20 };
        }

        var list = (data.list || []).map(buildVod).filter(function(v) { return v !== null; });
        var total = parseIntSafe(data.total) || (list.length * 10);
        var pagecount = Math.max(1, Math.ceil((total + 19) / 20));

        return {
            list: list,
            page: page,
            pagecount: pagecount,
            limit: 20,
            total: total,
        };
    },

    /**
     * 视频详情
     * @param {string} ids - 视频ID
     * @returns {object} { list: [{ vod_id, vod_name, vod_pic, vod_content, vod_play_from, vod_play_url }] }
     */
    detailContent: function(ids) {
        var vodId = typeof ids === 'string' ? ids : (ids[0] || '');

        var data = apiCall('/api/v3/home/public/video/long/detail', { id: vodId });
        if (!data) {
            return { list: [] };
        }

        // API 返回结构可能是 {data: {...}} 或直接是字典/数组
        var item = null;
        if (data.data && typeof data.data === 'object') {
            item = data.data;
        } else if (Array.isArray(data) && data.length > 0) {
            item = data[0];
        } else if (typeof data === 'object' && data.id) {
            item = data;
        }

        if (!item || !item.id) {
            return { list: [] };
        }

        var pic = item.upload_thumb || item.thumb || '';
        var desc = (item.desc || item.classify || '').substring(0, 500);

        // 构建播放线路
        var playHls = item.play_hls_url || '';
        var cdnList = item.cdn_list || [];

        var playFrom = [];
        var playUrlParts = [];

        if (playHls) {
            // 默认线路：统一替换 cdnId=3（从不返回 Brotli 压缩，最稳定）
            var stableUrl = playHls.replace(/cdnId=\d+/, 'cdnId=3');
            playFrom.push('默认线路');
            playUrlParts.push('播放$' + stableUrl);

            // 其他 CDN 线路：同样替换为 cdnId=3
            for (var i = 1; i < cdnList.length; i++) {
                var cdn = cdnList[i];
                var cdnTitle = cdn.title || ('线路' + cdn.id);
                var cdnHls = stableUrl; // 内容完全相同，直接用 cdnId=3
                playFrom.push(cdnTitle);
                playUrlParts.push('播放$' + cdnHls);
            }
        }

        // play_hls 为空时用 href 兜底
        if (!playHls) {
            var href = item.href || '';
            if (href && href.indexOf('http') !== 0) {
                href = 'https://kbu.xn--xhq15jk0k96h.cn/encryption-ts' + href;
            }
            if (href) {
                playFrom.push('默认线路');
                playUrlParts.push('播放$' + href);
            }
        }

        var vod = {
            vod_id: String(item.id || vodId),
            vod_name: item.title || '未知影片',
            vod_pic: pic,
            type_name: item.label || '',
            vod_year: item.years || '',
            vod_area: item.region || '',
            vod_remarks: item.classify || '',
            vod_actor: item.actor || '',
            vod_director: '',
            vod_content: desc,
            vod_play_from: playFrom.join('$$$'),
            vod_play_url: playUrlParts.join('$$$'),
        };

        return { list: [vod] };
    },

    /**
     * 搜索
     * @param {string} key - 搜索关键词
     * @param {number} pg - 页码
     * @returns {object} { list, page, pagecount, limit }
     */
    searchContent: function(key, quick, pg) {
        var page = parseIntSafe(pg) || 1;

        var data = apiCall('/api/old_v3/video/search', {
            keywords: key,
            page: page,
            page_size: 20,
        });

        if (!data) {
            return { list: [], page: page, pagecount: 1, limit: 20 };
        }

        var list = (data.list || []).map(buildVod).filter(function(v) { return v !== null; });
        var total = parseIntSafe(data.total) || 0;
        var pagecount = Math.max(1, Math.ceil((total + 19) / 20));

        return {
            list: list,
            page: page,
            pagecount: pagecount,
            limit: 20,
            total: total,
        };
    },

    /**
     * 获取播放地址
     * @param {string} flag - 线路名称
     * @param {string} id - 播放地址（m3u8 URL）
     * @returns {object} { parse, url, header }
     */
    playerContent: function(flag, id, vipFlags) {
        var url = id || '';

        // 统一替换 cdnId=3
        if (url.indexOf('cdnId=') !== -1) {
            url = url.replace(/cdnId=\d+/, 'cdnId=3');
        }

        return {
            parse: 0,
            playUrl: '',
            url: url,
            header: {
                'User-Agent': HEADER['User-Agent'],
                'Referer': 'https://3.3xlg40o.com/',
            },
        };
    },

    is_cat: true,
};
