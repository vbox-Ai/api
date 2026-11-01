# tools/ 逆向工具与情报资产索引

> 暮色聚合适配专项。所有脚本均可在本地直接运行（部分需走 127.0.0.1:7890 代理）。

## 一、数据资产（直接可用）

| 文件 | 内容 | 来源 |
|---|---|---|
| `_dec/box_api_splash.json` | **已解密明文**：38 个 host + 14 个 token | 6868 抓包 → AES+gzip 解密 |
| `_dec/box_api_home_versionCode=101.json` | **已解密明文**：40 个模块 / banner / app 更新信息 | 同上 |
| `_platform_intel.md` | 平台情报表（host 全集 + token 全集 + 模块表） | 由上面两个 JSON 自动生成 |
| `_1101_module_map.json` | 37 个平台模块 × URL / hex / 路径 结构化映射 | libapp.so 字符串池切分 |
| `_1101_keys.json` | 按模块归类的密钥候选 | 同上 |
| `_1101_final_keyintel.md` | 密钥 + 邻近平台验证结果 | 同上 |

## 二、核心脚本

### 6868 主后端

| 脚本 | 用途 |
|---|---|
| `_cap_dump.py` | 遍历抓包会话，导出 URL / 请求头 / 响应头到汇总文本 |
| `_cap_final.py` | **6868 响应解密器**：chunked → base64 → AES-128-CBC → 软 gzip → JSON |

解密参数（关键）：

```
key = "8992d27bceae2962"   # 16 字符 ASCII，不能用 bytes.fromhex
iv  = "62233532ac9029c6"
gzip 尾部有瑕疵，须用 zlib.decompressobj(-15) 从第 10~16 字节偏移软解
```

### libapp.so 分析

| 脚本 | 用途 |
|---|---|
| `_so_extract.py` | 全量提取 so 字符串，按 `avbox/module/<key>/` 分组 |
| `_so_modules.py` | **模块级密钥归属**：取每个模块边界后 40 个 token 窗口 |
| `_so_keys_final.py` | 确定性提取密钥候选（口令 / 16 位 / 32 位 hex 三种形态） |

验证方式：`lclf` 段捕获到 `185Hcomic3PAPP7R`，与已知禁漫天堂密钥一致 → 切分方法正确。

### 通用

| 脚本 | 用途 |
|---|---|
| `_lits.py` | 抽取任意 blutter 反汇编文件的字符串池字面量 |
| `_hgsp_strings.py` | 同上，hgsp 专用快捷入口 |
| `_intel.py` | 由解密后的 splash/home JSON 生成情报表 |
| `crack_muse_key.py` | 早期密钥破解探索脚本（保留备查） |

## 三、使用前提

- so 反汇编产物：`C:\Users\Administrator\Downloads\DPK\_apk\blutter_out\asm\`
- so 本体：`C:\Users\Administrator\Downloads\DPK\_apk\libdir\libapp.so`（11,273,104 B，与 muse.apk 内一致）
- 抓包数据：`C:\Users\Administrator\Downloads\暮色逆向\暮色逆向_*\`
  （目录名为 GBK 误判为 UTF-8 的乱码，脚本统一用 `os.walk` 遍历，不硬编码路径）
- 真机配置：`C:\Users\Administrator\Downloads\暮色逆向\_muse\com.look.avbox.plist`

## 四、APK 身份

```
包名       : com.look.mbox
versionName: 1.0.1
versionCode: 101
MainActivity: com.look.avbox.MainActivity
```
