# !/user/bin/env python3
# -*- coding: utf-8 -*-
"""
API客户端
"""

import os
import json
import logging
from typing import Dict, Any, Optional, List
from datetime import datetime

from utils.logger import get_logger

logger = get_logger(__name__)


class MockAPIClient:
    """模拟API客户端，用于测试和开发环境"""

    def __init__(self, api_key: Optional[str] = None, base_url: Optional[str] = None):
        """
        初始化API客户端

        Args:
            api_key: API密钥
            base_url: 基础URL
        """
        self.api_key = api_key or os.getenv("API_KEY", "mock-api-key")
        self.base_url = base_url or os.getenv("API_BASE_URL", "https://api.example.com")

    def chat(self, messages: List[Dict[str, str]], model: str = "deepseek-chat", **kwargs) -> Dict[str, Any]:
        """
        聊天API调用

        Args:
            messages: 消息列表
            model: 模型名称
            **kwargs: 其他参数

        Returns:
            API响应
        """
        logger.info(f"模拟聊天API调用: model={model}, messages_count={len(messages)}")

        # 返回模拟响应
        return {
            "model": "deepseek-chat",
            "choices": [
                {
                    "message": {
                        "content": "这是模拟的AI回复内容。",
                        "role": "assistant"
                    },
                    "finish_reason": "stop",
                    "index": 0
                }
            ],
            "usage": {
                "prompt_tokens": 10,
                "completion_tokens": 5,
                "total_tokens": 15
            }
        }

    # 其他API方法可以根据需要添加...
    def upload_file(self, file_path: str, purpose: str = "assistants") -> Dict[str, Any]:
        """模拟文件上传"""
        logger.info(f"模拟文件上传: file_path={file_path}, purpose={purpose}")
        return {
            "id": f"file-{datetime.now().strftime('%Y%m%d%H%M%S')}",
            "object": "file",
            "bytes": os.path.getsize(file_path),
            "created_at": int(datetime.now().timestamp()),
            "filename": os.path.basename(file_path),
            "purpose": purpose
        }
