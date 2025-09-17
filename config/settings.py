"""
系统配置文件
"""

import os
from pathlib import Path
from typing import Dict, Any, Optional
from pydantic_settings import BaseSettings
from pydantic import Field


class Settings(BaseSettings):
    """系统配置类"""

    # 基础配置
    app_name: str = "维标管理工具"
    app_version: str = "1.0.0"
    debug: bool = False

    # 路径配置
    project_root: Path = Path(__file__).parent.parent
    data_dir: Path = Field(default_factory=lambda: Path(__file__).parent.parent / "data")
    upload_dir: Path = Field(default_factory=lambda: Path(__file__).parent.parent / "data" / "uploads")
    export_dir: Path = Field(default_factory=lambda: Path(__file__).parent.parent / "data" / "exports")

    # 数据库配置
    neo4j_uri: str = "bolt://localhost:7687"
    neo4j_username: str = "neo4j"
    neo4j_password: str = "password"

    # API配置
    deepseek_api_key: Optional[str] = None
    deepseek_api_base: str = "https://api.deepseek.com"
    deepseek_model: str = "deepseek-chat"

    # 处理配置
    max_concurrency: int = 3
    default_timeout: int = 120  # 秒
    batch_size: int = 5

    # 界面配置
    server_name: str = "0.0.0.0"
    server_port: int = 7860
    share: bool = False

    # 日志配置
    log_level: str = "INFO"
    log_file: Path = Field(default_factory=lambda: Path(__file__).parent.parent / "logs" / "app.log")

    class Config:
        env_file = ".env"
        case_sensitive = False

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        # 确保必要的目录存在
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.upload_dir.mkdir(parents=True, exist_ok=True)
        self.export_dir.mkdir(parents=True, exist_ok=True)
        self.log_file.parent.mkdir(parents=True, exist_ok=True)


def load_settings() -> Settings:
    """加载系统配置"""
    return Settings()


# 全局配置实例
settings = load_settings()
