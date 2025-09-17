"""
处理状态管理
"""

from enum import Enum
from typing import Dict, Any, List, Optional
from datetime import datetime
import json
import logging
from pathlib import Path

from utils.logger import get_logger

logger = get_logger(__name__)


class ProcessingStatus(str, Enum):
    """处理状态枚举"""
    PENDING = "pending"      # 待处理
    PROCESSING = "processing"  # 处理中
    COMPLETED = "completed"   # 已完成
    ERROR = "error"          # 夙愿
    PAUSED = "paused"        # 已暂停


class ProcessingTask:
    """处理任务"""

    def __init__(
        self,
        task_id: str,
        document_ids: List[str],
        task_type: str,
        config: Dict[str, Any],
        created_by: str = "system"
    ):
        """
        初始化处理任务

        Args:
            task_id: 任务ID
            document_ids: 文档ID列表
            task_type: 任务类型
            config: 任务配置
            created_by: 创建者
        """
        self.task_id = task_id
        self.document_ids = document_ids
        self.task_type = task_type
        self.config = config
        self.created_by = created_by

        # 时间字段
        self.created_at = datetime.now()
        self.updated_at = datetime.now()
        self.started_at: Optional[datetime] = None
        self.completed_at: Optional[datetime] = None

        # 状态字段
        self.status = ProcessingStatus.PENDING
        self.progress = 0.0  # 进度 0.0-1.0
        self.current_document: Optional[str] = None
        self.error_message: Optional[str] = None

        # 结果统计
        self.success_count = 0
        self.error_count = 0
        self.skipped_count = 0

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "task_id": self.task_id,
            "document_ids": self.document_ids,
            "task_type": self.task_type,
            "config": self.config,
            "created_by": self.created_by,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "status": self.status.value,
            "progress": self.progress,
            "current_document": self.current_document,
            "error_message": self.error_message,
            "success_count": self.success_count,
            "error_count": self.error_count,
            "skipped_count": self.skipped_count
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ProcessingTask":
        """从字典创建任务"""
        task = cls(
            task_id=data["task_id"],
            document_ids=data["document_ids"],
            task_type=data["task_type"],
            config=data["config"],
            created_by=data.get("created_by", "system")
        )

        # 处理时间字段
        if "created_at" in data:
            task.created_at = datetime.fromisoformat(data["created_at"])

        if "updated_at" in data:
            task.updated_at = datetime.fromisoformat(data["updated_at"])

        if "started_at" in data:
            task.started_at = datetime.fromisoformat(data["started_at"])

        if "completed_at" in data:
            task.completed_at = datetime.fromisoformat(data["completed_at"])

        # 处理状态字段
        if "status" in data:
            task.status = ProcessingStatus(data["status"])

        # 处理其他字段
        task.progress = data.get("progress", 0.0)
        task.current_document = data.get("current_document")
        task.error_message = data.get("error_message")
        task.success_count = data.get("success_count", 0)
        task.error_count = data.get("error_count", 0)
        task.skipped_count = data.get("skipped_count", 0)

        return task

    def update_status(
        self,
        status: ProcessingStatus,
        error_message: Optional[str] = None,
        current_document: Optional[str] = None
    ) -> None:
        """
        更新任务状态

        Args:
            status: 新状态
            error_message: 错误信息
            current_document: 当前处理的文档
        """
        self.status = status
        self.updated_at = datetime.now()

        if error_message:
            self.error_message = error_message

        if current_document:
            self.current_document = current_document

        # 更新特定状态的时间戳
        if status == ProcessingStatus.PROCESSING and not self.started_at:
            self.started_at = datetime.now()

        if status in [ProcessingStatus.COMPLETED, ProcessingStatus.ERROR]:
            self.completed_at = datetime.now()
            self.current_document = None

    def update_progress(self, progress: float, current_document: Optional[str] = None) -> None:
        """
        更新任务进度

        Args:
            progress: 进度值 (0.0-1.0)
            current_document: 当前处理的文档
        """
        self.progress = max(0.0, min(1.0, progress))
        self.updated_at = datetime.now()

        if current_document:
            self.current_document = current_document

    def update_result_counts(
        self,
        success_count: int = 0,
        error_count: int = 0,
        skipped_count: int = 0
    ) -> None:
        """
        更新结果统计

        Args:
            success_count: 成功数量
            error_count: 错误数量
            skipped_count: 跳过数量
        """
        self.success_count += success_count
        self.error_count += error_count
        self.skipped_count += skipped_count
        self.updated_at = datetime.now()


