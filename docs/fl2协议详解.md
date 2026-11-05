# fulao2（fl2）协议详解 —— 信封与令牌已通（业务接口部分完成）

> 更新时间：2026-11-04 10:50（北京时间）
> 状态：**请求信封 / 响应解密 / register-token 全通**；`v2/menu/type`、`v1/actors` 已出数据；
> 列表/搜索接口的 HTTP 方法与子路径待补（下一步）
> 逆向来源：`module/fl2/network/interceptor.dart`（`onRequest` @0x8d76e8 / `onResponse` @0x8f0d6c）

---

## 一、请求信封（onRequest）

```
KEY  = base64Decode("euZN1Gg3JIwWOEWhmE7C4l5dSSRU34fyuPMXjtuoqVs=")     # 32B → AES-256
IV   = 16 字节安全随机（_randomIv 用 SecureRandom 逐字节取）

map  = 业务参数
     + timestamp = 秒
     + path      = 请求路径，**不带前导斜杠**（如 "v2/menu/type"）
     [+ register/token 专属字段，见下]

payload = base64(IV) + "." + base64( AES-256-CBC(jsonEncode(map), KEY, IV) )
GET  → ?payload=<payload>
POST → Content-Type: application/x-www-form-urlencoded；body=payload=<payload>

头（缺一不可）
  User-Agent: "Fulao2/Android 2.40; " + <manufacturer> + " " + <model>
  X-Info:     eyJjcGFnZSI6ImxhdW5jaCIsInBsYXRmb3JtIjoyLCJwcGFnZSI6IiIsInZlcnNpb24iOiIyLjQwIn0=
              （base64 的 {"cpage":"launch","platform":2,"ppage":"","version":"2.40"}）
  Uuid:       SpUtil "Uuid"（设备 id，注册时就是 device_id）
  Authorization: Bearer <token>     ← register/token 换来的
```

**关键坑**：`map["path"]` 必须**不带前导斜杠**。
带斜杠时服务端返回 `{"status":{"code":495,"message":"decrypt failure"}}` ——
这会把排查引向"密钥不对"，实际上密钥和结构都是对的。

## 二、响应解密（onResponse）

```
vtag  = resp.headers["X-VTag"]                 ← 数字串，服务端每次返回
h     = MD5(vtag)                               # 32 位十六进制
Key   = utf8("db6f7f9e5d7a770e0e3497a7d7a077f5")  # 32B ASCII → AES-256
IV    = utf8( h[8:24] )                         # 16 位十六进制字符 = 16 字节
plain = AES-256-CBC-decrypt64(body) → jsonDecode
```

> asm 里 `movz #0x30` + `substring(8, 0x30)` 的 `0x30` 是 **Smi 编码**，真实值 24；
> 与"Dart 的 substring 在 32 字符串上给 48 会抛"互证。

## 三、register/token（注册即拿令牌，无需账号）

```
POST /v1/register/token
map 附加：
  device_id    = <Uuid>（任意 uuid4 均可）
  key          = sha256("jav" + device_id + "jav")     # _hashKey
  utm_medium   = ""
  model        = "<manufacturer> <model>"
  universal_id = base64(device_id)                      # _universalId
  platform     = "Android"

响应（解密后）：
  {"status":{"code":200,"message":"success"},
   "response":{"token":"…","refresh":"…","expired":7200}}
```

`expired=7200`（2 小时）。过期可用 `v1/refresh/token` 或重新注册。

## 四、已验证的业务接口

| 接口 | 方法 | 返回 |
|---|---|---|
| `v2/menu/type` | GET | `pixeled`：推荐(1) / 最新(4) / 抢先看(16) … |
| `v1/actors` | GET | `total_results=15968`，actor_id / actor_name / actor_url |
| `v1/menu/{id}/layout` | GET | ✅ 返回 35 个区块，每块 `data[]` 是视频（video_id/title/thumb/cover），也有 banner 块 |
| `v1/video/info/{id}` | GET | ✅ 详情：`video_urls{240,480,intro}`（带 expire/hash 的 m3u8 相对路径）、cover_url、actor[]、tags、duration |
| `v1/actor/{id}` | GET | ✅ 演员页 + 其视频列表（24 条/页） |
| `v2/search/*`、`v1/search/*` | ? | 全部 405（Supported: OPTIONS）→ 搜索路径仍未找到 |
| `v1/menu/{id}`（无 /layout） | — | 405，说明 menu 只暴露 `/layout` |

## 四·补、播放（未通，差一步）

`v1/video/info/{id}` 给的 `video_urls` 是**相对路径 + 签名**：

```
"480": "/media/480/524937.m3u8?expire=1793893925&hash=1b700846…"
```

直取（无论带不带 Bearer、带不带信封）都返回同一句：
`{"status":{"code":498,"message":"Token 格式錯誤"}}` —— 说明 **媒体路径要的"token"不是 Bearer**，
而是另一个字段（很可能是 query 里的 `token`，或 payload 内的 token 字段），下一轮专门解这个。

> 注意：媒体响应也被同一套 X-VTag 加密包着（裸取回来是 base64 密文），
> 所以就算拿到 URL，客户端的播放器也读不了 —— 最终大概率要走 `localProxy`
> 做「取流→解密→回吐 m3u8/分片」的转发。这是 fl2 最后的工作量所在。

## 五、下一步（收尾清单）

1. **媒体 token**：写清 `/media/**.m3u8` 需要的 token 从哪来（query 参数名？payload 内字段？），
   以及分片 `.ts` 是否同样加密/需要同样的 token；
2. 若分片也加密 → 用 `localProxy` 实现「m3u8 重写 + 分片解密转发」，播放器才能吃；
3. 搜索路径待定（`v2/search/*` 全 405）；
4. 以上都通后落地 `sources/welfare-js/fl2.py`（homeContent 静态分类避开 20s 预算坑）并注册。

**当前不注册**：分类/列表/详情虽已通，但播放未通，按"不留半残平台"的口径先挂起。

## 六、脚本

| 文件 | 用途 |
|---|---|
| `tools/_fl2_r1.py` | 信封首版（path 带斜杠 → decrypt failure，留作反例） |
| `tools/_fl2_r2.py` | 四维变体扫描，定出「path 不带斜杠」 |
| `tools/_fl2_r3.py` / `_r4.py` | register/token + 响应解密（X-VTag 派生 IV） |
| `tools/_fl2_r5.py` | 带 token 的业务接口枚举 |
