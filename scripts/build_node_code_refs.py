"""为三个项目（estate-agent / photo-q / air-ticket）每个工作项的每个执行节点生成「实例代码」。

用户要求：全链路节点图的每个节点严禁出现无实例代码的情况（io 允许缺失，代码必须有）。
前端 teaching.js 已支持 codeRef.node 过滤 + codeRef.text 内嵌渲染。

每个 codeRef 结构：{node, path, start, end, text, note}
- text：该节点真实业务场景的教学 Python 代码（前端优先渲染 text）
- path：教程文件标题（展示用，指向 tutorial-data 里语义最近的文件）
- start/end：有 text 时固定 1/N，不参与切片
"""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PROJECTS = ['estate-agent', 'photo-q', 'air-ticket']

# ============ 各项目节点代码（业务场景教学示意） ============
CODE = {}

CODE['estate-agent'] = {
    'understand': '''# 意图理解：自然语言经营问题 → 结构化 Task Spec（estate_agent/intent.py）
# 把「朝阳最近7天带看转成交率为什么掉了」转成结构化查询任务
def parse_task_spec(question: str, session: dict) -> dict:
    spec = llm.extract_entities(question, schema=TASK_SCHEMA)   # 抽取 region/metric/date_range
    spec["compare_to"] = spec.get("compare_to") or "previous_7_days"
    spec["confidence"] = spec.get("rewrite_confidence", 0.9)
    if spec["confidence"] < 0.7:                                 # 低置信度回退原始诉求
        spec["fallback"] = question
    return spec''',
    'clarify': '''# 澄清追问：缺失关键参数时先问，不硬猜（estate_agent/intent.py）
MISSING_FIELDS = {"region": "哪个片区？", "metric": "看哪个指标？", "date_range": "看哪段时间？"}

def clarify_if_needed(spec: dict, history: list) -> dict | None:
    missing = [f for f in MISSING_FIELDS if not spec.get(f)]
    if not missing:
        return spec
    if len(history) >= 2:                                        # 已追问过一轮，取默认值
        spec.update({f: DEFAULT[f] for f in missing})
        return spec
    return {"ask": "，".join(MISSING_FIELDS[m] for m in missing)}''',
    'agent_node': '''# ReAct 规划：根据当前状态决定下一步调哪个工具（estate_agent/runtime.py）
def plan_next(state: AgentState) -> AgentState:
    tools = ["query_metric", "compare_baseline", "search_knowledge", "generate_report"]
    decision = llm.react_reason(
        question=state.question,
        observation=state.last_output,      # 上一步工具结果
        available=tools,
    )
    state.next_action = decision.tool       # 自主选择工具与入参
    state.confidence = decision.confidence
    return state''',
    'schema_retrieval': '''# 字段/表结构检索：Text-to-SQL 前先找到可用表字段（estate_agent/retrieval.py）
def retrieve_schema(metric: str) -> list[dict]:
    q = f"{metric} 字段 表"
    candidates = hybrid_recall(q, top_k=5)     # 语义 + BM25 双路召回
    return [c["schema"] for c in candidates if c["score"] >= 0.6]''',
    'query_sql': '''# 指标查询：生成 SQL 并执行（estate_agent/sql_tools.py）
def query_metric(spec: dict) -> pd.DataFrame:
    sql = text_to_sql(spec, schema=retrieve_schema(spec["metric"]))
    df = engine.execute(sql)                    # 只读查询，参数化防注入
    return validate_shape(df, spec["metric"])   # 空值/口径校验''',
    'calculate': '''# 指标计算：环比/同比/转化率等衍生指标（estate_agent/business.py）
def calc_derived(df: pd.DataFrame) -> dict:
    cur, prev = df.iloc[-1], df.iloc[-2]
    return {
        "current": float(cur.value),
        "prev": float(prev.value),
        "wow": round((cur.value / prev.value - 1) * 100, 1),  # 环比
        "trend": "up" if cur.value > prev.value else "down",
    }''',
    'analyze': '''# 归因分析：指标异动拆到门店/经纪人/作业环节（estate_agent/business.py）
def attribute_change(df: pd.DataFrame) -> list[dict]:
    stores = df.groupby("store").agg(rate=("rate", "mean")).sort_values("rate")
    factors = llm.reason_factors(stores, top_k=3)   # 定位掉得最多的门店
    return [
        {"store": s, "rate": r, "likely_cause": c}
        for s, r, c in factors
    ]''',
    'rag_search': '''# RAG 检索：经营规范/制度文档召回（estate_agent/retrieval.py）
def search_knowledge(query: str, top_k: int = 3) -> list[dict]:
    dense = vector_top50(query)          # 语义召回
    sparse = bm25_top50(query)           # 关键词召回
    fused = rrf_merge(dense, sparse, k=50)          # 融合去重取前 20
    reranked = cross_encoder(fused, keep=10)        # 精排
    return dedup_mmr(reranked, top_k)[:top_k]       # 去重后注入''',
    'generate_report': '''# 报告生成：结构化结论 + 依据引用（estate_agent/report.py）
def build_report(state: AgentState) -> str:
    return llm.generate(
        template=REPORT_TEMPLATE,                    # 结论/数据/依据分字段
        data=state.metrics,
        sources=state.knowledge,                     # 唯一数据源：只能引用检索到的制度
        constraints={"cite_required": True},         # 每条结论必须带来源
    )''',
    'validate': '''# 结果校验：口径/数字/引用一致性（estate_agent/contracts.py）
def validate_result(report: dict, metrics: dict) -> dict:
    ok = all(abs(float(report[k]) - metrics[k]) < 1e-6 for k in metrics)
    cited = all(has_source(c) for c in report["conclusions"])
    return {"valid": ok and cited, "errors": collect_errors()}
# 数字逐项与 SQL 结果比对，引用与检索材料比对，不依赖模型自觉''',
    'checkpoint_gate': '''# 检查点：置信度门 + 人工兜底路由（estate_agent/runtime.py）
CONFIDENCE_THRESHOLD = 0.85

def gate(state: AgentState) -> str:
    if state.confidence < CONFIDENCE_THRESHOLD:
        return "human_approval"     # 低置信度转人工
    if state.retries >= MAX_RETRIES:
        return "human_approval"     # 超重试次数兜底
    return "execute_action"''',
    'retry_node': '''# 有限重试：错误信息回灌给模型再决策（estate_agent/runtime.py）
def retry(state: AgentState) -> AgentState:
    state.retries += 1
    state.feedback = state.last_error          # 把具体错误带回规划节点
    state.next_action = None
    return state''',
    'execute_action': '''# 执行动作：路由到具体工具并记录结果（estate_agent/runtime.py）
TOOL_REGISTRY = {"query_metric": query_metric, "search_knowledge": search_knowledge,
                 "calc_derived": calc_derived, "attribute_change": attribute_change}

def execute_action(state: AgentState) -> AgentState:
    tool = TOOL_REGISTRY[state.next_action]
    try:
        state.last_output = tool(**state.args)
        state.last_error = None
    except ToolCallError as e:                 # 参数校验失败 → 进重试
        state.last_error = str(e)
    return state''',
    'human_approval': '''# 人工审批：低置信度/高风险动作给人工确认（estate_agent/runtime.py）
def human_approval(state: AgentState) -> AgentState:
    state.approval = await ask_user(
        action=state.next_action,
        evidence=state.last_output,
        reason=state.feedback or "置信度低于阈值",
    )
    return state''',
    'finish': '''# 结束节点：汇总最终回答并写审计记录（estate_agent/runtime.py）
def finish(state: AgentState) -> AgentState:
    state.answer = state.report if state.report else "未生成结论，已转人工处理"
    audit.log(question=state.question, path=state.trace, cost=state.tokens)
    return state''',
}

