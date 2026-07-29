#!/usr/bin/env python3
"""
从 pan-site-monitor.douer.me 拉取最新的站点 URL，
自动更新 cloud_sources.json 中对应源的域名。

特点：
- 只替换域名（scheme + host + port），保留路径和查询参数
- 不修改 name / type / priority / enabled 等其他字段
- 更新前生成带时间戳的备份文件
- 仅在有变化时才写回文件
"""
import json
import os
import shutil
import ssl
import sys
from datetime import datetime, timezone
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import urlparse, urlunparse
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parents[1]
CLOUD_SOURCES = ROOT / "sources" / "cloud_sources.json"
BACKUP_DIR = ROOT / "domain-monitor" / "backups"
MONITOR_API = "https://pan-site-monitor.douer.me/api/data"
TIMEOUT = 30

# 监控站名 → cloud_sources.json 中的源名称
NAME_MAP = {
    "玩偶": "玩偶资源",
    "木偶": "木偶资源",
    "蜡笔": "飞猫影视",
    "闪电": "闪电优汐",
    "至臻": "至臻影视",
    "多多": "多多资源",
    "欧哥": "欧歌资源",
    "二小": "2小盘",
    "虎斑": "虎斑资源",
    "小斑": "小斑资源",
}


def fetch_monitor_data():
    """从监控 API 拉取最新数据"""
    headers = {
        "User-Agent": "Mozilla/5.0 vbox-url-updater/1.0",
        "Accept": "application/json",
    }
    ctx = ssl.create_default_context()
    request = Request(MONITOR_API, headers=headers, method="GET")
    with urlopen(request, timeout=TIMEOUT, context=ctx) as response:
        return json.loads(response.read().decode("utf-8"))


def extract_origin(url):
    """提取 URL 的 origin 部分 (scheme + host + port)，不含路径"""
    parsed = urlparse(url)
    if not parsed.scheme or not parsed.netloc:
        return None
    return f"{parsed.scheme}://{parsed.netloc}"


def replace_origin(original_url, new_origin):
    """用新的 origin 替换原 URL 的 origin，保留路径和查询参数"""
    parsed = urlparse(original_url)
    new_parsed = urlparse(new_origin)
    return urlunparse((
        new_parsed.scheme,
        new_parsed.netloc,
        parsed.path,
        parsed.params,
        parsed.query,
        parsed.fragment,
    ))


def update_sources(data, monitor_data):
    """
    根据监控数据更新 cloud_sources.json
    返回 (updated_data, changes) 其中 changes 是变更列表
    """
    sites = monitor_data.get("sites", {})
    changes = []

    # 构建监控站名 → best_url 映射
    monitor_urls = {}
    for monitor_name, site_info in sites.items():
        best_url = site_info.get("best_url", "")
        if best_url:
            config_name = NAME_MAP.get(monitor_name)
            if config_name:
                monitor_urls[config_name] = best_url

    for site in data.get("cloudSites", []):
        name = site.get("name", "")
        if name not in monitor_urls:
            continue

        new_origin = extract_origin(monitor_urls[name])
        if not new_origin:
            continue

        updated = False
        for field in ("searchurl", "detailBase"):
            old_url = site.get(field, "")
            if not old_url:
                continue
            old_origin = extract_origin(old_url)
            if old_origin and old_origin != new_origin:
                new_url = replace_origin(old_url, new_origin)
                site[field] = new_url
                changes.append({
                    "name": name,
                    "field": field,
                    "old": old_url,
                    "new": new_url,
                })
                updated = True
            elif old_origin == new_origin:
                # 域名已是最优，无需更新
                pass

        # apiSearch 字段也需要更新（如果有）
        old_api = site.get("apiSearch", "")
        if old_api:
            old_origin = extract_origin(old_api)
            if old_origin and old_origin != new_origin:
                new_api = replace_origin(old_api, new_origin)
                site["apiSearch"] = new_api
                changes.append({
                    "name": name,
                    "field": "apiSearch",
                    "old": old_api,
                    "new": new_api,
                })

    return data, changes


def backup_file():
    """在更新前备份当前文件"""
    BACKUP_DIR.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    backup_path = BACKUP_DIR / f"cloud_sources_{timestamp}.json"
    shutil.copy2(CLOUD_SOURCES, backup_path)
    print(f"[backup] 已备份到 {backup_path}")
    return backup_path


def main():
    if not CLOUD_SOURCES.exists():
        print("[error] cloud_sources.json 不存在", file=sys.stderr)
        sys.exit(1)

    # 1. 读取当前配置
    with open(CLOUD_SOURCES, "r", encoding="utf-8") as f:
        data = json.load(f)

    # 2. 拉取监控数据
    print("[fetch] 正在拉取监控数据...")
    try:
        monitor_data = fetch_monitor_data()
    except (HTTPError, URLError) as e:
        print(f"[error] 拉取监控数据失败: {e}", file=sys.stderr)
        sys.exit(1)

    summary = monitor_data.get("summary", {})
    print(f"[fetch] 监控数据: {summary.get('success_sites', 0)}/{summary.get('total_sites', 0)} 站点在线")

    # 3. 更新配置
    data, changes = update_sources(data, monitor_data)

    # 4. 如果有变化，备份并写回
    if changes:
        backup_file()
        with open(CLOUD_SOURCES, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
            f.write("\n")
        print(f"[update] 共更新 {len(changes)} 处 URL:")
        for c in changes:
            print(f"  - {c['name']} / {c['field']}:")
            print(f"      旧: {c['old']}")
            print(f"      新: {c['new']}")
    else:
        print("[update] 所有 URL 均为最新，无需更新")

    # 5. 输出变更摘要（供 GitHub Actions 使用）
    if changes:
        summary_lines = [f"- {c['name']} / {c['field']}: {c['old']} → {c['new']}" for c in changes]
        gh_output = os.environ.get("GITHUB_OUTPUT")
        if gh_output:
            with open(gh_output, "a", encoding="utf-8") as f:
                f.write(f"updated={len(changes)}\n")
                f.write(f"changes<<EOF\n")
                f.write("\n".join(summary_lines) + "\n")
                f.write("EOF\n")


if __name__ == "__main__":
    main()
