# JavDB（javdb）协议详解 —— 三能力 + 官方试看

> 更新时间：2026-11-03 19:05（北京时间）
> 状态：**分类 / 列表 / 详情 三能力全通 + 官方 720p 试看播放**；正片需登录 + VIP
> 适配器：`sources/welfare-js/javdb.py` · 注册键 `javdb_py` · host `https://jdforrepam.com`

---

## 一、签名（`JavDbInterceptor::onRequest` @0x8df080，全函数仅 30 余条指令）

```
ts    = int(time.time())                                  ← 秒（micros/1000/1000，两次 sdiv）
first = MD5( f"{ts}{SECRET}" )
header accept-language = "zh"
header jdsignature     = f"{ts}.lpw6vgqzsp.{first}"
```

`SECRET` 不是常量池里的字面量，而是构造 `JavDbInterceptor` 时写入 `field_7` 的实参
（`service.dart` @0x7b9fa8）：

```
71cf27bb3c0bcdf207b64abecddc970098c7421ee7203b9cdae54478478a199e7d5a6e1a57691123c1a931c057842fb73ba3b3c83bcd69c17ccf174081e3d8aa
```

> 上一版情报卡在「需 jdsignature，asm 有 `.lpw6vgqzsp.` 线索」——线索是对的，
> 它是签名**中间段的固定字面量**，密钥在构造处而不在常量池。

## 二、接口

| 接口 | 参数 | 说明 |
|---|---|---|
| `GET api/v1/movies/latest` | `page` | 最新，10 条/页 |
| `GET api/v1/movies/tags` | `filter_by=tag&page` | 标签流 |
| `GET api/v2/search` | `q&page` | 搜索 |
| `GET api/v4/movies/{id}` | — | 详情（`data.movie`） |
| `GET api/v1/actors` | `type=all&page` | 演员（本轮未接入 UI） |
| `api/v2/tags` / `api/v1/makers` | 需 `type` | 枚举取值全 500，暂不可用 |

错误语义（很好用，可直接当"参数发现器"）：

| 返回 | 含义 |
|---|---|
| `{"status":404}` | 路径不存在 |
| `{"success":0,"action":"ParameterInvalid","message":"參數不能爲空: filter_by"}` | 路径对，缺参数 |
| `{"success":0,"action":"JWTVerificationError"}` | 路径对，需登录 |
| `{"success":1,...}` | 命中 |

## 三、播放

- 列表项：`can_play` 恒 false（匿名态）；`has_preview_video` 标记有试看。
- 详情 `data.movie.play_sources` = `[]`（正片需登录 + VIP，`show_vip_banner=true`）。
- **可播的是官方试看**：`data.movie.preview_video_url` =
  `https://jdforrepam.com/api/v1/movies/ttm3u8/preview/<n>/0/720p.m3u8?sign=…&t=…`
  （`sign`/`t` 由服务端签发，直取可播，无需额外头）。

适配器把试看放进 `vod_play_url`（`试看$<url>`），正片留空 —— 与 rryy/mmmh 的"能力受限"口径一致。

## 四、踩坑

| # | 坑 | 正解 |
|---|---|---|
| 1 | 用毫秒签名 | **秒**（两次 `sdiv 1000`） |
| 2 | 把 `.lpw6vgqzsp.` 当密钥 | 它是签名中间段字面量，密钥在 `service.dart` 构造实参里 |
| 3 | `api/v1/movies/{id}` 详情 | 该路径 404，详情是 **`api/v4/movies/{id}`** |
| 4 | `homeContent` 联网 | 客户端总预算 20s → 静态分类（见交接文档坑表 #25） |

## 五、验证

```
$ python tools/_smoke_standalone.py javdb
javdb  ✓2   ✓10   ✓1   ✓

播放 → 试看$https://jdforrepam.com/api/v1/movies/ttm3u8/preview/415011/0/720p.m3u8?sign=…&t=…
```

探测脚本：`tools/_javdb_r1.py`（签名验证）、`_javdb_r2.py`（参数取值发现）、`_javdb_r3.py`（详情/播放定位）。
