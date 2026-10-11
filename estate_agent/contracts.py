"""任务、查询计划、模型解释都使用Pydantic作为模块边界。"""
from datetime import date
from typing import Literal
from pydantic import BaseModel, ConfigDict, Field, model_validator


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class Intent(StrictModel):
    intent: Literal["analysis", "knowledge"] = "analysis"
    region: Literal["朝阳", "海淀"] = "朝阳"
    metric: Literal["viewing_to_deal", "effective_viewing_rate", "followup_rate"] = "viewing_to_deal"
    start: date
    end: date
    compare: Literal["previous", "yoy"] = "previous"
    store_id: str | None = None
    action: Literal["none", "create_ticket", "publish_report"] = "none"
    confidence: float = Field(default=1, ge=0, le=1)
    clarification: str = ""

    @model_validator(mode="after")
    def dates(self):
        if self.end < self.start or (self.end-self.start).days > 90:
            raise ValueError("日期窗口需为1~91天")
        return self


class TaskSpec(Intent):
    days: int
    baseline_start: date
    baseline_end: date
    question: str
    clock: date


class SQLPlan(StrictModel):
    metric: Literal["viewing_to_deal", "effective_viewing_rate", "followup_rate"]
    group_by: Literal["store"] = "store"
    aggregate: Literal["sum_then_ratio"] = "sum_then_ratio"
    tables: list[Literal["stores", "daily_metrics"]] = ["stores", "daily_metrics"]


class Narrative(StrictModel):
    """模型只能挑选已验证的事实与建议ID，不能自由创作数字或制度。"""
    fact_ids: list[str]
    recommendation_ids: list[str]
    hypothesis_ids: list[Literal["followup_gap", "viewing_match", "recording_delay"]]
    confidence: float = Field(ge=0, le=1)
