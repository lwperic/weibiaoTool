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
        from docx import Document as DocxDocument

        file_path = Path(document.file_path)
        if not file_path.exists():
            raise ValueError(f"文档文件不存在: {file_path}")

        try:
            doc = DocxDocument(file_path)
            content = []

            for table in doc.tables:
                for row in table.rows:
                    row_text = []
                    for cell in row.cells:
                        row_text.append(cell.text.strip())
                    content.append("	".join(row_text))

            return "".join(content)
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
        response = self.llm_client.chat_completion(
            messages=[
                {"role": "system", "content": "你是一个专业的知识抽取助手，能够从维修标准文档中提取结构化知识。"},
                {"role": "user", "content": prompt}
            ],
            temperature=0.2,
            max_tokens=4000
        )

        # 解析响应
        result_text = response["choices"][0]["message"]["content"]
        kg_data = self._parse_llm_response(result_text)

        # 创建知识图谱
        kg = KnowledgeGraph(
            id=f"kg_{source_doc_id}_{int(time.time())}",
            name=f"知识图谱_{source_doc_id}",
            description=f"从文档 {source_doc_id} 中抽取的知识",
            entities=[Entity.from_dict(e) for e in kg_data.get("entities", [])],
            relations=[Relation.from_dict(r) for r in kg_data.get("relations", [])],
            metadata={"source_document": source_doc_id}
        )

        return kg

    def _build_extraction_prompt(self, content: str) -> str:
        """
        构建知识抽取提示词

        Args:
            content: 文档内容

        Returns:
            提示词
        """
        return f"""
请从以下维修标准文档中抽取结构化知识，并以JSON格式返回。

文档内容：
{content}

请抽取以下类型的实体和关系：

实体类型：
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

关系类型：
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

请按照以下JSON格式返回结果：
{{
  "entities": [
    {{
      "id": "唯一标识符",
      "name": "实体名称",
      "type": "实体类型",
      "description": "实体描述",
      "properties": {{
        "属性名": "属性值"
      }}
    }}
  ],
  "relations": [
    {{
      "id": "唯一标识符",
      "type": "关系类型",
      "source": "源实体ID",
      "target": "目标实体ID",
      "description": "关系描述",
      "properties": {{
        "属性名": "属性值"
      }}
    }}
  ]
}}
"""

    def _parse_llm_response(self, response_text: str) -> Dict[str, Any]:
        """
        解析大模型响应

        Args:
            response_text: 响应文本

        Returns:
            解析后的数据
        """
        try:
            # 尝试直接解析JSON
            data = json.loads(response_text)
            return data
        except json.JSONDecodeError:
            # 如果不是有效的JSON，尝试提取JSON部分
            import re

            # 查找JSON开始和结束位置
            start_match = re.search(r"\{", response_text)
            end_match = re.search(r"\}", response_text)

            if not start_match or not end_match:
                logger.error("无法从响应中提取JSON")
                return {"entities": [], "relations": []}

            # 提取JSON字符串
            start_pos = start_match.start()
            end_pos = end_match.end()
            json_str = response_text[start_pos:end_pos]

            try:
                return json.loads(json_str)
            except json.JSONDecodeError as e:
                logger.error(f"解析JSON失败: {str(e)}")
                return {"entities": [], "relations": []}

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
