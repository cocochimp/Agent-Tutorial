# 房产经营分析 Agent：功能与代码索引

本文说明系统架构、模块职责、运行流程和验证范围，并列出各项功能对应的文件、函数及行号。第3至第8章与参考资料《贝壳找房_AI经营分析Agent_实习复盘手册》的六项工作对应。代码链接指向 `docs/source/` 中的只读源码副本；程序修改应在项目源码文件中进行。

## 1. 请求处理流程

从网页输入“分析朝阳最近7天带看转成交率下降的门店，给出原因和跟进建议”。请求发送到 FastAPI，然后交给后台线程中的 StateGraph。查询、计算和检索分别由对应工具执行。

```text
浏览器 POST /api/tasks
  → 服务端登录身份
  → understand：问题变成 TaskSpec
  → agent_node：选择一个工具
  → schema_retrieval → 回到 agent_node
  → query_sql → 回到 agent_node
  → calculate → 回到 agent_node
  → analyze：按指标变化排序，选出下降最多的门店 S01
  → rag_search：用当前身份检索适用制度
  → generate_report → validate
  → 若需要审批：interrupt → Command(resume=用户选择)
  → execute_action（可选）→ finish
```

执行路径由任务类型与中间结果决定：指标定义问题跳过SQL；未发现下降时跳过漏斗分析；有歧义时进入澄清；越权请求终止；工单请求进入审批。网页流程图由编译后的StateGraph生成，Trace记录节点执行顺序。

**主要入口：**

1. [[app.py::create_task]]：任务创建接口。
2. [[estate_agent/state.py::AgentState]]：任务共享状态定义。
3. [[estate_agent/runtime.py::build_graph]]：节点、边和路由的注册。
4. [[estate_agent/runtime.py::plan_node]]：工具选择与调用约束。
5. [[estate_agent/runtime.py::run]]：检查点持久化与任务恢复。

规则模式通过 `offline_action()` 选择工具；模型模式调用 `ModelClient.decide()`，解析模型返回的工具名和参数。两种模式共用StateGraph、工具实现、权限控制与验证器。规则模式的测试结果仅用于验证程序行为。

## 2. 业务场景与系统架构

| 功能 | 实现 | 代码入口 |
|---|---|---|
| 城市运营、区域经理、身份权限 | 朝阳/海淀区域经理、总监、只读观察员四种演示账号 | [[estate_agent/auth.py::identity]]、[[app.py::current_user]] |
| 问数、查口径、异常分析、生成复盘 | 三个指标、两个区域、六家门店；固定演示时钟 | [[estate_agent/data.py::initialize]]、[[estate_agent/sql_tools.py::retrieve_schema]] |
| 接入层、理解层、Agent层、工具层、数据层 | FastAPI → TaskSpec → StateGraph → SQL/RAG → SQLite/Qdrant | [[app.py::create_task]]、[[estate_agent/runtime.py::execute_tool]] |
| UI、服务拆分、异步返回 | 前端创建任务后用SSE接收状态，报告/Trace逐步显示 | [[app.py::task_events]]、[[web/app.js]]、[[web/workspace.js]] |

当前支持带看转成交率、有效带看占比和24小时跟进率。内置数据未包含成本、收入或设备指标，相关查询返回不支持的指标错误。

## 3. 工作一：意图理解与结构化输出

| 能力 | 实现和检查点 | 代码 |
|---|---|---|
| 意图分类、槽位提取 | 区分analysis/knowledge，抽取地区、门店、指标、起止日期、比较方式、业务动作 | [[estate_agent/contracts.py::Intent]]、[[estate_agent/intent.py::understand]] |
| LLM结构化输出 | JSON Schema传给模型，解析后再次验证；格式错误最多补救一次 | [[estate_agent/llm.py::ModelClient.structured]] |
| 规则解析 | 无需API Key，按规则提取任务参数 | [[estate_agent/intent.py::rule_intent]] |
| 时间归一化 | 最近N天、昨天、上周、上个月、本月、明确日期；环比/同比 | [[estate_agent/intent.py::normalize]] |
| 歧义澄清 | 泛称“转化率”或没有前文的“它”触发interrupt | [[estate_agent/runtime.py::clarify_node]] |
| 权限前置 | 角色来自登录，不来自模型；门店必须属于授权区域 | [[estate_agent/intent.py::normalize]] |

