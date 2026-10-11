import json
import pytest
from estate_agent import auth
from estate_agent.storage import Store


def test_load_accounts_from_file(tmp_path):
    p = tmp_path / "accounts.json"
    p.write_text(json.dumps({"stu01": {"password": "p1", "role": "student", "regions": []}}), encoding="utf-8")
    accounts = auth.load_accounts(str(p))
    assert accounts["stu01"]["password"] == "p1"


def test_load_accounts_fallback_when_missing(tmp_path):
    accounts = auth.load_accounts(str(tmp_path / "nope.json"))
    assert "chaoyang" in accounts  # 内置默认


def test_load_accounts_fallback_when_invalid_json(tmp_path):
    p = tmp_path / "accounts.json"
    p.write_text("{not valid json", encoding="utf-8")
    accounts = auth.load_accounts(str(p))
    assert "chaoyang" in accounts


def test_login_rejects_unknown_and_wrong_password(tmp_path):
    accounts = auth.load_accounts(str(tmp_path / "nope.json"))
    with pytest.raises(auth.DemoError):
        auth.login("nobody", "x", Store(tmp_path))
    with pytest.raises(auth.DemoError):
        auth.login("chaoyang", "wrong", Store(tmp_path))


def test_login_succeeds_with_valid_account(tmp_path):
    p = tmp_path / "accounts.json"
    p.write_text(json.dumps({"stu01": {"password": "p1", "role": "student", "regions": ["朝阳"]}}), encoding="utf-8")
    auth.ACCOUNTS = auth.load_accounts(str(p))
    try:
        token, user = auth.login("stu01", "p1", Store(tmp_path))
        assert token
        assert user["user_id"] == "stu01"
        assert user["role"] == "student"
    finally:
        auth.ACCOUNTS = auth.load_accounts()  # 恢复默认，避免污染其他测试
