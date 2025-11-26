"""
微信服务模块

提供微信消息处理、登录认证、日志管理和消息转发等功能。
"""

from .proxy import WkteamManager, Message, User, Talk
from .reorganize import reorganize_logs, reorganize_logs_async, reorganize_logs_sync
from .json_parser import (
    parse_multiline_json_objects_async,
    parse_multiline_json_objects_sync,
    parse_multiline_json_objects_async_with_batch
)

__all__ = [
    # 核心类
    'WkteamManager',
    'Message', 
    'User',
    'Talk',
    
    # 日志整理函数
    'reorganize_logs',
    'reorganize_logs_async',
    'reorganize_logs_sync',
    
    # JSON解析工具
    'parse_multiline_json_objects_async',
    'parse_multiline_json_objects_sync',
    'parse_multiline_json_objects_async_with_batch'
]