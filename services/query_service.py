"""
查询服务
"""

import json
import re
import time
from typing import List, Optional, Dict, Any, Union
from datetime import datetime
import logging
from pathlib import Path

from config.settings import settings
from models.knowledge import KnowledgeGraph, Entity, Relation, EntityType, RelationType
from utils.logger import get_logger
from utils.api_utils import DeepSeekClient
from api.client import MockAPIClient

logger = get_logger(__name__)


class QueryService:
    """知识图谱查询服务"""

    def __init__(self, settings, api_client):
        """
        初始化查询服务

        Args:
            settings: 配置对象
            api_client: API客户端
        """
        self.settings = settings
        self.api_client = api_client
        self.data_dir = settings.data_dir

        # 确保目录存在
        self.data_dir.mkdir(parents=True, exist_ok=True)

        # 初始化DeepSeek客户端
        if isinstance(api_client, DeepSeekClient):
            self.llm_client = api_client
        elif isinstance(api_client, MockAPIClient):
            # 使用模拟API客户端进行测试
            self.llm_client = api_client
        else:
            # 实际部署时使用DeepSeekClient
            self.llm_client = DeepSeekClient(settings)

        # 查询历史记录
        self.query_history = []

    def query_by_natural_language(
        self,
        query_text: str,
        kg_ids: Optional[List[str]] = None,
        max_results: int = 10
    ) -> Dict[str, Any]:
        """
        使用自然语言查询知识图谱

        Args:
            query_text: 查询文本
            kg_ids: 知识图谱ID列表，如果为None则查询所有图谱
            max_results: 最大返回结果数

        Returns:
            查询结果
        """
        # 构建Cypher查询
        cypher_query = self._natural_language_to_cypher(query_text)

        # 执行查询
        results = self._execute_cypher_query(cypher_query, kg_ids, max_results)

        # 保存查询历史
        self._save_query_history(query_text, cypher_query, results)

        # 格式化结果
        formatted_results = self._format_query_results(results)

        return {
            "query_text": query_text,
            "cypher_query": cypher_query,
            "results": formatted_results,
            "count": len(formatted_results)
        }

    def query_by_cypher(
        self,
        cypher_query: str,
        kg_ids: Optional[List[str]] = None,
        max_results: int = 10
    ) -> Dict[str, Any]:
        """
        使用Cypher查询知识图谱

        Args:
            cypher_query: Cypher查询语句
            kg_ids: 知识图谱ID列表，如果为None则查询所有图谱
            max_results: 最大返回结果数

        Returns:
            查询结果
        """
        # 执行查询
        results = self._execute_cypher_query(cypher_query, kg_ids, max_results)

        # 格式化结果
        formatted_results = self._format_query_results(results)

        return {
            "cypher_query": cypher_query,
            "results": formatted_results,
            "count": len(formatted_results)
        }

    def find_entity_by_id(self, entity_id: str, kg_ids: Optional[List[str]] = None) -> Optional[Dict[str, Any]]:
        """
        根据ID查找实体

        Args:
            entity_id: 实体ID
            kg_ids: 知识图谱ID列表，如果为None则查询所有图谱

        Returns:
            实体信息，不存在则返回None
        """
        cypher_query = f"MATCH (e) WHERE e.id = '{entity_id}' RETURN e"
        results = self._execute_cypher_query(cypher_query, kg_ids, 1)

        if results and len(results) > 0:
            return results[0]
        return None

    def find_entities_by_type(
        self,
        entity_type: EntityType,
        kg_ids: Optional[List[str]] = None,
        max_results: int = 10
    ) -> List[Dict[str, Any]]:
        """
        根据类型查找实体

        Args:
            entity_type: 实体类型
            kg_ids: 知识图谱ID列表，如果为None则查询所有图谱
            max_results: 最大返回结果数

        Returns:
            实体列表
        """
        cypher_query = f"MATCH (e:{entity_type.value}) RETURN e LIMIT {max_results}"
        results = self._execute_cypher_query(cypher_query, kg_ids, max_results)
        return results

    def find_relations_by_type(
        self,
        relation_type: RelationType,
        kg_ids: Optional[List[str]] = None,
        max_results: int = 10
    ) -> List[Dict[str, Any]]:
        """
        根据类型查找关系

        Args:
            relation_type: 关系类型
            kg_ids: 知识图谱ID列表，如果为None则查询所有图谱
            max_results: 最大返回结果数

        Returns:
            关系列表
        """
        cypher_query = f"MATCH ()-[r:{relation_type.value}]->() RETURN r LIMIT {max_results}"
        results = self._execute_cypher_query(cypher_query, kg_ids, max_results)
        return results

    def find_path_between_entities(
        self,
        source_id: str,
        target_id: str,
        max_depth: int = 3,
        kg_ids: Optional[List[str]] = None
    ) -> List[Dict[str, Any]]:
        """
        查找两个实体之间的路径

        Args:
            source_id: 源实体ID
            target_id: 目标实体ID
            max_depth: 最大路径深度
            kg_ids: 知识图谱ID列表，如果为None则查询所有图谱

        Returns:
            路径列表
        """
        cypher_query = f"""
        MATCH path = shortestPath(
            (e1 {{id: '{source_id}'}})-[*1..{max_depth}]-(e2 {{id: '{target_id}'}})
        )
        RETURN path
        """
        results = self._execute_cypher_query(cypher_query, kg_ids, 10)
        return results

    def get_query_history(self, limit: int = 20) -> List[Dict[str, Any]]:
        """
        获取查询历史

        Args:
            limit: 最大返回数量

        Returns:
            查询历史列表
        """
        return self.query_history[-limit:]

    def clear_query_history(self) -> None:
        """清除查询历史"""
        self.query_history = []
        logger.info("查询历史已清除")

    def _natural_language_to_cypher(self, query_text: str) -> str:
        """
        将自然语言查询转换为Cypher查询

        Args:
            query_text: 查询文本

        Returns:
            Cypher查询语句
        """
        # 构建提示词
        prompt = self._build_cypher_prompt(query_text)

        # 调用大模型
        response = self.llm_client.chat_completion(
            messages=[
                {"role": "system", "content": "你是一个专业的Cypher查询助手，能够将自然语言查询转换为Cypher查询语句。"},
                {"role": "user", "content": prompt}
            ],
            temperature=0.2,
            max_tokens=1000
        )

        # 提取Cypher查询
        result_text = response["choices"][0]["message"]["content"]
        cypher_query = self._extract_cypher_from_response(result_text)

        return cypher_query

    def _build_cypher_prompt(self, query_text: str) -> str:
        """
        构建Cypher转换提示词

        Args:
            query_text: 查询文本

        Returns:
            提示词
        """
        return f"""
请将以下自然语言查询转换为Cypher查询语句：

查询文本：{query_text}

可用的实体类型：
- equipment: 设备
- component: 部件
- procedure: 工序
- standard: 标准
- material: 材料
- condition: 条件
- error: 错误
- cause: 原因
- solution: 解决方案
- maintenance: 维修
- inspection: 检查
- other: 其他

可用的关系类型：
- part_of: 是...的一部分
- used_in: 用于...
- related_to: 与...相关
- causes: 导致
- is_solution_for: 是...的解决方案
- requires: 需要...
- results_in: 导致...
- checked_by: 被...检查
- maintained_by: 被...维护
- follows: 遵循...
- depends_on: 依赖于...

请只返回Cypher查询语句，不要包含其他解释。
"""

    def _extract_cypher_from_response(self, response_text: str) -> str:
        """
        从响应中提取Cypher查询

        Args:
            response_text: 响应文本

        Returns:
            Cypher查询语句
        """
        # 查找Cypher查询开始和结束位置
        import re

        # 尝试匹配MATCH或CREATE语句
        match = re.search(r"(MATCH|CREATE|MERGE|RETURN).*", response_text, re.IGNORECASE)

        if match:
            return match.group(0)

        # 如果没有找到，返回整个响应（可能已经是一个查询）
        return response_text.strip()

    def _execute_cypher_query(
        self,
        cypher_query: str,
        kg_ids: Optional[List[str]] = None,
        max_results: int = 10
    ) -> List[Dict[str, Any]]:
        """
        执行Cypher查询

        Args:
            cypher_query: Cypher查询语句
            kg_ids: 知识图谱ID列表，如果为None则查询所有图谱
            max_results: 最大返回结果数

        Returns:
            查询结果列表
        """
        # 如果没有指定图谱ID，则查询所有图谱
        if kg_ids is None:
            kg_ids = self._get_all_knowledge_graph_ids()

        # 如果没有图谱，返回空结果
        if not kg_ids:
            return []

        # 合并所有图谱的结果
        all_results = []

        for kg_id in kg_ids:
            kg = self._load_knowledge_graph(kg_id)
            if not kg:
                continue

            # 执行查询
            results = self._execute_query_on_graph(kg, cypher_query, max_results)
            all_results.extend(results)

        return all_results[:max_results]

    def _load_knowledge_graph(self, kg_id: str) -> Optional[KnowledgeGraph]:
        """
        加载知识图谱

        Args:
            kg_id: 知识图谱ID

        Returns:
            知识图谱对象，不存在则返回None
        """
        kg_path = self.data_dir / f"kg_{kg_id}.json"

        if not kg_path.exists():
            return None

        try:
            with open(kg_path, 'r', encoding='utf-8') as f:
                data = f.read()
                return KnowledgeGraph.from_dict(data)
        except Exception as e:
            logger.error(f"加载知识图谱失败: {str(e)}")
            return None

    def _execute_query_on_graph(
        self,
        kg: KnowledgeGraph,
        cypher_query: str,
        max_results: int = 10
    ) -> List[Dict[str, Any]]:
        """
        在知识图谱上执行查询

        Args:
            kg: 知识图谱
            cypher_query: Cypher查询语句
            max_results: 最大返回结果数

        Returns:
            查询结果列表
        """
        # 简化实现，实际应用中应该使用Neo4j等图数据库
        # 这里我们解析Cypher查询并在内存中执行

        results = []

        # 解析查询类型
        query_lower = cypher_query.lower()

        # 处理MATCH查询
        if "match" in query_lower:
            # 提取实体类型
            entity_match = re.search(r"match\s*\((\w*):(\w+)", query_lower)
            if entity_match:
                entity_type = entity_match.group(2)

                # 查找匹配的实体
                for entity in kg.entities:
                    if entity.type.value == entity_type:
                        results.append(entity.to_dict())

        # 处理关系查询
        elif "match" in query_lower and "-" in query_lower and ">" in query_lower:
            # 提取关系类型
            relation_match = re.search(r"-\[:([\w]+)\]->", query_lower)
            if relation_match:
                relation_type = relation_match.group(1)

                # 查找匹配的关系
                for relation in kg.relations:
                    if relation.type.value == relation_type:
                        results.append(relation.to_dict())

        # 处理路径查询
        elif "shortestpath" in query_lower or "path" in query_lower:
            # 简化实现，返回所有关系
            results = [r.to_dict() for r in kg.relations]

        return results[:max_results]

    def _get_all_knowledge_graph_ids(self) -> List[str]:
        """
        获取所有知识图谱ID

        Returns:
            知识图谱ID列表
        """
        kg_ids = []

        for file_path in self.data_dir.glob("kg_*.json"):
            # 从文件名中提取ID
            kg_id = file_path.stem.replace("kg_", "")
            kg_ids.append(kg_id)

        return kg_ids

    def _format_query_results(self, results: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        格式化查询结果

        Args:
            results: 原始查询结果

        Returns:
            格式化后的结果
        """
        formatted_results = []

        for result in results:
            # 确定结果类型
            if "type" in result and "name" in result:
                # 实体结果
                formatted_result = {
                    "type": "entity",
                    "id": result.get("id"),
                    "name": result.get("name"),
                    "type_value": result.get("type"),
                    "description": result.get("description"),
                    "properties": result.get("properties", {})
                }
            elif "type" in result and "source" in result and "target" in result:
                # 关系结果
                formatted_result = {
                    "type": "relation",
                    "id": result.get("id"),
                    "type_value": result.get("type"),
                    "source": result.get("source"),
                    "target": result.get("target"),
                    "description": result.get("description"),
                    "properties": result.get("properties", {})
                }
            else:
                # 其他结果
                formatted_result = {
                    "type": "other",
                    "data": result
                }

            formatted_results.append(formatted_result)

        return formatted_results

    def _save_query_history(
        self,
        query_text: str,
        cypher_query: str,
        results: List[Dict[str, Any]]
    ) -> None:
        """
        保存查询历史

        Args:
            query_text: 查询文本
            cypher_query: Cypher查询
            results: 查询结果
        """
        history_entry = {
            "query_text": query_text,
            "cypher_query": cypher_query,
            "result_count": len(results),
            "timestamp": datetime.now().isoformat()
        }

        self.query_history.append(history_entry)

        # 限制历史记录数量
        if len(self.query_history) > 100:
            self.query_history = self.query_history[-100:]
