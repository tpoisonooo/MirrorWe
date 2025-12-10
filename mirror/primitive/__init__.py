"""
基础工具模块

提供数据库、Token处理、LLM服务、限流器等基础功能。
"""

from .db import DB
from .utils import always_get_an_event_loop, get_env_or_raise, get_env_with_default, try_load_text, safe_write_text
from .utils import load_desc, time_string
from .llm import ChatCache, LLM
from .json_parser import parse_multiline_json_objects_async, parse_multiline_json_objects_sync, dump_multiline_json_objects_async
from .token import encode_string, decode_tokens, judge_language
from .limitter import RPM, TPM

__all__ = [
    # 数据库工具
    'DB',
    
    # Token处理
    'encode_string',
    'decode_tokens', 
    'judge_language',
    
    # LLM服务
    'ChatCache',
    'RPM',
    'TPM',
    'LLM',
    
    # 工具函数
    'always_get_an_event_loop',
    'get_env_or_raise',
    'get_env_with_default',
    'load_desc',

    # 文件操作
    'safe_write_text',
    'try_load_text',

    # JSON解析器
    'parse_multiline_json_objects_async',
    'parse_multiline_json_objects_sync',
    'dump_multiline_json_objects_async'
]