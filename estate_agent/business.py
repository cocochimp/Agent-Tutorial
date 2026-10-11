"""领域异常、可信登录身份、确定性漏斗分析。"""
from dataclasses import dataclass


class DemoError(Exception):
    def __init__(self, code, message):
        super().__init__(message)
        self.code = code


@dataclass(frozen=True)
class Identity:
    user_id: str = "demo-chaoyang-manager"
    role: str = "region_manager"
    regions: tuple = ("朝阳",)


USER = Identity()  # 服务端固定的模拟登录身份，不接受用户/模型传入角色


def analyze_funnel(query_result, store_id):
    row = next((r for r in query_result["rows"] if r["store_id"] == store_id), None)
    if row is None:
        raise DemoError("INVALID_ARGUMENT", "门店必须来自当前SQL结果。")
    signals = []
    for key, label in (("effective_viewings", "有效带看占比"), ("followups_24h", "24小时跟进率")):
        cur, prev = row["current"], row["previous"]
        c = cur[key]/cur["viewings"] if cur["viewings"] else None
        p = prev[key]/prev["viewings"] if prev["viewings"] else None
        signals.append({"metric": key, "label": label, "current_rate": c, "previous_rate": p,
                        "delta_pp": (c-p)*100 if c is not None and p is not None else None})
    return {"evidence_id": "CALC-01", "source_id": "SQL-01", "store_id": store_id, "name": row["name"],
            "signals": signals, "causality": "仅为同期变化，不能证明因果；需客户明细与人工核查。"}
