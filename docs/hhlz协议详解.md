# 嘿嘿连载（hhlz）协议详解 —— 抓包 + 反汇编双证据

> 更新时间：2026-11-06 08:40（北京时间）
> 状态：**分类 / 列表 / 详情 / 播放 四能力全通**，注册键 `hhlz_py`（`category=comic`）
> 适配器：`sources/welfare-js/hhlz.py` · host `https://rrs0a03ak.pye57rf.com`

---

## 一、来源

| 证据 | 位置 | 说明 |
|---|---|---|
| 抓包 | 桌面 `暮色抓包暮色抓包/归档.zip` → `2026-10-29-052251/64` | `POST /comic/list` 明文请求体 + 加密响应 |
| 反汇编 | `module/hhlz/network/interceptor.dart` | `onRequest` @0x8de210；`onResponse` @0x8f1548 |

> 此前 `hhlz` 被判为"站点已死"（那个 `https://snen24.com` 是 muse 表里的占位域名，实际是 INSAV 的）。
> 抓包给出了真域名 `rrs0a03ak.pye57rf.com`。

## 二、请求

所有接口都是 `POST`，`Content-Type: application/json`，**每个请求都带同一套设备参数**：

```json
{
  "appId": "1", "debug": "1", "osType": "3", "product": "1", "ver": "6.0.1",
  "marketChannel": "LDY", "sign": "d01ef895544ab4f2a1f4d38d66edb283",
  "sysVer": "13", "proxyChannel": "LDY",
  "packageName": "com.t55f8907c5.z222ec9ed4.vcd6814de920260901",
  "time": 1793222660, "phoneModel": "NX729J",
  "udid": "00867d34-62ad-3de6-b203-186d92fe0876",
  …业务参数
}
```

**`sign` 不用算 —— 它是硬编码常量**（asm 里直接 `r3 = "d01ef895…"` 写死，抓包里也一模一样）。
`udid` 任意 uuid4 均可，`time` 秒级。

## 三、响应

```json
{"code":0,"msg":"success","data":"<base64>","cimg":"1","capi":"1"}
```

```
data = base64( AES-128-CBC(JSON, key="D2o4XyQeIFobJ4tS", iv="sciCuBC7orQtDhTO") )
```

`code`：`0` 成功；`101` 参数无效（缺 osType 等）；`702` 参数缺失（如 `/comic/chapter` 缺 comic_id）。

## 四、接口

| 接口 | 参数 | 返回 |
|---|---|---|
| `/comic/list` | `cat`、`page_num` | `search_box[]`（分类树）+ `list{total_page,current_page,page_size:12,total_count:383047,list[]}` |
| `/cartoon/info` | `comic_id` | `comic{name,cover,author,total_chapters,is_finish,tag,description…}` |
| `/comic/catalog` | `comic_id` | `chapter_list[{chapter_id,subtitle,display_order,is_vip…}]` |
| `/comic/chapter` | **`comic_id` + `chapter_id`** | `image_list[{img,width,height}]`（webp，带 `$w960` 尺寸标记） |

列表项字段：`comic_id / name / cover / vertical_cover / author / total_chapters /
is_vip / is_finish / total_views / tag`。

## 五、播放（漫画约定）

`/comic/chapter` 的 `image_list[].img` 直接给整章图片，按 vbox 漫画约定输出：

```
vod_play_url  = "章节名$<comic_id>|<chapter_id>#…"
playerContent → "manga://" + "&&".join(images)
```

客户端会渲染成图片阅读器（与 `mw` / `mmmh` / `lclf` 同一口径）。

## 六、坑

| # | 坑 | 正解 |
|---|---|---|
| 1 | 以为要算 `sign` | 是常量，抄下来即可 |
| 2 | `/comic/chapter` 只给 chapter_id | 必须同时给 `comic_id`，否则 `code=702` |
| 3 | 响应直接 json 解 | 先按 `Accept-Encoding: gzip` 解压，再解 `data` 的 base64 |
| 4 | 按 muse 表用 `snen24.com` | 那是 INSAV 的域名；hhlz 用抓包里的 `rrs0a03ak.pye57rf.com` |
| 5 | `homeContent` 联网 | 静态分类（客户端 20s 总预算，坑表 #25） |

## 七、验证

```
$ python tools/_smoke_standalone.py hhlz
hhlz   ✓14   ✓12   ✓1   ✓

播放 → manga://https://enimages52.bole573.com/…001$w960.webp&&…（28 张）
localProxy → 200 image/webp 19728B
```

探测脚本：`tools/_hhlz_r1.py`（信封验证）、`_hhlz_r2.py`（解 data）、`_hhlz_r3.py`（详情/目录）、`_hhlz_r4.py`（章节图）。
