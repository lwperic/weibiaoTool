"""
知识图谱服务
"""

import json
import time
from typing import List, Optional, Dict, Any, Union
from datetime import datetime
import logging
from pathlib import Path

from config.settings import settings
from models.document import Document, DocumentStatus
from models.knowledge import KnowledgeGraph, Entity, Relation, EntityType, RelationType
from utils.logger import get_logger
from utils.api_utils import DeepSeekClient
from api.client import MockAPIClient

logger = get_logger(__name__)


class KnowledgeService:
    """知识图谱服务"""

    def __init__(self, settings, api_client):
        """
        初始化知识图谱服务

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

    def extract_knowledge_from_document(
        self,
        document: Document,
        timeout: Optional[int] = None
    ) -> KnowledgeGraph:
        """
        从文档中抽取知识

        Args:
            document: 文档对象
            timeout: 超时时间（秒）

        Returns:
            抽取的知识图谱
        """
        if timeout is None:
            timeout = self.settings.default_timeout

        # 更新文档状态为处理中
        document.update_status(DocumentStatus.PROCESSING)
        self._save_document(document)

        try:
            # 读取文档内容
            content = self._read_document_content(document)

            # 使用大模型抽取知识
            kg = self._extract_knowledge_with_llm(content, document.id)

            # 更新文档状态为已完成
            document.update_status(DocumentStatus.COMPLETED)
            document.update_processing_result(
                entities=[e.to_dict() for e in kg.entities],
                relations=[r.to_dict() for r in kg.relations],
                processing_time=time.time() - document.updated_at.timestamp()
            )

            # 保存文档更新
            self._save_document(document)

            logger.info(f"知识抽取完成: {document.name}")
            return kg

        except Exception as e:
            # 更新文档状态为错误
            document.update_status(DocumentStatus.ERROR, str(e))
            self._save_document(document)

            logger.error(f"知识抽取失败: {document.name} - {str(e)}")
            raise

    def extract_knowledge_from_documents(
        self,
        document_ids: List[str],
        concurrency: int = None,
        timeout: Optional[int] = None
    ) -> Dict[str, KnowledgeGraph]:
        """
        从多个文档中批量抽取知识

        Args:
            document_ids: 文档ID列表
            concurrency: 并发数量
            timeout: 超时时间（秒）

        Returns:
            文档ID到知识图谱的映射
        """
        if concurrency is None:
            concurrency = self.settings.max_concurrency

        if timeout is None:
            timeout = self.settings.default_timeout

        results = {}
        failed = []

        # 获取文档对象
        documents = []
        for doc_id in document_ids:
            doc = self._get_document(doc_id)
            if doc:
                documents.append(doc)
            else:
                logger.error(f"文档不存在: {doc_id}")
                failed.append(doc_id)

        # 批量处理文档
        from concurrent.futures import ThreadPoolExecutor, as_completed

        with ThreadPoolExecutor(max_workers=concurrency) as executor:
            # 提交任务
            futures = {
                executor.submit(self.extract_knowledge_from_document, doc, timeout): doc.id
                for doc in documents
            }

            # 收集结果
            for future in as_completed(futures):
                doc_id = futures[future]
                try:
                    kg = future.result()
                    results[doc_id] = kg
                except Exception as e:
                    logger.error(f"文档处理失败: {doc_id} - {str(e)}")
                    failed.append(doc_id)

        logger.info(f"批量处理完成: 成功 {len(results)}, 失败 {len(failed)}")
        return results

    def save_knowledge_graph(self, kg: KnowledgeGraph) -> None:
        """
        保存知识图谱

        Args:
            kg: 知识图谱
        """
        kg_path = self.data_dir / f"kg_{kg.id}.json"

        try:
            with open(kg_path, 'w', encoding='utf-8') as f:
                f.write(kg.json())

            logger.info(f"知识图谱保存成功: {kg.name}")
        except Exception as e:
            logger.error(f"保存知识图谱失败: {str(e)}")
            raise

    def load_knowledge_graph(self, kg_id: str) -> Optional[KnowledgeGraph]:
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

    def merge_knowledge_graphs(
        self,
        kg_ids: List[str],
        merge_entities: bool = True,
        merge_relations: bool = True
    ) -> Optional[KnowledgeGraph]:
        """
        合并多个知识图谱

        Args:
            kg_ids: 知识图谱ID列表
            merge_entities: 是否合并实体
            merge_relations: 是否合并关系

        Returns:
            合并后的知识图谱，失败则返回None
        """
        # 加载所有知识图谱
        kgs = []
        for kg_id in kg_ids:
            kg = self.load_knowledge_graph(kg_id)
            if kg:
                kgs.append(kg)

        if not kgs:
            return None

        # 合并知识图谱
        merged = kgs[0]
        for kg in kgs[1:]:
            merged = merged.merge_with(kg, merge_entities, merge_relations)

        # 保存合并后的知识图谱
        merged.id = f"merged_{int(time.time())}"
        merged.name = f"合并图谱_{len(kgs)}个"
        merged.updated_at = datetime.now()

        self.save_knowledge_graph(merged)
        logger.info(f"知识图谱合并完成: {merged.name}")

        return merged

    def _read_document_content(self, document: Document) -> str:
        """
        读取文档内容

        Args:
            document: 文档对象

        Returns:
            文档内容
        """
        file_path = Path(document.file_path)
        if not file_path.exists():
            raise ValueError(f"文档文件不存在: {file_path}")

        try:
            # 统一通过工具读取文本（兼容 .doc/.docx）
            from utils.word_reader import read_word_text

            text = read_word_text(file_path)
            return text
        except Exception as e:
            logger.error(f"读取文档内容失败: {str(e)}")
            raise

    def _extract_knowledge_with_llm(self, content: str, source_doc_id: str) -> KnowledgeGraph:
        """
        使用大模型从内容中抽取知识

        Args:
            content: 文档内容
            source_doc_id: 来源文档ID

        Returns:
            抽取的知识图谱
        """
        # 构建提示词
        prompt = self._build_extraction_prompt(content)

        # 调用大模型
        try:
            response = self.llm_client.chat_completion(
                messages=[
                    {"role": "system", "content": "你是一个专业的知识图谱工程师，擅长从非结构化文本中抽取结构化信息，并转换为 Neo4j 图数据库的 Cypher 查询语言。"},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.2,
                max_tokens=4000
            )
        except Exception as e:
            logger.error(f"大模型调用失败: {str(e)}")
            # 这里不能直接更新文档状态，因为document变量不在这个方法的参数中
            # 返回一个空的知识图谱
            return KnowledgeGraph(
                id=f"error_{source_doc_id}",
                name=f"Error Knowledge Graph for {source_doc_id}",
                entities=[],
                relations=[],
                metadata={"error": f"大模型调用失败: {str(e)}"}
            )

        # 解析响应
        try:
            result_text = response["choices"][0]["message"]["content"]
            # 确保文本是UTF-8编码
            if isinstance(result_text, str):
                result_text = result_text.encode('utf-8', errors='ignore').decode('utf-8')
            kg_data = self._parse_llm_response(result_text)
        except (KeyError, IndexError, UnicodeError) as e:
            logger.error(f"解析大模型响应失败: {str(e)}")
            # 返回一个空的知识图谱
            return KnowledgeGraph(
                id=f"error_{source_doc_id}",
                name=f"Error Knowledge Graph for {source_doc_id}",
                entities=[],
                relations=[],
                metadata={"error": f"解析响应失败: {str(e)}"}
            )

        # 处理新格式的关系数据（from/to -> source/target）
        relations_data = []
        for rel in kg_data.get("relations", []):
            if "from" in rel and "to" in rel:
                # 新格式：使用from/to
                # 映射关系类型
                relation_type = self._map_relation_type(rel.get("type", "other"))
                relations_data.append({
                    "id": rel.get("id", f"{rel['from']}-{rel['to']}-{rel['type']}"),
                    "source": rel["from"],
                    "target": rel["to"],
                    "type": relation_type,
                    "description": rel.get("description", ""),
                    "properties": rel.get("properties", {})
                })
            else:
                # 旧格式：直接使用source/target
                # 映射关系类型
                if "type" in rel:
                    rel["type"] = self._map_relation_type(rel["type"])
                relations_data.append(rel)

        # 处理实体类型映射
        entities_data = []
        for entity in kg_data.get("entities", []):
            # 映射实体类型
            entity_type = self._map_entity_type(entity.get("type", "other"))
            entity["type"] = entity_type
            entities_data.append(entity)

        # 创建知识图谱
        kg = KnowledgeGraph(
            id=f"kg_{source_doc_id}_{int(time.time())}",
            name=f"知识图谱_{source_doc_id}",
            description=f"从文档 {source_doc_id} 中抽取的知识",
            entities=[Entity.from_dict(e) for e in entities_data],
            relations=[Relation.from_dict(r) for r in relations_data],
            metadata={
                "source_document": source_doc_id,
                "cypher_statements": kg_data.get("cypher_statements", [])
            }
        )

        return kg

    def _map_entity_type(self, entity_type: str) -> str:
        """
        映射实体类型到预定义的类型

        Args:
            entity_type: 原始实体类型

        Returns:
            映射后的实体类型
        """
        # 类型映射字典
        type_mapping = {
            # 人员相关
            "person": "person",
            "people": "person",
            "worker": "person",
            "operator": "person",
            "technician": "person",
            "engineer": "person",
            # 首字母大写变体
            "Person": "person",
            "People": "person",
            "Worker": "person",
            "Operator": "person",
            "Technician": "person",
            "Engineer": "person",
            
            # 工具相关
            "tool": "tool",
            "tools": "tool",
            "instrument": "tool",
            "device": "tool",
            "equipment": "equipment",
            # 首字母大写变体
            "Tool": "tool",
            "Tools": "tool",
            "Instrument": "tool",
            "Device": "tool",
            "Equipment": "equipment",
            
            # 设备相关
            "machine": "equipment",
            "motor": "equipment",
            "pump": "equipment",
            "valve": "equipment",
            "belt": "equipment",
            "conveyor": "equipment",
            # 首字母大写变体
            "Machine": "equipment",
            "Motor": "equipment",
            "Pump": "equipment",
            "Valve": "equipment",
            "Belt": "equipment",
            "Conveyor": "equipment",
            
            # 部件相关
            "component": "component",
            "part": "component",
            "assembly": "component",
            # 首字母大写变体
            "Component": "component",
            "Part": "component",
            "Assembly": "component",
            
            # 工序相关
            "procedure": "procedure",
            "process": "procedure",
            "operation": "procedure",
            "step": "procedure",
            # 首字母大写变体
            "Procedure": "procedure",
            "Process": "procedure",
            "Operation": "procedure",
            "Step": "procedure",
            
            # 材料相关
            "material": "material",
            "substance": "material",
            "oil": "material",
            "lubricant": "material",
            # 首字母大写变体
            "Material": "material",
            "Substance": "material",
            "Oil": "material",
            "Lubricant": "material",
            
            # 位置相关
            "location": "location",
            "place": "location",
            "position": "location",
            "site": "location",
            # 首字母大写变体
            "Location": "location",
            "Place": "location",
            "Position": "location",
            "Site": "location",
            
            # 时间相关
            "time": "time",
            "date": "time",
            "period": "time",
            "duration": "time",
            # 首字母大写变体
            "Time": "time",
            "Date": "time",
            "Period": "time",
            "Duration": "time",
            
            # 其他
            "other": "other",
            "unknown": "other",
            # 首字母大写变体
            "Other": "other",
            "Unknown": "other"
        }
        
        # 首先尝试直接映射（支持大小写变体）
        if entity_type in type_mapping:
            return type_mapping[entity_type]
        
        # 转换为小写并查找映射
        normalized_type = entity_type.lower().strip()
        if normalized_type in type_mapping:
            return type_mapping[normalized_type]
        
        # 如果直接映射失败，尝试一些常见的变体
        # 处理首字母大写的情况
        if entity_type.capitalize() in ["Person", "Tool", "Equipment", "Component", "Procedure", "Standard", "Material", "Condition", "Error", "Cause", "Solution", "Maintenance", "Inspection", "Location", "Time"]:
            return normalized_type
        
        # 如果都不匹配，返回other
        return "other"

    def _map_relation_type(self, relation_type: str) -> str:
        """
        映射关系类型到预定义的类型

        Args:
            relation_type: 原始关系类型

        Returns:
            映射后的关系类型
        """
        # 关系类型映射字典
        type_mapping = {
            # 基本关系
            "part_of": "part_of",
            "used_in": "used_in",
            "related_to": "related_to",
            "causes": "causes",
            "is_solution_for": "is_solution_for",
            "requires": "requires",
            "results_in": "results_in",
            "checked_by": "checked_by",
            "maintained_by": "maintained_by",
            "follows": "follows",
            "depends_on": "depends_on",
            
            # 新增关系类型
            "compiled_by": "compiled_by",
            "compiled": "compiled_by",  # 处理COMPILED
            "created_by": "created_by",
            "created": "created_by",
            "operated_by": "operated_by",
            "operated": "operated_by",
            "located_in": "located_in",
            "located": "located_in",
            "contains": "contains",
            "belongs_to": "belongs_to",
            "belongs": "belongs_to",
            "connects_to": "connects_to",
            "connects": "connects_to",
            "replaces": "replaces",
            "improves": "improves",
            "prevents": "prevents",
            
            # 其他
            "other": "other",
            "unknown": "other"
        }
        
        # 转换为小写并查找映射
        normalized_type = relation_type.lower().strip()
        
        # 首先尝试直接映射
        if normalized_type in type_mapping:
            return type_mapping[normalized_type]
        
        # 如果直接映射失败，尝试一些常见的变体
        # 处理首字母大写的情况
        if relation_type.upper() in ["COMPILED", "CREATED", "OPERATED", "LOCATED", "BELONGS", "CONNECTS"]:
            return normalized_type + "_by" if relation_type.upper() in ["COMPILED", "CREATED", "OPERATED"] else normalized_type
        
        # 如果都不匹配，返回other
        return "other"

    def _build_extraction_prompt(self, content: str) -> str:
        """
        构建知识抽取提示词

        Args:
            content: 文档内容

        Returns:
            提示词
        """
        return f"""# 角色与任务