示例TaskSpec包含 `metric=viewing_to_deal`、`region=朝阳`、`start=2026-09-21`、`end=2026-09-27`、`baseline_start=2026-09-14`、`baseline_end=2026-09-20`。SQL只接收验证后的对象。

用户角色由服务端登录信息确定。模型输出Schema不包含角色字段，region等参数仍需通过权限校验；朝阳账号请求海淀数据时返回权限错误。

## 4. 工作二：企业知识库 RAG

| 检索阶段 | 实现 | 代码 |
|---|---|---|
| 标题、章节、父子分块 | 制度条款作为parent，按句号/分号拆child，保留标题和节号 | [[estate_agent/retrieval.py::chunks]]、[[data/knowledge.json]] |
| ACL/Metadata Filter | 地区、角色、有效期过滤，按family取最高version | [[estate_agent/retrieval.py::allowed_documents]] |
| Query Rewrite | 规则模式扩展同义词；模型模式返回受Schema约束的检索词 | [[estate_agent/retrieval.py::rewrite_query]] |
| HyDE补救 | 词法召回为空时生成假设检索词；只用于重新检索，不进入证据 | [[estate_agent/retrieval.py::search_knowledge]] |
| Embedding | 本地ONNX `BAAI/bge-small-zh-v1.5`，512维 | [[estate_agent/retrieval.py::models]] |
| Vector DB | Qdrant本地持久化，Dense检索前过滤允许的chunk ID | [[estate_agent/retrieval.py::dense_rank]] |
| BM25 | 中文bigram分词，BM25词频、文档频率和长度归一化 | [[estate_agent/retrieval.py::tokenize]]、[[estate_agent/retrieval.py::bm25]] |
| RRF融合 | 对两路排名按 `1/(60+rank)` 累加 | [[estate_agent/retrieval.py::search_knowledge]] |
| Cross-Encoder精排 | FlashRank多语Cross-Encoder对query和候选段落配对评分 | [[estate_agent/retrieval.py::search_knowledge]] |
| Authority / Validity | 有效期硬过滤，权威分参与最终选择 | [[estate_agent/retrieval.py::allowed_documents]]、[[data/knowledge.json]] |
| MMR、去重、动态TopK | 相关性与bigram Jaccard冗余权衡，父文档去重，低分裁剪 | [[estate_agent/retrieval.py::search_knowledge]] |
| Parent回取、引用溯源 | 输出父条款全文、child ID、命中片段、精排分数、RRF分数 | [[estate_agent/retrieval.py::search_knowledge]] |
| 缓存 | 用户、角色、地区、文档版本、参数、模型和Prompt版本共同组成Key | [[estate_agent/storage.py::Cache]] |

`models/` 已带检索权重，CPU可运行。BM25模式完全不加载模型；Dense与Hybrid模式加载模型。Dense、BM25、融合不精排、完整Hybrid四种选项对应消融实验。

知识库包含7条样例文档。MMR使用词项Jaccard相似度衡量冗余。HyDE在模型模式下、词法召回为空时触发；规则模式使用同义词扩展。

验证入口：搜索“薪酬、72小时跟进、海淀规范”，朝阳区域经理的结果不得包含PRIVATE-01、OLD-01、HD-01。[[tests/test_agent.py::test_acl_no_evidence]]、[[tests/test_agent.py::test_versions]]。

## 5. 工作三：Tool Calling 与智能查数

模型收到6类工具的名称、描述、参数Schema：Schema检索、查数、计算、漏斗分析、知识检索、报告生成。定义位于 [[estate_agent/llm.py]] 的 `TOOLS`。