class ProcessingStatusManager:
    """处理状态管理器"""

    def __init__(self, status_dir: str):
        """
        初始化状态管理器

        Args:
            status_dir: 状态文件目录
        """
        self.status_dir = Path(status_dir)
        self.status_dir.mkdir(parents=True, exist_ok=True)

        # 任务字典
        self.tasks: Dict[str, ProcessingTask] = {}

        # 加载现有任务
        self._load_tasks()

    def _load_tasks(self) -> None:
        """加载任务状态"""
        for task_file in self.status_dir.glob("task_*.json"):
            try:
                with open(task_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    task = ProcessingTask.from_dict(data)
                    self.tasks[task.task_id] = task
            except Exception as e:
                logger.error(f"加载任务状态失败: {str(e)}")
                continue

    def _save_task(self, task: ProcessingTask) -> None:
        """
        保存任务状态

        Args:
            task: 任务对象
        """
        task_file = self.status_dir / f"task_{task.task_id}.json"

        try:
            with open(task_file, "w", encoding="utf-8") as f:
                json.dump(task.to_dict(), f, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.error(f"保存任务状态失败: {str(e)}")
            raise

    def create_task(
        self,
        document_ids: List[str],
        task_type: str,
        config: Dict[str, Any],
        created_by: str = "system"
    ) -> str:
        """
        创建处理任务

        Args:
            document_ids: 文档ID列表
            task_type: 任务类型
            config: 任务配置
            created_by: 创建者

        Returns:
            任务ID
        """
        import uuid
        task_id = str(uuid.uuid4())

        # 创建任务
        task = ProcessingTask(
            task_id=task_id,
            document_ids=document_ids,
            task_type=task_type,
            config=config,
            created_by=created_by
        )

        # 保存任务
        self.tasks[task_id] = task
        self._save_task(task)

        logger.info(f"创建处理任务: {task_id}")
        return task_id

    def get_task(self, task_id: str) -> Optional[ProcessingTask]:
        """
        获取任务

        Args:
            task_id: 任务ID

        Returns:
            任务对象，不存在则返回None
        """
        return self.tasks.get(task_id)

    def list_tasks(
        self,
        task_type: Optional[str] = None,
        status: Optional[ProcessingStatus] = None,
        limit: int = 100
    ) -> List[ProcessingTask]:
        """
        列出任务

        Args:
            task_type: 任务类型筛选
            status: 状态筛选
            limit: 最大返回数量

        Returns:
            任务列表
        """
        tasks = []

        for task in self.tasks.values():
            # 应用筛选条件
            if task_type and task.task_type != task_type:
                continue

            if status and task.status != status:
                continue

            tasks.append(task)

        # 按创建时间排序
        tasks.sort(key=lambda x: x.created_at, reverse=True)

        # 返回指定数量的任务
        return tasks[:limit]

    def update_task_status(
        self,
        task_id: str,
        status: ProcessingStatus,
        error_message: Optional[str] = None,
        current_document: Optional[str] = None
    ) -> bool:
        """
        更新任务状态

        Args:
            task_id: 任务ID
            status: 新状态
            error_message: 错误信息
            current_document: 当前处理的文档

        Returns:
            是否成功
        """
        task = self.get_task(task_id)
        if not task:
            return False

        # 更新状态
        task.update_status(status, error_message, current_document)

        # 保存更新
        self._save_task(task)

        logger.info(f"任务状态更新: {task_id} - {status.value}")
        return True

    def update_task_progress(
        self,
        task_id: str,
        progress: float,
        current_document: Optional[str] = None
    ) -> bool:
        """
        更新任务进度

        Args:
            task_id: 任务ID
            progress: 进度值 (0.0-1.0)
            current_document: 当前处理的文档

        Returns:
            是否成功
        """
        task = self.get_task(task_id)
        if not task:
            return False

        # 更新进度
        task.update_progress(progress, current_document)

        # 保存更新
        self._save_task(task)

        return True

    def update_task_result_counts(
        self,
        task_id: str,
        success_count: int = 0,
        error_count: int = 0,
        skipped_count: int = 0
    ) -> bool:
        """
        更新任务结果统计

        Args:
            task_id: 任务ID
            success_count: 成功数量
            error_count: 错误数量
            skipped_count: 跳过数量

        Returns:
            是否成功
        """
        task = self.get_task(task_id)
        if not task:
            return False

        # 更新结果统计
        task.update_result_counts(success_count, error_count, skipped_count)

        # 保存更新
        self._save_task(task)

        return True

    def delete_task(self, task_id: str) -> bool:
        """
        删除任务

        Args:
            task_id: 任务ID

        Returns:
            是否成功
        """
        if task_id not in self.tasks:
            return False

        # 删除任务文件
        task_file = self.status_dir / f"task_{task_id}.json"
        try:
            task_file.unlink()
        except Exception as e:
            logger.error(f"删除任务文件失败: {str(e)}")

        # 从字典中删除
        del self.tasks[task_id]

        logger.info(f"任务已删除: {task_id}")
        return True

    def get_processing_queue(self) -> List[ProcessingTask]:
        """
        获取处理队列

        Returns:
            处理队列中的任务列表
        """
        return [
            task for task in self.tasks.values()
            if task.status == ProcessingStatus.PENDING
        ]

    def get_active_tasks(self) -> List[ProcessingTask]:
        """
        获取活动任务

        Returns:
            活动任务列表
        """
        return [
            task for task in self.tasks.values()
            if task.status == ProcessingStatus.PROCESSING
        ]

    def clear_completed_tasks(self, days: int = 7) -> int:
        """
        清除已完成的任务

        Args:
            days: 保留天数

        Returns:
            清除的任务数量
        """
        count = 0
        cutoff_date = datetime.now().timestamp() - (days * 24 * 60 * 60)

        for task_id, task in list(self.tasks.items()):
            # 检查是否是已完成任务且超过保留天数
            if (task.status in [ProcessingStatus.COMPLETED, ProcessingStatus.ERROR] and
                task.completed_at and task.completed_at.timestamp() < cutoff_date):

                # 删除任务
                if self.delete_task(task_id):
                    count += 1

        logger.info(f"清除已完成任务: {count} 个")
        return count
