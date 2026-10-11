"""LangGraph运行时。重点阅读build_graph内add_node/add_conditional_edges/compile。"""
import json
import time
import uuid
from dataclasses import asdict
from pathlib import Path
from jsonschema import validate as validate_json
from jsonschema.exceptions import ValidationError as JSONValidationError
from pydantic import ValidationError
from langgraph.graph import StateGraph, START, END
from langgraph.types import Command, interrupt
from langgraph.checkpoint.sqlite import SqliteSaver
from .business import DemoError, Identity, USER, analyze_funnel
from .contracts import SQLPlan, Narrative
from .data import ROOT, initialize
from .intent import understand
from .llm import ModelClient, SYSTEM, TOOLS, PROMPT_VERSION
from .retrieval import search_knowledge
from .report import build_report, verify_report, markdown_report
from .settings import settings
from .sql_tools import retrieve_schema, query_metrics, calculate_metrics
from .state import AgentState
from .storage import Store, STATE_DIR

RUNS = ROOT / "runs"
TOOL_NODES = {"retrieve_schema": "schema_retrieval", "query_metrics": "query_sql", "calculate_metrics": "calculate",
              "analyze_funnel": "analyze", "retrieve_knowledge": "rag_search", "generate_report": "generate_report"}


# Trace 记录可审计的输入、输出、耗时与错误，不记录模型的内部思维。
# 每次返回新列表，避免修改上一个检查点持有的对象。
def trace(state, node, inputs, output, started, reason="", status="ok"):
    return state.get("trace", []) + [{"step": node, "input": inputs, "output": output, "reason": reason,
                                      "status": status, "latency_ms": round((time.perf_counter()-started)*1000, 2)}]


# 规则模式是一个可预测的决策器：先补齐查数与计算，再根据实际下降情况选择漏斗分析。
# 工具执行逻辑与模型模式共用，只有“下一步选什么”的来源不同。
def offline_action(state):
    results, task = state["results"], state["task"]
    if task["intent"] == "analysis":
        for name in ("retrieve_schema", "query_metrics", "calculate_metrics"):
            if name not in results:
                return {"name": name, "arguments": {}}
        worst = results["query_metrics"]["rows"][0]
        if worst["delta_pp"] is not None and worst["delta_pp"] < 0 and "analyze_funnel" not in results:
            return {"name": "analyze_funnel", "arguments": {"store_id": worst["store_id"]}}
    if "retrieve_knowledge" not in results:
        return {"name": "retrieve_knowledge", "arguments": {"query": task["question"][:400] if task["intent"] == "knowledge" else "带看转成交率下降 有效带看 24小时跟进 核查规范"}}
    return {"name": "generate_report", "arguments": {}}


def context_messages(state):
    """仅装配结构化摘要和当前证据，避免无限增长的原始工具聊天记录。"""
    # 模型只需看到可用于下一步决策的信息。原始 SQL 明细仍保留在 State/Trace 中，
    # 此处压缩送入上下文的内容，以免工具结果越积越多。
    observations = {}
    for name, result in state["results"].items():
        if name == "query_metrics":
            observations[name] = {"evidence_id": result["evidence_id"], "rows": result.get("rows", []), "row_count": len(result.get("raw_rows", []))}
        elif name == "retrieve_knowledge":
            observations[name] = {"evidence": [{"id": d["id"], "title": d["title"], "text": d["text"]} for d in result["evidence"]]}
        elif name == "retrieve_schema":
            observations[name] = {"definition": result["definition"], "tables": result["tables"]}
        else:
            observations[name] = result
    return [{"role": "system", "content": SYSTEM}, {"role": "user", "content": json.dumps({
        "task": state["task"], "context": state["context"], "observations": observations}, ensure_ascii=False)}] + (
        [{"role": "assistant", "content": None, "tool_calls": [state["last_observation"]["call"]]},
         {"role": "tool", "tool_call_id": state["last_observation"]["call"]["id"], "content": json.dumps(state["last_observation"]["result"], ensure_ascii=False)}]
        if state.get("last_observation", {}).get("call") else [])


