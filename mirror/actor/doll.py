from __future__ import annotations

import asyncio
import os
import textwrap
from pathlib import Path
from argparse import ArgumentParser
from typing import Literal

from dotenv import load_dotenv
from pydantic import BaseModel

import kosong
from kosong.chat_provider import ChatProvider
from kosong.message import Message
from kosong.tooling import CallableTool2, ToolError, ToolOk, ToolResult, ToolReturnValue, Toolset
from kosong.tooling.simple import SimpleToolset
from kosong.chat_provider.kimi import Kimi

from ..tool.circle import GetCircle, SnsPraise, SnsComment, SnsSend
from ..tool.contact import ListGroup, ListPrivateFriend, GroupChatFriend, SearchAndAdd, GetContact
from ..tool.message import RevertAll, SendGroupUrl, SendGroupEmoji, SendGroupText, SendGroupImage, SendUserText
from ..tool.think import Think
from ..primitive import load_desc
from ..core import Person
from typing import List, Dict, Any
from loguru import logger
load_dotenv()

class Doll:
    def __init__(self):
        provider = 'kimi'
        provider_upper = provider.upper()
        base_url = os.getenv(f"{provider_upper}_BASE_URL")
        api_key = os.getenv(f"{provider_upper}_API_KEY")
        model = os.getenv(f"{provider_upper}_MODEL_NAME")

        base_url = base_url or "https://api.moonshot.ai/v1"
        assert api_key is not None, "Expect KIMI_API_KEY environment variable"
        model = model or "kimi-k2-turbo-preview"

        self.chat_provider = Kimi(base_url=base_url, api_key=api_key, model=model)
        self.toolset = self.build_toolset()
        self.system_prompt = load_desc(Path(__file__).parent / "doll.md", {})

        self.format_prompt = (Path(__file__).parent / "format_person.md").read_text(encoding="utf-8")

        logger.info(f'Awake {__name__}, available tools {str(self.toolset._tool_dict)}')

    def build_toolset(self):
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
        return toolset

    def tool_result_to_message(self, result: ToolResult) -> Message:
        return Message(
            role="tool",
            tool_call_id=result.tool_call_id,
            content=result.return_value.output,
        )

    async def agent_loop(self, p: Person):
        history: list[Message] = []
        step = 0
        max_step_size = 20

        content = self.format_prompt.format(basic=p.basic, bio=p.bio, personality=str(p.analysis_result), private=str(p.memory.private))
        history.append(Message(role="user", content=content))

        while step < max_step_size:
            step += 1
            result = await kosong.step(
                chat_provider=self.chat_provider,
                system_prompt=self.system_prompt,
                toolset=self.toolset,
                history=history,
            )

            await asyncio.sleep(1)

            tool_results = await result.tool_results()

            assistant_message = result.message
            tool_messages = [self.tool_result_to_message(tr) for tr in tool_results]

            if s := assistant_message.extract_text():
                print("Assistant:\n", textwrap.indent(s, "  "))
            for tool_msg in tool_messages:
                if s := tool_msg.extract_text():
                    print("Tool:\n", textwrap.indent(s, "  "))

            if not result.tool_calls:
                break

            history.append(result.message)
            history.extend(tool_messages)
