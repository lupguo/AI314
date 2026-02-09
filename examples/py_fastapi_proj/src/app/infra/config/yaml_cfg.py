"""YAML 配置单例模块，支持环境变量替换"""
import os
from typing import Any, Dict, Optional

import yaml

_yaml_config: Optional[Dict[str, Any]] = None
_config_path: Optional[str] = None


def _resolve_env_vars(config: Any) -> Any:
    """递归替换 ${ENV_VAR} 占位符"""
    if isinstance(config, dict):
        return {k: _resolve_env_vars(v) for k, v in config.items()}
    elif isinstance(config, list):
        return [_resolve_env_vars(item) for item in config]
    elif isinstance(config, str) and config.startswith("${") and config.endswith("}"):
        env_var = config[2:-1]
        return os.getenv(env_var, config)
    return config


def get_config_file_path() -> str:
    """获取配置文件路径"""
    if config_file := os.getenv("CONFIG_FILE"):
        return config_file
    app_env = os.getenv("APP_ENV", "dev")
    return f"conf/app_{app_env}.yaml"


def init_yaml_config(config_path: Optional[str] = None) -> None:
    """初始化 YAML 配置单例"""
    global _yaml_config, _config_path

    if config_path is None:
        config_path = get_config_file_path()

    if not os.path.exists(config_path):
        raise FileNotFoundError(f"配置文件不存在: {config_path}")

    with open(config_path, "r", encoding="utf-8") as f:
        config = yaml.safe_load(f) or {}

    _yaml_config = _resolve_env_vars(config)
    _config_path = config_path


def get_yaml_config() -> Dict[str, Any]:
    """获取完整配置"""
    if _yaml_config is None:
        init_yaml_config()
    return _yaml_config


def get_yaml_block(block_name: str) -> Dict[str, Any]:
    """获取指定配置块"""
    config = get_yaml_config()
    return config.get(block_name, {}) if block_name else config