| 能力 | 实现 | 代码 |
|---|---|---|
| Function Calling | 每轮恰好接受一个工具调用，读取name与JSON arguments | [[estate_agent/llm.py::ModelClient.decide]]、[[estate_agent/runtime.py::plan_node]] |
| 参数契约 | JSON Schema拒绝多余参数；计划由Pydantic验证 | [[estate_agent/contracts.py::SQLPlan]] |
| Schema Retrieval | 返回表、字段、关联键、聚合规则 | [[estate_agent/sql_tools.py::retrieve_schema]] |
| Text-to-SQL | 自然语言→Task→模型选择受约束查询计划→确定性SQL编译 | [[estate_agent/sql_tools.py::query_metrics]] |
| AST检查 | sqlglot解析，单SELECT、白名单字段/表/函数、限制JOIN/LIMIT，禁止CTE/子查询/UNION | [[estate_agent/sql_tools.py::guard_sql]] |
| 只读与行级隔离 | SQLite mode=ro、TEMP授权视图、query_only、authorizer、执行超时 | [[estate_agent/sql_tools.py::execute_readonly]] |
| 指标计算 | SQL聚合分子分母，Python计算比例、百分点、相对变化、排序 | [[estate_agent/sql_tools.py::calculate_metrics]] |
| 空值与缺失日 | 分母0返回null；缺记录停止比较，避免错误归因 | [[estate_agent/sql_tools.py::calculate_metrics]] |
| 异常诊断 | 从结果选下降最多的店，拆有效带看与24小时跟进 | [[estate_agent/business.py::analyze_funnel]] |
| 工具返回契约 | status/data/source/latency_ms/error_code封装并进入Trace | [[estate_agent/runtime.py::execute_tool]] |

Text-to-SQL采用受约束查询计划，由代码编译SQL，并校验地区、指标口径和访问范围。`execute_readonly()`即使执行不带WHERE的SELECT，也只能读到该身份允许的门店。

关键测试：[[tests/test_agent.py::test_row_security_without_where]]、[[tests/test_agent.py::test_sql_ast]]、[[tests/test_agent.py::test_incomplete_data]]、[[tests/test_agent.py::test_zero_denominator]]。

## 6. 工作四：Agent规划与LangGraph编排

编排入口为 `build_graph()`：创建 `StateGraph(AgentState)`，通过 `add_node()` 注册节点、`add_edge()` 和 `add_conditional_edges()` 定义路由，最后调用 `compile(checkpointer=...)` 绑定检查点存储。

| 编排概念 | 对应实现 | 代码 |
|---|---|---|
| State | task、results、trace、seen、retry_count、tool_calls、risk_level、approval等显式字段 | [[estate_agent/state.py::AgentState]] |
| ReAct / 动态next_action | plan_node看工具观察结果决定一个行动，执行后再回到它 | [[estate_agent/runtime.py::plan_node]]、[[estate_agent/runtime.py::context_messages]] |
| Node | understand、query_sql、rag_search、analyze、validate、human_approval等 | [[estate_agent/runtime.py::build_graph]] |
| 条件边 | 读取state.next_node，映射到已注册节点 | [[estate_agent/runtime.py::build_graph]] |
| Checkpoint | 每轮节点状态通过SqliteSaver落盘 | [[estate_agent/runtime.py::run]] |
| Interrupt | 澄清、人工审批、演示暂停点均调用LangGraph interrupt | [[estate_agent/runtime.py::clarify_node]]、[[estate_agent/runtime.py::approval_node]]、[[estate_agent/runtime.py::checkpoint_gate]] |
| Resume | 同一thread_id读取旧检查点，再传Command(resume=...) | [[estate_agent/runtime.py::run]] |
| 重复调用检测 | 记录工具名+排序后的参数签名，重复即停止 | [[estate_agent/runtime.py::plan_node]] |
| 终止与预算 | max_tool_calls、max_model_calls、token/上下文预算、总时限 | [[estate_agent/runtime.py::guard]]、[[estate_agent/llm.py::ModelClient._request]] |
| 错误分类与重试 | 瞬时SQL/模型错误重试；参数/顺序错误允许模型重新规划 | [[estate_agent/runtime.py::execute_tool]]、[[estate_agent/runtime.py::retry_node]] |
| 高风险执行 | 审批成功且有权限后写本地工单；风险标记由服务端产生 | [[estate_agent/runtime.py::execute_action]] |

