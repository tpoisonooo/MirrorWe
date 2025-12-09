"""
增强版 Person 类，支持加载本地消息数据
"""

from abc import ABC, abstractmethod
import json
import os
import sys
import inspect
import aiofiles
from pathlib import Path
from typing import List, Dict, Any
from loguru import logger
from ..prompt import GROUP_BIO
from ..primitive import parse_multiline_json_objects_async, dump_multiline_json_objects_async
from ..primitive import try_load_text, safe_write_text
from ..primitive import LLM
from datetime import datetime

# 添加项目路径
from mirror.core.memory import MemoryStream

# TODO
class Group(ABC):
    """ Group 类，支持加载本地消息数据"""
    
    def __init__(self, wxid: str):
        self.wxid = wxid
        self.memory = MemoryStream()
        self.bio = ""

        current_file = inspect.getfile(self.__class__)
        data_dir = os.path.join(os.path.dirname(current_file), "..", "..", "data")
        self.wxid_dir = os.path.join(data_dir, 'groups', self.wxid)
        self.basic_path = os.path.join(self.wxid_dir, "basic.json")
        self.group_path = os.path.join(self.wxid_dir, "message.jsonl")
        self.llm = LLM()

        # 群聊累计达到 threshold 条消息，就只保留末尾 max_keep 条有效的
        # 同时开始更新 bio
        self.threshold = 4096
        self.max_keep = 1024

    async def update(self):
        # 尝试加载本地消息数据
        group_file_size = os.path.getsize(self.group_path) if os.path.exists(self.group_path) else 0

        # 没啥消息的空群，跳过
        if group_file_size < 32*1024 and not os.path.exists(self.basic_path):
            return

        await self.load_local([self.group_path])
        if len(self.memory) >= self.threshold:
            await self.brief_bio()
            await dump_multiline_json_objects_async(self.group_path, self.memory.group[-self.max_keep:])

    async def brief_bio(self) -> str:
        """生成群的  bio.md 文件"""
        basic = await try_load_text(self.basic_path)
        bio_path = os.path.join(self.wxid_dir, "bio.md")
        bio = await try_load_text(bio_path)

        if not basic and not self.memory.private and len(self.memory.group) < 64:
            return "" # 无法生成画像
        
        # 按 LLM 最大长度，截断百分之多少上下文
        max_text_size = self.llm.backend.max_token_size * 2 * 0.7
        cur_text_size = len(basic) + len(bio) + len(str(self.memory.private)) + len(str(self.memory.group))
        cut_ratio = max_text_size / cur_text_size
        if cut_ratio > 1.0:
            cut_group_index = 0
        else:
            cut_group_index = max(0, int(cut_ratio * len(self.memory.group)))

        group = self.memory.group[-cut_group_index:]
        prompt = GROUP_BIO.format(
            basic=basic,
            bio=bio,
            group=json.dumps(group, ensure_ascii=False, indent=2))
        # 使用新的LLM适配器
        try:
            self.bio = await self.llm.chat_text(prompt)
        except Exception as e:
            self.bio = str(e)

        await safe_write_text(bio_path, self.bio)

    async def load_local(self, message_files: List[str]):
        """加载 message.jsonl 文件"""
        try:
            total_loaded = 0
            # 解析多行JSON格式
            for messages_file in message_files:
                if not os.path.exists(messages_file):
                    continue
                
                file_loaded = 0
                async for obj in parse_multiline_json_objects_async(messages_file):
                    data = obj.get('data', {})
                    is_self = data.get('self', False)
                    content = data.get('content', '').strip()
                    name = data.get('pushContent', ':').split(':')[0].strip()
                    ts = data.get('timestamp', 0)

                    if obj.get('messageType') == '80001':
                        message = {"content":f"{name}:{content}", "ts":ts}
                        self.memory.add(group_chat=message)
                        file_loaded += 1
                
                total_loaded += file_loaded
                logger.info(f"从 {messages_file} 加载了 {file_loaded} 条有效消息")
            
            logger.info(f"总共加载了 {total_loaded} 条有效消息")
            
        except Exception as e:
            logger.error(f"加载本地消息数据失败: {e}")
            import traceback
            traceback.print_exc()
    