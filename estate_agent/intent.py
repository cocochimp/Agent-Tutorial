"""统一时间归一化、LLM结构化理解、多轮指代与服务端权限校验。"""
import calendar
import re
from datetime import date, timedelta
from pydantic import ValidationError
from .business import DemoError, USER
from .contracts import Intent, TaskSpec
from .data import AS_OF, STORES


# 将候选意图转成可执行的任务：统一指标、地区、绝对时间和比较基线。
# 此处的 user 来自服务端登录；自然语言和模型输出都没有权力扩展访问范围。
def normalize(value, question, user=USER):
    intent = Intent.model_validate(value)
    if intent.region not in user.regions:
        raise DemoError("PERMISSION_DENIED", "当前登录账号无权访问该区域。")
    if intent.store_id:
        stores = {s[0]: s for s in STORES}
        if intent.store_id not in stores or stores[intent.store_id][2] != intent.region:
            raise DemoError("INVALID_ARGUMENT", "门店和区域不匹配。")
    if intent.end >= AS_OF:
        raise DemoError("INVALID_ARGUMENT", "演示数据库只到2026-09-27，请使用已结束的日期。")
    if intent.action != "none" and user.role == "viewer":
        raise DemoError("PERMISSION_DENIED", "只读观察员无权创建工单或发布报告。")
    days = (intent.end-intent.start).days+1
    if intent.compare == "previous":
        bs, be = intent.start-timedelta(days=days), intent.start-timedelta(days=1)
    else:
        def previous_year(d):
            return d.replace(year=d.year-1, day=min(d.day, calendar.monthrange(d.year-1, d.month)[1]))
        bs, be = previous_year(intent.start), previous_year(intent.end)
    if bs < date(2025, 8, 1):
        raise DemoError("EMPTY_RESULT", "比较基线超出演示数据范围（2025-08-01起）。")
    return TaskSpec(**intent.model_dump(), days=days, baseline_start=bs, baseline_end=be,
                    question=question, clock=AS_OF).model_dump(mode="json")


# 无模型时使用有限规则提取意图。它适合观察工程流程，并不等价于通用语言理解。
# 当问题出现“它”时尝试读取本会话 focus；没有上下文就要求澄清。
def rule_intent(question, context=None, user=USER):
    if not isinstance(question, str) or not question.strip() or len(question) > 2000:
        raise DemoError("INVALID_ARGUMENT", "请输入1~2000字的问题。")
    if any(w in question for w in ("删除数据库", "修改数据库", "DROP TABLE", "删库")):
        raise DemoError("PERMISSION_DENIED", "经营数据库仅允许只读查询。")
    if any(w in question for w in ("能耗", "客单价", "收入", "成本")):
        raise DemoError("UNSUPPORTED_METRIC", "本房产业务数据不包含能耗、成本或收入，不能编造指标。")
    context = context or {"focus": {}}
    focus = context.get("focus", {})
    references = any(w in question for w in ("它", "这家店", "刚才", "那家", "也这样"))
    if references and not focus.get("store_id"):
        raise DemoError("NEED_CLARIFICATION", "当前会话还没有门店对象，请先查询门店或写出门店名。")
    region = "海淀" if "海淀" in question else "朝阳" if "朝阳" in question else focus.get("region", user.regions[0])
    store_id = focus.get("store_id") if references else None
    for sid, name, reg in STORES:
        if name in question:
            store_id, region = sid, reg
    metric = focus.get("metric", "viewing_to_deal") if references else "viewing_to_deal"
    if "有效带看" in question and "转成交" not in question:
        metric = "effective_viewing_rate"
    elif any(w in question for w in ("跟进率", "回访率")) and "转成交" not in question:
        metric = "followup_rate"
    knowledge = any(w in question for w in ("怎么算", "定义", "口径", "是什么", "如何计算"))
    knowledge |= any(w in question for w in ("规范", "制度")) and not any(w in question for w in ("最近", "下降", "分析", "门店"))
    if "转化率" in question and "带看" not in question and not references and not knowledge:
        raise DemoError("NEED_CLARIFICATION", "请确认：带看转成交率、有效带看占比，还是24小时跟进率？")
    end = AS_OF-timedelta(days=1)
    start = end-timedelta(days=6)
    matches = re.findall(r"\d{4}-\d{2}-\d{2}", question)
    if matches:
        if len(matches) > 2:
            raise DemoError("NEED_CLARIFICATION", "请只提供本期起止两个日期，比较基线会自动生成。")
        start, end = date.fromisoformat(matches[0]), date.fromisoformat(matches[-1])
    elif "上个月" in question:
        end = AS_OF.replace(day=1)-timedelta(days=1)
        start = end.replace(day=1)
    elif "本月" in question:
        start = AS_OF.replace(day=1)
    elif "昨天" in question:
        start = end
    elif "上周" in question:
        end = AS_OF-timedelta(days=AS_OF.weekday()+1)
        start = end-timedelta(days=6)
    elif match := re.search(r"(?:最近|近|过去)\s*(\d+)\s*天", question):
        days = int(match[1])
        if not 1 <= days <= 91:
            raise DemoError("INVALID_ARGUMENT", "日期窗口支持1~91天。")
        start = end-timedelta(days=days-1)
    action = "create_ticket" if "工单" in question else "publish_report" if any(w in question for w in ("发通知", "发送报告", "发布报告")) else "none"
    return {"intent": "knowledge" if knowledge else "analysis", "region": region, "metric": metric,
            "start": start.isoformat(), "end": end.isoformat(), "compare": "yoy" if "同比" in question else "previous",
            "store_id": store_id, "action": action, "confidence": 1.0, "clarification": ""}


# 模型模式与规则模式在同一个入口汇合，最后都必须通过 normalize。
# 因此能解析出 JSON 只是第一步，字段、日期与权限仍需要确定性校验。
def understand(question, context=None, user=USER, client=None):
    if client:
        # 权限字段不属于模型输出Schema；日期与区域仍要经过normalize硬校验。
        value = client.structured("理解房产经营问题。按Schema输出JSON，不回答问题。时钟2026-09-28，数据到09-27。"
                                  "转化率歧义时confidence设为0.3并提出clarification。只识别用户明确要求的工单或发布动作。"
                                  "默认地区为登录用户首个区域。门店映射："+str(STORES),
                                  {"question": question, "context": context, "allowed_regions": list(user.regions)}, Intent.model_json_schema())
    else:
        try:
            value = rule_intent(question, context, user)
        except ValueError as exc:
            raise DemoError("INVALID_ARGUMENT", "日期格式或范围无效。") from exc
    try:
        task = normalize(value, question, user)
    except ValidationError as exc:
        raise DemoError("INVALID_ARGUMENT", "任务参数未通过Schema验证，请检查日期、地区和指标。") from exc
    if task["confidence"] < .65 or task["clarification"]:
        raise DemoError("NEED_CLARIFICATION", task["clarification"] or "请明确地区、指标与时间范围。")
    return task
