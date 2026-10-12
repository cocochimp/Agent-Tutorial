"""生成 web/projects/photo-q/tutorial-data.json（教学示例代码）+ 回填 work-items codeRefs。

拍照搜题项目无真实源码，示例代码为教学示意（结构正确、可讲解），供节点浮窗「实例代码」展示。
"""
import json, hashlib
from pathlib import Path

PHOTO = Path('web/projects/photo-q')
OUT = PHOTO / 'tutorial-data.json'

FILES = {}

FILES['photo_agent/tools.py'] = '''"""拍照搜题 Agent · 工具封装（Function Calling）
统一入参出参 Schema，供 Agent 规划层调度；校验失败触发错误重试。"""
TOOL_SCHEMAS = {
    "ocr_parse": {"desc": "解析题目图片，输出文本与 LaTeX",
                  "params": {"image_id": "str", "page_slice": "int"},
                  "required": ["image_id"]},
    "tool_retrieve": {"desc": "题库混合检索，返回候选题目",
                      "params": {"query": "str", "top_k": "int"},
                      "required": ["query"]},
    "tool_generate": {"desc": "基于检索结果生成解题步骤",
                      "params": {"qid": "str", "evidence": "list"},
                      "required": ["qid"]},
    "similar_recommend": {"desc": "推荐相似题练习",
                          "params": {"qid": "str", "n": "int"},
                          "required": ["qid"]},
}

class ToolCallError(Exception):
    """工具调用不符合 Schema 时抛出，由重试节点捕获。"""

def validate_call(name, args):
    schema = TOOL_SCHEMAS.get(name)
    if not schema:
        raise ToolCallError(f"未知工具: {name}")
    missing = [k for k in schema["required"] if k not in args]
    if missing:
        raise ToolCallError(f"{name} 缺参: {missing}")
    for k, v in args.items():
        expected = schema["params"].get(k)
        if expected == "str" and not isinstance(v, str):
            raise ToolCallError(f"{name} 参数 {k} 应为 str, 实为 {type(v).__name__}")
    return {"valid": True, "schema": schema["desc"]}
'''

FILES['photo_agent/graph.py'] = '''"""LangGraph 状态机：解析→检索→记忆→生成→校验，含重试与人工兜底。"""
from typing import TypedDict
from langgraph.graph import StateGraph, END

MAX_ATTEMPTS = 2
CONFIDENCE_THRESHOLD = 0.85

class PhotoAgentState(TypedDict):
    image_id: str
    sub_queries: list
    candidates: list
    answer: dict
    attempts: int
    confidence: float

def should_retry(state: PhotoAgentState) -> bool:
    """校验失败且未超次数 → 重试；否则人工兜底。"""
    return state["attempts"] < MAX_ATTEMPTS and state["confidence"] < CONFIDENCE_THRESHOLD

def passed(state: PhotoAgentState) -> bool:
    return state["confidence"] >= CONFIDENCE_THRESHOLD

def build_agent():
    g = StateGraph(PhotoAgentState)
    g.add_node("user_input", receive_image)
    g.add_node("ocr_parse", ocr_parse)
    g.add_node("query_understand", understand)
    g.add_node("agent_node", plan_next_tool)     # ReAct 决策：选工具
    g.add_node("tool_retrieve", hybrid_retrieve)
    g.add_node("tool_generate", generate_answer)
    g.add_node("verify_node", fact_check)
    g.add_node("retry_node", self_refine)
    g.add_node("memory_node", update_memory)
    g.add_node("finish", output)
    g.add_edge("user_input", "ocr_parse")
    g.add_edge("ocr_parse", "query_understand")
    g.add_edge("query_understand", "agent_node")
    g.add_conditional_edges("verify_node", should_retry,
                            {True: "retry_node", False: "finish"})
    g.add_edge("retry_node", "verify_node")
    g.add_edge("finish", END)
    return g.compile(checkpointer=SQLiteCheckpointer("state.db"))
'''

