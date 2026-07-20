#!/usr/bin/env python3
import json
import re
from pathlib import Path
from urllib.parse import urlparse

ROOT = Path(__file__).resolve().parents[1]
SOURCES_DIR = ROOT / "sources"
OUT_DIR = ROOT / "domain-monitor"
URL_RE = re.compile(r"https?://[^\s\"'<>\\)\]}]+")


def walk(value, path=""):
    if isinstance(value, dict):
        source_key = value.get("key")
        source_name = value.get("name")
        for key, child in value.items():
            child_path = f"{path}.{key}" if path else key
            yield from walk_with_context(child, child_path, source_key, source_name)
    elif isinstance(value, list):
        for index, child in enumerate(value):
            child_path = f"{path}[{index}]"
            yield from walk(child, child_path)
    elif isinstance(value, str):
        for match in URL_RE.finditer(value):
            yield {
                "field": path.split(".")[-1] if path else "",
                "jsonPath": path,
                "fullUrl": match.group(0).rstrip(".,;"),
                "sourceKey": None,
                "sourceName": None,
            }


def walk_with_context(value, path, source_key=None, source_name=None):
    if isinstance(value, dict):
        next_key = value.get("key", source_key)
        next_name = value.get("name", source_name)
        for key, child in value.items():
            child_path = f"{path}.{key}" if path else key
            yield from walk_with_context(child, child_path, next_key, next_name)
    elif isinstance(value, list):
        for index, child in enumerate(value):
            yield from walk_with_context(child, f"{path}[{index}]", source_key, source_name)
    elif isinstance(value, str):
        for match in URL_RE.finditer(value):
            yield {
                "field": path.split(".")[-1] if path else "",
                "jsonPath": path,
                "fullUrl": match.group(0).rstrip(".,;"),
                "sourceKey": source_key,
                "sourceName": source_name,
            }


def host_of(url):
    parsed = urlparse(url)
    if not parsed.scheme or not parsed.netloc:
        return None
    return f"{parsed.scheme}://{parsed.netloc}"


def main():
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    records = []

    for file_path in sorted(SOURCES_DIR.glob("*.json")):
        if file_path.name in {"disabled_sources.json", "manifest.json"}:
            print(f"[extract] skip config-only file {file_path}")
            continue
        try:
            data = json.loads(file_path.read_text(encoding="utf-8"))
        except Exception as exc:
            print(f"[extract] skip invalid json {file_path}: {exc}")
            continue

        for item in walk(data):
            host = host_of(item["fullUrl"])
            if not host:
                continue
            records.append({
                "host": host,
                "fullUrl": item["fullUrl"],
                "sourceFile": str(file_path.relative_to(ROOT)),
                "sourceKey": item.get("sourceKey"),
                "sourceName": item.get("sourceName"),
                "field": item.get("field"),
                "jsonPath": item.get("jsonPath"),
            })

    unique = {}
    for record in records:
        key = (record["host"], record["fullUrl"], record["sourceFile"], record.get("jsonPath"))
        unique[key] = record

    result = list(unique.values())
    result.sort(key=lambda item: (item["host"], item["sourceFile"], item.get("sourceName") or ""))

    (OUT_DIR / "domains.json").write_text(
        json.dumps(result, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    hosts = sorted({item["host"] for item in result})
    (OUT_DIR / "domains.txt").write_text("\n".join(hosts) + ("\n" if hosts else ""), encoding="utf-8")
    print(f"[extract] urls={len(result)} hosts={len(hosts)}")


if __name__ == "__main__":
    main()
