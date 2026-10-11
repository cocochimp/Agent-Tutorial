"""学员账号；权限来自服务端账户，绝不取自Prompt或模型输出。

账号由老师维护：默认从项目根 accounts.json 加载（改后重启生效），
文件缺失或内容非法时回退到内置演示账号，保证开发与测试可用。
"""
import hmac
import json
from dataclasses import asdict
from pathlib import Path
from .business import DemoError, Identity

DEFAULT_ACCOUNTS = {
    "chaoyang": {"password": "demo-chaoyang", "role": "region_manager", "regions": ["朝阳"]},
    "haidian": {"password": "demo-haidian", "role": "region_manager", "regions": ["海淀"]},
    "director": {"password": "demo-director", "role": "director", "regions": ["朝阳", "海淀"]},
    "viewer": {"password": "demo-viewer", "role": "viewer", "regions": ["朝阳"]},
}

ACCOUNTS_PATH = Path(__file__).resolve().parent.parent / "accounts.json"


def load_accounts(path=None):
    """从账号配置文件加载账号表；缺失或非法时回退内置演示账号。"""
    target = Path(path) if path else ACCOUNTS_PATH
    try:
        data = json.loads(target.read_text(encoding="utf-8"))
        if isinstance(data, dict) and data:
            return data
    except (OSError, ValueError):
        pass
    return dict(DEFAULT_ACCOUNTS)


ACCOUNTS = load_accounts()


def identity(username):
    account = ACCOUNTS.get(username)
    if not account:
        raise DemoError("UNAUTHENTICATED", "请先登录演示账号。")
    return Identity(user_id=username, role=account["role"], regions=tuple(account["regions"]))


def login(username, password, store):
    account = ACCOUNTS.get(username)
    if not account or not hmac.compare_digest(account["password"], password):
        raise DemoError("UNAUTHENTICATED", "账号或密码错误。")
    return store.login(username), asdict(identity(username))
