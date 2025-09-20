"""
文档服务
"""

import os
import shutil
from pathlib import Path
from typing import List, Optional, Dict, Any, Tuple, Union
from datetime import datetime
import logging

from config.settings import settings
from models.document import Document, DocumentStatus
from utils.logger import get_logger
from utils.time_utils import format_timestamp
from utils.data_cleaner import DefaultDataCleaner, CustomDataCleaner
from utils.error_handler import ErrorHandler, ErrorType

logger = get_logger(__name__)


class DocumentService:
    """文档管理服务"""

    def __init__(self, settings, api_client):
        """
        初始化文档服务

        Args:
            settings: 配置对象
            api_client: API客户端
        """
        self.settings = settings
        self.api_client = api_client
        self.upload_dir = settings.upload_dir
        self.data_dir = settings.data_dir

        # 确保目录存在
        self.upload_dir.mkdir(parents=True, exist_ok=True)
        self.data_dir.mkdir(parents=True, exist_ok=True)
        
        # 初始化数据清洗器
        self.data_cleaner = DefaultDataCleaner()
        
        # 初始化错误处理器
        error_dir = self.data_dir / "errors"
        self.error_handler = ErrorHandler(error_dir)

    def upload_document(self, file_path: Path, metadata: Optional[Dict] = None) -> Document:
        """
        上传文档

        Args:
            file_path: 文件路径
            metadata: 元数据

        Returns:
            文档对象
        """
        if not file_path.exists():
            raise ValueError(f"文件不存在: {file_path}")

        # 检查文件类型
        if file_path.suffix.lower() not in ['.doc', '.docx']:
            raise ValueError("只支持Word文档(.doc, .docx)")

        # 创建文档对象
        document = Document.create_from_file(file_path, metadata)
        
        # 检查是否已存在相同哈希值的文档
        existing_doc = self.get_document_by_hash(document.file_hash)
        if existing_doc:
            logger.warning(f"检测到重复文件: {file_path.name} 与 {existing_doc.name} 相同")
            raise ValueError(f"文件已存在: {existing_doc.name}")

        # 验证文档内容
        try:
            from utils.word_reader import read_word_text
            content = read_word_text(file_path)
            if not content or not content.strip():
                raise ValueError("文档内容为空或无法读取")
            logger.info(f"文档内容验证成功: {file_path.name}, 内容长度: {len(content)}")
        except Exception as e:
            logger.error(f"文档内容验证失败: {file_path.name} - {str(e)}")
            raise ValueError(f"文档内容验证失败: {str(e)}")

        # 移动文件到上传目录
        dest_path = self.upload_dir / file_path.name
        shutil.copy2(file_path, dest_path)

        # 更新文档路径
        document.file_path = str(dest_path)

        # 保存文档信息
        self._save_document(document)

        logger.info(f"文档上传成功: {document.name}")
        return document
        
    def upload_documents(self, file_paths: List[Path], metadata: Optional[Dict] = None) -> List[Document]:
        """
        批量上传文档

        Args:
            file_paths: 文件路径列表
            metadata: 元数据

        Returns:
            文档对象列表
        """
        documents = []
        failed = []
        
        for file_path in file_paths:
            try:
                document = self.upload_document(file_path, metadata)
                documents.append(document)
            except Exception as e:
                logger.error(f"文档上传失败: {file_path.name} - {str(e)}")
                failed.append(file_path.name)
        
        logger.info(f"批量上传完成: 成功 {len(documents)}, 失败 {len(failed)}")
        return documents
        
    def upload_folder(self, folder_path: Path, metadata: Optional[Dict] = None) -> List[Document]:
        """
        上传文件夹中的所有Word文档

        Args:
            folder_path: 文件夹路径
            metadata: 元数据

        Returns:
            文档对象列表
        """
        if not folder_path.is_dir():
            raise ValueError(f"路径不是文件夹: {folder_path}")
        
        # 查找所有Word文档
        word_files = []
        for ext in [".doc", ".docx"]:
            word_files.extend(folder_path.glob(f"*{ext}"))
        
        if not word_files:
            logger.warning(f"文件夹中没有找到Word文档: {folder_path}")
            return []
        
        return self.upload_documents(word_files, metadata)
        
    def get_document_by_hash(self, file_hash: str) -> Optional[Document]:
        """
        根据文件哈希值获取文档

        Args:
            file_hash: 文件哈希值

        Returns:
            文档对象，不存在则返回None
        """
        for file_path in self.data_dir.glob("*.json"):
            try:
                with open(file_path, "r", encoding="utf-8") as f:
                    data = f.read()
                    document = Document.from_dict(data)
                    if document.file_hash == file_hash:
                        return document
            except Exception as e:
                logger.error(f"读取文档信息失败: {str(e)}")
                continue
        
        return None

    def get_document(self, document_id: str) -> Optional[Document]:
        """
        获取文档信息

        Args:
            document_id: 文档ID

        Returns:
            文档对象，不存在则返回None
        """
        document_path = self.data_dir / f"{document_id}.json"

        if not document_path.exists():
            return None

        try:
            with open(document_path, 'r', encoding='utf-8') as f:
                data = f.read()
                return Document.from_dict(data)
        except Exception as e:
            logger.error(f"读取文档信息失败: {str(e)}")
            return None

    def list_documents(
        self,
        status: Optional[DocumentStatus] = None,
        search_keyword: Optional[str] = None,
        page: int = 1,
        page_size: int = 20
    ) -> Tuple[List[Document], int]:
        """
        列出文档

        Args:
            status: 文档状态筛选
            search_keyword: 搜索关键词
            page: 页码
            page_size: 每页数量

        Returns:
            文档列表和总数
        """
        documents = []
        total = 0

        # 遍历数据目录
        for file_path in self.data_dir.glob("*.json"):
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    data = f.read()
                    document = Document.from_dict(data)

                    # 状态筛选
                    if status and document.status != status:
                        continue

                    # 关键词搜索
                    if search_keyword:
                        keyword = search_keyword.lower()
                        if (keyword not in document.name.lower() and 
                            (document.original_name and keyword not in document.original_name.lower())):
                            continue

                    documents.append(document)
                    total += 1
            except Exception as e:
                logger.error(f"读取文档信息失败: {str(e)}")
                continue

        # 排序
        documents.sort(key=lambda x: x.created_at, reverse=True)

        # 分页
        start = (page - 1) * page_size
        end = start + page_size
        paged_documents = documents[start:end]

        return paged_documents, total
        
    def get_document_statistics(self) -> Dict[str, Any]:
        """
        获取文档统计信息

        Returns:
            统计信息字典
        """
        statistics = {
            "total": 0,
            "pending": 0,
            "processing": 0,
            "completed": 0,
            "error": 0,
            "deleted": 0,
            "recent_uploads": []
        }
        
        # 遍历数据目录
        recent_documents = []
        
        for file_path in self.data_dir.glob("*.json"):
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    data = f.read()
                    document = Document.from_dict(data)
                    
                    # 统计各状态文档数量
                    statistics["total"] += 1
                    statistics[document.status.value] += 1
                    
                    # 收集最近上传的文档
                    recent_documents.append(document)
            except Exception as e:
                logger.error(f"读取文档信息失败: {str(e)}")
                continue
        
        # 按上传时间排序，获取最近上传的5个文档
        recent_documents.sort(key=lambda x: x.created_at, reverse=True)
        statistics["recent_uploads"] = [
            {
                "id": doc.id,
                "name": doc.name,
                "upload_time": doc.created_at.strftime("%Y-%m-%d %H:%M:%S")
            }
            for doc in recent_documents[:5]
        ]
        
        return statistics

    def update_document(self, document_id: str, **kwargs) -> Optional[Document]:
        """
        更新文档信息

        Args:
            document_id: 文档ID
            **kwargs: 更新字段

        Returns:
            更新后的文档对象，失败则返回None
        """
        document = self.get_document(document_id)
        if not document:
            return None

        # 更新字段
        for key, value in kwargs.items():
            if hasattr(document, key):
                setattr(document, key, value)

        document.updated_at = datetime.now()

        # 保存更新
        self._save_document(document)

        logger.info(f"文档更新成功: {document.name}")
        return document

    def delete_document(self, document_id: str) -> bool:
        """
        删除文档

        Args:
            document_id: 文档ID

        Returns:
            是否成功
        """
        document = self.get_document(document_id)
        if not document:
            return False

        # 更新状态为已删除
        document.update_status(DocumentStatus.DELETED)

        # 保存更新
        self._save_document(document)

        # 删除文件
        file_path = Path(document.file_path)
        if file_path.exists():
            try:
                file_path.unlink()
                logger.info(f"文档文件已删除: {document.name}")
            except Exception as e:
                logger.error(f"删除文档文件失败: {str(e)}")

        logger.info(f"文档已标记为删除: {document.name}")
        return True

    def rename_document(self, document_id: str, new_name: str) -> Optional[Document]:
        """
        重命名文档

        Args:
            document_id: 文档ID
            new_name: 新名称

        Returns:
            更新后的文档对象，失败则返回None
        """
        document = self.get_document(document_id)
        if not document:
            return None

        # 更新名称
        document.name = new_name
        document.updated_at = datetime.now()

        # 保存更新
        self._save_document(document)

        logger.info(f"文档重命名成功: {document.name}")
        return document

    def update_document_status(
        self,
        document_id: str,
        status: DocumentStatus,
        error_message: Optional[str] = None
    ) -> Optional[Document]:
        """
        更新文档状态

        Args:
            document_id: 文档ID
            status: 新状态
            error_message: 错误信息（如果有）

        Returns:
            更新后的文档对象，失败则返回None
        """
        document = self.get_document(document_id)
        if not document:
            return None

        # 更新状态
        document.update_status(status, error_message)

        # 保存更新
        self._save_document(document)

        logger.info(f"文档状态更新成功: {document.name} - {status.value}")
        return document

    def _save_document(self, document: Document) -> None:
        """
        保存文档信息

        Args:
            document: 文档对象
        """
        document_path = self.data_dir / f"{document.id}.json"

        try:
            with open(document_path, 'w', encoding='utf-8') as f:
                f.write(document.json())
        except Exception as e:
            logger.error(f"保存文档信息失败: {str(e)}")
            raise

    def get_document_preview(self, document_id: str) -> Optional[str]:
        """
        获取文档预览内容

        Args:
            document_id: 文档ID

        Returns:
            预览文本，失败则返回None
        """
        document = self.get_document(document_id)
        if not document:
            return None

        file_path = Path(document.file_path)
        if not file_path.exists():
            return None

        try:
            # 统一通过工具读取文本（兼容 .doc/.docx）
            from utils.word_reader import read_word_text

            preview_text = read_word_text(file_path)

            # 限制预览长度
            if len(preview_text) > 5000:
                preview_text = preview_text[:5000] + "\n...[内容已截断]"

            return preview_text
        except Exception as e:
            logger.error(f"获取文档预览失败: {str(e)}")
            return None
            
    def clean_document(self, document_id: str) -> Optional[Document]:
        """
        清洗文档数据

        Args:
            document_id: 文档ID

        Returns:
            清洗后的文档对象，失败则返回None
        """
        document = self.get_document(document_id)
        if not document:
            return None
        
        try:
            # 使用数据清洗器清洗文档
            cleaned_document = self.data_cleaner.clean_document(document)
            
            # 保存清洗后的文档
            self._save_document(cleaned_document)
            
            logger.info(f"文档数据清洗完成: {cleaned_document.name}")
            return cleaned_document
        except Exception as e:
            logger.error(f"文档数据清洗失败: {str(e)}")
            return None
            
    def set_data_cleaner(self, cleaner: Union[DefaultDataCleaner, CustomDataCleaner]) -> None:
        """
        设置数据清洗器

        Args:
            cleaner: 数据清洗器实例
        """
        if isinstance(cleaner, (DefaultDataCleaner, CustomDataCleaner)):
            self.data_cleaner = cleaner
            logger.info("数据清洗器设置成功")
        else:
            raise ValueError("不支持的数据清洗器类型")
            
    def validate_document(self, document: Document) -> bool:
        """
        验证文档数据

        Args:
            document: 文档对象

        Returns:
            是否有效
        """
        try:
            # 使用数据清洗器验证数据
            return self.data_cleaner.validate_data(document.to_dict())
        except Exception as e:
            logger.error(f"文档数据验证失败: {str(e)}")
            return False
            
    def handle_document_error(
        self,
        document_id: str,
        error_type: ErrorType,
        message: str,
        details: Optional[str] = None,
        suggestion: Optional[str] = None
    ) -> None:
        """
        处理文档错误

        Args:
            document_id: 文档ID
            error_type: 错误类型
            message: 错误消息
            details: 详细信息
            suggestion: 修复建议
        """
        # 处理错误
        self.error_handler.handle_error(
            document_id=document_id,
            error_type=error_type,
            message=message,
            details=details,
            suggestion=suggestion
        )
        
        # 更新文档状态
        self.update_document_status(document_id, DocumentStatus.ERROR, message)
        
    def get_error_reports(
        self,
        document_id: Optional[str] = None,
        error_type: Optional[ErrorType] = None,
        limit: int = 100
    ) -> List[Dict[str, Any]]:
        """
        获取错误报告

        Args:
            document_id: 文档ID筛选
            error_type: 错误类型筛选
            limit: 最大返回数量

        Returns:
            错误报告列表
        """
        reports = self.error_handler.get_error_reports(document_id, error_type, limit)
        return [report.to_dict() for report in reports]
        
    def clear_error_reports(self, document_id: Optional[str] = None) -> int:
        """
        清除错误报告

        Args:
            document_id: 文档ID，如果为None则清除所有报告

        Returns:
            清除的报告数量
        """
        return self.error_handler.clear_error_reports(document_id)