CODE['photo-q'] = {
    'user_input': '''# 入口：接收照片 + 学生诉求（photo_agent/graph.py）
def user_input(raw: dict) -> AgentState:
    return AgentState(image=raw["image"], question=raw.get("question"),
                      session_id=raw.get("session_id"), retries=0)''',
    'ocr_parse': '''# OCR 识别：一图多题先切题（photo_agent/tools.py）
def ocr_parse(image: bytes) -> list[dict]:
    blocks = ocr.recognize(image)                 # 版面分析 + 文字识别
    return split_questions(blocks)                # 按题号/题面边界切成多题
# 识别结果示例：[{"qid": 1, "text": "求导数 y=x^2", "latex": ...}, ...]''',
    'query_understand': '''# 意图理解：拆题 + 指代消解（photo_agent/query.py）
def parse_question(blocks: list[dict], history: list) -> list[dict]:
    sub_queries = [b["text"] for b in blocks]     # 一图多题拆成多条子 query
    resolved = resolve_reference(sub_queries, history)   # 「它/这题」绑定上下文
    return [{"query": q, "intent": classify(q), "confidence": 0.9} for q in resolved]''',
    'step_back': '''# Step-back：把具体题目抽象成考点维度用于召回（photo_agent/query.py）
def step_back(query: str) -> str:
    return llm.abstract(query, dims=["考点", "公式", "年级"])   # 例：「求导数」→「导数 求导法则」
# 抽象结果喂给 Filter 与检索，解决「换个说法搜不到原题」''',
    'agent_node': '''# ReAct 规划：决定下一步调哪个工具（photo_agent/graph.py）
def plan_next(state: AgentState) -> AgentState:
    state.next_action = llm.react_reason(
        question=state.current_query,
        observation=state.last_output,
        available=["tool_retrieve", "tool_generate", "tool_rerank"],
    )
    return state''',
    'schema_validate': '''# 工具参数校验：缺参/类型错即抛错触发重试（photo_agent/tools.py）
def validate_call(tool: str, args: dict) -> None:
    schema = TOOL_SCHEMAS[tool]
    for field, rule in schema["params"].items():
        if rule["required"] and field not in args:
            raise ToolCallError(f"{tool} 缺必填参数 {field}")
        if type(args.get(field)) is not rule["type"]:
            raise ToolCallError(f"{tool} 参数 {field} 类型应为 {rule['type']}")''',
    'tool_retrieve': '''# 题库检索：向量 + BM25 双路召回（photo_agent/retrieval.py）
def retrieve(query: str, filters: dict) -> list[dict]:
    dense = vector_top60(query)      # 语义召回（懂「换说法」）
    sparse = bm25_top60(query)       # 关键词召回（公式/符号精确匹配）
    fused = rrf_merge(dense, sparse, k=60)          # 融合取前 40
    return hard_filter(fused, filters)              # 按年级/题型硬过滤''',
    'tool_rerank': '''# 精排：Cross-Encoder 逐对打分（photo_agent/retrieval.py）
def rerank(candidates: list[dict], query: str) -> list[dict]:
    scored = [(c, reranker.score(query, c["text"])) for c in candidates]
    scored.sort(key=lambda x: -x[1])
    return [c for c, s in scored if s >= 0.6][:10]   # 动态截断：分≥0.6 最多10''',
    'mmr_filter': '''# 去重：MMR 平衡相关性与多样性（photo_agent/retrieval.py）
def mmr_dedup(scored: list[dict], lam: float = 0.7, k: int = 5) -> list[dict]:
    chosen, pool = [], scored[:]
    while pool and len(chosen) < k:
        def value(c):
            rel = c["score"]
            sim = max(sim_between(c, x) for x in chosen) if chosen else 0
            return lam * rel - (1 - lam) * sim
        best = max(pool, key=value)
        chosen.append(pool.pop(pool.index(best)))
    return chosen''',
    'rag_search': '''# RAG 组装：注入前 3 条相似题与解析（photo_agent/retrieval.py）
def assemble_context(query: str) -> list[str]:
    hits = retrieve(query, {})
    hits = mmr_dedup(rerank(hits, query), k=5)
    return [h["solution"] for h in hits[:3]]        # 供生成节点引用''',
    'tool_generate': '''# 解题生成：基于相似题解析，分步讲解（photo_agent/tools.py）
def generate_solution(query: str, context: list[str]) -> str:
    return llm.generate(
        template=SOLUTION_TEMPLATE,      # 思路/步骤/答案分字段
        question=query,
        references=context,              # 唯一数据源：只能引用检索到的相似题
        steps_required=4,
    )''',
    'verify_node': '''# 校验：答案正确性 + 引用一致性（photo_agent/verify.py）
def verify(sol: dict, context: list[str]) -> dict:
    correct = check_answer(sol["answer"])                    # 代码验算
    cited = all(ref in context for ref in sol["refs"])       # 引用必须在检索材料里
    confidence = 0.5 * correct + 0.5 * cited
    return {"pass": confidence >= 0.85, "confidence": confidence,
            "errors": ["答案错误", "引用悬空"] if not (correct and cited) else []}''',
    'retry_node': '''# 重试：错误信息回灌定向修改（photo_agent/graph.py）
def retry(state: AgentState) -> AgentState:
    state.retries += 1
    if state.retries > MAX_RETRIES:
        return route(state, "human_review")
    state.feedback = state.verify_errors     # 如「答案验算错误，请重算」
    return route(state, "tool_generate")''',
    'human_review': '''# 人工兜底：低置信度/超重试转人工审核（photo_agent/graph.py）
def human_review(state: AgentState) -> AgentState:
    state.result = await ask_teacher(state.draft, state.verify_errors)
    return state''',
    'checkpoint_gate': '''# 检查点：路由 + 状态持久化（photo_agent/graph.py）
def gate(state: AgentState) -> str:
    if state.verify.pass:
        return "finish"
    if state.retries < MAX_RETRIES:
        return "retry_node"
    return "human_review"''',
    'finish': '''# 结束：合并多题结果并返回（photo_agent/graph.py）
def finish(state: AgentState) -> AgentState:
    state.answer = join_answers(state.per_question)   # 逐题答案拼装
    memory.record(state.session_id, state.questions)  # 写入记忆
    return state''',
    'memory_node': '''# 记忆：多轮上下文 + 学生画像（photo_agent/memory.py）
def remember(state: AgentState) -> AgentState:
    hist = state.history
    ctx = window_summary(hist, keep_rounds=5)         # 滑动窗口 + 摘要
    state.prompt_budget = prioritize(
        [system_prompt, state.question, ctx, profile_top3(state.user)], budget=4096)
    return state''',
}

