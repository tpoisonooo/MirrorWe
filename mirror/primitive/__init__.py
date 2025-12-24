"""
基础工具模块

提供数据库、Token处理、LLM服务、限流器等基础功能。
"""

from .db import DB
from .limitter import RPM, TPM
from .llm import LLM, ChatCache
from .metaclass import SingletonMeta
from .token import decode_tokens, encode_string, judge_language
from .utils import (
    always_get_an_event_loop,
    get_env_or_raise,
    get_env_with_default,
    load_desc,
    safe_write_text,
    time_string,
    try_load_text,
)

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

    # 元类
    'SingletonMeta',
]
