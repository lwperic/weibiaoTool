"""
API工具模块
"""

import json
import time
from typing import Dict, Any, Optional, Union
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
            API响应

        Raises:
            Exception: 请求失败
        """
        import requests

        timeout = timeout or self.timeout

        # 默认请求头
        default_headers = {
            'Accept': 'application/json',
            'Content-Type': 'application/json'
        }

        # 合并请求头
        if headers:
            default_headers.update(headers)

        last_exception = None

        for attempt in range(retries):
            try:
                # 直接使用requests，不使用session
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

    def chat_completion(
        self,
        messages: list,
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

        # 设置认证头
        headers = {
            "Authorization": f"Bearer {self.api_key}"
        }

        return self.request("POST", url, json=payload, headers=headers)


def generate_hash(content: Union[str, Dict, bytes]) -> str:
    """
    生成内容的哈希值

    Args:
        content: 内容，可以是字符串、字典或字节

    Returns:
        哈希值
    """
    import hashlib

    if isinstance(content, dict):
        content = json.dumps(content, sort_keys=True)

    # 如果是bytes类型，直接使用；如果是str类型，则编码为bytes
    if isinstance(content, bytes):
        content_bytes = content
    else:
        content_bytes = content.encode('utf-8')

    return hashlib.md5(content_bytes).hexdigest()


def safe_json_loads(json_str: str) -> Optional[Dict[str, Any]]:
    """
    安全的JSON解析

    Args:
        json_str: JSON字符串

    Returns:
        解析后的字典，解析失败时返回None
    """
    try:
        return json.loads(json_str)
    except (json.JSONDecodeError, TypeError, ValueError) as e:
        logger.warning(f"JSON解析失败: {str(e)}")
        return None