CODE['air-ticket'] = {
    'user_input': '''# 入口：接收退改签口语诉求 + 订单上下文（air_ticket_agent/graph.py）
def user_input(raw: dict) -> AgentState:
    return AgentState(question=raw["question"],
                      order_id=raw.get("order_id"),
                      session_id=raw.get("session_id"), retries=0)''',
    'order_align': '''# 订单字段对齐：把口语绑定到订单（air_ticket_agent/query.py）
def align_order(raw: str, order: dict) -> dict:
    return {
        "airline": order["airline"],          # 从订单栈取，不猜
        "cabin": order["cabin"],
        "fare_product": order.get("fare_product"),
        "travel_date": order.get("travel_date"),
        "raw": raw,
    }
# 「这票能退吗」→ 绑定到 ORD20260926001 的 MU/Y/特价舱''',
    'query_understand': '''# 意图理解：拆解 + 指代消解 + 结构化输出（air_ticket_agent/query.py）
def parse_intent(question: str, order: dict) -> dict:
    subs = split_sub_queries(question)            # 一句话多诉求拆成多条
    resolved = [resolve_ref(q, order) for q in subs]   # 「那退票呢」回填订单
    return {"sub_queries": resolved,
            "filters": {"airline": order["airline"], "cabin": order["cabin"]},
            "rewrite_confidence": 0.91}           # 低置信度回退原始 query''',
    'step_back': '''# Step-back：诉求抽象成规则维度（air_ticket_agent/query.py）
def step_back(intent: dict) -> dict:
    return llm.abstract(intent, dims=["舱位", "票价产品", "动作", "费用类型"])
# 「特价票改到后天」→ 「Y舱 特价 改期 手续费」，供 Filter 与规则召回''',
    'agent_node': '''# ReAct 规划：决定先调哪个工具（air_ticket_agent/graph.py）
def plan_next(state: AgentState) -> AgentState:
    tools = ["tool_flight_status", "tool_rule_retrieve",
             "tool_recalc_fee", "tool_scheme_gen"]
    state.next_action = llm.react_reason(
        question=state.current_sub_query,
        observation=state.last_output,
        available=tools,
    )
    return state''',
    'schema_validate': '''# 工具参数校验：日期必须是绝对日期，防止传「后天」（air_ticket_agent/tools.py）
def validate_call(tool: str, args: dict) -> None:
    if "target_date" in args and not re.fullmatch(r"\\d{4}-\\d{2}-\\d{2}", args["target_date"]):
        raise ToolCallError("target_date 必须为 YYYY-MM-DD 绝对日期，请换算后重试")
    if tool == "recalc_change_fee" and not args.get("order_id"):
        raise ToolCallError("recalc_change_fee 缺必填 order_id")''',
    'tool_flight_status': '''# 航班状态查询：判断改签可行性（air_ticket_agent/tools.py）
def check_flight_status(flight_no: str, date: str) -> dict:
    return gds.query_status(flight_no=flight_no, date=date)
# 返回：{"status": "scheduled", "delay": 0, "cancel": False}
# 航班取消/延误时改签规则不同，状态是改签方案的前置输入''',
    'tool_rule_retrieve': '''# 规则检索：双路召回 + RRF + 精排（air_ticket_agent/retrieval.py）
def retrieve_rules(query: str, filters: dict) -> list[dict]:
    dense = vector_top60(query)                  # 语义：懂「经济舱打折票≈Y舱特价」
    sparse = bm25_top60(query)                   # 关键词：MU / Y / T fare 精确命中
    fused = rrf_merge(dense, sparse, k=60)       # 融合去重取前 40
    filtered = hard_filter(fused, filters)       # 同航司/舱位硬过滤
    top10 = cross_encoder(filtered, min_score=0.6, max_n=10)
    return mmr_dedup(top10, lam=0.7, k=5)        # 去冗余后注入前 3''',
    'tool_rerank': '''# 精排：Cross-Encoder 逐对打分（air_ticket_agent/retrieval.py）
def rerank(candidates: list[dict], query: str) -> list[dict]:
    scored = sorted(((c, reranker.score(query, c["text"])) for c in candidates),
                    key=lambda x: -x[1])
    kept = [c for c, s in scored if s >= 0.6]
    return kept[:10] if len(kept) >= 2 else kept[:2]   # 动态截断：最多10 至少2''',
    'mmr_filter': '''# 去重：MMR 剔除近似重复规则（air_ticket_agent/retrieval.py）
def mmr_dedup(scored: list[dict], lam: float = 0.7, k: int = 5) -> list[dict]:
    chosen, pool = [], scored[:]
    while pool and len(chosen) < k:
        def value(c):
            rel = c["score"]
            sim = max(sim_rules(c, x) for x in chosen) if chosen else 0
            return lam * rel - (1 - lam) * sim
        best = max(pool, key=value)
        chosen.append(pool.pop(pool.index(best)))
    return chosen''',
    'rag_search': '''# RAG 组装：注入前 3 条政策供生成引用（air_ticket_agent/retrieval.py）
def assemble_policy_context(query: str, filters: dict) -> list[dict]:
    hits = retrieve_rules(query, filters)
    return hits[:3]                                # 唯一数据源：生成只能引用这些''',
    'tool_recalc_fee': '''# 差价计算：唯一金额来源，模型不许自己算（air_ticket_agent/tools.py）
def recalc_change_fee(order_id: str, target_date: str) -> dict:
    return engine.calc_change_fee(order_id=order_id, target_date=target_date)
# 返回：{"change_fee": 580, "fare_diff": 120, "currency": "CNY"}
# 金额一律走引擎工具 + 模板回填，生成层不写数字''',
    'tool_scheme_gen': '''# 方案生成：唯一数据源 + 结构化输出（air_ticket_agent/tools.py）
def gen_scheme(policy: dict, fee: dict) -> dict:
    return {
        "refundable": policy["refundable"],
        "changeable": policy["changeable"],
        "change_fee": fee["change_fee"],        # 金额从工具结果模板回填
        "policy_ref": policy["id"],              # 政策引用必须有出处
    }''',
    'verify_node': '''# 质量校验：金额后验 + 事实核查 + 置信度（air_ticket_agent/verify.py）
def verify(scheme: dict, fee: dict, rules: list[dict]) -> dict:
    quote_ok = extract_amount(scheme["text"]) == fee["change_fee"]   # 正则抽数比对
    claims = split_claims(scheme["text"])
    supported = all(has_evidence(c, rules) for c in claims)          # 政策比对
    confidence = min(float(quote_ok), float(supported))
    return {"confidence": confidence, "quote_mismatch": not quote_ok,
            "unsupported_claim": not supported}''',
    'retry_node': '''# 重试：错误信息回灌定向重写（air_ticket_agent/graph.py）
def retry(state: AgentState) -> AgentState:
    state.retries += 1
    if state.retries > MAX_RETRIES:
        return route(state, "human_review")
    state.feedback = state.verify_errors       # 如「金额必须引用工具580」「删除无依据新规」
    return route(state, "tool_scheme_gen")''',
    'human_review': '''# 人工兜底：低置信度不硬输出（air_ticket_agent/graph.py）
def human_review(state: AgentState) -> AgentState:
    state.answer = await ask_cs(state.draft, state.verify_errors)
    return state
# 资金流红线：宁可让用户等人工，不可给错误政策/差价''',
    'checkpoint_gate': '''# 检查点：置信度门 + 出票确认（air_ticket_agent/graph.py）
CONFIDENCE_THRESHOLD = 0.85

def gate(state: AgentState) -> str:
    if state.action == "issue_ticket":
        return "await_confirm"                  # 出票必须用户确认（human-in-the-loop）
    if state.verify.confidence < CONFIDENCE_THRESHOLD:
        return "human_review"                   # 低置信度转人工
    return "finish"''',
    'finish': '''# 结束：合并子诉求结果 + 记忆写入（air_ticket_agent/graph.py）
def finish(state: AgentState) -> AgentState:
    state.answer = join_subs(state.per_sub_query)      # 退+改多诉求合并返回
    memory.record(state.session_id, state.order_stack, state.profile_hint)
    return state''',
    'memory_node': '''# 记忆：订单栈 + 滑动窗口 + 画像按需注入（air_ticket_agent/memory.py）
def remember(state: AgentState) -> AgentState:
    ctx = window_summary(state.history, keep_rounds=5)     # 旧内容压摘要
    profile = profile_top3(state.user, route=state.route)  # 画像当一路召回
    state.prompt_budget = prioritize(
        [system_prompt, state.question, state.policy_top3, profile], budget=4096)
    return state
# 优先级：系统提示 > 当前诉求 > 检索政策/差价 > 画像''',
}

