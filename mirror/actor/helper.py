from __future__ import annotations

from kosong.tooling.simple import SimpleToolset
from kosong.chat_provider.kimi import Kimi

from ..tool.circle import GetCircle, SnsPraise, SnsComment, SnsSend
from ..tool.contact import ListGroup, ListPrivateFriend, GroupChatFriend, SearchAndAdd, GetContact
from ..tool.message import RevertAll, SendGroupUrl, SendGroupEmoji, SendGroupText, SendGroupImage, SendUserText
from ..tool.think import Think, Wait
from ..primitive import load_desc, time_string
from ..core import Person

from typing import List, Dict, Any
from loguru import logger

def build_toolset():
    toolset = SimpleToolset()
    # 朋友圈相关
    toolset += GetCircle()
    toolset += SnsPraise()
    toolset += SnsComment()
    toolset += SnsSend()

    # 联系人相关
    toolset += ListGroup()
    toolset += ListPrivateFriend()
    toolset += GroupChatFriend()
    toolset += SearchAndAdd()
    toolset += GetContact()

    # 消息相关
    toolset += RevertAll()
    # toolset += SendGroupUrl()
    # toolset += SendGroupEmoji()
    toolset += SendGroupText()
    # toolset += SendGroupImage()
    toolset += SendUserText()

    # 思考，必须
    toolset += Think()
    toolset += Wait()
    return toolset