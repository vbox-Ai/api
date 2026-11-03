# 麻豆TV（mdtv）协议详解 —— 已全线打通

> 更新时间：2026-11-03 14:40（北京时间）
> 状态：**分类 / 列表 / 详情 / 播放 四能力全通**（101 分类、120/页、last_page 79、共 9404 条）
> 适配器：`sources/welfare-js/mdtv.py` · 注册键 `mdtv_py` · 首页 host `https://spi.d5c4a712.com`
> 逆向来源：`libapp.so` blutter 反汇编 `package:avbox/module/mdtv/**`

---

## 一、为什么之前卡在 `{"code":1002,"msg":"参数错误"}`

前两轮把密钥、签名、参数结构都还原对了，却始终 1002，并且**误判成"业务参数名不对"**，
连续穷举了路径 × channel 0-8 × type × list_row × 时间戳精度 × body 三种形态 —— 全是 1002。

真相是两处**报文层**细节，与业务参数完全无关：

| # | 缺失/错误项 | 现象 | 根因 |
|---|---|---|---|
| 1 | 请求头 `suffix: JGDZMX` 没发 | 恒 `1002 参数错误` | 服务端用 `suffix` 头还原**请求 IV**：`"-p9B[~PnPs" + 头值`。头缺失 → 请求体解不开 → 业务层拿到空参 → 参数校验必然不过 |
| 2 | 签名 SECRET 多了一个反斜杠 | 补上 suffix 头后立刻变 `1001 签名错误` | blutter 打印字符串时把 `?` 印成了 `\?`；`libapp.so` 偏移 **367007** 的原始字节里**没有反斜杠** |

这也是"响应能解密、请求恒失败"的迷惑点：响应 IV 只依赖响应体的 `suffix` 字段，
用同一个 KEY 照样解得开，看起来"算法全对"，实际上请求压根没被服务端读进去。

> 排查方法论：**先用一个必然失败的已知错误（少发头）观察错误码是否变化**。
> 1002（解不开请求体）→ 补头 → 1001（签名错）→ 改 secret → 200，
> 每一步错误码都在"往前走"，说明前一刀切在了正确的位置。

---

## 二、请求构造（`MdTvInterceptor::onRequest` @ 0x8d5ae8）

```
1)  data = RequestOptions.data（业务 map）── 拷进 interceptor 自持的 map 并 clear 复用
2)  ts = DateTime._getCurrentMicros() / 1000                ← 毫秒（0x8d5c38~0x8d5c68）
    map["timestamp"] = ts
3)  keys = map.keys.toList()..sort()                        ← Dart String.compareTo（按码位）
    joined = "&".join( Uri.encodeComponent(k) + "=" + v.toString() )   （键需 encode，值不 encode）
4)  sign = MD5( joined + "&m}q%ea6:LDcmS?aK)CeF287bPvd99@E,9Up^" )     ← 小写 hex
    map["encode_sign"] = sign
5)  post = base64( AES-256-CBC( jsonEncode(map), key, iv ) )
       key = "Vq234zBeSdGgYXzVTEfnnjjdmaTkk7A4"   (32B)
       iv  = "-p9B[~PnPsJGDZMX"                   (16B)
6)  map.clear(); map["post-data"] = post
7)  headers["suffix"]         = "JGDZMX"
    headers["Content-Type"]   = "application/json"
```

要点：

- **timestamp 进签名串**（写 map → 再排序 → 拼串），漏了它必然 1001。
- 排序在 timestamp 之后、encode_sign 之前，所以签名串形如
  `channel=21&list_row=120&page=1&timestamp=1793685868789&type=4`。
- `jsonEncode` 输出的键顺序是 map 插入顺序（业务键 → timestamp → encode_sign）；
  服务端按值解析 + 重算签名，键序不影响校验，但保持同序最稳。
- AES 用 `encrypt` 包的默认档：CBC + PKCS7，`Encrypter.encrypt(String)` 返回字节，
  外层再 `base64.encode` → 标准 base64（非 url-safe）。

## 三、响应解密（`MdTvInterceptor::onResponse` @ 0x8f2f28）

```
body  = {"suffix":"<6位hex>","data":"<base64>"}
iv    = ("-p9B[~PnPs" + suffix)[:16]  → UTF-8 取字节              ← 9+6=15，末位补 \x00
plain = AES-256-CBC-decrypt( base64(data), key, iv )            ← 同一把 32B key
信封  = {"code":0,"msg":"操作成功","data":{...}}
```

错误码语义：

| code | msg | 含义 |
|---|---|---|
| 0 | 操作成功 | 正常 |
| 1001 | 签名错误 | 请求体解得开，但 `encode_sign` 不匹配（secret / 参与字段 / 时间戳精度） |
| 1002 | 参数错误 | **请求体解不开**（suffix 头缺失）或业务必填项缺失 —— 泛化错误码，不可单凭它定位 |

## 四、接口与业务参数

