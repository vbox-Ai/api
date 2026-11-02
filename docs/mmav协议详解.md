# mmav（猫咪AV）协议详解

> 2026-11-02 全链路打通：分类 / 列表 / 详情 / 封面 / 播放 m3u8

## 一、结论速览

| 环节 | 状态 | 关键点 |
|---|---|---|
| 分类 | ✅ | `data/category/base-1.js` |
| 列表 | ✅ | `data/mediaVideo/list-{cid}-{page}-50.js` |
| 详情 | ✅ | 列表项自带全部字段，无需二次请求 |
| 封面 | ✅ | `image_domain` + cover 相对路径 |
| 播放 | ✅ | m3u8 + wsSecret 签名，200 application/vnd.apple.mpegurl |

**这是第一个做到「分类+列表+详情+播放」全通的非 hdb 平台。**

## 二、加密（AES-256-CBC + 动态 IV）

数据来源：`avbox/module/mmav/network/interceptor.dart`

```
key = "IdTJq0HklpuI6mu8iB%OO@!vd^4K&uXW"     # 32 字符 → AES-256
iv  = "$0v@krH7V2" + response["suffix"]       # 固定常量在前，动态 suffix 在后
plain = AES-CBC-decrypt(key, iv, base64decode(response["data"]))
      → jsonDecode
```

响应外层结构：

```json
{"code":0, "time":"2026-11-02 01:28:57", "msg":"操作成功",
 "data":"<base64 密文>", "suffix":"189751"}
```

### 踩坑记录

1. **IV 顺序**：`$0v@krH7V2` 在前、`suffix` 在后。反过来也能解出「看起来像明文」的乱码
   （首块会变成 `m!5Ui4...`），极易误判为成功。
2. **key 是 32 字符**，不是 16。当 AES-256 用，不是 AES-128。
3. **`suffix` 是 6 位十六进制**，拼上 10 字符常量正好 16 字节。

## 三、接口清单

```
配置  GET /data/config/base-1.js
分类  GET /data/category/base-1.js
列表  GET /data/mediaVideo/list-{cid}-{page}-50.js
```

### 分页语义（实测纠正）

模板中间数字是**页码**，不是偏移量：

| 请求 | current_page | 首条 id |
|---|---|---|
| `list-7-1-50.js` | 1 | 54433 |
| `list-7-2-50.js` | 2 | 50526 |
| `list-7-3-50.js` | 3 | 47571 |
| `list-7-51-50.js` | **51** | 1961（几乎到底） |
| `list-7-101-50.js` | 101 | 空 |

误按偏移量传（`(page-1)*50+1`）会导致第 2 页直接跳到第 51 页并返回空列表。

## 四、播放鉴权（wsSecret）

数据来源：`avbox/util/url_util.dart::mmAvVideo` + `avbox/util/str_util.dart::wsSecret`

```
mmAvVideo(path) = wsSecret(SALT, host + path)
SALT = "D7hGKHnWThaECaQ3ji4XyAF3MfYKJ53M"

wsSecret(salt, url):
    expire = now_seconds + 7200
    secret = md5( salt + uri.path + expire )        # hex 小写
    return url + "?wsSecret=" + secret + "&wsTime=" + expire + "&ip=" + ip
```

### 踩坑记录

1. **哈希输入是 `salt + uri.path + expire`**，不是 `url + salt + expire`。
   我第一版把 url 整个塞进去，全部 403。
2. **`uri.path` 要取解析后的 path**，不含 scheme/host，但含开头的 `/`。
3. **`ip` 参数可以是 `0.0.0.0`**，服务端不校验实际来源 IP。
4. **域名必须是 `m3u8_host_encrypt`**（`cf-worker-r2.mtzionhub.com`）。
   用 `image_domain` 或主站域名拼 m3u8 一律 403——它们只服务图片。

## 五、域名分工（config 解密所得，实测验证）

| 用途 | 域名 | 实测 |
|---|---|---|
| 数据/配置 | `bvbvbvssu.a63qv1sy.com` | 200（无需代理） |
| 封面 | `wzzqlm.erbaiwulaoge.com` | 200 image/jpeg |
| 封面备用 | `m3m.1vkx.cn` | 200 image/jpeg |
| 播放 m3u8 | `cf-worker-r2.mtzionhub.com` | 200 application/vnd.apple.mpegurl |
| 封面（失效） | `catsta.tingqian.top` | 000 不可达 |
| API 网关 | `mapsjbogs.hongtaitanghua.com/api` | 406（需要特殊头，未使用） |

> `catsta.tingqian.top` 是 config 里的 `img_host`，已彻底不可达。
> 所以封面域名必须优先用 `image_domain`，不能用 `img_host`。

## 六、数据结构

分类树（`menus`）10 个一级菜单，每个 8 个子分类：

```
1 热销专题    channel=topic        子项带 topic_id
2 限时专题    channel=topic
3 热门专区    channel=vip
4 热门专区2   channel=media_video  ← 当前列表接口服务的就是这一类
5 精品推荐    channel=remen
6 官方推荐    channel=remen2
7 另类色情    channel=remen3
8 在线电影    channel=shipin
...
```

列表项关键字段：

```json
{
 "id": 54433,
 "title": "...",
 "cover": "/common/cover_img/cover-mv-54433-....jpg",
 "video_url": "/common/msdl//xxx/hls/1/index.m3u8",
 "category_id": 7,
 "tags": ["国产", "妹妹", ...],
 "duration_seconds": 3402,
 "resolution": "1280x720",
 "published_at": "2026-10-10 08:19:54"
}
```

`video_url` 是**相对路径**，且路径里有双斜杠 `msdl//`，这是服务端原样，不要去重。

## 七、m3u8 结构

```
#EXTM3U
#EXT-X-VERSION:3
#EXT-X-TARGETDURATION:2
#EXT-X-PLAYLIST-TYPE:VOD
#EXT-X-KEY:METHOD=AES-128,URI=".../enc.key?wsSecret=...&wsTime=...",IV=0x00...
#EXTINF:2.002000,
https://.../index0.ts?wsSecret=...&wsTime=...
```

- 3411 行，约 305 KB
- 分片自身**已带签名**，播放器跟随播放即可，无需二次签名
- 分片是 AES-128 加密的 TS，key 也在同一个 CDN 上

## 八、遗留

1. `data/list/base-{slug}-{page}-50.js` 是另一种列表（按 tag 过滤），
   返回 `cat_list: []`，暂未使用。
2. 专题频道（`channel=topic`）走网页 `/page/topic/{id}`，未接入。
3. `channel=vip / remen / shipin` 走 HTML 页面，未接入。
   当前只接了 `media_video` 频道（数据最全、结构最规整）。

## 九、可复用脚本

| 脚本 | 用途 |
|---|---|
| `tools/_mmav_dec.py` | 解密核心（fetch + AES-256 解密） |
| `tools/_mmav_ws2.py` | wsSecret 签名验证（正确算法） |
| `tools/_mmav_page.py` | 分页语义验证 |
| `tools/_mmav_play.py` | 播放域名对比 |
| `tools/_smoke_mmav2.py` | 端到端验证 |
