# 教学网站 V2 改版设计文档（Teaching Website V2 Design）

- 日期：2026-10-11
- 状态：已实施（builder check 后提交用户批准）
- 项目：`/Users/cocochimp/Downloads/estate_agent_langgraph_demo`（FastAPI + LangGraph 房产经营分析 Agent）
- 前置：V1 教学网站（2026-10-11 已实施，四象限蓝白风格）→ 本文档为 V2 改版设计

---

## 1. 背景与意图（Intent & Why）

V1 采用四象限布局（左上工作项列表 / 右上节点图 / 左下内容介绍 / 右下 IO 与代码），7 个工作项（工作一~六 + 补充工程化评测）。复盘发现三个核心问题：

1. **7 个工作项与「实习经历模版」对不上**：简历模版只有 5 条工作内容（Agent Runtime/工作流、企业 RAG、Text-to-SQL、可信生成、Evals & Observability），教学却按手册章节分成 7 项，学员学完无法直接映射到简历话术。
2. **信息密度与主次不清**：四象限把"内容介绍"（教学核心）和"节点 IO"（辅助）平铺，学员容易迷失；分析执行图（整图）在 V1 被移除。
3. **样式不如旧手册丰富**：旧手册（实习复盘手册.html）采用墨绿青主题 + story/callout/badge 等组件化排版，比 V1 蓝白风格更适合教学阅读。

**意图**：以「实习经历模版」的 5 条工作内容为教学主线，重构为"四模块纵向布局"，让学员：先看工作项全貌 → 看一次请求怎么跑（分析执行图）→ 看当前工作项涉及哪些节点 → 沉浸式学习该工作项内容介绍；节点细节（IO/代码）以浮窗按需弹出。整体采用旧手册的丰富排版风格，全站统一。

## 2. 目标（Goals）

1. 「实现教程」Tab 改名「**实习项目教程**」，四模块纵向布局：
   - 模块 1 工作项（顶部横向标签，**5 个**，与简历一一对应）
   - 模块 2 分析执行图（恢复整图，压缩高度，只展示"一次请求怎么跑"）
   - 模块 3 全链路节点图（当前工作项涉及节点，压缩高度，**点击弹浮窗**展示 IO + 实例代码）
   - 模块 4 内容介绍（**核心模块**，占主要空间，5 个工作项的七段式内容）
2. 5 个工作项与「实习经历模版」严格一一对应；原手册工作一（意图理解）与工作五（Context/Memory）**并入「Agent Runtime / 工作流」作子主题**（内容不丢）。
3. 模块 4 内容采用旧手册七段式结构（业务现场 → 遇到问题 → 怎么定位 → 我做了什么 → 为什么这样选 → 结果怎么讲 → 被追问时），**完整性尽可能保证**（教学用，含面试追问）。
4. 全站统一旧手册主题：墨绿青主色 + 组件化卡片（story/callout/badge/case），高频面试题 Tab 同步换肤。
5. 高频面试题 Tab 分类与 5 个工作项对齐（agent / rag / sql / hallucination / evals / general）。
6. 导出功能保留并适配新布局：工作项学习页（四模块内容合并为单页可编辑 HTML）+ 面试题清单导出。

## 3. 非目标（Non-Goals）

- 不做多角色/权限体系（学员登录仍为服务端账号校验，accounts.json 不变）。
- 不恢复运行分析/SSE/工单/说明书/API 文档等入口（前端不暴露，后台 API 保留实现）。
- 不引入新后端依赖；分析执行图直接复用现有 `/api/graph`（svg_graph 输出）。
- 不改动后端数据查询/Agent 核心逻辑（tests/ 全绿基线保持不变）。

## 4. 约束（Constraints）

- 前端仍为静态文件（web/），由现有 FastAPI 服务托管；静态资源引用带版本参数防缓存。
- 教学内容全部数据驱动：`web/work-items.json`（V2）、`web/interview-questions.json`（V2）。
- 旧手册文案为唯一内容来源（`/Users/Doc/review/贝壳找房_AI经营分析Agent_实习复盘手册.html`），七段式内容从 work1~work6 / memory / quality / engineering / eval / trace 章节提取并对齐。
- 5 个工作项标题/量化指标必须与「实习经历模版」原文一致（含 baseline → 优化后数值）。
- 页面无控制台报错；导航仅保留「实习项目教程 / 高频面试题」两个 Tab。

