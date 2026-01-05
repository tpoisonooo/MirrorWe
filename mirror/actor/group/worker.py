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
from ...core.topic import Topic
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

        # Consider topic evolution as well
        topics = g.get_all_topics()
        if topics:
            logger.info(f"Group {g.group_id}: Evaluating evolution for {len(topics)} topics")

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

        try:
            # Get current topic if available
            current_topic = g.get_current_topic()
            topic_context = ""
            
            if current_topic:
                topic_context = f"\n当前话题: {current_topic.name}\n"
                # Get recent messages from current topic for better context
                topic_messages = current_topic.get_recent_messages(10)
                if topic_messages:
                    topic_context += "话题上下文:\n"
                    for msg in topic_messages[-5:]:  # Last 5 messages from topic
                        topic_context += f"- {msg.content[:100]}\n"
            else:
                topic_context = "\n当前话题: 默认话题\n"

            history: list[Message] = []
            step = 0
            max_step_size = 3

            system_prompt = '{}{}\n\n{}'.format(
                time_string(), topic_context, load_desc(Path(__file__).parent / "self.md", {}))
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
                        
                        # Also add to current topic if available
                        if current_topic:
                            # Create a mock message for the topic
                            from ...wechat.message import Message as WkMessage
                            mock_msg = WkMessage()
                            mock_msg.content = send_text
                            mock_msg.sender_id = 'bot'
                            mock_msg._type = '80001'
                            await current_topic.add_message(mock_msg, 'bot')

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

        finally:
            self.state.remove(g.group_id)

    async def process_topic_specific(self, g: Group, topic: Topic, p: Person):
        """Process messages within a specific topic context."""
        if g.group_id in self.state:
            logger.info(f'Group {g.group_id} is already being processed, skipping topic-specific processing...')
            return
        
        self.state.add(g.group_id)
        
        try:
            history: list[Message] = []
            step = 0
            max_step_size = 2  # Limit steps for topic-specific processing

            # Build topic-specific system prompt
            topic_summary = topic.get_summary()
            system_prompt = '{}{}\n\n{}'.format(
                time_string(), 
                f"\n话题上下文: {topic.name}\n{topic_summary}\n",
                load_desc(Path(__file__).parent / "self.md", {}))
            
            input_template = (Path(__file__).parent /
                              "input.md").read_text(encoding="utf-8")

            # Use topic-specific context
            topic_messages = topic.get_recent_messages(15)
            if topic_messages:
                current = topic_messages[-1]
                local = topic_messages[-14:-1] if len(topic_messages) > 1 else []
            else:
                # Fallback to group memory
                current = g.memory.group[-1] if g.memory.group else None
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
                
                direct_break = False
                
                for tool_call in result.tool_calls:
                    if tool_call.function.name == Finish.name:
                        direct_break = True
                        break

                    if tool_call.function.name == SendGroupText.name:
                        # Handle group text sending within topic context
                        try:
                            tool_call_arguments = json.loads(tool_call.function.arguments)
                            send_text = tool_call_arguments.get('text', '')
                            group_id = tool_call_arguments.get('group_id', '')
                        except Exception as e:
                            logger.error(f'Parse tool_call_arguments failed, {str(e)}: {str(tool_call.function.arguments)}')
                            send_text = tool_call.function.arguments
                            group_id = ''

                        inner = build_self_inner(sender_name=self.name, content=send_text, group_id=group_id)
                        # Add to both group memory and topic memory
                        g.memory.add(group=inner)
                        
                        # Create mock message for topic
                        from ...wechat.message import Message as WkMessage
                        mock_msg = WkMessage()
                        mock_msg.content = send_text
                        mock_msg.sender_id = 'bot'
                        mock_msg._type = '80001'
                        await topic.add_message(mock_msg, 'bot')

                if direct_break:
                    break

                if not result.tool_calls:
                    break

                history.append(result.message)
                history.extend([tool_result_to_message(tr) for tr in tool_results])

        finally:
            self.state.remove(g.group_id)