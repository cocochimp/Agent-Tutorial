# 双角色账号体系（主/子账号 + 批量创建 + 不可逆哈希）实施计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 把教学站单账号登录升级为「主账号（超管，永不过期）+ 子账号（学员，60 天过期）」体系：主账号可批量创建 1~10 个子账号，创建时一次性展示明文，系统只存不可逆 SHA-256 哈希；子账号数据随站点发布（GitHub Pages 静态），学员在线登录校验。

**Architecture:** 纯前端实现（GitHub Pages 无后端）。登录校验在 `app.js`：主账号写死比对；子账号拉取 `static/sub-accounts.json`，按账号算 `SHA-256(salt:账号:密码)` 比对 + `expiresAt` 过期校验。创建流程在 `web/accounts.js`：批量生成随机账号密码 → 一次性明文展示 → 只存哈希进草稿（localStorage）→ 导出 `sub-accounts.json`（合并已发布文件）→ 用户放入 `web/` push 部署。系统内无明文、无密文、无解密/找回能力（用户明确「不要可回溯逻辑」）。

**Tech Stack:** 原生 JS（Web Crypto `crypto.subtle`/`getRandomValues`）、HTML/CSS、Python pytest（数据契约与算法一致性测试）、GitHub Pages。

**Spec:** `docs/superpowers/specs/2026-10-12-account-system-design.md`

## Global Constraints

- 子账号有效期固定 **60 天**（`createdAt + 60*24*3600*1000`，毫秒时间戳）。
- 哈希算法固定：`sha256$<salt>$<hex>`，`hex = SHA-256(salt + ':' + account + ':' + password)`，`salt` 为 16 字节随机 hex（32 个 hex 字符）。
- 数据文件路径：`web/sub-accounts.json`；前端 fetch 相对路径 `static/sub-accounts.json`（本地 FastAPI `/static` 挂载与 Pages 均成立）；**禁止** `projects/...` 裸路径与绝对 `/static/`。
- 数据文件字段白名单：`version`(==2)、`algorithm`、`accounts[]`，每项仅 `id / note / createdAt / expiresAt / hash`。**禁止**任何明文、密文、公钥、私钥字段。
- 主账号：`chaoyang / demo-chaoyang`（写死前端常量），永不过期，不进入数据文件。
- 创建入口：仅主账号登录后可见「创建子账号」；面板批量数量 1~10。
- 账号生成：随机账号 8 位、密码 12 位，字符集排除易混淆字符（`0O1lI`），大小写+数字（密码可含符号）。
- 每次修改静态文件递增 `?v=` 版本参数（当前 `v=20261012a` → 下一版 `v=20261012b`）。
- 版本参数递增后必须重新运行 `scripts/build_pages_site.py` 并 push 部署（`git -c http.proxy=http://127.0.0.1:7897 push origin main`）。

## Review Focus

- **数据文件被扒**：`sub-accounts.json` 与前端 JS 全部可下载，任何一处出现明文/可逆凭证即视为漏洞——测试断言字段白名单。
- **过期边界**：`expiresAt` 恰好在「现在」的账号（等于边界）应视为过期；测试用固定时间戳钉死。
- **主账号与子账号同名校验冲突**：子账号列表里出现 `chaoyang` 时，登录必须以主账号优先；生成器禁止产出主账号同名。
- **导出合并丢数据**：导出时若站点已发布文件含旧账号，合并去重必须按 `id` 保留全部旧账号，仅追加新草稿；测试断言合并规则（Python 侧实现同一合并函数并断言）。
- **本地与 Pages 一致性**：`static/sub-accounts.json` 相对路径在两环境下必须同时可用；版本递增与构建脚本必须同步执行。

---

### Task 1: 子账号数据契约与测试基线

**Files:**
- Create: `tests/test_account_system.py`
- Create: `web/sub-accounts.json`

**Interfaces:**
- Produces: `web/sub-accounts.json`（`{"version": 2, "algorithm": "sha256$salt$hash(salt:account:password)", "accounts": []}`）——后续所有任务的读取源。
- Produces: `tests/test_account_system.py` 中三个契约函数（供后续任务引用同一断言逻辑）：`hash_of(account, password, salt)`、`expired(createdAtMs, nowMs)`（60 天）、`assert_account_fields(acc)`。

- [ ] **Step 1: 写失败测试**

