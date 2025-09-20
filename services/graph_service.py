"""
Neo4j 图数据库写入服务
"""

from __future__ import annotations

from typing import Optional
from neo4j import GraphDatabase, Driver

from config.settings import settings as global_settings
from models.knowledge import KnowledgeGraph, Entity, Relation
from utils.logger import get_logger


logger = get_logger(__name__)


class GraphService:
    """负责与 Neo4j 的连接与数据写入。"""

    def __init__(self, settings=global_settings) -> None:
        self.settings = settings
        self._driver: Optional[Driver] = None
        self._driver = GraphDatabase.driver(
            self.settings.neo4j_uri,
            auth=(self.settings.neo4j_username, self.settings.neo4j_password),
        )

    def close(self) -> None:
        if self._driver is not None:
            self._driver.close()

    def write_cypher(self, cypher: str) -> int:
        """执行一段 Cypher 语句（可包含多条 MERGE/CREATE）。

        返回受影响记录的统计（简化为 1 表示成功执行）。
        """
        if not cypher or not cypher.strip():
            return 0

        # 将多个语句分开执行
        statements = self._split_cypher_statements(cypher)
        logger.info("写入 Neo4j: 开始执行 %d 个 Cypher 语句", len(statements))
        
        with self._driver.session() as session:
            for i, statement in enumerate(statements):
                if statement.strip():
                    try:
                        session.run(statement)
                        logger.debug("执行语句 %d/%d 成功", i+1, len(statements))
                    except Exception as e:
                        logger.error("执行语句 %d/%d 失败: %s", i+1, len(statements), str(e))
                        logger.error("失败语句: %s", statement)
                        raise
        
        logger.info("写入 Neo4j: 执行完成")
        return len(statements)

    def _split_cypher_statements(self, cypher: str) -> list[str]:
        """将包含多个语句的Cypher字符串分割为单个语句列表"""
        if not cypher or not cypher.strip():
            return []
        
        # 按分号分割语句
        statements = []
        current_statement = ""
        
        lines = cypher.split('\n')
        for line in lines:
            line = line.strip()
            if not line:
                continue
            
            # 跳过注释行
            if line.startswith('--'):
                continue
                
            current_statement += line + "\n"
            
            # 如果行以分号结尾，说明一个语句结束
            if line.endswith(';'):
                statements.append(current_statement.strip())
                current_statement = ""
        
        # 如果还有未完成的语句，添加它
        if current_statement.strip():
            statements.append(current_statement.strip())
        
        return statements

    def upsert_knowledge_graph(self, kg: KnowledgeGraph) -> int:
        """将 KnowledgeGraph 幂等写入 Neo4j（使用 MERGE）。"""
        statements = []

        # 节点
        for entity in kg.entities:
            label = entity.type.value
            props_pairs = ["id: $id", "name: $name"]
            params = {
                "id": entity.id,
                "name": entity.name,
            }
            for k, v in (entity.properties or {}).items():
                props_pairs.append(f"{k}: ${k}")
                params[k] = v

            props_str = ", ".join(props_pairs)
            stmt = f"MERGE (n:`{label}` {{{props_str}}})"
            statements.append((stmt, params))

        # 关系
        for rel in kg.relations:
            rel_label = rel.type.value
            rel_props_pairs = ["id: $rid"]
            rparams = {
                "sid": rel.source,
                "tid": rel.target,
                "rid": rel.id,
            }
            for k, v in (rel.properties or {}).items():
                rel_props_pairs.append(f"{k}: ${k}")
                rparams[k] = v

            rel_props_str = ", ".join(rel_props_pairs)
            stmt = (
                "MATCH (s {id: $sid}), (t {id: $tid})\n"
                f"MERGE (s)-[r:`{rel_label}` {{{rel_props_str}}}]->(t)"
            )
            statements.append((stmt, rparams))

        # 执行（逐条，保证参数化）
        with self._driver.session() as session:
            for stmt, params in statements:
                session.run(stmt, **params)

        return len(statements)