## 5. 数据设计（Data Design）

### 5.1 `web/work-items.json`（V2）—— 5 个工作项

结构（每项）：

```jsonc
{
  "id": "work-1",
  "title": "工作一 · Agent Runtime / 工作流",
  "short": "Agent Runtime / 工作流",
  "summary": "一句话摘要",
  "resume": {              // 简历模版原条目（教学锚点）
    "label": "Agent Runtime / 工作流：",
    "text": "简历原文描述",
    "metrics": "量化指标原文（86.8%→94.1% 等）"
  },
  "subTopics": [           // 并入的子主题（仅 work-1 有）
    { "title": "子主题：意图理解与结构化输出", "node": "understand" },
    { "title": "子主题：Context 与 Memory", "node": "finish" }
  ],
  "nodes": ["understand", "clarify", "agent_node", "checkpoint_gate", "retry_node", "execute_action", "finish"],
  "intro": {               // 七段式（对齐简历条目）
    "scene": "业务现场…",
    "problem": "遇到问题…",
    "locate": "怎么定位…",
    "action": "我做了什么…",
    "why": "为什么这样选…",
    "result": "结果怎么讲…",
    "qa": ["面试追问 1", "面试追问 2"]
  },
  "io": [ { "node": "understand", "input": {}, "output": {}, "note": "" } ],
  "codeRefs": [ { "path": "estate_agent/runtime.py", "start": 1, "end": 40, "note": "" } ]
}
```

5 个工作项与简历/手册章节映射：

| id | 标题（简历锚点） | 手册内容来源 | 节点 |
|---|---|---|---|
| work-1 | 工作一 · Agent Runtime / 工作流 | work4（主体）+ work1（子主题：意图理解）+ memory（子主题：Context/Memory） | understand / clarify / agent_node / checkpoint_gate / retry_node / execute_action / finish |
| work-2 | 工作二 · 企业知识库 RAG | work2 | rag_search |
| work-3 | 工作三 · Tool Calling 与智能查数 | work3 | schema_retrieval / query_sql / calculate / analyze |
| work-4 | 工作四 · 可信生成与幻觉治理 | work6（quality） | generate_report / validate / human_approval |
| work-5 | 工作五 · Evals & Observability | engineering + eval + trace | （无图节点，仅内容） |

说明：
- work-1 的 resume 指标：Tool Selection Accuracy 86.8%→94.1%、Task Success Rate 73.5%→89.2%、重复 Tool Call 7.6%→2.1%。
- work-2：Recall@20 79.0%→94.0%、MRR 0.61→0.78、nDCG@10 0.69→0.84（420 条标注 Query）。
- work-3：Execution Accuracy 90.6%、高风险 SQL 拦截率 100%、无效 SQL 14.4%→5.0%（180 条 Gold Case）。
- work-4：Faithfulness 87.3%→96.1%、无依据结论率 6.8%→1.9%（300 条回答评测）。
- work-5：500 条分层回归用例、P95 延迟 5.2s→3.8s、平均 Prompt Token 下降约 28%。

### 5.2 `web/interview-questions.json`（V2）—— 分类对齐

categories 由 7 类改为 6 类：

```
intent(并入 agent) → agent
rag → rag
sql → sql
agent → agent
memory(并入 agent) → agent
hallucination → hallucination
(新增) → evals
general → general
```

即：`agent / rag / sql / hallucination / evals / general`。题目字段不变（question/tips/answer/weight/status），**原有题目重新归类**：intent 类题目归入 agent、memory 类题目归入 agent、工程化/评测类题目归入 evals；缺失的 evals 类题目从手册 qa/engineering/eval 章节补 3~5 题。总题数不低于 25。

## 6. 界面设计（UI Design）

### 6.1 页面结构（实习项目教程）

