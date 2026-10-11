# 教学网站 V4 设计 · 高频面试题重构（已实施）

日期：2026-10-11

## 意图与背景
学员面试辅导需要一套「面试题库」：项目面试题必须结合简历 5 个工作项，回答按六段式模板（业务现场→出现问题→定位原因→我的动作→为什么这样选→结果/指标）；Agent / RAG / LLM 八股题覆盖常问原理；高频面试题后续用学员真实录音沉淀。删除 V2 的随机抽题逻辑，改为 P2 形态（问题点开 = 要点说明 + 参考问答）。

## 目标 / 非目标
- 目标：新增「面试」父导航（与「学习」同纬度）；5 个子题库；项目面试题按工作项分组（每工作项 ≥10 题）；Agent/RAG/LLM 各 ≥20 题八股；导出适配。
- 非目标：不做在线练习/评测交互；不保留随机抽题；「高频面试题」本轮仅占位。

## 数据设计
新文件 `web/interview-topics.json`：
```json
{"version":"4.0","topics":[
  {"id":"project","title":"项目面试题","desc":"…","groups":[
     {"id":"work-1","title":"工作一 · Agent Runtime / 工作流","questions":[{q,points[],qa[{q,a}]}]}, …]},
  {"id":"agent","title":"Agent 八股","questions":[…]},
  {"id":"rag","title":"RAG 八股","questions":[…]},
  {"id":"llm","title":"LLM 八股","questions":[…]},
  {"id":"recording","title":"高频面试题","questions":[]}]}
```
- 旧 `interview-questions.json`（31 题）保留未删，作为迁移源与兼容旧测试。
- 题量：project 54（work1=14 / work2=10 / work3=10 / work4=10 / work5=10）、agent 22、rag 22、llm 22、recording 0。共 120 题。
- 旧 31 题→新工作项映射（id 级）：work1 = q-intent-01/02/03、q-agent-01..05、q-memory-01/02/03、q-general-01 + 2 新；work2 = q-rag-01..06、q-general-06 + 3 新；work3 = q-sql-01..04 + 6 新；work4 = q-hallucination-01/02 + 8 新；work5 = q-evals-01/02、q-general-02/03/04/05 + 4 新。

## 前端设计（已实施）
- `index.html`：侧边栏拆「学习」（项目导读 / 实习项目）与「面试」（面试题库）两区；interview-view 头部改「INTERVIEW PREP / 面试题库」；左侧子题库列表 + 右侧分组 tabs + 问题列表；删除 `interview-shuffle` 按钮。
- `interview.js`：整体重写——5 子题库渲染（含题数徽标）；项目面试题渲染六段式模板卡 + 5 工作项分组 tabs；问题卡 = `<details>` 展开，含「要点说明」（points 列表）与「参考问答」（qa 多对）；recording 显示占位卡；导出挂 `getCurrentTopic()` / `getActiveQuestions()`。
- `export.js`：interviewBody 适配 `{q,points,qa}`，导出当前子题库（文件名=子题库名_练习清单.html）。
- `app.js`：crumb 文案「面试题库」；视图切换逻辑不变。
- `style.css`：新增 .answer-template / .interview-group-tabs / .group-tab / .iq-card / .iq-details / .iq-body / .iq-points / .iq-qa / .iq-pair 等样式。

## 测试
- 新增 `tests/test_interview_topics_v4.py`：5 主题顺序与数量（项目每工作项 ≥10、Agent/RAG/LLM ≥20）、题目结构（q/points/qa）、recording 占位空数组。
- 基线 70 → 73 passed（旧 test_interview_questions_v2.py 仍绿，旧文件未删）。
- 浏览器冒烟（Edge bu）：登录后「面试题库」5 子题库渲染；项目面试题六段式模板 + 5 分组 + 14 题列表；展开卡要点+问答内容正确；Agent 八股 22 题；recording 占位；teaching/guide 视图无回归；无随机抽题按钮。冒烟版本参数 `?v=20261011h`（script src 同步 h）。

## Rulings
- 旧 interview-questions.json 保留不删（旧测试与迁移可溯源），前端不再引用。
- interview-topics.json 顶层包 `{"version","topics"}`（规划目标格式）。
- 导出面试题粒度 = 当前子题库（跟随页面当前所选子题库与分组），文件名为子题库标题。

