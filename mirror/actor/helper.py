from __future__ import annotations

from kosong.message import Message
from kosong.tooling import ToolResult
from kosong.tooling.simple import SimpleToolset

from ..tool.circle import GetCircleDetail, GetCircleList, SnsComment, SnsPraise
from ..tool.contact import GetContact, GroupChatFriend, ListGroup, ListPrivateFriend, SearchAndAdd
from ..tool.message import (
    RevertAll,
    SendGroupText,
    SendUserText,
)
from ..tool.search import WebSearch
from ..tool.think import Finish, Think, Wait


def build_toolset() -> SimpleToolset:
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


def tool_result_to_message(result: ToolResult) -> Message:
    return Message(
        role="tool",
        tool_call_id=result.tool_call_id,
        content=result.return_value.output,
    )