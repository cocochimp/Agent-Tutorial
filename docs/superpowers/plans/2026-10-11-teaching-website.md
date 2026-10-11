# 教学网站改造 Implementation Plan

> **For agentic workers:**
>
>  REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (
>
> `- [ ]`
>
> ) syntax for tracking.

**Goal:** 将房产经营分析 Agent 项目重构为以 "实习工作项" 为学习单位的教学网站 —— 登录后默认进入四象限学习视图（实现教程），另有高频面试题 Tab，均支持导出可编辑 HTML。

**Architecture:** 前端为主的重构：`index.html` 改为两个 Tab（实现教程四象限视图 / 高频面试题），新增 `teaching.js`、`interview.js`、`export.js` 与两个数据文件 `work-items.json`、`interview-questions.json`；后端仅最小改动 —— 登录账号改为老师可维护的配置文件加载，分析 API 保留但前端不再暴露调用。右下角实例代码复用现有 `tutorial-data.json` 源码快照与 `learning.js` 源码阅读器。

**Tech Stack:** FastAPI（后端不变）、原生 JS（前端，无框架）、pytest（后端 / 数据校验测试）、contenteditable（导出 HTML 可编辑）。

**Spec:** `docs/superpowers/specs/2026-10-11-teaching-website-design.md`

## Global Constraints



* 界面语言：中文；所有新文案使用中文。

* 登录必须在**服务端**校验（`estate_agent/auth.py`），账号由老师维护（配置文件），登录框**不预填、不显示密码提示、无角色下拉**。

* 移除前端分析交互：页面中不得出现 "提交经营问题 / 运行分析 / 取消任务 / 历史任务 / 工单 / 能力对照说明书 / API 文档" 入口。

* 节点名必须与 `web/app.js` 的 `labels` 键一致（understand/clarify/agent\_node/schema\_retrieval/query\_sql/calculate/analyze/rag\_search/generate\_report/validate/human\_approval/execute\_action/finish/retry\_node）。

* 右下角实例代码**只从** `web/tutorial-data.json` 的 `files` 快照取（`refs` 用 path/start/end 指向），不重复存源码。

* 导出 HTML 必须是**单文件自包含、正文 contenteditable 可编辑**（参考手册机制：点击修改、Ctrl+S 保存草稿、生成独立新文件）；导出内容一律用 textContent / 转义，禁止把题库或介绍文本当 HTML 注入。

* 工作项清单：手册工作一～六 + 补充项 "工程化与评测"。

* 面试题：按工作项分类 + `general`（汇总）；字段含 `weight`（频次）、`status`（active/draft）。

* 项目**当前不是 git 仓库**：默认以 "验证步骤" 作为每个任务的收尾；若用户同意 `git init`，则每个任务末追加 commit 步骤（在 Task 1 前询问并执行 `git init` + 首次提交）。

* 后端分析 API 保留实现（避免破坏 `tests/test_api.py`），前端不调用。

## Review Focus

以下为 spec 隐含、无任务测试直接覆盖但最可能咬人的输入 / 失败模式，每条对应的测试已放入所属任务：



1. **未登录访问**：未登录用户访问教学页面或任意 `/api/*` → 应跳登录或返回 401，不得看到教学视图内容。（Task 1 测试 + 现有 test\_api.py 首行已覆盖 `/api/tasks` 401，教学页门禁由 Task 4 前端检查 `/api/session` 实现）

2. **work-items.json 节点名非法**：某工作项的 `nodes` 出现 `labels` 之外的名字 → 右上角节点图与右下角联动失效且无提示。（Task 2 校验测试：节点名必须 ∈ labels 键集）

3. **codeRefs 指向失效**：`codeRefs` 的 path 不在 tutorial-data.json `files` 中，或 start/end 越界 → 右下角代码区渲染失败。（Task 2 校验测试逐条核对）

