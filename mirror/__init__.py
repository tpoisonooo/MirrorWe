"""
MirrorWe (HuixiangDou3) - 微信智能助手

一个基于大语言模型的微信智能助手，支持消息处理、智能回复和日志管理。
"""

__version__ = "3.0.0"
__author__ = "tpoisonooo"
__description__ = "微信智能助手，基于大语言模型"

from .wechat import APIContact, APICircle, APIMessage
from .core import Person, Group
from .primitive import always_get_an_event_loop

__all__ = [
    'APIContact',
    'APICircle',
    'APIMessage',
    'Person',
    'Group',
]