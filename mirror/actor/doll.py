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
from ..primitive import load_desc, time_string
from ..core import Person
from typing import List, Dict, Any
from loguru import logger
from .helper import build_toolset

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

        self.chat_provider = Kimi(base_url=base_url,
                                  api_key=api_key,
                                  model=model)

        self.welcome_template = (Path(__file__).parent /
                                 "agent_welcome.md").read_text(
                                     encoding="utf-8")
        logger.info(f'Awake {__name__}')

    def tool_result_to_message(self, result: ToolResult) -> Message:
        return Message(
            role="tool",
            tool_call_id=result.tool_call_id,
            content=result.return_value.output,
        )

    async def welcome(self, p: Person):
        # TODO
        pass

    async def agent_loop_private(self, p: Person):
        history: list[Message] = []
        step = 0
        max_step_size = 3

        system_prompt = '{}\n\n{}'.format(
            time_string(), load_desc(Path(__file__).parent / "doll.md", {}))

        current = p.memory.private[-1]
        local = p.memory.private[0:-1] if len(p.memory.private) > 1 else []

        input_template = (Path(__file__).parent /
                          "private_input.md").read_text(encoding="utf-8")
        content = input_template.format(current=current,
                                        basic=p.basic,
                                        bio=p.bio,
                                        personality=str(p.analysis_result),
                                        local=str(local))
        history.append(Message(role="user", content=content))
        toolset = build_toolset()

        # 私聊每次最多发送 2 条消息，多了挺烦人的
        send_user_text_tool_life = 2
        while step < max_step_size:
            step += 1
            result = await kosong.step(
                chat_provider=self.chat_provider,
                system_prompt=system_prompt,
                toolset=toolset,
                history=history,
            )

            await asyncio.sleep(1)
            tool_results = await result.tool_results()
            print(tool_results)

            for tool_call in result.tool_calls:
                if tool_call.function.name == 'SendUserText':
                    send_user_text_tool_life -= 1
                    if send_user_text_tool_life <= 0:
                        del toolset._tool_dict['SendUserText']

            assistant_message = result.message
            tool_messages = [
                self.tool_result_to_message(tr) for tr in tool_results
            ]

            if s := assistant_message.extract_text():
                print("Assistant:\n", textwrap.indent(s, "  "))
            for tool_msg in tool_messages:
                if s := tool_msg.extract_text():
                    print("Tool:\n", textwrap.indent(s, "  "))

            if not result.tool_calls:
                break

            history.append(result.message)
            history.extend(tool_messages)

    async def agent_loop_group(self, g: Group, p: Person):
        history: list[Message] = []
        step = 0
        max_step_size = 2

        system_prompt = '{}\n\n{}'.format(
            time_string(), load_desc(Path(__file__).parent / "doll.md", {}))
        input_template = (Path(__file__).parent /
                          "group_input.md").read_text(encoding="utf-8")

        current = g.memory.group[-1]
        local = g.memory.group[-30:-1] if len(g.memory.group) > 1 else []

        content = input_template.format(current=current,
                                        person_bio=p.bio,
                                        group_bio=g.bio,
                                        local=str(local))
        history.append(Message(role="user", content=content))

        toolset = build_toolset()
        while step < max_step_size:
            step += 1
            result = await kosong.step(
                chat_provider=self.chat_provider,
                system_prompt=system_prompt,
                toolset=toolset,
                history=history,
            )

            await asyncio.sleep(1)

            tool_results = await result.tool_results()
            print(tool_results)

            assistant_message = result.message
            tool_messages = [
                self.tool_result_to_message(tr) for tr in tool_results
            ]

            if s := assistant_message.extract_text():
                print("Assistant:\n", textwrap.indent(s, "  "))
            for tool_msg in tool_messages:
                if s := tool_msg.extract_text():
                    print("Tool:\n", textwrap.indent(s, "  "))

            if not result.tool_calls:
                break

            history.append(result.message)
            history.extend(tool_messages)
