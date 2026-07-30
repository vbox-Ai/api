#!/usr/bin/env python3
"""
LIBVIO 域名自动更新脚本

从 libviogroup.github.io 发布页解析 XOR 编码的备用线路域名，
测试可用性后更新 cloud_sources.json 中的 LIBVIO 配置。
"""

import json
import re
import sys
import urllib.request
import ssl

# ── 配置 ──
PUBLISH_URL = "https://libviogroup.github.io"
XOR_KEY = "lv2025"
SEARCH_PATH = "/search/-------------.html?wd="
CLOUD_SOURCES_PATH = "sources/cloud_sources.json"
SITE_NAME = "LIBVIO"

# 忽略 SSL 证书验证（某些域名可能证书不完整）
SSL_CTX = ssl.create_default_context()
SSL_CTX.check_hostname = False
SSL_CTX.verify_mode = ssl.CERT_NONE


def xor_decode(encoded, key):
    """XOR 解码：逗号分隔的数字数组与 key 逐字符异或"""
    nums = [int(n) for n in encoded.split(",")]
    key_chars = list(key)
    return "".join(chr(n ^ ord(key_chars[i % len(key_chars)])) for i, n in enumerate(nums))


def fetch_publish_page():
    """抓取发布页 HTML"""
    req = urllib.request.Request(
        PUBLISH_URL,
        headers={"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"},
    )
    with urllib.request.urlopen(req, timeout=15, context=SSL_CTX) as resp:
        return resp.read().decode("utf-8")


def extract_backup_domains(html):
    """从发布页 HTML 中提取 XOR 编码的备用线路域名"""
    domains = []

    # 提取 _BACKUP 数组中的 XOR 编码字符串
    # 格式: { e: xorDecode('...', _K), label: '备用线路 01' }
    backup_pattern = r"_BACKUP\s*=\s*\[(.*?)\]"
    backup_match = re.search(backup_pattern, html, re.DOTALL)
    if not backup_match:
        print("ERROR: 未找到 _BACKUP 数组")
        return domains

    backup_content = backup_match.group(1)

    # 提取所有 XOR 编码的字符串
    enc_pattern = r"xorDecode\('([^']+)'"  # 注意：JS 中用的是单引号
    enc_matches = re.findall(enc_pattern, backup_content)

    for enc in enc_matches:
        try:
            decoded = xor_decode(enc, XOR_KEY)
            # 确保是域名格式
            if "." in decoded and not decoded.startswith("http"):
                decoded = "https://" + decoded
            if decoded.startswith("http"):
                domains.append(decoded)
                print(f"  解码域名: {decoded}")
        except Exception as e:
            print(f"  解码失败: {enc[:30]}... → {e}")

    return domains


def test_domain(domain):
    """测试域名是否可用（返回 HTTP 200）"""
    try:
        req = urllib.request.Request(
            domain,
            headers={"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"},
        )
        with urllib.request.urlopen(req, timeout=10, context=SSL_CTX) as resp:
            return resp.status == 200
    except Exception as e:
        print(f"    测试失败: {domain} → {e}")
        return False


def test_search_url(base_url):
    """测试搜索 URL 是否返回有效内容"""
    search_url = base_url + SEARCH_PATH + "test"
    try:
        req = urllib.request.Request(
            search_url,
            headers={"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"},
        )
        with urllib.request.urlopen(req, timeout=10, context=SSL_CTX) as resp:
            if resp.status == 200:
                html = resp.read().decode("utf-8", errors="ignore")
                # 检查是否包含 MacCMS 标志或搜索表单
                if "maccms" in html or "search" in html or "stui" in html:
                    return True
        return False
    except Exception:
        return False


def update_cloud_sources(working_domains):
    """更新 cloud_sources.json 中的 LIBVIO 配置"""
    with open(CLOUD_SOURCES_PATH, "r", encoding="utf-8") as f:
        data = json.load(f)

    sites = data.get("cloudSites", [])

    # 构建所有可用域名的 searchurls 数组
    searchurls = [d + SEARCH_PATH for d in working_domains]

    if not searchurls:
        print("ERROR: 没有可用域名，跳过更新")
        return False

    # 查找现有的 LIBVIO 配置
    libvio_entry = None
    for site in sites:
        if site.get("name") == SITE_NAME:
            libvio_entry = site
            break

    if libvio_entry:
        # 更新现有配置
        old_urls = libvio_entry.get("searchurls", [])
        old_primary = libvio_entry.get("searchurl", "")

        # 如果域名列表没变化，跳过
        if old_urls == searchurls:
            print("域名列表无变化，跳过更新")
            return False

        libvio_entry["searchurl"] = searchurls[0]
        libvio_entry["detailBase"] = working_domains[0]
        libvio_entry["searchurls"] = searchurls
        print(f"更新 LIBVIO 配置: 主域名={working_domains[0]}, 备用={len(working_domains)}个")
    else:
        # 新增配置
        new_entry = {
            "name": SITE_NAME,
            "type": "cms",
            "searchurl": searchurls[0],
            "detailBase": working_domains[0],
            "searchurls": searchurls,
            "enabled": True,
            "priority": 1035,
            "group": "cloud",
        }
        sites.append(new_entry)
        data["cloudSites"] = sites
        print(f"新增 LIBVIO 配置: 主域名={working_domains[0]}, 备用={len(working_domains)}个")

    # 写回文件
    with open(CLOUD_SOURCES_PATH, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
        f.write("\n")

    return True


def main():
    print("=" * 50)
    print("LIBVIO 域名自动更新")
    print("=" * 50)

    # 1. 抓取发布页
    print(f"\n[1/4] 抓取发布页: {PUBLISH_URL}")
    try:
        html = fetch_publish_page()
        print(f"  成功: {len(html)} bytes")
    except Exception as e:
        print(f"  失败: {e}")
        sys.exit(1)

    # 2. 解码备用域名
    print(f"\n[2/4] XOR 解码备用线路 (key={XOR_KEY})")
    domains = extract_backup_domains(html)
    if not domains:
        print("  未找到任何域名，退出")
        sys.exit(1)
    print(f"  共解码 {len(domains)} 个域名")

    # 3. 测试域名可用性
    print(f"\n[3/4] 测试域名可用性")
    working = []
    for domain in domains:
        print(f"  测试: {domain}")
        if test_domain(domain):
            # 进一步测试搜索功能
            if test_search_url(domain):
                print(f"    ✅ 可用（搜索正常）")
                working.append(domain)
            else:
                print(f"    ⚠️ 可访问但搜索异常")
        else:
            print(f"    ❌ 不可用")

    if not working:
        print("\nERROR: 没有可用域名！保留现有配置不变。")
        sys.exit(1)

    # 4. 更新配置
    print(f"\n[4/4] 更新 cloud_sources.json")
    changed = update_cloud_sources(working)

    if changed:
        print("\n✅ 配置已更新，等待 git commit")
    else:
        print("\n⏭️ 无需更新")


if __name__ == "__main__":
    main()
