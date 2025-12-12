import asyncio
import os
import textwrap
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

from .actor.helper import build_toolset
import asyncio

load_dotenv()


async def agent_loop(chat_provider: ChatProvider, toolset: Toolset):
    system_prompt = "You are a helpful assistant."
    history: list[Message] = []

    while True:
        user_input = input("You: ").strip()
        if not user_input:
            continue
        if user_input.lower() in {"exit", "quit"}:
            break

        history.append(Message(role="user", content=user_input))

        step = 0
        max_step_size = 20
        while step < max_step_size:
            step += 1
            result = await kosong.step(
                chat_provider=chat_provider,
                system_prompt=system_prompt,
                toolset=toolset,
                history=history,
            )

            await asyncio.sleep(2)

            tool_results = await result.tool_results()
            assistant_message = result.message
            tool_messages = [tool_result_to_message(tr) for tr in tool_results]

            if s := assistant_message.extract_text():
                print("Assistant:\n", textwrap.indent(s, "  "))
            for tool_msg in tool_messages:
                if s := tool_msg.extract_text():
                    print("Tool:\n", textwrap.indent(s, "  "))

            if not result.tool_calls:
                break

            history.append(result.message)
            history.extend(tool_messages)


def tool_result_to_message(result: ToolResult) -> Message:
    return Message(
        role="tool",
        tool_call_id=result.tool_call_id,
        content=result.return_value.output,
    )


async def main():
    provider = 'kimi'
    provider_upper = provider.upper()
    base_url = os.getenv(f"{provider_upper}_BASE_URL")
    api_key = os.getenv(f"{provider_upper}_API_KEY")
    model = os.getenv(f"{provider_upper}_MODEL_NAME")

    base_url = base_url or "https://api.moonshot.ai/v1"
    assert api_key is not None, "Expect KIMI_API_KEY environment variable"
    model = model or "kimi-k2-turbo-preview"

    chat_provider = Kimi(base_url=base_url, api_key=api_key, model=model)

    toolset = build_toolset()
    # 找到 🎈 的联系方式，想办法给他发条消息。内容随意，写个她可能感兴趣会回复的话题。 或者告诉她 “你老公一会儿下班”
    await agent_loop(chat_provider, toolset)


asyncio.run(main())
