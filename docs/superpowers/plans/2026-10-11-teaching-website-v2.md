# 教学网站 V2 改版 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 将教学网站 V1（四象限蓝白、7 工作项）重构为 V2：5 个工作项与简历模版一一对应、四模块纵向布局、节点浮窗展示 IO/代码、全站旧手册墨绿青主题、面试题分类对齐。

**Architecture:** 纯前端重构 + 数据重写。后端不动（`/api/graph` 现成提供分析执行图 SVG）；教学内容全部数据驱动（`web/work-items.json` V2、`web/interview-questions.json` V2）；`teaching.js` 承担四模块渲染与浮窗（复用 V1 源码阅读器 colorLine/renderCode）。

**Tech Stack:** 原生 JS + CSS + FastAPI 静态托管（无新依赖）。

**Spec:** `docs/superpowers/specs/2026-10-11-teaching-website-v2-design.md`（已获用户批准）

## Global Constraints

- 工作项标签共 **5 个**，标题与「实习经历模版」5 条工作内容一一对应；每条含简历原文摘要与量化指标徽章（数字与简历原文一致：86.8→94.1 / 79.0→94.0 / 90.6 / 96.1 / P95 5.2s→3.8s）。
- work-1 含 2 个子主题（意图理解、Context/Memory），内容来自手册 work1/memory 章节。
- 模块 4 内容七段式完整：scene/problem/locate/action/why/result/qa，qa 非空（教学用）。
- 全站统一旧手册主题（墨绿青 #245d65/#087f8c/#17324d/#2d7c61 + 点缀 #9c4a1e/#c7682e + 底色 #fbfcfc/#e7f1f2）；高频面试题 Tab 同主题。
- 面试题分类 = `agent/rag/sql/hallucination/evals/general` 6 类；总数 ≥ 25；原 intent/memory 题并入 agent，工程化/评测类并入 evals。
- 导航仅两 Tab（实习项目教程 / 高频面试题）；页面无控制台报错。
- 静态资源引用统一版本参数 `?v=20261011b`。
- 后端 `estate_agent/*`、`accounts.json`、既有 `tests/*` 不改；`/api/graph` 复用不新增接口。

## Review Focus

1. **codeRefs 指向失效** — work-items.json V2 的 `codeRefs[].path` 必须在 `web/tutorial-data.json` 的 `files` 键中存在，否则导出/浮窗代码区 404。→ Task 1 测试断言。
2. **面试题归类丢失** — 重归类后每题的 `category` 必须在新 `categories` 数组中；agent 分类必须包含原 intent(3)+memory(3) 题，总数 ≥ 25。→ Task 2 测试断言。
3. **七段式缺段** — 任一工作项 `intro` 缺 scene/problem/locate/action/why/result 或 qa 为空，模块 4 渲染空白。→ Task 1 测试断言全部非空。
4. **节点名超 labels** — `nodes[]` 中的每个节点必须存在于 `web/app.js` 的 `labels` 映射，否则显示英文原名。→ Task 1 测试用 labels 清单断言。
5. **/api/graph 失败降级** — 模块 2 在接口失败/SVG 为空时显示占位说明，不阻塞其余模块渲染。→ Task 5 实现 + Task 7 冒烟。

---

### Task 1: work-items.json V2（5 工作项数据重写）

**Files:**
- Create: `web/work-items.json`（整体重写）
- Test: `tests/test_work_items_v2.py`

**Interfaces:**
- Consumes: 手册章节（work1/work2/work3/work4/memory/quality/engineering/eval/trace）、`web/tutorial-data.json`（files 键）、`web/app.js` labels 清单
- Produces: `workItems` 数组，每项结构：
  `{id, title, short, summary, resume:{label,text,metrics}, subTopics:[{title,node}]|[], nodes:[], intro:{scene,problem,locate,action,why,result,qa:[]}, io:[{node,input,output,note}], codeRefs:[{path,start,end,note}]}`
  id 固定：`work-1`(Agent Runtime/工作流) / `work-2`(企业 RAG) / `work-3`(Tool Calling 查数) / `work-4`(可信生成/幻觉治理) / `work-5`(Evals & Observability)

- [ ] **Step 1: 写失败测试 `tests/test_work_items_v2.py`**

