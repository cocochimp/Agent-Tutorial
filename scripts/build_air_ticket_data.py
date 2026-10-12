"""生成 web/projects/air-ticket/ 五件套：handbook、guide-data、work-items、graph、tutorial。

内容源：/Users/Doc/review/机票退改签-agent-实习复盘手册-v2.html（14 章节）。
结构与房产/拍照搜题项目完全一致（5 工作项 + hero + 9 章导读 + 执行图 + 教程代码）。
"""
import json
import re
from pathlib import Path

SRC = Path('/Users/Doc/review/机票退改签-agent-实习复盘手册-v2.html')
ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / 'web' / 'projects' / 'air-ticket'
INDEX = ROOT / 'web' / 'projects' / 'index.json'

h = SRC.read_text(encoding='utf-8')

def section(sid):
    m = re.search(r'<section[^>]*id="%s"[^>]*>(.*?)</section>' % sid, h, re.S)
    return m.group(1).strip() if m else ''

def text(html):
    t = re.sub(r'<script.*?</script>', '', html, flags=re.S)
    t = re.sub(r'<style.*?</style>', '', t, flags=re.S)
    t = re.sub(r'<[^>]+>', ' ', t)
    return re.sub(r'\s+', ' ', t).strip()

OUT.mkdir(parents=True, exist_ok=True)

# 1) handbook.html —— 手册原样副本
(OUT / 'handbook.html').write_text(h, encoding='utf-8')

# 2) guide-data.json —— hero + 9 章（除 5 工作项外）
GUIDE_CHAPTERS = [
    ('resume', '实习经历模板'),
    ('opening', '项目总览 & 30 秒开场'),
    ('architecture', '整体架构与检索漏斗'),
    ('rag', 'RAG 核心概念'),
    ('deepdive', '检索漏斗逐层拆解'),
    ('eval', '评测体系'),
    ('qa', '高频面试追问'),
    ('pitfalls', '答题易错点'),
    ('cheatsheet', '指标与术语速查'),
]
guide = {
    'version': '1.0',
    'hero': {
        'eyebrow': 'AI APPLICATION ENGINEERING · AGENT + RAG + TOOLS',
        'title': '机票退改签智能 Agent',
        'desc': '面向机票售后退改签咨询与办理场景，把一句口语化诉求转成可溯源、可校验的退改政策与真实差价，支持多轮追问与个性化话术。',
        'facts': [
            {'label': '业务', 'value': '机票售后 / 退改签 / 政策咨询 / 改签比价'},
            {'label': '岗位', 'value': 'AI 应用研发 / Agent 开发实习生'},
            {'label': '技术栈', 'value': 'RAG · Function Calling · LangGraph · Evals · Observability'},
        ],
    },
    'chapters': [{'id': cid, 'title': title, 'html': section(cid)} for cid, title in GUIDE_CHAPTERS],
}
(OUT / 'guide-data.json').write_text(json.dumps(guide, ensure_ascii=False, indent=2), encoding='utf-8')

# 3) work-items.json —— 5 工作项
def first_sentence(html, n=60):
    t = text(html)
    return t[:n] + ('…' if len(t) > n else '')

