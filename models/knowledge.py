"""
知识图谱模型
"""

from typing import Optional, Dict, Any, List, Union
from datetime import datetime
from enum import Enum
from pydantic import BaseModel, Field
from utils.time_utils import format_timestamp
from utils.api_utils import generate_hash


class EntityType(str, Enum):
    """实体类型枚举"""
    EQUIPMENT = "equipment"      # 设备
    COMPONENT = "component"      # 部件
    PROCEDURE = "procedure"      # 工序
    STANDARD = "standard"        # 标准
    MATERIAL = "material"        # 材料
    CONDITION = "condition"      # 条件
    ERROR = "error"              # 错误
    CAUSE = "cause"              # 原因
    SOLUTION = "solution"        # 解决方案
    MAINTENANCE = "maintenance"  # 维修
    INSPECTION = "inspection"    # 检查
    OTHER = "other"              # 其他


class RelationType(str, Enum):
    """关系类型枚举"""
    PART_OF = "part_of"         # 是...的一部分
    USED_IN = "used_in"         # 用于...
    RELATED_TO = "related_to"    # 与...相关
    CAUSES = "causes"           # 导致
    IS_SOLUTION_FOR = "is_solution_for"  # 是...的解决方案
    REQUIRES = "requires"        # 需要...
    RESULTS_IN = "results_in"    # 导致...
    CHECKED_BY = "checked_by"    # 被...检查
    MAINTAINED_BY = "maintained_by"  # 被...维护
    FOLLOWS = "follows"         # 遵循...
    DEPENDS_ON = "depends_on"    # 依赖于...


class Entity(BaseModel):
    """知识图谱实体模型"""

    # 基本字段
    id: str = Field(..., description="实体唯一标识")
    name: str = Field(..., description="实体名称")
    type: EntityType = Field(..., description="实体类型")
    description: Optional[str] = Field(None, description="实体描述")

    # 来源信息
    source_document: Optional[str] = Field(None, description="来源文档ID")
    source_table: Optional[str] = Field(None, description="来源表格")

    # 时间字段
    created_at: datetime = Field(default_factory=datetime.now, description="创建时间")
    updated_at: datetime = Field(default_factory=datetime.now, description="更新时间")

    # 属性
    properties: Dict[str, Any] = Field(default_factory=dict, description="实体属性")

    # 标准化信息
    normalized_name: Optional[str] = Field(None, description="标准化名称")

    class Config:
        json_encoders = {
            datetime: format_timestamp,
            EntityType: lambda v: v.value
        }

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return self.dict()

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Entity":
        """从字典创建实体对象"""
        # 处理时间字段
        if "created_at" in data and isinstance(data["created_at"], str):
            data["created_at"] = datetime.fromisoformat(data["created_at"])

        if "updated_at" in data and isinstance(data["updated_at"], str):
            data["updated_at"] = datetime.fromisoformat(data["updated_at"])

        # 处理类型字段
        if "type" in data and isinstance(data["type"], str):
            data["type"] = EntityType(data["type"])

        return cls(**data)

    def update(self, **kwargs) -> None:
        """更新实体信息"""
        for key, value in kwargs.items():
            if hasattr(self, key):
                setattr(self, key, value)

        self.updated_at = datetime.now()

    def normalize_name(self) -> str:
        """标准化实体名称"""
        if not self.normalized_name:
            # 简单的标准化规则：去除前后空格，转为小写，去除多余空格
            normalized = self.name.strip().lower()
            normalized = " ".join(normalized.split())
            self.normalized_name = normalized
            return normalized
        return self.normalized_name

    def get_hash(self) -> str:
        """获取实体哈希值"""
        # 用于增量更新，基于名称和类型生成稳定ID
        content = f"{self.normalize_name()}_{self.type.value}"
        return generate_hash(content)

    def to_cypher(self) -> str:
        """转换为Cypher创建语句"""
        props = []
        for key, value in self.properties.items():
            if isinstance(value, str):
                props.append(f"{key}: '{value}'")
            else:
                props.append(f"{key}: {value}")

        properties = ", ".join(props)
        if properties:
            properties = f", {properties}"

        return f"CREATE (e:{self.type.value} {{id: '{self.id}', name: '{self.name}'{properties}}})"


class Relation(BaseModel):
    """知识图谱关系模型"""

    # 基本字段
    id: str = Field(..., description="关系唯一标识")
    type: RelationType = Field(..., description="关系类型")
    source: str = Field(..., description="源实体ID")
    target: str = Field(..., description="目标实体ID")

    # 描述信息
    description: Optional[str] = Field(None, description="关系描述")

    # 来源信息
    source_document: Optional[str] = Field(None, description="来源文档ID")
    source_table: Optional[str] = Field(None, description="来源表格")

    # 时间字段
    created_at: datetime = Field(default_factory=datetime.now, description="创建时间")
    updated_at: datetime = Field(default_factory=datetime.now, description="更新时间")

    # 属性
    properties: Dict[str, Any] = Field(default_factory=dict, description="关系属性")

    class Config:
        json_encoders = {
            datetime: format_timestamp,
            RelationType: lambda v: v.value
        }

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return self.dict()

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Relation":
        """从字典创建关系对象"""
        # 处理时间字段
        if "created_at" in data and isinstance(data["created_at"], str):
            data["created_at"] = datetime.fromisoformat(data["created_at"])

        if "updated_at" in data and isinstance(data["updated_at"], str):
            data["updated_at"] = datetime.fromisoformat(data["updated_at"])

        # 处理类型字段
        if "type" in data and isinstance(data["type"], str):
            data["type"] = RelationType(data["type"])

        return cls(**data)

    def update(self, **kwargs) -> None:
        """更新关系信息"""
        for key, value in kwargs.items():
            if hasattr(self, key):
                setattr(self, key, value)

        self.updated_at = datetime.now()

    def to_cypher(self) -> str:
        """转换为Cypher创建语句"""
        props = []
        for key, value in self.properties.items():
            if isinstance(value, str):
                props.append(f"{key}: '{value}'")
            else:
                props.append(f"{key}: {value}")

        properties = ", ".join(props)
        if properties:
            properties = f", {properties}"

        return f"CREATE (e1)-[:{self.type.value} {{id: '{self.id}'{properties}}}]->(e2)"


