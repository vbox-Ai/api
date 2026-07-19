#!/usr/bin/env python3
import json
import socket
import ssl
import time
from datetime import datetime, timezone
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import urlparse
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parents[1]
OUT_DIR = ROOT / "domain-monitor"
DOMAINS_JSON = OUT_DIR / "domains.json"
RESULT_JSON = OUT_DIR / "check-results.json"
RESULT_MD = OUT_DIR / "check-results.md"
TIMEOUT = 10


def check_url(url):
    start = time.time()
    headers = {
        "User-Agent": "Mozilla/5.0 vbox-domain-monitor/1.0",
        "Accept": "*/*",
    }
    request = Request(url, headers=headers, method="GET")
    try:
        with urlopen(request, timeout=TIMEOUT, context=ssl.create_default_context()) as response:
            elapsed = int((time.time() - start) * 1000)
            code = getattr(response, "status", 200)
            return {
                "ok": 200 <= code < 500,
                "statusCode": code,
                "responseMs": elapsed,
                "error": "",
            }
    except HTTPError as exc:
        elapsed = int((time.time() - start) * 1000)
        return {
            "ok": 200 <= exc.code < 500,
            "statusCode": exc.code,
            "responseMs": elapsed,
            "error": f"HTTP {exc.code}",
        }
    except (URLError, socket.timeout, TimeoutError) as exc:
        elapsed = int((time.time() - start) * 1000)
        return {
            "ok": False,
            "statusCode": None,
            "responseMs": elapsed,
            "error": str(exc.reason if isinstance(exc, URLError) else exc),
        }
    except Exception as exc:
        elapsed = int((time.time() - start) * 1000)
        return {
            "ok": False,
            "statusCode": None,
            "responseMs": elapsed,
            "error": str(exc),
        }


def markdown_table(results):
    lines = [
        "# vbox 远程源每周检测报告",
        "",
        f"检测时间：{datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC')}",
        "",
        "## 总览",
        "",
    ]
    total = len(results)
    ok = sum(1 for item in results if item["ok"])
    failed = total - ok
    lines.extend([
        f"- 总记录：{total}",
        f"- 正常：{ok}",
        f"- 异常：{failed}",
        "",
    ])

    failed_items = [item for item in results if not item["ok"]]
    if failed_items:
        lines.extend([
            "## 异常记录",
            "",
            "| 域名 | 来源 | 字段 | 状态 | 耗时 | 错误 |",
            "|---|---|---|---:|---:|---|",
        ])
        for item in failed_items:
            source = item.get("sourceName") or item.get("sourceKey") or item.get("sourceFile") or ""
            lines.append(
                f"| {item['host']} | {source} | {item.get('field') or ''} | "
                f"{item.get('statusCode') or '-'} | {item.get('responseMs') or '-'}ms | {item.get('error') or ''} |"
            )
        lines.append("")

    lines.extend([
        "## 全部记录",
        "",
        "| 域名 | 来源 | 文件 | 字段 | 状态 | 耗时 |",
        "|---|---|---|---|---:|---:|",
    ])
    for item in results:
        source = item.get("sourceName") or item.get("sourceKey") or ""
        status = item.get("statusCode") or "-"
        lines.append(
            f"| {item['host']} | {source} | {item.get('sourceFile') or ''} | "
            f"{item.get('field') or ''} | {status} | {item.get('responseMs') or '-'}ms |"
        )
    lines.append("")
    return "\n".join(lines)


def main():
    if not DOMAINS_JSON.exists():
        raise SystemExit("domains.json 不存在，请先运行 extract_domains.py")

    records = json.loads(DOMAINS_JSON.read_text(encoding="utf-8"))
    results = []

    for record in records:
        parsed = urlparse(record["host"])
        if parsed.scheme not in {"http", "https"} or not parsed.netloc:
            continue
        result = check_url(record["host"])
        results.append({**record, **result})
        print(f"[check] {record['host']} ok={result['ok']} status={result['statusCode']} ms={result['responseMs']}")

    RESULT_JSON.write_text(json.dumps(results, ensure_ascii=False, indent=2), encoding="utf-8")
    RESULT_MD.write_text(markdown_table(results), encoding="utf-8")

    failed = sum(1 for item in results if not item["ok"])
    print(f"[check] total={len(results)} failed={failed}")


if __name__ == "__main__":
    main()
