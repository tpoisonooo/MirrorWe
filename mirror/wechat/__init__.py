"""
微信服务模块

提供微信消息处理、登录认证、日志管理和消息转发等功能。
"""

from .api_contact import APIContact
from .api_circle import APICircle
from .api_message import APIMessage
from .api_manage import APIManage
from .message import Message

__all__ = [
    'APIContact',
    'APICircle',
    'APIMessage',
    'APIManage',
    'Message',
]