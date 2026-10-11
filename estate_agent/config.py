"""每次创建模型客户端时读配置，保存文件后下一次分析立即生效。"""
import json
import os
from .business import DemoError
from .data import ROOT

CONFIG_PATH = ROOT / "deepseek_config.json"
DEFAULTS = {"base_url": "https://api.deepseek.com", "model": "deepseek-flash", "api_key": ""}


def load_model_config():
    file_config = dict(DEFAULTS)
    if CONFIG_PATH.exists():
        try:
            # utf-8-sig兼容Windows编辑器写入的UTF-8 BOM。
            raw = json.loads(CONFIG_PATH.read_text(encoding="utf-8-sig"))
        except (OSError, ValueError) as exc:
            # 不回显JSON原文，避免把密钥带到错误信息或Trace。
            raise DemoError("INVALID_CONFIG", "deepseek_config.json读取失败，请检查JSON双引号、逗号和UTF-8编码。") from exc
        if not isinstance(raw, dict) or set(raw) - set(DEFAULTS):
            raise DemoError("INVALID_CONFIG", "deepseek_config.json只支持base_url、model、api_key三个字段。")
        if any(not isinstance(value, str) for value in raw.values()):
            raise DemoError("INVALID_CONFIG", "deepseek_config.json中的配置值必须是字符串。")
        file_config.update({key: value.strip() for key, value in raw.items()})
        # 填过key的文件优先，整个配置一起使用，避免混用其他服务的地址和密钥。
        if file_config["api_key"]:
            return file_config
    env_config = {key: os.environ.get(env, "").strip() for key, env in (
        ("base_url", "AGENT_BASE_URL"), ("model", "AGENT_MODEL"), ("api_key", "AGENT_API_KEY"))}
    return env_config if any(env_config.values()) else file_config
