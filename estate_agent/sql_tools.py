"""Schema Retrieval → Pydantic查询计划 → SQL AST → 只读/行级隔离执行。"""
import sqlite3
import time
from datetime import date
import sqlglot
from sqlglot import exp
from .business import DemoError, USER
from .contracts import SQLPlan
from .data import DB

FIELDS = {"stores": {"store_id", "name", "region"}, "daily_metrics": {
    "day", "store_id", "leads", "viewings", "effective_viewings", "followups_24h", "deals"}}
# 每个指标明确规定分子、分母和显示名称，避免模型临时改变统计口径。
METRICS = {"viewing_to_deal": ("deals", "viewings", "带看转成交率"),
           "effective_viewing_rate": ("effective_viewings", "viewings", "有效带看占比"),
           "followup_rate": ("followups_24h", "viewings", "24小时跟进率")}


def retrieve_schema(metric):
    if metric not in METRICS:
        raise DemoError("UNSUPPORTED_METRIC", "未知指标。")
    numerator, denominator, label = METRICS[metric]
    return {"evidence_id": "SCHEMA-01", "tables": {k: sorted(v) for k, v in FIELDS.items()},
            "join": "daily_metrics.store_id = stores.store_id", "metric": metric,
            "definition": f"{label}=SUM({numerator})/SUM({denominator})；比较百分比差使用百分点；分母零返回null。",
            "plan_schema": SQLPlan.model_json_schema()}


# AST 检查针对 SQL 的结构，而不是简单搜索 DELETE 等关键词。
# 仅允许一个 SELECT，并逐项检查表、字段、函数、JOIN 和行数上限。
def guard_sql(sql):
    try:
        expressions = sqlglot.parse(sql, read="sqlite")
    except sqlglot.errors.ParseError as exc:
        raise DemoError("UNSAFE_SQL", "SQL解析失败。") from exc
    if len(expressions) != 1 or not isinstance(expressions[0], exp.Select):
        raise DemoError("UNSAFE_SQL", "只允许单条SELECT。")
    tree = expressions[0]
    if any(tree.find(t) for t in (exp.Subquery, exp.CTE, exp.Union, exp.Command, exp.Into)):
        raise DemoError("UNSAFE_SQL", "不开放子查询、CTE、UNION或写入语法。")
    tables = list(tree.find_all(exp.Table))
    if not tables or len(tables) > 2:
        raise DemoError("UNSAFE_SQL", "查询必须访问白名单表，且最多连接两张表。")
    aliases = {}
    for table in tables:
        if table.name not in FIELDS or table.db or table.catalog:
            raise DemoError("UNSAFE_SQL", "表名或数据库限定符不在白名单。")
        aliases[table.alias_or_name] = table.name
    output_aliases = {alias.alias for alias in tree.find_all(exp.Alias)}
    for col in tree.find_all(exp.Column):
        valid = FIELDS.get(aliases.get(col.table, ""), set()) if col.table else set().union(*FIELDS.values()) | output_aliases
        if col.name not in valid:
            raise DemoError("UNSAFE_SQL", "查询字段不在白名单。")
    for func in tree.find_all(exp.Func):
        if func.sql_name() not in {"SUM", "COUNT", "AVG", "MAX", "MIN", "COALESCE", "NULLIF", "ROUND", "CASE", "IF", "AND", "OR"}:
            raise DemoError("UNSAFE_SQL", "SQL函数不在白名单。")
    for star in tree.find_all(exp.Star):
        if not isinstance(star.parent, exp.Count):
            raise DemoError("UNSAFE_SQL", "禁止SELECT *，请明确字段。")
    if any(join.args.get("kind") == "CROSS" or not join.args.get("on") for join in tree.find_all(exp.Join)):
        raise DemoError("UNSAFE_SQL", "连接必须有ON条件。")
    limit = tree.args.get("limit")
    if limit is not None:
        try:
            if not isinstance(limit.expression, exp.Literal) or int(limit.expression.name) < 0:
                raise ValueError()
        except (TypeError, ValueError):
            raise DemoError("UNSAFE_SQL", "LIMIT必须是非负常量。")
    tree = tree.limit(min(int(limit.expression.name), 100) if limit is not None else 100)
    return tree.sql(dialect="sqlite")