4. **导出内容含 HTML 特殊字符**：面试题答案 / 工作项文案含 `<`、`&` 等 → 导出 HTML 结构被破坏或脚本注入。（Task 7 导出实现用 textContent / 转义，测试含 `<script>` 样例句）

5. **提炼文案缺字段**：手册提炼时漏掉 intro 必填字段 → 左下角空面板。（Task 2 校验测试：intro 的 scene/problem/action/why/result 必填非空）



***

### Task 1: 学员账号配置加载（后端）

**Files:**



* Create: `accounts.json`（项目根）

* Modify: `estate_agent/auth.py`

* Test: `tests/test_auth_accounts.py`

**Interfaces:**



* Consumes: 无（独立任务）。

* Produces: `estate_agent/auth.load_accounts(path) -> dict`（`{username: {"password": str, "role": str, "regions": [str]}}`，文件不存在或 JSON 非法时回退到内置默认 demo 账号）；`ACCOUNTS` 常量改为由 `load_accounts` 初始化。

- [ ] **Step 1: 写失败测试&#x20;**`tests/test_auth_accounts.py`



```
import json, pytest
from estate_agent import auth

def test_load_accounts_from_file(tmp_path):
    p = tmp_path / "accounts.json"
    p.write_text(json.dumps({"stu01": {"password": "p1", "role": "student", "regions": []}}), encoding="utf-8")
    assert auth.load_accounts(str(p))["stu01"]["password"] == "p1"

def test_load_accounts_fallback_when_missing(tmp_path):
    accounts = auth.load_accounts(str(tmp_path / "nope.json"))
    assert "chaoyang" in accounts  # 内置默认

def test_login_rejects_unknown_and_wrong_password(tmp_path):
    from estate_agent.storage import Store
    accounts = auth.load_accounts(str(tmp_path / "nope.json"))
    with pytest.raises(auth.DemoError): auth.login("nobody", "x", Store(tmp_path))
    with pytest.raises(auth.DemoError): auth.login("chaoyang", "wrong", Store(tmp_path))
```



* [ ] **Step 2: 运行确认失败**

Run: `./.venv/bin/python -m pytest tests/test_auth_accounts.py -v`

Expected: FAIL（`load_accounts` 不存在）



* [ ] **Step 3: 在&#x20;**`estate_agent/auth.py`**&#x20;实现&#x20;**`load_accounts(path)`**&#x20;并改造&#x20;**`ACCOUNTS`**&#x20;初始化**

签名：`load_accounts(path: str | None = None) -> dict`。读取 JSON；`json.load` 失败、文件缺失、或结果为空 dict 时回退内置 `DEFAULT_ACCOUNTS`（现 `ACCOUNTS` 的 4 个 demo 账号原样保留为默认）。`ACCOUNTS = load_accounts(ACCOUNTS_PATH)`，`ACCOUNTS_PATH` 指向项目根 `accounts.json`（不存在则回退默认）。`login()`/`identity()` 逻辑不变。



* [ ] **Step 4: 创建项目根&#x20;**`accounts.json`**（默认 = 现有 demo 账号）**

内容为现有 4 个 demo 账号（chaoyang/haidiand/director/viewer），并在文件内以 JSON 注释格式（顶层 `"_note"` 字段）写明 "老师在此增删学员账号，改后重启生效；上线前务必替换默认密码"。



* [ ] **Step 5: 运行确认通过**

Run: `./.venv/bin/python -m pytest tests/test_auth_accounts.py tests/test_api.py -v`

Expected: 全部 PASS（test\_api.py 用默认 demo 账号登录，仍应通过）



***

### Task 2: 工作项数据文件（web/work-items.json）

**Files:**



* Create: `web/work-items.json`

* Create: `tests/test_work_items.py`

**Interfaces:**



* Consumes: Task 1 无依赖；依赖 `web/tutorial-data.json` 的 `files` 键与 `web/app.js` 的 `labels` 键。