```python
def test_sub_accounts_file_exists_and_structure():
    p = Path('web/sub-accounts.json')
    assert p.is_file(), 'sub-accounts.json 必须存在'
    d = json.loads(p.read_text(encoding='utf-8'))
    assert d['version'] == 2
    assert d['algorithm'] == 'sha256$salt$hash(salt:account:password)'
    assert isinstance(d['accounts'], list)
    for acc in d['accounts']:
        assert set(acc.keys()) == {'id', 'note', 'createdAt', 'expiresAt', 'hash'}

def test_hash_format_contract():
    # 前端与测试必须用同一算法：hex = SHA-256(salt + ':' + account + ':' + password)
    salt = 'a' * 32
    h = hash_of('stu_abc1', 'Passw0rd!', salt)
    assert h == 'sha256$a' * 32 + '$' + hashlib.sha256((salt + ':stu_abc1:Passw0rd!').encode()).hexdigest()

def test_expiry_rule_fixed_60_days():
    created = 1730000000000
    assert not expired(created, created + 59 * 86400000)
    assert expired(created, created + 60 * 86400000)
    assert expired(created, created + 60 * 86400000)  # 恰好 60 天 → 过期
```

- [ ] **Step 2: 运行测试确认失败**

Run: `./.venv/bin/python -m pytest tests/test_account_system.py -v`
Expected: FAIL（`sub-accounts.json` 不存在 / `hash_of`/`expired` 未定义）

- [ ] **Step 3: 创建 `web/sub-accounts.json` 与测试内契约函数**

`web/sub-accounts.json`：
```json
{"version": 2, "algorithm": "sha256$salt$hash(salt:account:password)", "accounts": []}
```
`tests/test_account_system.py` 顶部：
```python
def hash_of(account, password, salt):
    return 'sha256$' + salt + '$' + hashlib.sha256((salt + ':' + account + ':' + password).encode()).hexdigest()
def expired(created_at_ms, now_ms, days=60):
    return now_ms - created_at_ms >= days * 86400000
```

- [ ] **Step 4: 运行测试确认通过**

Run: `./.venv/bin/python -m pytest tests/test_account_system.py -v`
Expected: PASS

- [ ] **Step 5: 提交**

```bash
git add tests/test_account_system.py web/sub-accounts.json
git commit -m "feat: 子账号数据契约（不可逆哈希 + 60 天过期规则）+ 初始数据文件"
```

---

### Task 2: 前端批量创建与导出（accounts.js）

**Files:**
- Create: `web/accounts.js`
- Test: `tests/test_account_system.py`（追加合并规则测试）

**Interfaces:**
- Consumes: `web/sub-accounts.json`（Task 1 数据契约）。
- Produces: `window.Accounts = { generateBatch(n), sha256Hex(str), hashOf(account, password, salt), now(), expiresAtOf(createdAt), mergeWithPublished(draftAccounts, publishedFile), buildExport(draftAccounts, publishedData), downloadExport(json) }`——Task 3（登录校验）消费 `hashOf`/`expiresAtOf`，Task 4（UI）消费 `generateBatch`/`mergeWithPublished`/`downloadExport`。

- [ ] **Step 1: 追加失败测试（合并规则 + 批量 id 唯一）**

```python
def test_merge_with_published_keeps_all_and_dedup_by_id():
    published = [{'id': 'stu-001', 'note': '', 'createdAt': 1, 'expiresAt': 2, 'hash': 'h1'}]
    draft = [{'id': 'stu-002', 'note': '', 'createdAt': 3, 'expiresAt': 4, 'hash': 'h2'}]
    merged = merge_with_published(draft, published)
    ids = [a['id'] for a in merged]
    assert ids == ['stu-001', 'stu-002']  # 旧账号全部保留，新草稿追加

def test_batch_ids_unique_and_never_master_name():
    ids = [generate_id(i) for i in range(10)]
    assert len(set(ids)) == 10
    assert all(not x.startswith('chaoyang') for x in ids)
```

- [ ] **Step 2: 运行测试确认失败**

Run: `./.venv/bin/python -m pytest tests/test_account_system.py::test_merge_with_published_keeps_all_and_dedup_by_id tests/test_account_system.py::test_batch_ids_unique_and_never_master_name -v`
Expected: FAIL（函数未定义）

- [ ] **Step 3: 在测试文件实现 `merge_with_published`/`generate_id`（合并规则与 id 生成规范，前端必须同规则）**

```python
def merge_with_published(draft, published):
    by_id = {a['id']: a for a in published}
    for a in draft:
        by_id[a['id']] = a
    return [by_id[k] for k in sorted(by_id)]
def generate_id(i, date='20261012'):
    return f'stu-{date}-{i:03d}'
```

- [ ] **Step 4: 运行测试确认通过**

Run: `./.venv/bin/python -m pytest tests/test_account_system.py -v`
Expected: PASS

- [ ] **Step 5: 实现 `web/accounts.js`**