## 待办（后续迭代）
- 「高频面试题」子题库内容：等学员真实面试录音/记录后补充 questions（保持 {q,points,qa} 结构）。
- 面试题可按实际面试反馈持续优化项目题与八股题内容。

---

## V4.1 第二轮迭代（2026-10-11，已完成）

### 用户调整三点（截图确认）
1. **删除「实习项目」页顶部标题区**（INTERNSHIP PROJECT TUTORIAL + 导出本工作项按钮）；**导出入口迁移到「项目导读」页**，导出内容 = hero 卡 + 全部 13 章，样式沿用旧手册墨绿青主题、contenteditable 可编辑，供学员自行修改。
2. **面试子题库全部平铺为页面顶部 tab**，顺序固定：项目面试题 → 高频面试题 → Agent 八股 → RAG 八股 → LLM 八股（高频面试题从末位移到第 2 位）。
3. **项目面试题参考答案严格按六段式模板**（业务现场→出现问题→定位原因→我的动作→为什么这样选→结果/指标）重写为完整第一人称故事，每题展开后能支撑讲述 5-10 分钟（批评 V4 答案太短）。

### 数据（interview-topics.json v4.1）
- 54 题项目面试题全部重写为六段式完整答案：work1 14 题 / work2 10 题 / work3 10 题 / work4 10 题 / work5 10 题；每题 `qa[0].a` = 六段第一人称故事（每段 3-6 句、含量化数字），`points` 同步更新为六段式要点。
- topics 顺序重排为 `['project','recording','agent','rag','llm']`。

### 前端
- `index.html`：teaching-view 删除顶部 page-heading（含 export-work）；导读页 page-heading 追加 `#export-guide` 导出按钮；interview-view 改为顶部平铺 `#interview-cats.interview-cats-h`。
- `teaching.js`：删除 `el('export-work').disabled` 引用（修复 null 报错）。
- `interview.js`：新增 `renderAnswer()`——六段式答案按 "\nN." 拆成带编号的 `.iq-step` 小节（段号+标签+正文），八股短答案保持整段。
- `export.js`：新增 `Export.guide()`（hero+13 章 → `项目导读_实习复盘手册.html`）；interviewBody 导出六段式分段（`.q-step`）；bind 改为 export-guide / export-interview；修复 `getActive()` → `getActiveQuestions()`。
- `style.css`：新增 `.interview-cats-h` 平铺样式（胶囊 tab + 题数徽标）、`.iq-steps/.iq-step/.iq-step-no/.iq-step-label/.iq-step-text`。
- script src 版本 `?v=20261011l`。

### 测试
- `tests/test_interview_topics_v4.py`：首条断言改为新顺序 `['project','recording','agent','rag','llm']`；新增 `test_project_six_stage_answers`（每题 ≥6 段、段号 1-6 齐全、回答 ≥400 字）。
- 全量 74 passed（73 + 新增六段式断言）。

### 浏览器冒烟（Edge bu，?v=20261011l）
- 实习项目页：无顶部标题区、无导出按钮，5 工作项 + 指标 chips + 执行图正常。
- 面试页：顶部平铺 5 tab 顺序正确（项目面试题54/高频面试题0/Agent 22/RAG 22/LLM 22）；六段式模板卡 + 5 分组；展开卡渲染 6 段小节（toggle=收起）。
- 导读页：#export-guide 存在，点击下载 `项目导读_实习复盘手册.html`（47KB，hero×3 + 13 章 + contenteditable×16）。
- 面试导出：`项目面试题_练习清单.html`（52KB，14 题 × 6 段 = 84 个 q-step 小节）。

### Rulings
- 六段式答案按题库题目文本精确匹配合并，0 未匹配；旧八股短答案保留。
- 导出粒度：导读导出=全量 13 章；面试导出=当前子题库（跟随页面所选）。

---

## V4.2 登录页优化（2026-10-11，已完成）

### 用户需求（截图确认）
1. **未登录时不展示任何项目内容**（侧栏导航/顶栏/面包屑/页脚全部隐藏），页面只显示居中的学员登录卡，登录后才能进入系统——防止外人查看项目内容。
2. **账号简化成一个**：只保留一个固定账号密码（不默认展示，手动输入）。

