from __future__ import annotations

import asyncio
import json
import textwrap
from pathlib import Path

import aiofiles
import kosong
from dotenv import load_dotenv
from kosong.message import Message, TextPart
from loguru import logger

from ...core import Person, build_self_inner
from ...primitive import load_desc, time_string
from ...tool.message import (
    SendGroupText,
)
from ...tool.think import Finish
from ..base import ActorBase
from ..helper import build_toolset, tool_result_to_message

load_dotenv()

class GroupActor(ActorBase):

    def __init__(self):
        super().__init__()

        self.name = 'MirrorWe'
        # lock by group_id
        self.state = set()
        logger.info(f'Awake {__name__}')

    async def evolution(self, g: Group):
        step = g.max_keep / 4
        if len(g.memory.group) < step:
            return  # 消息量不足，不进行进化

        if len(g.memory.group) % step != 0:
            return  # 每 256 条消息进化一次

        import pdb; pdb.set_trace()
        template = (Path(__file__).parent / "evolution.md").read_text(encoding="utf-8")
        prompt = template.format(name=self.name, bio=g.bio, history=g.memory.recent_group_json_str(limit=step))
        
        text_part = TextPart(text='')

        async for part in await self.chat_provider.generate(system_prompt=time_string(), tools=[], history=[Message(role="user", content=prompt)]):
            text_part.merge_in_place(part)

        try:
            json_str = text_part.text.strip()
            clean_json_str = json_str[8:-4] if json_str.startswith('```json\n') and json_str.endswith('\n```') else json_str
            
            evolution_data = json.loads(clean_json_str)
            decision = evolution_data.get("decision", "no").lower()
            content = evolution_data.get("content", "")
            if decision == "yes" and content:
                async with aiofiles.open(str(Path(__file__).parent / "self.md"), "w", encoding='utf-8') as f:
                    await f.write(content + '\n')
                    await f.flush()
                logger.info("Updated group actor description successfully.")
        except Exception as e:
            logger.error(f"Failed to parse evolution data: {e}")

    async def agent_loop(self, g: Group, p: Person):
        if g.group_id in self.state:
            logger.info(f'Group {g.group_id} is already being processed, skipping...')
            return
        self.state.add(g.group_id)

        history: list[Message] = []
        step = 0
        max_step_size = 3

        system_prompt = '{}\n\n{}'.format(
            time_string(), load_desc(Path(__file__).parent / "self.md", {}))
        input_template = (Path(__file__).parent /
                          "input.md").read_text(encoding="utf-8")

        current = g.memory.group[-1]
        local = g.memory.group[-30:-1] if len(g.memory.group) > 1 else []
        content = input_template.format(
                                        now=time_string(),
                                        current=current,
                                        person_summary=p.summary,
                                        group_summary=g.summary,
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
            
            direct_break = False
            
            for tool_call in result.tool_calls:
                if tool_call.function.name == Finish.name:
                    direct_break = True
                    break

                if tool_call.function.name == SendGroupText.name:
                    # 取回参数
                    try:
                        tool_call_arguments = json.loads(tool_call.function.arguments)
                        send_text = tool_call_arguments.get('text', '')
                        group_id = tool_call_arguments.get('group_id', '')
                        # 群聊每次最多发送 1 条消息
                        # TODO wait kosong upgrade to support removing tool by life
                        # toolset.remove(SendGroupText.name)
                    except Exception as e:
                        logger.error(f'Parse tool_call_arguments failed, {str(e)}: {str(tool_call.function.arguments)}')
                        send_text = tool_call.function.arguments
                        group_id = ''

                    inner = build_self_inner(sender_name=self.name, content=send_text, group_id=group_id)
                    # 群聊里需要加一下 actor 发过的消息
                    g.memory.add(group=inner)

            if direct_break:
                break

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

        self.state.remove(g.group_id)