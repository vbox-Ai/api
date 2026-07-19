# vbox 远程默认源配置仓库模板

这个目录用于复制到公开仓库 `https://github.com/vbox-Ai/api`。

App 默认入口：

```text
https://raw.githubusercontent.com/vbox-Ai/api/main/sources/manifest.json
```

## 目录说明

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
  extract_domains.py     自动提取 sources 目录中的 URL 和域名
  check_domains.py       自动检测域名状态并生成报告
  domains.json           自动生成
  domains.txt            自动生成
  check-results.json     自动生成
  check-results.md       自动生成
```

## 邮件报告

如需每周自动发送检测报告，请在仓库 `Settings -> Secrets and variables -> Actions` 添加：

```text
SMTP_SERVER
SMTP_PORT
SMTP_USERNAME
SMTP_PASSWORD
MAIL_TO
```

QQ 邮箱的 `SMTP_PASSWORD` 应填写授权码，不是登录密码。

## 注意

- 标准 JSON 不支持 `//` 注释，所以每个 JSON 文件用 `_meta` 字段说明当前文件类型。
- 福利平台入口不做远程源控制；只允许通过 `domain_overrides.json` 覆盖域名。
- 用户自定义源、用户订阅、自定义解析器和切片源不受远程默认源覆盖。
