# 福利专区专用 Spider 脚本目录

此目录只用于存放 `welfare_platforms.json` 中 `serviceType: "welfare_spider"` 的福利专区专用脚本。

不要把这里的脚本加入 `spider_sources.json`，也不要把它们作为普通远程 JS Spider 源发布。福利 Spider 只能通过福利专区远程配置进入客户端，避免参与首页、普通全局搜索和普通播放链路。

## 平台配置模板

在 `welfare_platforms.json` 的 `platforms` 数组中新增平台时，可参考：

```json
{
  "platformKey": "your_platform_key",
  "name": "你的平台名称",
  "category": "video",
  "icon": "film.fill",
  "desc": "平台描述",
  "serviceType": "welfare_spider",
  "defaultHosts": [
    "https://your-default-domain.com"
  ],
  "sortOrder": 300,
  "defaultProxy": false,
  "notes": "Python Spider 福利源",
  "api": "./sources/welfare-js/your_platform_key.py",
  "scriptType": "python",
  "engine": "spider",
  "visibleInNormalSpider": false,
  "visibleInGlobalSearch": false,
  "visibleInHome": false
}
```

## 发布要求

新增或修改福利 Spider 后，需要重新生成并提交：

- `sources/welfare_platforms.json`
- `sources/all_sources.json`
- `sources/manifest.json`
- `sources/manifest.version`
- `sources/welfare-js/*.py`

## 隔离要求

- 福利 Spider 脚本只允许放在 `sources/welfare-js/`
- 福利 Spider 平台只允许配置在 `welfare_platforms.json`
- `visibleInNormalSpider` 必须为 `false`
- `visibleInGlobalSearch` 必须为 `false`
- `visibleInHome` 必须为 `false`
