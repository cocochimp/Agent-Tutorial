# 房产经营分析 Agent

基于 FastAPI 和 LangGraph 的门店经营分析应用，支持指标查询、异常分析、制度检索、报告生成及人工审批。StateGraph 管理任务编排，SQLite 保存业务数据和检查点，Qdrant 与 ONNX 模型提供混合检索。系统支持规则模式和模型模式：规则模式无需 API Key，模型模式由 DeepSeek 等兼容服务选择工具。

内置数据与制度为虚构样例，账号用于本地演示。功能范围、源码位置和评测结果见能力对照说明书。

## 使用导航

- [快速启动](#start)：安装依赖、启动服务、登录。
- [完成一次分析](#first-run)：页面设置、运行结果和 Trace。
- [配置 DeepSeek](#deepseek)：填写密钥并切换决策模式。
- [项目阅读顺序](#reading)：先了解流程，再按模块阅读代码。
- [常用操作](#operations)：多轮追问、审批、任务恢复和报告导出。
- [常见问题](#troubleshooting)：启动失败、端口占用和检索目录锁定。

首次使用可按“快速启动 → 完成一次分析 → 项目阅读顺序”操作。查找某项功能的实现位置，可直接打开[能力对照说明书](docs/能力对照说明书.html)。

> **教学站（学员端）**：`web/` 为学员教学中心（项目导读 / 实习项目 / 面试题库，支持完整手册与面试题导出）。本地访问 `http://127.0.0.1:8765`，默认账号见 `accounts.json`（未配置时回退内置演示账号）。线上公开版部署在 GitHub Pages（`https://cocochimp.github.io/Agent-Tutorial/`）：GitHub Pages 无法运行后端，自动降级为前端校验登录，账号与本地一致；`scripts/build_pages_site.py` 构建 Pages 兼容目录，`.github/workflows/pages.yml` 在 push 到 main 时自动构建部署。

<a id="start"></a>

## 快速启动

### 环境准备

- Windows，Python 3.11 或以上。Python 3.11 和 3.13 已完成安装与运行验证。
- 首次安装 Python 依赖需要网络；规则模式无需模型 API Key，内置检索模型使用 CPU。
- 所有命令均在项目根目录执行，即包含 `app.py`、`launch.py` 和 `start_demo.cmd` 的目录。

### 启动与登录

1. 使用 Python 3.11 或以上版本，安装时勾选 Add Python to PATH。
2. 在项目根目录双击 `start_demo.cmd`。首次启动会联网安装 Python 依赖，检索模型位于 `models/`。
3. 看到 Uvicorn running 后打开 http://127.0.0.1:8765 。保持终端运行，停止时按 Ctrl+C。
4. 登录默认朝阳区域经理：账号 `chaoyang`，密码 `demo-chaoyang`。页面也列出了其他演示账号。
5. 选择“规则模式”，点击“运行分析”。不要直接双击 `web/index.html`，否则浏览器无法连接后端。

也可以打开 PowerShell 执行：

```powershell
Set-Location -LiteralPath 'E:\Codex\培训资料\estate_agent_langgraph_demo\estate_agent_langgraph_demo'
python -X utf8 launch.py
```

启动器会创建或复用项目内的 `.venv`，安装 `requirements.txt` 中的依赖，然后启动后端。无需手动激活虚拟环境。安装期间保持窗口打开；看到 `Uvicorn running on http://127.0.0.1:8765` 后再访问页面。

服务已运行时，直接打开页面即可。关闭浏览器不会停止后端；在启动终端按 `Ctrl+C` 可停止服务，下次继续使用相同启动方式。

### 演示账号

登录页选择角色后会自动显示对应密码。账号权限由服务端控制。

| 页面角色 | 账号 | 密码 | 访问范围 |
|---|---|---|---|
| 朝阳区域经理 | `chaoyang` | `demo-chaoyang` | 朝阳门店与适用制度 |
| 海淀区域经理 | `haidian` | `demo-haidian` | 海淀门店与适用制度 |
| 城市总监 | `director` | `demo-director` | 朝阳、海淀两区 |
| 朝阳只读观察员 | `viewer` | `demo-viewer` | 朝阳查询，无工单或发布权限 |

以上为本地演示账号，不适用于公网认证。

若端口被占用：`python -X utf8 launch.py --port 8766`，然后打开 http://127.0.0.1:8766 。

依赖按 Python 版本自动选择：Python 3.11 使用 NumPy 2.4.6，Python 3.12 及以上使用 NumPy 2.5.3。启动时会打印项目 `.venv` 实际使用的解释器与版本。安装失败后可重新运行 `start_demo.cmd`，启动器会继续安装缺失的依赖。

<a id="first-run"></a>

## 完成一次分析

登录后保留以下设置：

| 页面选项 | 初次运行建议 | 作用 |
|---|---|---|
| 决策模式 | 规则模式（无需 API Key） | 按规则选择下一步工具 |
| 检索链路 | 完整混合检索 | BM25、向量召回、融合与精排 |
| 编排方式 | 单Agent | 通过一个规划节点调度工具 |
| 会话 ID | `learning-01` | 将同一组多轮问题关联起来 |
| 增加知识图谱关系检索 | 不勾选 | 熟悉基本流程后再比较关系检索的影响 |

在“分析问题”中输入：

```text
分析朝阳最近7天带看转成交率下降的门店，给出原因和跟进建议
```

点击“运行分析”，完成后依次查看：

1. **分析报告**：门店指标、变化幅度、同期线索和制度引用。
2. **逐节点 Trace**：展开“参数与结果”，核对每一步输入与输出。
3. **执行图**：查看涉及哪些节点；具体执行先后以 Trace 为准。

该样例中，望京A店的带看转成交率由20.65%降至9.29%，变化约为-11.35个百分点。报告中的原因属于待核查线索，不代表因果结论。

### Trace 和 RAG 的查看位置

| Trace 名称 | 对应节点 | 重点字段 |
|---|---|---|
| 理解与鉴权 | `understand` | 地区、指标、本期及比较基线 |
| 规划下一步 | `agent_node` | `output.name` 和 `output.arguments`，表示选择的工具与参数 |
| SQL 查询 | `query_sql` | `output.data.sql`、`parameters`、`raw_rows` |
| 指标计算 | `calculate` | 计算结果摘要及排序首位门店 |
| 漏斗分析 | `analyze` | 分析对象和同期指标变化 |
| RAG 混合检索 | `rag_search` | `input.query`、`output.data.stages`、`output.data.evidence` |
| 生成报告、结果校验 | `generate_report`、`validate` | 引用证据、待核查假设及校验结果 |

执行图中“混合检索”对应 RAG 检索节点。`stages` 记录权限过滤、查询改写、BM25、Dense、RRF和精排过程；`evidence` 保存最终文档原文、来源ID和排序分数。检索结果随后进入报告生成环节。

“规划下一步”会在一次任务中重复出现，表示每次工具执行后重新决策。绿色标记 Trace 中已记录的节点，橙色标记最后一条记录；部分内部节点未单独写入 Trace，因此灰色不一定表示未执行。

<a id="deepseek"></a>

## 配置 DeepSeek

编辑根目录 `deepseek_config.json`，在 `api_key` 字段填写 API Key：

```json
{
  "base_url": "https://api.deepseek.com",
  "model": "deepseek-flash",
  "api_key": "填写 API Key"
}
```

保存后，在“决策模式”中选择 **DeepSeek / 兼容模型 + StateGraph**，再点击“运行分析”。下一次请求会重新读取配置，无需重启。配置是 JSON：使用英文双引号，不加注释。密钥配置仅保存在本地，不随源码分发。

模型名称以账号可用型号为准。客户端使用 Chat Completions 和 Function Calling，在 DeepSeek 请求中关闭 thinking。接口错误显示 HTTP 状态，密钥不写入响应或 Trace。

模型模式下，DeepSeek负责理解问题、选择工具和选择报告证据；SQL执行、指标计算和知识检索由本地工具完成。规则模式同样执行SQL和RAG，但工具选择由规则完成。

模型配置提示在登录时读取。填写密钥后，若提示仍未更新，可刷新页面。确认某次任务是否使用模型，应查看该任务的JSON Trace：`mode` 为 `llm`，`model_stats` 中记录模型名称、调用次数与Token用量。

<a id="reading"></a>

## 项目阅读顺序

### 工作台布局

- **分析报告**：默认工作区，展示指标卡片、门店前后期对比图、数据表和制度引用。对比图使用本次任务的实际结果。
- **执行过程 / Trace**：通过报告上方的页签切换，查看图状态或逐节点输入输出。
- **右侧分析助手**：输入问题、选择决策模式；展开“分析设置”可修改检索链路、编排方式和会话 ID。
- **左侧历史任务**：选择已保存的任务查看报告；会话记忆与偏好也在这里管理。
- **左侧工单收件箱**：查看审批通过的本地动作记录。

窄屏设备中，分析助手移到报告上方，主导航显示为底部导航。切换工作区不会取消分析任务。

### 在网页里阅读教程和源码

启动后，点击左侧导航的 **实现教程**。无需登录即可阅读；执行分析仍需登录演示账号。

- 左侧按主题选择 LangGraph、RAG、SQL、会话记忆、审批恢复等内容，也可搜索函数名或文件名。
- 每个主题包含处理流程、实现步骤、观察方法和对应源码。点击“对应实现”中的按钮切换函数。
- 源码默认显示关键片段及原始行号，支持语法高亮、复制代码和“查看完整文件”。完整文件中的浅绿色区域对应当前片段。
- 在分析工作台点击图中的节点，或点击 Trace 每条记录的“查看实现”，可直接进入对应教程。切换视图不会中断正在运行的任务。
- 侧栏“能力对照说明书”在页面内打开完整能力对照文档；按 Esc 或点击“关闭”返回。

建议先读“从一个问题到一份报告”，再读“LangGraph 怎样编排任务”。对知识检索感兴趣可直接选择“RAG：从制度中找到依据”。

教程源码是从项目文件生成的只读快照，包含核心流程的中文注释，不包含密钥与运行数据。修改代码或教程内容后，可更新网页快照及说明书行号：

```powershell
.venv\Scripts\python.exe -X utf8 scripts/build_tutorial.py
.venv\Scripts\python.exe -X utf8 scripts/build_manual.py
```

主题文案维护在 `docs/tutorials.json`，函数范围由 Python AST 定位。`scripts/build_release.py` 打包前也会自动刷新这两套文档。

### 先了解完整流程

先运行一条分析，保留页面上的 Trace，再打开[能力对照说明书](docs/能力对照说明书.html)。第1章说明请求处理流程，第6章说明LangGraph编排，第4章说明RAG。说明书中的链接可跳转到带行号的源码。

主流程按以下顺序阅读：

```text
app.py：create_task()
  → runtime.py：run() / build_graph()
  → understand_node：理解问题与鉴权
  → plan_node：选择工具
  → execute_tool：执行SQL、计算或检索
  → report_node / validate_node：生成并校验报告
  → finish：保存会话记忆
```

### 按模块阅读代码

| 顺序 | 文件与入口 | 阅读重点 |
|---|---|---|
| 1 | [state.py](estate_agent/state.py) 的 `AgentState` | 一次任务保存哪些字段，工具结果和执行状态怎样共享 |
| 2 | [runtime.py](estate_agent/runtime.py) 的 `build_graph()`、`run()` | 节点注册、条件边、循环、检查点与恢复 |
| 3 | [llm.py](estate_agent/llm.py) 的 `TOOLS`、`ModelClient.decide()` | 工具Schema如何发给模型，模型怎样返回工具调用 |
| 4 | [contracts.py](estate_agent/contracts.py)、[intent.py](estate_agent/intent.py) | 自然语言怎样变成经过校验的任务参数 |
| 5 | [sql_tools.py](estate_agent/sql_tools.py)、[business.py](estate_agent/business.py) | Schema检索、SQL安全检查、指标计算和漏斗分析 |
| 6 | [retrieval.py](estate_agent/retrieval.py) 的 `search_knowledge()` | 文档过滤、两路召回、融合、精排和证据回取 |
| 7 | [report.py](estate_agent/report.py) | 数字与引用如何进入报告，校验失败时如何处理 |
| 8 | [storage.py](estate_agent/storage.py)、[auth.py](estate_agent/auth.py) | 会话记忆、缓存、幂等操作与账号权限 |
| 9 | [app.py](app.py)、[web/app.js](web/app.js) | 网页如何提交任务、接收状态、审批和下载结果 |
| 10 | [tests/](tests/)、[evaluate.py](evaluate.py) | 如何验证计算、权限、恢复、检索和报告校验 |

查阅数据结构时，可同时打开 [data.py](estate_agent/data.py)、[knowledge.json](data/knowledge.json) 和 [relations.json](data/relations.json)，分别对应业务样例生成、制度文档和实体关系。

### 按问题定位实现

| 关注的问题 | 入口 |
|---|---|
| 下一步由谁决定？ | `runtime.py` 的 `plan_node()`；规则模式另看 `offline_action()` |
| LangGraph在哪里连线？ | `build_graph()` 内的 `add_node()`、`add_edge()`、`add_conditional_edges()` |
| RAG在哪里？ | `retrieval.py` 的 `search_knowledge()`；进入模型上下文的过程见 `runtime.py` 的 `context_messages()` |
| 如何避免查询未授权区域？ | `intent.py` 的 `normalize()` 和 `sql_tools.py` 的 `execute_readonly()` |
| 关闭进程后如何继续？ | `runtime.py` 的 `run()`，重点看 `SqliteSaver`、`thread_id` 和 `Command(resume=...)` |
| 工单为什么不会重复创建？ | `storage.py` 的 `Store.action()`，检查幂等键和数据库唯一约束 |
| 报告如何防止编造数字？ | `report.py` 的 `verify_report()` 和 `runtime.py` 的 `validate_node()` |

<a id="operations"></a>

## 常用操作

| 操作 | 使用方法 |
|---|---|
| 多轮追问 | 保持同一会话ID，完成分析后继续问“它最近14天带看转成交率怎样”；新的独立对话使用另一个会话ID |
| 查看记忆 | 点击“查看记忆”；“保存偏好”保存当前账号的长期偏好 |
| 清除记忆 | “清除本会话与偏好”会删除当前会话记忆及当前账号的长期偏好 |
| 工单审批 | 问题中明确提出“创建工单”，报告校验后选择“批准 / 继续”或“拒绝” |
| 查看历史任务 | 点击“刷新任务”，再选择任务ID查看报告和Trace |
| 恢复任务 | 服务重启后重新登录、选择原任务，按页面提示继续；需保留原 `state/` 目录 |
| 下载结果 | 报告区点击“下载报告 Markdown”，Trace区点击“下载 JSON” |
| 取消任务 | 点击“取消当前任务”；正在进行的外部调用结束后，在下一节点检查取消状态 |
| 比较检索效果 | 对同一问题分别使用完整混合检索、BM25消融、Dense消融和去掉精排，对比RAG的 `stages` 与 `evidence` |
| 查看多专家编排 | 将“编排方式”改为“三专家子图”，查看数据、知识和报告子图的调用情况 |

审批通过的工单保存在页面底部“本地工单 / 通知收件箱”，不向外部消息平台发送。

## 查询示例

1. `分析朝阳最近7天带看转成交率下降的门店，给出原因和跟进建议`：查数→计算→选择望京A店→漏斗→检索→校验。
2. `带看转成交率怎么算`：只走知识检索分支，跳过 SQL。
3. `最近7天转化率下降了`：触发澄清，输入“带看转成交率”后继续。
4. `分析海淀最近7天带看转成交率`：朝阳账号会被权限拦截；海淀或总监账号可查询该区域。
5. `分析朝阳最近7天带看转成交率并创建工单`：出现明确审批；通过后写入网页底部的**本地**工单收件箱。
6. 相同会话里问 `它最近14天带看转成交率怎样`：从短期记忆取门店对象。
7. 切换“三专家子图”、勾选关系图检索，观察图和 Trace。

演示时钟固定为 2026-09-28，数据覆盖 2025-08-01 至 2026-09-27。最近7天为09-21至09-27，基线为09-14至09-20。望京A店基线64/310=20.65%，本期29/312=9.29%，变化约-11.35个百分点。

## CLI、测试与评测

先运行一次启动器完成依赖安装。以下命令均在项目根目录运行：

```powershell
.venv\Scripts\python.exe -X utf8 app.py --ask --backend bm25
.venv\Scripts\python.exe -X utf8 app.py --ask --pause-after query_metrics --backend bm25
# 将上一条打印的任务ID替换进去；可以关闭进程、重新打开终端后执行
.venv\Scripts\python.exe -X utf8 app.py --resume 任务ID
.venv\Scripts\python.exe -m pytest -q
.venv\Scripts\python.exe -X utf8 evaluate.py
.venv\Scripts\python.exe -X utf8 scripts/check_mcp.py
```

CLI 审批恢复使用 `--resume 任务ID --approve yes` 或 `--approve no`；澄清使用 `--answer "带看转成交率"`。缺少明确审批值不会批准。

`evaluate.py` 运行4种检索消融和500条回归检查项，输出 `output/eval_results.json`。其中6条是手写检索Gold，494条是参数化合成回归；重复使用6条做消融不增加独立样本数。`--quick` 只跑检索，`--bm25-only` 不启动向量模型。

**Qdrant 本地目录仅供一个进程使用。运行完整检索评测前先关闭网页服务。** 同一个服务内部的并发请求已加锁。BM25测试可以与网页服务并存。

<a id="troubleshooting"></a>

## 常见问题

| 现象 | 处理方法 |
|---|---|
| 双击启动脚本后提示找不到Python | 检查 `python --version`；安装Python时勾选Add Python to PATH，重新打开终端 |
| NumPy安装报版本不匹配 | Python 3.11对应 `numpy==2.4.6`，确认使用项目当前的 `requirements.txt`；直接重新运行启动脚本 |
| 出现 `WinError 10048` 或端口占用 | 若已有服务，直接打开原页面；需要换端口时执行 `python -X utf8 launch.py --port 8766`，访问 http://127.0.0.1:8766 |
| 页面出现 `Failed to fetch` | 确认后端仍在运行、浏览器端口与后端一致，并通过HTTP地址进入页面；不要双击 `web/index.html` |
| 模型接口返回401、402或429 | 按错误状态检查密钥、余额或请求限制；修正配置后重新运行任务 |
| 页面一直显示“等待输入” | 检查澄清或审批区域，补充信息或明确选择批准、拒绝 |
| Qdrant提示目录被占用 | 关闭访问同一项目向量目录的其他进程；完整检索评测与网页服务不能同时运行 |
| 首次混合检索较慢 | 等待ONNX模型加载和向量索引初始化；可先用BM25模式确认基本流程 |
| 页面文案或配置提示未更新 | 使用 `Ctrl+F5` 刷新页面；模型配置文件会在下一次分析时读取 |

依赖安装失败时，错误信息位于启动窗口。需要检查环境可运行：

```powershell
.venv\Scripts\python.exe --version
.venv\Scripts\python.exe -m pip check
```

## 扩展

- MCP：`.venv\Scripts\python.exe -X utf8 mcp_server.py --user chaoyang`，stdio协议，3个只读工具和1个Schema资源。
- LoRA/SFT：先安装 `extras/requirements-training.txt`，再运行 `extras/train_lora.py --smoke`。领域模型训练使用 `--model 本地模型目录 --data 数据集路径`。详见能力说明书。
- Redis、vLLM：`extras/compose.yaml` 与 `extras/部署说明.md`。Redis可替换默认SQLite检索缓存；vLLM是可选Linux/GPU部署配置，尚未完成本地部署验证。
- 备用模型：复制 `fallback_model_config.example.json` 为 `fallback_model_config.json` 并填写。瞬时网络或HTTP错误重试失败后尝试备用模型，结果记录在 `fallback_used` 字段。

## 数据存储与适用范围

`data/business.sqlite3` 首次运行生成；`state/` 保存会话、任务、检查点、缓存、报告和本地工单。它们不会放进发行包。清理运行数据前应停止服务并备份。

登录采用本地演示账号，工单和通知保存在本地数据库，尚未接入企业身份与消息服务。知识库包含7条样例文档；关系图检索采用人工维护的实体关系和两跳遍历。评测使用合成业务数据，结果适用于当前样例范围。

## 模型来源与许可

内置BGE中文Embedding来自 [BAAI/bge-small-zh-v1.5](https://huggingface.co/BAAI/bge-small-zh-v1.5)，ONNX导出来自 [Qdrant](https://huggingface.co/Qdrant/bge-small-zh-v1.5)，MIT许可。

内置 `ms-marco-MultiBERT-L-12` 量化精排权重由 **Prithivi Da** 提供，源自 [prithivida/flashrank](https://huggingface.co/prithivida/flashrank)，按该仓库 **CC BY-SA 4.0** 许可原样分发；本项目没有改动权重。下载和使用库是 [FlashRank](https://github.com/PrithivirajDamodaran/FlashRank)，库代码为Apache-2.0。权重许可与库许可不同。许可文件见 `docs/licenses/`。