你是一个专业的知识图谱工程师，擅长从非结构化文本中抽取结构化信息，并转换为 Neo4j 图数据库的 Cypher 查询语言。

## 背景与目标
我将提供一段文本内容，你的任务是：
1.  **精确地抽取出知识图谱的核心要素**：
    *   **实体 (Entities/Nodes)**： 识别出文本中提及的人、地点、组织、产品、事件等主要对象。
    *   **关系 (Relationships/Edges)**： 识别出实体之间的具体关系。关系必须是有向的，并用一个清晰的动词或动词短语描述（如 `隶属于`, `出生于`, `投资了`, `发布了`）。
    *   **属性 (Properties)**： 识别出实体或关系的关键属性（如 人物的`年龄`、公司的`市值`、关系的`开始时间`）。
    *   **约束 (Constraints)**： 推断出实体的**标签 (Labels)**和关系的**类型 (Type)**。

## 可用的实体类型
请使用以下预定义的实体类型（**必须使用小写格式**）：
- **equipment**: 设备、机器、装置
- **component**: 部件、组件、零件
- **procedure**: 工序、流程、操作步骤
- **standard**: 标准、规范、要求
- **material**: 材料、物质、原料
- **condition**: 条件、状态、情况
- **error**: 错误、故障、问题
- **cause**: 原因、起因
- **solution**: 解决方案、方法
- **maintenance**: 维修、保养
- **inspection**: 检查、检验
- **person**: 人员、操作员、技术人员
- **tool**: 工具、仪器、设备
- **location**: 位置、地点、场所
- **time**: 时间、日期、周期
- **other**: 其他类型

