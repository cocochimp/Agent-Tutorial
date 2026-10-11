# V3 优化设计：教学网站「项目导读 + 教程页四优化」2026-10-11

> 状态：已实施（Native 内联执行，V2 基础上升级）

## 背景与诉求

V2 交付后用户基于 5 张设计稿截图提出 4 项优化：
1. **布局**：教程页模块2（分析执行图）与模块3（全链路节点图）由纵向堆叠改为**左右并排**；分析执行图**按当前工作项标亮节点**（图1）。
2. **头部**：教程页头部（INTERNSHIP PROJECT TUTORIAL 白底）替换为**深色 hero 卡片**（图3）：eyebrow「AI APPLICATION ENGINEERING · AGENT + RAG + TOOLS」、主标题「房产经纪经营AI智能分析与决策平台」、描述、右侧业务/岗位/技术栈三列（图2→图3）。
3. **内容介绍完整化**：模块4 不能只有七段式摘要（图4），要**完整照搬旧手册对应章节**的全部内容（story + case + mini + grid + pre + callout 等，图5），并按实际内容调整——新工作一 = 手册 work4（Agent 规划与 LangGraph）+ 子主题（意图理解=手册 work1、Context/Memory=手册 memory）。
4. **新增「项目导读」tab**（置于「实习项目教程」之上）：旧手册除工作一~六 + 工程化/评测/Trace 之外的 13 个章节**原样照搬**（实习经历模板/项目定位/30 秒开场/业务场景/场景化面试法/整体架构/核心介绍 LLM·RAG·Agent/高级加分项/岗位版本/简历写法/高频追问/易错点/术语速查）。

## 关键设计决策

| 决策点 | 结论 |
|---|---|
| 数据形态 | 章节 HTML 原文内联进 JSON：`web/guide-data.json`（13 章 `{id,title,html}`）；`web/work-items.json` 每项加 `introHtml`（对应手册章节完整 HTML，去 h2/script/空白），子主题加 `html`（work1/memory 章节） |
| 章节提取 | Python 正则 `<section id="X">…</section>` → 去 `<h2>` 标题、去唯一 `<script>`（页面编辑功能，与内容无关）、压缩空白 |
| 工作项映射 | work-1=work4(+work1、memory 子主题)；work-2=work2；work-3=work3；work-4=quality；work-5=engineering+eval+trace |
| 渲染安全 | 手册为自产静态内容、提取时已剥 script；前端 `innerHTML` 渲染（`guide-html` 容器）；导出同构 |
| 执行图高亮 | SVG 节点为 `<g data-node="…"><rect fill="#f4f6ef" stroke="#95b1a5"/>`；前端按 `item.nodes` 集合匹配 `data-node`，命中节点 rect 换 `#e7f7f7/#087f8c` + 描边加粗 + 文字加深，非命中复位 |
| 导出 | 工作项导出内容介绍改为完整章节 HTML（`guide-html` 内联样式 + 子主题分区），仍可编辑 |
| 版本缓存 | 全站静态引用 `?v=20261011c` |

## 文件变更

- 新增 `web/guide-data.json`（13 章，21KB）、`web/guide.js`（导读目录+内容渲染）
- 修改 `web/index.html`（三 nav tab + guide-view + hero 头部 + exec-row 并排）、`web/teaching.js`（renderStory 完整 HTML + highlightGraph）、`web/export.js`（完整章节导出）、`web/app.js`（三视图）、`web/work-items.json`（introHtml/subTopics.html）、`web/style.css`（hero/exec-row/legend-active/guide 布局/手册组件样式）

## 非目标

- 不改后端图结构；执行图仍为后端单次生成的全局图，前端仅做视觉高亮
- 不新增登录方式；仍用既有 demo 账号
- 不移动/删除 V1 遗留文件（learning.js/workspace.js 保留）

## 验证结果

- 全量 pytest **70 passed**
- 浏览器冒烟（JS 级 DOM 断言，窄视口）：三视图切换；hero 头部三 facts；5 工作项 tabs；工作1 高亮 7 节点、工作2 高亮 1 节点（rag_search）+1 case+3 grid-3、工作5 高亮 0+降级；内容介绍完整章节（story/mini/pre/qa）；子主题 3 tabs（总览+意图理解+Context/Memory 各 7 段式）；导读 13 章节切换（整体架构 pre 渲染）；节点浮窗 IO×2；工作项导出 47KB 含完整章节+子主题+IO+代码（10 项结构校验全绿）
