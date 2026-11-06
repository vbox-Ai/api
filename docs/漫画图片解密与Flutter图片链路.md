# 漫画图片解密 & Flutter 图片链路（2026-11-06 修复记录）

> 触发：用户反馈「嘿嘿连载、迷妹漫画不加载图片和封面图；漫蛙漫画加载部分封面图，图片不加载」

---

## 一、根因（两个，互相独立）

### 1. Flutter 客户端**没有** `/proxy?do=py` 路由

- iOS（`vbox/Services/DoubanImageProxyServer.swift`）实现了 `routePythonProxy` → 调 Python 的 `localProxy()`；
- **Flutter 端全仓没有 `do=py`**（`grep -r "do=py" lib/` 为空），18080 端口只跑 Go 代理（`/quark-stream`、`/spider/push` 等）。

⇒ 我们之前在 `mdtv / javdb / kpsp / hhlz` 里把封面改写成
`http://127.0.0.1:18080/proxy?do=py&key=xxx_py&url=…`
**在 App 内一律 404**，封面必然空白。这是上一轮"封面修复"引入的回归。

**已修**：四个适配器的 `_px()` 全部改回**直连**（保留方法签名，内部直接 `return u`）。

### 2. 这些平台的图片本身是**密文**

直接抓回来的字节熵很高、无 RIFF/JPEG/PNG 魔术字。客户端在
`images/decrypt_image_byte.dart::decryptImage`（@0xa41748）里按 **module 路径**分派解密：

| 分支 | 参数（asm 地址） | 状态 |
|---|---|---|
| 默认（`/module/hhlz`、`hdb`、`zlt` 等） | AES-128-CBC `key=saIZXc4yMvq0Iz56` `iv=kbJYtBJUECT0oyjo`（@0xa41bd4 / @0xa41be8） | ✅ 已复现，hhlz 验证通过（解出 RIFF/WEBP） |
| `/module/mw`（`my2ecret782ecret`，@0xa41dd8/@0xa41dec，key=iv） | AES-128-CBC `key=iv=my2ecret782ecret` | ✅ 已复现，mw 验证通过（解出 WEBP） |
| `/module/91sp` | `Jui7X#cdleN^3eZb`（@0xa4186c） | 未验 |
| 其它 | `2019ysapp7527`、`f5d965df75336270/97b60394abc2fbe1`、`525202f9149e061d` | 未验 |
| `mmmh` | `MmMhAnimImg` + `MmMhChain`（`mi2siQgcLREck`）链式，暂未破 | ❌ 待攻 |

## 二、交付方式：`data:` 内联

Flutter 漫画阅读器 `welfare_comic_reader_page.dart::_downloadImage` **支持 `data:`**：

```dart
if (parsed.url.startsWith('data:')) { … base64Decode(…); return …; }
```

所以适配器在 Python 侧完成「抓取 → AES 解密 → base64」，把
`data:image/webp;base64,…` 直接塞进 `manga://…&&…`，客户端零网络、零解码成本。

## 三、性能与兜底（客户端 20s 总预算）

| 平台 | 图片数 | 内联后体积 | 耗时（本地） |
|---|---|---|---|
| hhlz | 28 | 3.17 MB | 1.6 s |
| mw | 41 | 2.59 MB | 10.4 s（16 并发） |

- 并发 16 线程抓取；
- **14s 硬截止**：超过预算的图片回落原地址（不会整次超时把详情/播放打成失败）。

## 四、附带修正

| 问题 | 处理 |
|---|---|
| `mmmh` 注册成 `comic`，但它下发的是 **m3u8 视频**（`playerContent` 返回 HLS 直链）→ 客户端走图片阅读器必然"未解析到套图图片" | 注册分类改回 **video**（已重新注册 `mmmh_py`） |
| `hhlz` host 指向 `snen24.com`（INSAV 的域名） | 已在 `muse_avbox.py` 改为 `rrs0a03ak.pye57rf.com`（上一轮） |
| `mw` 封面本身是**真 JPEG**（只是 `?v=` 参数），可以直接显示 | 保持直连，不做内联 |

## 五、待办

1. `mmmh` 的图片链式解密（`MmMhAnimImg` + `MmMhChain`）—— 破了之后 mmmh 封面才能出；
2. 其余分支参数（`91sp` / `jmtt` / `4hu` / `one` …）按需复用同一套 `data:` 内联管线；
3. 若客户端后续补齐 `/proxy?do=py`（Flutter 侧），可切回代理以节省带宽。
