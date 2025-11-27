"""
工具函数模块
"""

import asyncio


def always_get_an_event_loop():
    """
    获取当前的事件循环，如果不存在则创建新的
    
    Returns:
        asyncio.AbstractEventLoop: 事件循环对象
    """
    try:
        return asyncio.get_event_loop()
    except RuntimeError:
        # 如果没有当前事件循环，创建新的
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        return loop


def get_env_or_raise(key: str) -> str:
    """Get environment variable or raise exception."""
    value = os.getenv(key)
    if not value:
        raise Exception(f'{key} not configured')
    return value


def get_env_with_default(key: str, default: any) -> any:
    """Get environment variable with default value."""
    value = os.getenv(key)
    if value is None:
        return default
    
    # Try to convert to appropriate type
    if isinstance(default, int):
        try:
            return int(value)
        except ValueError:
            return default
    elif isinstance(default, float):
        try:
            return float(value)
        except ValueError:
            return default
    return value
