# -*- coding: utf-8 -*-
"""把 mdtv 第二轮（更精确的算法）追加进情报文档"""
import io
import os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
P = os.path.join(ROOT, "docs", "剩余21平台攻坚情报.md")
s = io.open(P, encoding="utf-8").read()

ADD = '''
---

## 六、mdtv 深度修正（第二轮，2026-11-03 晚）

### 6.1 之前两处关键错误（已修正）

| 项 | 错误值 | 正确值 |
|---|---|---|
| 请求加密 key | `-p9B[~PnPsJGDZMX`（16B，当 AES-128 用） | **`Vq234zBeSdGgYXzVTEfnnjjdmaTkk7A4`（32B，AES-256）** |
| 签名 secret | 借用 aijav 的 `&NRkw0g3iJLDvw5tJ5PuVt5276z0SOuyL` | **`&m}q%ea6:LDcmS\\?aK)CeF287bPvd99@E,9Up^`（mdtv 专有）** |

IV 仍为 `-p9B[~PnPsJGDZMX`（16B）。

### 6.2 精确的请求加密流程（`MdTvInterceptor::onRequest`）

```
1) biz = {业务参数}
2) biz["timestamp"] = 秒级时间戳                      ← 关键：timestamp 在签名前就放进 map
3) joined = "&".join(f"{k}={biz[k]}" for k in sorted(biz.keys()))
4) biz["encode_sign"] = MD5(joined + "&m}q%ea6:LDcmS\\?aK)CeF287bPvd99@E,9Up^")
5) post_data = base64( AES-256-CBC(jsonEncode(biz), key=Vq234z…, iv=-p9B[~PnPsJGDZMX) )
6) map.clear() → map["post-data"] = post_data
7) 请求体 = {"post-data": post_data}
```

**注意**：签名串里含 `timestamp`（`0x8d5c88` 先写 map 再排序），这是第一轮漏掉的关键点。

### 6.3 `video/listcache` 的 map 结构（`video_page.dart::loadData` @ 0x99b03c）

```dart
{
  "page":       <当前页>,
  "list_row":   120,          // 常量
  "type":       4,            // 常量
  "<动态键>":    <动态值>,     // widget.field_13 / widget.field_b（推测为 channel 相关）
}
```

### 6.4 当前卡点（未出数据）

post-data 解密链路和签名都已按 asm 精确实现，但服务端仍返回：

```json
{"code": 1002, "msg": "参数错误"}
```

已穷举测试（全部 1002）：
- 路径：`/video/list`、`/video/listcache`、`/video/channel`、`/video/tags`
- `channel_id` ∈ {0, 1, 2, 3, "", "0", "1"}
- `type` ∈ {4, 1, 0, 2}
- `list_row` ∈ {20, 120}
- 请求体带/不带 timestamp

**结论**：1002 出现在 post-data 成功解密之后（否则会报签名/解密错误），
说明**业务层参数校验未通过** —— 缺的应是那个「动态键」（widget 传入的 channel 相关参数）。
下一步应从 `channel_page.dart` / `mdtv_main.dart` 追溯该字段的真实名称与取值来源。

### 6.5 已确认可用的算法资产

| 项 | 值 |
|---|---|
| 响应解密 key | `Vq234zBeSdGgYXzVTEfnnjjdmaTkk7A4`（AES-256） |
| 响应解密 IV | `-p9B[~PnPs` + 响应 `suffix`（9+6，补齐 16） |
| 响应结构 | `{"suffix":"<6hex>","data":"<base64>"}` |
| 签名 secret | `&m}q%ea6:LDcmS\\?aK)CeF287bPvd99@E,9Up^` |
| 请求加密 | AES-256-CBC，key 同上，IV `-p9B[~PnPsJGDZMX` |

> 响应解密已在 `/video/list`、`/video/channel`、`/video/tags` 三个接口实测成功
> （明文 `{"code":1002,"msg":"参数错误"}`），**解密链路 100% 可信**。
'''

if "## 六、mdtv 深度修正" not in s:
    s = s.rstrip() + "\n" + ADD
    io.open(P, "w", encoding="utf-8", newline="\n").write(s)
    print("已追加 mdtv 第二轮修正")
else:
    print("已存在")