**重要提示**：实体类型必须使用小写格式，如：tool、person、equipment，不要使用Tool、Person、Equipment等大写格式。

## 可用的关系类型
请使用以下预定义的关系类型（**必须使用小写格式**）：
- **part_of**: 是...的一部分
- **used_in**: 用于...
- **related_to**: 与...相关
- **causes**: 导致
- **is_solution_for**: 是...的解决方案
- **requires**: 需要...
- **results_in**: 导致...
- **checked_by**: 被...检查
- **maintained_by**: 被...维护
- **follows**: 遵循...
- **depends_on**: 依赖于...
- **compiled_by**: 由...编译/编制
- **created_by**: 由...创建
- **operated_by**: 由...操作
- **located_in**: 位于...
- **contains**: 包含
- **belongs_to**: 属于
- **connects_to**: 连接到
- **replaces**: 替换
- **improves**: 改善
- **prevents**: 防止
- **other**: 其他

**重要提示**：关系类型必须使用小写格式，如：part_of、used_in、related_to，不要使用Part_Of、Used_In、Related_To等大写格式。

2.  **生成对应的 Cypher 语句**：
    *   根据抽取出的信息，生成用于创建该知识图谱的 Cypher `MERGE` 语句。
    *   `MERGE` 语句用于确保节点和关系的唯一性（如果不存在则创建，存在则匹配）。
    *   为实体分配合适的标签，为关系指定类型。
    *   将属性添加到对应的节点和关系中。

