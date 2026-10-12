"""生成 web/projects/photo-q/work-items.json：从手册 14 章提取 5 工作项教学数据。"""
import json, re
from pathlib import Path

SRC = Path('/Users/Doc/review/拍照搜题-agent-实习复盘手册-v2.html')
OUT = Path('web/projects/photo-q/work-items.json')
h = SRC.read_text(encoding='utf-8')

def section(sid):
    m = re.search(r'<section[^>]*id="%s"[^>]*>(.*?)</section>' % sid, h, re.S)
    return m.group(1) if m else ''

def strip(t):
    t = re.sub(r'<[^>]+>', '', t)
    t = t.replace('&nbsp;', ' ').replace('&amp;', '&').replace('&lt;', '<').replace('&gt;', '>')
    return re.sub(r'\s+', ' ', t).strip()

# 从 resume 章节提取 5 个条目文本（按「工作内容」列表项）
resume_html = section('resume')
resume_texts = {}
# 以工作内容标题起点的列表项切分
raw = strip(resume_html)
# 各条目关键词定位
for key, kw in [
    ('work-1', 'ReAct 规划编排'),
    ('work-2', '多模态/增强 Query 理解'),
    ('work-3', '混合检索与结果精排'),
    ('work-4', '解题生成与质量保障'),
    ('work-5', '上下文与记忆系统'),
]:
    i = raw.find(kw)
    resume_texts[key] = raw[i:i+520] if i >= 0 else ''

def build_item(wid, title, short, label, resume_text, metrics, metric_details,
               nodes, intro, io, intro_sid, intro_head):
    return {
        'id': wid,
        'title': title,
        'short': short,
        'summary': short,
        'resume': {
            'label': label,
            'text': resume_text,
            'metrics': metrics,
            'metricDetails': metric_details,
        },
        'subTopics': [],
        'nodes': nodes,
        'intro': intro,
        'io': io,
        'codeRefs': [],
        'introHtml': '<div class="story"><div class="story-head">%s</div>%s</div>' % (
            intro_head, section(intro_sid)),
    }

