# 多项目支持实施计划

> **For agentic workers:** REQUIRED SUB-SKILL: superpowers:executing-plans（Native 内联执行）

**Goal:** 教学站支持多项目：新增项目切换器 + 拍照搜题 Agent 完整项目（导读/实习项目/面试/导出/执行图），房产项目内容零改动。

**Architecture:** 数据按 `web/projects/<pid>/` 目录隔离，`projects/index.json` 注册表驱动切换器；前端 `app.js` 持 `currentProject` 状态（localStorage 记忆），各视图按当前项目 fetch 相对路径 `projects/<pid>/xxx.json`；八股题（Agent/RAG/LLM）抽到 `static/interview-common.json` 全局共享；Pages 构建脚本同步 projects/ 目录。

**Tech Stack:** FastAPI + 原生前端（无框架）、GitHub Pages 静态部署（相对路径兼容）

**Spec:** `docs/superpowers/specs/2026-10-12-multi-project-design.md`（已确认：侧栏顶部下拉、每工作项 10 题、八股共享、手工构造 SVG）

## Global Constraints

- 相对路径 `static/...` / `projects/...`，本地 FastAPI 与 Pages 子路径均兼容；不改回绝对路径。
- 登录单账号（chaoyang/demo-chaoyang），切换项目不改变登录态。
- 房产项目（estate-agent）内容零改动，仅迁移文件目录。
- 每次改静态文件递增 `?v=` 版本参数（当前 v=20261011s）。
- 每任务 TDD：先写失败测试 → 实现 → 全量 pytest 绿 → 浏览器冒烟。
- 拍照搜题手册源：`/Users/Doc/review/拍照搜题-agent-实习复盘手册-v2.html`（14 章）。

## Review Focus

- 切换项目后视图缓存（svgCache / 已渲染 DOM）必须清空重建，否则显示上一项目内容。
- 未登录/静态模式下切换器可用性；localStorage 无值时默认 estate-agent。
- projects/index.json 缺失或某项目数据文件缺失时的优雅降级（不白屏）。
- 八股共享后，各项目 interview-topics.json 只含 project/recording，前端合并 common 展示。
- 导出文件名含项目名；导出数据必须来自当前项目。

---

### Task 1: 数据目录重构（estate-agent 迁移 + 注册表 + 八股抽取）

**Files:**
- Create: `web/projects/index.json`
- Create: `web/static/interview-common.json`（Agent/RAG/LLM 三主题从 interview-topics.json 抽出）
- Move: 现有 web 根下 `work-items.json`、`guide-data.json`、`tutorial-data.json`、`graph.json`、`handbook.html` → `web/projects/estate-agent/`
- Rewrite: `web/projects/estate-agent/interview-topics.json`（只含 project + recording，八股删去）
- Modify: `tests/`（路径更新 + 注册表断言 + 八股共享断言）

- [ ] Step 1: 写失败测试：projects/index.json 存在且含 estate-agent；estate-agent 目录五件套齐全；interview-common.json 含 agent/rag/llm 三主题；estate 的 interview-topics.json 不再含 agent/rag/llm。
- [ ] Step 2: 跑测试确认 FAIL。
- [ ] Step 3: 创建目录、迁移文件、生成注册表与 common 文件、重写 estate interview-topics.json。
- [ ] Step 4: 跑测试确认 PASS；全量 pytest 绿。
- [ ] Step 5: Commit。

### Task 2: 前端项目状态 + 侧栏下拉切换器

**Files:**
- Modify: `web/index.html`（侧栏品牌区加项目切换器 DOM）
- Modify: `web/style.css`（切换器样式）
- Modify: `web/app.js`（currentProject 状态、loadProjects、切换逻辑、localStorage、品牌联动）

- [ ] Step 1: 写失败测试（node 侧无法直接测 DOM；用静态断言：index.html 含切换器容器、app.js 含 currentProject/loadProjects 逻辑）→ 或浏览器冒烟先行。改用 Python 静态断言测试。
- [ ] Step 2: 跑测试确认 FAIL。
- [ ] Step 3: 实现切换器 DOM + 样式 + app.js 状态逻辑。
- [ ] Step 4: 测试 PASS；全量 pytest 绿；本地浏览器冒烟（切换器可见、可展开、选中后状态持久化）。
- [ ] Step 5: Commit。

### Task 3: 视图加载适配当前项目

**Files:**
- Modify: `web/teaching.js`（fetch `projects/<pid>/work-items.json`、`tutorial-data.json`、`graph.json`；暴露 reload 接口）
- Modify: `web/guide.js`（fetch `projects/<pid>/guide-data.json`）
- Modify: `web/interview.js`（fetch `projects/<pid>/interview-topics.json` + `static/interview-common.json` 合并）
- Modify: `web/app.js`（切换时调用各视图 reload）