def build_graph(checkpointer, store, client=None, cancel_check=None, strategy="single"):
    limits, started_run = settings(), time.monotonic()

    def identity(state):
        return Identity(**state["user"])

    def guard(state):
        if cancel_check and cancel_check():
            raise DemoError("CANCELLED", "任务已取消。")
        if time.monotonic()-started_run > limits["request_timeout_seconds"]:
            raise DemoError("TASK_TIMEOUT", "任务达到总时间预算；可检查Trace后重试。")

    def fail_update(state, exc, node):
        return {"status": "blocked", "next_node": "failed", "error": {"code": exc.code, "message": str(exc)},
                "trace": trace(state, node, {}, {"error_code": exc.code, "message": str(exc)}, time.perf_counter(), status="error")}

    # 第一个业务节点：读取会话 → 理解问题 → 日期/指标归一化 → 权限检查。
    # 返回字典是对 AgentState 的局部更新，不需要重建整份状态。
    def understand_node(state):
        started = time.perf_counter()
        try:
            guard(state)
            context = store.context(state["user"]["user_id"], state["session_id"])
            context["preferences"] = store.memories(state["user"]["user_id"])
            task = understand(state["question"], context, identity(state), client)
            return {"task": task, "context": context, "error": {}, "next_node": "agent_node", "risk_level": "high" if task["action"] != "none" else "low",
                    "model_stats": client.stats() if client else {},
                    "trace": trace(state, "understand", {"question": state["question"]}, task, started, "Pydantic验证、绝对日期归一化、权限硬校验")}
        except DemoError as exc:
            if exc.code == "NEED_CLARIFICATION" and state.get("clarify_count", 0) < 2:
                return {"error": {"code": exc.code, "message": str(exc)}, "next_node": "clarify"}
            return fail_update(state, exc, "understand")

    # interrupt 会把暂停状态交给检查点保存器。恢复后此节点从开头重新执行，
    # interrupt 表达式返回用户提供的回答，因此中断前不要安排不可重复的副作用。
    def clarify_node(state):
        answer = interrupt({"kind": "clarification", "question": state["error"]["message"]})
        if not isinstance(answer, str) or not answer.strip() or len(answer) > 1000:
            return fail_update(state, DemoError("INVALID_ARGUMENT", "澄清内容需为1~1000字。"), "clarify")
        return {"question": state["question"]+"\n用户补充："+answer, "clarify_count": state.get("clarify_count", 0)+1,
                "trace": trace(state, "clarify", {}, {"answer": answer}, time.perf_counter()), "error": {}}

    # ReAct 中的行动选择发生在这里：基于已有观察，只选择一个工具。
    # LangGraph 本身不会替模型决定业务策略，它按返回的 next_node 调度。
    def plan_node(state):
        started = time.perf_counter()
        try:
            guard(state)
            if state["tool_calls"] >= limits["max_tool_calls"]:
                raise DemoError("STEP_LIMIT", "达到工具调用上限。")
            if client:
                response = client.decide(context_messages(state))
                calls = response.get("tool_calls", [])
                if len(calls) != 1:
                    raise DemoError("MODEL_PROTOCOL_ERROR", "每轮必须只返回一个工具调用。")
                call = calls[0]
                action = {"name": call["function"]["name"], "arguments": json.loads(call["function"]["arguments"]), "call": call}
            else:
                action = offline_action(state)
            name = action["name"]
            if name not in TOOL_NODES:
                raise DemoError("INVALID_ARGUMENT", "模型请求了不存在的工具。")
            schema = next(t["function"]["parameters"] for t in TOOLS if t["function"]["name"] == name)
            validate_json(action["arguments"], schema)
            # 工具名与规范化参数一起作为调用签名。同一工具可以使用不同参数，
            # 但完全相同的调用会被拒绝，防止模型陷入重复执行循环。
            signature = json.dumps([name, action["arguments"]], sort_keys=True)
            if signature in state["seen"]:
                raise DemoError("REPEATED_CALL", "同一个工具及相同参数已经调用过，停止重复执行。")
            return {"action": action, "tool_calls": state["tool_calls"]+1, "seen": state["seen"]+[signature],
                    "next_node": TOOL_NODES[name], "model_stats": client.stats() if client else {},
                    "trace": trace(state, "agent_node", {}, action, started, "模型工具决策" if client else "教学规则决策")}
        except DemoError as exc:
            return fail_update(state, exc, "agent_node")
        except (ValueError, KeyError, JSONValidationError) as exc:
            return fail_update(state, DemoError("MODEL_PROTOCOL_ERROR", "模型工具参数格式错误。"), "agent_node")

    # 工具节点共用的分发器。读取 action.arguments，执行确定性的业务函数。
    # results 按工具名保存最新结果；Trace 则保留每一次调用及其先后顺序。
    def execute_tool(state, name):
        started = time.perf_counter()
        args, results, task = state["action"]["arguments"], dict(state["results"]), state["task"]
        try:
            guard(state)
            if name == "retrieve_schema":
                output = retrieve_schema(task["metric"])
            elif name == "query_metrics":
                if "retrieve_schema" not in results:
                    raise DemoError("INVALID_SEQUENCE", "请先检索Schema。")
                # 模型只能输出受 SQLPlan 约束的查询计划，不能直接提供任意 SQL。
                # 真正的 SQL 由 query_metrics 编译，并经过 AST 与只读执行层检查。
                plan = client.structured("按Task和Schema输出受约束SQL查询计划JSON。", {"task": task, "schema": results["retrieve_schema"]}, SQLPlan.model_json_schema()) if client else None
                output = query_metrics(task, identity(state), plan=plan)
            elif name == "calculate_metrics":
                if "query_metrics" not in results:
                    raise DemoError("INVALID_SEQUENCE", "请先查询数据。")
                calculated = calculate_metrics(results["query_metrics"])
                results["query_metrics"] = calculated
                output = {"evidence_id": "METRIC-CALC-01", "store_count": len(calculated["rows"]), "first": calculated["rows"][0]["store_id"]}
            elif name == "analyze_funnel":
                if "calculate_metrics" not in results:
                    raise DemoError("INVALID_SEQUENCE", "请先计算指标。")
                if args["store_id"] != results["query_metrics"]["rows"][0]["store_id"]:
                    raise DemoError("INVALID_ARGUMENT", "分析对象必须是当前排序中下降最多的门店。")
                output = analyze_funnel(results["query_metrics"], args["store_id"])
            elif name == "retrieve_knowledge":
                # RAG 的实际入口：检索词可以由模型决定，权限身份来自服务端 State。
                # 返回 evidence（引用原文）和 stages（检索过程），一起进入 Trace。
                output = search_knowledge(args["query"][:500], task["region"], identity(state), backend=state["backend"], client=client, graph=state["graph_rag"])
            else:
                raise DemoError("INVALID_ARGUMENT", "未知工具。")
            results[name] = output
            return {"results": results, "retry_count": 0, "error": {}, "next_node": "checkpoint_gate",
                    "last_observation": {"call": state["action"].get("call"), "result": {"status": "ok", "tool": name}},
                    "pending_pause": state.get("pause_after") == name and name not in state.get("paused_nodes", []),
                    "model_stats": client.stats() if client else {},
                    "trace": trace(state, TOOL_NODES[name], args, {"status": "ok", "data": output, "source": name, "error_code": None, "latency_ms": round((time.perf_counter()-started)*1000, 2)}, started)}
        except (DemoError, ValidationError) as exc:
            if isinstance(exc, ValidationError):
                exc = DemoError("INVALID_ARGUMENT", "查询计划未通过Schema验证。")
            output = {"status": "error", "error_code": exc.code, "message": str(exc), "data": None, "source": name, "latency_ms": round((time.perf_counter()-started)*1000, 2)}
            # 瞬时错误允许有限重试；参数或调用顺序错误可反馈给模型重新规划。
            # 不可恢复的业务错误进入 failed，不进行无限重试。
            retryable = exc.code in ("SQL_TIMEOUT", "MODEL_UNAVAILABLE", "MODEL_HTTP_ERROR") and state.get("retry_count", 0) < 2
            destination = "retry_node" if retryable else "agent_node" if client and exc.code in ("INVALID_SEQUENCE", "INVALID_ARGUMENT") else "failed"
            return {"error": {"code": exc.code, "message": str(exc)}, "next_node": destination,
                    "last_observation": {"call": state["action"].get("call"), "result": output},
                    "trace": trace(state, TOOL_NODES[name], args, output, started, status="error")}

    # 普通情况下直接返回规划节点。CLI 指定 pause_after 时在这里暂停，
    # 便于演示关闭进程后从已完成的工具之后继续。
    def checkpoint_gate(state):
        if state.get("pending_pause"):
            interrupt({"kind": "pause", "after": state["action"]["name"], "message": "检查点已保存，可关闭服务后恢复。"})
            return {"pending_pause": False, "paused_nodes": state.get("paused_nodes", [])+[state["action"]["name"]]}
        return {}

    def retry_node(state):
        time.sleep(.2*2**state.get("retry_count", 0))
        return {"retry_count": state.get("retry_count", 0)+1, "next_node": TOOL_NODES[state["action"]["name"]],
                "trace": trace(state, "retry_node", {}, {"attempt": state.get("retry_count", 0)+1}, time.perf_counter())}

    # 报告的数值与原文先由工具结果组成。模型只从候选 ID 中选择事实、建议、假设，
    # 不承担比例计算，也不能凭空提供新的数字和制度引用。
    def report_node(state):
        started = time.perf_counter()
        try:
            if "retrieve_knowledge" not in state["results"]:
                raise DemoError("MISSING_EVIDENCE", "缺少知识检索结果。")
            draft = build_report(state)
            if client:
                choices = {"fact_ids": ["SQL-01", "CALC-01"] if draft["facts"] else [],
                           "recommendation_ids": [d["id"] for d in draft["knowledge"]],
                           "hypothesis_ids": ["followup_gap", "viewing_match", "recording_delay"] if draft["signals"] else []}
                narrative = client.structured("选择有证据支持的事实、建议和待核查假设ID。不得选择候选之外的ID。confidence范围0~1。", {"report": draft, "choices": choices, "validation_feedback": state.get("error", {})}, Narrative.model_json_schema())
            else:
                narrative = {"fact_ids": ["SQL-01"] if draft["facts"] else [], "recommendation_ids": [d["id"] for d in draft["knowledge"]],
                             "hypothesis_ids": ["recording_delay"] if draft["signals"] else [], "confidence": .9 if draft["knowledge"] else .4}
            return {"draft": draft, "narrative": narrative, "next_node": "validate", "model_stats": client.stats() if client else {},
                    "trace": trace(state, "generate_report", {}, {"report": draft, "narrative": narrative}, started)}
        except DemoError as exc:
            return fail_update(state, exc, "generate_report")

    # 独立复算数字并核对引用。校验与生成分开，避免仅让生成模型自我确认。
    # 对模型选择错误最多反馈一次；失败不能被当作成功报告继续执行。
    def validate_node(state):
        try:
            guard(state)
            verification = verify_report(state["draft"], state)
            narrative = Narrative.model_validate(state["narrative"])
            valid_facts = {"SQL-01"} if state["draft"]["facts"] else set()
            if state["draft"]["signals"]:
                valid_facts.add("CALC-01")
            valid_docs = {d["id"] for d in state["draft"]["knowledge"]}
            if not set(narrative.fact_ids) <= valid_facts or not set(narrative.recommendation_ids) <= valid_docs:
                raise DemoError("VERIFICATION_FAILED", "模型引用了不存在的证据。")
            if narrative.hypothesis_ids and not state["draft"]["signals"]:
                raise DemoError("VERIFICATION_FAILED", "缺少漏斗证据，不能输出原因假设。")
            report = dict(state["draft"])
            report["narrative"] = narrative.model_dump()
            return {"report": report, "verification": verification, "markdown": markdown_report(report), "error": {},
                    "risk_level": "high" if state["task"]["action"] != "none" else "medium" if narrative.confidence < .65 else "low",
                    "next_node": "human_approval" if state["task"]["action"] != "none" or narrative.confidence < .65 else "finish",
                    "trace": trace(state, "validate", {}, verification, time.perf_counter())}
        except (DemoError, ValidationError) as exc:
            if isinstance(exc, ValidationError):
                exc = DemoError("VERIFICATION_FAILED", "报告选择未通过Schema校验。")
            if client and state.get("refinement_count", 0) < 1:
                return {"next_node": "generate_report", "refinement_count": 1,
                        "error": {"code": exc.code, "message": str(exc)},
                        "trace": trace(state, "validate", {}, {"passed": False, "feedback": str(exc)}, time.perf_counter(), status="error")}
            return fail_update(state, exc, "validate")

    # 人工审批是图中的暂停点。必须收到明确布尔值；缺失回答不等于批准。
    # 审批记录与执行动作分开，便于审计，也便于在执行端再次核验权限。
    def approval_node(state):
        decision = interrupt({"kind": "approval", "action": state["task"]["action"], "summary": state["report"]["summary"],
                              "message": "请检查报告和引用。批准后仅写入本地演示工单/通知收件箱；低置信报告仅确认查看。"})
        if not isinstance(decision, bool):
            return fail_update(state, DemoError("INVALID_ARGUMENT", "审批必须是true或false。"), "human_approval")
        store.audit(state["user"]["user_id"], "approval", {"run_id": state["run_id"], "approved": decision})
        return {"approval": decision, "next_node": "execute_action" if decision and state["task"]["action"] != "none" else "finish",
                "trace": trace(state, "human_approval", {}, {"approved": decision}, time.perf_counter())}

    # interrupt 恢复和进程重试可能重复到达此节点。Store.action 用唯一键幂等写入，
    # 确保同一个任务的同一业务动作不会创建多条本地记录。
    def execute_action(state):
        if not state.get("approval") or state["user"]["role"] == "viewer":
            return fail_update(state, DemoError("PERMISSION_DENIED", "审批未通过或无执行权限。"), "execute_action")
        output = store.action(state)
        return {"action_result": output, "trace": trace(state, "execute_action", {}, output, time.perf_counter())}

    def finish(state):
        store.remember_turn(state, limits["session_ttl_seconds"])
        return {"status": "completed", "trace": trace(state, "finish", {}, {"status": "completed"}, time.perf_counter())}

    def failed(state):
        return {"status": "cancelled" if state.get("error", {}).get("code") == "CANCELLED" else "blocked"}

    # ── 图的装配区：前面定义工作函数，这里注册节点和路由。──
    # AgentState 是各节点共享的状态契约；条件边只从允许的目标中选择。
    builder = StateGraph(AgentState)
    for name, node in {"understand": understand_node, "clarify": clarify_node, "agent_node": plan_node,
                       "checkpoint_gate": checkpoint_gate, "retry_node": retry_node, "generate_report": report_node,
                       "validate": validate_node, "human_approval": approval_node, "execute_action": execute_action,
                       "finish": finish, "failed": failed}.items():
        builder.add_node(name, node)
    for tool, node in TOOL_NODES.items():
        if tool != "generate_report":
            # 默认参数 tool=tool 固定当前循环的工具名，避免 Python 闭包延迟绑定
            # 导致所有节点都执行最后一个工具。
            builder.add_node(node, lambda state, tool=tool: execute_tool(state, tool))
            builder.add_conditional_edges(node, lambda s: s["next_node"], {x: x for x in ("checkpoint_gate", "retry_node", "agent_node", "failed")})
    builder.add_edge(START, "understand")
    builder.add_conditional_edges("understand", lambda s: s["next_node"], {x: x for x in ("agent_node", "clarify", "failed")})
    builder.add_conditional_edges("clarify", lambda s: "failed" if s.get("next_node") == "failed" else "understand", {"understand": "understand", "failed": "failed"})
    if strategy == "multi":
        # 三个专家各自是实际编译的StateGraph子图，检查点由父图继承。
        data_agent = StateGraph(AgentState)
        data_tools = {k: v for k, v in TOOL_NODES.items() if k in ("retrieve_schema", "query_metrics", "calculate_metrics", "analyze_funnel")}
        for tool, name in data_tools.items():
            data_agent.add_node(name, lambda state, tool=tool: execute_tool(state, tool))
            data_agent.add_edge(name, END)
        data_agent.add_conditional_edges(START, lambda s: s["next_node"], {n: n for n in data_tools.values()})
        knowledge_agent = StateGraph(AgentState)
        knowledge_agent.add_node("retrieve", lambda s: execute_tool(s, "retrieve_knowledge"))
        knowledge_agent.add_edge(START, "retrieve").add_edge("retrieve", END)
        report_agent = StateGraph(AgentState)
        report_agent.add_node("write", report_node)
        report_agent.add_edge(START, "write").add_edge("write", END)
        builder.add_node("data_agent", data_agent.compile())
        builder.add_node("knowledge_agent", knowledge_agent.compile())
        builder.add_node("report_agent", report_agent.compile())
        def supervisor_route(state):
            destination = state["next_node"]
            return "data_agent" if destination in data_tools.values() else "knowledge_agent" if destination == "rag_search" else "report_agent" if destination == "generate_report" else destination
        builder.add_conditional_edges("agent_node", supervisor_route, {n: n for n in ("data_agent", "knowledge_agent", "report_agent", "failed")})
        for name in ("data_agent", "knowledge_agent"):
            builder.add_conditional_edges(name, lambda s: s["next_node"], {n: n for n in ("checkpoint_gate", "retry_node", "agent_node", "failed")})
        builder.add_conditional_edges("report_agent", lambda s: s["next_node"], {"validate": "validate", "failed": "failed"})
    else:
        builder.add_conditional_edges("agent_node", lambda s: s["next_node"], {x: x for x in list(TOOL_NODES.values())+["failed"]})
    # 工具 → 检查点 → 规划，形成可控循环；报告校验完成后才离开循环。
    builder.add_edge("checkpoint_gate", "agent_node")
    builder.add_conditional_edges("retry_node", lambda s: s["next_node"], {x: x for x in TOOL_NODES.values()})
    builder.add_conditional_edges("generate_report", lambda s: s["next_node"], {"validate": "validate", "failed": "failed"})
    builder.add_conditional_edges("validate", lambda s: s["next_node"], {x: x for x in ("human_approval", "finish", "failed", "generate_report")})
    builder.add_conditional_edges("human_approval", lambda s: s["next_node"], {x: x for x in ("execute_action", "finish", "failed")})
    builder.add_edge("execute_action", "finish")
    builder.add_edge("finish", END)
    builder.add_edge("failed", END)
    # compile 将定义转换成可执行图；checkpointer 负责在运行过程中持久化状态。
    return builder.compile(checkpointer=checkpointer)


