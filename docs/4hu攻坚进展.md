# 4hu（4虎）攻坚进展

> 2026-11-02。状态：**加密算法全部破解，但站点域名高频轮换 + SPA 化，数据接口未拿到**

## 一、已破解的部分

### 1. 业务响应解密（AES-256-CBC）

数据来源：`avbox/module/hu4/network/interceptor.dart`

```
Key = "22946bc50fd63164b79df55070a85a92"   ← 32 字符，按 UTF-8 直接当 32 字节用（AES-256）
IV  = "kaixin1234567890"                    ← 16 字符，按 UTF-8（AES-CBC）
先 _safeBase64（- _ → + /），再 decrypt64 → jsonDecode
```

**踩坑**：key 是「32 个字符」不是「32 位 hex」。按 hex 解码只有 16 字节，会解出乱码。

实测（`/api/v2/search?keyword=test`）：

```json
原始: {"status":1,"data":"pTtX-Us8BCClv0V7wpAxHpMAwEaUN-r0..."}
解密: {"per_page":50,"current_page":1,"total":0,"data":[],"keywords":[""]}
```

### 2. CDN 反爬（ap-d 挑战）算法

站点对 `json/`、`public2/json/` 等路径返回挑战页：

```html
<script type="text/plain" id="ap-d" data-m="1" data-k="<32位hex>" data-c="utf-8">
  <base64 密文>
</script>
<script src="/.cdn-OfgxKS1PrI2KYpqH/d.js?v=f1b3107c1f2f" onerror="..."></script>
```

从 `d.js` 反混淆（386 处字符串还原）得到核心算法 `_0x388899` / `_0xdd0cd6`：

```js
// key 派生
key_bytes[i] = parseInt(data_k_hex.substr(i*2, 2), 16) ^ 0xA5
// 解密
plain[i] = base64decode(ap_d_blob)[i] ^ key_bytes[i % len(key_bytes)]
```

**这是纯 XOR，不需要执行 JS。** Python 实现见 `tools/4hu_client.py`。

### 3. 媒体签名机制（已定位未验证）

反混淆代码里：

```js
signUrl(u) => fetch("/.cdn-OfgxKS1PrI2KYpqH/sign?u=" + encodeURIComponent(u))
                  .then(r => r.json()).then(j => j.u || u)
// 触发条件：window.__APM === "sign" 且 URL 命中
//   /\.(jpe?g|png|gif|webp|avif|svg|ico|mp4|webm|ogv|ogg|m3u8|ts)([?#]|$)/i
//   且 URL 不含 scdn_s=
```

即 m3u8/ts/图片走 `sign?u=` 换签名地址。直接 GET 该端点返回 404（可能需要特定头或 POST），未继续验证。

## 二、卡点

### 域名高频轮换

| 时间 | 入口域名 | 跳转目标 |
|---|---|---|
| 首测 | `h96h69.com` | `872k5e.com` / `k2hy98.com`（轮换） |
| 数小时后 | `872k5e.com` | `xa49d8.com` |

每次 302 跳到域名池里的另一个站。池成员会变，需要动态跟随。

### SPA 化

解密 `ap-d` 后拿到的是 **SPA 壳页**（3713 字节的 HTML），不是数据。
真实数据由 SPA 加载后通过 XHR 取，而 XHR 又受同一套 `sign` 机制保护。

### 搜索接口被忽略的关键词

`/api/v2/search` 免挑战可直接访问，但：

- ASCII 关键词（test/abc/4k）→ 200，`total:0`，`keywords:[""]`（关键词被吞）
- 中文关键词 → 500
- 空关键词 → `请输入关键字`

说明搜索接口能通但拿不到数据，可能需要额外参数（`tbname` / `listtempid` 等）。

### 4hu_api 域名已挂

`portal.instruno.com`（splash 里的 `4hu_api`）返回 **502 Bad Gateway**，上游已停。

## 三、客户端接口清单（反汇编提取）

| 用途 | 路径 |
|---|---|
| 分类 | `public2/json/category/{x}.json` |
| 详情 | `public2/json/view/{id}.json` |
| 播放数据 | `json/video/{id}.json` |
| 搜索 | `api/v2/search?page=&classid=&keyword=` |

请求头只有 `user-agent`（iPhone Safari UA），无签名（`onRequest` 只设这一个头）。

## 四、下一步

1. 实现域名池自动跟随（302 跟到底，缓存可用域名）
2. 验证 `sign?u=` 的正确调用方式（头/方法）
3. 若 `sign` 通，媒体即可播放；否则 4hu 只能拿到 SPA 壳，价值有限
4. 搜索接口试 `tbname` / `listtempid` 等参数组合

## 五、脚本

| 文件 | 用途 |
|---|---|
| `tools/4hu_client.py` | XOR 解密 + AES 解密 + 域名跟随 |
| `tools/_4hu_work/deob2.js` | d.js 反混淆（386 处字符串还原，产出 d.deob.js） |
