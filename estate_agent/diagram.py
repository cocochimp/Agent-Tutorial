"""由编译图的真实边生成离线SVG，页面可按Trace点亮节点。"""
from html import escape


def svg_graph(graph):
    positions = {"__start__": (40, 30), "understand": (180, 30), "clarify": (360, 30),
                 "agent_node": (180, 130), "schema_retrieval": (20, 230), "query_sql": (180, 230),
                 "calculate": (340, 230), "analyze": (500, 230), "rag_search": (660, 230),
                 "checkpoint_gate": (440, 130), "retry_node": (650, 130),
                 "generate_report": (180, 350), "validate": (340, 350), "human_approval": (500, 350),
                 "execute_action": (660, 350), "finish": (340, 450), "failed": (660, 450), "__end__": (510, 450),
                 "data_agent": (20, 520), "knowledge_agent": (240, 520), "report_agent": (470, 520)}
    labels = {"__start__": "开始", "__end__": "结束", "understand": "理解/鉴权", "clarify": "澄清中断", "agent_node": "规划下一步",
              "schema_retrieval": "Schema检索", "query_sql": "SQL校验/执行", "calculate": "指标计算", "analyze": "漏斗分析", "rag_search": "混合检索",
              "checkpoint_gate": "检查点", "retry_node": "重试", "generate_report": "报告生成", "validate": "Verifier",
              "human_approval": "人工审批", "execute_action": "幂等执行", "finish": "保存记忆", "failed": "错误兜底",
              "data_agent": "数据专家子图", "knowledge_agent": "知识专家子图", "report_agent": "报告专家子图"}
    definition = graph.get_graph()
    parts = ['<svg id="graph-svg" viewBox="0 0 840 600" xmlns="http://www.w3.org/2000/svg" role="img" aria-label="LangGraph真实节点与边">',
             '<defs><marker id="arrow" markerWidth="6" markerHeight="6" refX="5" refY="3" orient="auto"><path d="M0,0 L6,3 L0,6" fill="#93a9a0"/></marker></defs>']
    for edge in definition.edges:
        if edge.source not in positions or edge.target not in positions:
            continue
        x, y = positions[edge.source]
        xx, yy = positions[edge.target]
        parts.append(f'<path d="M{x+65},{y+22} L{xx+65},{yy+22}" stroke="#bdcac4" fill="none" marker-end="url(#arrow)" stroke-dasharray="{"4 3" if edge.conditional else "none"}"/>')
    for name in definition.nodes:
        if name not in positions:
            continue
        x, y = positions[name]
        parts.append(f'<g data-node="{escape(name)}"><rect x="{x}" y="{y}" width="130" height="44" rx="8" fill="#f4f6ef" stroke="#95b1a5"/><text x="{x+65}" y="{y+27}" text-anchor="middle" font-size="13" fill="#294b44">{escape(labels.get(name,name))}</text></g>')
    return ''.join(parts)+"</svg>"
