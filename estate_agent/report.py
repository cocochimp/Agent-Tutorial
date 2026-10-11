"""报告采用证据绑定的结构化字段，不信任模型随手输出的数字。"""
from .business import DemoError, analyze_funnel
from .sql_tools import calculate_metrics, METRICS


# 用已有工具事实生成结构化报告。来源 ID 随事实保留，以便后续复核与引用。
def build_report(state):
    task, results = state["task"], state["results"]
    rag = results.get("retrieve_knowledge", {})
    report = {"title": "房产经营分析复盘 · 教学数据", "period": f'{task["start"]} 至 {task["end"]}',
              "baseline": f'{task["baseline_start"]} 至 {task["baseline_end"]}',
              "knowledge": rag.get("evidence", []), "facts": [], "signals": [],
              "limitations": ["数据与制度全部虚构，不代表贝壳真实业务。", "汇总数据反映同期变化，不能单独证明因果。"]}
    report["metric_label"] = METRICS[task["metric"]][2]
    if task["intent"] == "analysis":
        query = results.get("query_metrics")
        if not query:
            raise DemoError("MISSING_EVIDENCE", "缺少SQL结果，不能生成经营复盘。")
        report["facts"] = [{"evidence_id": query["evidence_id"], "store_id": r["store_id"], "name": r["name"],
                            "current_rate": r["current_rate"], "previous_rate": r["previous_rate"],
                            "delta_pp": r["delta_pp"], "relative_change": r["relative_change"]} for r in query["rows"]]
        worst = query["rows"][0]
        declined = worst["delta_pp"] is not None and worst["delta_pp"] < 0
        report["focus_store"] = worst["name"] if declined else None
        if declined:
            analysis = results.get("analyze_funnel")
            if not analysis or analysis["store_id"] != worst["store_id"]:
                raise DemoError("MISSING_EVIDENCE", "下降最大的门店尚未完成漏斗分析。")
            report["signals"] = [{**s, "evidence_id": analysis["evidence_id"]} for s in analysis["signals"]]
        report["summary"] = (f'{worst["name"]}的{report["metric_label"]}下降最多，优先核查该店的带看及跟进记录。'
                             if declined else f'本次完整可比数据未发现{report["metric_label"]}下降的门店。')
    else:
        report["summary"] = "以下为检索到的演示指标口径与制度原文。"
    if not report["knowledge"]:
        report["limitations"].append("未找到适用制度证据，仅提供已验证的数据事实，不编造处置要求。")
    return report


# 校验器从原始聚合值重新计算，且重新读取授权文档比较引用内容。
# 这样即使草稿和中间引用一起被篡改，也不能仅靠二者相等而通过。
def verify_report(report, state):
    """独立检查数字/对象/引用内容；测试会故意篡改它们来证明能拦截。"""
    expected = build_report(state)
    for key in ("facts", "signals", "knowledge", "period", "baseline", "summary", "focus_store", "limitations", "metric_label"):
        if report.get(key) != expected.get(key):
            raise DemoError("VERIFICATION_FAILED", f"报告字段{key}与工具证据不一致。")
    query = state["results"].get("query_metrics")
    if query and calculate_metrics(query)["rows"] != query["rows"]:
        raise DemoError("VERIFICATION_FAILED", "指标结果与原始SQL聚合值不一致。")
    analysis = state["results"].get("analyze_funnel")
    if analysis and query:
        recalculated = analyze_funnel(query, analysis["store_id"])
        if recalculated != analysis:
            raise DemoError("VERIFICATION_FAILED", "漏斗计算与SQL明细不一致。")
    from .retrieval import allowed_documents
    from .business import Identity
    from .data import read_documents
    canonical = {d["id"]: d for d in allowed_documents(read_documents(), state["task"]["region"], Identity(**state["user"]))}
    for doc in report["knowledge"]:
        source = canonical.get(doc["id"])
        if not source or any(doc.get(k) != v for k, v in source.items()):
            raise DemoError("VERIFICATION_FAILED", "引用与当前授权有效原文不一致。")
    return {"passed": True, "checks": ["数字与工具字段一致", "时间窗口一致", "引用ID及原文一致", "漏斗计算复核"],
            "scope": "验证模板内的结构化字段；不是通用自然语言事实核查器。"}


def percent(value):
    return "不可计算（分母为0）" if value is None else f"{value*100:.2f}%"


def markdown_report(report):
    lines = ["# "+report["title"], "", report["summary"], "",
             f'指标：{report["metric_label"]}；本期：{report["period"]}；比较基线：{report["baseline"]}。', ""]
    if report["facts"]:
        lines += ["| 门店 | 基线指标值 | 本期指标值 | 变化（百分点） | 相对变化 |", "|---|---:|---:|---:|---:|"]
        for row in report["facts"]:
            delta = "不可计算" if row["delta_pp"] is None else f'{row["delta_pp"]:+.2f}'
            lines.append(f'| {row["name"]} | {percent(row["previous_rate"])} | {percent(row["current_rate"])} | {delta} | {percent(row["relative_change"])} |')
        lines += ["", "数据依据：[SQL-01]，按指标口径先汇总分子分母，再求比例。", ""]
    for signal in report["signals"]:
        lines.append(f'- {signal["label"]}：{percent(signal["previous_rate"])} → {percent(signal["current_rate"])} [CALC-01]')
    lines += ["", "## 跟进参考 / 制度证据", ""]
    for doc in report["knowledge"]:
        lines += [f'### [{doc["id"]}] {doc["title"]} · {doc["section"]}', doc["text"], ""]
    narrative = report.get("narrative", {})
    hypotheses = {"followup_gap": "核查跟进遗漏与任务分配；同期下降不能证明因果。", "viewing_match": "抽查客户需求与房源匹配；需要明细证据验证。", "recording_delay": "复核成交录入延迟与口径；属于待排查因素，尚未证实。"}
    lines += ["## 证据选择与待核查假设", "", "重点建议依据："+"、".join(narrative.get("recommendation_ids", []))]
    lines += ["- "+hypotheses[h]+" [CALC-01]" for h in narrative.get("hypothesis_ids", [])]
    lines += ["## 结论边界", ""] + ["- "+x for x in report["limitations"]]
    return "\n".join(lines)
