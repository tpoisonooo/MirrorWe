from __future__ import annotations

import asyncio
import json
import textwrap
from pathlib import Path

import kosong
from dotenv import load_dotenv
from kosong.message import Message
from loguru import logger

from ...core import Person, build_self_inner
from ...primitive import load_desc, time_string
from ...tool.message import (
    SendUserText,
)
from ..base import ActorBase
from ..helper import build_toolset, tool_result_to_message

load_dotenv()

class PrivateActor(ActorBase):

    def __init__(self):
        super().__init__()

        self.name = 'MirrorWe'
        logger.info(f'Awake {__name__}')

    async def agent_loop(self, p: Person, **extra) -> None:
        history: list[Message] = []
        step = 0
        max_step_size = 5

        system_prompt = '{}\n\n{}'.format(
            time_string(), load_desc(Path(__file__).parent / "self.md", {}))

        current = p.memory.private[-1]
        local = p.memory.private[0:-1] if len(p.memory.private) > 1 else []

        input_template = (Path(__file__).parent /
                          "input.md").read_text(encoding="utf-8")
        content = input_template.format(current=current,
                                        basic=p.basic,
                                        bio=p.bio,
                                        personality=str(p.analysis_result),
                                        local=str(local))
        history.append(Message(role="user", content=content))

        send_user_text_tool_life = 2
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

            for tool_call in result.tool_calls:
                if tool_call.function.name == SendUserText.name:
                    try:
                        send_text = json.loads(tool_call.function.arguments).get('text', '')
                    except Exception as e:
                        logger.error(f'Parse tool_call_arguments failed, {str(e)}: {str(tool_call.function.arguments)}')
                        send_text = tool_call.function.arguments

                    inner = build_self_inner(sender_name=self.name, content=send_text)
                    p.memory.add(private=inner)

                    # 私聊每轮最多发 2 条消息
                    send_user_text_tool_life -= 1
                    # TODO wait kosong upgrade to support removing tool by life
                    # if send_user_text_tool_life <= 0:
                    #     toolset.remove(SendUserText.name)

            assistant_message = result.message
            tool_messages = [
                tool_result_to_message(tr) for tr in tool_results
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
        logger.info(f'Agent loop ended in {step} steps.')