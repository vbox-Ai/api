# -*- coding: utf-8 -*-
"""追加 mdtv 第三轮发现：idKey="channel" 已确认"""
import io
import os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
P = os.path.join(ROOT, "docs", "剩余21平台攻坚情报.md")
s = io.open(P, encoding="utf-8").read()

ADD = '''
### 6.6 第三轮：动态键名已确认 = `"channel"`

从 `mdtv_route.dart` 的 `VideoPage` 构造 + `channel_page.dart` 的跳转参数还原：

```dart
// mdtv_route.dart  [closure] VideoPage
VideoPage(
  id:    getExtraInt("id"),
  idKey: getExtraString("idKey"),
  title: getExtraString("title"),
)

// channel_page.dart  跳转 /module/mdtv/segVideo
extra = {
  "title":  <频道名>,
  "id":     <频道 id (int)>,
  "idKey":  "channel",        ← 就是这个字符串
}
```

因此 `video/listcache` 的完整 biz 为：

```json
{
  "page":      1,
  "list_row":  120,
  "type":      4,
  "channel":   <频道 id>
}
```

（`tag_page.dart` 走的是另一条 `idKey`，应为 `"tag"`，尚未核）

### 6.7 仍 1002 —— 问题已定位到 post-data 编码层

参数名/结构现在完全对上 asm，但服务端仍返回 `{"code":1002,"msg":"参数错误"}`。
已排除：
- 路径（4 个都试）
- `channel` 取值 0–8
- `type` 4/1/0/2
- `list_row` 20/120
- body 带/不带 timestamp

**新怀疑点（下轮验证）**：
1. **Dart `jsonEncode` 的非 ASCII 转义差异** —— Dart 默认把非 ASCII 转成 `\\uXXXX`，
   而 Python `json.dumps` 默认 `ensure_ascii=True`（我用的是 `False`，输出原始 UTF-8）
   → 若 map 里有中文（如 title）会导致明文不同、签名不符
2. **外层 body 可能还缺字段**（`app_id` / `version` / `suffix` 之类），
   asm 里 `map.clear()` 后只放了 post-data，但可能还有别的 header 承载
3. **`timestamp` 的精度** —— Dart 用 `millisecondsSinceEpoch` 还是 `secondsSinceEpoch` 需再核

**结论**：算法层已 100% 还原（加密/解密/签名/参数结构），卡在最后一层报文细节。
最快路径是**真机抓一次 `/video/listcache` 的实际请求体**做逐字节对比。
'''

if "### 6.6 第三轮" not in s:
    s = s.rstrip() + "\n" + ADD
    io.open(P, "w", encoding="utf-8", newline="\n").write(s)
    print("已追加第三轮发现")
else:
    print("已存在")