FILES['photo_agent/query.py'] = '''"""Query 理解：一图多题拆解 / 指代消解 / 改写 / 结构化输出。"""
def understand_query(image_text: str, conversation: list) -> dict:
    # 1) 一图多题：版面切分拆成多条子 query
    sub_queries = split_multi_problem(image_text)
    # 2) 跨题指代消解：「上一题的结果」「这道题」绑定题目栈
    resolved = resolve_coreference(sub_queries, conversation)
    # 3) 必要时代码改写 / HyDE 扩写，错字顺句
    rewritten = [rewrite(q) for q in resolved]
    # 4) 结构化字段驱动下游 Filter 与精排加权
    return {
        "sub_queries": rewritten,
        "intent": classify(rewritten),            # 数学-导数-求值
        "filters": extract_filters(rewritten),    # {年级, 科目, 知识点, 题型}
        "dense_sparse": decide_fusion(rewritten), # 偏语义/偏精确 → 融合权重 α
        "rewrite_confidence": 0.91,               # 低于阈值回退原始 query
    }
'''

FILES['photo_agent/retrieval.py'] = '''"""混合检索：BGE 向量 + BM25 双路 → RRF 融合 → Cross-Encoder 精排 → MMR。"""
TOP_DENSE, TOP_SPARSE = 100, 100
FUSE_TOP, RERANK_TOP, FINAL_TOP = 50, 10, 5
INJECT_TOP = 3

def hybrid_retrieve(query: str, filters: dict) -> list:
    dense = bge_index.search(query, k=TOP_DENSE)     # 语义：换了说法也能找到
    sparse = bm25_index.search(query, k=TOP_SPARSE)  # 关键词：公式、题号精确匹配
    fused = rrf_fuse(dense, sparse, top=FUSE_TOP)    # 只看排名融合，天然可比
    filtered = apply_filters(fused, filters)         # 年级/科目/知识点硬过滤
    reranked = cross_encoder.rerank(filtered, top=RERANK_TOP)  # 逐条精判
    final = mmr_dedup(reranked, top=FINAL_TOP, lambda_=0.7)    # 去近似重复
    return final[:INJECT_TOP]                        # 注入 Top-3
'''

FILES['photo_agent/verify.py'] = '''"""质量把关：唯一数据源 + LaTeX 渲染校验 + Fact-Checker + Self-Refinement。"""
def verify(answer: dict, evidence: list) -> dict:
    checks = []
    # 格式校验：LaTeX 逐行送渲染器试渲染
    for i, latex in enumerate(answer["latex"]):
        ok = try_render(latex)
        checks.append({"type": "render", "line": i + 1, "pass": ok,
                       "detail": None if ok else f"L{i+1} 渲染失败"})
    # 事实核查：生成内容必须能在检索命中材料里找到依据
    claims = extract_claims(answer["steps"])
    for claim in claims:
        supported = any(claim in e for e in evidence)
        checks.append({"type": "fact", "claim": claim, "pass": supported,
                       "detail": None if supported else "unsupported_claim"})
    confidence = min(c["pass"] for c in checks)  # 取最差一项
    if confidence:
        return {"verdict": "pass", "confidence": 0.93}
    feedback = [c["detail"] for c in checks if not c["pass"]]
    return {"verdict": "refine", "confidence": 0.6, "feedback": feedback}
'''

FILES['photo_agent/memory.py'] = '''"""记忆系统：短期会话记忆 + 长期学生画像 + 上下文预算管理。"""
def build_context(state: dict, profile: dict) -> str:
    # 短期：滑动窗口 + 摘要压缩，只留最近几轮原文
    short = compress_window(state["rounds"], window=6)
    # 长期：画像按当前题知识点检索注入（画像也当一路召回）
    boost = retrieve_profile(profile, state["topic"], top=3)
    # 预算：按优先级注入 系统提示 > 当前问题 > 检索原题 > 记忆/画像
    return priority_inject([
        ("system", state["system"]),
        ("question", state["question"]),
        ("evidence", state["evidence"]),
        ("memory", short + boost),
    ])

def update_mastery(profile: dict, topic: str, correct: bool):
    """掌握度建模：答对上调 / 答错下调 / 遗忘衰减（概念级即可）。"""
    profile[topic] = max(0.0, min(1.0, profile.get(topic, 0.5)
                                  + (0.08 if correct else -0.12)))
'''

