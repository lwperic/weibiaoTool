"""
API客户端
"""

import os
import json
import time
import logging
from typing import Dict, Any, Optional, List
from datetime import datetime

from config.settings import settings
from utils.logger import get_logger

logger = get_logger(__name__)


class APIClient:
    """通用API客户端基类"""

    def __init__(self, settings):
        """
        初始化API客户端

        Args:
            settings: 配置对象
        """
        self.settings = settings
        self.timeout = settings.default_timeout

    def request(
        self,
        method: str,
        url: str,
        params: Optional[Dict] = None,
        data: Optional[Dict] = None,
        json: Optional[Dict] = None,
        headers: Optional[Dict] = None,
        timeout: Optional[int] = None,
        retries: int = 3,
        backoff: float = 1.0
    ) -> Dict[str, Any]:
        """
        发送HTTP请求

        Args:
            method: HTTP方法
            url: 请求URL
            params: URL参数
            data: 表单数据
            json: JSON数据
            headers: 请求头
            timeout: 超时时间（秒）
            retries: 重试次数
            backoff: 重试退避因子

        Returns:
            响应数据

        Raises:
            Exception: 请求失败时抛出异常
        """
        if timeout is None:
            timeout = self.timeout

        # 设置默认请求头
        default_headers = {
            "Content-Type": "application/json",
            "User-Agent": f"{settings.app_name}/{settings.app_version}"
        }

        if headers:
            default_headers.update(headers)

        last_exception = None

        for attempt in range(retries):
            try:
                # 使用requests库发送请求
                import requests
                response = requests.request(
                    method=method,
                    url=url,
                    params=params,
                    data=data,
                    json=json,
                    headers=default_headers,
                    timeout=timeout
                )

                response.raise_for_status()
                return response.json()

            except Exception as e:
                last_exception = e
                logger.warning(f"请求失败 (尝试 {attempt + 1}/{retries}): {str(e)}")

                if attempt < retries - 1:
                    # 计算退避时间
                    sleep_time = backoff * (2 ** attempt)
                    logger.info(f"等待 {sleep_time} 秒后重试...")
                    time.sleep(sleep_time)

        # 所有重试都失败
        error_msg = f"请求失败，已重试 {retries} 次: {str(last_exception)}"
        logger.error(error_msg)
        raise Exception(error_msg)


class MockAPIClient(APIClient):
    """模拟API客户端，用于测试和开发"""

    def __init__(self, settings):
        """
        初始化模拟API客户端

        Args:
            settings: 配置对象
        """
        super().__init__(settings)
        self.mock_responses = {}

    def set_mock_response(self, url: str, response: Dict[str, Any]) -> None:
        """
        设置模拟响应

        Args:
            url: 请求URL
            response: 模拟响应数据
        """
        self.mock_responses[url] = response

    def request(self, method: str, url: str, **kwargs) -> Dict[str, Any]:
        """
        发送请求（模拟）

        Args:
            method: HTTP方法
            url: 请求URL
            **kwargs: 其他参数

        Returns:
            模拟响应数据
        """
        # 检查是否有模拟响应
        if url in self.mock_responses:
            return self.mock_responses[url]

        # 返回默认模拟响应
        return {
            "status": "success",
            "message": "模拟响应",
            "timestamp": datetime.now().isoformat(),
            "data": {}
        }
