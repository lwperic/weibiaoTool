"""
文档模型
"""
import hashlib
from typing import Optional, Dict, Any, List, Union
from datetime import datetime
from enum import Enum
from pathlib import Path
from pydantic import BaseModel, Field
from utils.time_utils import format_timestamp
from utils.api_utils import generate_hash


class DocumentStatus(str, Enum):
    """文档状态枚举"""
    PENDING = "pending"      # 待处理
    PROCESSING = "processing"  # 处理中
    COMPLETED = "completed"   # 已完成
    ERROR = "error"          # 处理错误
    DELETED = "deleted"      # 已删除


class Document(BaseModel):
    """文档模型"""

    # 基本字段
    id: str = Field(..., description="文档唯一标识")
    name: str = Field(..., description="文档名称")
    original_name: str = Field(..., description="原始文档名称")
    file_path: str = Field(..., description="文件路径")
    file_size: int = Field(..., description="文件大小(字节)")
    file_hash: str = Field(..., description="文件哈希值")

    # 处理状态
    status: DocumentStatus = Field(DocumentStatus.PENDING, description="处理状态")
    error_message: Optional[str] = Field(None, description="错误信息")

    # 时间字段
    created_at: datetime = Field(default_factory=datetime.now, description="创建时间")
    updated_at: datetime = Field(default_factory=datetime.now, description="更新时间")
    processed_at: Optional[datetime] = Field(None, description="处理完成时间")

    # 处理结果
    extracted_entities: Optional[List[Dict[str, Any]]] = Field(None, description="抽取的实体")
    extracted_relations: Optional[List[Dict[str, Any]]] = Field(None, description="抽取的关系")
    processing_time: Optional[float] = Field(None, description="处理耗时(秒)")

    # 扩展字段
    metadata: Dict[str, Any] = Field(default_factory=dict, description="扩展元数据")

    class Config:
        json_encoders = {
            datetime: format_timestamp,
            DocumentStatus: lambda v: v.value
        }

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return self.dict()

    @classmethod
    def from_dict(cls, data: Union[str, Dict[str, Any]]) -> "Document":
        """从字典或JSON字符串创建文档对象"""
        # 如果data是字符串，先解析为字典
        if isinstance(data, str):
            try:
                import json
                data = json.loads(data)
            except json.JSONDecodeError as e:
                raise ValueError(f"无法解析JSON数据: {str(e)}")

        # 确保data是字典类型
        if not isinstance(data, dict):
            raise ValueError("数据必须是字典或可解析为字典的JSON字符串")

        # 处理时间字段
        if "created_at" in data and isinstance(data["created_at"], str):
            data["created_at"] = datetime.fromisoformat(data["created_at"])

        if "updated_at" in data and isinstance(data["updated_at"], str):
            data["updated_at"] = datetime.fromisoformat(data["updated_at"])

        if "processed_at" in data and isinstance(data["processed_at"], str):
            data["processed_at"] = datetime.fromisoformat(data["processed_at"])

        # 处理状态字段
        if "status" in data and isinstance(data["status"], str):
            data["status"] = DocumentStatus(data["status"])

        return cls(**data)

    def update_status(self, status: DocumentStatus, error_message: Optional[str] = None) -> None:
        """更新文档状态"""
        self.status = status
        self.updated_at = datetime.now()

        if status == DocumentStatus.COMPLETED:
            self.processed_at = datetime.now()

        if error_message:
            self.error_message = error_message

    def update_processing_result(
        self,
        entities: Optional[List[Dict[str, Any]]] = None,
        relations: Optional[List[Dict[str, Any]]] = None,
        processing_time: Optional[float] = None
    ) -> None:
        """更新处理结果"""
        if entities is not None:
            self.extracted_entities = entities

        if relations is not None:
            self.extracted_relations = relations

        if processing_time is not None:
            self.processing_time = processing_time

        self.updated_at = datetime.now()

    @classmethod
    def create_from_file(cls, file_path: Path, metadata: Optional[Dict[str, Any]] = None) -> "Document":
        """从文件创建文档对象"""
        # 计算文件哈希
        file_hash = generate_hash(file_path.read_bytes())

        # 创建文档对象
        return cls(
            id=f"doc_{file_hash}",
            name=file_path.stem,
            original_name=file_path.name,
            file_path=str(file_path),
            file_size=file_path.stat().st_size,
            file_hash=file_hash,
            metadata=metadata or {}
        )

    def get_file_extension(self) -> str:
        """获取文件扩展名"""
        return Path(self.file_path).suffix.lower()

    def is_valid_document(self) -> bool:
        """检查文档是否有效"""
        # 检查文件是否存在
        if not Path(self.file_path).exists():
            return False

        # 检查文件哈希是否匹配
        current_hash = generate_hash(Path(self.file_path).read_bytes())
        if current_hash != self.file_hash:
            return False

        return True

    # models/document.py
    @classmethod
    def _calculate_file_hash(cls, file_path: Path) -> str:
        """
        计算文件哈希值
        Args:
            file_path: 文件路径

        Returns:
            文件哈希值
        """
        sha256 = hashlib.sha256()
        with open(file_path, 'rb') as f:
            while chunk := f.read(4096):
                sha256.update(chunk)  # 直接更新二进制数据，不需要编码
        return sha256.hexdigest()