lessons = [
    {'id': 'l1', 'title': '工具封装与 Schema 校验', 'files': ['photo_agent/tools.py'],
     'desc': '把 OCR/检索/生成/相似题封装为统一 Schema 的工具，校验失败重试。'},
    {'id': 'l2', 'title': 'LangGraph 状态机编排', 'files': ['photo_agent/graph.py'],
     'desc': '解析→检索→记忆→生成→校验五段式，条件边实现重试与人工兜底。'},
    {'id': 'l3', 'title': 'Query 理解与拆题', 'files': ['photo_agent/query.py'],
     'desc': '一图多题拆解、指代消解、结构化字段输出。'},
    {'id': 'l4', 'title': '混合检索与精排', 'files': ['photo_agent/retrieval.py'],
     'desc': 'BGE+BM25 双路、RRF 融合、Cross-Encoder 精排、MMR 去冗余。'},
    {'id': 'l5', 'title': '幻觉治理与质量把关', 'files': ['photo_agent/verify.py'],
     'desc': '唯一数据源、LaTeX 渲染校验、Fact-Checker、Self-Refinement。'},
    {'id': 'l6', 'title': '记忆与上下文预算', 'files': ['photo_agent/memory.py'],
     'desc': '短期会话记忆、长期画像掌握度、按优先级注入。'},
]

files_out = {}
for path, text in FILES.items():
    files_out[path] = {'text': text, 'sha256': hashlib.sha256(text.encode('utf-8')).hexdigest()}

data = {'version': '1.0', 'lessons': lessons, 'files': files_out}
OUT.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding='utf-8')
print('tutorial written, files:', len(files_out))

# 回填 work-items codeRefs（行号按示例代码实际行数计算）
def code_refs(path, start_kw, end_kw, note):
    text = FILES[path]
    lines = text.split('\n')
    s = next(i + 1 for i, ln in enumerate(lines) if start_kw in ln)
    e = next(i + 1 for i, ln in enumerate(lines) if end_kw in ln)
    return {'path': path, 'start': s, 'end': e, 'note': note}

refs = {
    'work-1': [
        code_refs('photo_agent/tools.py', 'TOOL_SCHEMAS = {', 'def validate_call(name, args):',
                  '工具 Schema 定义与校验：缺参/类型错误即抛 ToolCallError'),
        code_refs('photo_agent/graph.py', 'def build_agent():', 'g.add_edge("finish", END)',
                  'LangGraph 状态机装配：五段式节点 + 条件边（重试/兜底）'),
    ],
    'work-2': [
        code_refs('photo_agent/query.py', 'def understand_query', 'return {',
                  'Query 理解：拆题 / 指代消解 / 结构化字段输出'),
    ],
    'work-3': [
        code_refs('photo_agent/retrieval.py', 'def hybrid_retrieve', 'return final[:INJECT_TOP]',
                  '双路召回 → RRF → 精排 → MMR → 注入 Top-3'),
    ],
    'work-4': [
        code_refs('photo_agent/verify.py', 'def verify(answer: dict', 'return {"verdict": "refine"',
                  'Fact-Checker：渲染校验 + 事实核查 + 自我修正反馈'),
    ],
    'work-5': [
        code_refs('photo_agent/memory.py', 'def build_context', 'def update_mastery',
                  '上下文预算注入 + 画像按需检索'),
    ],
}

wi_path = PHOTO / 'work-items.json'
wi = json.loads(wi_path.read_text(encoding='utf-8'))
for it in wi['workItems']:
    it['codeRefs'] = refs[it['id']]
wi_path.write_text(json.dumps(wi, ensure_ascii=False, indent=2), encoding='utf-8')
for wid, r in refs.items():
    print(wid, [(x['path'], x['start'], x['end']) for x in r])