| 接口 | biz | 用途 | 实测 |
|---|---|---|---|
| `POST video/channel` | `{}` | 分类（频道） | code 0，返回 id/name/desc/image/total |
| `POST video/tags` | `{}` | 标签 | code 0，返回 id/name/key/thumb/is_hot/order |
| `POST video/listcache` | `{page, list_row:120, type:4}` | 首页推荐 | 9404 条 / 79 页 |
| `POST video/listcache` | `{page, list_row, type:4, channel:<id>}` | 分区列表 | channel=21 → 2546 条 |
| `POST video/listcache` | `{page, list_row, type:4, tags:<id>}` | 标签过滤 | tags=99 → 6829 条 |
| `POST video/list` | `{page, list_row, keyword}` | 搜索（注意**没有 type**） | 关键词「麻豆」→ 52 条 |

分页参数：`page` 从 1 起，`list_row` 客户端固定 120（传 20 也接受），
响应 `data` 里带 `total / per_page / current_page / last_page`。

**不存在** `/video/detail` 与 `/video/play`：客户端的"详情页""播放"全部直接用列表项字段
（`VideoPage` 跳到 `/player` 时把整条 `Video` 塞进 `Playlist`）。
所以适配器的 detail / play 都从列表缓存取，缓存 miss 时回溯翻 3 页推荐列表。

## 五、资源

| 资源 | 来源 | 说明 |
|---|---|---|
| 封面 | `thumb`（`imgsmd.n123dx.xyz`） | 另有 `preview` / `panorama`（webp） |
| 播放 | `video_url` | **HLS m3u8 直链**（`m3md.n6uem8.xyz`），分段在 `mdsm3.n6uem8.xyz` |
| 试看 | `test_video_url` | 相对路径，`hls/preview/index.m3u8` |
| 加密 | `#EXT-X-KEY:METHOD=AES-128,URI="enc.key"` | `enc.key` 同目录匿名可取，播放器自己处理 |

m3u8 实测：`Dart/3.4 (dart:io)` 与 iPhone Safari UA 均 200，无需 Referer / Cookie。

## 六、代码索引（asm → 结论）

| 位置 | 读到的东西 |
|---|---|
| `module/mdtv/network/interceptor.dart` 0x8d5ae8 | onRequest 全流程（clear → addAll → 毫秒 ts → sort → MD5 → AES → post-data → 两个头） |
| 同上 0x8d59f0 | 签名串闭包：`encodeComponent(key) + "=" + value.toString()` |
| 同上 0x8f2f28 | onResponse：`"-p9B[~PnPs" + body["suffix"]` 作 IV |
| `module/mdtv/network/service.dart` 0x82e6f4 | `MdTvHttp._dio.baseUrl = SpUtil.getString("mdtv")` + `MdTvInterceptor` 挂载 |
| `module/mdtv/page/home_page.dart` 0x99a9e4 | 推荐 biz `{page, list_row:120, type:4}`（数组长度 12 = 3 对） |
| `module/mdtv/page/video_page.dart` 0x99b03c | 分区 biz 追加 `widget.idKey → widget.id` 第 4 对 |
| `module/mdtv/page/channel_page.dart` 0x5c053c | 跳 `/module/mdtv/segVideo`，extra `{title, id, idKey:"channel"}` |
| `module/mdtv/page/tag_page.dart` 0x5c07e8 | 同上，`idKey:"tags"` |
| `module/mdtv/page/search_page.dart` 0x99aed8 | 搜索 biz `{page, list_row, keyword}` → `video/list` |
| `libapp.so` @367007 | SECRET 原始字节（无 `\`）、@532843 KEY、@537465 请求 IV |
| `module/mdtv/page/video_page.dart` 0x976cfc | 点击 → `push("/player", extra: Playlist)`，播放地址即 `video_url` |

## 七、验证记录（2026-11-03 14:35）

```
$ python tools/_smoke_standalone.py mdtv
mdtv   ✓101   ✓120   ✓1   ✓

$ python tools/_test_inject.py
mdtv   {"_vbox_effective_hosts": ["https://spi.d5c4a712.com"]}   101   120   1

$ python tools/_gen_platform_table.py
总 31 / 平铺 11 / 出数据 11 / 四能力全通 11
```

探测脚本留档：`tools/_mdtv_r8.py`（打通这一刀）、`tools/_mdtv_r9.py`（全接口 + 字段结构）、
`tools/_mdtv_strbytes.py`（二进制字符串取证）。

## 八、可复用的三条经验

1. **flutter AOT 反汇编里的字符串不可信到字节级**：`\?` `\\` `\"` 之类要先回
   `libapp.so` 查原始字节（`re.finditer(needle, data)` 打 ±40 字节上下文），
   一个转义就能让签名差 1 字节、错误码却是"参数错误"。
2. **interceptor 里 `headers[...] = ...` 的赋值和 body 加密同等重要**：
   这类平台的 IV 常常由"固定前缀 + 平台标识头"拼成，头就是密钥的一部分。
3. **错误码迁移是进度条**：同一请求改一个变量后错误码变化（1002→1001→0），
   比任何 A/B 穷举都更能证明"改的是正确的那一层"。