items = [
    build_item(
        'work-1', '工作一 · Agent 工具编排与流程规划', 'Agent 工具编排与流程规划', 'Agent 工具编排与流程规划',
        resume_texts['work-1'],
        '工具调用准确率 ≥92% · Schema 校验+错误重试 · 检索工具必经节点',
        [
            {'title': '工具调用准确率', 'design': '把 OCR、公式识别、题库检索、解题生成、相似题推荐封装为 Function Calling 工具，入参出参用固定 Schema 约束；模型传错字段/漏参数即校验失败并触发错误重试。以「一次调用是否按 Schema 成功执行并返回有效结果」为判定口径。',
             'source': '工具调用评测集（含正常、缺参数、类型错误、非法枚举四类用例）统计调用成功率；上线前基线约 78%，经 Schema 校验 + 重试后 ≥92%。'},
            {'title': '检索工具必经节点', 'design': '不强制先检索再作答，模型会跳过检索直接编答案——这是幻觉的主要来源。在 LangGraph 状态机中把题库检索设为必经节点，生成节点只消费检索结果。',
             'source': '线上事故复盘 + 评测集「无依据作答率」指标统计；强制必经后该指标降至 2% 以下。'},
        ],
        ['user_input', 'agent_node', 'schema_validate', 'tool_retrieve', 'tool_generate', 'verify_node', 'retry_node', 'checkpoint_gate', 'finish'],
        {
            'scene': '产品需求：家长拍一张含 3 道题的作业照片，App 要能自动逐题识别、分别讲解。',
            'problem': '没法用一条写死的流程搞定：有的题要查公式、有的要找相似题、识别失败还要重试；固定链路表达不了这些分支。',
            'locate': '问题在「决策层」：系统缺一个根据中间结果自主决定下一步调用哪个工具的能力。',
            'action': '把 OCR、公式识别、题库检索、解题生成、相似题推荐封装成统一 Schema 的工具；用 ReAct「思考→行动→观察→再思考」循环自主调度；用 LangGraph 状态机把「解析→检索→记忆→生成→校验」串起来，关键节点设置信度阈值与人工兜底。',
            'why': 'ReAct 适合不确定分支，代价是更耗 token、更难预测；状态机把边界框住，只在需要判断的节点交给模型。',
            'result': '工具调用准确率提升至 ≥92%；识题失败可回退重试、低置信度转人工，杜绝答非所问。',
        },
        [
            {'node': 'agent_node', 'input': {'question': '照片含 3 道题（一图多题），任务：逐题识别并讲解', 'tools': ['ocr_parse', 'tool_retrieve', 'tool_generate', 'similar_recommend'], 'schema': 'ocr_parse(image_id, page_slice) -> {latex, text}'},
             'output': {'plan': 'step1: ocr_parse 识别第 1 题 → step2: tool_retrieve 检索原题 → step3: tool_generate 生成讲解 → step4: 处理第 2 题…', 'selected_tool': 'ocr_parse', 'confidence': 0.93},
             'note': 'ReAct 循环：模型看着上一步结果决定下一步，调错工具时校验失败走 retry_node。'},
            {'node': 'schema_validate', 'input': {'tool_call': {'name': 'tool_retrieve', 'args': {'query': '求 f(x)=x²+2x+1 在 x=3 处的导数', 'top_k': 100}}},
             'output': {'valid': True, 'checked': ['query 非空', 'top_k 范围合法', '枚举正确'], 'error': None},
             'note': '入参出参强制 Schema：传错字段/漏参数即校验失败，触发错误重试。'},
        ],
        'work1', '🎯 场景复盘 · 一图三题怎么「自己决定下一步」 <small>ReAct / LangGraph / Schema 校验</small>',
    ),
    build_item(
        'work-2', '工作二 · 多模态解析与 Query 理解', '多模态解析与 Query 理解', '多模态解析与 Query 理解',
        resume_texts['work-2'],
        '复杂场景检索解决率 +25% · 一图多题拆解 · 指代消解',
        [
            {'title': '复杂场景检索解决率', 'design': '把 Query 理解拆为「改写与拆解（一图多题拆多条子 query、追问做指代消解与补全、OCR 错字顺句、必要时 HyDE 扩写）+ 问题理解（判学科题型路由、判精确/语义调融合权重）+ 关键信息提取（年级/科目/知识点/题型结构化字段驱动 Filter 与精排加权）」。',
             'source': '复杂场景评测集（一图多题、跨题指代、错字、表述残缺四类）对比「仅 OCR 直出 query」基线的检索解决率，提升 25%。'},
        ],
        ['user_input', 'ocr_parse', 'query_understand', 'step_back', 'agent_node', 'checkpoint_gate'],
        {
            'scene': '两个真实痛点：学生追问「这道题第 2 步为什么这么写」——「这道题」指哪道？一张照片混着好几道题。',
            'problem': '送进检索的问题本身残缺：一图多题没拆开、跨题指代没消解、OCR 有错字，后面检索再强也白搭。',
            'locate': '问题在「入口层」：图片没有先被读懂、拆清、补全，结构化信息没有提取出来。',
            'action': 'OCR + 公式识别输出 LaTeX → 版面切分拆题 → 指代消解/补全 → 输出 {sub_queries, intent, filters, dense_sparse, time_sensitivity, rewrite_confidence} 结构化字段。',
            'why': '结构化字段驱动下游 Filter 硬过滤与精排加权；rewrite_confidence 低于阈值回退用原始 query，避免过度改写。',
            'result': '复杂场景（一图多题、跨题指代）检索解决率提升 25%。',
        },
        [
            {'node': 'ocr_parse', 'input': {'image_id': 'IMG_20261012_001.jpg', 'page_slices': 3},
             'output': {'recognized': [{'latex': '已知 aₙ=2n-1，求该数列前 n 项和', 'confidence': 0.91}, {'latex': '求 f(x)=x²+2x+1 在 x=3 处的导数', 'confidence': 0.95}], 'render_errors': []},
             'note': 'OCR + 公式识别输出 LaTeX；渲染失败的行标记 render_error 触发重试。'},
            {'node': 'query_understand', 'input': {'raw_query': '这道题第 2 步为什么这么写', 'conversation': [{'user': '已知 aₙ=2n-1，求该数列前 n 项和', 'assistant': '通项公式代入求和…'}]},
             'output': {'sub_queries': ['求该数列前 n 项和，第 2 步为什么这样化简'], 'intent': '数学-数列-求和', 'filters': {'subject': '数学', 'grade': '高三', 'topic': '数列'}, 'dense_sparse': '偏语义', 'rewrite_confidence': 0.88},
             'note': '指代消解：把「这道题」绑定到题目栈里的当前对象，再补全上下文。'},
        ],
        'work2', '🎯 场景复盘 · 先把题读懂，再去搜 <small>OCR / 公式识别 / 拆题 / 指代消解 / 结构化字段</small>',
    ),
    build_item(
        'work-3', '工作三 · 混合检索与结果精排', '混合检索与结果精排', '混合检索与结果精排',
        resume_texts['work-3'],
        '原题命中率 +18% · 检索漏斗 60→40→10→5→3 · Recall@100 84%→96%',
        [
            {'title': '原题命中率', 'design': '双路召回：语义（BGE 向量）懂「换了说法也能找到」，关键词（BM25）懂「公式、题号精确匹配」，各取 Top-60 并行互补；RRF 按排名融合去重取 Top-40，Cross-Encoder 精排取 Top-10，MMR 去冗余取 Top-5，注入 Top-3。',
             'source': '题库命中评测集（含「换写法的同一道题」「带根号/绝对值符号的精确题」两类难点）对比单路语义检索基线，原题命中率提升 18%。'},
            {'title': 'Recall@100 84%→96%', 'design': '双路召回并行后，粗召回阶段 Top-100 覆盖度显著提升：语义召回覆盖跨写法相似题，BM25 覆盖字面精确题，两路互补。',
             'source': '评测集粗召回覆盖度统计；配合 QA 子切片泛化召回，Recall@100 从 84% 提升至 96%。'},
        ],
        ['agent_node', 'tool_retrieve', 'tool_rerank', 'mmr_filter', 'rag_search', 'checkpoint_gate'],
        {
            'scene': '线上 bug：一道带根号、绝对值符号的数学题，系统搜出一堆「看着像但其实不是」的题，找不到原题。',
            'problem': '纯语义检索擅长「意思相近」，但对公式符号、专有名词的精确匹配不敏感。',
            'locate': '问题在「召回层」：单一语义通道漏掉了字面精确匹配的题。',
            'action': '搭双路召回（BGE 向量 + BM25 关键词各 Top-100）→ RRF 融合 Top-50 → Cross-Encoder 精排 Top-10 → MMR 去冗余 Top-5 → 注入 Top-3。',
            'why': '两路分数不可比，RRF 只看排名天然可融合；精排用 Cross-Encoder 逐条精判，MMR 去掉近似重复，保证注入的是「真原题」。',
            'result': '原题命中率提升 18%，Recall@100 84%→96%。',
        },
        [
            {'node': 'tool_retrieve', 'input': {'sub_query': '求函数 f(x)=x²+2x+1 在 x=3 处的导数', 'subject': '数学', 'grade': '高三', 'top_k': 100},
             'output': {'dense_hits': 82, 'bm25_hits': 61, 'union': 100, 'recall_top100': 0.96},
             'note': '双路并行：语义 + 关键词各取 Top-100，union 后进融合。'},
            {'node': 'tool_rerank', 'input': {'candidates': 100, 'fuse': 'RRF top50', 'filters': {'subject': '数学', 'topic': '导数'}},
             'output': {'reranked_top10': [{'qid': 'MATH-09321', 'score': 0.97, 'source': '原题（换写法）'}, {'qid': 'MATH-10457', 'score': 0.91, 'source': 'QA 子切片'}]},
             'note': 'RRF 融合取 Top-50 → Cross-Encoder 精排取 Top-10 → MMR 去冗余取 Top-5 → 注入 Top-3。'},
        ],
        'work3', '🎯 场景复盘 · 带公式的题怎么「搜得到又搜得准」 <small>双路召回 / RRF 融合 / Cross-Encoder 精排 / MMR</small>',
    ),
    build_item(
        'work-4', '工作四 · 解题生成、幻觉治理与质量把关', '解题生成、幻觉治理与质量把关', '解题生成、幻觉治理与质量把关',
        resume_texts['work-4'],
        '解题步骤正确率 ≥96% · Fact-Checker 阈值 0.85 · 公式逐项校验',
        [
            {'title': '解题步骤正确率', 'design': '治幻觉三板斧：①唯一数据源（只能引用检索到的原题与知识点）；②结构化输出 + LaTeX 逐项渲染校验；③Fact-Checker 打置信度，低于阈值 0.85 触发 Self-Refinement，仍不过关转人工。',
             'source': '多学科「金标准」评测集（数学/物理/化学，标注禁止错误类型：无中生有、张冠李戴、计算错误、格式错误），解题步骤正确率 ≥96%。'},
            {'title': '置信度阈值 0.85', 'design': '在评测集上扫描 0.7~0.95 的阈值：太低拦不住幻觉，太高误伤正常讲解（转人工过多）。0.85 处「漏放幻觉」与「误转人工」总代价最小。',
             'source': '评测集阈值扫描实验；线上低于阈值的样本进入 Self-Refinement 或人工兜底。'},
        ],
        ['tool_generate', 'verify_node', 'retry_node', 'human_review', 'finish'],
        {
            'scene': '线上事故：模型编造一个不存在的公式，把学生教错了。教育场景对正确率容忍度极低。',
            'problem': '「讲得多漂亮」不设防：模型自由发挥、凭记忆编，讲错一步就是事故。',
            'locate': '问题在「生成层」：输出不可溯源、不可校验、错了拦不住。',
            'action': '唯一数据源约束（只消费检索命中内容）→ 强制结构化输出（步骤/公式/答案分字段）→ LaTeX 逐项渲染校验 → Fact-Checker 打置信度 → 低于 0.85 自我修正重试 → 仍不过关转人工。',
            'why': '把幻觉分类（无中生有/张冠李戴/计算错误/格式错误）再对症下药；阈值 0.85 是评测集扫描出的「漏放幻觉 vs 误转人工」总代价最小点。',
            'result': '解题步骤正确率提升至 ≥96%，P99 ≤ 1.2s。',
        },
        [
            {'node': 'verify_node', 'input': {'draft': {'steps': ['step1: 由 aₙ=2n-1 求前 n 项和…', 'step2: 根据韦达差值定理可得…'], 'latex': ['S_n = \\frac{n(a_1+a_n)}{2}', '\\frac{-b}{2a']}, 'evidence': ['检索命中知识点：数列求和公式', '检索命中知识点：导数定义']},
             'output': {'checks': [{'type': 'render', 'result': 'fail', 'detail': 'L2 LaTeX \\frac{-b}{2a 缺少花括号'}, {'type': 'fact', 'result': 'fail', 'detail': '「韦达差值定理」检索材料中无此依据（unsupported_claim）'}], 'confidence': 0.62, 'verdict': 'refine'},
             'note': '低于阈值 0.85 → Self-Refinement：把「哪一行渲染失败、哪句缺依据」作为反馈回灌模型重写。'},
        ],
        'work4', '🎯 场景复盘 · 讲得对、不编造、错了拦得住 <small>唯一数据源 / 公式校验 / Fact-Checker / Self-Refinement</small>',
    ),
    build_item(
        'work-5', '工作五 · 上下文与记忆系统设计', '上下文与记忆系统', '上下文与记忆系统',
        resume_texts['work-5'],
        '多轮追问理解准确率 +30% · Token 成本降 70% · 知识点掌握度建模',
        [
            {'title': '多轮追问理解准确率', 'design': '三层记忆：短期（会话级）维护「当前题目栈 + 讲解进度」，多轮指代消解绑定题目栈对象，滑动窗口 + 摘要压缩；长期（用户级）学生画像（知识点掌握度 0~1、错题本）向量化存储，检索时作个性化 boost；上下文预算管理按优先级注入。',
             'source': '多轮对话评测集（指代消解、跨轮依赖、长对话）对比无记忆基线，追问理解准确率提升 30%。'},
            {'title': 'Token 成本', 'design': '画像不全量塞进上下文：按当前题知识点检索最相关的几条再注入（画像也当一路「召回」）；滑动窗口把旧内容压成摘要，只留最近几轮原文。',
             'source': '线上单次会话 token 计量（含历史对话）对比无压缩基线，成本下降约 70%（Prompt Token 降 40% 且问答质量不降）。'},
        ],
        ['user_input', 'memory_node', 'query_understand', 'agent_node', 'checkpoint_gate'],
        {
            'scene': '两个需求：学生连续追问「这一步为什么」「换个方法讲」，系统必须记得上一轮讲了什么、当前在讲哪道题；学生每天来搜题，产品希望针对他常错的知识点讲得更细。',
            'problem': '「这一轮忘了上一轮」（短期断片）、「越用越不了解这个学生」（长期无画像），且上下文无限膨胀烧 token。',
            'locate': '问题在「记忆层」：会话状态、用户画像、上下文预算三块都没建。',
            'action': '短期记忆：题目栈 + 讲解进度 + 滑动窗口摘要压缩；长期记忆：知识点掌握度（答对上调/答错下调/遗忘衰减）+ 错题本，向量化存储检索时 boost；上下文预算管理按优先级注入。',
            'why': '画像按需检索注入而非全量塞入——画像也当一路「召回」，既个性化又不烧 token。',
            'result': '多轮追问理解准确率 +30%，Token 成本降约 70%。',
        },
        [
            {'node': 'memory_node', 'input': {'current_topic': '一元二次方程-判别式Δ', 'rounds': 5, 'user_actions': ['追问「判别式Δ与根的关系」3 次', '答对 1 题']},
             'output': {'profile_update': {'mastery_Δ与根的关系': 0.36, 'mastery_韦达定理': 0.82}, 'inject': ['画像top3：Δ与根的关系(0.36)、配方法(0.55)、求根公式(0.71)'], 'summary_compressed': True},
             'note': '短期记忆滑动窗口压缩旧轮次；长期画像按当前题知识点检索注入，薄弱点驱动讲解详略。'},
        ],
        'memory', '🎯 场景复盘 · 记得住上一轮，也越用越懂学生 <small>短期记忆 / 长期画像 / 掌握度建模 / 上下文预算</small>',
    ),
]

out = {'version': '1.0', 'workItems': items}
OUT.parent.mkdir(parents=True, exist_ok=True)
OUT.write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding='utf-8')
print('written', OUT, 'items:', len(items))
for it in items:
    print(it['id'], '| nodes:', len(it['nodes']), '| io:', len(it['io']), '| introHtml:', len(it['introHtml']))