## 输出格式要求
你必须严格按照以下 JSON 格式输出结果，不要有任何额外的解释或说明：

{{
  "entities": [
    {{
      "id": "唯一的标识符（可使用实体名称）",
      "name": "实体名称",
      "type": "实体类型（必须使用预定义的类型：equipment, component, procedure, standard, material, condition, error, cause, solution, maintenance, inspection, person, tool, location, time, other）",
      "properties": {{"属性键": "属性值", ...}}
    }},
    ...
  ],
  "relations": [
    {{
      "from": "起始实体id",
      "to": "指向实体id",
      "type": "关系类型（如 WORKS_FOR, FOUNDED, LOCATED_IN等）",
      "properties": {{"属性键": "属性值", ...}}
    }},
    ...
  ],
  "cypher_statements": [
    "// 注释说明",
    "MERGE (a:Label {{name: '实体名称'}}) ON CREATE SET a += {{properties}};",
    "MERGE (b:Label {{name: '实体名称'}}) ON CREATE SET b += {{properties}};",
    "MERGE (a)-[r:RELATIONSHIP_TYPE]->(b) ON CREATE SET r += {{properties}};",
    ...
  ]
}}

## 处理原则与约束
- **实体消歧**： 如果同一实体以不同名称出现（如"苹果"和"Apple Inc."），请将它们归一化为一个标准名称，并使用相同的 `id`。
- **关系明确性**： 关系必须是有方向的，并且类型使用英文大写蛇形命名（如 `IS_FRIEND_OF`）。
- **属性类型**： 尽量推断属性的数据类型（如数字、字符串、布尔值），并在 Cypher 语句中正确表示（字符串用引号，数字不用）。
- **优先使用 MERGE**： 使用 `MERGE` 而非 `CREATE` 来避免重复创建相同节点和关系。
- **简洁性**： 只抽取关键信息，忽略不重要的细节。

