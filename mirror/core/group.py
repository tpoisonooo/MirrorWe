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
from .inner import convert_to_inner, Inner, parse_multi_inner_async, dump_multi_inner_sync, dump_multi_inner_async
from .inner import convert_wkteam_to_inner

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

        current_file = inspect.getfile(self.__class__)
        data_dir = os.path.join(os.path.dirname(current_file), "..", "..",
                                "data")
        self.group_dir = os.path.join(data_dir, 'groups', self.group_id)
        self.basic_path = os.path.join(self.group_dir, "basic.json")
        self.group_path = os.path.join(self.group_dir, "message.jsonl")
        self.llm = LLM()
        self.bio_path = os.path.join(self.group_dir, "bio.md")
        self.bio = ""

        self.summary_path = os.path.join(self.group_dir, "summary.md")
        self.summary = ""

        # 群聊累计达到 threshold 条消息，就只保留末尾 max_keep 条有效的
        # 同时开始更新 bio
        self.threshold = 4096
        self.max_keep = 1024
        self.update_counter = 0

        # 销毁遗言，保留数据
        self._wr = weakref.ref(self)
        atexit.register(self._atexit_dump)

    async def initialize(self):
        # 加载数据
        async for inner in parse_multi_inner_async(self.group_path):
            self.memory.add(group=inner)

        # 加载基本信息
        self.basic = await try_load_text(self.basic_path)
        self.bio = await try_load_text(self.bio_path)
        self.summary = await try_load_text(self.summary_path)
        
        # 扔个空消息，触发分析
        await self.update(wk_msg=None)

    def _atexit_dump(self):
        me = self._wr()

        if me is None:
            logger.info('Group 对象已被销毁，跳过保存消息偏移')
            return

        if me.memory is None:
            logger.info('Group 内存为空，跳过保存消息')
            return
        logger.info(
            f'Group {me.group_id}: 正在保存 {len(me.memory.group)} 条群聊消息...')
        dump_multi_inner_sync(me.group_path, me.memory.group, mode='write')
        logger.info(f'Group {me.group_id}: 完成保存消息')

    async def update(self, wk_msg: Message):
        """更新消息数据，触发个性分析"""
        self.update_counter += 1
        if wk_msg:
            # 如果是群聊消息，加 group
            inner = convert_wkteam_to_inner(wk_msg)
            if wk_msg._type.startswith('8'):
                self.memory.add(group=inner)

        if len(self.memory) >= self.threshold:
            logger.info(
                f"Group {self.group_id}: 消息数量达到 {len(self.memory.group)} 条，开始生成群画像"
            )
            await self.brief_bio()
            self.memory.group = self.memory.group[-self.max_keep:]
            await dump_multi_inner_async(self.group_path,
                                         self.memory.group,
                                         mode='write')
            logger.info(
                f"Group {self.group_id}: 当前 {len(self.memory.group)} 条群聊消息，完成个性分析"
            )
        elif self.update_counter > 0 and self.update_counter % 5 == 0:
            await dump_multi_inner_async(self.group_path,
                                         self.memory.group,
                                         mode='write')

    async def brief_bio(self) -> str:
        """生成群的  bio.md 文件"""
        basic = await try_load_text(self.basic_path)
        bio_path = os.path.join(self.group_dir, "bio.md")
        bio = await try_load_text(bio_path)

        if len(self.memory.group) < 64:
            return ""  # 无法生成画像

        # 按 LLM 最大长度，截断百分之多少上下文
        max_text_size = self.llm.max_token_size * 2 * 0.7
        cur_text_size = len(basic) + len(bio) + len(str(self.memory.group))
        cut_ratio = max_text_size / cur_text_size
        if cut_ratio > 1.0:
            cut_group_index = 0
        else:
            cut_group_index = max(0, int(cut_ratio * len(self.memory.group)))

        group = self.memory.group[-cut_group_index:]
        group_json_str = Inner.schema().dumps(group,
                                              many=True,
                                              ensure_ascii=False)
        prompt = GROUP_BIO.format(basic=basic, bio=bio, group=group_json_str)
        # 使用新的LLM适配器
        try:
            self.bio = await self.llm.chat_text(prompt)
        except Exception as e:
            self.bio = str(e)
        await safe_write_text(bio_path, self.bio)

        prompt = SUMMARY_BIO.format(bio=self.bio)
        self.summary = await self.llm.chat_text(prompt=prompt)
        await safe_write_text(self.summary_path, self.summary)