WORK_ITEMS = [
    {
        'id': 'work-1',
        'title': '工作一 · Agent 工具编排与流程规划',
        'short': '工具封装 / ReAct 多步规划 / LangGraph 状态机',
        'summary': '把查航班状态、算退改差价、规则库检索、方案生成、出票封装成统一工具，基于 ReAct 做多步推理与工具调度，用 LangGraph 编排「解析→检索→确认→生成→校验」状态机（含置信度阈值与 human-in-the-loop）。',
        'resume': {
            'label': 'Agent 工具编排与流程规划',
            'text': first_sentence(section('work1'), 200),
            'metrics': '工具调用准确率 ≥92% · ReAct 多步规划 · LangGraph 状态机 · 必经节点防跳步',
            'metricDetails': [
                {'title': '工具调用准确率 ≥92%', 'design': '把查航班状态、算退改差价、规则检索、方案生成、出票封装为 Function Calling 工具，入参出参用固定 Schema 约束；模型传错字段/漏参数即校验失败并触发错误重试。以「一次调用是否按 Schema 成功执行并返回有效结果」为判定口径。', 'source': '工具调用评测集（含正常、缺参数、类型错误、非法枚举四类用例）统计调用成功率；上线前基线约 78%，经 Schema 校验 + 重试后 ≥92%。'},
                {'title': 'ReAct 多步规划', 'design': '让模型「思考→行动→观察结果→再思考」循环，自主决定调用哪个工具、按什么顺序调；配合 LangGraph 状态机把「解析→检索→确认→生成→校验」串起来，规则检索设为必经节点防止跳过检索直接编政策。', 'source': '状态机在关键节点设置置信度阈值（0.85）与 human-in-the-loop；出票必须用户确认，低置信度转人工。'},
            ],
        },
        'nodes': ['user_input', 'agent_node', 'schema_validate', 'tool_flight_status', 'tool_rule_retrieve', 'tool_recalc_fee', 'verify_node', 'retry_node', 'checkpoint_gate', 'finish'],
        'io': [
            {'node': 'user_input', 'input': {'question': '帮我看下这票现在啥情况，能改到后天吗，补多少钱'}, 'output': {'order_id': 'ORD20260926001', 'intent': '改签-差价查询', 'raw': '口语诉求'}, 'note': '用户口语诉求 + 订单上下文'},
            {'node': 'agent_node', 'input': {'sub_queries': ['改签到后天的差价规则'], 'order': {'airline': 'MU', 'cabin': 'Y'}}, 'output': {'plan': ['tool_flight_status', 'tool_rule_retrieve', 'tool_recalc_fee'], 'confidence': 0.94}, 'note': 'ReAct 规划下一步调哪个工具'},
            {'node': 'tool_recalc_fee', 'input': {'order_id': 'ORD20260926001', 'target_date': '2026-09-28'}, 'output': {'change_fee': 580, 'fare_diff': 120, 'currency': 'CNY'}, 'note': '差价只能来自引擎工具，模型不许自己算'},
        ],
    },
    {
        'id': 'work-2',
        'title': '工作二 · 意图理解与 Query 改写',
        'short': '订单字段对齐 / 多诉求拆解 / 指代消解 / 结构化输出',
        'summary': '把口语诉求与订单结构化字段对齐，做一句话多诉求拆解、上下文改写与指代消解，必要时 HyDE 扩写、Step-back 政策泛化，输出 {意图/航司/舱位/票价产品} 结构化字段驱动下游 Filter 与精排加权。',
        'resume': {
            'label': '意图理解与 Query 改写',
            'text': first_sentence(section('work2'), 200),
            'metrics': '复杂场景解决率 +25% · 一句话多诉求拆解 · 指代消解 · 改写置信度兜底',
            'metricDetails': [
                {'title': '复杂场景解决率 +25%', 'design': '复杂场景定义为三类难例：口语改写（换说法描述同一诉求）、一句话多诉求（退+改同时问）、指代追问（「那退票呢」依赖上下文）。以「正确匹配到适用政策」为判定口径，对比有无 Query 理解的正确匹配率。', 'source': '从真实线上咨询抽取复杂难例构成评测集，标注每条的适用规则金标准；加入订单对齐、拆解、指代消解、结构化输出后提升 25%，普通场景无退化。'},
                {'title': '改写置信度兜底', 'design': 'Query 理解输出 rewrite_confidence，模型对改写结果打置信度（示例 0.91）；低于阈值时回退用原始 query 检索，避免「过度改写」导致语义漂移。', 'source': '线上 bad case（把 Y 舱扩写成头等舱）驱动设计；阈值在评测集上取「改写收益 > 改写风险」的经验值。'},
            ],
        },
        'nodes': ['user_input', 'order_align', 'query_understand', 'step_back', 'agent_node', 'checkpoint_gate'],
        'io': [
            {'node': 'order_align', 'input': {'raw': '这票太贵了我想退，要不你看看改签到明天划不划算'}, 'output': {'order': {'airline': 'MU', 'cabin': 'Y', 'fare_product': '特价舱', 'travel_date': '2026-09-26'}}, 'note': '订单字段对齐，补全「这票」指代'},
            {'node': 'query_understand', 'input': {'raw': '那退票呢，手续费多少'}, 'output': {'sub_queries': ['退票手续费规则'], 'intent': '退票-手续费', 'filters': {'airline': 'MU', 'cabin': 'Y'}, 'rewrite_confidence': 0.91}, 'note': '指代消解 + 结构化字段'},
        ],
    },
    {
        'id': 'work-3',
        'title': '工作三 · 混合检索与结果精排',
        'short': '双路召回 / RRF 融合 / Cross-Encoder 精排 / MMR 去重',
        'summary': '语义（向量）+ 关键词（BM25）双路各取 Top-60，RRF 融合去重取前 40，Cross-Encoder 精排取前 10（动态截断），MMR 去冗余取前 5，注入前 3；配合结构化 Filter 硬过滤。',
        'resume': {
            'label': '混合检索与结果精排',
            'text': first_sentence(section('work3'), 200),
            'metrics': '政策命中率 +18% · 60→40→10→5→3 漏斗 · 双路召回 + RRF + Cross-Encoder + MMR',
            'metricDetails': [
                {'title': '政策命中率 +18%', 'design': '以「适用规则是否进入最终注入生成的候选集合（前 3/前 5）」为判定口径——它直接决定生成能否引用到对的规则。', 'source': '带版本号评测集（v1.0，抽真实线上咨询 + 人工难例，标注金标准规则）；对比纯向量基线 vs 双路+融合+精排+去重完整漏斗，命中率提升 18%，Recall@K、nDCG@10 同步改善。'},
                {'title': '60→40→10→5→3 漏斗', 'design': '意图理解后双路并行召回各取 Top-60 → RRF（k=60）融合去重取 40 → Cross-Encoder 精排取 10（动态截断：分≥0.6、最多 10、至少 2）→ MMR（λ≈0.7）去冗余取 5 → 注入生成前 3。', 'source': '每层参数在评测集上扫「效果/延迟/成本」曲线：60 为召回收益拐点，0.6/0.7 为相关性门槛与多样性权重拐点，均写进复盘手册可复现。'},
            ],
        },
        'nodes': ['agent_node', 'tool_rule_retrieve', 'tool_rerank', 'mmr_filter', 'rag_search', 'checkpoint_gate'],
        'io': [
            {'node': 'tool_rule_retrieve', 'input': {'query': 'Y 舱特价票改签到后天的手续费规则'}, 'output': {'recall_top60': 60, 'fused_top40': 40, 'hits': ['RULE-10023', 'RULE-10024']}, 'note': '双路召回 + RRF 融合'},
            {'node': 'tool_rerank', 'input': {'candidates': 40}, 'output': {'top10': ['RULE-10023'], 'scores': [0.87]}, 'note': 'Cross-Encoder 精排，分≥0.6 动态截断'},
            {'node': 'mmr_filter', 'input': {'top10': ['RULE-10023']}, 'output': {'top5': ['RULE-10023'], 'top3_inject': ['RULE-10023']}, 'note': 'MMR 去冗余后注入前 3'},
        ],
    },
    {
        'id': 'work-4',
        'title': '工作四 · 方案生成、幻觉治理与质量把关',
        'short': '唯一数据源 / 金额校验 / Fact-Checker / Self-Refinement',
        'summary': '作答只能引用检索政策与工具差价（唯一数据源），结构化输出 + 金额逐项比对，Fact-Checker 打置信度（阈值 0.85），低置信度触发自我修正重试，仍不过关转人工，绝不硬输出。',
        'resume': {
            'label': '方案生成、幻觉治理与质量把关',
            'text': first_sentence(section('work4'), 200),
            'metrics': '方案正确率 96% · 置信阈值 0.85 · 金额后验 + Fact-Checker + Self-Refinement',
            'metricDetails': [
                {'title': '方案正确率 96%', 'design': '以「最终返回方案是否正确」为口径：政策引用准确（引用的是适用规则）+ 金额正确（与引擎一致）+ 结构化完整（字段齐全）。', 'source': '带金标准端到端评测集（v1.0）人工判定正确率；金额类、编造类错误由唯一数据源约束 + 代码后验 + Fact-Checker 拦截后基本清零。'},
                {'title': '置信阈值 0.85', 'design': '对生成结果打置信度（金额比对、事实核查、Schema 校验的综合），低于 0.85 触发 Self-Refinement 重写，仍不过关转人工，绝不硬输出。', 'source': '在评测集上扫描 0.5~0.95 阈值，画「漏放错误 vs 误拦正确」PR 曲线，0.85 为几乎不漏放硬伤、又不过度误拦的拐点。'},
            ],
        },
        'nodes': ['tool_scheme_gen', 'verify_node', 'retry_node', 'human_review', 'finish'],
        'io': [
            {'node': 'tool_scheme_gen', 'input': {'policy': 'RULE-10023', 'fee': {'change_fee': 580}}, 'output': {'scheme': {'refundable': False, 'changeable': True, 'change_fee': 580, 'policy_ref': 'RULE-10023'}}, 'note': '结构化输出，金额模板回填'},
            {'node': 'verify_node', 'input': {'scheme': {'change_fee': 580}, 'quote_in_text': 200}, 'output': {'quote_mismatch': True, 'unsupported_claim': True, 'confidence': 0.62}, 'note': '金额后验 + 事实核查，置信度低于 0.85 拦截'},
            {'node': 'human_review', 'input': {'confidence': 0.62, 'reason': ['quote_mismatch', 'unsupported_claim']}, 'output': {'review': '人工确认后返回'}, 'note': '低置信度转人工兜底'},
        ],
    },
    {
        'id': 'work-5',
        'title': '工作五 · 上下文与记忆系统设计',
        'short': '短期会话栈 / 长期用户画像 / 上下文预算',
        'summary': '短期记忆维护当前订单栈与咨询进度（会话级，Redis 缓存）；长期记忆维护常旅客画像（常走航线/退改偏好/价格敏感度），去重写入；上下文按优先级预算注入，画像按需检索作个性化 boost。',
        'resume': {
            'label': '上下文与记忆系统设计',
            'text': first_sentence(section('memory'), 200),
            'metrics': '多轮追问理解 +30% · 会话 Token 成本 −70% · 三层记忆 + 预算管理',
            'metricDetails': [
                {'title': '多轮追问理解 +30%', 'design': '以「多轮追问能否正确绑定订单/回溯方案」为口径：会话状态维护当前订单栈 + 咨询进度，配合滑动窗口 + 摘要压缩；指代消解（工作二）直接复用订单栈数据。', 'source': '多轮评测集对比「有会话状态/记忆」 vs 「无状态」的正确理解率；线上长对话回溯准确率同步提升。'},
                {'title': '会话 Token 成本 −70%', 'design': '滑动窗口只保留最近几轮原文、旧内容压成摘要常驻；画像按当前订单/航线检索最相关几条再注入（画像也当一路召回）；检索结果按预算只注入前 3。', 'source': '线上长对话 token 计量对比：信息等价、体积更小，省 token 不省信息量；方案正确率 96% 不降反稳。'},
            ],
        },
        'nodes': ['user_input', 'memory_node', 'query_understand', 'agent_node', 'checkpoint_gate'],
        'io': [
            {'node': 'memory_node', 'input': {'round': 3, 'order_stack': ['ORD20260926001']}, 'output': {'short_term': {'current_order': 'ORD20260926001', 'progress': '差价询问'}}, 'note': '短期记忆：当前订单栈 + 咨询进度'},
            {'node': 'memory_node', 'input': {'user_id': 'U-7788', 'route': '上海-北京'}, 'output': {'profile': {'frequent_route': 'SHA-PEK', 'price_sensitive': 0.8, 'prefer': '比价'}}, 'note': '长期画像：常航线 + 价格敏感度'},
        ],
    },
]