def run(question="", mode="offline", resume_id=None, resume_value=None, pause_after=None, directory=None,
        user=USER, session_id=None, backend=None, graph_rag=False, strategy="single", client=None, run_id=None, cancel_check=None):
    initialize()
    store = Store(directory or STATE_DIR)
    started = time.perf_counter()
    if resume_id:
        existing = store.get_task(resume_id, user.user_id)
        if not existing:
            raise DemoError("NOT_FOUND", "任务不存在或无访问权限。")
        if existing["status"] == "completed":
            return existing
        mode, run_id = existing["mode"], resume_id
    else:
        run_id = run_id or uuid.uuid4().hex[:12]
        existing = {"run_id": run_id, "session_id": session_id or uuid.uuid4().hex[:12], "user": asdict(user), "question": question,
                    "mode": mode, "strategy": strategy, "backend": backend or settings()["retrieval"]["backend"], "graph_rag": graph_rag,
                    "results": {}, "trace": [], "seen": [], "tool_calls": 0, "retry_count": 0, "status": "running",
                    "pause_after": pause_after or "", "paused_nodes": [], "model_stats": {}}
        store.put_task(existing)
    try:
        model = (client or ModelClient()) if mode == "llm" else None
        if model and resume_id and hasattr(model, "calls"):
            model.calls = existing.get("model_stats", {}).get("calls", 0)
            model.usage = existing.get("model_stats", {}).get("usage", [])
        # 应用数据库保存网页查询用的快照；checkpoints.sqlite3 保存 LangGraph 的运行位置。
        # 恢复必须复用同一个 thread_id，而不是另外生成任务 ID。
        with SqliteSaver.from_conn_string(str(store.directory/"checkpoints.sqlite3")) as saver:
            graph = build_graph(saver, store, model, cancel_check, existing.get("strategy", "single"))
            config = {"configurable": {"thread_id": run_id}, "recursion_limit": 100}
            if resume_id:
                snapshot = graph.get_state(config)
                waiting = any(t.interrupts for t in snapshot.tasks)
                if waiting and resume_value is None:
                    kinds = [i.value.get("kind") for t in snapshot.tasks for i in t.interrupts]
                    if any(k != "pause" for k in kinds):
                        # 缺少回答绝不能被当成批准；保留原来的中断状态。
                        return existing
                graph_input = Command(resume=resume_value if resume_value is not None else "continue") if waiting else None
                if not snapshot.values:
                    # 排队后、首个检查点之前退出：保留请求配置，安全开始执行。
                    graph_input = {**existing, "status": "running", "results": {}, "trace": [], "seen": [],
                                   "tool_calls": 0, "retry_count": 0, "paused_nodes": [], "model_stats": {},
                                   "strategy": existing.get("strategy", "single"), "backend": existing.get("backend", "bm25"),
                                   "graph_rag": existing.get("graph_rag", False)}
            else:
                graph_input = existing
            # values 模式每步给出合并后的完整状态。将其写入应用数据库，
            # HTTP/SSE 层随后读取这些快照并更新网页，不需要直接持有图对象。
            for update in graph.stream(graph_input, config, stream_mode="values"):
                value = {k: v for k, v in update.items() if k != "__interrupt__"}
                store.put_task(value)
            snapshot = graph.get_state(config)
            result = dict(snapshot.values)
            interrupted = [i.value for t in snapshot.tasks for i in t.interrupts]
            if interrupted:
                result["status"] = "waiting"
                result["interrupts"] = interrupted
    except DemoError as exc:
        result = store.get_task(run_id, user.user_id) or existing
        result.update(status="blocked", error={"code": exc.code, "message": str(exc)})
    except Exception as exc:
        result = store.get_task(run_id, user.user_id) or existing
        result.update(status="failed", error={"code": "RUNTIME_ERROR", "message": f"运行失败：{type(exc).__name__}。检查Trace和模型安装。"})
        # 对本地CLI保留诊断类型；不把可能含原始模型内容的异常写入网页。
        import traceback
        traceback.print_exc()
    result["latency_ms"] = round((time.perf_counter()-started)*1000, 2)
    store.put_task(result)
    if result.get("markdown"):
        exports = store.directory/"reports"
        exports.mkdir(exist_ok=True)
        (exports/(run_id+".md")).write_text(result["markdown"], encoding="utf-8")
    return result
