# one 平台 token 管理说明

> 2026-11-02 攻坚结论

## 一、为什么不能自动刷新

三条路都堵死了，逐个说清楚：

| 途径 | 结论 | 证据 |
|---|---|---|
| 客户端内登录/注册接口 | **不存在** | `avbox/module/one/` 全量反汇编，只有 7 个业务接口，无任何 auth 路径 |
| one 服务端 visitor 接口 | **不存在** | `v2.5/user/visitor` 与随机路径返回完全相同的 `500 系统繁忙`，属统一兜底 |
| 6868 主后端 splash | **被加固** | 正确 `time`+`uuid` 仍返回 `{"code":400,"msg":"违规请求"}` |

所以 token 只能**人工获取后喂入**。这是客观约束，不是没做。

## 二、token 从哪来

三个来源，按可靠性排序：

1. **真机抓包**（最可靠）
   - Android：HttpCanary / Reqable 抓一次 App 启动
   - iOS：FLEX 抓 `6868 /box/api/splash`
   - 取 `data.token[]` 中 `name == "token_one"` 的 `token` 字段

2. **真机 plist**
   - 路径：`Library/Preferences/com.look.avbox.plist`
   - 键名：`flutter.token_one`

3. **已解密的历史资产**（会过期）
   - `tools/_dec/box_api_splash.json` → `token_one`
   - 当前这份 exp=1793574000（2026-11-02 07:00）

## 三、怎么用

```bash
# 只看当前内置 token 状态
python tools/one_token_tool.py check

# 验证一个 token 是否可用（不写入）
python tools/one_token_tool.py verify eyJ0eXAi...

# 验证通过后写入 muse_avbox.py
python tools/one_token_tool.py patch eyJ0eXAi...

# 从已解密的 splash 资产取（会自动验证，过期则拒绝）
python tools/one_token_tool.py from-splash
```

`patch` 会同时更新 `OneAdapter.UUID`（从 JWT payload 自动提取），
因为 UUID 必须与 token 匹配，否则签名校验失败。

## 四、运行时注入（不改代码）

脚本支持三种优先级：`extend` > 环境变量 > 内置常量。

```json
// 客户端福利平台配置的 extend 字段
{"one_token": "eyJ0eXAi...", "one_uuid": "xxxx-xxxx"}
```

或环境变量：

```bash
set ONE_TOKEN=eyJ0eXAi...
set ONE_UUID=da23a300-cebf-11f1-9be0-2b844569af39
```

## 五、失效时的表现

适配器首次请求会做一次**真实探活**（调一次 `getDemandTagList`）：

- token 可用 → `code:200`，正常返回
- token 失效 → 服务端 `HTTP 401`，适配器写一条 `ERROR` 日志：
  ```
  one: token 不可用（本地判断 已过期，剩余 -1.2 小时）。
  请更新 OneAdapter.TOKEN 或在 extend 中传 one_token。
  ```
- 不会静默返回空列表，避免"平台看起来挂了"的误判

## 六、踩过的坑（重要）

### 坑 1：`user-key` 空值头必须发送

```
不带 user-key 头      -> {"code":401,"message":"缺少用户码参数！请清理APP缓存后重新打开APP"}
带 user-key: （空值） -> 正常返回加密数据
```

**urllib 会发送 `user-key: `，curl 会丢弃空值头。** 这就是为什么用 curl 调试
怎么都过不去、而适配器却能取到数据。排查这类问题时优先怀疑空值头。

### 坑 2：签名用的 uuid 必须是 token 里的那个

反汇编里硬编码了 visitor 的 uuid `9b1a29f0-...`，但那是 visitor 分支用的。
正式 token 必须用自己 payload 里的 `uuid`，否则：

```
{"code":401,"message":"API 签名不正确，授权失败！"}
```

### 坑 3：URL 双斜杠

适配器拼出的 URL 是 `https://api.3459381.com//v2.5/...`（双斜杠），
服务端接受。不要"顺手修正"成单斜杠，行为需要用实测确认。

### 坑 4：one 的 500 是兜底，不代表路由存在

```
v2.5/user/visitor  -> 500 系统繁忙
随机不存在的路径    -> 500 系统繁忙      ← 一模一样
```

看到 500 就以为"路由存在、参数不对"会走错方向。必须用**对照实验**（已知不存在路径）
才能判断。

## 七、签名链（备查）

```
sign = MD5( MD5("0.0.0.0.3." + timestamp + ".." + uuid) + "m4n2hjPeYWkD6tFpqKF^3HO^h24P@idT" )
正文加解密：AES-128-CBC(key="l*bv%Ziq000Biaog", iv="8597506002939249")
请求头：User-Agent / ip=0.0.0.0 / uuid / Content-Type=x-www-form-urlencoded
        / timestamp / platform=3 / token / sign / user-key=空 / app-version=2.6.4
```