* Produces: `web/work-items.json` 顶层 `{"version": 1, "workItems": [...]}`；每个 item：`{id, title, short, summary, nodes: [str], intro: {scene, problem, action, why, result}, io: [{node, input, output, note}], codeRefs: [{path, start, end, note}]}`。文件名与结构为 Task 5 前端读取契约，**不得改名**。

- [ ] **Step 1: 写失败测试&#x20;**`tests/test_work_items.py`



```
import json, pathlib, pytest
ROOT = pathlib.Path(__file__).resolve().parent.parent

def _items():
    return json.loads((ROOT / "web" / "work-items.json").read_text(encoding="utf-8"))["workItems"]

def test_schema_and_mandatory_fields():
    items = _items()
    assert len(items) >= 6  # 工作一~六 + 补充
    for it in items:
        assert {"id","title","short","summary","nodes","intro","io","codeRefs"} <= set(it)
        for k in ("scene","problem","action","why","result"):
            assert it["intro"][k] and it["intro"][k].strip()

def test_node_names_in_labels():
    import re
    labels_src = (ROOT / "web" / "app.js").read_text(encoding="utf-8")
    keys = set(re.findall(r"(\w+):'", labels_src.split("const labels =")[1].split(";")[0]))
    for it in _items():
        for n in it["nodes"]:
            assert n in keys, f"{it['id']} 节点 {n} 不在 labels 中"

def test_code_refs_point_into_tutorial_files():
    data = json.loads((ROOT / "web" / "tutorial-data.json").read_text(encoding="utf-8"))
    for it in _items():
        for ref in it["codeRefs"]:
            assert ref["path"] in data["files"], f"{it['id']} 引用缺失文件 {ref['path']}"
            line_count = data["files"][ref["path"]]["text"].count("\n") + 1
            assert 1 <= ref["start"] <= ref["end"] <= line_count, f"{it['id']} 行号越界 {ref}"
```



* [ ] **Step 2: 运行确认失败**

Run: `./.venv/bin/python -m pytest tests/test_work_items.py -v`

Expected: FAIL（work-items.json 不存在）



* [ ] **Step 3: 阅读手册并提炼生成&#x20;**`web/work-items.json`

阅读 `/Users/Doc/review/贝壳找房_AI经营分析Agent_实习复盘手册.html` 的工作一～六章节与 "工程化 / 评测体系" 章节，按上述结构提炼 7 个工作项（工作一～六 + 补充）。节点映射参考设计文档 §7.1；`io` 样例从手册 "完整 Trace" 章节或对应代码注释提炼 1\~3 个关键节点的真实输入输出；`codeRefs` 指向 tutorial-data.json 中对应源码（可用现有 lessons 的 refs 辅助定位，如 intent→intent.py、rag→retrieval.py、sql→sql\_tools.py、report→report.py、graph→runtime.py）。



* [ ] **Step 4: 运行确认通过**

Run: `./.venv/bin/python -m pytest tests/test_work_items.py -v`

Expected: PASS



***

### Task 3: 面试题库（web/interview-questions.json）

**Files:**



* Create: `web/interview-questions.json`

* Create: `tests/test_interview_questions.py`

**Interfaces:**



* Consumes: 无。

* Produces: `web/interview-questions.json` 顶层 `{"version": 1, "categories": [...], "questions": [...]}`；question：`{id, category, question, tips, answer, weight, status}`。为 Task 6 前端读取契约，**不得改名**。

- [ ] **Step 1: 写失败测试&#x20;**`tests/test_interview_questions.py`



```
import json, pathlib
ROOT = pathlib.Path(__file__).resolve().parent.parent

def _data():
    return json.loads((ROOT / "web" / "interview-questions.json").read_text(encoding="utf-8"))

def test_schema():
    d = _data()
    cats = set(d["categories"])
    ids = set()
    for q in d["questions"]:
        assert q["category"] in cats and q["status"] in ("active", "draft")
        assert q["weight"] >= 1
        assert q["question"] and q["answer"]
        assert q["id"] not in ids; ids.add(q["id"])
    assert "general" in cats

def test_at_least_ten_active():
    d = _data()
    assert sum(1 for q in d["questions"] if q["status"] == "active") >= 10
```



