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
| `v1/menu/*` | **POST** | GET 返回 405（Supported: OPTIONS/POST） |
| `v1/user/info` | POST | 405 on GET，支持 POST |
| `v2/vertical/list/{id}` | 待定 | GET 405 |
| `v2/search/*` | 待定 | GET 405 |

## 五、下一步（收尾清单）

1. 用 **POST** 重试 `v1/menu/*`、`v2/vertical/list/{id}`、`v2/search/…`，把列表/搜索/详情路径定下来；
2. 详情页字段（actor/maker/tags/播放地址）→ `v1/actor/{id}`、`v2/vertical/*`；
3. 播放地址形态确认（m3u8 直链 or 需再取流）；
4. 落地 `sources/welfare-js/fl2.py`（homeContent 静态分类，避免 20s 预算坑）并注册。

## 六、脚本

| 文件 | 用途 |
|---|---|
| `tools/_fl2_r1.py` | 信封首版（path 带斜杠 → decrypt failure，留作反例） |
| `tools/_fl2_r2.py` | 四维变体扫描，定出「path 不带斜杠」 |
| `tools/_fl2_r3.py` / `_r4.py` | register/token + 响应解密（X-VTag 派生 IV） |
| `tools/_fl2_r5.py` | 带 token 的业务接口枚举 |
