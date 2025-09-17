"""
用户模型
"""

from typing import Optional, Dict, Any
from datetime import datetime
from pydantic import BaseModel, Field
from utils.time_utils import format_timestamp


class User(BaseModel):
    """用户模型"""

    # 基本字段
    id: str = Field(..., description="用户唯一标识")
    name: str = Field(..., description="用户名称")
    email: Optional[str] = Field(None, description="用户邮箱")
    role: str = Field("user", description="用户角色")

    # 时间字段
    created_at: datetime = Field(default_factory=datetime.now, description="创建时间")
    updated_at: datetime = Field(default_factory=datetime.now, description="更新时间")

    # 扩展字段
    metadata: Dict[str, Any] = Field(default_factory=dict, description="扩展元数据")

    class Config:
        json_encoders = {
            datetime: format_timestamp
        }

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return self.dict()

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "User":
        """从字典创建用户对象"""
        # 处理时间字段
        if "created_at" in data and isinstance(data["created_at"], str):
            data["created_at"] = datetime.fromisoformat(data["created_at"])

        if "updated_at" in data and isinstance(data["updated_at"], str):
            data["updated_at"] = datetime.fromisoformat(data["updated_at"])

        return cls(**data)

    def update(self, **kwargs) -> None:
        """更新用户信息"""
        for key, value in kwargs.items():
            if hasattr(self, key):
                setattr(self, key, value)

        self.updated_at = datetime.now()
