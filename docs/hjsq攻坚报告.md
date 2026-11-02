# hjsq 海角社区 · 攻坚报告

> 完成时间：2026-11-02 23:10（北京时间）
> 结论：**全链路打通** —— 分类 / 列表 / 详情 / 搜索 / 视频播放 / 图片解码 全部出真实数据
> 适配器：`sources/welfare-js/hjsq.py`（自包含，零外部依赖）
> 平台注册：`welfare_platforms.json` + `all_sources.json` → `hjsq_py`

---

## 一、情报来源

| 项 | 位置 |
|---|---|
| 域名 | `http://23.225.145.74`（SpUtil 键 `hjsq`，splash 下发） |
| token | `b2dc730bf54441f18492061ce80659b3`（SpUtil 键 `token_hjsq`） |
| 反汇编源码 | `DPK\_apk\blutter_out\asm\avbox\module\hjsq\*`（15 个 .dart 文件） |
| 关键文件 | `network/service.dart`（HTTP 封装）、`network/interceptor.dart`（鉴权头）、`bean/topic_vo.dart`、`bean/video_vo.dart` |

此前 `docs/暮色52平台接口侦察报告.md` 把 hjsq 记为「nginx 默认页」，根因是**根路径确实只配了 nginx 欢迎页**，业务全在 `api2/` 前缀下。与反爬无关。

---

## 二、鉴权头（静态硬编码，非动态签名）

`HjSqInterceptor::onRequest`（addr 0x8de5b0）只有两个动作：

```
X-User-Id    : "171299991201"        ← 字符串常量，直接写在代码里
X-User-Token : SpUtil.getString("token_hjsq")
```

- **没有签名、没有时间戳、没有 nonce、没有加密**。这与 hxsp / hgsp 那类 HMAC 链完全是两个难度层级。
- `X-User-Id` 是**固定的游客 ID**，全站共用。
- 游客 token 足以读取全站公开帖子（列表 / 详情 / 搜索）。

---

## 三、响应信封

```json
{"errorCode": 0, "message": "", "success": true, "data": {...}}
```

| 方法 | 取值键 | 说明 |
|---|---|---|
| GET | `data` | 正常业务体 |
| POST | `response` | 仅 `api2/attachment` 用 |
| 失败 | `errorCode != 0` | 同时带 `message` |

> `HjSqHttp.get` 内部逻辑：先取 `errorCode`，等于 0 才取 `data` 走 parser，否则取 `message` 构造 `ApiFailure`。

---

## 四、接口全表（实测状态）

| 用途 | 方法 | 路径 | 参数 | 实测 |
|---|---|---|---|---|
| 节点树 | GET | `api2/topic/nodes` | — | ✅ 137 条 |
| 节点帖子 | GET | `api2/topic/node/topics` | `page` `nodeId` `type` | ✅ |
| 热帖 | GET | `api2/topic/hot/topics` | `page` | ✅ total 1000 |
| 新闻 | GET | `api2/topic/node/news` | `page` | ✅ total 900 |
| 最新 | GET | `api2/topic/node/topics` | `type=1` | ✅ total 10000 |
| 精华 | GET | `api2/topic/node/topics` | `type=3` | ✅ total 5757 |
| 原创 | GET | `api2/topic/node/topics` | `type=7` | ✅ total 7555 |
| 详情 | GET | `api2/topic/{topicId}` | 路径插值 | ✅ |
| 搜索 | GET | `api2/topic/search` | `node_id=0` `keyword` | ✅ |
| 视频流 | GET | `api2/video/node_list` | `pageIndex` `type` `orderType` | ❌ `请先登录` |
| 用户视频 | GET | `api2/video/user_list` | — | ❌ 需登录 |
| 播放解析 | POST | `api2/attachment` | `id` `resource_type` `resource_id` | ⚠ 图片帖恒 `errorCode=1`；视频直链已在详情里，用不上 |

### 分页语义

`data.page = {page, limit:20, total}`，`page` 从 1 起。热帖 / 新闻 / 节点列表都支持 `page` 翻页（已验证 pg1 与 pg2 内容不同）。

### 节点树结构

`api2/topic/nodes` 返回**扁平 137 条**，无 `children` 字段，靠 `parentId` 组层级：

```
parentId == 0  → 顶级板块（短视频专区 900 / 热门 888 / 大事记 16 / 福利姬 999 / 讨论 24 / 头条 1 / 专区 2000 …）
parentId != 0  → 挂在父板块下的子版块
```

实测各节点帖量：

| nodeId | 名称 | total |
|---|---|---|
| 888 | 热门 | 10006 |
| 24 | 讨论 | 10000 |
| 2000 | 专区 | 10000 |
| 1001 | 收费视频 | 7388 |
| 999 | 福利姬 | 1030 |
| 1 | 头条 | 900 |
| 300 | 海角认证 | 146 |
| 16 | 大事记 | 11 |
| 900 | 短视频专区 | **0（平台侧真空）** |

