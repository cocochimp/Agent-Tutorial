# 教学站多项目支持设计方案

> 日期：2026-10-12 ｜ 状态：待确认 ｜ 涉及仓库：Agent-Tutorial（`estate_agent_langgraph_demo`）

## 一、目标

教学站从「单项目（房产经纪经营 AI）」升级为「多项目教学平台」：

1. 增加**项目切换器**：学员可点击切换当前教学项目（房产经纪经营 AI ↔ 拍照搜题 Agent）。
2. 新增**拍照搜题 Agent** 项目，内容组织逻辑与房产项目完全一致（项目导读 / 实习项目四象限 / 面试题库 / 完整手册导出）。
3. 切换项目后，站点整体（导读、学习视图、面试题库、导出）跟随当前项目联动。

## 二、交互设计：项目切换器

- 位置：左侧导航栏顶部品牌区（当前「经营分析 Agent 教学」标题下方）。
- 形态：下拉选择器「当前项目：房产经纪经营AI」▼；点击展开两个项目卡片（项目名 + 一句话简介），选中即切换。
- 记忆：`localStorage` 记住上次选择的项目，下次打开默认进入上次项目；未选择过时默认「房产经纪经营AI」。
- 切换行为：切换后重新加载当前项目的全部视图（导读 / 实习项目 / 面试题库），并更新侧栏标题、页面品牌、面包屑。

## 三、数据结构改造（核心）

### 3.1 数据按项目目录组织

新建 `web/projects/<project-id>/`，每个项目一份完整数据包，项目间完全隔离：

```
web/projects/
├── estate-agent/            # 房产经纪经营 AI（现有内容迁入）
│   ├── work-items.json      # 5 工作项教学数据（nodes/io/metrics/subTopics/introHtml）
│   ├── guide-data.json      # 项目导读 13 章
│   ├── interview-topics.json# 项目面试题 54 题（project）+ 八股共享引用
│   ├── tutorial-data.json   # 教程数据（实现教程 lessons/files）
│   ├── graph.json           # 分析执行图 SVG
│   └── handbook.html        # 完整实习复盘手册副本
└── photo-q/                 # 拍照搜题 Agent（新建）
    ├── work-items.json      # 5 工作项教学数据（从手册抽取）
    ├── guide-data.json      # 项目导读章节（手册除工作项外的内容）
    ├── interview-topics.json# 项目面试题 5 组（手册 qa + 各工作项扩展）
    ├── tutorial-data.json   # 教程数据
    ├── graph.json           # 拍照搜题执行图 SVG
    └── handbook.html        # 拍照搜题手册副本
```

- 顶层 `web/projects/index.json`：项目注册表（`[{id, name, tagline, color}]`），供切换器渲染。
- **八股题（Agent / RAG / LLM）是通用知识，项目无关**：从 interview-topics.json 中抽出，放 `web/static/interview-common.json`，所有项目共享；各项目的 interview-topics.json 只含 project（项目面试题）+ recording（高频面试题占位）。
- 现有根目录数据文件（work-items.json / guide-data.json / interview-topics.json / tutorial-data.json / graph.json / handbook.html）迁入 `projects/estate-agent/` 后删除根目录副本，避免双源。

### 3.2 前端状态与加载

- `app.js` 增加全局 `currentProject` 状态（id 来自 `projects/index.json` + localStorage）。
- 所有视图加载改为 `fetch('projects/' + pid + '/xxx.json')` 相对路径（本地 FastAPI 与 Pages 子路径均兼容，沿用现有相对路径机制）。
- 切换项目：更新状态 → 清空各视图缓存（svgCache 等）→ 重新 init 各视图 → 持久化 localStorage。
- 页面品牌/侧栏标题随项目名称变化。

### 3.3 导出适配

- `Export.guide()`：下载当前项目的 `projects/<pid>/handbook.html`（完整手册，可编辑自定义）。
- `Export.interview()`：项目面试题取当前项目 interview-topics.json 的 project 全量（54 题/5 组）；八股题取共享 interview-common.json。
- 导出文件名带项目名前缀（如 `拍照搜题Agent_项目面试题_练习清单.html`）。

## 四、拍照搜题 Agent 内容计划

数据源：`/Users/Doc/review/拍照搜题-agent-实习复盘手册-v2.html`（14 章，含 5 个工作项、检索漏斗、评测、面试追问、速查）。

### 4.1 五个工作项（对齐房产项目 work-items 结构）