断言（值取自 spec §5.1）：
```python
def test_v2_has_exactly_five_items():
    wi = json.load(open('web/work-items.json'))
    items = wi['workItems']
    assert [i['id'] for i in items] == ['work-1','work-2','work-3','work-4','work-5']
    assert [i['title'].split(' · ')[0] for i in items] == ['工作一','工作二','工作三','工作四','工作五']

def test_resume_metrics_match_resume_template():
    # 简历锚点量化指标存在且与简历原文数字一致
    w1 = next(i for i in items if i['id']=='work-1')
    assert '86.8%' in w1['resume']['metrics'] and '94.1%' in w1['resume']['metrics']
    assert '73.5%' in w1['resume']['metrics'] and '89.2%' in w1['resume']['metrics']
    w4 = next(i for i in items if i['id']=='work-4')
    assert '96.1%' in w4['resume']['metrics']
    w5 = next(i for i in items if i['id']=='work-5')
    assert 'P95' in w5['resume']['metrics']

def test_seven_part_intro_complete():
    for item in items:
        for k in ['scene','problem','locate','action','why','result']:
            assert item['intro'][k] and item['intro'][k].strip()
        assert len(item['intro']['qa']) >= 1

def test_work1_subtopics_present():
    w1 = next(i for i in items if i['id']=='work-1')
    assert len(w1['subTopics']) == 2
    assert '意图' in w1['subTopics'][0]['title'] and 'Memory' in w1['subTopics'][1]['title']

def test_nodes_in_labels():
    labels = {"understand","clarify","agent_node","schema_retrieval","query_sql","calculate","analyze","rag_search","generate_report","validate","human_approval","execute_action","finish","retry_node","checkpoint_gate"}
    for item in items:
        for n in item['nodes']:
            assert n in labels, n
    # 节点映射与 spec §5.1 一致
    assert set(next(i for i in items if i['id']=='work-1')['nodes']) == {"understand","clarify","agent_node","checkpoint_gate","retry_node","execute_action","finish"}
    assert set(next(i for i in items if i['id']=='work-2')['nodes']) == {"rag_search"}

def test_code_refs_exist_in_tutorial_files():
    files = json.load(open('web/tutorial-data.json'))['files']
    for item in items:
        for ref in item['codeRefs']:
            assert ref['path'] in files, ref['path']
            assert ref['start'] >= 1 and ref['end'] > ref['start']
```

- [ ] **Step 2: 运行测试确认失败**

Run: `./.venv/bin/python -m pytest tests/test_work_items_v2.py -v`
Expected: FAIL（work-items.json 仍为 V1 7 项结构）

- [ ] **Step 3: 重写 `web/work-items.json`**

从手册章节提取（七段式原文尽量保留手册措辞，量化指标核对简历模版）：
- work-1 ← work4（主链路：understand/agent_node/checkpoint/retry/execute/finish）+ work1 子主题「意图理解与结构化输出」+ memory 子主题「Context 与 Memory」；io 取 understand/agent_node 真实样例；codeRefs 指向 runtime.py/intent.py
- work-2 ← work2；nodes=[rag_search]；io 取 rag_search；codeRefs 指向 retrieval.py
- work-3 ← work3；nodes=[schema_retrieval,query_sql,calculate,analyze]；io 取 query_sql；codeRefs 指向 sql_tools.py
- work-4 ← quality；nodes=[generate_report,validate,human_approval]；io 取 validate；codeRefs 指向 report.py/runtime.py
- work-5 ← engineering+eval+trace；nodes=[]；resume 指标 500 条用例/P95 3.8s/-28% Token；io 仅 trace 样例或空；codeRefs 指向 evals 相关文件（若 tutorial-data 有）
- 每项 `summary` 一句话；`resume.label` 用简历原文条目名；`resume.text` 用简历原文描述（可截断）

- [ ] **Step 4: 运行测试确认通过**

Run: `./.venv/bin/python -m pytest tests/test_work_items_v2.py -v`
Expected: PASS（6 用例全绿）

- [ ] **Step 5: 验证（项目非 git 仓库，以验证替代 commit）**

Run: `./.venv/bin/python -m pytest tests/ -q`
Expected: 全量 PASS（原 63 + 新 6）

---

### Task 2: interview-questions.json V2（6 分类重归类 + evals 补题）

**Files:**
- Modify: `web/interview-questions.json`
- Test: `tests/test_interview_questions_v2.py`

**Interfaces:**
- Consumes: Task 1 之后的 `web/work-items.json`（分类锚点可选）、手册 qa/engineering/eval 章节（evals 补题素材）
- Produces: `categories = ["agent","rag","sql","hallucination","evals","general"]`；`questions[]` 每题 `category` 在 6 类内

