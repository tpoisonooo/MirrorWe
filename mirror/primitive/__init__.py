"""
基础工具模块

提供数据库、Token处理、LLM服务、限流器等基础功能。
"""

from .db import DB
from .utils import always_get_an_event_loop

# 可选导入，失败时提供降级处理
try:
    from .token import encode_string, decode_tokens, judge_language
    TOKEN_AVAILABLE = True
except ImportError:
    TOKEN_AVAILABLE = False
    encode_string = None
    decode_tokens = None
    judge_language = None

try:
    from .llm import ChatCache, OpenAIGPT, AsyncLLMGPT
    LLM_AVAILABLE = True
except ImportError:
    LLM_AVAILABLE = False
    ChatCache = None
    OpenAIGPT = None
    AsyncLLMGPT = None

try:
    from .limitter import RPM, TPM
    LIMITTER_AVAILABLE = True
except ImportError:
    LIMITTER_AVAILABLE = False
    RPM = None
    TPM = None

__all__ = [
    # 数据库工具（总是可用）
    'DB',
    
    # Token处理（可选）
    'encode_string',
    'decode_tokens', 
    'judge_language',
    'TOKEN_AVAILABLE',
    
    # LLM服务（可选）
    'ChatCache',
    'OpenAIGPT',
    'AsyncLLMGPT',
    'LLM_AVAILABLE',
    
    # 限流器（可选）
    'RPM',
    'TPM',
    'LIMITTER_AVAILABLE',
    
    # 工具函数（总是可用）
    'always_get_an_event_loop'
]