class KnowledgeGraph(BaseModel):
    """知识图谱模型"""

    # 基本字段
    id: str = Field(..., description="图谱唯一标识")
    name: str = Field(..., description="图谱名称")
    description: Optional[str] = Field(None, description="图谱描述")

    # 时间字段
    created_at: datetime = Field(default_factory=datetime.now, description="创建时间")
    updated_at: datetime = Field(default_factory=datetime.now, description="更新时间")

    # 实体和关系
    entities: List[Entity] = Field(default_factory=list, description="实体列表")
    relations: List[Relation] = Field(default_factory=list, description="关系列表")

    # 元数据
    metadata: Dict[str, Any] = Field(default_factory=dict, description="扩展元数据")

    class Config:
        json_encoders = {
            datetime: format_timestamp
        }

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return self.dict()

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "KnowledgeGraph":
        """从字典创建知识图谱对象"""
        # 处理时间字段
        if "created_at" in data and isinstance(data["created_at"], str):
            data["created_at"] = datetime.fromisoformat(data["created_at"])

        if "updated_at" in data and isinstance(data["updated_at"], str):
            data["updated_at"] = datetime.fromisoformat(data["updated_at"])

        # 处理实体和关系
        if "entities" in data and isinstance(data["entities"], list):
            data["entities"] = [Entity.from_dict(e) for e in data["entities"]]

        if "relations" in data and isinstance(data["relations"], list):
            data["relations"] = [Relation.from_dict(r) for r in data["relations"]]

        return cls(**data)

    def add_entity(self, entity: Entity) -> None:
        """添加实体"""
        self.entities.append(entity)
        self.updated_at = datetime.now()

    def add_relation(self, relation: Relation) -> None:
        """添加关系"""
        self.relations.append(relation)
        self.updated_at = datetime.now()

    def get_entity_by_id(self, entity_id: str) -> Optional[Entity]:
        """根据ID获取实体"""
        for entity in self.entities:
            if entity.id == entity_id:
                return entity
        return None

    def get_relations_by_entity(self, entity_id: str) -> List[Relation]:
        """获取与指定实体相关的所有关系"""
        relations = []
        for relation in self.relations:
            if relation.source == entity_id or relation.target == entity_id:
                relations.append(relation)
        return relations

    def get_entities_by_type(self, entity_type: EntityType) -> List[Entity]:
        """根据类型获取实体"""
        return [e for e in self.entities if e.type == entity_type]

    def get_relations_by_type(self, relation_type: RelationType) -> List[Relation]:
        """根据类型获取关系"""
        return [r for r in self.relations if r.type == relation_type]

    def to_cypher(self) -> str:
        """转换为Cypher创建语句"""
        statements = []

        # 添加实体
        for entity in self.entities:
            statements.append(entity.to_cypher())

        # 添加关系
        for relation in self.relations:
            statements.append(relation.to_cypher())

        return "".join(statements)

    def merge_with(
        self, 
        other: "KnowledgeGraph", 
        merge_entities: bool = True, 
        merge_relations: bool = True
    ) -> "KnowledgeGraph":
        """
        与另一个知识图谱合并

        Args:
            other: 另一个知识图谱
            merge_entities: 是否合并实体
            merge_relations: 是否合并关系

        Returns:
            合并后的知识图谱
        """
        # 创建新图谱的副本
        merged = KnowledgeGraph(
            id=self.id,
            name=self.name,
            description=self.description,
            entities=self.entities.copy(),
            relations=self.relations.copy(),
            metadata=self.metadata.copy()
        )

        # 处理实体合并
        if merge_entities:
            entity_map = {}  # 用于映射实体ID

            for entity in other.entities:
                # 检查是否已存在相同名称和类型的实体
                found = None
                for e in merged.entities:
                    if e.normalize_name() == entity.normalize_name() and e.type == entity.type:
                        found = e
                        break

                if found:
                    # 更新现有实体
                    found.update(
                        description=entity.description or found.description,
                        properties={**found.properties, **entity.properties},
                        source_document=entity.source_document or found.source_document,
                        source_table=entity.source_table or found.source_table
                    )
                    entity_map[entity.id] = found.id
                else:
                    # 添加新实体
                    merged.add_entity(entity)
                    entity_map[entity.id] = entity.id

            # 处理关系合并
            if merge_relations:
                for relation in other.relations:
                    # 更新关系中的实体ID
                    new_source = entity_map.get(relation.source, relation.source)
                    new_target = entity_map.get(relation.target, relation.target)

                    # 检查关系是否已存在
                    exists = False
                    for r in merged.relations:
                        if (r.type == relation.type and 
                            r.source == new_source and 
                            r.target == new_target):
                            exists = True
                            break

                    if not exists:
                        # 创建新关系
                        new_relation = Relation(
                            id=relation.id,
                            type=relation.type,
                            source=new_source,
                            target=new_target,
                            description=relation.description,
                            properties=relation.properties.copy(),
                            source_document=relation.source_document,
                            source_table=relation.source_table
                        )
                        merged.add_relation(new_relation)

        return merged
