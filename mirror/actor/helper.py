from __future__ import annotations

from kosong.tooling.simple import SimpleToolset
from kosong.chat_provider.kimi import Kimi

from ..tool.circle import GetCircleList, GetCircleDetail, SnsPraise, SnsComment, SnsSend
from ..tool.contact import ListGroup, ListPrivateFriend, GroupChatFriend, SearchAndAdd, GetContact
from ..tool.message import RevertAll, SendGroupUrl, SendGroupEmoji, SendGroupText, SendGroupImage, SendUserText
from ..tool.think import Think, Wait, Finish
from ..tool.search import WebSearch
from ..primitive import load_desc, time_string
from ..core import Person

from typing import List, Dict, Any
from loguru import logger


def build_toolset(skip: List[str] = []) -> SimpleToolset:
    toolset = SimpleToolset()
    # 朋友圈相关
    toolset += GetCircleList()
    toolset += GetCircleDetail()
    toolset += SnsPraise()
    toolset += SnsComment()
    # toolset += SnsSend()

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
    
    # Hotfix here: allow skipping sending tools
    # if 'SendGroupText' not in skip:
    toolset += SendGroupText()
    # if 'SendUserText' not in skip:
    toolset += SendUserText()

    # 搜索相关
    toolset += WebSearch()

    # 思考，必须
    toolset += Think()
    toolset += Wait()
    toolset += Finish()
    return toolset
