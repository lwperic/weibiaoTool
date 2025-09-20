"""
编码修复工具
"""

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
import json


class UTF8HTTPAdapter(HTTPAdapter):
    """强制使用UTF-8编码的HTTP适配器"""
    
    def send(self, request, **kwargs):
        """发送请求，强制使用UTF-8编码"""
        # 确保请求体使用UTF-8编码
        if request.body:
            if isinstance(request.body, str):
                request.body = request.body.encode('utf-8')
            elif isinstance(request.body, bytes):
                # 如果已经是bytes，检查是否是有效的UTF-8
                try:
                    # 尝试解码为UTF-8，如果失败则跳过处理
                    request.body.decode('utf-8')
                except UnicodeDecodeError:
                    # 如果不是UTF-8，尝试用errors='ignore'处理
                    try:
                        decoded = request.body.decode('utf-8', errors='ignore')
                        request.body = decoded.encode('utf-8')
                    except:
                        pass
        
        # 发送请求
        response = super().send(request, **kwargs)
        
        # 强制设置响应编码
        if response.encoding is None or response.encoding.lower() in ['latin-1', 'iso-8859-1']:
            response.encoding = 'utf-8'
        
        return response


def setup_utf8_requests_session():
    """设置强制UTF-8编码的requests会话"""
    session = requests.Session()
    
    # 使用自定义适配器
    adapter = UTF8HTTPAdapter(
        max_retries=Retry(
            total=3,
            backoff_factor=1,
            status_forcelist=[500, 502, 503, 504]
        )
    )
    
    session.mount('http://', adapter)
    session.mount('https://', adapter)
    
    # 设置默认头部（只使用ASCII字符）
    session.headers.update({
        'Accept': 'application/json',
        'Content-Type': 'application/json',
        'User-Agent': 'WeibiaoTool/1.0'
    })
    
    return session


def safe_json_dumps(obj, **kwargs):
    """安全的JSON序列化，确保UTF-8编码"""
    return json.dumps(obj, ensure_ascii=False, **kwargs)


def safe_encode_dict(data):
    """安全编码字典中的所有字符串"""
    if isinstance(data, dict):
        return {key: safe_encode_dict(value) for key, value in data.items()}
    elif isinstance(data, list):
        return [safe_encode_dict(item) for item in data]
    elif isinstance(data, str):
        # 确保字符串是UTF-8编码，处理特殊字符
        try:
            # 先尝试编码为UTF-8，如果失败则使用错误处理
            return data.encode('utf-8', errors='ignore').decode('utf-8')
        except (UnicodeEncodeError, UnicodeDecodeError):
            # 如果仍有问题，使用更宽松的处理方式
            return data.encode('utf-8', errors='replace').decode('utf-8')
    else:
        return data

