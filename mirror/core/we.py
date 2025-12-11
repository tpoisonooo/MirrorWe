"""
微信实体工厂类 - 提供Person和Group对象的LRU缓存管理
"""

import os
import weakref
import atexit
from typing import Optional, Dict, Any, Union
from functools import lru_cache
from loguru import logger
import asyncio
from pathlib import Path

from .person import Person
from .group import Group
from .memory import MemoryStream
from .inner import Inner, dump_multi_inner_async, parse_multi_inner_async
from ..primitive import try_load_text
import weakref
import atexit

class WeFactory:
    """
    微信实体工厂类
    
    功能：
    1. 根据wxid创建和管理Person对象
    2. 根据group_id（包含@符号）创建和管理Group对象  
    3. 提供LRU缓存机制，支持对象换入换出
    4. 同步消息数据到本地文件夹
    """
    
    def __init__(self, max_cache_size: int = 128):
        """
        初始化工厂
        
        Args:
            max_cache_size: LRU缓存的最大对象数量
        """
        self.max_cache_size = max_cache_size
        
        # 使用weakref管理缓存对象，允许垃圾回收
        self._person_cache: Dict[str, weakref.ref] = {}
        self._group_cache: Dict[str, weakref.ref] = {}
        
        # 统计信息
        self._cache_stats = {
            'person_hits': 0,
            'person_misses': 0,
            'group_hits': 0,
            'group_misses': 0,
            'evictions': 0
        }
        
        # 注册清理函数
        atexit.register(self._cleanup_all)
        
        logger.info(f"WeFactory 初始化完成，缓存大小: {max_cache_size}")
    
    def _is_group_id(self, wxid: str) -> bool:
        """
        判断是否为群聊ID
        
        Args:
            wxid: 微信ID
            
        Returns:
            True如果是群聊ID（包含@符号）
        """
        return '@' in wxid and ('chatroom' in wxid or 'openim' in wxid)
    
    def _get_data_dir(self) -> str:
        """获取数据目录路径"""
        current_file = os.path.abspath(__file__)
        return os.path.join(os.path.dirname(current_file), "..", "..", "data")
    
    def _ensure_entity_directory(self, entity_id: str, entity_type: str) -> str:
        """
        确保实体目录存在
        
        Args:
            entity_id: 实体ID
            entity_type: 实体类型 ('friends' 或 'groups')
            
        Returns:
            实体目录路径
        """
        data_dir = self._get_data_dir()
        entity_dir = os.path.join(data_dir, entity_type, entity_id)
        os.makedirs(entity_dir, exist_ok=True)
        return entity_dir
    
    async def get_person_async(self, wxid: str, auto_create: bool = True) -> Optional[Person]:
        """
        获取Person对象
        
        Args:
            wxid: 微信用户ID
            auto_create: 如果不存在是否自动创建
            
        Returns:
            Person对象或None
        """
        # 检查缓存
        if wxid in self._person_cache:
            person_ref = self._person_cache[wxid]
            person = person_ref()
            if person is not None:
                self._cache_stats['person_hits'] += 1
                # logger.debug(f"Person 缓存命中: {wxid}")
                return person
            else:
                # 对象已被垃圾回收，从缓存中移除
                del self._person_cache[wxid]
        
        self._cache_stats['person_misses'] += 1
        
        # 检查缓存大小，如果需要则清理
        if len(self._person_cache) >= self.max_cache_size:
            await self._evict_oldest_person()
        
        # 创建新的Person对象
        if auto_create:
            person = Person(wxid)
            await person.initialize()
            # 确保目录存在
            self._ensure_entity_directory(wxid, 'friends')
            
            # 添加到缓存
            self._person_cache[wxid] = weakref.ref(person, self._on_person_finalized)
            
            # logger.info(f"创建新的Person对象: {wxid}")
            return person
        
        return None
    
    async def get_group_async(self, group_id: str, auto_create: bool = True) -> Optional[Group]:
        """
        获取Group对象
        
        Args:
            group_id: 群聊ID（必须包含@符号）
            auto_create: 如果不存在是否自动创建
            
        Returns:
            Group对象或None
        """
        # 验证group_id格式
        if not self._is_group_id(group_id):
            logger.warning(f"无效的群聊ID格式: {group_id}")
            return None
        
        # 检查缓存
        if group_id in self._group_cache:
            group_ref = self._group_cache[group_id]
            group = group_ref()
            if group is not None:
                self._cache_stats['group_hits'] += 1
                # logger.debug(f"Group 缓存命中: {group_id}")
                return group
            else:
                # 对象已被垃圾回收，从缓存中移除
                del self._group_cache[group_id]
        
        self._cache_stats['group_misses'] += 1
        
        # 检查缓存大小，如果需要则清理
        if len(self._group_cache) >= self.max_cache_size:
            await self._evict_oldest_group()
        
        # 创建新的Group对象
        if auto_create:
            group = Group(group_id)
            await group.initialize()
            # 确保目录存在
            self._ensure_entity_directory(group_id, 'groups')
            
            # 添加到缓存
            self._group_cache[group_id] = weakref.ref(group, self._on_group_finalized)
            
            logger.info(f"创建新的Group对象: {group_id}")
            return group
        
        return None
    
    async def get_entity(self, wxid: str, auto_create: bool = True) -> Optional[Union[Person, Group]]:
        """
        智能获取实体对象，自动判断类型
        
        Args:
            wxid: 微信ID（可能是用户或群聊）
            auto_create: 如果不存在是否自动创建
            
        Returns:
            Person或Group对象，或None
        """
        if self._is_group_id(wxid):
            return await self.get_group(wxid, auto_create)
        else:
            return await self.get_person(wxid, auto_create)
    
    def _on_person_finalized(self, weak_ref):
        """Person对象被垃圾回收时的回调"""
        # 找到并移除对应的缓存项
        for wxid, ref in list(self._person_cache.items()):
            if ref is weak_ref:
                del self._person_cache[wxid]
                logger.debug(f"Person对象被垃圾回收: {wxid}")
                break
        
        # Person对象通过atexit注册了自己的清理函数，这里不需要额外处理
    
    def _on_group_finalized(self, weak_ref):
        """Group对象被垃圾回收时的回调"""
        # 找到并移除对应的缓存项
        for group_id, ref in list(self._group_cache.items()):
            if ref is weak_ref:
                del self._group_cache[group_id]
                logger.debug(f"Group对象被垃圾回收: {group_id}")
                break
        
        # Group对象通过atexit注册了自己的清理函数，这里不需要额外处理
    
    async def _evict_oldest_person(self):
        """清理最老的Person对象"""
        if self._person_cache:
            # 简单策略：移除第一个（可以改进为LRU）
            wxid, ref = next(iter(self._person_cache.items()))
            del self._person_cache[wxid]
            self._cache_stats['evictions'] += 1
            # logger.info(f"清理Person缓存: {wxid}")
    
    async def _evict_oldest_group(self):
        """清理最老的Group对象"""
        if self._group_cache:
            # 简单策略：移除第一个（可以改进为LRU）
            group_id, ref = next(iter(self._group_cache.items()))
            del self._group_cache[group_id]
            self._cache_stats['evictions'] += 1
            logger.info(f"清理Group缓存: {group_id}")
    
    async def _sync_entity_data(self, entity: Union[Person, Group]) -> None:
        """
        同步实体数据到磁盘
        
        Args:
            entity: Person或Group对象
        """
        try:
            if isinstance(entity, Person):
                # 同步Person的内存数据
                if hasattr(entity, 'memory') and entity.memory.group:
                    group_file = os.path.join(entity.wxid_dir, "group_segment.jsonl")
                    await dump_multi_inner_async(group_file, entity.memory.group)
                
                if hasattr(entity, 'memory') and entity.memory.private:
                    private_file = os.path.join(entity.wxid_dir, "message.jsonl") 
                    await dump_multi_inner_async(private_file, entity.memory.private)
                    
            elif isinstance(entity, Group):
                # 同步Group的内存数据
                if hasattr(entity, 'memory') and entity.memory.group:
                    group_file = os.path.join(entity.group_dir, "message.jsonl")
                    await dump_multi_inner_async(group_file, entity.memory.group)
            
            logger.debug(f"同步实体数据完成: {entity.wxid if hasattr(entity, 'wxid') else entity.group_id}")
            
        except Exception as e:
            logger.error(f"同步实体数据失败: {e}")
    

    
    def get_cache_stats(self) -> Dict[str, Any]:
        """获取缓存统计信息"""
        return {
            'person_cache_size': len(self._person_cache),
            'group_cache_size': len(self._group_cache),
            'total_cached': len(self._person_cache) + len(self._group_cache),
            'max_cache_size': self.max_cache_size,
            **self._cache_stats
        }
    
    async def cleanup(self) -> None:
        """清理工厂资源"""
        logger.info("正在清理WeFactory资源...")
        # Person和Group对象会自行处理数据同步，这里只需要清理缓存
        self._person_cache.clear()
        self._group_cache.clear()
        logger.info("WeFactory清理完成")
    
    def _cleanup_all(self):
        """程序退出时的清理函数"""
        try:
            # Person和Group对象已经通过atexit注册了自己的清理函数
            # 这里只需要清理缓存引用
            self._person_cache.clear()
            self._group_cache.clear()
            logger.info("WeFactory缓存清理完成")
        except Exception as e:
            logger.error(f"清理工厂资源时出错: {e}")


