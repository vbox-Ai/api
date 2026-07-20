# vbox-Ai/api 远程默认源仓库配置设置说明

## 仓库用途

`vbox-Ai/api` 是 `vbox-ios` 的远程默认源配置仓库。App 启动后会读取 `manifest.json`，再根据 manifest 里的地址加载 API 源、网盘源、JS/站源、域名覆盖、解析器和禁用列表。

当前推荐入口：

```text
https://raw.githubusercontent.com/vbox-Ai/api/main/sources/manifest.json
```

如果 GitHub Pages 可用，后期可以切换为：

```text
https://vbox-ai.github.io/api/sources/manifest.json
```

## 当前文件结构

```text
sources/
  manifest.json          远程默认源入口
  api_sources.json       API 采集源
  cloud_sources.json     网盘搜索源
  spider_sources.json    JS 蜘蛛和站源
  domain_overrides.json  域名覆盖
  parsers.json           解析器和切片源
  disabled_sources.json  禁用源

domain-monitor/
  extract_domains.py     自动提取 sources 里的 URL 和域名
  check_domains.py       自动检测域名状态
  domains.json           自动生成的详细域名列表
  domains.txt            自动生成的纯域名列表
  check-results.json     Actions 自动生成的检测结果，作为 artifact 保存
  check-results.md       Actions 自动生成的检测报告，作为 artifact 保存并可发送邮件

.github/workflows/
  check-domains.yml      每周检测、手动检测、配置变化自动检测
```

## 必须开启的设置

### Actions 权限

当前检测脚本会把结果上传为 GitHub Actions artifact，不再强制提交回仓库。

设置路径：

```text
Settings → Actions → General → Workflow permissions
```

推荐选择：

```text
Read repository contents permission
```

如果你后续希望重新把检测结果自动提交回仓库，可以再改成：

```text
Read and write permissions
```

然后点击：

```text
Save
```

### 邮件 Secrets

如果需要每周自动发送检测报告，需要设置仓库 Secrets。

设置路径：

```text
Settings → Secrets and variables → Actions → New repository secret
```

需要添加：

```text
SMTP_SERVER
SMTP_PORT
SMTP_USERNAME
SMTP_PASSWORD
MAIL_TO
```

QQ 邮箱示例：

```text
SMTP_SERVER=smtp.qq.com
SMTP_PORT=465
SMTP_USERNAME=你的QQ邮箱@qq.com
SMTP_PASSWORD=QQ邮箱授权码
MAIL_TO=接收报告的邮箱
```

`SMTP_PASSWORD` 必须是邮箱授权码，不是登录密码。

## Actions 触发规则

当前 `check-domains.yml` 支持三种触发方式。

### 每周自动检测

```yaml
schedule:
  - cron: "0 18 * * 0"
```

大约对应北京时间每周一凌晨 2 点。

### 手动检测

在 GitHub 页面：

```text
Actions → Check Source Domains → Run workflow
```

点击即可手动跑一次。

### 配置变化自动检测

当以下文件变化并推送到 `main` 时，会自动运行 Actions：

```text
sources/**
domain-monitor/extract_domains.py
domain-monitor/check_domains.py
.github/workflows/check-domains.yml
README.md
docs/**
```

检测结果文件不会提交回仓库，默认在 Actions 运行详情页的 artifact 中下载；如果配置了 SMTP Secrets，也会发送到邮箱。

## GitHub Pages

GitHub Pages 可选，不是必须。

不开 Pages 时，App 用 raw 地址：

```text
https://raw.githubusercontent.com/vbox-Ai/api/main/sources/manifest.json
```

开启 Pages 后，可以使用：

```text
https://vbox-ai.github.io/api/sources/manifest.json
```

如果 Pages 地址访问 404，请检查：

```text
Settings → Pages
Source: Deploy from a branch
Branch: main
Folder: / (root)
```

首次开启后可能需要等几分钟。

## 源文件维护规则

### `manifest.json`

每次修改远程源配置后建议更新：

```text
configVersion
updatedAt
```

App 通过 `configVersion` 判断当前配置版本。

### `api_sources.json`

用于存放 API 采集源，后期替代：

```text
ibox_sources.json
SpiderManager.builtinFallbackSites
```

### `cloud_sources.json`

用于存放网盘搜索源，后期替代：

```text
video_sources.json
```

### `spider_sources.json`

用于存放 JS 蜘蛛和站源。当前可以先留空，后期再从 `default_subscribe.json` 分阶段迁移。

### `domain_overrides.json`

用于替换失效域名。福利平台只使用这里做域名覆盖，不通过远程源控制平台显示。

### `parsers.json`

用于远程默认解析器和切片源。用户自定义解析器优先级高于这里的远程默认解析器。

### `disabled_sources.json`

用于临时禁用失效源或域名，不影响用户自定义源。

## 当前还需要人工确认

1. `Settings → Actions → General` 是否已经开启 `Read and write permissions`
2. 邮件 Secrets 是否已设置
3. GitHub Pages 地址是否能访问
4. App 默认地址最终使用 raw 还是 Pages
5. 后续是否把 `ibox_sources.json`、`video_sources.json` 的全部真实源迁入远程仓库

## 安全提醒

不要把 GitHub token、邮箱授权码、cookie、网盘 token 写入仓库文件。

如果 token 已经发到聊天或提交记录中，请立即撤销并重新生成。