- [ ] Step 1: 写失败测试（静态断言：各 JS 含 projects/ 路径拼接逻辑、common 合并逻辑）。
- [ ] Step 2: 跑测试确认 FAIL。
- [ ] Step 3: 实现三视图按项目加载 + reload 接口。
- [ ] Step 4: 测试 PASS；全量 pytest 绿；本地冒烟（切换项目后三视图内容变化）。
- [ ] Step 5: Commit。

### Task 4: 导出适配当前项目

**Files:**
- Modify: `web/export.js`（Export.guide 取 `projects/<pid>/handbook.html`；Export.interview 取当前项目 project 题 + common 八股；文件名带项目名）

- [ ] Step 1: 写失败测试（静态断言 export.js 含 projects/<pid> 路径与项目名前缀）。
- [ ] Step 2: 跑测试确认 FAIL。
- [ ] Step 3: 实现。
- [ ] Step 4: 测试 PASS；全量 pytest 绿；冒烟（两项目导出文件名/内容正确）。
- [ ] Step 5: Commit。

### Task 5: 拍照搜题 work-items.json（5 工作项教学数据）

**Files:**
- Create: `web/projects/photo-q/work-items.json`
- Modify: `tests/test_photo_q_data.py`

- [ ] Step 1: 写失败测试（photo-q work-items 5 项、每项含 nodes/io/metrics/subTopics/introHtml、指标可解析）。
- [ ] Step 2: 跑测试确认 FAIL。
- [ ] Step 3: 从手册提取 5 工作项数据（work1~work4 + memory）：intro（真实需求场景）、nodes（执行节点链+每节点 io 输入输出示例+codeRefs 示例代码）、metrics（设计思路+数据来源）、subTopics。
- [ ] Step 4: 测试 PASS；全量 pytest 绿。
- [ ] Step 5: Commit。

### Task 6: 拍照搜题导读 + 手册副本

**Files:**
- Create: `web/projects/photo-q/guide-data.json`（hero + 章节，手册除 5 工作项外内容）
- Create: `web/projects/photo-q/handbook.html`（手册 v2 原样副本）
- Create: `web/projects/photo-q/tutorial-data.json`
- Modify: `tests/test_photo_q_data.py`

- [ ] Step 1: 写失败测试（guide chapters ≥10、handbook 自包含 14 章、tutorial 可解析）。
- [ ] Step 2: 跑测试确认 FAIL。
- [ ] Step 3: 从手册提取导读章节 + 复制手册 + 教程数据。
- [ ] Step 4: 测试 PASS；全量 pytest 绿。
- [ ] Step 5: Commit。

### Task 7: 拍照搜题项目面试题 50 题（5 组 ×10，六段式）

**Files:**
- Create: `web/projects/photo-q/interview-topics.json`（project 5 组 50 题 + recording 占位）
- Modify: `tests/test_photo_q_data.py`

- [ ] Step 1: 写失败测试（project 5 组、每组 ≥10 题、每题六段式 ≥6 段 ≥400 字、含量化数字）。
- [ ] Step 2: 跑测试确认 FAIL。
- [ ] Step 3: 基于手册 qa 14 题 + 各工作项内容撰写 50 题六段式答案（脚本生成 JSON）。
- [ ] Step 4: 测试 PASS；全量 pytest 绿。
- [ ] Step 5: Commit。

### Task 8: 拍照搜题执行图 SVG

**Files:**
- Create: `web/projects/photo-q/graph.json`（mermaid + svg，18 节点左右）
- Modify: `tests/test_photo_q_data.py`

- [ ] Step 1: 写失败测试（svg 有效、≥15 data-node）。
- [ ] Step 2: 跑测试确认 FAIL。
- [ ] Step 3: 按手册架构手工构造 SVG（节点：用户输入→解析→规划→OCR→公式识别→检索→重排→生成→校验→记忆→输出等）。
- [ ] Step 4: 测试 PASS；全量 pytest 绿。
- [ ] Step 5: Commit。

### Task 9: Pages 构建 + 集成回归 + 部署

**Files:**
- Modify: `scripts/build_pages_site.py`（复制 projects/ 目录进 site_pages/static/projects/）
- Modify: `tests/`（Pages 构建产物断言）
- Modify: `docs/superpowers/specs/2026-10-12-multi-project-design.md`（追加实施记录）

- [ ] Step 1: 写失败测试（构建后 site_pages/static/projects/ 含两项目五件套）。
- [ ] Step 2: 跑测试确认 FAIL。
- [ ] Step 3: 修改构建脚本。
- [ ] Step 4: 测试 PASS；全量 pytest 绿；本地静态服务器模拟两项目切换冒烟；版本递增。
- [ ] Step 5: Commit + push（自动部署）；线上冒烟验证两项目切换。