def work_item(it):
    html = section({'work-1': 'work1', 'work-2': 'work2', 'work-3': 'work3', 'work-4': 'work4', 'work-5': 'memory'}[it['id']])
    return {
        'id': it['id'], 'title': it['title'], 'short': it['short'], 'summary': it['summary'],
        'resume': it['resume'], 'subTopics': [], 'nodes': it['nodes'], 'intro': it['summary'],
        'io': it['io'], 'codeRefs': [], 'introHtml': html,
    }

work_items = {'version': '1.0', 'workItems': [work_item(it) for it in WORK_ITEMS]}
(OUT / 'work-items.json').write_text(json.dumps(work_items, ensure_ascii=False, indent=2), encoding='utf-8')

# 4) graph.json —— 执行图 SVG（20 节点，与 work-items 节点对齐）
NODES = [
    ('__start__', 40, 30, '开始'),
    ('user_input', 190, 30, '用户诉求'),
    ('order_align', 340, 30, '订单对齐'),
    ('query_understand', 490, 30, '意图理解'),
    ('agent_node', 640, 30, '规划编排'),
    ('memory_node', 40, 130, '记忆读写'),
    ('schema_validate', 340, 130, 'Schema校验'),
    ('tool_rule_retrieve', 190, 230, '规则检索'),
    ('tool_rerank', 340, 230, '结果精排'),
    ('mmr_filter', 490, 230, '去重筛选'),
    ('rag_search', 640, 230, 'RAG组装'),
    ('tool_flight_status', 190, 330, '航班状态'),
    ('tool_recalc_fee', 340, 330, '差价计算'),
    ('tool_scheme_gen', 490, 330, '方案生成'),
    ('verify_node', 640, 330, '质量校验'),
    ('retry_node', 490, 420, '重试修正'),
    ('human_review', 190, 420, '人工兜底'),
    ('checkpoint_gate', 340, 500, '检查点'),
    ('finish', 490, 500, '记忆写入'),
    ('__end__', 640, 500, '结束'),
]
EDGES = [
    (105, 52, 190, 52, False), (255, 52, 340, 52, False), (405, 52, 490, 52, False),
    (555, 52, 640, 52, False), (705, 74, 405, 130, False),
    (255, 74, 105, 130, True), (105, 174, 490, 52, True),
    (405, 174, 255, 230, False), (255, 274, 405, 230, False), (405, 274, 555, 230, False),
    (555, 274, 705, 230, False),
    (705, 274, 255, 330, False), (255, 374, 405, 330, False), (405, 374, 555, 330, False),
    (555, 374, 705, 330, False),
    (705, 374, 555, 420, False), (705, 374, 255, 420, True),
    (555, 464, 405, 500, False), (255, 464, 405, 500, True),
    (405, 544, 555, 500, False), (555, 544, 705, 500, False),
]

