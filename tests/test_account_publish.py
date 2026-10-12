"""一键提交发布接口契约测试：POST /api/accounts/publish。

仅主账号可调用；数据契约校验通过后写 web/sub-accounts.json 并自动 git commit + push。
"""
import json
import subprocess
from types import SimpleNamespace
from fastapi.testclient import TestClient
import app as web
from estate_agent.storage import Store
from estate_agent.auth import identity


def _valid_body():
    now = 1791822527381
    day = 86400000
    return {
        "version": 2,
        "algorithm": "sha256$salt$hash(salt:account:password)",
        "accounts": [{
            "id": "stu-test-001", "note": "", "createdAt": now,
            "expiresAt": now + 60 * day,
            "hash": "sha256$" + "a" * 32 + "$" + "b" * 64,
        }],
    }


def _setup(tmp_path, monkeypatch):
    store = Store(tmp_path)
    monkeypatch.setattr(web, "store", store)
    web_root = tmp_path / "web"
    web_root.mkdir(parents=True, exist_ok=True)
    (web_root / "sub-accounts.json").write_text(
        json.dumps({"version": 2, "algorithm": "sha256$salt$hash(salt:account:password)", "accounts": []}),
        encoding="utf-8")
    monkeypatch.setattr(web, "WEB_ROOT", web_root)
    return web_root


def test_publish_requires_login(tmp_path, monkeypatch):
    _setup(tmp_path, monkeypatch)
    with TestClient(web.app) as client:
        r = client.post("/api/accounts/publish", json=_valid_body())
        assert r.status_code == 401


def test_publish_rejects_non_master(tmp_path, monkeypatch):
    web_root = _setup(tmp_path, monkeypatch)
    # 模拟已登录但非主账号
    monkeypatch.setattr(web, "current_user",
                        lambda request: SimpleNamespace(user_id='director'))
    with TestClient(web.app) as client:
        r = client.post("/api/accounts/publish", json=_valid_body())
        assert r.status_code == 403
    assert json.loads((web_root / "sub-accounts.json").read_text(encoding="utf-8"))["accounts"] == []


def test_publish_rejects_plaintext_fields(tmp_path, monkeypatch):
    web_root = _setup(tmp_path, monkeypatch)
    monkeypatch.setattr(web, "current_user",
                        lambda request: identity("chaoyang"))
    body = _valid_body()
    body["accounts"][0]["password"] = "P@ss12345678"  # 明文密码，必须拒绝
    with TestClient(web.app) as client:
        r = client.post("/api/accounts/publish", json=body)
        assert r.status_code == 400
    assert json.loads((web_root / "sub-accounts.json").read_text(encoding="utf-8"))["accounts"] == []


def test_publish_rejects_bad_hash_format(tmp_path, monkeypatch):
    web_root = _setup(tmp_path, monkeypatch)
    monkeypatch.setattr(web, "current_user",
                        lambda request: identity("chaoyang"))
    body = _valid_body()
    body["accounts"][0]["hash"] = "sha256$short$xxxx"
    with TestClient(web.app) as client:
        assert client.post("/api/accounts/publish", json=body).status_code == 400
    assert json.loads((web_root / "sub-accounts.json").read_text(encoding="utf-8"))["accounts"] == []


def test_publish_rejects_expiry_not_60d(tmp_path, monkeypatch):
    web_root = _setup(tmp_path, monkeypatch)
    monkeypatch.setattr(web, "current_user",
                        lambda request: identity("chaoyang"))
    body = _valid_body()
    body["accounts"][0]["expiresAt"] = body["accounts"][0]["createdAt"] + 30 * 86400000
    with TestClient(web.app) as client:
        assert client.post("/api/accounts/publish", json=body).status_code == 400
    assert json.loads((web_root / "sub-accounts.json").read_text(encoding="utf-8"))["accounts"] == []


def test_publish_writes_file_and_runs_git(tmp_path, monkeypatch):
    web_root = _setup(tmp_path, monkeypatch)
    monkeypatch.setattr(web, "current_user",
                        lambda request: identity("chaoyang"))
    calls = []
    monkeypatch.setattr(web, "run_git", lambda cmd: calls.append(cmd) or ("fake-commit", ""))
    with TestClient(web.app) as client:
        r = client.post("/api/accounts/publish", json=_valid_body())
        assert r.status_code == 200
        data = r.json()
        assert data["ok"] is True and data["count"] == 1 and data["commit"] == "fake-commit"
    saved = json.loads((web_root / "sub-accounts.json").read_text(encoding="utf-8"))
    assert len(saved["accounts"]) == 1
    assert saved["accounts"][0]["id"] == "stu-test-001"
    joined = " | ".join(" ".join(x) for c in calls for x in c)
    assert "add web/sub-accounts.json" in joined
    assert "commit" in joined and "学员账号" in joined
    assert "push origin main" in joined


def test_publish_no_changes_reports_ok(tmp_path, monkeypatch):
    web_root = _setup(tmp_path, monkeypatch)
    monkeypatch.setattr(web, "current_user",
                        lambda request: identity("chaoyang"))
    monkeypatch.setattr(web, "run_git", lambda cmd: calls.append(cmd) or (None, "nothing to commit"))
    calls = []
    with TestClient(web.app) as client:
        r = client.post("/api/accounts/publish", json=_valid_body())
        assert r.status_code == 200
        assert r.json()["no_changes"] is True