`window.Accounts`（原生 JS + Web Crypto）：
- `generateBatch(n)`：1~10 校验；随机账号 8 位 / 密码 12 位，字符集 `abcdefghjkmnpqrstuvwxyzABCDEFGHJKMNPQRSTUVWXYZ23456789!@#$%^&*`（排除 `0O1lI` 与易混淆符号）；为每个生成 `{id, note, account, password, salt, hash, createdAt, expiresAt}`，`hash = sha256$salt$sha256hex(salt:account:password)`，`expiresAt = createdAt + 60 天`；账号禁止与 `chaoyang` 冲突。
- `mergeWithPublished(draft, published)` / `buildExport`：按 Task 1/2 测试锁定的合并规则（by id、保留全部旧账号）。
- `downloadExport(json)`：Blob 下载 `sub-accounts.json`。
- 草稿区：localStorage key `agent_tutorial_draft_accounts`。
- 随机数用 `crypto.getRandomValues`；SHA-256 用 `crypto.subtle.digest`。

- [ ] **Step 6: 提交**

```bash
git add web/accounts.js tests/test_account_system.py
git commit -m "feat: 子账号批量创建/草稿/导出（accounts.js，不可逆哈希）"
```

---

### Task 3: 登录校验扩展（app.js）

**Files:**
- Modify: `web/app.js`（登录与 `loggedIn` 部分）
- Test: `tests/test_account_system.py`（追加：校验 = 按账号取哈希比对 + 过期，用 Python 同一算法断言）

**Interfaces:**
- Consumes: `window.Accounts.hashOf`、`window.Accounts.expired`（Task 2）；`web/sub-accounts.json`。
- Produces: `window.Session = { verify(account, password) -> {role:'master'|'student', userId, expired?} }`；`loggedIn(user)` 增加 `user.role`，`role==='master'` 时显示「创建子账号」按钮（Task 4 消费）。

- [ ] **Step 1: 追加失败测试（校验算法与过期优先级）**

```python
def test_verify_student_uses_hash_and_expiry():
    salt = 'b' * 32
    acc = {'id': 'stu-001', 'account': 'stu_abc1', 'hash': hash_of('stu_abc1', 'Passw0rd!', salt), 'createdAt': 1730000000000, 'expiresAt': 1730000000000 + 60 * 86400000}
    assert verify('stu_abc1', 'Passw0rd!', acc, now_ms=1730000000000 + 10 * 86400000) is True
    assert verify('stu_abc1', 'wrong', acc, now_ms=1730000000000 + 10 * 86400000) is False
    assert verify('stu_abc1', 'Passw0rd!', acc, now_ms=1730000000000 + 61 * 86400000) is False  # 过期优先

def test_master_account_never_expires_and_wins_over_student_same_name():
    assert verify('chaoyang', 'demo-chaoyang', [], now_ms=10 ** 15) == 'master'
```

- [ ] **Step 2: 运行测试确认失败**

Run: `./.venv/bin/python -m pytest tests/test_account_system.py -v`
Expected: 新增两个 FAIL

- [ ] **Step 3: 测试文件实现 `verify`（前端必须同规则：先主账号，再子账号哈希，过期优先）**

```python
def verify(account, password, accounts, now_ms):
    if account == 'chaoyang' and password == 'demo-chaoyang':
        return 'master'
    for a in accounts:
        if a.get('account') != account:
            continue
        salt = a['hash'].split('$')[1]
        if a['hash'] != hash_of(account, password, salt):
            return False
        if now_ms >= a['expiresAt']:
            return False
        return 'student'
    return False
```

- [ ] **Step 4: 运行测试确认通过**

Run: `./.venv/bin/python -m pytest tests/test_account_system.py -v`
Expected: PASS

- [ ] **Step 5: 修改 `web/app.js`**

- `staticMode` 登录分支：先比对主账号 → 返回 `{role:'master'}`；否则 `fetch('static/sub-accounts.json')`（失败 → 仅主账号可登录，提示「账号服务暂不可用」）→ 按 `verify` 同规则校验（含过期）→ 返回 `{role:'student', userId: account}`。
- `loggedIn(user)`：`$('who').textContent = user.user_id + (user.role === 'master' ? ' · 管理员' : ' · 学员')`；`user.role === 'master'` 时显示 `$('create-account-btn')`，否则隐藏。
- 后端模式（`/api/login` 存在）：保留现有主账号流程，返回的 `user` 加 `role:'master'`（本地服务无子账号体系，子账号校验统一走前端 `static/sub-accounts.json`）。

- [ ] **Step 6: 提交**

```bash
git add web/app.js tests/test_account_system.py
git commit -m "feat: 登录校验扩展（主账号优先 + 子账号哈希/过期校验）"
```

---

### Task 4: 「创建子账号」UI（index.html + style.css）

**Files:**
- Modify: `web/index.html`（右上角按钮 + 面板 DOM + script 引入 accounts.js）
- Modify: `web/style.css`（面板样式）