- [ ] **Step 1: 写失败测试 `tests/test_interview_questions_v2.py`**

```python
def test_six_categories_and_total():
    data = json.load(open('web/interview-questions.json'))
    assert data['categories'] == ['agent','rag','sql','hallucination','evals','general']
    active = [q for q in data['questions'] if q['status']=='active']
    assert len(active) >= 25

def test_categories_valid_and_merged():
    data = json.load(open('web/interview-questions.json'))
    valid = set(data['categories'])
    for q in data['questions']:
        assert q['category'] in valid
    cats = Counter(q['category'] for q in data['questions'] if q['status']=='active')
    assert cats['agent'] >= 8          # 原 intent(3)+memory(3)+agent(5) 至少 11
    assert cats['evals'] >= 3          # 补题下限
    assert 'intent' not in cats and 'memory' not in cats
```

- [ ] **Step 2: 运行测试确认失败**

Run: `./.venv/bin/python -m pytest tests/test_interview_questions_v2.py -v`
Expected: FAIL（仍 7 类）

- [ ] **Step 3: 重归类 `web/interview-questions.json`**

- intent 3 题、memory 3 题、agent 5 题 → 全部 `category="agent"`
- rag 6、sql 4、hallucination 2 → 不变
- general 6 → 逐题判断：工程化/评测/Trace/性能类移入 `evals`，其余留 general
- 从手册 engineering/eval 章节提炼 2~4 题补 `evals`（如「P95 延迟怎么优化」「500 条回归用例怎么分层」），保证 evals ≥ 3、总数 ≥ 25
- `version` 更新为 "2.0"

- [ ] **Step 4: 运行测试确认通过**

Run: `./.venv/bin/python -m pytest tests/test_interview_questions_v2.py -v`
Expected: PASS

- [ ] **Step 5: 验证**

Run: `./.venv/bin/python -m pytest tests/ -q`
Expected: 全量 PASS

---

### Task 3: style.css 全站换肤（旧手册主题 + 四模块布局 + 浮窗）

**Files:**
- Modify: `web/style.css`（整体重写 :root 色板与组件，保留响应式）

**Interfaces:**
- Produces: 全局 CSS 变量（--ink/--muted/--brand/--brand-deep/--accent/--paper/--surface/--line 等映射旧手册色板）；组件类 `.hero/.callout/.warn/.good/.badge/.story/.story-head/.story-script/.case/.resume/.tabs-bar/.exec-graph/.node-chain/.story-content/.node-dialog` 等

- [ ] **Step 1: 提取旧手册 CSS 主题（只读）**

从 `/Users/Doc/review/贝壳找房_AI经营分析Agent_实习复盘手册.html` 提取 `<style>`，记录 hero/callout/warn/good/story/case/badge/resume 的配色与排版（背景、边框、圆角、字体）。

- [ ] **Step 2: 重写 `web/style.css`**

- `:root` 色板替换为旧手册色：brand `#245d65`、brand-deep `#17324d`、teal `#087f8c`、green `#2d7c61`、accent `#9c4a1e`、accent-light `#c7682e`、paper `#fbfcfc`、surface `#fff`、tint `#e7f1f2`、line `#cfe0e2`
- 组件样式按旧手册 CSS 迁移（保留 V1 中仍有用的布局：sidebar/header/login/interview-layout 改色）
- 新增四模块布局：`.tabs-bar`（横向工作项标签）、`.exec-graph`（压缩高度 + 横向滚动）、`.node-chain`（节点卡片链）、`.story-content`（七段式卡片）、`.node-dialog`（`<dialog>` 浮窗：IO JSON + 代码区）
- 保留响应式断点（≤1200/≤1000/≤780/≤480）
- 静态资源引用方（index.html）稍后统一换 `?v=20261011b`

- [ ] **Step 3: 语法自检**

Run: `python3 -c "css=open('web/style.css').read(); assert css.count('{')==css.count('}'), 'brace mismatch'; print(len(css),'chars ok')"`
Expected: 花括号匹配、无报错

---

### Task 4: index.html 四模块结构 + app.js 联动 + interview.js 文案

**Files:**
- Modify: `web/index.html`、`web/app.js`、`web/interview.js`

