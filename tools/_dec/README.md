# tools/_dec —— 已解密的明文资产

> 这些是**解密后的服务端原始响应**，不是代码。用于离线查阅协议、校对字段、避免重复抓包。

## 文件清单

| 文件 | 来源 | 大小 | 说明 |
|---|---|---|---|
| `box_api_splash.json` | 6868 `/box/api/splash` | 5.9 KB | **38 个 host + 14 个 token** 的权威表 |
| `box_api_home_versionCode=101.json` | 6868 `/box/api/home` | 9.9 KB | 40 个模块 / banner / 版本信息 |
| `collect_api_status.json` | 6868 `/collect/api/status` | 46 B | 登录态校验体 |
| `mmav_config.json` | mmav `data/config/base-1.js` | 4.2 KB | 域名分工、开关、客服链接等 60+ 字段 |
| `mmav_category.json` | mmav `data/category/base-1.js` | 27 KB | 分类树，10 个一级菜单 × 8 子分类 |
| `mmav_list_sample.json` | mmav `data/mediaVideo/list-7-1-50.js` | 51 KB | 列表样本，50 条完整字段 |

## 各文件的解密方式

### 6868 主后端（box_* / collect_*）

```
chunked 去帧 → base64 解码 → AES-128-CBC → 软 gzip → JSON
key = "8992d27bceae2962"      # 16 字符 ASCII，不是 hex
iv  = "62233532ac9029c6"
gzip 尾部有瑕疵，须用 zlib.decompressobj(-15) 从第 10~16 字节偏移软解
```

解密器：`tools/_cap_final.py`

### mmav（mmav_*）

```
base64 解码 → AES-256-CBC → JSON
key = "IdTJq0HklpuI6mu8iB%OO@!vd^4K&uXW"   # 32 字符 → AES-256
iv  = "$0v@krH7V2" + response["suffix"]     # 固定串在前，动态 suffix 在后
```

解密器：`tools/_mmav_dec.py`
重新生成：`python tools/mmav_dump.py`

## 用途

1. **离线查域名**：不用每次都跑抓包，直接看 `box_api_splash.json`
2. **校对字段名**：写 Adapter 时对照 `mmav_list_sample.json` 的真实结构
3. **验证解密实现**：改完解密代码，比对产物是否一致
4. **追溯协议变更**：服务端改字段时，diff 新旧产物即可发现

## 注意

- `box_api_splash.json` 里的 token 会过期（`token_one` 已过期），**不能当永久凭据用**
- 域名会轮换，以最新一次抓取为准
- 这些文件含真实域名与 token，仓库为私有