# path 标题映射（指向 tutorial-data 中语义最近的文件）
PATH_HINT = {
    'estate-agent': {
        'understand': 'estate_agent/intent.py', 'clarify': 'estate_agent/intent.py',
        'agent_node': 'estate_agent/runtime.py', 'checkpoint_gate': 'estate_agent/runtime.py',
        'retry_node': 'estate_agent/runtime.py', 'execute_action': 'estate_agent/runtime.py',
        'finish': 'estate_agent/runtime.py', 'rag_search': 'estate_agent/retrieval.py',
        'schema_retrieval': 'estate_agent/retrieval.py', 'query_sql': 'estate_agent/sql_tools.py',
        'calculate': 'estate_agent/business.py', 'analyze': 'estate_agent/business.py',
        'generate_report': 'estate_agent/report.py', 'validate': 'estate_agent/contracts.py',
        'human_approval': 'estate_agent/runtime.py',
    },
    'photo-q': {
        'user_input': 'photo_agent/graph.py', 'ocr_parse': 'photo_agent/tools.py',
        'query_understand': 'photo_agent/query.py', 'step_back': 'photo_agent/query.py',
        'agent_node': 'photo_agent/graph.py', 'schema_validate': 'photo_agent/tools.py',
        'tool_retrieve': 'photo_agent/retrieval.py', 'tool_rerank': 'photo_agent/retrieval.py',
        'mmr_filter': 'photo_agent/retrieval.py', 'rag_search': 'photo_agent/retrieval.py',
        'tool_generate': 'photo_agent/tools.py', 'verify_node': 'photo_agent/verify.py',
        'retry_node': 'photo_agent/graph.py', 'human_review': 'photo_agent/graph.py',
        'checkpoint_gate': 'photo_agent/graph.py', 'finish': 'photo_agent/graph.py',
        'memory_node': 'photo_agent/memory.py',
    },
    'air-ticket': {
        'user_input': 'air_ticket_agent/graph.py', 'order_align': 'air_ticket_agent/query.py',
        'query_understand': 'air_ticket_agent/query.py', 'step_back': 'air_ticket_agent/query.py',
        'agent_node': 'air_ticket_agent/graph.py', 'schema_validate': 'air_ticket_agent/tools.py',
        'tool_flight_status': 'air_ticket_agent/tools.py', 'tool_rule_retrieve': 'air_ticket_agent/retrieval.py',
        'tool_rerank': 'air_ticket_agent/retrieval.py', 'mmr_filter': 'air_ticket_agent/retrieval.py',
        'rag_search': 'air_ticket_agent/retrieval.py', 'tool_recalc_fee': 'air_ticket_agent/tools.py',
        'tool_scheme_gen': 'air_ticket_agent/tools.py', 'verify_node': 'air_ticket_agent/verify.py',
        'retry_node': 'air_ticket_agent/graph.py', 'human_review': 'air_ticket_agent/graph.py',
        'checkpoint_gate': 'air_ticket_agent/graph.py', 'finish': 'air_ticket_agent/graph.py',
        'memory_node': 'air_ticket_agent/memory.py',
    },
}

