"""
时间处理工具
"""

from datetime import datetime, timedelta
from typing import Union, Optional


def format_timestamp(timestamp: Union[datetime, int, float], fmt: str = "%Y-%m-%d %H:%M:%S") -> str:
    """
    格式化时间戳

    Args:
        timestamp: 时间戳，可以是datetime对象或Unix时间戳
        fmt: 格式字符串

    Returns:
        格式化后的时间字符串
    """
    if isinstance(timestamp, (int, float)):
        dt = datetime.fromtimestamp(timestamp)
    else:
        dt = timestamp

    return dt.strftime(fmt)


def parse_datetime(time_str: str, fmt: str = "%Y-%m-%d %H:%M:%S") -> datetime:
    """
    解析时间字符串为datetime对象

    Args:
        time_str: 时间字符串
        fmt: 格式字符串

    Returns:
        datetime对象
    """
    return datetime.strptime(time_str, fmt)


def get_current_time(fmt: str = "%Y-%m-%d %H:%M:%S") -> str:
    """
    获取当前时间

    Args:
        fmt: 格式字符串

    Returns:
        当前时间字符串
    """
    return format_timestamp(datetime.now(), fmt)


def time_ago(timestamp: Union[datetime, int, float]) -> str:
    """
    获取相对于当前时间的时间差描述

    Args:
        timestamp: 时间戳，可以是datetime对象或Unix时间戳

    Returns:
        时间差描述字符串，如"5分钟前"、"3天前"等
    """
    if isinstance(timestamp, (int, float)):
        dt = datetime.fromtimestamp(timestamp)
    else:
        dt = timestamp

    now = datetime.now()
    diff = now - dt

    seconds = diff.total_seconds()

    if seconds < 60:
        return f"{int(seconds)}秒前"
    elif seconds < 3600:
        return f"{int(seconds // 60)}分钟前"
    elif seconds < 86400:
        return f"{int(seconds // 3600)}小时前"
    else:
        return f"{int(seconds // 86400)}天前"


def add_time(
    time_point: Union[datetime, str],
    days: int = 0,
    hours: int = 0,
    minutes: int = 0,
    seconds: int = 0,
    fmt: str = "%Y-%m-%d %H:%M:%S"
) -> datetime:
    """
    在指定时间点上增加时间

    Args:
        time_point: 时间点，可以是datetime对象或时间字符串
        days: 天数
        hours: 小时数
        minutes: 分钟数
        seconds: 秒数
        fmt: 如果time_point是字符串，则使用的格式

    Returns:
        增加时间后的datetime对象
    """
    if isinstance(time_point, str):
        dt = parse_datetime(time_point, fmt)
    else:
        dt = time_point

    delta = timedelta(days=days, hours=hours, minutes=minutes, seconds=seconds)
    return dt + delta


def is_valid_time_range(start_time: Union[datetime, str], end_time: Union[datetime, str]) -> bool:
    """
    检查时间范围是否有效（开始时间不晚于结束时间）

    Args:
        start_time: 开始时间
        end_time: 结束时间

    Returns:
        是否有效
    """
    if isinstance(start_time, str):
        start_time = parse_datetime(start_time)

    if isinstance(end_time, str):
        end_time = parse_datetime(end_time)

    return start_time <= end_time