```
┌──────────────────────────────────────────────┐
│ 顶栏：面包屑「工作空间 > 实习项目教程」 + 导出按钮 │
├──────────────────────────────────────────────┤
│ 模块1 工作项： 横向标签 ×5（含简历锚点短名）      │
│   [工作一·Agent Runtime] [工作二·企业RAG] ...   │
│   （选中项下方显示简历条目摘要 + 量化指标徽章）    │
├────────────────────────┬─────────────────────┤
│ 模块2 分析执行图（整图） │ 模块3 全链路节点图      │
│  /api/graph SVG 压缩展示│  当前工作项节点卡片链    │
│  一次请求怎么跑          │  点击 → 浮窗(IO+代码)  │
├────────────────────────┴─────────────────────┤
│ 模块4 内容介绍（核心，高度优先）                  │
│  子主题 tab（仅 work-1）→ 七段式 story 卡片       │
│  [业务现场][遇到问题][怎么定位][我做了什么]         │
│  [为什么这样选][结果怎么讲][被追问时]             │
└──────────────────────────────────────────────┘
```

- 模块 2、3 各占约 220~260px 高度（压缩），模块 4 占据剩余高度并可滚动。
- 模块 2 与模块 3 关联：分析执行图展示全链路；模块 3 高亮当前工作项涉及的节点子集；两者共用同一节点命名（labels 映射）。
- 浮窗（`<dialog>`）：标题 = 节点名；内容 = 输入/输出（JSON）+ 实例代码（源码阅读器：行号/词法着色/复制/查看完整文件），复用 V1 teaching.js 的 colorLine/renderCode 能力；无内容节点显示占位说明。

### 6.2 高频面试题 Tab

- 同主题换肤（旧手册色板），布局不变（分类栏 + 随机抽题 + 提示/答案 + 导出）。
- 分类文案对齐：工作一 Agent Runtime（含意图理解/Context-Memory 子题）…工作五 Evals & Observability + 汇总。

### 6.3 样式规范（旧手册主题）

提取自旧手册 CSS（9.8KB），V2 全站采用：

- **主色**：`#245d65`（墨绿深青）、`#087f8c`（青）、`#17324d`（深蓝墨）、`#2d7c61`（绿）
- **点缀**：`#9c4a1e` / `#c7682e`（橙棕，用于强调/警示）
- **底色**：`#fbfcfc` / `#e7f1f2` / `#f4f7f8`（浅青灰纸感）
- **组件**：`.hero`（页头）、`.callout/.warn/.good`（提示条）、`.case/.case-title`（案例卡）、`.badge`（指标徽章）、`.story/.story-head/.story-script`（七段式叙事）、`.resume`（简历卡）
- 布局从"蓝白工具风"改为"青绿文档书感"；正文行高/字号沿用旧手册（约 14px/1.9）。

## 7. 交互设计（Interaction）

1. 点击工作项标签 → 模块 2 高亮对应节点子集（节点卡片边框着色）+ 模块 3 重渲染 + 模块 4 切换内容；URL hash 更新（`#work-1`）。
2. 点击模块 3 节点 → 弹浮窗（IO + 代码）；浮窗可关闭/ESC。
3. work-1 的模块 4 顶部有子主题 tab（意图理解 / Context-Memory / 主链路），切换只变内容区。
4. 导出按钮：导出当前工作项完整学习页（模块 1~4 内容合并为单文件可编辑 HTML，contenteditable，含简历条目、七段式、节点 IO/代码）；面试题 Tab 导出当前筛选题目。
5. 登录/登出、会话恢复逻辑不变（服务端校验，`/api/session` 自动登录）。

## 8. 后端改动（Backend）

- **无后端逻辑改动**。`/api/graph` 已存在（`estate_agent/diagram.py svg_graph`），直接复用；`accounts.json`、`auth.py` 不变。
- 若 `/api/graph` 的 SVG 需要工作项高亮参数（如 `?highlight=work-1`），由前端对 SVG 节点做 DOM 标记（无需后端改动）。

## 9. 文件清单（Files）

**修改**：
- `web/index.html` — 改名「实习项目教程」、四模块结构、旧手册主题 link
- `web/app.js` — 视图切换、标签映射（labels 不变）、hash 联动
- `web/teaching.js` — 四模块渲染与联动、浮窗（IO+代码）、源码阅读器保留
- `web/style.css` — 全站换肤为旧手册主题 + 四模块布局样式
- `web/work-items.json` — V2：5 个工作项（含 subTopics/七段式/简历锚点）
- `web/interview-questions.json` — V2：6 分类重新归类 + evals 补题
- `web/export.js` — 适配新布局（工作项单页合并导出）