NOTE_HINT = {
    'understand': '意图解析：自然语言问题 → 结构化任务，低置信度回退', 'clarify': '缺失参数澄清追问，不硬猜',
    'agent_node': 'ReAct 决策：根据上一步结果选择下一步工具', 'checkpoint_gate': '置信度门 + 重试/人工兜底路由',
    'retry_node': '有限重试：具体错误信息回灌模型', 'execute_action': '工具路由与执行，校验失败进重试',
    'finish': '汇总最终回答并写入审计/记忆', 'rag_search': 'RAG 双路召回 + 精排，注入上下文',
    'schema_retrieval': 'Text-to-SQL 前先检索可用表字段', 'query_sql': '指标 SQL 生成与执行（参数化防注入）',
    'calculate': '环比/转化率等衍生指标计算', 'analyze': '指标异动归因拆解',
    'generate_report': '报告生成：唯一数据源 + 引用约束', 'validate': '数字/引用一致性校验',
    'human_approval': '低置信度/高风险动作人工确认',
    'user_input': '入口：接收用户诉求与上下文', 'ocr_parse': 'OCR 识别 + 一图多题切题',
    'query_understand': '意图理解：拆题 + 指代消解 + 结构化输出', 'step_back': 'Step-back 抽象成考点/规则维度',
    'schema_validate': '工具参数 Schema 校验，失败触发重试', 'tool_retrieve': '题库双路召回 + 融合 + 过滤',
    'tool_rerank': 'Cross-Encoder 精排，动态截断', 'mmr_filter': 'MMR 去重，λ≈0.7 平衡相关与多样',
    'tool_generate': '基于相似题解析分步讲解（唯一数据源）', 'verify_node': '答案验算 + 引用一致性 + 置信度',
    'human_review': '低置信度/超重试转人工兜底', 'memory_node': '滑动窗口摘要 + 画像按需注入',
    'order_align': '订单字段对齐：口语绑定订单，回填指代', 'tool_flight_status': '航班状态查询，改签前置判断',
    'tool_rule_retrieve': '政策双路召回 + 硬过滤 + 精排 + 去重', 'tool_recalc_fee': '引擎差价计算（唯一金额来源）',
    'tool_scheme_gen': '方案生成：模板回填金额 + 政策引用', 'rag_search': 'RAG 组装：注入前 3 条政策供生成引用',
}


def build_code_refs(pid: str, work: dict) -> list[dict]:
    refs = []
    for node in work['nodes']:
        code = CODE.get(pid, {}).get(node)
        if not code:
            raise SystemExit(f'缺少节点代码: {pid} {work["id"]} {node}')
        refs.append({
            'node': node,
            'path': PATH_HINT.get(pid, {}).get(node, f'{pid}/graph.py'),
            'start': 1,
            'end': code.count('\n') + 1,
            'text': code.rstrip('\n'),
            'note': NOTE_HINT.get(node, '该节点实例代码'),
        })
    return refs


def main():
    for pid in PROJECTS:
        p = ROOT / 'web' / 'projects' / pid
        wi_path = p / 'work-items.json'
        wi = json.loads(wi_path.read_text(encoding='utf-8'))
        for work in wi['workItems']:
            work['codeRefs'] = build_code_refs(pid, work)
        wi_path.write_text(json.dumps(wi, ensure_ascii=False, indent=2), encoding='utf-8')
        total = sum(len(w['nodes']) for w in wi['workItems'])
        print(f'{pid}: {total} 节点全部补齐实例代码')


if __name__ == '__main__':
    main()