* [ ] **Step 2: 运行确认失败**

Run: `./.venv/bin/python -m pytest tests/test_interview_questions.py -v`

Expected: FAIL（interview-questions.json 不存在）



* [ ] **Step 3: 从手册提炼生成&#x20;**`web/interview-questions.json`

阅读手册 "高频面试追问"、"场景化面试法"、"答题易错点"、"术语与指标速查" 章节，提炼 ≥10 道 active 题：按工作项分类（intent/rag/sql/agent/memory/hallucination）+ `general`（项目定位、30 秒开场、工程化、简历写法、易错点等）。`tips` 为提示要点（先自答再展开）；`answer` 为参考回答；`weight` 初始按手册篇幅 / 重要性给 1\~5；全部 `status: "active"`。



* [ ] **Step 4: 运行确认通过**

Run: `./.venv/bin/python -m pytest tests/test_interview_questions.py -v`

Expected: PASS



***

### Task 4: 前端骨架重构（导航两个 Tab + 登录卡简化）

**Files:**



* Modify: `web/index.html`

* Modify: `web/style.css`

* Modify: `web/app.js`

**Interfaces:**



* Consumes: Task 1 的登录接口（`POST /api/login` 返回 user、`GET /api/session`）；现有 `web/learning.js`（保留源码阅读器能力）。

* Produces: 登录后前端进入默认 "实现教程" 视图；`window.Teaching`（Task 5 挂载）、`window.Interview`（Task 6 挂载）的挂载点 DOM id 在本任务中确定：`#teaching-view`、`#interview-view`、`#nav-teaching`、`#nav-interview`。

- [ ] **Step 1: 修改&#x20;**`web/index.html`**&#x20;导航为两个 Tab**

移除 `data-view="history"`、`data-view="actions"`、`data-manual`、`/docs` 四个导航入口；`#nav-workspace` 改为 `#nav-teaching`（文案 "实现教程"），新增 `#nav-interview`（文案 "高频面试题"）；`#page-crumb` 随 Tab 切换。保留登录卡但移除角色 `<select>` 与 `#password-hint`，密码输入框 `value` 置空、`placeholder="输入账号密码"`；登录卡文案改为 "学员账号登录"。



* [ ] **Step 2: 精简&#x20;**`web/app.js`

删除 `loadGraph/refreshTasks/refreshActions/watch/render/resume` 等分析链路函数及 `#run/#cancel/#approve` 绑定；`loggedIn()` 改为：调 `/api/session` 判登录态 → 显示 `#teaching-view` 与登录卡切换；`login` 提交 `{username, password}`，成功后进入默认视图。保留 `download()` 工具函数（Task 7 复用）。



* [ ] **Step 3: 在&#x20;**`index.html`**&#x20;中新增两个视图容器**

在 `<main>` 内：`<section id="teaching-view" hidden>`（四象限骨架：`#work-item-picker`、`#node-graph`、`#work-intro`、`#node-detail` 四个子区域，本任务只放空容器与标题，内容由 Task 5 渲染）与 `<section id="interview-view" hidden>`（空容器，Task 6 渲染）。`#learning-panel` 保留作为源码阅读器弹层 / 面板供右下角复用（Task 5 决定复用方式）。



* [ ] **Step 4: 启动服务做浏览器冒烟验证**

Run: `cd /Users/cocochimp/Downloads/estate_agent_langgraph_demo && ./.venv/bin/python -X utf8 launch.py`（后台）后访问 `http://127.0.0.1:8765/`

