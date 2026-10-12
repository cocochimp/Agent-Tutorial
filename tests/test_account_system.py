"""子账号体系数据契约与算法一致性测试。

契约（前端 web/accounts.js 必须与这里完全一致）：
- hash 格式：sha256$<salt>$<hex>，hex = SHA-256(salt + ':' + account + ':' + password)
- salt：16 字节随机 hex（32 个 hex 字符）
- 过期：expiresAt = createdAt + 60 天；now >= expiresAt 即过期
- 数据文件字段白名单：version(2)/algorithm/accounts[]，每项仅 id/note/createdAt/expiresAt/hash
- 系统内禁止明文/密文/公钥/私钥字段（无可回溯凭证）
"""
import hashlib
import json
from pathlib import Path

WEB = Path('web')


# —— 契约函数（前端必须同规则）——

def hash_of(account, password, salt):
    """hash = sha256$salt$SHA256(salt:account:password)"""
    return 'sha256$' + salt + '$' + hashlib.sha256(
        (salt + ':' + account + ':' + password).encode('utf-8')).hexdigest()


def expired(created_at_ms, now_ms, days=60):
    """子账号自创建日起 days 天过期；到达边界即视为过期。"""
    return now_ms - created_at_ms >= days * 86400000


def merge_with_published(draft, published):
    """导出合并：按 id 去重，保留全部旧账号，新草稿追加/覆盖同名。"""
    by_id = {a['id']: a for a in published}
    for a in draft:
        by_id[a['id']] = a
    return [by_id[k] for k in sorted(by_id)]


def generate_id(i, date='20261012'):
    """批量账号 id：stu-<date>-<3位序号>，永不与主账号同名。"""
    return f'stu-{date}-{i:03d}'


def verify(account, password, accounts, now_ms):
    """登录校验：主账号优先；子账号遍历各条目哈希匹配 + 过期优先。

    数据文件不存账号名（字段白名单无 account），登录时对每个条目用其
    salt 计算 hash(输入账号:输入密码) 比对。返回 'master'/'student'/False。
    """
    if account == 'chaoyang' and password == 'demo-chaoyang':
        return 'master'
    for a in accounts:
        salt = a['hash'].split('$')[1]
        if a['hash'] != hash_of(account, password, salt):
            continue
        if now_ms >= a['expiresAt']:
            return False
        return 'student'
    return False


# —— Task 1: 数据文件与契约 ——

def test_sub_accounts_file_exists_and_structure():
    p = WEB / 'sub-accounts.json'
    assert p.is_file(), 'sub-accounts.json 必须存在'
    d = json.loads(p.read_text(encoding='utf-8'))
    assert d['version'] == 2
    assert d['algorithm'] == 'sha256$salt$hash(salt:account:password)'
    assert isinstance(d['accounts'], list)
    for acc in d['accounts']:
        assert set(acc.keys()) == {'id', 'note', 'createdAt', 'expiresAt', 'hash'}


def test_hash_format_contract():
    salt = 'a' * 32
    h = hash_of('stu_abc1', 'Passw0rd!', salt)
    expected_hex = hashlib.sha256((salt + ':stu_abc1:Passw0rd!').encode('utf-8')).hexdigest()
    assert h == 'sha256$' + salt + '$' + expected_hex
    # 不可逆断言：数据中不得出现账号/密码明文
    assert 'Passw0rd!' not in h


def test_expiry_rule_fixed_60_days():
    created = 1730000000000
    assert not expired(created, created + 59 * 86400000)
    assert expired(created, created + 60 * 86400000)   # 恰好 60 天 → 过期
    assert expired(created, created + 61 * 86400000)


def test_accounts_field_whitelist_no_plaintext():
    """数据文件任何账号条目都不得含明文/密文/密钥字段（无可回溯凭证）。"""
    d = json.loads((WEB / 'sub-accounts.json').read_text(encoding='utf-8'))
    for acc in d['accounts']:
        assert set(acc.keys()) == {'id', 'note', 'createdAt', 'expiresAt', 'hash'}
        assert 'account' not in acc and 'password' not in acc
        assert 'encrypted' not in acc and 'key' not in acc


# —— Task 2: 合并规则与批量 id ——

def test_merge_with_published_keeps_all_and_dedup_by_id():
    published = [{'id': 'stu-001', 'note': '', 'createdAt': 1, 'expiresAt': 2, 'hash': 'h1'}]
    draft = [{'id': 'stu-002', 'note': '', 'createdAt': 3, 'expiresAt': 4, 'hash': 'h2'}]
    merged = merge_with_published(draft, published)
    assert [a['id'] for a in merged] == ['stu-001', 'stu-002']
    # 同名草稿覆盖旧账号（按 id 去重）
    draft2 = [{'id': 'stu-001', 'note': 'new', 'createdAt': 9, 'expiresAt': 10, 'hash': 'h3'}]
    merged2 = merge_with_published(draft2, published)
    assert [a['id'] for a in merged2] == ['stu-001']
    assert merged2[0]['hash'] == 'h3'


def test_batch_ids_unique_and_never_master_name():
    ids = [generate_id(i) for i in range(10)]
    assert len(set(ids)) == 10
    assert all(not x.startswith('chaoyang') for x in ids)


# —— Task 3: 登录校验规则 ——

def test_verify_student_uses_hash_and_expiry():
    salt = 'b' * 32
    created = 1730000000000
    acc = {'id': 'stu-001', 'note': '',
           'hash': hash_of('stu_abc1', 'Passw0rd!', salt),
           'createdAt': created, 'expiresAt': created + 60 * 86400000}
    assert verify('stu_abc1', 'Passw0rd!', [acc], now_ms=created + 10 * 86400000) == 'student'
    assert verify('stu_abc1', 'wrong', [acc], now_ms=created + 10 * 86400000) is False
    assert verify('stu_abc1', 'Passw0rd!', [acc], now_ms=created + 61 * 86400000) is False
    # 数据文件无 account 字段：账号名也不落盘
    assert 'account' not in acc and 'password' not in acc


def test_master_account_never_expires_and_wins_over_student_same_name():
    assert verify('chaoyang', 'demo-chaoyang', [], now_ms=10 ** 15) == 'master'
    salt = 'c' * 32
    acc = {'id': 'stu-001', 'note': '', 'hash': hash_of('chaoyang', 'x', salt),
           'createdAt': 1, 'expiresAt': 2}
    # 即使子账号列表里有同名 chaoyang 的哈希，主账号凭证也优先
    assert verify('chaoyang', 'demo-chaoyang', [acc], now_ms=10 ** 15) == 'master'


# —— Task 4: UI 契约 id ——

def test_index_contains_account_contract_ids():
    html = (WEB / 'index.html').read_text(encoding='utf-8')
    for dom_id in ['create-account-btn', 'account-panel', 'batch-count', 'gen-batch-btn',
                   'batch-result', 'draft-list', 'export-accounts-btn']:
        assert dom_id in html, f'index.html 缺少 {dom_id}'