**检查点恢复。** 任务ID同时用作LangGraph thread_id。`state/checkpoints.sqlite3`保存每步状态及下一节点，`state/application.sqlite3`保存供网页查询的任务快照。新Python进程用相同thread_id恢复，不重新查已经成功的SQL。跨进程测试见 [[tests/test_agent.py::test_cross_process_resume]]。

**动作幂等。** 外部动作成功后到下一个检查点之间仍可能崩溃。`Store.action()`用run_id+动作类型生成唯一Key，并通过数据库唯一约束及INSERT OR IGNORE避免重复记录。[[estate_agent/storage.py::Store.action]]、[[tests/test_agent.py::test_approval_idempotency]]。

**条件路由验证。** “带看转成交率怎么算”进入知识检索分支；带看下降分析进入SQL与漏斗分支；“创建工单”进入human_approval，拒绝后跳过execute_action。可通过Mermaid图定义和Trace核对执行路径。

## 7. 工作五：Context与Memory

| 三种状态 | 保存在哪里 | 代码 |
|---|---|---|
| 当前任务状态 | LangGraph SQLite Checkpointer | [[estate_agent/runtime.py::run]] |
| 短期会话 | SQLite conversations，user+session隔离，最近4轮+摘要+focus，TTL | [[estate_agent/storage.py::Store.context]]、[[estate_agent/storage.py::Store.remember_turn]] |
| 长期偏好 | SQLite memories，user隔离、TTL，页面可保存和清除 | [[estate_agent/storage.py::Store.set_memory]]、[[estate_agent/storage.py::Store.memories]] |
| 模型上下文装配 | 当前Task、短期摘要、偏好、压缩工具观察、最近一次tool message | [[estate_agent/runtime.py::context_messages]] |
| 指代消解 | “它/这家店/刚才”读取本会话focus.store_id | [[estate_agent/intent.py::rule_intent]] |
| 删除记忆 | 删除当前会话和本账号长期偏好 | [[estate_agent/storage.py::Store.clear_memory]] |

会话摘要采用截断压缩，不调用模型。长期记忆仅保存用户显式填写的偏好，并在模型模式下加入上下文；规则模式使用固定报告模板。会话与记忆存储于SQLite，Redis用于热点检索缓存。

## 8. 工作六：幻觉治理与结果校验

| 能力 | 硬约束 | 代码 |
|---|---|---|
| 数字证据绑定 | 事实引用SQL-01；同期变化引用CALC-01；制度引用文档ID | [[estate_agent/report.py::build_report]] |
| 模型受约束生成 | 模型只选择候选事实ID、建议ID和待核查假设ID，不自由编造数字 | [[estate_agent/contracts.py::Narrative]]、[[estate_agent/runtime.py::report_node]] |
| 数字复核 | 用原始SQL聚合值重算指标与漏斗 | [[estate_agent/report.py::verify_report]] |
| 引用一致性 | 报告引用须与当前授权、有效版本的原文逐字段相等 | [[estate_agent/report.py::verify_report]] |
| 因果边界 | 报告将录入延迟、匹配问题等列为待核查假设，不能说已经证明原因 | [[estate_agent/report.py::markdown_report]] |
| Self-refinement | 模型选择了不存在的证据时，反馈校验错误，最多重新生成一次 | [[estate_agent/runtime.py::validate_node]] |
| 低置信度转人工 | confidence低于0.65进入human_approval；无制度证据不生成规范 | [[estate_agent/runtime.py::validate_node]] |

Verifier校验范围为结构化报告中的数字、时间范围和引用一致性，不覆盖开放文本的通用事实判断或因果识别。审批仅记录用户决定，报告中的证据缺失标记仍予以保留。

