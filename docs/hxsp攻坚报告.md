# hxsp（红杏视频）攻坚报告

> 2026-11-02。结论：**签名链完整还原，服务端可达并进入业务层，但卡在 `10` 回执**。

## 一、已取得的进展

| 项 | 状态 |
|---|---|
| 真实 host | `https://hxapi.ruueyek.com/`（splash 下发）+ `http://172.247.132.138/`（反汇编硬编码，同一后端） |
| token | `exp=2306664775`（**2043 年，永不过期**） |
| 接口路径 | 16 个，全部从反汇编提取 |
| 签名算法 | **完整还原**（见下） |
| 请求加解密 | AES-128-CBC，往返自检通过 |
| 服务端可达 | ✅ 已绕开 Python TLS 问题（改用 curl） |
| 路由存在性 | ✅ 用对照实验确认 |

## 二、签名链（完整还原）

数据来源：`avbox/module/hxsp/network/interceptor.dart`

```
固定字段（注意 matchid 全小写）：
  appVersion = "5.3"
  client     = "1"
  tenant     = "05"
  phoneIp    = "10.0.0.0"     (先设 0.0.0.0，后被覆盖)
  matchid    = "4310ced81499c24b"
  m3         = "1"
  m2         = "a4a099fc3c66bf328caa4ce4d5268c0b"
  token      = token_hxsp
  timestamp  = 13 位毫秒
  nonce      = uuid4

① 合并业务参数 → SplayTreeMap（按键名字典序排序）
② sign = MD5( jsonEncode(sortedMap) + "b7flnSQP98989988fMEQXhhG" )
③ map["sign"] = sign
④ ct = base64( AES-128-CBC(
       key = "W$S3skNwm3zkHXqd",
       iv  = "ZV8^Vg!aSyk!uRNh",
       data = PKCS7(jsonEncode(map))
   ) )
⑤ 请求体 = {"ct": ct}
   Authorization = "Bearer_" + token_hxsp
   Content-Type  = application/json
```

响应解密：`Encrypter.decrypt64(response, iv)` —— 同一对 key/iv。

## 三、服务端行为矩阵（实测）

| 请求 | 响应 | 判定 |
|---|---|---|
| `GET` 接口 | `唯一编码:xxx Request method 'GET' not supported` | Spring 层在，路由存在 |
| `POST {}` | `{"code":1,"message":"参数缺失"}` | 参数绑定层 |
| `POST {"ct":""}` | `{"code":1,"message":"参数缺失"}` | 同上 |
| `POST [数组]` | `唯一编码:xxx null` | 绑定器拿不到 ct |
| `POST "裸字符串"` | `唯一编码:xxx null` | 同上 |
| `POST {"ct":"任意非空"}` | **`10`** | ← **卡在这里** |
| `POST` 不存在的路径 | Spring 404 | 对照 |
| `PUT` / `PATCH` | `Request method 'X' not supported` | 对照 |

## 四、`10` 的性质（已穷尽验证）

**`10` 是 2 字节纯文本（hex `3130`），与输入完全无关。**

| 测试维度 | 结果 |
|---|---|
| ct 长度 1→4096 | 全部 `10` |
| ct = 全零密文 16/32B | `10` |
| ct = 随机 64B | `10` |
| ct = 合法 base64 + 正确 AES 加密 | `10` |
| ct = 特殊字符（XSS/SQL/模板注入） | `10` |
| ct = `null` / `true` / `[]` / `{}` | `10` |
| 加 sign / timestamp / nonce | `10` |
| 加 client / tenant / matchid / appVersion | `10` |
| 换 UA（5 种） | `10` |
| 加 X-Forwarded-For / X-Real-IP | `10` |
| 连续 8 次请求 | 恒定 `10` |
| 去掉 Authorization | `10` |
| 换 Content-Type（json/form/plain） | `10`（multipart 会报解析错误） |
| 换域名（CDN / 源 IP） | `10` |

## 五、结论

`10` 是**服务端在 `ct` 非空之后、解密之前的某个固定校验失败的回执**。

为什么可以确定不是"解密失败"：
- 合法的、用正确算法加密的 ct 和随机字节的 ct 返回完全相同
- 若真走到解密，至少应该有不同的 padding 错误表现

为什么可以确定不是"路由不存在"：
- 相同路径用 GET 会返回 `Request method 'GET' not supported`（说明路由注册了）
- 不存在的路径返回标准 Spring 404

**推测**：服务端可能在 `ct` 之外还有一个必填但未在客户端代码出现的要素
（例如需要在 Header 里带某种签名、或需要先调某个初始化接口拿 grant）。
客户端反汇编里没有这个要素，说明它可能由更底层（如原生 SO 或证书绑定）提供。

## 六、下一步需要什么

要继续突破，需要以下之一：

1. **真机抓一次 hxsp 的成功请求**（最直接）
   - 抓包工具：HttpCanary / Reqable / Frida hook Dio
   - 重点看：完整的请求头集合、请求体原文、以及**请求前的其它调用**

2. **Frida hook `HxSpInterceptor.onRequest`**
   - 直接拿到 map 的最终内容（在加密前）
   - 和最终发出的 headers
   - 这样能确认我漏了什么

3. 检查是否有原生层（libapp.so 之外的 .so）参与签名

## 七、可复用脚本

| 脚本 | 用途 |
|---|---|
| `_hxsp_http.py` | curl 客户端（绕开 Python OpenSSL 与该 CDN 的 TLS 不兼容） |
| `_hxsp_v3.py` | 签名链实现：构造 + 加密 + 发送 |
| `_hx2_exist.py` | 路由存在性对照实验 |
| `_hx2_chain.py` | ct 处理链探测 |
| `_hx2_bytes.py` | 原始字节分析 |
| `_hx2_send.py` | 往返自检 + 发送 |
| `_hx2_ip.py` | 双后端对比 |

## 八、重要副产品：Python TLS 问题

```
Python urllib → hxapi.ruueyek.com  SSL: UNEXPECTED_EOF_WHILE_READING
curl (schannel) → 正常
```

该域名 CNAME 到 `.gccdn.net`（14.0.47.29 / 138.113.152.120），
Python 的 OpenSSL 与该 CDN 握手不兼容。**所有 hxsp 请求改用 curl 子进程**。
这解释了文档里"CloudFront WAF 403"的部分现象——不全是 WAF，有 TLS 层问题。
