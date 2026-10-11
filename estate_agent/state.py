"""StateGraph显式共享状态；只保存业务数据，不保存模型API密钥。"""
from typing import TypedDict


# total=False 允许节点只更新部分字段；未产生的结果可以暂时不存在。
# 这些字段进入检查点，不能放 API Key、客户端对象或数据库连接。
class AgentState(TypedDict, total=False):
    # 请求身份与运行设置：run_id 标识本次任务，session_id 串联多轮问题。
    run_id: str
    session_id: str
    user: dict
    question: str
    mode: str
    strategy: str
    backend: str
    graph_rag: bool
    # task 是校验后的业务参数；context 是会话摘要/偏好；results 是工具观察结果。
    task: dict
    context: dict
    results: dict
    trace: list
    # 循环控制：调用签名、工具次数、重试次数与修正次数都显式保存。
    seen: list
    tool_calls: int
    retry_count: int
    refinement_count: int
    risk_level: str
    clarify_count: int
    # action 是当前选定工具及参数，next_node 是条件边读取的目标。
    action: dict
    next_node: str
    status: str
    error: dict
    last_observation: dict
    model_stats: dict
    # 报告阶段分开保存草稿、证据选择、校验结果与最终报告，便于回溯。
    draft: dict
    report: dict
    narrative: dict
    verification: dict
    markdown: str
    # 业务副作用需明确审批；暂停状态记录供 interrupt/Command 恢复使用。
    approval: bool
    action_result: dict
    pause_after: str
    paused_nodes: list
    pending_pause: bool
    interrupts: list
    latency_ms: float
