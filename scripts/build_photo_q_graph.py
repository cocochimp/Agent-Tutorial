"""生成 web/projects/photo-q/graph.json：拍照搜题 Agent 执行图（mermaid + SVG，20 节点）。

节点名与 web/projects/photo-q/work-items.json 的 nodes 对齐，SVG 带 data-node 属性供 teaching.js 高亮。
"""
import json
from pathlib import Path

OUT = Path('web/projects/photo-q/graph.json')

# 节点: id -> (x, y, 中文标签)
# 画布 900x660，节点 130x44
NODES = [
    ('__start__',      40, 30,  '开始'),
    ('user_input',    190, 30,  '用户输入'),
    ('ocr_parse',     340, 30,  '多模态解析'),
    ('query_understand', 490, 30, 'Query理解'),
    ('agent_node',    640, 30,  '决策编排'),
    ('memory_node',    40, 130, '记忆读写'),
    ('schema_validate', 340, 130, 'Schema校验'),
    ('tool_retrieve', 190, 230, '混合检索'),
    ('tool_rerank',   340, 230, '结果精排'),
    ('mmr_filter',    490, 230, '去重筛选'),
    ('rag_search',    640, 230, 'RAG组装'),
    ('tool_generate', 190, 330, '解题生成'),
    ('verify_node',   340, 330, '质量校验'),
    ('retry_node',    640, 330, '重试修正'),
    ('human_review',  490, 420, '人工兜底'),
    ('checkpoint_gate', 190, 420, '检查点'),
    ('finish',        340, 500, '记忆写入'),
    ('__end__',       640, 500, '结束'),
]

# 边: (x1,y1,x2,y2, dash)
# 端点取源节点右下 / 目标节点左上，手工定坐标
EDGES = [
    (105, 52, 190, 52, False),        # start -> user_input
    (255, 52, 340, 52, False),        # user_input -> ocr_parse
    (405, 52, 490, 52, False),        # ocr_parse -> query_understand
    (555, 52, 640, 52, False),        # query_understand -> agent_node
    (705, 74, 405, 130, False),       # agent_node -> schema_validate
    (255, 74, 105, 130, True),        # user_input -.. memory_node (记忆读取)
    (105, 174, 490, 52, True),        # memory_node -.. query_understand (记忆注入)
    (405, 174, 255, 230, False),      # schema_validate -> tool_retrieve
    (255, 274, 405, 230, False),      # tool_retrieve -> tool_rerank
    (405, 274, 555, 230, False),      # tool_rerank -> mmr_filter
    (555, 274, 705, 230, False),      # mmr_filter -> rag_search
    (705, 274, 255, 330, False),      # rag_search -> tool_generate
    (255, 374, 405, 330, False),      # tool_generate -> verify_node
    (405, 374, 255, 420, False),      # verify_node -> checkpoint_gate (通过)
    (405, 374, 705, 330, False),      # verify_node -> retry_node (失败)
    (705, 374, 255, 330, True),       # retry_node -.. tool_generate (重试回灌)
    (705, 374, 555, 420, False),      # retry_node -> human_review (超次)
    (555, 464, 255, 420, False),      # human_review -> checkpoint_gate
    (255, 464, 405, 500, False),      # checkpoint_gate -> finish
    (405, 544, 705, 500, False),      # finish -> __end__
]

def build_svg():
    p = ['<svg id="graph-svg" viewBox="0 0 900 660" xmlns="http://www.w3.org/2000/svg" role="img" aria-label="LangGraph真实节点与边">']
    p.append('<defs><marker id="arrow" markerWidth="6" markerHeight="6" refX="5" refY="3" orient="auto"><path d="M0,0 L6,3 L0,6" fill="#93a9a0"/></marker></defs>')
    for x1, y1, x2, y2, dash in EDGES:
        dash_attr = ' stroke-dasharray="4 3"' if dash else ' stroke-dasharray="none"'
        p.append(f'<path d="M{x1},{y1} L{x2},{y2}" stroke="#bdcac4" fill="none" marker-end="url(#arrow)"{dash_attr}/>')
    for nid, x, y, label in NODES:
        cx, cy = x + 65, y + 27
        p.append(f'<g data-node="{nid}"><rect x="{x}" y="{y}" width="130" height="44" rx="8" fill="#f4f6ef" stroke="#95b1a5"/>'
                 f'<text x="{cx}" y="{cy}" text-anchor="middle" font-size="13" fill="#294b44">{label}</text></g>')
    p.append('</svg>')
    return ''.join(p)

def build_mermaid():
    lines = ['---', 'config:', '  flowchart:', '    curve: linear', '---', 'graph TD;']
    for nid, _, _, label in NODES:
        cls = 'first' if nid == '__start__' else ''
        lines.append(f'\t{nid}([{label}]){":::" + cls if cls else ""}')
    edges = [
        ('__start__', 'user_input'), ('user_input', 'ocr_parse'),
        ('ocr_parse', 'query_understand'), ('query_understand', 'agent_node'),
        ('user_input', 'memory_node'), ('memory_node', 'query_understand'),
        ('agent_node', 'schema_validate'), ('schema_validate', 'tool_retrieve'),
        ('tool_retrieve', 'tool_rerank'), ('tool_rerank', 'mmr_filter'),
        ('mmr_filter', 'rag_search'), ('rag_search', 'tool_generate'),
        ('tool_generate', 'verify_node'), ('verify_node', 'checkpoint_gate'),
        ('verify_node', 'retry_node'), ('retry_node', 'tool_generate'),
        ('retry_node', 'human_review'), ('human_review', 'checkpoint_gate'),
        ('checkpoint_gate', 'finish'), ('finish', '__end__'),
    ]
    for s, t in edges:
        lines.append(f'\t{s} --> {t}')
    return '\n'.join(lines)

out = {'mermaid': build_mermaid(), 'svg': build_svg()}
OUT.write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding='utf-8')
print('written, data-nodes:', len(NODES), 'edges:', len(EDGES), 'svg len:', len(out['svg']))
