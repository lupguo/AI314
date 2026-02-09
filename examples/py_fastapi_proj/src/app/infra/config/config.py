"""统一配置获取模块"""
from typing import Any, Dict, Literal

from . import yaml_cfg


def init_settings(config_path: str | None = None) -> None:
    """初始化配置系统"""
    yaml_cfg.init_yaml_config(config_path)


def get_app_env() -> Literal["dev", "test", "prod"]:
    """获取应用环境"""
    return yaml_cfg.get_yaml_block("").get("app_env", "dev")


def get_server_config() -> Dict[str, Any]:
    """获取服务器配置"""
    return yaml_cfg.get_yaml_block("server")


def get_logging_config() -> Dict[str, Any]:
    """获取日志配置"""
    return yaml_cfg.get_yaml_block("logging")


def get_retry_policy() -> Dict[str, Any]:
    """获取重试策略配置"""
    return yaml_cfg.get_yaml_block("retry_policy")


def get_service_config() -> Dict[str, Any]:
    """获取外部服务配置"""
    return yaml_cfg.get_yaml_block("external_service")
