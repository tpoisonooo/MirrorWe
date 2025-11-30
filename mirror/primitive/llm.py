"""LLM server proxy."""
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
from .utils import get_env_or_raise, get_env_with_default

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

    def add(self, query: str, response: str, backend:str):
        _hash = self.hash(query)
        
        with DB(self.file_path) as db:
            db.execute('''
                INSERT OR IGNORE INTO chat (_hash, query, response, backend)
                VALUES (?, ?, ?, ?)
            ''', (_hash, query, response, backend))
        
    def get(self, query: str, backend:str) -> Union[str, None]:
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

backend2url = {
    "kimi": "https://api.moonshot.cn/v1",
    'siliconcloud': 'https://api.siliconflow.cn/v1',
    'aliyun': 'https://dashscope.aliyuncs.com/compatible-mode/v1',
    'local': 'http://198.11.18.24:3000/v1'
}

backend2model = {
    "kimi": "kimi-k2-turbo-preview",
    "siliconcloud": "Qwen/Qwen2.5-14B-Instruct",
    "aliyun": "qwen3-30b-a3b-instruct-2507",
    "local": "vllm"
}

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


class Backend:

    def __init__(self):
        self.api_key = get_env_or_raise('LLM_API_KEY')
        self.max_token_size = int(get_env_or_raise('LLM_MAX_TOKEN_SIZE'))
        self.rpm = RPM(int(get_env_or_raise('LLM_RPM')))
        self.tpm = TPM(int(get_env_or_raise('LLM_TPM')))
        self.name = get_env_with_default('LLM_TYPE', 'kimi')
        self.base_url =  get_env_with_default('LLM_BASE_URL', '')
        self.model = get_env_with_default('LLM_MODEL', '')
        # 如果没填，尝试按名字给个默认值
        if not self.base_url and self.name in backend2url:
            self.base_url = backend2url[self.name]
        if not self.model and self.name in backend2model:
            self.model = backend2model[self.name]

    def jsonify(self):
        return {"api_key": self.name, "model": self.model}

    def __str__(self):
        return json.dumps(self.jsonify())

class LLM:

    def __init__(self):
        """Initialize the LLM with the path of the configuration file."""
        self.backend = Backend()
        self.sum_input_token_size = 0
        self.sum_output_token_size = 0
        self.cache = ChatCache()

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=30, max=60),
        retry=retry_if_exception_type(
            (RateLimitError, APIConnectionError, Timeout, APITimeoutError)),
    )
    @limit_async_func_call(16)
    async def chat(self,
                   prompt: str,
                   system_prompt=None,
                   history=[],
                   allow_truncate=False,
                   max_tokens=8192,
                   timeout=600,
                   enable_cache:bool=True) -> str:
        if enable_cache:
            r = self.cache.get(query=prompt, backend=self.backend.name)
            if r is not None:
                logger.info('LLM cache hit')
                return r
        
        # try truncate input prompt
        input_tokens = encode_string(content=prompt)
        input_token_size = len(input_tokens)
        if input_token_size > self.backend.max_token_size:
            if not allow_truncate:
                raise Exception(
                    f'input token size {input_token_size}, max {self.backend.max_token_size}'
                )

            tokens = input_tokens[0:self.backend.max_token_size - input_token_size]
            prompt = decode_tokens(tokens=tokens)
            input_token_size = len(tokens)

        await self.backend.tpm.wait(token_count=input_token_size)

        # build messages
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        else:
            time_str = datetime.now().strftime("当前时间：%Y年%m月%d日 %H时%M分%S秒")
            messages.append({"role": "system", "content": time_str})
        
        messages.extend(history)
        messages.append({"role": "user", "content": prompt})

        content = ''
        # try:
        openai_async_client = AsyncOpenAI(base_url=self.backend.base_url,
                                          api_key=self.backend.api_key,
                                          timeout=timeout)
        # response = await openai_async_client.chat.completions.create(model=model, messages=messages, max_tokens=8192, temperature=0.7, top_p=0.7, extra_body={'repetition_penalty': 1.05})

        kwargs = {
            "model": self.backend.model,
            "messages": messages,
            "extra_body": {"enable_thinking": False}
        }
        if max_tokens:
            kwargs['max_tokens'] = max_tokens

        response = await openai_async_client.chat.completions.create(**kwargs)
        if response.choices is None:
            pass
        logger.info(response.choices[0].message.content)

        content = response.choices[0].message.content
        self.cache.add(query=prompt, response=content, backend=self.backend.name)
        
        # except Exception as e:
        #     logger.error( str(e) +' input len {}'.format(len(str(messages))))
        #     raise e
        content_token_size = len(encode_string(content=content))

        if False:
            dump_json = {"messages": messages, "reply": content}
            dump_json_str = json.dumps(dump_json, ensure_ascii=False)
            with open('llm.jsonl', 'w') as f:
                f.write(dump_json_str)
                f.write('\n')

        self.sum_input_token_size += input_token_size
        self.sum_output_token_size += content_token_size

        await self.backend.tpm.wait(token_count=content_token_size)
        await self.backend.rpm.wait()

        think_tag = "</think>"
        index = content.find(think_tag)
        if index > 0:
            content = content[index+len(think_tag):]
        return content

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=30, max=60),
        retry=retry_if_exception_type(
            (RateLimitError, APIConnectionError, Timeout, APITimeoutError)),
    )
    async def chat_stream(self,
                          prompt: str,
                          backend: str = 'default',
                          system_prompt=None,
                          history=[],
                          allow_truncate=False,
                          max_tokens=1024,
                          timeout=600,
                          enable_cache:bool=True) -> AsyncGenerator[str, None]:
    
        if enable_cache:
            r = self.cache.get(query=prompt, backend=backend)
            if r is not None:
                for char in r:
                    yield char
                return

        # try truncate input prompt
        input_tokens = encode_string(content=prompt)
        input_token_size = len(input_tokens)
        if input_token_size > self.backend.max_token_size:
            if not allow_truncate:
                raise Exception(
                    f'input token size {input_token_size}, max {self.backend.max_token_size}'
                )

            tokens = input_tokens[0:self.backend.max_token_size - input_token_size]
            prompt = decode_tokens(tokens=tokens)
            input_token_size = len(tokens)

        await self.backend.tpm.wait(token_count=input_token_size)

        # build messages
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.extend(history)
        messages.append({"role": "user", "content": prompt})

        content = ''
        try:
            openai_async_client = AsyncOpenAI(base_url=self.backend.base_url,
                                              api_key=self.backend.api_key,
                                              timeout=timeout)

            print(messages)
            stream = await openai_async_client.chat.completions.create(
                model=self.backend.model,
                messages=messages,
                max_tokens=self.backend.max_token_size - input_token_size,
                stream=True)

            async for chunk in stream:
                if chunk.choices is None:
                    raise Exception(str(chunk))
                delta = chunk.choices[0].delta
                if delta.content:
                    content += delta.content
                    yield delta.content

        except Exception as e:
            logger.error(str(e) + ' input len {}'.format(len(str(messages))))
            raise e
        content_token_size = len(encode_string(content=content))
        self.cache.add(query=prompt, response=content, backend=self.backend.name)

        self.sum_input_token_size += input_token_size
        self.sum_output_token_size += content_token_size

        await self.backend.tpm.wait(token_count=content_token_size)
        await self.backend.rpm.wait()
        return

    def chat_sync(self,
                  prompt: str,
                  system_prompt=None,
                  history=[]):
        loop = always_get_an_event_loop()
        return loop.run_until_complete(
            self.chat(prompt=prompt,
                      system_prompt=system_prompt,
                      history=history))