Expected: 页面加载无 JS 报错；导航只有 "实现教程 / 高频面试题"；登录卡无角色下拉、密码框为空；输入 `chaoyang/demo-chaoyang` 登录成功并显示 `#teaching-view`；未登录访问 `/api/tasks` 返回 401。



***

### Task 5: 四象限学习视图（teaching.js）

**Files:**



* Create: `web/teaching.js`

* Modify: `web/index.html`（挂 `<script src="/static/teaching.js">`）

* Modify: `web/style.css`

**Interfaces:**



* Consumes: `web/work-items.json`（Task 2）、`web/tutorial-data.json`（files 快照）、`web/app.js` 的 `labels` 映射、`web/learning.js` 源码阅读器（词法着色 / 行号 / 复制）。

* Produces: `window.Teaching = {selectWorkItem(id), selectNode(nodeName)}`（Task 5 内部联动；Task 7 导出时调用 `Teaching.exportCurrentWorkItem()`）。

- [ ] **Step 1: 实现&#x20;**`web/teaching.js`**&#x20;数据加载与工作项切换**

`fetch('/static/work-items.json')` + `fetch('/static/tutorial-data.json')` 并行加载；`selectWorkItem(id)`：更新左上 `#work-item-picker` 高亮与 `summary` → 重绘右上节点图 → 填充左下 `#work-intro`（intro 五段）→ 默认选中该工作项第一个节点并渲染右下 `#node-detail`。



* [ ] **Step 2: 实现右上角节点图渲染**

在 `#node-graph` 渲染当前工作项 `nodes` 的节点卡片链：每卡显示节点名（`labels` 映射中文）+ 一句话内容介绍（可从 `io[].note` 或 intro 关联，实现者给每个节点补一句静态说明映射）；展示 "共 N 个节点" 计数；每卡可点击 → `selectNode(node)`；当前选中节点高亮。



* [ ] **Step 3: 实现右下角&#x20;**`#node-detail`**&#x20;渲染**

`selectNode(node)`：查找该工作项 `io` 中 `node` 匹配项 → 展示输入 / 输出 JSON（`<pre>`，textContent）；匹配 `codeRefs` 中引用该节点的片段 → 复用 `learning.js` 的源码阅读器渲染（行号、词法着色、复制按钮、`查看完整文件`）；**无 io 且无 codeRefs 的节点显示 "该步骤无可展示的输入输出与代码"，右下角该区域留空提示**（符合 spec：无内容可省略展示）。



* [ ] **Step 4: 挂载并浏览器验证**

`index.html` 挂载 teaching.js；登录后默认 `selectWorkItem('work-1')`。验证：切换工作一～六 + 补充项 → 四区联动更新；点节点 → 右下角切换为该节点 IO + 代码；无内容节点显示占位提示；控制台无报错。



***

### Task 6: 高频面试题视图（interview.js）

**Files:**



* Create: `web/interview.js`

* Modify: `web/index.html`（挂 `<script src="/static/interview.js">`）

* Modify: `web/style.css`

**Interfaces:**



* Consumes: `web/interview-questions.json`（Task 3）。

* Produces: `window.Interview = {shuffle(), render(category), exportCurrent()}`（Task 7 导出复用 `exportCurrent()`）。

- [ ] **Step 1: 实现分类浏览与随机抽题**

`fetch('/static/interview-questions.json')`；左侧 / 顶部按 `categories` 渲染分类筛选（含 "全部"）；`shuffle()` 从当前筛选集随机抽一题显示题目；按钮 "显示提示" 展开 `tips`、"显示参考回答" 展开 `answer`；"下一题" 再抽；支持只抽 `status=active` 的题。



* [ ] **Step 2: 浏览器验证**

切换到 `#nav-interview`：分类可筛选；随机抽题不重复于当前已展示（实现者用 Fisher–Yates 洗牌取序列）；提示 / 答案可展开收起；无控制台报错。



***

### Task 7: 导出可编辑 HTML

**Files:**