---

## 五、Topic / Video 字段结构（VO 还原）

`Topic.fromJson`（0x7db8f4）解析出的完整字段：

```
topicId     int          user      {id, avatar, nickname, vip, certified, famous, title{id,name,icon}}
node        {nodeId, parentId, name, icon, description, vipLimit, external_url}
tags        [{tagId, tagName}]
title       String
type        int          money_type int      （0 免费 / 1、2 付费）
liteContent String       content   [{type, text, imgUrl, videoUrl, audioUrl}]
                  type: "1"=纯文本  "2"=图片  ...
doors       [{id, type, title, img_url}]      ← 付费门
attachments [{id, category, remoteUrl, coverUrl, video_time_length}]
createTime  viewCount  likeCount  commentCount
hasVideo / hasPic / hasAudio   bool
is_original / is_cream / is_hot / is_top
currentUserPurchased  sale  reward  remarks  status
```

---

## 六、视频直链（零破解，明文下发）

**关键发现：播放地址根本不需要 `POST api2/attachment` 去换，详情响应里就已经是完整直链。**

```json
{
  "id": 14386723,
  "category": "video",
  "remoteUrl": "https://0ts10.hj260302818.top/hjstore/video/20261101/b5cfbcae…/571842_i_preview.m3u8",
  "coverUrl": "https://pic.hj260302818.top/hjstore/video/20261101/b5cfbcae…/571842.jpeg.txt",
  "video_time_length": 697
}
```

播放链路实测：

```
GET  …/571842_i_preview.m3u8   → 200  audio/x-mpegurl  1470 字节
     #EXT-X-KEY:METHOD=AES-128,URI="enc_14386723.key",IV=0x826ad24a…
     24 个 .ts 分片
GET  …/enc_14386723.key        → 200  16 字节  25ae9037f3a047f9d65be8f1bd3bc303
GET  …/c223baf8….ts            → 200  （AES-128 密文分片）
```

- 标准 HLS + AES-128，**key 明文同目录可取、无需鉴权**，任何 HLS 播放器直接吃。
- `_preview` 后缀的帖多为付费内容（`money_type>0`），免费帖为完整源。
- `video_time_length` 单位秒，适配器已换算成 `正片 11:37` 形式。

---

## 七、图片加密（本次唯一需要破解的部分）

### 现象

`attachments[category=images].remoteUrl` 形如：

```
https://pic.hj260302818.top/hjstore/images/20261102/3b8756537400d11c9d4c38e5034feb5a.jpg.txt
```

- 请求返回 `Content-Type: text/plain`，**不是图片**
- 去掉 `.txt` 直接取 `.jpg` → **403 Forbidden**
- 正文首字节：`#FEyXSnnZVEl#R8oa…`，138,448 字节

### 破解过程（三次假设迭代）

| 轮次 | 假设 | 结果 |
|---|---|---|
| 1 | 标准 base64 + `*`/`#` 简单替换 | ❌ 无图片魔数 |
| 2 | 逐位加法密码 + 周期密钥（利用 16 字符重复块） | ❌ 残基约束下无任何位移可行 |
| 3 | 去二进制搜字母表 | ✅ **命中** |

第 2 轮失败的根因值得记一笔：`TzoRWjMYij4SVnIc` 这个 16 字符重复块极易被误判成「周期密钥打出的零填充区」，但实际它是解码后 `data:image` 前缀附近的结构性重复，把人引向错误方向。

### 正解

`libapp.so` 偏移 **651830** 处存在一个字面量（64 字符，互不重复）：

```
ABCD*EFGHIJKLMNOPQRSTUVWX#YZabcdefghijklmnopqrstuvwxyz1234567890
```

它是**自定义 base64 字母表**：`*` 顶替 `+`、`#` 顶替 `/`，但**位置被重排过**（`*` 在索引 4、`#` 在索引 25），所以按标准表做字符替换必然失败。

关键破局点：**`#FE` 不是魔数头，不能剥掉**。全文长度 138,448 恰好被 4 整除，而剥掉 3 字符后余 1 —— 这个 `len % 4 == 1` 就是「对齐错了」的信号。带上 `#FE` 解码，首 4 字符 `#FEy` 正好解出 `dat`。

### 完整链路

```
.txt 正文
  → 按 ALPH64 查表得 6-bit 值 → 拼字节
  → "data:image/jpeg;base64,/9j/2wCEAAgG…"
  → 取逗号后部分 → 标准 base64 解码
  → JPEG（FFD8FFDB，1080×1440，77,858 字节）
```

实测产物：`tools/_dec/hjsq_img_decoded.jpg`，肉眼确认是真实照片（带「海角社区 haijiao.com」水印）。

### 落地方式

