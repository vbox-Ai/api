#!/usr/bin/env python3
"""合并 6 个源文件为 all_sources.json，并更新 manifest 版本号。

由 CI 在每次 push 到 sources/ 时自动执行。
客户端通过 all_sources.json 一次请求拿到全部数据，替代 6 次独立请求。
"""
import json
import os
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SOURCES_DIR = ROOT / "sources"
MANIFEST_FILE = SOURCES_DIR / "manifest.json"
OUTPUT_FILE = SOURCES_DIR / "all_sources.json"
VERSION_FILE = SOURCES_DIR / "manifest.version"

# 6 个源文件 → 合并后顶层 key 的映射
SOURCE_FILES = {
    "apiSources": "api_sources.json",
    "cloudSources": "cloud_sources.json",
    "spiderSources": "spider_sources.json",
    "domainOverrides": "domain_overrides.json",
    "parsers": "parsers.json",
    "disabledSources": "disabled_sources.json",
}


def bump_version(version: str) -> str:
    """版本号自动 +1，格式 2026.07.20.1 → 2026.07.20.2"""
    parts = version.rsplit(".", 1)
    if len(parts) == 2 and parts[1].isdigit():
        return f"{parts[0]}.{int(parts[1]) + 1}"
    return f"{version}.1"


def main():
    # 1. 合并 6 个文件
    result = {}
    for key, filename in SOURCE_FILES.items():
        file_path = SOURCES_DIR / filename
        if not file_path.exists():
            print(f"[merge] 跳过不存在的文件: {filename}")
            continue
        try:
            data = json.loads(file_path.read_text(encoding="utf-8"))
        except Exception as exc:
            print(f"[merge] 跳过无效 JSON {filename}: {exc}")
            continue
        # 去掉 _meta 元数据，只保留实际数据
        data.pop("_meta", None)
        result[key] = data

    OUTPUT_FILE.write_text(
        json.dumps(result, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    print(f"[merge] all_sources.json 已生成，包含 {len(result)} 个源")

    # 2. 更新 manifest 版本号
    if not MANIFEST_FILE.exists():
        raise SystemExit("manifest.json 不存在")

    manifest = json.loads(MANIFEST_FILE.read_text(encoding="utf-8"))
    old_version = manifest.get("configVersion", "")
    new_version = bump_version(old_version)
    manifest["configVersion"] = new_version
    manifest["updatedAt"] = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

    # 确保 manifest.files 包含 allSources
    if "files" not in manifest:
        manifest["files"] = {}
    manifest["files"]["allSources"] = (
        "https://raw.githubusercontent.com/vbox-Ai/api/main/sources/all_sources.json"
    )

    MANIFEST_FILE.write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(f"[merge] manifest.json 版本号: {old_version} → {new_version}")

    # 3. 生成 manifest.version 文件（客户端启动时探测用，约 30 字节）
    VERSION_FILE.write_text(
        json.dumps({"configVersion": new_version}, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    print(f"[merge] manifest.version: {new_version}")


if __name__ == "__main__":
    main()