**Interfaces:**
- Consumes: Task 3 样式类；V1 `web/app.js` 的 labels/登录/视图切换
- Produces: DOM 容器 id：`#work-tabs`、`#work-resume`（模块1）、`#exec-graph`（模块2）、`#node-chain`、`#node-count`（模块3）、`#story-content`、`#story-subtopics`（模块4）、`#node-dialog`（浮窗）；`window.Teaching.init/selectWorkItem/getCurrent/getNodeRefs`；`window.Interview.init/shuffle`；事件 `teaching:work`

- [ ] **Step 1: 重写 `web/index.html` 的 teaching-view 为四模块结构**

- 标题「实习工作项学习」、面包屑文案「实习项目教程」、按钮文案「导出本工作项 HTML」
- 模块1：`#work-tabs`（横向 5 标签容器）+ `#work-resume`（简历摘要与指标徽章）
- 模块2：`#exec-graph`（分析执行图容器，含说明行）
- 模块3：`#node-chain` + `#node-count`
- 模块4：`#story-subtopics`（work-1 子主题 tab）+ `#story-content`
- 浮窗：`<dialog id="node-dialog">`（含关闭按钮、标题、内容区）
- script 引用 `app.js/teaching.js/interview.js/export.js?v=20261011b`

- [ ] **Step 2: 修改 `web/app.js`**

- 保留 labels/登录/登出/视图切换逻辑；`page-crumb` 文案改为「实习项目教程」/「高频面试题」
- 移除 V1 已废弃的 `#work-item-picker/#work-summary/#work-intro/#node-graph/#node-detail` 相关调用（由 teaching.js 全权接管）

- [ ] **Step 3: 修改 `web/interview.js` catNames**

- `catNames` 改为 6 类文案：`agent:'工作一 · Agent Runtime（含意图理解/Context-Memory）'`、`rag:'工作二 · 企业知识库 RAG'`、`sql:'工作三 · Tool Calling 与智能查数'`、`hallucination:'工作四 · 可信生成与幻觉治理'`、`evals:'工作五 · Evals & Observability'`、`general:'汇总 · 项目与工程'`

- [ ] **Step 4: 静态验证**

Run: `curl -s http://127.0.0.1:8765/ | grep -c 'work-tabs\|exec-graph\|node-chain\|story-content\|node-dialog'`
Expected: ≥ 4（新容器存在）；`grep -o 'id="[a-z-]*"' web/index.html` 无 V1 残留 id（work-item-picker 等）

---

### Task 5: teaching.js 四模块渲染与节点浮窗

**Files:**
- Modify: `web/teaching.js`（整体重写为四模块渲染）

**Interfaces:**
- Consumes: Task 1 数据（V2 结构）、Task 3 样式、Task 4 DOM id、`/api/graph`（SVG）
- Produces: `window.Teaching.{init,selectWorkItem,getCurrent,getNodeRefs}`；渲染模块1~4；浮窗打开函数 `openNodeDialog(name)`

- [ ] **Step 1: 写失败测试（DOM 契约，用 node 静态断言）**

创建 `tests/test_teaching_contract.py`（纯数据/字符串级契约，不跑浏览器）：
```python
def test_teaching_js_exports_required_api():
    js = open('web/teaching.js', encoding='utf-8').read()
    for token in ['window.Teaching', 'selectWorkItem', 'getCurrent', 'getNodeRefs', 'openNodeDialog', 'renderStory', 'renderNodeChain', 'renderExecGraph']:
        assert token in js
def test_teaching_js_reads_v2_container_ids():
    js = open('web/teaching.js', encoding='utf-8').read()
    for cid in ['work-tabs', 'work-resume', 'exec-graph', 'node-chain', 'node-count', 'story-subtopics', 'story-content', 'node-dialog']:
        assert cid in js
```

- [ ] **Step 2: 运行确认失败**

Run: `./.venv/bin/python -m pytest tests/test_teaching_contract.py -v`
Expected: FAIL（teaching.js 仍为 V1 四象限逻辑）

- [ ] **Step 3: 重写 `web/teaching.js`**

