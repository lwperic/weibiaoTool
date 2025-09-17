"""
API调用工具
"""

import time
import hashlib
import json
from typing import Dict, Any, Optional, Union, List
import requests
import logging
from datetime import datetime

from config.settings import settings
from utils.logger import get_logger

logger = get_logger(__name__)


class APIClient:
    """API客户端基类"""

    def __init__(self, settings):
        """
        初始化API客户端

        Args:
            settings: 配置对象
        """
        self.settings = settings
        self.session = requests.Session()
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
                response = self.session.request(
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

            except requests.exceptions.RequestException as e:
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


class DeepSeekClient(APIClient):
    """DeepSeek API客户端"""

    def __init__(self, settings):
        """
        初始化DeepSeek客户端

        Args:
            settings: 配置对象
        """
        super().__init__(settings)
        self.api_key = settings.deepseek_api_key
        self.api_base = settings.deepseek_api_base
        self.model = settings.deepseek_model

        if not self.api_key:
            raise ValueError("DeepSeek API密钥未配置")

        # 设置认证头
        self.session.headers.update({
            "Authorization": f"Bearer {self.api_key}"
        })

    def chat_completion(
        self,
        messages: List[Dict[str, str]],
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
        stream: bool = False,
        **kwargs
    ) -> Dict[str, Any]:
        """
        调用DeepSeek聊天完成API

        Args:
            messages: 消息列表
            temperature: 温度参数
            max_tokens: 最大令牌数
            stream: 是否流式输出
            **kwargs: 其他参数

        Returns:
            API响应
        """
        url = f"{self.api_base}/chat/completions"

        payload = {
            "model": self.model,
            "messages": messages,
            "temperature": temperature,
            "stream": stream
        }

        if max_tokens:
            payload["max_tokens"] = max_tokens

        payload.update(kwargs)

        return self.request("POST", url, json=payload)


def generate_hash(content: Union[str, Dict]) -> str:
    """
    生成内容的哈希值

    Args:
        content: 内容，可以是字符串或字典

    Returns:
        哈希值
    """
    if isinstance(content, dict):
        content = json.dumps(content, sort_keys=True)

    return hashlib.md5(content.encode()).hexdigest()


def safe_json_loads(json_str: str) -> Optional[Dict]:
    """
    安全地解析JSON字符串

    Args:
        json_str: JSON字符串

    Returns:
        解析后的字典，解析失败返回None
    """
    try:
        return json.loads(json_str)
    except json.JSONDecodeError:
        logger.error(f"JSON解析失败: {json_str}")
        return None
