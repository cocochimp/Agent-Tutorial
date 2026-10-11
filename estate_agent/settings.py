"""不含密钥的项目设置。修改project_config.json后新任务读取新配置。"""
import json
from .data import ROOT


def settings():
    return json.loads((ROOT / "project_config.json").read_text(encoding="utf-8-sig"))