### 改动
- `accounts.json`（项目根，新建）：只保留 `chaoyang / demo-chaoyang`（region_manager，朝阳），加载后需重启服务生效；`auth.py` 在文件缺失时仍回退内置演示账号（开发兼容）。
- `web/index.html`：`<body class="logged-out">`。
- `web/style.css`：`body.logged-out` 隐藏 `.app-sidebar/.app-header/.footer` 及除 `#login-card` 外的所有 section；`.app-shell` 去 margin、`main` 居中；登录卡 margin 归零。
- `web/app.js`：`loggedIn()` 先 `document.body.classList.remove('logged-out')` 再展示系统；登出走 `location.reload()` 恢复登录态。
- 测试：`test_api.py` 多账号断言改为单账号语义（登出后未认证 401）；`test_agent.py` 注入 haidian/viewer 到 `auth.ACCOUNTS`（仅测试进程，权限/隔离用例保持多角色覆盖）。全量 74 passed。
- script src 版本 `?v=20261011n`。

### 浏览器冒烟（Edge bu）
- 未登录：sidebar/header/footer 全部 display:none，页面仅 STUDENT ACCESS 登录卡；无任何视图可见。
- 错误密码 → 「账号或密码错误。」留在登录页。
- 正确密码 chaoyang/demo-chaoyang → 登录成功：进入「实习项目」视图，侧栏恢复，显示「chaoyang · 学员」。

---

## V4.3 导出还原完整手册（2026-10-11，已完成）

### 用户需求（截图确认）
P1 = 当前导出（项目导读页「导出 HTML」产物，简化 hero+13 章版式）不符合预期；P2 = 旧手册《贝壳找房_房产经纪经营AI Agent_实习复盘手册.html》完整格式与内容。要求导出效果对齐 P2——完整手册（22 章、目录侧栏、搜索/编辑/保存/导出 PDF/随机抽题工具栏、正文可编辑），让学员下载后自定义项目。

### 改动
- `web/handbook.html`（新增，128KB）：旧手册完整副本（22 `<section>`、style+script 自包含、零外链，可直接离线编辑）。
- `web/export.js`：`Export.guide()` 改为 fetch `/static/handbook.html` 原样下载，文件名 `贝壳找房_房产经纪经营AI Agent_实习复盘手册.html`；原 hero+13 章简化导出逻辑移除。
- 教学站「项目导读」页面展示不变（仍用 guide-data.json）。
- 新增 `tests/test_handbook_export.py`：断言 22 章齐全、contenteditable 与交互脚本、样式自包含、零外链。全量 **75 passed**。
- script src 版本 `?v=20261011o`。

### 浏览器冒烟（Edge bu）
- 登录 → 项目导读 → 点「导出 HTML」→ 下载 `贝壳找房_房产经纪经营AI Agent_实习复盘手册.html`（128KB，与 web/handbook.html md5 完全一致）。
- 本地打开下载文件：顶部工具栏 7 按钮齐全（锁定编辑/保存草稿/导出新HTML/导出PDF/新增章节/恢复已发布版/随机抽题）、目录侧栏 22 项、22 section、hero 卡、搜索框，正文全部可编辑——与 P2 效果一致。

---

## V4.4 项目面试题导出全量化（2026-10-11，已完成）

### 用户需求（截图确认）
「项目面试题」的「导出面试题 HTML」一次导出全部 54 题（5 个工作项），而非只导出当前选中的工作项（14 题）。

### 改动
- `web/export.js`：
  - 抽取 `renderQ(q, i)` 单题渲染（要点说明 + 六段式分段参考问答，可编辑）。
  - `interviewBody` 复用 `renderQ`；新增 `groupsBody(groups, topicTitle)`——按工作项分组输出，组标题 `<h3>` + 题数徽标 + 全局题号，总量标签「共 N 题（5 个工作项）」。
  - `Export.interview()` 改为 fetch `interview-topics.json` 取全量：`topic.groups`（项目面试题）→ `groupsBody` 全部 54 题；`topic.questions`（Agent/RAG/LLM 八股）→ 该子题库全部题目。
- script src 版本 `?v=20261011p`。

### 验证
- pytest 全量 75 passed（无回归）。
- 浏览器冒烟：面试题库页点「导出面试题 HTML」→ 下载 `项目面试题_练习清单.html`（163KB）：54 题、5 个分组标题（工作一~工作五）、324 个六段式小节（54×6）、总量标签「共 54 题（5 个工作项）」。