def build_svg():
    p = ['<svg id="graph-svg" viewBox="0 0 900 660" xmlns="http://www.w3.org/2000/svg" role="img" aria-label="LangGraph真实节点与边">']
    p.append('<defs><marker id="arrow" markerWidth="6" markerHeight="6" refX="5" refY="3" orient="auto"><path d="M0,0 L6,3 L0,6" fill="#93a9a0"/></marker></defs>')
    for x1, y1, x2, y2, dash in EDGES:
        dash_attr = ' stroke-dasharray="4 3"' if dash else ' stroke-dasharray="none"'
        p.append(f'<path d="M{x1},{y1} L{x2},{y2}" stroke="#bdcac4" fill="none" marker-end="url(#arrow)"{dash_attr}/>')
    for nid, x, y, label in NODES:
        p.append(f'<g data-node="{nid}"><rect x="{x}" y="{y}" width="130" height="44" rx="8" fill="#f4f6ef" stroke="#95b1a5"/>'
                 f'<text x="{x+65}" y="{y+27}" text-anchor="middle" font-size="13" fill="#294b44">{label}</text></g>')
    p.append('</svg>')
    return ''.join(p)

def build_mermaid():
    lines = ['---', 'config:', '  flowchart:', '    curve: linear', '---', 'graph TD;']
    for nid, _, _, label in NODES:
        lines.append(f'\t{nid}([{label}])')
    pairs = [('__start__', 'user_input'), ('user_input', 'order_align'), ('order_align', 'query_understand'),
             ('query_understand', 'agent_node'), ('user_input', 'memory_node'), ('memory_node', 'query_understand'),
             ('agent_node', 'schema_validate'), ('schema_validate', 'tool_rule_retrieve'),
             ('tool_rule_retrieve', 'tool_rerank'), ('tool_rerank', 'mmr_filter'), ('mmr_filter', 'rag_search'),
             ('rag_search', 'tool_flight_status'), ('tool_flight_status', 'tool_recalc_fee'),
             ('tool_recalc_fee', 'tool_scheme_gen'), ('tool_scheme_gen', 'verify_node'),
             ('verify_node', 'retry_node'), ('verify_node', 'human_review'), ('retry_node', 'tool_scheme_gen'),
             ('retry_node', 'human_review'), ('human_review', 'checkpoint_gate'), ('checkpoint_gate', 'finish'),
             ('finish', '__end__')]
    for s, t in pairs:
        lines.append(f'\t{s} --> {t}')
    return '\n'.join(lines)