## 文本内容
{content}
"""

    def _parse_llm_response(self, response_text: str) -> Dict[str, Any]:
        """
        解析大模型响应

        Args:
            response_text: 响应文本

        Returns:
            解析后的数据
        """
        logger.info(f"开始解析LLM响应，响应长度: {len(response_text)}")
        logger.debug(f"响应内容前500字符: {response_text[:500]}")
        
        try:
            # 尝试直接解析JSON
            data = json.loads(response_text)
            logger.info(f"成功解析JSON，包含实体: {len(data.get('entities', []))}，关系: {len(data.get('relations', []))}")
            return data
        except json.JSONDecodeError as e:
            logger.warning(f"直接JSON解析失败: {str(e)}，尝试提取JSON部分")
            
            # 如果不是有效的JSON，尝试提取JSON部分
            import re

            # 使用更复杂的正则表达式来匹配完整的JSON对象
            json_pattern = r'\{(?:[^{}]|{[^{}]*})*\}'
            matches = re.findall(json_pattern, response_text, re.DOTALL)
            
            if not matches:
                # 尝试寻找代码块中的JSON
                code_block_pattern = r'```(?:json)?\s*(\{.*?\})\s*```'
                code_matches = re.findall(code_block_pattern, response_text, re.DOTALL)
                if code_matches:
                    matches = code_matches

            if not matches:
                logger.error("无法从响应中提取JSON")
                logger.debug(f"完整响应内容: {response_text}")
                return {"entities": [], "relations": [], "cypher_statements": []}

            # 尝试解析找到的JSON字符串
            for json_str in matches:
                try:
                    data = json.loads(json_str)
                    logger.info(f"成功从文本中提取并解析JSON，包含实体: {len(data.get('entities', []))}，关系: {len(data.get('relations', []))}")
                    return data
                except json.JSONDecodeError:
                    continue
            
            logger.error("所有JSON提取尝试都失败")
            logger.debug(f"找到的潜在JSON字符串: {matches}")
            return {"entities": [], "relations": [], "cypher_statements": []}

    def _save_document(self, document: Document) -> None:
        """
        保存文档信息

        Args:
            document: 文档对象
        """
        from services.document_service import DocumentService

        # 使用文档服务保存文档
        doc_service = DocumentService(self.settings, self.api_client)
        doc_service._save_document(document)

    def _get_document(self, document_id: str) -> Optional[Document]:
        """
        获取文档对象

        Args:
            document_id: 文档ID

        Returns:
            文档对象，不存在则返回None
        """
        from services.document_service import DocumentService

        # 使用文档服务获取文档
        doc_service = DocumentService(self.settings, self.api_client)
        return doc_service.get_document(document_id)
