# kpsp 看片视频 · 攻坚报告

> 完成时间：2026-11-02 23:30（北京时间）
> 结论：**全链路打通** —— 分类 / 列表 / 详情 / 搜索 / 播放 全部出真实数据
> 适配器：`sources/welfare-js/kpsp.py`（自包含）
> 注册键：`kpsp_py`，`sortOrder=641`

---

## 一、为什么选它

对 24 个未攻平台做了一次 interceptor 扫描，按「是否含摘要签名 / 签名相关常量数」排序。kpsp 得分最低档：

- interceptor 里**没有任何签名逻辑**，只有一个 `onResponse`（响应解密）
- 有专属媒体域名 `kpsp_media` = `https://hm-img.hdstfb.com`
- 属于视频类，客户价值高

实测确认：**请求侧零鉴权**，无需 token、无需签名头。

---

## 二、响应加密（唯一需要破的部分）

### 现象

```
GET https://sm-api.wieuc.com/api/vod/video?page=1&per_page=20&site_id=1
→ 200  application/json
→ {"x-data":"gAAAAABq6KqIYVCaQb6J_PbO2IczFccGGBf_JeiaeAwAmSUA..."}
```

注意两个反直觉点：

1. **`x-data` 在响应体 JSON 里**，不在响应头（名字像头，实为 body 字段）
2. 密文以 `gAAAAA` 开头 —— 这是 **Fernet** 的特征前缀

### 算法还原

`CryptoUtil::ksSpDecrypt` @ `0x8f2484`，配套 `_decode64ToHex` @ `0x8df848`：

```dart
// _decode64ToHex
String s = x.replaceAll("-", "+").replaceAll("_", "/");   // URL-safe 还原
if (s.length % 4 != 0) s += "=" * (4 - s.length % 4);
String hex = base64Decode(s).map((b) => b.toRadixString(16).padLeft(2,"0")).join();

// ksSpDecrypt
int a = 2 + 16;        // 18
int b = a + 32;        // 50
String iv  = hex.substring(18, 50);                 // 32 hex = 16 字节
String ct  = hex.substring(50, hex.length - 64);    // 去掉尾部 32 字节
AES-128-CBC(key = decodeHex("7af630c7e06ccecfa70d5a085f189c06"))
```

对上 Fernet 结构后，每个切片都有了解释：

| hex 区间 | 字节 | 含义 |
|---|---|---|
| `[0:18]` | 9 | `version(1B) + timestamp(8B)` — 丢弃 |
| `[18:50]` | 16 | **IV** |
| `[50:len-64]` | N | **ciphertext** |
| `[len-64:]` | 32 | HMAC-SHA256 — 客户端**跳过校验** |

AES 模式判定：该 `AESMode` 实例（`Obj!AESMode@a81bc1`）与 4hu 已确认的 CBC 用法是同一个，且带 IV，故为 **CBC**。

### 验证

```
解密成功 14396 字节
明文：{"data":{"items":[{"id":242253,"name":"酒店偷拍一对年轻情侣体力就是好",...
```

### 图片解密 `ksSpDecryptImg` @ `0xa42164`

同一套算法，额外两步：`split("@@@")[0]` 取密文，解密后按 `,` 切分取 `[1]`。
不过实测 `/source3/**.image` **可直接取**（200，`application/x-image`），无需解密，故适配器直接用直链。

---

## 三、接口全表（实测）

| 用途 | 路径 | 参数 | 实测 |
|---|---|---|---|
| 列表 | `api/vod/video` | `page` `per_page` `site_id` `tag` | ✅ total 115048 |
| 详情 | `api/vod/video/{id}` | — | ✅ 全字段 |
| 标签 | `api/vod/tag` | `page` `per_page` | ✅ 全站 **6628** 个 |
| 搜索 | `search/vod` | `search` `page` `per_page` `site_id` | ✅ |

- `per_page` 上限 **100**（200 会报错）
- `site_id` 1–6 结果完全一致，无实质区别
- 认证头：无。只需普通 UA

### 坑：tag 过滤必须传 id

传中文名会被**静默忽略**，返回全站基线：

```
tag=偷拍        → total 115048（= 基线，无效）
tag=407         → total 1623   ✓
tag=3594        → total 33
tag=479         → total 39
tag=300         → total 34477
tag=1211        → total 18346
tag=107         → total 85513
```

因此适配器内置了 name→id 映射（通过全量拉取 6628 个标签建索引获得）。

---

## 四、资源域名

`MEDIA = https://hm-img.hdstfb.com`（splash 下发的 `kpsp_media`）

