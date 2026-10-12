"""GitHub Issue 一键发布：契约校验测试。

线上版点「确认提交」→ 打开预填 GitHub issue → Actions 调 publish_accounts.py 校验并写入。
"""
import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / ".github" / "scripts"))
import publish_accounts as pa


def _body(n=1):
    now = 1791822527381
    day = 86400000
    return {
        "version": 2,
        "algorithm": "sha256$salt$hash(salt:account:password)",
        "accounts": [{
            "id": f"stu-test-{i:03d}", "note": "", "createdAt": now,
            "expiresAt": now + 60 * day,
            "hash": "sha256$" + "a" * 32 + "$" + "b" * 64,
        } for i in range(1, n + 1)],
    }


def test_validate_accepts_valid():
    ok, reason = pa.validate(_body())
    assert ok is True and reason == ""


def test_validate_rejects_plaintext_password():
    b = _body()
    b["accounts"][0]["password"] = "P@ss12345678"
    ok, reason = pa.validate(b)
    assert ok is False and "明文" in reason


def test_validate_rejects_account_name_field():
    b = _body()
    b["accounts"][0]["account"] = "stu001"
    assert pa.validate(b)[0] is False


def test_validate_rejects_bad_hash():
    b = _body()
    b["accounts"][0]["hash"] = "md5$xxxx"
    assert pa.validate(b)[0] is False


def test_validate_rejects_wrong_expiry():
    b = _body()
    b["accounts"][0]["expiresAt"] = b["accounts"][0]["createdAt"] + 30 * 86400000
    assert pa.validate(b)[0] is False


def test_validate_rejects_extra_keys():
    b = _body()
    b["accounts"][0]["secret"] = "xxx"
    assert pa.validate(b)[0] is False


def test_main_writes_file(tmp_path, monkeypatch):
    out = tmp_path / "sub-accounts.json"
    monkeypatch.setattr(pa, "TARGET", out)
    monkeypatch.setenv("ISSUE_BODY", json.dumps(_body(2)))
    pa.main()
    saved = json.loads(out.read_text(encoding="utf-8"))
    assert len(saved["accounts"]) == 2


def test_main_exits_on_invalid(monkeypatch):
    monkeypatch.setenv("ISSUE_BODY", json.dumps({"version": 1, "accounts": []}))
    with pytest.raises(SystemExit):
        pa.main()
