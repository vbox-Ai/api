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
    {"type_id":