# 全局工厂实例
_factory_instance: Optional[WeFactory] = None


def get_factory(max_cache_size: int = 128) -> WeFactory:
    """
    获取全局工厂实例（单例模式）
    
    Args:
        max_cache_size: 缓存大小
        
    Returns:
        WeFactory实例
    """
    global _factory_instance
    if _factory_instance is None:
        _factory_instance = WeFactory(max_cache_size=max_cache_size)
    return _factory_instance


# 便捷的同步包装函数（用于非异步环境）
def get_person_sync(wxid: str, max_cache_size: int = 100) -> Optional[Person]:
    """同步获取Person对象"""
    factory = get_factory(max_cache_size)
    try:
        loop = asyncio.get_event_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
    return loop.run_until_complete(factory.get_person(wxid))


def get_group_sync(group_id: str, max_cache_size: int = 100) -> Optional[Group]:
    """同步获取Group对象"""
    factory = get_factory(max_cache_size)
    try:
        loop = asyncio.get_event_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
    return loop.run_until_complete(factory.get_group(group_id))


def get_entity_sync(wxid: str, max_cache_size: int = 100) -> Optional[Union[Person, Group]]:
    """同步获取实体对象（自动判断类型）"""
    factory = get_factory(max_cache_size)
    try:
        loop = asyncio.get_event_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
    return loop.run_until_complete(factory.get_entity(wxid))