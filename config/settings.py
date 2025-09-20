"""
系统配置文件
"""

import os
from pathlib import Path
from typing import Dict, Any, Optional


class Settings:
    """系统配置类"""

    def __init__(self):
        # 基础配置
        self.app_name: str = "维标管理工具"
        self.app_version: str = "1.0.0"
        self.debug: bool = False

        # 路径配置
        self.project_root: Path = Path(__file__).parent.parent
        self.data_dir: Path = self.project_root / "data"
        self.upload_dir: Path = self.data_dir / "uploads"
        self.export_dir: Path = self.data_dir / "exports"

        # 数据库配置
        self.neo4j_uri: str = "bolt://124.223.52.226:7687"
        self.neo4j_username: str = "neo4j"
        self.neo4j_password: str = "neo4jneo4j"

        # API配置
        self.deepseek_api_key: Optional[str] = "sk-af8dd0517c7649bb81341ac2761c4041"
        self.deepseek_api_base: str = "https://api.deepseek.com/v1"
        self.deepseek_model: str = "deepseek-chat"

        # 处理配置
        self.max_concurrency: int = 3
        self.default_timeout: int = 120  # 秒
        self.batch_size: int = 5

        # 界面配置
        self.server_name: str = "0.0.0.0"
        self.server_port: int = 7860
        self.share: bool = False

        # 日志配置
        self.log_level: str = "INFO"
        self.log_file: Path = self.project_root / "logs" / "app.log"

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
