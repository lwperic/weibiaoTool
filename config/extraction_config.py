"""
知识抽取配置
"""

from typing import Dict, Any, Optional, List
from pydantic import BaseModel, Field
from enum import Enum


class ExtractionModel(str, Enum):
    """抽取模型枚举"""
    DEEPSEEK_R1 = "deepseek-r1"
    DEEPSEEK_V2 = "deepseek-v2"
    CUSTOM = "custom"


class ExtractionConfig(BaseModel):
    """知识抽取配置"""

    # 基本配置
    model: ExtractionModel = Field(ExtractionModel.DEEPSEEK_R1, description="抽取模型")
    model_params: Dict[str, Any] = Field(default_factory=dict, description="模型参数")

    # 处理配置
    max_concurrency: int = Field(3, ge=1, le=10, description="最大并发数量")
    timeout: int = Field(120, ge=30, le=300, description="处理超时时间(秒)")
    batch_size: int = Field(5, ge=1, le=20, description="批量处理大小")

    # 实体配置
    entity_types: List[str] = Field(
        default_factory=lambda: [
            "equipment", "component", "procedure", "standard", 
            "material", "condition", "error", "cause", 
            "solution", "maintenance", "inspection", "other"
        ],
        description="抽取的实体类型"
    )

    # 关系配置
    relation_types: List[str] = Field(
        default_factory=lambda: [
            "part_of", "used_in", "related_to", "causes", 
            "is_solution_for", "requires", "results_in", 
            "checked_by", "maintained_by", "follows", "depends_on"
        ],
        description="抽取的关系类型"
    )

    # 高级配置
    enable_incremental_update: bool = Field(True, description="启用增量更新")
    entity_name_normalization: bool = Field(True, description="实体名称标准化")
    min_confidence: float = Field(0.7, ge=0.0, le=1.0, description="最小置信度")

    # 自定义配置
    custom_prompt: Optional[str] = Field(None, description="自定义提示词")
    custom_examples: Optional[List[Dict[str, Any]]] = Field(None, description="自定义示例")

    class Config:
        use_enum_values = True

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return self.dict()

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ExtractionConfig":
        """从字典创建配置"""
        return cls(**data)

    def get_model_name(self) -> str:
        """获取模型名称"""
        model_map = {
            ExtractionModel.DEEPSEEK_R1: "deepseek-chat",
            ExtractionModel.DEEPSEEK_V2: "deepseek-chat",
            ExtractionModel.CUSTOM: "custom-model"
        }
        return model_map.get(self.model, "deepseek-chat")


class ExtractionConfigManager:
    """抽取配置管理器"""

    def __init__(self, config_dir: str):
        """
        初始化配置管理器

        Args:
            config_dir: 配置文件目录
        """
        self.config_dir = config_dir
        self.default_config = ExtractionConfig()
        self.current_config = self.default_config.copy()

        # 确保目录存在
        import os
        os.makedirs(config_dir, exist_ok=True)

        # 尝试加载配置文件
        self._load_config()

    def _load_config(self) -> None:
        """加载配置文件"""
        config_file = f"{self.config_dir}/extraction_config.json"

        try:
            import json
            with open(config_file, "r", encoding="utf-8") as f:
                data = json.load(f)
                self.current_config = ExtractionConfig.from_dict(data)
        except Exception:
            # 如果加载失败，使用默认配置
            self.current_config = self.default_config.copy()

    def _save_config(self) -> None:
        """保存配置文件"""
        config_file = f"{self.config_dir}/extraction_config.json"

        try:
            import json
            with open(config_file, "w", encoding="utf-8") as f:
                json.dump(self.current_config.to_dict(), f, ensure_ascii=False, indent=2)
        except Exception as e:
            raise Exception(f"保存配置失败: {str(e)}")

    def get_config(self) -> ExtractionConfig:
        """获取当前配置"""
        return self.current_config

    def update_config(self, **kwargs) -> None:
        """
        更新配置

        Args:
            **kwargs: 配置参数
        """
        # 更新配置
        for key, value in kwargs.items():
            if hasattr(self.current_config, key):
                setattr(self.current_config, key, value)

        # 保存配置
        self._save_config()

    def reset_config(self) -> None:
        """重置为默认配置"""
        self.current_config = self.default_config.copy()
        self._save_config()

    def validate_config(self) -> bool:
        """
        验证配置有效性

        Returns:
            是否有效
        """
        try:
            # 验证基本配置
            if not self.current_config.model:
                return False

            # 验证处理配置
            if not (1 <= self.current_config.max_concurrency <= 10):
                return False

            if not (30 <= self.current_config.timeout <= 300):
                return False

            if not (1 <= self.current_config.batch_size <= 20):
                return False

            # 验证置信度
            if not (0.0 <= self.current_config.min_confidence <= 1.0):
                return False

            return True
        except Exception:
            return False