**不变**：`web/interview.js`（布局不变，仅分类数据驱动）、`estate_agent/*`、`tests/*`、`accounts.json`。

**新增**：`tests/test_work_items_v2.py`（5 工作项结构/简历指标/七段式完整性/节点合法性）、`tests/test_interview_questions_v2.py`（6 分类/题量/归类一致性）。

## 10. 验收标准（Acceptance Criteria）

1. 「实现教程」更名为「实习项目教程」，导航仅两 Tab，页面无控制台报错。
2. 工作项标签共 **5 个**，与「实习经历模版」5 条工作内容标题一一对应；每条含简历原文摘要与量化指标徽章。
3. work-1 含 2 个子主题（意图理解、Context/Memory），内容来自手册 work1/memory 章节，完整性不丢。
4. 模块 2 分析执行图：嵌入 `/api/graph` SVG 全图，可缩放/横向滚动，高度压缩；与模块 3 节点命名一致。
5. 模块 3 全链路节点图：显示当前工作项节点卡片链，点击任意节点弹出浮窗，浮窗含「输入/输出」JSON 与「实例代码」（行号/着色/复制）；无内容节点显示占位。
6. 模块 4 内容介绍：七段式结构（业务现场/遇到问题/怎么定位/我做了什么/为什么这样选/结果怎么讲/被追问时）完整呈现，量化指标与简历条目一致；work-1 可切换子主题。
7. 全站统一旧手册主题（墨绿青主色 + story/callout/badge 组件），高频面试题 Tab 同主题。
8. 高频面试题分类 = agent/rag/sql/hallucination/evals/general，总数 ≥ 25，原有 intent/memory 题目正确并入 agent。
9. 导出：工作项学习页（含简历条目/七段式/节点 IO 与代码，contenteditable）+ 面试题清单，均可下载打开编辑。
10. 后端全量 pytest 全绿（含新增 V2 数据测试）；浏览器冒烟覆盖：登录 → 默认实习项目教程 → 切换工作项联动 → 点节点弹浮窗 → 面试题抽题 → 两处导出。

## 11. 实施范围提示（Implementation Notes）

- V2 数据重写是内容密集型任务：`work-items.json` V2 需逐项从手册对应章节提取七段式原文（含面试追问），量化指标与简历模版核对一致；`interview-questions.json` V2 需逐题重归类。
- 样式迁移量大：以旧手册 CSS 为基准重写 `style.css` 全局变量与组件，再套四模块布局。
- teaching.js 的源码阅读器（colorLine/renderCode）从 V1 直接复用，浮窗基于 `<dialog>` 实现。
- 静态资源版本参数统一更新（`?v=20261011b`）。


---

## §14 交付说明（2026-10-11，Native 实施完成）

- **数据**：`web/work-items.json`（V2：5 工作项与简历实习经历模版一一对应，work-1 含 2 子主题，七段式正文来自旧手册，io/codeRefs 与真实代码位置绑定）；`web/interview-questions.json`（V2：6 分类 31 题全 active）。
- **前端**：`web/index.html`（四模块纵向布局 + 节点浮窗 dialog + 登录卡）；`web/style.css`（旧手册墨绿青主题全站换肤，含四模块/浮窗/响应式样式）；`web/teaching.js`（四模块渲染：工作项标签/分析执行图/全链路节点图/七段式内容，节点浮窗展示 Trace 输入输出与实例代码）；`web/interview.js`（6 分类 catNames）；`web/export.js`（V2 布局导出：简历卡+七段式+节点 IO+实例代码，墨绿主题内联样式，正文可编辑）。
- **回归**：全量 pytest 70 passed；浏览器冒烟通过（四模块渲染、5 工作项切换、节点浮窗 IO+代码、工作5 无图降级、子主题切换、面试题 6 分类抽题、工作项导出 HTML 结构校验）。
- **已知取舍**：work-4 追问仅 1 条（手册 quality 章节原文如此）；执行图不按工作项高亮（SVG 由后端一次性生成）；V1 的 `learning.js`/`workspace.js` 不再被引用（保留未删）。