**Interfaces:**
- Consumes: `window.Accounts`（Task 2）、`window.Session`/`loggedIn` role（Task 3）。
- Produces: DOM id 契约：`#create-account-btn`（右上角，仅主账号可见）、`#account-panel`（弹窗）、`#batch-count`（数量输入 1~10）、`#gen-batch-btn`、`#batch-result`（明文列表 + 复制）、`#draft-list`（草稿区）、`#export-accounts-btn`、`#export-status`。

- [ ] **Step 1: 实现 `web/index.html` 与 `web/style.css`（本任务为 UI，测试以 DOM 冒烟验证；Python 测试补一条「页面包含契约 id」）**

```python
def test_index_contains_account_contract_ids():
    html = Path('web/index.html').read_text(encoding='utf-8')
    for dom_id in ['create-account-btn', 'account-panel', 'batch-count', 'gen-batch-btn',
                   'batch-result', 'draft-list', 'export-accounts-btn']:
        assert dom_id in html
```

- [ ] **Step 2: 运行测试确认失败**

Run: `./.venv/bin/python -m pytest tests/test_account_system.py::test_index_contains_account_contract_ids -v`
Expected: FAIL

- [ ] **Step 3: 修改 `web/index.html`**

- 右上角（`$('logout')` 旁）加 `#create-account-btn`（文本「创建子账号」，默认 hidden，主账号登录后显示）。
- 面板 `#account-panel`（弹窗）：批量数量步进器（`#batch-count`，1~10）+ `#gen-batch-btn`；`#batch-result` 明文列表（每行「账号 / 密码 / 复制」+ 顶部「一键复制全部」）；`#draft-list` 草稿（id/备注/有效期，无明文）+ 「移除」；`#export-accounts-btn`（导出）+ `#export-status` 提示「放入 web/ 目录并 push 部署」。
- `<script src="static/accounts.js?v=20261012b"></script>`；其余 script `?v=` 递增到 `v=20261012b`。

- [ ] **Step 4: 修改 `web/style.css`**

沿用现有主题（墨绿青浅色系）：`.panel-overlay`、`.account-panel`、`.batch-row`、`.cred-line`、`.draft-row`、`.btn-*` 等样式。

- [ ] **Step 5: 运行测试确认通过**

Run: `./.venv/bin/python -m pytest tests/test_account_system.py -v`
Expected: PASS

- [ ] **Step 6: 本地冒烟（8765）**

启动/确认 `launch.py` 后浏览器（或 curl 静态断言）验证：登录主账号 → `#create-account-btn` 可见 → 选 3 个批量生成 → 明文列表出现 → 导出下载 `sub-accounts.json`（内容仅 hash 无明文）→ 用生成账号登录成功；过期账号（手工改 expiresAt 为过去）登录被拒。

- [ ] **Step 7: 提交**

```bash
git add web/index.html web/style.css tests/test_account_system.py
git commit -m "feat: 创建子账号面板（批量 1~10 + 明文一次性展示 + 草稿导出）"
```

---

### Task 5: 集成回归 + 部署

**Files:**
- Modify: `scripts/build_pages_site.py`（无需逻辑改动，仅确认 web/ 根新文件自动复制）
- Modify: `web/sub-accounts.json`（若冒烟时产生测试账号，恢复为空或保留正式草稿——由用户部署前决定）

**Interfaces:**
- Consumes: 全部 Task 1~4 产物。

- [ ] **Step 1: 全量回归**

Run: `./.venv/bin/python -m pytest tests/ -q`
Expected: 全绿（原 91 + 新增账号测试）

- [ ] **Step 2: 构建 Pages 站点并确认子账号文件进入**

Run: `./.venv/bin/python -X utf8 scripts/build_pages_site.py && ls site_pages/static/sub-accounts.json`
Expected: 文件存在

- [ ] **Step 3: 提交 + 推送部署**

```bash
git add -A
git commit -m "chore: 账号体系集成回归；版本参数递增 v=20261012b"
git -c http.proxy=http://127.0.0.1:7897 push origin main
```

- [ ] **Step 4: 线上验证**

- `curl https://cocochimp.github.io/Agent-Tutorial/static/sub-accounts.json` → 200。
- 浏览器冒烟：线上主账号登录 → 创建子账号按钮可见 → 批量创建 → 导出；学员账号登录成功；过期拒绝（用构造的过期账号）。
- 确认默认打开「项目导读」等既有功能未回归。

Expected: 全部通过

- [ ] **Step 5: 交付说明**

在最终回复中说明：主账号凭证、创建/导出/部署流程、安全边界（不可逆哈希、无找回）、忘记密码处理（删旧重建）、已知局限。
