# AiJav（aijav）协议详解 —— 三能力已通，播放需账号

> 更新时间：2026-11-03 14:45（北京时间）
> 状态：**分类 / 列表 / 详情 三能力全通**（46 分类、54/页、总 18774 条）；**播放受限**（匿名态服务端不下发 m3u8）
> 适配器：`sources/welfare-js/aijav.py` · 注册键 `aijav_py` · host `https://newavapi.9xyrp3kg4b86.com`

---

## 一、为什么一轮就通

aijav 与 mdtv 是**同一套 encrypt 包胶水层**（`MdTvInterceptor` / `AijavInterceptor` 结构逐指令一致），
所以 mdtv 结案时总结的两条经验直接套用：

1. **逐行抄 `headers[...] = ...`**，别只抄 body 加密；
2. **常量回 `libapp.so` 取原始字节**，别信 blutter 注释里的转义。

两边的差异只有 4 个常量：

| 常量 | mdtv | aijav | 二进制偏移 |
|---|---|---|---|
| KEY（AES-256） | `Vq234zBeSdGgYXzVTEfnnjjdmaTkk7A4` | `0XxdjmI55ZjjqQLO3nI7gGqrBP0Vz9jS` | aijav @322372 |
| 请求 IV | `-p9B[~PnPsJGDZMX` | `RWf23muavYNWSdef` | @944669 |
| SECRET | `&m}q%ea6:LDcmS?aK)…` | `&NRkw0g3iJLDvw5tJ5PuVt5276z0SOuyL` | @500125 |
| 头 `suffix` | `JGDZMX` | `NWSdef` | @572092 |

**请求 IV = IV 前缀 + suffix 头值** 这个设计完全一致：
`"-p9B[~PnPs"+JGDZMX` / `"RWf23muavY"+NWSdef`；响应对应 `"-p9B[~PnPs"+响应suffix` / `"RWf23muavY"+响应suffix`。

> 上一版 `剩余21平台攻坚情报.md` 把 aijav 的 `REQ_KEY` 记成 16B 的 `RWf23muavYNWSdef`（当 AES-128 用）——那是 IV，不是 key。
> key 一直是 32B 的 `0Xxdjm…`，请求与响应共用。

## 二、请求 / 响应

```
请求  biz → biz["timestamp"]=毫秒 → 键排序 "k=v&k=v" → encode_sign=MD5(串+SECRET)
      → base64(AES-256-CBC(jsonEncode(biz), KEY, REQ_IV)) → body={"post-data":…}
      headers: Content-Type: application/json; suffix: NWSdef
响应  {"suffix":"<6hex>","data":"<b64>"} → iv=("RWf23muavY"+suffix)[:16] → AES-256-CBC → JSON
      信封 {"code":1,"msg":"操作成功","timestamp":…,"data":…}      ← **成功码 1，不是 0**
```

## 三、路由判据：`code 999` = 路由不存在

这是这轮最有价值的发现，比猜路径高效得多：

| 返回 | 含义 |
|---|---|
| `{"code":999,"msg":"网络异常，请稍候再试"}` | **路由不存在**（框架兜底） |
| `{"code":3001,"msg":"视频不存在"}` | 路由存在，业务参数对不上 |
| `{"code":2000,"msg":"登录已失效"}` | 路由存在，但需要登录 |
| `{"code":1,"msg":"操作成功"}` | 命中 |

靠这个判据扫 `{video,player,media,play,vod,app/video} × {play,url,m3u8,source,detail,info,…}` 共 186 条，
只有 3 条不是 999：`video/info`、`video/purchase`、`video/collect`。

## 四、接口清单

| 接口 | biz | 说明 |
|---|---|---|
| `video/lists` | `{page, limit:54, type:8}` | 首页/最新，总 18774 条，348 页 |
| `video/lists` | `{page, limit:40, tag_id:<id>}` | 标签分区（tag_id=10 → 1125 条） |
| `video/lists` | `{page, limit:40, actor_id:<id>}` | 演员（actor_id=5 → 4596 条） |
| `video/lists` | `{page, limit:40, publisher_id:<id>}` | 片商（publisher_id=1 → 193 条） |
| `video/lists` | `{page, limit, keyword}` | 搜索 |
| `video/info` | `{vid:<id>}` | **详情，参数名是 `vid`**（传 `id` 会 3001） |
| `tag/lists` | `{page, limit}` | 标签总表，580 个 |
| `actor/lists` | `{page, limit}` | 演员总表，6016 个 |
| `publisher/lists` | `{page, limit}` | 片商总表，280 个 |

`video/info` 返回字段：`id/title/mash/duration/publish_date/actor[]/publisher/tags[]/description/
rating_avg/rating_count/play/play_day/week/month/private/video_point/is_purchase/zimu{or,en,zh,…}/thumb/preview/panorama`。

## 五、播放为什么打不通（结论已定，不是没找到）

1. 列表项与 `video/info` 都**不含**任何媒体直链：只有 `thumb/preview/panorama` 图片与 `zimu` 字幕 vtt；
   `private`(2/3)、`video_point`、`is_purchase` 是购买/权益标记，匿名态恒 `is_purchase=0`。
2. 取流相关路由（`video/play|url|m3u8|source|stream|…`）全部 999 = **不存在**。
3. `video/purchase`、`video/collect` 返回 `2000 登录已失效` —— 这是有账号体系的付费点播站。
4. `libapp.so` 里确实存在 `m3u8_url` 这个 JSON 字段名，但只在购买后由服务端下发。

→ 与 `rryy`（播放需 VIP）同类。适配器如实交付三能力，`vod_play_url` 留空，避免客户端空起点播放器。

## 六、验证记录

```
$ python tools/_smoke_standalone.py aijav
aijav  ✓46   ✓54   ✓1   -          ← 播放列为 -（服务端不下发）

$ python tools/_gen_platform_table.py
总 31 / 平铺 12 / 出数据 11 / 四能力全通 11
```

探测脚本：`tools/_aijav_r1.py`（一次打通全接口）、`_aijav_r2.py`（取流路径枚举）、
`_aijav_r3.py`（`video/info` 参数名 = vid）、`_aijav_r4.py`（186 条路径按 999 判据扫）、
`_aijav_strbytes.py`（常量二进制取证）。

## 七、剩下的同类目标

`insav`（同家族，已死）之外，**`qysq`** 是本套胶水层的第三个同构目标（签名已全破，只差响应解密函数）；
`zlt`（驾照）、`javdb`（jdsignature）也都在同一 AOT 里，值得用「999/业务码区分路由」这套判据重扫。