验证入口：[[tests/test_agent.py::test_tamper]]、[[tests/test_agent.py::test_tamper_both_state_and_citation]]、[[tests/test_model_loop.py::test_refinement_once]]。

## 9. 工程化：API、鉴权、并发、缓存、重试、观测

| 工程能力 | 实现 | 代码 |
|---|---|---|
| FastAPI | 登录、创建/列出/读取任务、SSE、恢复/取消、记忆、工单接口；/docs可查看OpenAPI | [[app.py]] |
| 登录与鉴权 | HttpOnly/SameSite cookie，服务端token哈希存储，读任务时校验owner | [[estate_agent/auth.py::login]]、[[app.py::owned_task]] |
| 并发限制 | 有界工作线程数与最大排队数，队列满返回429；同任务不可并发恢复 | [[app.py::submit]] |
| 请求取消 | 下一节点检查取消标志；已进行的外部HTTP等待超时返回 | [[app.py::cancel_task]]、[[estate_agent/runtime.py::guard]] |
| 重启中断发现 | 已排队/运行任务不在当前进程的pending表时显示interrupted | [[app.py::owned_task]] |
| 连接超时、指数退避 | HTTP35秒，瞬时错误最多3次尝试，.3/.6秒退避 | [[estate_agent/llm.py::ModelClient._request]] |
| 备用模型 | 瞬时错误两次后读取备用配置尝试；fallback_used记录切换 | [[estate_agent/llm.py::ModelClient._request]] |
| 降级路径 | 支持切换规则模式和BM25检索，执行模式记录在任务状态中 | [[app.py::RunBody]] |
| Redis热点缓存 | Redis GET/SETEX适配器，可配置；默认使用SQLite TTL缓存 | [[estate_agent/storage.py::Cache]]、[[project_config.json]] |
| Trace/可观测 | 节点、参数、结果、错误码、耗时；模型、Prompt版本、usage、Token | [[estate_agent/runtime.py::trace]]、[[estate_agent/llm.py::ModelClient.stats]] |
| 导出 | Markdown复盘、网页下载JSON Trace、本地报告文件 | [[estate_agent/report.py::markdown_report]]、[[web/app.js]] |

服务默认绑定127.0.0.1，采用四组本地演示账号。公网部署需要替换认证方式。工单与通知仅写入本地收件箱，尚未接入邮件、企业微信或企业SSO。当前幂等约束覆盖本地动作，接入外部服务时需传递相同的幂等Key。

## 10. 评测方法与结果

运行 `python evaluate.py`，代码入口 [[evaluate.py::main]]、[[evaluate.py::retrieval_eval]]、[[evaluate.py::layers]]。

| 层 | 样本及指标 | 验证方式 |
|---|---|---|
| 意图 | 120条参数化问题，地区/指标/天数完全匹配 | 与生成时Gold字段比对 |
| SQL | 同120种条件，执行与数值正确率 | 另写独立聚合SQL得到Gold |
| 任务 | 120条单双图交替，任务成功、完整工具序列正确率、重复调用比例、P95耗时 | 实际调用StateGraph |
| Verifier | 80个报告篡改负例 | 改数字、日期、原文、因果结论，看能否拦截 |
| 安全/澄清 | 54条越权、歧义、非法字段负例 | 必须拒绝或要求澄清 |
| 检索 | 6条手写Gold，4种消融 | Recall@20、Recall@5、MRR@5、nDCG@5、耗时 |

共500条检查项，包含6条手写检索Gold和494条参数化合成回归项；不同层之间存在相关样本。每条检索Gold见 [[eval_cases.json]]，合成规则见 [[evaluate.py::generated_cases]]。完整原始结果在 `output/eval_results.json`。

基准评测结果：120/120意图、120/120 SQL、120/120任务、80/80篡改拦截、54/54安全/澄清检查通过。6条检索Gold在4种设置下Recall@5均为1；完整Hybrid MRR@5为0.9167，其他3种为1。在该样本集上，精排未提高MRR。样本规模较小，结果不足以评价泛化能力；Dense首轮耗时包含模型加载，稳态性能需另行测量。

