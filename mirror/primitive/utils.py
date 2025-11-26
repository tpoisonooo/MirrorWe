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