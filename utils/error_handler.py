"""
错误处理工具
"""

from enum import Enum
from typing import Dict, Any, List, Optional
from datetime import datetime
import json
import logging
from pathlib import Path

from utils.logger import get_logger

logger = get_logger(__name__)


class ErrorType(str, Enum):
    """错误类型枚举"""
    FORMAT_ERROR = "format_error"      # 格式错误
    PARSE_ERROR = "parse_error"        # 解析错误
    DATA_ERROR = "data_error"         # 数据错误
    SYSTEM_ERROR = "system_error"     # 系统错误


class ErrorReport:
    """错误报告类"""

    def __init__(
        self,
        document_id: str,
        error_type: ErrorType,
        message: str,
        details: Optional[str] = None,
        suggestion: Optional[str] = None,
        timestamp: Optional[datetime] = None
    ):
        """
        初始化错误报告

        Args:
            document_id: 文档ID
            error_type: 错误类型
            message: 错误消息
            details: 详细信息
            suggestion: 修复建议
            timestamp: 时间戳
        """
        self.document_id = document_id
        self.error_type = error_type
        self.message = message
        self.details = details or ""
        self.suggestion = suggestion or ""
        self.timestamp = timestamp or datetime.now()

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "document_id": self.document_id,
            "error_type": self.error_type.value,
            "message": self.message,
            "details": self.details,
            "suggestion": self.suggestion,
            "timestamp": self.timestamp.isoformat()
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ErrorReport":
        """从字典创建错误报告"""
        return cls(
            document_id=data["document_id"],
            error_type=ErrorType(data["error_type"]),
            message=data["message"],
            details=data.get("details"),
            suggestion=data.get("suggestion"),
            timestamp=datetime.fromisoformat(data["timestamp"]) if "timestamp" in data else None
        )

    def to_json(self) -> str:
        """转换为JSON字符串"""
        return json.dumps(self.to_dict(), ensure_ascii=False)


class ErrorHandler:
    """错误处理器"""

    def __init__(self, error_dir: Path):
        """
        初始化错误处理器

        Args:
            error_dir: 错误报告存储目录
        """
        self.error_dir = error_dir
        self.error_dir.mkdir(parents=True, exist_ok=True)

        # 错误类型处理函数
        self.type_handlers = {
            ErrorType.FORMAT_ERROR: self._handle_format_error,
            ErrorType.PARSE_ERROR: self._handle_parse_error,
            ErrorType.DATA_ERROR: self._handle_data_error,
            ErrorType.SYSTEM_ERROR: self._handle_system_error
        }

    def handle_error(
        self,
        document_id: str,
        error_type: ErrorType,
        message: str,
        details: Optional[str] = None,
        suggestion: Optional[str] = None
    ) -> ErrorReport:
        """
        处理错误

        Args:
            document_id: 文档ID
            error_type: 错误类型
            message: 错误消息
            details: 详细信息
            suggestion: 修复建议

        Returns:
            错误报告
        """
        # 创建错误报告
        error_report = ErrorReport(
            document_id=document_id,
            error_type=error_type,
            message=message,
            details=details,
            suggestion=suggestion
        )

        # 保存错误报告
        self._save_error_report(error_report)

        # 调用特定错误类型的处理函数
        if error_type in self.type_handlers:
            self.type_handlers[error_type](error_report)

        logger.error(f"错误处理完成: {error_type.value} - {message}")
        return error_report

    def get_error_reports(
        self,
        document_id: Optional[str] = None,
        error_type: Optional[ErrorType] = None,
        limit: int = 100
    ) -> List[ErrorReport]:
        """
        获取错误报告

        Args:
            document_id: 文档ID筛选
            error_type: 错误类型筛选
            limit: 最大返回数量

        Returns:
            错误报告列表
        """
        reports = []

        # 遍历错误报告文件
        for error_file in self.error_dir.glob("error_*.json"):
            try:
                with open(error_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    report = ErrorReport.from_dict(data)

                    # 应用筛选条件
                    if document_id and report.document_id != document_id:
                        continue

                    if error_type and report.error_type != error_type:
                        continue

                    reports.append(report)
            except Exception as e:
                logger.error(f"读取错误报告失败: {str(e)}")
                continue

        # 按时间戳排序
        reports.sort(key=lambda x: x.timestamp, reverse=True)

        # 返回指定数量的报告
        return reports[:limit]

    def clear_error_reports(self, document_id: Optional[str] = None) -> int:
        """
        清除错误报告

        Args:
            document_id: 文档ID，如果为None则清除所有报告

        Returns:
            清除的报告数量
        """
        count = 0

        if document_id:
            # 清除指定文档的错误报告
            for error_file in self.error_dir.glob("error_*.json"):
                try:
                    with open(error_file, "r", encoding="utf-8") as f:
                        data = json.load(f)
                        if data["document_id"] == document_id:
                            error_file.unlink()
                            count += 1
                except Exception as e:
                    logger.error(f"删除错误报告失败: {str(e)}")
                    continue
        else:
            # 清除所有错误报告
            for error_file in self.error_dir.glob("error_*.json"):
                try:
                    error_file.unlink()
                    count += 1
                except Exception as e:
                    logger.error(f"删除错误报告失败: {str(e)}")
                    continue

        logger.info(f"错误报告清除完成: 清除了 {count} 个报告")
        return count

    def _save_error_report(self, report: ErrorReport) -> None:
        """
        保存错误报告

        Args:
            report: 错误报告
        """
        error_file = self.error_dir / f"error_{report.timestamp.strftime('%Y%m%d_%H%M%S')}.json"

        try:
            with open(error_file, "w", encoding="utf-8") as f:
                f.write(report.to_json())
        except Exception as e:
            logger.error(f"保存错误报告失败: {str(e)}")
            raise

    def _handle_format_error(self, report: ErrorReport) -> None:
        """
        处理格式错误

        Args:
            report: 错误报告
        """
        # 格式错误通常与文件格式有关
        logger.warning(f"检测到格式错误: 文档 {report.document_id}")

        # 可以在这里添加特定的格式错误处理逻辑
        # 例如：发送通知、记录到专门的日志等

    def _handle_parse_error(self, report: ErrorReport) -> None:
        """
        处理解析错误

        Args:
            report: 错误报告
        """
        # 解析错误通常与文档内容解析有关
        logger.warning(f"检测到解析错误: 文档 {report.document_id}")

        # 可以在这里添加特定的解析错误处理逻辑

    def _handle_data_error(self, report: ErrorReport) -> None:
        """
        处理数据错误

        Args:
            report: 错误报告
        """
        # 数据错误通常与数据内容有关
        logger.warning(f"检测到数据错误: 文档 {report.document_id}")

        # 可以在这里添加特定的数据错误处理逻辑

    def _handle_system_error(self, report: ErrorReport) -> None:
        """
        处理系统错误

        Args:
            report: 错误报告
        """
        # 系统错误通常与系统环境有关
        logger.error(f"检测到系统错误: 文档 {report.document_id}")

        # 可以在这里添加特定的系统错误处理逻辑
