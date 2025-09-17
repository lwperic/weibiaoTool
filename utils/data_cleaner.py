"""
数据清洗工具
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, List, Optional, Union
from pathlib import Path
import logging

from models.document import Document
from utils.logger import get_logger

logger = get_logger(__name__)


class DataCleaner(ABC):
    """数据清洗器抽象基类"""

    @abstractmethod
    def clean_document(self, document: Document) -> Document:
        """
        清洗文档数据

        Args:
            document: 原始文档对象

        Returns:
            清洗后的文档对象
        """
        pass

    @abstractmethod
    def validate_data(self, data: Dict[str, Any]) -> bool:
        """
        验证数据有效性

        Args:
            data: 要验证的数据

        Returns:
            是否有效
        """
        pass

    @abstractmethod
    def get_supported_formats(self) -> List[str]:
        """
        获取支持的文件格式

        Returns:
            支持的文件格式列表
        """
        pass


class DefaultDataCleaner(DataCleaner):
    """默认数据清洗器实现"""

    def __init__(self):
        """初始化默认数据清洗器"""
        self.supported_formats = [".doc", ".docx"]

    def clean_document(self, document: Document) -> Document:
        """
        清洗文档数据

        Args:
            document: 原始文档对象

        Returns:
            清洗后的文档对象
        """
        # 创建文档副本
        cleaned_document = document.copy()

        # 清洗文档名称
        cleaned_document.name = self._clean_text(cleaned_document.name)

        # 清洗原始文档名称
        if cleaned_document.original_name:
            cleaned_document.original_name = self._clean_text(cleaned_document.original_name)

        # 清洗元数据
        if cleaned_document.metadata:
            cleaned_document.metadata = self._clean_metadata(cleaned_document.metadata)

        logger.info(f"文档数据清洗完成: {cleaned_document.name}")
        return cleaned_document

    def validate_data(self, data: Dict[str, Any]) -> bool:
        """
        验证数据有效性

        Args:
            data: 要验证的数据

        Returns:
            是否有效
        """
        # 检查必要字段
        required_fields = ["id", "name", "file_path", "file_size", "file_hash"]
        for field in required_fields:
            if field not in data or not data[field]:
                logger.error(f"缺少必要字段: {field}")
                return False

        # 检查文件哈希格式
        if not isinstance(data["file_hash"], str) or len(data["file_hash"]) != 32:
            logger.error("文件哈希格式无效")
            return False

        # 检查文件大小
        if not isinstance(data["file_size"], int) or data["file_size"] <= 0:
            logger.error("文件大小无效")
            return False

        return True

    def get_supported_formats(self) -> List[str]:
        """
        获取支持的文件格式

        Returns:
            支持的文件格式列表
        """
        return self.supported_formats

    def _clean_text(self, text: str) -> str:
        """
        清洗文本内容

        Args:
            text: 原始文本

        Returns:
            清洗后的文本
        """
        if not text:
            return ""

        # 去除前后空格
        text = text.strip()

        # 去除多余空白字符
        text = " ".join(text.split())

        return text

    def _clean_metadata(self, metadata: Dict[str, Any]) -> Dict[str, Any]:
        """
        清洗元数据

        Args:
            metadata: 原始元数据

        Returns:
            清洗后的元数据
        """
        cleaned_metadata = {}

        for key, value in metadata.items():
            # 清理键名
            clean_key = self._clean_text(key)
            if not clean_key:
                continue

            # 清理值
            if isinstance(value, str):
                clean_value = self._clean_text(value)
            elif isinstance(value, dict):
                clean_value = self._clean_metadata(value)
            elif isinstance(value, list):
                clean_value = [self._clean_text(item) if isinstance(item, str) else item for item in value]
            else:
                clean_value = value

            # 只保留非空值
            if clean_value:
                cleaned_metadata[clean_key] = clean_value

        return cleaned_metadata


class CustomDataCleaner(DataCleaner):
    """自定义数据清洗器"""

    def __init__(self, config: Dict[str, Any]):
        """
        初始化自定义数据清洗器

        Args:
            config: 配置信息
        """
        self.config = config
        self.supported_formats = config.get("supported_formats", [".doc", ".docx"])
        self.cleaning_rules = config.get("cleaning_rules", {})

    def clean_document(self, document: Document) -> Document:
        """
        清洗文档数据

        Args:
            document: 原始文档对象

        Returns:
            清洗后的文档对象
        """
        # 创建文档副本
        cleaned_document = document.copy()

        # 应用自定义清洗规则
        if "name" in self.cleaning_rules:
            cleaned_document.name = self._apply_rule(cleaned_document.name, self.cleaning_rules["name"])

        if "original_name" in self.cleaning_rules:
            if cleaned_document.original_name:
                cleaned_document.original_name = self._apply_rule(
                    cleaned_document.original_name, 
                    self.cleaning_rules["original_name"]
                )

        if "metadata" in self.cleaning_rules:
            cleaned_document.metadata = self._apply_metadata_rules(
                cleaned_document.metadata, 
                self.cleaning_rules["metadata"]
            )

        logger.info(f"自定义数据清洗完成: {cleaned_document.name}")
        return cleaned_document

    def validate_data(self, data: Dict[str, Any]) -> bool:
        """
        验证数据有效性

        Args:
            data: 要验证的数据

        Returns:
            是否有效
        """
        # 首先应用默认验证
        default_cleaner = DefaultDataCleaner()
        if not default_cleaner.validate_data(data):
            return False

        # 应用自定义验证规则
        validation_rules = self.config.get("validation_rules", {})

        for field, rule in validation_rules.items():
            if field in data:
                if not self._validate_field(data[field], rule):
                    logger.error(f"字段验证失败: {field}")
                    return False

        return True

    def get_supported_formats(self) -> List[str]:
        """
        获取支持的文件格式

        Returns:
            支持的文件格式列表
        """
        return self.supported_formats

    def _apply_rule(self, value: str, rule: Dict[str, Any]) -> str:
        """
        应用清洗规则

        Args:
            value: 原始值
            rule: 清洗规则

        Returns:
            清洗后的值
        """
        if not value:
            return ""

        cleaned_value = value

        # 应用文本替换规则
        if "replacements" in rule:
            for old, new in rule["replacements"].items():
                cleaned_value = cleaned_value.replace(old, new)

        # 应用正则表达式规则
        if "regex" in rule:
            import re
            for pattern, replacement in rule["regex"].items():
                cleaned_value = re.sub(pattern, replacement, cleaned_value)

        # 应用修剪规则
        if "trim" in rule and rule["trim"]:
            cleaned_value = cleaned_value.strip()

        return cleaned_value

    def _apply_metadata_rules(self, metadata: Dict[str, Any], rules: Dict[str, Any]) -> Dict[str, Any]:
        """
        应用元数据清洗规则

        Args:
            metadata: 原始元数据
            rules: 清洗规则

        Returns:
            清洗后的元数据
        """
        cleaned_metadata = {}

        for key, value in metadata.items():
            # 检查是否有针对此键的规则
            if key in rules:
                clean_value = self._apply_rule(str(value), rules[key])
            else:
                clean_value = value

            # 只保留非空值
            if clean_value:
                cleaned_metadata[key] = clean_value

        return cleaned_metadata

    def _validate_field(self, value: Any, rule: Dict[str, Any]) -> bool:
        """
        验证字段

        Args:
            value: 字段值
            rule: 验证规则

        Returns:
            是否通过验证
        """
        # 类型验证
        if "type" in rule:
            expected_type = rule["type"]
            if expected_type == "string" and not isinstance(value, str):
                return False
            elif expected_type == "number" and not isinstance(value, (int, float)):
                return False
            elif expected_type == "list" and not isinstance(value, list):
                return False
            elif expected_type == "dict" and not isinstance(value, dict):
                return False

        # 长度验证
        if "min_length" in rule and len(str(value)) < rule["min_length"]:
            return False

        if "max_length" in rule and len(str(value)) > rule["max_length"]:
            return False

        # 正则表达式验证
        if "pattern" in rule:
            import re
            if not re.match(rule["pattern"], str(value)):
                return False

        return True
