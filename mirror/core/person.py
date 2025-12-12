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
import datetime

from pathlib import Path
from typing import List, Dict, Any
from loguru import logger
from ..prompt import FRIEND_BIO, SUMMARY_BIO
from .inner import convert_wkteam_to_inner, Inner, parse_multi_inner_async, dump_multi_inner_sync, dump_multi_inner_async
from ..primitive import safe_write_text, try_load_text
from ..primitive import LLM, always_get_an_event_loop
from ..wechat.message import Message
from datetime import datetime

# 添加项目路径
from mirror.core.memory import MemoryStream
from mirror.core.personality import Personality


class Person(ABC):
    """增强版 Person 类，支持加载本地消息数据"""

    def __init__(self, wxid: str):
        self.wxid = wxid
        self.memory = MemoryStream()
        self.personality = Personality()
        self.analysis_result = {}  # 存储分析结果

        self.TAG_ME = "我"
        current_file = inspect.getfile(self.__class__)
        data_dir = os.path.join(os.path.dirname(current_file), "..", "..",
                                "data")
        self.wxid_dir = os.path.join(data_dir, 'friends', self.wxid)

        self.basic_path = os.path.join(self.wxid_dir, "basic.json")
        self.bio_path = os.path.join(self.wxid_dir, "bio.md")
        self.basic = ''
        self.bio = ''

        self.private_path = os.path.join(self.wxid_dir, "message.jsonl")
        self.group_path = os.path.join(self.wxid_dir, "group_segment.jsonl")
        self.llm = LLM()

        # 加载消息的 offset，销毁时要用 offset 把消息追加下去
        self.offset = (0, 0)

        # 群聊、私聊累计达到 threshold 条消息，就只保留末尾 max_keep 条有效的
        # 同时开始更新 bio
        self.threshold = 512  # AKA 多少条消息，足以刻画这个人
        self.max_keep = 128
        self.update_counter = 0

        # 销毁遗言，保留数据
        self._wr = weakref.ref(self)
        atexit.register(self._atexit_dump)

    def get_name(self):
        name = '对方昵称或备注，初始化时将从消息记录提取'
        if self.memory.private:
            name = self.memory.private[0].sender_name
        elif self.memory.group:
            name = self.memory.group[0].sender_name
        return name

    async def initialize(self):
        # 加载数据
        async for inner in parse_multi_inner_async(self.private_path):
            self.memory.add(private=inner)
        async for inner in parse_multi_inner_async(self.group_path):
            self.memory.add(group=inner)

        # 加载基本信息
        self.basic = await try_load_text(self.basic_path)
        self.bio = await try_load_text(self.bio_path)
        # 扔个空消息，触发分析
        await self.update(wk_msg=None)

    def _atexit_dump(self):
        me = self._wr()

        if me is None:
            logger.info('Person 对象已被销毁，跳过保存消息')
            return

        logger.info(
            f'Person {me.wxid}: 正在保存 {len(me.memory.private)} 私聊消息, {len(me.memory.group)} 群聊消息'
        )
        private_offset, group_offset = me.offset

        if not me.memory.private:
            logger.info('Person 私聊内存为空，跳过保存私聊消息')
        else:
            logger.info(f'Person {me.wxid}: 正在保存私聊消息...')
            dump_multi_inner_sync(me.private_path,
                                  me.memory.private,
                                  mode='write')
            logger.info(f'Person {me.wxid}: 完成保存私聊消息')

        if not me.memory.group:
            logger.info('Person 群聊内存为空，跳过保存群聊消息')
        else:
            logger.info(f'Person {me.wxid}: 正在保存群聊消息...')
            dump_multi_inner_sync(me.group_path, me.memory.group, mode='write')
            logger.info(f'Person {me.wxid}: 完成保存消息')

    async def update(self, wk_msg: Message):
        """更新消息数据，触发个性分析"""
        self.update_counter += 1

        if wk_msg:
            # 如果是私聊消息，加 private，否则加 group
            inner = convert_wkteam_to_inner(wk_msg)
            if wk_msg._type.startswith('6'):
                self.memory.add(private=inner)
            elif wk_msg._type.startswith('8'):
                if wk_msg.is_self:
                    return  # 跳过自己的群消息（可能是自己的 forward 消息）
                self.memory.add(group=inner)

        if len(self.memory) >= self.threshold:
            logger.info(
                f"Person {self.wxid}: 消息数量达到 {len(self.memory.private)} 条私聊消息+ {len(self.memory.group)} 条群聊消息，开始生成朋友画像"
            )
            # 触发更新
            await self.brief_bio(name=self.get_name())
            await self._analyze_personality()
            await self._setup_personality_from_analysis()

            # 截断消息
            self.memory.private = self.memory.private[-self.max_keep:]
            self.memory.group = self.memory.group[-self.max_keep:]

            await dump_multi_inner_async(self.private_path,
                                         self.memory.private,
                                         mode='write')
            await dump_multi_inner_async(self.group_path,
                                         self.memory.group,
                                         mode='write')

            logger.info(
                f"Person {self.wxid}: 当前 {len(self.memory.private)} 条私聊消息+ {len(self.memory.group)} 条群聊消息，完成个性分析"
            )

        elif self.update_counter > 0 and self.update_counter % 10 == 0:
            await dump_multi_inner_async(self.private_path,
                                         self.memory.private,
                                         mode='write')
            await dump_multi_inner_async(self.group_path,
                                         self.memory.group,
                                         mode='write')

    async def brief_bio(self, name: str) -> str:
        """生成朋友的  bio.md 文件，做个 summary.md"""
        if not self.basic and not self.memory.private and len(
                self.memory.group) < 64:
            return ""  # 无法生成画像

        # 按 LLM 最大长度，截断百分之多少上下文
        max_text_size = self.llm.max_token_size * 2 * 0.7
        cur_text_size = len(self.basic) + len(self.bio) + len(
            str(self.memory.private)) + len(str(self.memory.group))
        cut_ratio = max_text_size / max(1, cur_text_size)
        if cut_ratio > 1.0:
            cut_private_index = 0
            cut_group_index = 0
        else:
            cut_private_index = max(0,
                                    int(cut_ratio * len(self.memory.private)))
            cut_group_index = max(0, int(cut_ratio * len(self.memory.group)))

        private = self.memory.private[-cut_private_index:]
        private_json_str = Inner.schema().dumps(private,
                                                many=True,
                                                ensure_ascii=False)

        group = self.memory.group[-cut_group_index:]
        group_json_str = Inner.schema().dumps(group,
                                              many=True,
                                              ensure_ascii=False)

        prompt = FRIEND_BIO.format(name=name,
                                   basic=self.basic,
                                   bio=self.bio,
                                   private=private_json_str,
                                   group=group_json_str)
        # 使用新的LLM适配器
        try:
            self.bio = await self.llm.chat_text(prompt)
        except Exception as e:
            self.bio = str(e)

        await safe_write_text(self.bio_path, self.bio)

        prompt = SUMMARY_BIO.format(bio=self.bio)
        summary = await self.llm.chat_text(prompt=prompt)
        summary_path = os.path.join(self.wxid_dir, 'summary.md')
        await safe_write_text(summary_path, summary)

    async def _analyze_personality(self):
        """基于消息数据进行个性分析"""
        # 从 memory 中获取消息数据
        if not self.memory:
            self.analysis_result = self._get_default_analysis()
            return

        try:
            # 提取消息内容
            contents = []
            timestamps = []

            for msg in self.memory:
                if not isinstance(msg, dict):
                    continue

                role = msg.get('role', '')
                if role == self.TAG_ME:
                    continue  # 跳过自己的消息

                content = msg.get('content', '').strip()
                if content:
                    contents.append(content)
                    ts = msg.get('ts', 0)
                    if ts:
                        timestamps.append(ts)

            if not contents:
                self.analysis_result = self._get_default_analysis()
                return

            # 基础统计
            total_messages = len(contents)
            avg_length = sum(len(c) for c in contents) / total_messages

            # 时间模式分析
            time_pattern = await self._analyze_time_pattern(timestamps)

            # 语言特征分析
            language_features = await self._analyze_language_features(contents)

            # 情感分析
            emotion_pattern = await self._analyze_emotion_pattern(contents)

            # 关键词提取
            keywords = await self._extract_keywords(contents)

            self.analysis_result = {
                'total_messages': total_messages,
                'avg_message_length': avg_length,
                'time_pattern': time_pattern,
                'language_features': language_features,
                'emotion_pattern': emotion_pattern,
                'keywords': keywords,
            }

            logger.info(
                f"个性分析完成: {total_messages} 条消息, 平均长度: {avg_length:.1f}")

        except Exception as e:
            logger.error(f"个性分析失败: {e}")
            self.analysis_result = self._get_default_analysis()

    def _get_default_analysis(self) -> Dict[str, Any]:
        """获取默认分析结果"""
        return {
            'total_messages': 0,
            'avg_message_length': 0,
            'time_pattern': 'unknown',
            'language_features': {
                'has_emoji': False,
                'has_questions': False,
                'has_exclamations': False,
                'has_links': False,
                'style': 'neutral'
            },
            'emotion_pattern': {
                'positive_ratio': 0.5,
                'negative_ratio': 0.5,
                'neutral_ratio': 0.5,
                'dominant_emotion': 'neutral'
            },
            'keywords': [],
        }

    async def _analyze_time_pattern(self, timestamps: List[int]) -> str:
        """分析时间模式"""

        if not timestamps:
            return "unknown"

        # 转换为小时
        hours = []
        for ts in timestamps:
            if ts > 0:
                try:
                    hour = datetime.datetime.fromtimestamp(ts).hour
                    hours.append(hour)
                except:
                    continue

        if not hours:
            return "unknown"

        avg_hour = sum(hours) / len(hours)

        if 6 <= avg_hour < 12:
            return "morning_person"
        elif 12 <= avg_hour < 18:
            return "afternoon_person"
        elif 18 <= avg_hour < 23:
            return "evening_person"
        else:
            return "night_person"

    async def _analyze_language_features(
            self, contents: List[str]) -> Dict[str, Any]:
        """分析语言特征"""
        if not contents:
            return {
                'has_emoji': False,
                'has_questions': False,
                'has_exclamations': False,
                'has_links': False,
                'style': 'neutral'
            }

        features = {
            'has_emoji':
            any('😀' in c or '😊' in c or '😂' in c for c in contents),
            'has_questions': any('？' in c or '?' in c for c in contents),
            'has_exclamations': any('！' in c or '!' in c for c in contents),
            'has_links': any('http' in c or 'www.' in c for c in contents),
        }

        # 判断风格
        if features['has_emoji']:
            features['style'] = 'expressive'
        elif features['has_questions']:
            features['style'] = 'inquisitive'
        elif features['has_exclamations']:
            features['style'] = 'enthusiastic'
        else:
            features['style'] = 'neutral'

        return features

    async def _analyze_emotion_pattern(self,
                                       contents: List[str]) -> Dict[str, Any]:
        """分析情感模式"""
        if not contents:
            return {
                'positive_ratio': 0.5,
                'negative_ratio': 0.5,
                'neutral_ratio': 0.5,
                'dominant_emotion': 'neutral'
            }

        positive_words = ['好', '棒', '不错', '喜欢', '开心', '哈哈', '谢谢', '赞']
        negative_words = ['不好', '差', '讨厌', '烦', '生气', '难过', '抱歉']

        positive_count = 0
        negative_count = 0

        for content in contents:
            if any(word in content for word in positive_words):
                positive_count += 1
            if any(word in content for word in negative_words):
                negative_count += 1

        total = len(contents)
        positive_ratio = positive_count / total if total > 0 else 0
        negative_ratio = negative_count / total if total > 0 else 0
        neutral_ratio = 1 - positive_ratio - negative_ratio

        if positive_ratio > negative_ratio and positive_ratio > 0.3:
            dominant_emotion = 'positive'
        elif negative_ratio > positive_ratio and negative_ratio > 0.2:
            dominant_emotion = 'negative'
        else:
            dominant_emotion = 'neutral'

        return {
            'positive_ratio': positive_ratio,
            'negative_ratio': negative_ratio,
            'neutral_ratio': neutral_ratio,
            'dominant_emotion': dominant_emotion,
        }

    async def _extract_keywords(self, contents: List[str]) -> List[str]:
        """提取关键词"""
        if not contents:
            return []

        # 简单的关键词提取：出现频率较高的词
        word_freq = {}
        for content in contents:
            words = content.split()
            for word in words:
                if len(word) > 1:  # 忽略单字词
                    word_freq[word] = word_freq.get(word, 0) + 1

        # 返回频率最高的10个词
        sorted_words = sorted(word_freq.items(),
                              key=lambda x: x[1],
                              reverse=True)
        return [word for word, freq in sorted_words[:10]]

    async def _setup_personality_from_analysis(self):
        """基于分析结果设置个性"""
        if not self.analysis_result:
            return

        analysis = self.analysis_result

        # 设置 MBTI
        self.personality.mbti = await self._infer_mbti(analysis)

        # 设置 Big Five
        self.personality.bigfive = await self._generate_bigfive(analysis)

        # 设置幽默风格
        self.personality.humor_style = analysis['language_features']['style']

        # 设置爱情语言
        self.personality.love_language = await self._infer_love_language(
            analysis)

    async def _infer_mbti(self, analysis: Dict[str, Any]) -> str:
        """基于分析推断 MBTI 类型"""
        if not analysis or analysis.get('total_messages', 0) == 0:
            return "ISFJ"

        features = analysis.get('language_features', {})
        emotion = analysis.get('emotion_pattern', {})

        # 外向 vs 内向
        e_i = "E" if analysis.get('total_messages', 0) > 50 else "I"

        # 实感 vs 直觉
        s_n = "N" if features.get('has_questions', False) else "S"

        # 思考 vs 情感
        t_f = "F" if emotion.get('dominant_emotion') == 'positive' else "T"

        # 判断 vs 知觉
        j_p = "P" if features.get('style') in ['expressive', 'inquisitive'
                                               ] else "J"

        return f"{e_i}{s_n}{t_f}{j_p}"

    async def _generate_bigfive(self, analysis: Dict[str,
                                                     Any]) -> Dict[str, float]:
        """生成 Big Five 人格特质"""
        if not analysis or analysis.get('total_messages', 0) == 0:
            return {"O": 0.5, "C": 0.5, "E": 0.5, "A": 0.5, "N": 0.5}

        features = analysis.get('language_features', {})
        emotion = analysis.get('emotion_pattern', {})
        avg_length = analysis.get('avg_message_length', 0)

        # 开放性 (Openness)
        openness = 0.8 if features.get('has_questions', False) else 0.4

        # 尽责性 (Conscientiousness)
        conscientiousness = 0.7 if avg_length > 20 else 0.5

        # 外向性 (Extraversion)
        total_messages = analysis.get('total_messages', 0)
        extraversion = 0.8 if total_messages > 50 else 0.3

        # 宜人性 (Agreeableness)
        agreeableness = 0.8 if emotion.get(
            'dominant_emotion') == 'positive' else 0.4

        # 神经质 (Neuroticism)
        neuroticism = 0.7 if emotion.get(
            'dominant_emotion') == 'negative' else 0.3

        return {
            "O": openness,
            "C": conscientiousness,
            "E": extraversion,
            "A": agreeableness,
            "N": neuroticism
        }

    async def _infer_love_language(self, analysis: Dict[str, Any]) -> str:
        """推断爱情语言"""
        if not analysis:
            return "words_of_affirmation"

        features = analysis.get('language_features', {})
        avg_length = analysis.get('avg_message_length', 0)

        if features.get('style') in ['expressive', 'enthusiastic']:
            return "words_of_affirmation"
        elif avg_length > 30:
            return "quality_time"
        elif features.get('has_emoji'):
            return "receiving_gifts"
        elif features.get('has_questions'):
            return "acts_of_service"
        else:
            return "physical_touch"

    def get_analysis_summary(self) -> str:
        """获取分析摘要"""
        if not self.analysis_result:
            return "暂无分析数据"

        analysis = self.analysis_result
        return (f"朋友 {self.wxid} 分析摘要:\n"
                f"  总消息数: {analysis['total_messages']}\n"
                f"  平均长度: {analysis['avg_message_length']:.1f}\n"
                f"  时间模式: {analysis['time_pattern']}\n"
                f"  语言风格: {analysis['language_features']['style']}\n"
                f"  主导情感: {analysis['emotion_pattern']['dominant_emotion']}\n"
                f"  MBTI类型: {self.personality.mbti}")