```
封面   MEDIA + pic                 → /source3/.../source_jpg.image    200 application/x-image
播放   MEDIA + play_url            → /videos3/.../index.m3u8          200 application/vnd.apple.mpegurl
下载   MEDIA + down_url            → /videos3/.../index.mp4
预览   MEDIA + preview_play_url    → /videos3/.../preview.m3u8
```

### 播放链路实测

```
m3u8: 2873 个分片
      #EXT-X-KEY:METHOD=AES-128,URI="enc.key",IV=0x00000000000000000000000000000000
GET  …/enc.key  → 200  16 字节  "8bd7a481be884450"（ASCII）
GET  …/abc000.png → 200  172592 字节（实为 AES-128 加密的 .ts 分片）
```

- key 相对路径解析在同目录，**匿名可取**
- 标准 HLS + AES-128，播放器直接吃
- 分片命名伪装成 `.png`，实际是加密 TS

---

## 五、数据结构

```json
{"code":0,"data":{"items":[…],"page":1,"per_page":20,"total":115048,"pages":5753}}
```

item 字段：

```
id  name  product_type  is_paid  is_hongguo  price  pubdate
hits  likes_count  score  level  year  duration
pic  pic_thumb  preview_url
play_url  preview_play_url  down_url
tag [{id,name,is_ad,target,sort,ad_type}]
description  created  updated  update_day
```

详情比对列表多出：`status remarks drama_pay_mode drama_free_episodes drama_bundle_discount hits_day/week/month scored_by source draft created_user_name site[]`

**`duration` 单位是秒**（5750s ≈ 1:35:50，与 2873 分片 × 2.002s 吻合）。

---

## 六、适配器设计

| 方法 | 实现 |
|---|---|
| `homeContent` | 24 个固定分类（含 id 映射）+ 动态补充 `api/vod/tag` 前 60 个，上限 90 |
| `categoryContent` | `api/vod/video`；`all` 不带 tag；`extend.tag` 可覆盖 |
| `detailContent` | `api/vod/video/{id}`；`play_url`/`preview_play_url`/`down_url` 多档；duration 秒→`1:35:50` |
| `searchContent` | `search/vod?search=` |
| `playerContent` | `parse:0` + 绝对化 m3u8 + UA/Referer |
| `localProxy` | 媒体直取兜底 |

AES 后端三档降级（与 `muse_avbox._aes_cbc` 同策略，保证自包含）：

```
Crypto (pycryptodome) → cryptography → pyaes（vbox 运行时内置）
```

---

## 七、实测结果

`tools/_smoke_kpsp.py` → **PASS 12 / 12**

```
[OK] homeContent                 24+ 分类
[OK] category all/2194/407/300   全部出数据
[OK] pagination                  pg1 与 pg2 首条不同
[OK] tag isolation               tag=407 total 1623 ≠ 基线 115048
[OK] detail 242253               含 play_url
[OK] search "偷拍"                命中
[OK] playerContent               parse=0，m3u8
[OK] HLS+AES key                 2873 分片，key 16 字节
[OK] cover fetch                 封面可取
```

---

## 八、踩坑清单

| # | 坑 | 现象 | 正解 |
|---|---|---|---|
| 1 | `x-data` 当响应头找 | 头部没有该字段，以为接口未加密 | 它在**响应体 JSON** 里 |
| 2 | 密文当普通 base64+AES 解 | 直接解出乱码 | 是 **Fernet 结构**，要跳过 9 字节头、去掉 32 字节 HMAC |
| 3 | tag 传中文名 | 结果与基线一模一样，以为 tag 无效 | 必须传 **tag id**，中文名被静默忽略 |
| 4 | 中文名 tag 看似"有效" | 返回 115048 条数据，像成功 | total 与基线相同即无效，要拿 total 做判据 |
| 5 | per_page 调大提速 | 200 报错、无 x-data | 上限 **100** |
| 6 | 分片叫 `.png` | 以为是图片资源 | 是 AES 加密的 `.ts`，播放器按 HLS 处理 |
| 7 | 首条相同误判过滤失败 | tag=407 首条与全站首条同片 | 用 **total** 判定，不要只看第一条 |
| 8 | `duration` 当毫秒 | 5750 毫秒只有 5 秒，明显不对 | 单位是**秒**，5750s = 1:35:50 |
| 9 | 图片以为要解密 | 准备好 `ksSpDecryptImg` | `.image` 直链可直接取，200 正常图片 |

---

## 九、遗留

1. `api/vod/tag` 有 6628 个标签，适配器只固化了 24 个常用 + 动态前 60，长尾标签未收录（可按需扩大）。
2. 付费内容（`is_paid=1`）未验证是否只给预览片段；`drama_pay_mode` / `drama_free_episodes` 字段暗示有剧集付费逻辑，未深挖。
3. `product_type` 取值差异未穷举（当前全站以 1 为主）。