- `loadData()`：读 `work-items.json?v=20261011b` + `tutorial-data.json`
- `renderTabs()`：模块1 5 个横向标签（title.split(' · ')[1] 短名），选中态 + 简历摘要（`resume.text`）+ 指标徽章（`resume.metrics` 拆分展示）；点击 → `selectWorkItem(id)` + hash `#work-N`
- `renderExecGraph()`：模块2 fetch `/api/graph` → `{svg}` 插入 `#exec-graph`（innerHTML 中 SVG 由后端生成，仅含静态节点与边）；失败/空 → 占位说明（Review Focus 5）
- `renderNodeChain()`：模块3 节点卡片链（labels 中文名 + io.note 一句话），`#node-count`；无节点（work-5）→ 占位「该工作项为工程化与评测，不绑定执行节点」
- `renderStory()`：模块4 七段式卡片（业务现场/遇到问题/怎么定位/我做了什么/为什么这样选/结果怎么讲/被追问时=qa 列表）；work-1 显示 `#story-subtopics` 子主题 tab（意图理解 / Context-Memory / 主链路），切换改变内容区前缀说明
- `openNodeDialog(name)`：`<dialog>` showModal，标题=labels[name]，内容=该节点 io（输入/输出 JSON）+ codeRefs 实例代码（复用 V1 colorLine/renderCode），无内容节点 → 占位；关闭按钮 + ESC
- 保留 `getCurrent/getNodeRefs`（export.js 依赖）；`init()` 默认 `selectWorkItem('work-1')`
- 静态资源 fetch 带版本参数

- [ ] **Step 4: 运行确认通过**

Run: `./.venv/bin/python -m pytest tests/test_teaching_contract.py -v`
Expected: PASS（2 用例）

- [ ] **Step 5: 快速浏览器冒烟（本任务级）**

重启服务后浏览器验证：登录 → 默认 work-1 → 模块1 5 标签 + 简历徽章、模块2 SVG 出现、模块3 节点链、模块4 七段式 + 子主题 tab；点击节点弹浮窗见 IO 与代码。
Expected: 四模块渲染正常、浮窗可开可关、console 无报错

---

### Task 6: export.js 适配 V2

**Files:**
- Modify: `web/export.js`

**Interfaces:**
- Consumes: Task 5 `window.Teaching.getCurrent()`（V2 结构：resume/subTopics/intro/io/codeRefs）、`web/tutorial-data.json` files
- Produces: 工作项学习页导出（单文件 contenteditable，含简历条目 + 七段式 + 节点 IO/代码，V2 主题内联样式）；面试题导出（不变逻辑，仅主题色更新）

- [ ] **Step 1: 写失败测试 `tests/test_export_contract.py`**

```python
def test_export_js_handles_v2_structure():
    js = open('web/export.js', encoding='utf-8').read()
    for token in ['resume', 'subTopics', 'intro.qa', 'contenteditable', 'node-dialog']:
        assert token in js
```

- [ ] **Step 2: 运行确认失败**

Run: `./.venv/bin/python -m pytest tests/test_export_contract.py -v`
Expected: FAIL

- [ ] **Step 3: 修改 `web/export.js`**

- `workBody()` 重构：输出 = 简历卡（label + text + metrics 徽章）→ 七段式卡片（scene…result + qa 追问列表）→ 节点 IO（每节点 details + 输入/输出 JSON）→ 实例代码（codeRefs，行号区间）
- shell() 内联样式更新为 V2 主题（墨绿青）
- 面试题导出逻辑不变（分类文案由 interview.js 输出）

- [ ] **Step 4: 运行确认通过**

Run: `./.venv/bin/python -m pytest tests/test_export_contract.py -v`
Expected: PASS

- [ ] **Step 5: 导出文件实际生成验证**

浏览器点击「导出本工作项 HTML」，检查下载文件字节数 > 10KB 且含 `contenteditable`。
Expected: 下载成功、文件可打开

---

### Task 7: 集成回归与交付

**Files:**
- Modify: 按回归结果修复（如 `web/style.css`、`web/teaching.js` 细节）
- Modify: `docs/superpowers/specs/2026-10-11-teaching-website-v2-design.md`（状态 → 已实施 + V2 交付说明）

**Interfaces:**
- Consumes: Task 1~6 全部产物

- [ ] **Step 1: 全量后端测试**

Run: `cd /Users/cocochimp/Downloads/estate_agent_langgraph_demo && ./.venv/bin/python -m pytest tests/ -v`
Expected: 全部 PASS（原 63 + 新增 test_work_items_v2/test_interview_questions_v2/test_teaching_contract/test_export_contract）

- [ ] **Step 2: 重启服务 + 全流程浏览器冒烟**

