"""
增强版 Person 类，支持加载本地消息数据
"""

from abc import ABC, abstractmethod
import json
import os
import sys
import inspect
import aiofiles
import weakref
import atexit
from pathlib import Path
from typing import List, Dict, Any
from loguru import logger
from ..prompt import GROUP_BIO, SUMMARY_BIO
from .inner import convert_json_to_inner, Inner, parse_multi_inner_async, dump_multi_inner_async
from ..primitive import try_load_text, safe_write_text
from ..primitive import LLM
from datetime import datetime
from ..wechat.message import Message

# 添加项目路径
from mirror.core.memory import MemoryStream
from mirror.primitive import always_get_an_event_loop

# TODO
class Group(ABC):
    """ Group 类，支持加载本地消息数据"""
    
    def __init__(self, group_id: str):
        self.group_id = group_id
        self.memory = MemoryStream()
        self.bio = ""

        current_file = inspect.getfile(self.__class__)
        data_dir = os.path.join(os.path.dirname(current_file), "..", "..", "data")
        self.group_dir = os.path.join(data_dir, 'groups', self.group_id)
        self.basic_path = os.path.join(self.group_dir, "basic.json")
        self.group_path = os.path.join(self.group_dir, "message.jsonl")
        self.offset = 0
        self.llm = LLM()
        self.bio_path = os.path.join(self.group_dir, "bio.md")

        # 群聊累计达到 threshold 条消息，就只保留末尾 max_keep 条有效的
        # 同时开始更新 bio
        self.threshold = 4096
        self.max_keep = 1024

        # 销毁遗言，保留数据
        self._wr = weakref.ref(self)
        atexit.register(self._atexit_dump)

    async def initialize(self):
        # 加载数据
        async for inner in parse_multi_inner_async(self.private_path):
            self.memory.add(private=inner)
        async for inner in parse_multi_inner_async(self.group_path):
            self.memory.add(group=inner)
        # 消息加载偏移
        self.offset = len(self.memory.group)
        
        # 对方名字
        self.name = self.memory.private[0].sender_name if self.memory.private else self.memory.group[0].sender_name
        
        self.basic = await try_load_text(self.basic_path)
        self.bio = await try_load_text(self.bio_path)
        # 扔个空消息，触发分析
        await self.update(wk_msg=None)

    def _atexit_dump(self):
        me = self._wr()
        
        if me is None:   
            logger.info('Group 对象已被销毁，跳过保存消息偏移')           
            return

        async def _dump(me):
            """将当前内存中的消息追加到文件末尾，析构时调用"""
            group_offset = me.offset
            if len(me.memory.group) > group_offset:
                await dump_multi_inner_async(
                    me.group_path, me.memory.group[group_offset:], mode='append')
        
        loop = always_get_an_event_loop()
        logger.info(f'Group {me.group_id}: 正在保存消息偏移...')
        loop.run_until_complete(_dump(me))
        logger.info(f'Group {me.group_id}: 完成保存消息偏移')

    async def update(self, wk_msg: Message):
        """更新消息数据，触发个性分析"""
        if wk_msg:
            # 如果是群聊消息，加 group
            inner = convert_json_to_inner(wk_msg) 
            if hasattr(wk_msg, '_type') and str(wk_msg._type) in ['80001', '80001']:
                self.memory.add(group=inner)

        if len(self.memory) >= self.threshold:
            await self.brief_bio()
            self.memory.group = self.memory.group[-self.max_keep:]
            self.offset = 0
            logger.info(f"Group {self.group_id}: 当前 {len(self.memory.group)} 条群聊消息，完成个性分析")

    async def brief_bio(self) -> str:
        """生成群的  bio.md 文件"""
        basic = await try_load_text(self.basic_path)
        bio_path = os.path.join(self.group_dir, "bio.md")
        bio = await try_load_text(bio_path)

        if len(self.memory.group) < 64:
            return "" # 无法生成画像
        
        # 按 LLM 最大长度，截断百分之多少上下文
        max_text_size = self.llm.max_token_size * 2 * 0.7
        cur_text_size = len(basic) + len(bio) + len(str(self.memory.group))
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

        prompt = SUMMARY_BIO.format(bio=self.bio)
        summary = await self.llm.chat_text(prompt=prompt)
        summary_path = os.path.join(self.group_dir, 'summary.md')
        await safe_write_text(summary_path, summary)

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
                        self.memory.add(group=message)
                        file_loaded += 1
                
                total_loaded += file_loaded
                logger.info(f"从 {messages_file} 加载了 {file_loaded} 条有效消息")
            
            logger.info(f"总共加载了 {total_loaded} 条有效消息")
            
        except Exception as e:
            logger.error(f"加载本地消息数据失败: {e}")
            import traceback
            traceback.print_exc()
    