"""LLM proxy."""
import json
import pdb
import os
from .limitter import RPM, TPM
from .utils import always_get_an_event_loop
import asyncio
from typing import Dict, List, Dict, Union, AsyncGenerator
import pytoml
from loguru import logger
from openai import AsyncOpenAI, APIConnectionError, RateLimitError, Timeout, APITimeoutError
from .token import encode_string, decode_tokens
from tenacity import (
    retry,
    stop_after_attempt,
    wait_exponential,
    retry_if_exception_type,
)
from functools import wraps
import sqlite3
import uuid
import hashlib
from datetime import datetime

from .db import DB
from .utils import get_env_or_raise, get_env_with_default, time_string

from kosong.chat_provider.kimi import Kimi
from kosong.message import ContentPart, Message, TextPart, ThinkPart, ToolCall, ToolCallPart
from kosong.tooling import Tool
from kosong.chat_provider import APIStatusError, StreamedMessagePart


class ChatCache:

    def __init__(self, file_path: str = '.cache_llm'):
        self.file_path = file_path
        with DB(self.file_path) as db:
            db.execute('''
                CREATE TABLE IF NOT EXISTS chat (
                    _hash TEXT PRIMARY KEY,
                    query TEXT,
                    response TEXT,
                    backend TEXT
                )
            ''')

    def hash(self, content: str) -> str:
        md5 = hashlib.md5()
        if type(content) is str:
            md5.update(content.encode('utf8'))
        else:
            md5.update(content)
        return md5.hexdigest()[0:6]

    def add(self, query: str, response: str, backend: str = 'default'):
        _hash = self.hash(query)

        with DB(self.file_path) as db:
            db.execute(
                '''
                INSERT OR IGNORE INTO chat (_hash, query, response, backend)
                VALUES (?, ?, ?, ?)
            ''', (_hash, query, response, backend))

    def get(self, query: str, backend: str = 'default') -> Union[str, None]:
        """Retrieve a chunk by its ID."""
        if not query:
            return None
        _hash = self.hash(query)

        with DB(self.file_path) as db:
            db.execute(
                'SELECT response FROM chat WHERE _hash = ? and backend = ?',
                (_hash, backend))
            r = db.fetchone()
            if r:
                return r[0]
            return None


os.environ["TOKENIZERS_PARALLELISM"] = "false"


def limit_async_func_call(max_size: int, waitting_time: float = 0.1):
    """Add restriction of maximum async calling times for a async func"""

    def final_decro(func):
        """Not using async.Semaphore to aovid use nest-asyncio"""
        __current_size = 0

        @wraps(func)
        async def wait_func(*args, **kwargs):
            nonlocal __current_size
            while __current_size >= max_size:
                await asyncio.sleep(waitting_time)
            __current_size += 1
            result = await func(*args, **kwargs)
            __current_size -= 1
            return result

        return wait_func

    return final_decro


class LLM:

    def __init__(self):
        """Initialize the LLM with the path of the configuration file."""
        self.cache = ChatCache()
        self.rpm = RPM(int(get_env_or_raise('LLM_RPM')))
        self.tpm = TPM(int(get_env_or_raise('LLM_TPM')))
        self.max_token_size = int(get_env_or_raise('LLM_MAX_TOKEN_SIZE'))
        self.sum_input_token_size = 0
        self.sum_output_token_size = 0
        self.provider = Kimi(model=get_env_or_raise("KIMI_MODEL_NAME"))

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=30, max=60),
        retry=retry_if_exception_type(
            (RateLimitError, APIConnectionError, Timeout, APITimeoutError)),
    )
    @limit_async_func_call(16)
    async def chat_text(self,
                        prompt: str,
                        system_prompt=None,
                        tools=[]) -> str:
        """Chat with text response."""
        llm_cache_enable = get_env_with_default('LLM_CACHE_ENABLE', False)
        if llm_cache_enable:
            r = self.cache.get(query=prompt, backend=self.provider.model)
            if r is not None:
                logger.info('LLM cache hit')
                return r

        # 计算 TPM，看是否需要等待
        input_tokens = encode_string(content=prompt)
        input_token_size = len(input_tokens)
        await self.tpm.wait(token_count=input_token_size)

        # 如果没 system，给个当前时间戳
        if not system_prompt:
            system_prompt = time_string()

        text_part = TextPart(text='')
        async for part in await self.provider.generate(
                system_prompt=system_prompt,
                tools=tools,
                history=[
                    Message(role="user", content=[TextPart(text=prompt)])
                ],
        ):
            text_part.merge_in_place(part)

        content = text_part.text
        self.cache.add(query=prompt,
                       response=content,
                       backend=self.provider.model)

        content_token_size = len(encode_string(content=content))

        self.sum_input_token_size += input_token_size
        self.sum_output_token_size += content_token_size

        await self.tpm.wait(token_count=content_token_size)
        await self.rpm.wait()
        return content