重启（`./.venv/bin/python -X utf8 launch.py`）后逐项验证：
登录（错误密码 401、正确进入实习项目教程默认 work-1）→ 模块1 五标签/简历徽章 → 模块2 分析执行图 SVG → 模块3 节点链 → 点击节点浮窗（IO+代码）→ work-1 子主题切换 → 切换 work-5（无节点占位）→ 高频面试题 6 分类 → 随机抽题/提示/答案 → 导出×2（下载成功）；页面无控制台报错；导航仅两 Tab。
Expected: 全部符合设计文档验收标准 §10

- [ ] **Step 3: 更新设计文档状态 + V2 交付说明**

状态改「已实施」；在文档追加 §14 V2 交付说明：启动方式、默认账号、新增/修改文件清单、验证情况、遗留说明（V1 四象限文件已由 V2 替代、面试题库可继续迭代、上线建议）。

---

## 执行记录（Native，2026-10-11）

- `V2 Task 1: Ruling: 删除 tests/test_work_items.py` — V1 测试断言旧数据契约（≥6 项），数据升级 V2 后必红；其 3 条断言被 test_work_items_v2.py 的 7 条完全覆盖 — 成本：无（覆盖充分）。Task 1 完成：全量 67 passed。
- `V2 Task 2: Ruling: 面试题重归类` — intent(3)+memory(3)+agent(5)→agent(11)；general 中 Evals 相关 3 题→evals、ACL→rag、2 题留 general；补 2 题 evals（Trace vs 日志、P95 优化路径）— 与用户「6 分类对齐」一致 — 成本：题目归类口径可再调。Task 2 完成：全量 70 passed。
- `V2 Task 3: Ruling: style.css 整体重写` — V1 蓝白主题全部替换为旧手册墨绿青主题 + 四模块/浮窗样式，V1 独有类（overview-strip/workbench-tabs/quad-panel 等）不再保留 — 与用户「全站统一旧手册主题」一致 — 成本：若后续要还原 V1 需从旧文件恢复。
- `V2 Task 5: Ruling: 子主题标题去重` — work-items.json 的 subTopics.title 原带「子主题 · 」前缀，渲染时又加前缀导致「子主题 · 子主题」重复；改为数据存纯标题、渲染统一加前缀 — 成本：无。Task 3~6 完成（style.css/index.html/app.js/interview.js/teaching.js/export.js）。
- `V2 Task 7: 集成回归通过` — 全量 pytest 70 passed；浏览器冒烟：四模块渲染、5 工作项切换、节点浮窗 IO+代码、工作5 无图降级、子主题切换、面试题 6 分类抽题、工作项导出 HTML 结构校验（11 项全绿）；设计文档状态改「已实施」+ 追加 §14 交付说明。Task 7 完成。

---

## V3 执行记录（2026-10-11，Native 内联执行）

- `V3 Task 1: 数据提取` — 从旧手册 22 章节提取：导读 13 章 → `web/guide-data.json`（21KB HTML）；工作章节 → `work-items.json` 每项 `introHtml`（work-1=work4 7.6KB + 子主题 work1 3.4KB/memory 2.3KB；work-2=work2 9.5KB；work-3=work3 3.4KB；work-4=quality 2.3KB；work-5=engineering+eval+trace 9.9KB）。提取清洗：去 h2/script/空白。全量 70 passed。
- `V3 Task 2: 前端改造` — index.html 三 nav（项目导读置顶）+ hero 深色卡 + exec-row 并排 + guide-view；teaching.js renderStory 改完整章节 innerHTML + highlightGraph（data-node 匹配 item.nodes 高亮）；新增 guide.js；export.js 内容介绍改完整章节；style.css 追加 hero/exec-row/legend-active/guide 布局/手册组件样式（mini/grid/case/table/pre/qa 等）。全量 70 passed。
- `V3 Task 3: 回归交付` — 浏览器冒烟全绿（见 V3 设计文档 §验证结果）；导出工作一学习页 47KB 10 项结构校验全绿；新增 V3 设计文档并置「已实施」。
- `V3 Ruling: work-4 章节较短（2.3KB）` — quality 章节原文如此，未人为扩充 — 若教学需要可后续补写，成本：一次数据编辑。
- `V3 Ruling: work-5 合并 engineering+eval+trace 三段` — 用户要求内容照搬完整，工作五（Evals & Observability）对应手册三章，直接拼接 — 成本：章节边界处可能需手动分隔，当前顺序工程化→评测→Trace 与简历条目一致。