def execute_readonly(sql, parameters, user=USER, db=DB):
    safe = guard_sql(sql)
    con = sqlite3.connect(db.resolve().as_uri()+"?mode=ro", uri=True, timeout=2)
    try:
        con.row_factory = sqlite3.Row
        # 在读取连接内建立行级视图：即使SELECT没有WHERE也无法越区。
        quoted = ",".join("'"+region.replace("'", "''")+"'" for region in user.regions)
        con.execute(f"CREATE TEMP VIEW stores AS SELECT * FROM main.stores WHERE region IN ({quoted})")
        con.execute(f"CREATE TEMP VIEW daily_metrics AS SELECT d.* FROM main.daily_metrics d JOIN main.stores s ON d.store_id=s.store_id WHERE s.region IN ({quoted})")
        con.execute("PRAGMA query_only=ON")
        def authorize(action, table, column, database, trigger):
            if action == sqlite3.SQLITE_READ:
                return sqlite3.SQLITE_OK if table in FIELDS and (column in FIELDS[table] or column == "") else sqlite3.SQLITE_DENY
            return sqlite3.SQLITE_OK if action in (sqlite3.SQLITE_SELECT, sqlite3.SQLITE_FUNCTION) else sqlite3.SQLITE_DENY
        # AST 是第一层，SQLite authorizer 是执行层的第二次检查。
        # progress_handler 按虚拟机指令周期检查超时，阻止超长查询。
        con.set_authorizer(authorize)
        deadline = time.monotonic()+2
        con.set_progress_handler(lambda: int(time.monotonic()>deadline), 500)
        rows = [dict(row) for row in con.execute(safe, parameters).fetchmany(100)]
    except sqlite3.OperationalError as exc:
        raise DemoError("SQL_TIMEOUT" if "interrupted" in str(exc) else "SQL_ERROR", "查询超时或执行失败。") from exc
    finally:
        con.close()
    return safe, rows


# task 已经过意图与权限校验；plan 还需验证指标和表与任务一致。
# 查询值用命名参数绑定，不将用户输入直接拼接到 SQL 文本。
def query_metrics(task, user=USER, db=DB, plan=None):
    if task["region"] not in user.regions:
        raise DemoError("PERMISSION_DENIED", "查询区域越权。")
    parsed = SQLPlan.model_validate(plan or {"metric": task["metric"]})
    if parsed.metric != task["metric"] or set(parsed.tables) != set(FIELDS):
        raise DemoError("INVALID_ARGUMENT", "查询计划与任务指标或Schema不一致。")
    sql = '''SELECT s.store_id, s.name, s.region,
      CASE WHEN d.day >= :start THEN 'current' ELSE 'previous' END AS period,
      COUNT(*) AS observed_days, SUM(d.leads) AS leads, SUM(d.viewings) AS viewings,
      SUM(d.effective_viewings) AS effective_viewings, SUM(d.followups_24h) AS followups_24h, SUM(d.deals) AS deals
      FROM daily_metrics AS d JOIN stores AS s ON s.store_id=d.store_id
      WHERE s.region=:region AND ((d.day BETWEEN :start AND :end) OR (d.day BETWEEN :baseline_start AND :baseline_end))'''
    if task.get("store_id"):
        sql += " AND s.store_id=:store_id"
    sql += " GROUP BY s.store_id,s.name,s.region,period ORDER BY s.store_id,period LIMIT 100"
    safe, rows = execute_readonly(sql, task, user, db)
    if not rows:
        raise DemoError("EMPTY_RESULT", "指定范围没有数据，不能推断经营原因。")
    return {"evidence_id": "SQL-01", "sql": safe, "plan": parsed.model_dump(), "raw_rows": rows,
            "parameters": {key: task.get(key) for key in ("region", "start", "end", "baseline_start", "baseline_end", "store_id")},
            "source": "SQLite只读行级视图 / 虚构日数据", "task": task}


# 输入是按门店/时期聚合的原始计数，输出 rows 按指标下降幅度排序。
# 比例使用 SUM(分子)/SUM(分母)，而不是把每日比例直接求平均。
def calculate_metrics(raw):
    task = raw["task"]
    groups = {}
    for row in raw["raw_rows"]:
        groups.setdefault(row["store_id"], {})[row["period"]] = row
    result = []
    numerator, denominator, label = METRICS[task["metric"]]
    expected_previous = (date.fromisoformat(task["baseline_end"])-date.fromisoformat(task["baseline_start"])).days+1
    for sid, periods in groups.items():
        if set(periods) != {"current", "previous"} or periods["current"]["observed_days"] != task["days"] or periods["previous"]["observed_days"] != expected_previous:
            raise DemoError("INCOMPLETE_DATA", "本期或基线日记录不完整，停止比较。")
        c, p = periods["current"], periods["previous"]
        # 分母为零不能返回 0%：0% 表示可计算但没有转化，None 表示无法计算。
        # delta_pp 是百分点差；relative_change 是相对基线的变化比例。
        cr, pr = c[numerator]/c[denominator] if c[denominator] else None, p[numerator]/p[denominator] if p[denominator] else None
        result.append({"store_id": sid, "name": c["name"], "current": c, "previous": p, "current_rate": cr, "previous_rate": pr,
                       "delta_pp": (cr-pr)*100 if cr is not None and pr is not None else None,
                       "relative_change": cr/pr-1 if cr is not None and pr else None})
    if not any(r["delta_pp"] is not None for r in result):
        raise DemoError("NO_COMPARABLE_DATA", "分母为零，没有可比较的指标。")
    result.sort(key=lambda row: (row["delta_pp"] is None, row["delta_pp"] or 0))
    return {**raw, "rows": result, "metric_label": label, "calculation_evidence_id": "METRIC-CALC-01"}
