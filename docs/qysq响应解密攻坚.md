# qysq 响应解密 · 攻坚记录（未破，已排除面收窄）

> 时间：2026-11-03 15:20（北京时间）
> 状态：**签名链 100% 通（code=200）**；响应 `data` 仍为密文，本轮 10 轮爆破未命中。
> 相关脚本：`tools/_qysq_r5.py` ~ `_qysq_r10.py`、`tools/_qysq_env.py`、`_qysq_saltbytes.py`

---

## 一、已实证的部分

签名（`QySqInterceptor::_generateSign` @0x8e100c）已在真实接口上跑通：

```
msg  = f"{token_qysq}&/{path}&{DEV_UA}&{ts}&{nonce}"
sign = HMAC_SHA1("gH3nA7fR9tV1jY6z", msg)
头：X-User-Agent / user-agent / authorization: Bearer <token> / x-api-key: timestamp=…;sign=…;nonce=…
```

实测（2026-11-03 15:1x）：

| 接口 | code | 密文字节数 | %16 | 说明 |
|---|---|---|---|---|
| `POST api/app/media/home` | 6023（演员不存在） | 172 | 12 | 业务错也要密文回包 |
| `GET api/app/ping/config` | **200 success** | 108556 | 12 | 最佳样本（业务成功） |
| `POST api/app/media/short/hot` | 200 success | ~340000 | 12 | 之前那份 340012B 即此类 |

信封统一为 `{"code":…,"msg":…,"tip":…,"hash":true,"data":"<base64>"}`，
`hash:true` 标记 data 为密文。

## 二、解密函数已定位：`CryptoUtil::asGjCrypto` @0x7237f0（size 0x55c）

调用点：`module/qysq/network/service.dart::QySqHttp.post` @0x7235ec → 返回值直接 `jsonDecode`。

asm 里能确定的事实：

| 锚点 | 内容 |
|---|---|
| 0x723814 | 32 字节固定盐 `vEukA&w15z4VAD3kAY#fkL#rBnU!WDhN`（`libapp.so` @521089 原始字节实证） |
| 0x72382c | `D = base64Decode(resp["data"])` |
| 0x7239bc | `sublist(D, 0, ?)` → 与盐拼接后喂 `sha256`（第一次 KDF） |
| 0x723a38 / 0x723ac4 | 两处 `Instance__Sha256` → 两段式 KDF |
| 0x723ca8~0x723d34 | `Key(x)` + `AES(mode=Instance_AESMode)` + `Encrypted(D.sublist(12))` + `IV(y)` + `decrypt()` |
| 0x723cf0 | **密文 = `D[12:]`**（12 字节前缀），与样本 `%16=12` 完全吻合 |

即：`plain = AES-CBC(ct=D[12:], key, iv)`，key/iv 由 盐 + D 前缀经两段 sha256 派生。

## 三、本轮排除面（共约 120 万组合，全部 0 命中）

| 轮次 | 覆盖面 | 结果 |
|---|---|---|
| r5 | nonce∈{12,16,24} × key/iv 切片 × cut，CBC | 0 |
| r6 | 加 H2/H3 二次哈希、CFB/OFB/CTR、skip∈{0,12,16,24} | 0（唯一"命中"是可打印率噪声，已废弃判据） |
| r7 | sha256 族 + md5 + sha512，打分排序 | 0 高分候选 |
| r8 | **sha384/sha512**（让 asm 里 `H[8:48]`、`H[12:40]`、`H[28:]` 这些边界合法）× 顺序 × 切片 × CBC/CFB/OFB | 0 |
| r9 | 盐本身当 key/iv + 哈希族全切片（1755 keys × 721 ivs） | 0 |
| r10 | 两段式 KDF 精确建模：`H2 = sha256(K1 + D[a:b])`，a/b 取 asm 边界 | 0 |

## 四、下一步（三条路，按性价比）

1. **真机 Frida（最快，一步到位）**：hook `CryptoUtil::asGjCrypto`（`libapp.so` 基址 + `0x7237f0`）
   的入参与返回值 —— 返回即明文 JSON；再 hook `Key()`/`IV()` 构造即可拿到最终 key/iv 字节，
   反推派生链一次成型。**需要真机/模拟器通道**（本机无）。
2. **补全分支建模**（纯静态，继续投入）：给解释器加 `tbz/tbnz` + 类型标签比较，
   让两条编译分支各自可达，越界 clamp 自然消失。
3. **先换目标**：用 aijav 那套「业务码 vs 泛化码」判据扫 `zlt`/`javdb` 的路由表
   （那两个的卡点是"缺一个要素"，扫路由常能把缺的端点/字段一并暴露），回头再啃 qysq。

## 四·补、本轮新增：指令级迷你解释器（`tools/_qysq_r12_sim.py`）

不再猜公式，把 `asGjCrypto` 的 **341 条指令**按地址顺序喂给状态机
（x0..x21 寄存器 + `[fp-0xNN]` 槽位 + SP 参数栈），分支全部忽略，桩函数按 Dart ABI 语义实现。

跑通后确认/发现：

| 观察 | 含义 |
|---|---|
| `sublist(D,0,24)` 结果拼到 32B 盐后面 → **56 字节缓冲** | `X = P + D[0:24]` 确认无误 |
| 该 56B 缓冲先 `Uint8List.fromList` 实体化再喂 `sha256` | 第一次 KDF 确认 |
| 之后出现 `sublist(8,48)` / `(0,16)` / `(24)` / `(12,40)` / `(28)` | **在 32B 摘要上全部越界** → 只有两种可能：① 摘要其实是 48/64B（sha384/512）；② blutter 打印的立即数是 Smi 编码（真实值需 /2） |
| 末尾两次 `_slowSetRange` 产出两个缓冲，分别进 `Key()` 与 `IV()` | key/iv 由「sha 链 + 切片」拼成 |

**新卡点（已定位到具体机制）**：忽略分支会让越界 `sublist` 被 clamp
（`[8:48]` 在 32B 上被截成 24B），而真实 Dart 走的是**另一条内联拷贝分支**，边界不同 ——
模拟出的 key/iv 必然不是真的。判据也现成：`sublist(0,24)` 作用在 172B 的 D 上，
若 24 是 Smi(=12)，则 `X = P + D[0:12]` 只有 44 字节，后面 `sublist(0,112)` 立刻越界 ——
**故 24 是真实值，Smi 假设被排除**；剩下就是必须把 `tbz/tbnz` 的类型标签比较建模。

## 五、判据教训（已进交接文档）

- 「明文以 `{` 开头」不能当命中判据（随机噪声也会命中）→ 必须严格 `json.loads`。
- 样本长度 `%16 == 12` 是硬线索：**密文一定从 D[12] 开始**，先把这一条钉死再谈 key/iv。
- 先拿业务成功（code=200）的样本，比错误包更适合做爆破目标。
