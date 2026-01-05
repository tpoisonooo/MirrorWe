"""
增强版 Person 类，支持加载本地消息数据
"""

import atexit
import inspect
import os
import weakref
from abc import ABC
from typing import Dict, List, Optional

from loguru import logger

# 添加项目路径
from mirror.core.memory import MemoryStream

from ..primitive import LLM, safe_write_text, try_load_text
from ..prompt import GROUP_BIO, SUMMARY_BIO
from ..wechat.message import Message
from .inner import (
    Inner,
    convert_wkteam_to_inner,
    dump_multi_inner_async,
    dump_multi_inner_sync,
    parse_multi_inner_async,
)
from .topic import Topic
from .topic_classifier import TopicClassifier


# TODO
class Group(ABC):
    """ Group 类，支持加载本地消息数据和话题管理"""

    def __init__(self, group_id: str):
        self.group_id = group_id
        self.memory = MemoryStream()
        
        # Topic management
        self.topics: Dict[str, Topic] = {}
        self.topic_classifier = TopicClassifier()
        self.current_topic_id: Optional[str] = None

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
        
        # 加载现有话题
        await self._load_topics()
        
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

    async def _load_topics(self):
        """Load existing topics from disk."""
        topics_dir = os.path.join(self.group_dir, "topics")
        if not os.path.exists(topics_dir):
            return
        
        for topic_id in os.listdir(topics_dir):
            topic_dir = os.path.join(topics_dir, topic_id)
            if os.path.isdir(topic_dir):
                try:
                    # Load topic info
                    topic_info_path = os.path.join(topic_dir, "topic_info.json")
                    if os.path.exists(topic_info_path):
                        content = await try_load_text(topic_info_path)
                        if content:
                            info = json.loads(content)
                            topic = Topic(
                                topic_id=topic_id,
                                name=info.get('name', topic_id),
                                group_id=self.group_id
                            )
                            self.topics[topic_id] = topic
                            logger.info(f"Loaded topic: {topic.name} ({topic_id})")
                except Exception as e:
                    logger.warning(f"Failed to load topic {topic_id}: {e}")

    async def update(self, wk_msg: Message, person_id: str = None):
        """更新消息数据，触发个性分析，支持话题分类"""
        self.update_counter += 1
        
        if wk_msg:
            # 如果是群聊消息，进行话题分类
            if wk_msg._type.startswith('8'):
                # Convert to Inner format for main memory
                inner = convert_wkteam_to_inner(wk_msg)
                self.memory.add(group=inner)
                
                # Classify message into topic
                if person_id:
                    await self._classify_into_topic(wk_msg, person_id)
            else:
                # 非群聊消息，按原逻辑处理
                inner = convert_wkteam_to_inner(wk_msg)
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

    async def _classify_into_topic(self, message: Message, person_id: str):
        """Classify a message into an appropriate topic."""
        try:
            # Get recent messages for context
            recent_messages = []
            if self.memory.group:
                recent_messages = [
                    {
                        'person_id': msg.person if hasattr(msg, 'person') else 'unknown',
                        'content': msg.content,
                        'timestamp': msg.ts.isoformat() if hasattr(msg, 'ts') else ''
                    }
                    for msg in self.memory.group[-20:]  # Last 20 messages
                ]
            
            # Get recent topics
            recent_topics = list(self.topics.values())
            
            # Classify the message
            topic_id, topic_name, confidence = await self.topic_classifier.classify_message(
                message, recent_topics, recent_messages
            )
            
            # Create new topic if it doesn't exist
            if topic_id not in self.topics:
                topic = Topic(topic_id=topic_id, name=topic_name, group_id=self.group_id)
                self.topics[topic_id] = topic
                logger.info(f"Created new topic: {topic_name} ({topic_id}) with confidence {confidence:.2f}")
            
            # Add message to topic
            topic = self.topics[topic_id]
            await topic.add_message(message, person_id)
            self.current_topic_id = topic_id
            
            logger.debug(f"Message classified to topic '{topic_name}' with confidence {confidence:.2f}")
            
        except Exception as e:
            logger.error(f"Error classifying message into topic: {e}")
            # Fallback: create a default topic
            if 'default' not in self.topics:
                self.topics['default'] = Topic(topic_id='default', name='默认话题', group_id=self.group_id)
            
            await self.topics['default'].add_message(message, person_id)
            self.current_topic_id = 'default'

    def get_current_topic(self) -> Optional[Topic]:
        """Get the current active topic."""
        if self.current_topic_id and self.current_topic_id in self.topics:
            return self.topics[self.current_topic_id]
        return None
    
    def get_topic(self, topic_id: str) -> Optional[Topic]:
        """Get a specific topic by ID."""
        return self.topics.get(topic_id)
    
    def get_all_topics(self) -> List[Topic]:
        """Get all topics for this group."""
        return list(self.topics.values())
    
    def get_recent_topics(self, limit: int = 10) -> List[Topic]:
        """Get recently active topics sorted by last updated time."""
        topics = list(self.topics.values())
        topics.sort(key=lambda t: t.last_updated, reverse=True)
        return topics[:limit]

    async def brief_bio(self) -> str:
        """生成群的  bio.md 文件，包含话题信息"""
        basic = await try_load_text(self.basic_path)
        bio_path = os.path.join(self.group_dir, "bio.md")
        bio = await try_load_text(bio_path)

        if len(self.memory.group) < 64:
            return ""  # 无法生成画像

        # 按 LLM 最大长度，截断百分之多少上下文
        max_text_size = self.llm.max_token_size * 2 * 0.7
        cur_text_size = len(basic) + len(bio) + len(str(self.memory.group))
        cut_ratio = max_text_size / cur_text_size
        cut_group_index = 0 if cut_ratio > 1.0 else max(0, int(cut_ratio * len(self.memory.group)))

        group = self.memory.group[-cut_group_index:]
        group_json_str = Inner.schema().dumps(group,
                                              many=True,
                                              ensure_ascii=False)
        
        # Add topic information to prompt
        topic_info = self._get_topic_info_for_bio()
        prompt = GROUP_BIO.format(basic=basic, bio=bio, group=group_json_str)
        
        # Append topic information
        if topic_info:
            prompt += f"\n\n当前活跃话题:\n{topic_info}"
        
        # 使用新的LLM适配器
        try:
            self.bio = await self.llm.chat_text(prompt)
        except Exception as e:
            self.bio = str(e)
        await safe_write_text(bio_path, self.bio)

        prompt = SUMMARY_BIO.format(bio=self.bio)
        self.summary = await self.llm.chat_text(prompt=prompt)
        await safe_write_text(self.summary_path, self.summary)
    
    def _get_topic_info_for_bio(self) -> str:
        """Get topic information for bio generation."""
        if not self.topics:
            return ""
        
        topic_info = []
        recent_topics = self.get_recent_topics(5)
        
        for topic in recent_topics:
            info = f"- {topic.name}: {len(topic.memory.group)} 条消息，最后活跃: {topic.last_updated.strftime('%Y-%m-%d %H:%M')}"
            topic_info.append(info)
        
        return '\n'.join(topic_info)