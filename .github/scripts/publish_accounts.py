#!/usr/bin/env python3
"""GitHub Issue 一键发布：校验 issue body 中的子账号数据并写入 web/sub-accounts.json。

由 .github/workflows/publish-accounts.yml 在 Actions 中调用；
本地可用 pytest 覆盖（tests/test_issue_publish.py）。
"""
import json
import os
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
TARGET = ROOT / "web" / "sub-accounts.json"

HASH_RE = re.compile(r"^sha256\$[0-9a-f]{32}\$[0-9a-f]{64}$")
KEYS = {"id", "note", "createdAt", "expiresAt", "hash"}


def validate(data):
    """契约校验：仅接受不可逆哈希数据，禁止任何可回溯凭证。"""
    if not isinstance(data, dict) or data.get("version") != 2:
        return False, "version 必须为 2"
    if not str(data.get("algorithm", "")).startswith("sha256$salt$hash"):
        return False, "algorithm 不匹配"
    accounts = data.get("accounts")
    if not isinstance(accounts, list):
        return False, "accounts 必须是数组"
    for a in accounts:
        if not isinstance(a, dict):
            return False, "账号条目格式错误"
        if set(a.keys()) != KEYS:
            return False, "账号条目含不允许的字段（禁止明文/密文/密钥）"
        if not isinstance(a.get("id"), str) or not a["id"]:
            return False, "id 非法"
        if not isinstance(a.get("createdAt"), int) or not isinstance(a.get("expiresAt"), int):
            return False, "时间戳非法"
        if a["expiresAt"] - a["createdAt"] != 60 * 86400000:
            return False, "有效期必须为 60 天"
        if not HASH_RE.match(a.get("hash", "")):
            return False, "hash 格式非法"
    return True, ""


def main():
    body = os.environ.get("ISSUE_BODY", "")
    if not body.strip():
        sys.exit("issue body 为空")
    try:
        data = json.loads(body)
    except json.JSONDecodeError as exc:
        sys.exit("issue body 不是合法 JSON：" + str(exc))
    ok, reason = validate(data)
    if not ok:
        sys.exit("契约校验失败：" + reason)
    TARGET.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"OK: {len(data['accounts'])} accounts written to web/sub-accounts.json")


if __name__ == "__main__":
    main()