| 工作项 | 手册章节 | 教学数据（nodes/io/codeRefs/metrics/introHtml） |
|---|---|---|
| 工作一 · Agent 工具编排与流程规划 | work1 | 工具封装（OCR/公式识别/题库检索/解题生成/相似题）、ReAct 多步规划、LangGraph 状态机；指标：工具调用准确率 92%、Schema 校验+错误重试 |
| 工作二 · 多模态解析与 Query 理解 | work2 | 拍照输入解析、OCR、公式识别、Query 理解与改写 |
| 工作三 · 混合检索与结果精排 | work3 | 多路召回（向量/BM25/RRF）、Cross-Encoder 精排、MMR；指标：检索漏斗 60→40→10→5→3、Top5 准确率 |
| 工作四 · 解题生成、幻觉治理与质量把关 | work4 | 解题生成、置信度阈值 0.85、Verifier/guardrail、自校验重试 |
| 工作五 · 上下文与记忆系统设计 | memory | 短期/长期记忆、知识点掌握度、token 控制 |

每工作项从手册提取：真实需求场景（intro）、执行节点链（nodes + 每节点 io/codeRefs，手册中「我做了什么/为什么这么做 + 参数指标」逐段映射）、量化指标（metrics，可点击浮窗解释设计思路与数据来源——延续现有交互）。

### 4.2 项目导读

- 手册中除 5 工作项 + deepdive 拆解外的内容：实习经历模板（resume）、项目总览与 30 秒开场（opening）、整体架构与检索漏斗（architecture）、RAG 核心概念（rag）、检索漏斗逐层拆解（deepdive）、评测体系（eval）、答题易错点（pitfalls）、指标与术语速查（cheatsheet）→ 按现有导读 13 章版式组织（hero + 章节卡）。
- 完整手册导出 = 拍照搜题手册 v2 原样副本（可编辑自定义，延续现有机制）。

### 4.3 面试题库

- **项目面试题**：按 5 工作项分组，每工作项 10 题以上（对齐房产 54 题的体量）。题目与六段式完整答案基于手册 qa 章节 14 题 + 各工作项章节内容扩展撰写（每题可讲 5-10 分钟、含量化数字）。
- **八股题**：共享现有 Agent 22 / RAG 22 / LLM 22（通用知识，不随项目变）。
- **高频面试题**：占位保持（后续用学员真实面试录音补充）。
- 子库顺序不变：项目面试题 → 高频面试题 → Agent → RAG → LLM。

### 4.4 分析执行图

- 拍照搜题的执行图 SVG：根据手册「整体架构与检索漏斗」章节（mermaid 描述 + 节点链 用户输入→模型规划→调用工具→观察→答案）手工构造一张与房产项目同风格的 LangGraph 全流程图（18 节点左右），前端高亮机制复用（当前工作项节点高亮）。

## 五、测试与部署

- 新增 pytest：projects/index.json 注册表完整、每个项目目录数据齐全（work-items 5 项、graph 有效、handbook 自包含）、estate-agent 与现有断言兼容（54 题/13 章/22 章手册）、photo-q 数据可解析。
- 全量回归：现有 76 passed 保持；浏览器冒烟覆盖：项目切换器切换 → 两项目各自导读/实习项目/面试/导出。
- Pages 部署：build_pages_site.py 需把 projects/ 目录一起复制进 site_pages/static/projects/（保持 /static 映射），自动部署流程不变。

## 六、明确取舍

- 八股题共享、项目面试题按项目隔离：符合教学逻辑，避免重复维护。
- 切换项目不改变登录态（单账号全局）。
- 房产项目内容零改动，仅迁移数据目录（内容不变）。
- 拍照搜题项目面试题第一版按「每工作项 10 题 + 手册 qa 全量」撰写约 50 题；如需与房产完全同量（54 题），可后续迭代补齐。

## 七、待确认点

1. **切换器形态**：侧栏顶部下拉（推荐）可否？还是希望做成顶栏标签/其他位置？
2. **拍照搜题面试题体量**：第一版 50 题（每工作项 10 题）是否满足？还是要求与房产一致 54 题以上？
3. **八股题共享**（Agent/RAG/LLM 不随项目变）是否接受？
4. **执行图**：手工构造的拍照搜题 SVG（基于手册架构、与房产同风格）可否？

确认后进入实施计划（按现有 V 系列迭代节奏执行：TDD + 冒烟 + 部署）。