* Create: `web/export.js`

* Modify: `web/index.html`（挂 `<script src="/static/export.js">`；在 `#teaching-view` 与 `#interview-view` 各加 "导出 HTML" 按钮）

* Modify: `web/style.css`

**Interfaces:**



* Consumes: `window.Teaching.exportCurrentWorkItem()` 数据、`window.Interview.exportCurrent()` 数据、`web/app.js` 的 `download()`。

* Produces: `export.js` 内部函数 `buildEditableHtml(title, sections) -> string`（单文件自包含：内联 `<style>`，正文 `contenteditable="true"`，含 "保存草稿" 按钮（触发下载当前编辑后 HTML）与 "生成独立新文件" 按钮）。

- [ ] **Step 1: 实现&#x20;**`buildEditableHtml(title, sections)`

入参 `sections: [{heading, html}]`—— 所有正文一律先经转义（实现 `escapeHtml`，替换 `& < > " '`）再组装，禁止原样拼接数据文本。模板含：`<html lang="zh-CN">`、内联样式（继承深蓝基调的极简版）、`contenteditable` 正文、顶栏两个按钮（保存草稿 = Blob 下载当前 innerHTML；生成新文件 = 打开 `document.write` 副本）。参考手册的可编辑机制。



* [ ] **Step 2: 实现教程导出**

`Teaching.exportCurrentWorkItem()`：组装当前工作项标题、summary、intro 五段、节点清单、各节点 IO JSON（`<pre>`）+ 代码片段（从 tutorial-data.json 取文本，textContent 转义），调用 `buildEditableHtml` 并 `download()` 为 `工作项-<id>.html`。



* [ ] **Step 3: 面试题导出**

`Interview.exportCurrent()`：组装当前筛选分类的全部题目（question/tips/answer），调用 `buildEditableHtml` 下载为 `面试题-<category>.html`。



* [ ] **Step 4: 验证导出物可编辑**

Run: 浏览器中点击两个导出按钮 → 下载 HTML → 用 `Read` 打开下载文件检查：单文件自包含（无外部依赖）、含 `contenteditable`、含含 `<script>alert(1)</script>` 的样例面试题文本被转义为文本而非可执行脚本（`<` 转义为 `&lt;`）。

Expected: 文件可独立打开、正文可点击编辑、样例脚本不执行。



***

### Task 8: 集成回归与交付

**Files:**



* Modify: 按回归结果修复（如 `web/style.css`、`web/teaching.js` 细节）

* 不新增文件（除非回归发现必须项）

**Interfaces:**



* Consumes: Task 1\~7 全部产物。

* Produces: 可交付的完整教学网站。

- [ ] **Step 1: 全量后端测试**

Run: `cd /Users/cocochimp/Downloads/estate_agent_langgraph_demo && ./.venv/bin/python -m pytest tests/ -v`

Expected: 全部 PASS（含原 test\_api.py、test\_agent.py 等）



* [ ] **Step 2: 全流程浏览器冒烟**

重启服务（`./.venv/bin/python -X utf8 launch.py`）后逐项验证：登录（错误密码 401 提示、正确密码进入默认实现教程）→ 四象限联动（切换工作项、点节点跳转、右下角 IO / 代码、无内容节点占位）→ 高频面试题（分类、随机抽题、提示 / 答案）→ 两个导出按钮下载且导出物可打开可编辑；页面无控制台报错；导航仅两个 Tab。

Expected: 全部符合设计文档验收标准 §10。



* [ ] **Step 3: 更新设计文档状态并交付**

将设计文档 `docs/superpowers/specs/2026-10-11-teaching-website-design.md` 状态改为 "已实施"，并在交付说明中写明：启动方式（`./.venv/bin/python -X utf8 launch.py`）、默认登录账号、如何修改 `accounts.json` 管理学员账号、新增文件清单（work-items.json/interview-questions.json/teaching.js/interview.js/export.js）。