上述评测采用规则决策与合成数据，用于验证工程行为。规则解析正确率、结构化篡改拦截率分别统计，不等同于LLM理解准确率或开放回答Faithfulness。参考资料中的生产规模与业绩指标不纳入本项目评测结果。

## 11. 扩展模块

| 项目 | 已提供内容 | 代码与运行方式 |
|---|---|---|
| GraphRAG | 小型人工实体关系图，两跳遍历，关系关联的文档参与排序，仍受ACL限制 | [[estate_agent/graph_rag.py::graph_lookup]]、[[data/relations.json]]；网页勾选关系图检索 |
| MCP | stdio MCP服务，3个工具+1个资源，身份在启动时绑定 | [[mcp_server.py::create_server]]；`python scripts/check_mcp.py`实测握手/发现/调用/越权 |
| Multi-Agent | Supervisor路由到数据、知识、报告三个StateGraph子图；共享受控状态 | [[estate_agent/runtime.py::supervisor_route]]、[[estate_agent/runtime.py::build_graph]] |
| LoRA / SFT | PEFT低秩适配、assistant-only loss、训练/验证分开、保存adapter、烟雾模式重载 | [[extras/train_lora.py::main]]；先安装extras/requirements-training.txt，再`python extras/train_lora.py --smoke` |
| vLLM | Linux/GPU容器配置及兼容API接入；可扩展LoRA服务参数 | [[extras/compose.yaml]]、[[estate_agent/config.py::load_model_config]] |

关系图检索基于人工维护的实体关系，不含社区发现与社区摘要。Multi-Agent由共享规划模型向专家子图分派任务。LoRA冒烟测试覆盖随机小模型的1024个可训练参数更新、保存和重载；领域模型训练需通过 `--model` 指定基座，并另行评测效果。vLLM与Redis提供部署配置，尚未完成本地服务联调。部署步骤见 `extras/部署说明.md`。

## 12. 常见故障与阅读顺序

**Failed to fetch**：启动后端，用HTTP地址进入；不要打开file://页面。检查终端是否仍运行、浏览器端口与启动端口是否一致。前后端由同一个FastAPI服务提供。

**模型未配置/401/402/429**：检查deepseek_config.json、密钥、余额、并发限制；API Key只在Python服务端读取。[[estate_agent/config.py::load_model_config]]。

**Qdrant目录被占用**：不要同时启动两个完整检索进程。先关闭一个，或把完整项目复制到独立目录运行。服务内部线程使用锁。

**等待输入**：任务正在等待澄清或审批。查看网页输入框；CLI传`--answer`或`--approve`。跨进程恢复保留任务ID和state目录。

**模型下载失败**：检索模型位于`models/`。缺少权重时，运行`python scripts/prepare_models.py`下载；也可切换至不依赖向量模型的BM25模式。

建议按 `data.py → contracts.py → intent.py → sql_tools.py → retrieval.py → runtime.py → report.py → app.py → tests/ → evaluate.py` 阅读。可结合Trace中的输入、输出与节点名称核对各模块的调用关系。

## 13. 官方参考

- [LangGraph persistence](https://docs.langchain.com/oss/python/langgraph/persistence)
- [LangGraph interrupts](https://docs.langchain.com/oss/python/langgraph/interrupts)
- [FastEmbed models](https://qdrant.github.io/fastembed/examples/Supported_Models/)
- [FlashRank](https://github.com/PrithivirajDamodaran/FlashRank)
- [DeepSeek models and API](https://api-docs.deepseek.com/quick_start/pricing/)
- [MCP Python SDK](https://github.com/modelcontextprotocol/python-sdk)
- [PEFT LoRA](https://huggingface.co/docs/peft/en/package_reference/lora)

源码映射由 `scripts/build_manual.py` 自动生成；修改Python文件后重新运行该脚本，可刷新行号和源码镜像。