客户端无法直连渲染 `.txt`，适配器内置 `localProxy` 做**实时解码**：

```
vod_pic = http://127.0.0.1:9978/proxy?do=py&type=hjsq&url=<urlencode(.txt 地址)>
```

`pic` 模式可在 `extend` 里切换：`proxy`（默认，出真图）/ `raw`（直连 .txt，不渲染）/ `none`（不出图）。

另注：列表接口里图片另有 `_mini.jpg.txt` 缩略图变体，解码方式完全相同。

---

## 八、适配器设计

`sources/welfare-js/hjsq.py`，**自包含**（满足硬约束：客户端只下载单个 .py）：

| 方法 | 实现 |
|---|---|
| `homeContent` | 5 个固定栏目（热帖/新闻/最新/精华/原创）+ 顶级节点；子版块挂进 `filters.node` |
| `categoryContent` | `hot`/`news`/`new`/`cream`/`original` 走特殊分支；其余按 `nodeId`；`extend.node` 可切子版块 |
| `detailContent` | `api2/topic/{id}`；正文拼 `content[].text`；`video_time_length` 换算成 `正片 m:ss`；纯图帖把图片作为可播资源（走代理） |
| `searchContent` | `api2/topic/search`；该接口不分页，`pg>1` 返回空以避免客户端无限翻页 |
| `playerContent` | `parse:0` + m3u8 直链 + UA/Referer |
| `localProxy` | 拉 `.txt` → `decode_img_bytes` → 输出 `image/jpeg`，带 1 天缓存头 |

内置容错：
- `_open()` 先走默认 opener，失败再**显式绕代理**重试（本机常见全局代理环境变量）
- 节点树 30 分钟缓存
- `hj64decode` 忽略表外字符；`decode_img_bytes` 兼容「已是明文 data URI」和「已是裸 JPEG」两种远端变化

---

## 九、实测结果

`tools/_smoke_hjsq.py` → **PASS 15 / 15**

```
[OK] homeContent                    分类 130+，含 5 固定栏目
[OK] category hot/news/new/cream/original    全部出数据
[OK] category 900 pg1/pg2           平台真空节点，按 total=0 正常处理
[OK] pagination hot                 pg1 与 pg2 首条不同
[OK] detail 视频帖 2304257          play_url = 正片 11:37$…m3u8
[OK] detail 图帖 2304720            play_url = 图1$proxy…
[OK] search "自拍"                  命中
[OK] localProxy decode              200 image/jpeg 72,588 字节 ffd8ffdb
[OK] playerContent                  parse=0，m3u8
[OK] HLS+AES key                    24 分片，key 16 字节
```

---

## 十、踩坑清单

| # | 坑 | 现象 | 正解 |
|---|---|---|---|
| 1 | 根路径误判 | `/` 返回 nginx 欢迎页，被记为「未配置」 | 业务全在 `api2/` 前缀下 |
| 2 | `X-User-Id` 被忽略 | 只带 token 也能通，容易以为不需要 | 两者都要发，ID 是静态硬编码 |
| 3 | 想用 `POST api2/attachment` 换播放地址 | 图片帖恒 `errorCode=1` 且 `message` 为空 | 视频直链**已在详情** `attachments[].remoteUrl` |
| 4 | 节点树当树解析 | 137 条全是平级、无 `children` | 按 `parentId` 自行组层级 |
| 5 | `#FE` 当魔数头剥掉 | 长度 `%4==1`，解出乱码 | **不能剥**，它是 base64 流的一部分 |
| 6 | 按标准表替换 `*`→`+`、`#`→`/` | 无图片魔数 | 字母表**被重排**，必须整表查索引 |
| 7 | 16 字符重复块误导 | 误判为周期密钥的零填充 | 实际是解码后 `data:image` 附近的结构重复 |
| 8 | 空节点当故障 | nodeId=900 返回空 | 平台侧 `total=0` 属正常，判据要看 total |
| 9 | 搜索接口当分页接口 | `pg>1` 仍返回同一批 | 接口不分页，本地切片 |
| 10 | `api2/video/node_list` 反复调参 | 任何参数组合都 `请先登录` | 需真实账号态，游客 token 无解；视频内容走节点/帖子里拿 |

---

## 十一、遗留

1. **`api2/video/node_list` / `api2/video/user_list`** 需真实登录态。游客 token 拿不到。若要打通，需真机抓一次登录后的 `token_hjsq`（会覆盖游客 token）。
2. **付费帖完整性**：`money_type>0` 的帖，`remoteUrl` 带 `_preview` 后缀，拿到的是预览片段。完整源需购买（`doors` 字段是付费门列表）。已尝试去掉 `_preview` 直取，未验证到完整源。
3. **`POST api2/attachment` 的正确入参**仍未确定（图片帖恒失败）。因视频直链已明文可得，该接口暂无必要继续投入。