(OUT / 'graph.json').write_text(json.dumps({'mermaid': build_mermaid(), 'svg': build_svg()}, ensure_ascii=False, indent=2), encoding='utf-8')

# 5) tutorial-data.json —— 教学示例代码（air_ticket_agent/*.py，教学示意）
TUTORIAL_FILES = {
    'air_ticket_agent/tools.py': {'text': '''# 工具封装：查航班状态 / 算差价 / 查规则 / 生成方案 / 出票
# 固定 Schema 入参出参 + validate_call 校验（工作一）
TOOLS = [
  {"name": "check_flight_status", "params": {"flight_no": "str", "date": "str"}},
  {"name": "recalc_change_fee",    "params": {"order_id": "str", "target_date": "str"}},
  {"name": "retrieve_refund_rule", "params": {"airline": "str", "cabin": "str"}},
  {"name": "gen_change_scheme",    "params": {"order_id": "str", "target_date": "str"}},
  {"name": "issue_ticket",         "params": {"order_id": "str", "scheme_id": "str"}},
]

def validate_call(tool, args):
    # 参数类型/必填/枚举校验，失败抛 ToolCallError 触发重试
    ...'''},
    'air_ticket_agent/graph.py': {'text': '''# LangGraph 状态机：解析→检索→确认→生成→校验（工作一）
# 条件边：查不到政策→重试；低置信度→人工兜底；出票→用户确认
from langgraph.graph import StateGraph

def build_graph():
    g = StateGraph(AgentState)
    g.add_node("query_understand", understand)
    g.add_node("agent_node", plan_next)          # ReAct 决策
    g.add_node("tool_rule_retrieve", retrieve)   # 必经节点，防跳步
    g.add_node("verify_node", verify)            # 金额后验 + Fact-Checker
    g.add_edge("query_understand", "agent_node")
    g.add_conditional_edges("verify_node", gate, {
        "ok": "checkpoint_gate", "retry": "retry_node", "human": "human_review"})
    return g.compile(checkpointer=MemorySaver())'''},
    'air_ticket_agent/query.py': {'text': '''# 意图理解与 Query 改写（工作二）
# 订单字段对齐 → 多诉求拆解 → 指代消解 → 结构化输出
def parse_intent(raw, order):
    sub_queries = split_sub_queries(raw)          # 一句话多诉求拆成多条
    resolved = resolve_reference(sub_queries, order)  # 「这票/它」回填订单字段
    return {
        "sub_queries": resolved,
        "intent": classify(resolved[0]),
        "filters": {"airline": order.airline, "cabin": order.cabin},
        "rewrite_confidence": 0.91,               # 低于阈值回退原始 query
    }'''},
    'air_ticket_agent/retrieval.py': {'text': '''# 混合检索与精排（工作三）：60→40→10→5→3
def hybrid_retrieve(query, filters):
    dense = vector_top60(query)      # 语义召回 Top-60
    sparse = bm25_top60(query)       # 关键词召回 Top-60（航司/舱位代码）
    fused = rrf_merge(dense, sparse, k=60)          # 排名融合取前 40
    filtered = hard_filter(fused, filters)          # 结构化过滤
    top10 = cross_encoder_rerank(filtered)          # 精排，动态截断
    top5 = mmr_dedup(top10, lam=0.7)                # 去冗余
    return top5[:3]                                  # 注入前 3'''},
    'air_ticket_agent/verify.py': {'text': '''# 幻觉治理与质量把关（工作四）
def verify_scheme(scheme, fee_from_tool, retrieved_rules):
    quote_ok = extract_amount(scheme.text) == fee_from_tool  # 金额后验
    claims = split_claims(scheme.text)
    supported = all(has_evidence(c, retrieved_rules) for c in claims)  # 事实核查
    confidence = min(quote_ok_score, supported_score)
    if confidence < 0.85:                       # 阈值 0.85
        return refine(scheme, errors=collect_errors())   # Self-Refinement
    return scheme'''},
    'air_ticket_agent/memory.py': {'text': '''# 上下文与记忆系统（工作五）
# 短期：会话栈 + 滑动窗口摘要；长期：用户画像（去重写入）；预算：按优先级注入
def inject_context(question, order_stack, profile, budget):
    pri = [system_prompt, question, retrieved_policy, profile_top3]
    return fit_into_budget(pri, budget)   # 系统提示 > 当前诉求 > 政策 > 画像'''},
}
tutorial = {
    'version': '1.0',
    'lessons': [
        {'id': 'overview', 'title': '从一个退改诉求到可溯源方案', 'category': '从这里开始',
         'summary': '沿着一次「改签比价」咨询，认识工具封装、意图理解、混合检索、记忆与校验的整体链路。',
         'tags': ['入门', 'Function Calling', 'LangGraph', '整体流程'], 'chapter': 1,
         'flow': ['用户口语诉求', '意图理解/改写', '混合检索政策', '引擎算差价', '方案生成与校验', '返回可溯源答复'],
         'steps': ['用户发「能改到后天吗补多少钱」，query_understand 拆成「改签到后天的差价规则」子 query 并回填订单字段。',
                   'hybrid_retrieve 双路召回（语义 + BM25）融合后精排，命中适用政策 RULE-10023。',
                   'recalc_change_fee 引擎算出真实差价 580 元（模型不自己算）。',
                   'tool_scheme_gen 基于政策 + 差价生成结构化方案，verify_node 金额后验 + 事实核查（阈值 0.85）。',
                   '通过后返回「可改签，补差价 580 元，依据 RULE-10023」，全程可溯源。']},
    ],
    'files': TUTORIAL_FILES,
}
(OUT / 'tutorial-data.json').write_text(json.dumps(tutorial, ensure_ascii=False, indent=2), encoding='utf-8')

# 6) index.json 注册表加第三项
idx = json.loads(INDEX.read_text(encoding='utf-8'))
if not any(p['id'] == 'air-ticket' for p in idx['projects']):
    idx['projects'].append({
        'id': 'air-ticket',
        'name': '机票退改签Agent',
        'tagline': '退改签 Agent · 意图理解 · 混合检索 · 幻觉治理'
    })
INDEX.write_text(json.dumps(idx, ensure_ascii=False, indent=2), encoding='utf-8')

print('handbook chars:', len(h))
print('guide chapters:', len(guide['chapters']))
print('work-items:', len(work_items['workItems']))
print('graph svg nodes:', build_svg().count('data-node'))
print('tutorial files:', len(TUTORIAL_FILES))
print('index projects:', [p['id'] for p in idx['projects']])
