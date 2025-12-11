#!/usr/bin/env python3
"""
多行JSON解析工具函数
用于异步解析多行格式的JSON文件
"""

import json
import asyncio
import aiofiles
import aiofiles.os
import anyio

from typing import AsyncGenerator, Optional
from typing import Any, List, Dict
from loguru import logger
from pathlib import Path

import os

from dataclasses import dataclass
from dataclasses_json import dataclass_json
from ..wechat.message import Message

@dataclass_json
@dataclass
class Inner:
    """内部消息表示，用于 LLM 处理。原始的 wkteam 太多无用字段"""
    type: str = ''
    group_id: str = ''
    sender_id: str = ''
    sender_name: str = ''
    content: str = ''
    ts: int = 0

def convert_wkteam_to_inner(msg: Message):
    """将 wkteam 的 Message 对象转换为 Inner 对象"""
    if msg.is_self:
        sender_name = 'me'
    else:
        sender_name = msg.push_content.split(':')[0].strip()

    inner = Inner(type=msg.type, group_id=msg.group_id, sender_id=msg.sender_id,
                  sender_name=sender_name, content=msg.content, ts=msg.ts)
    return inner

# def convert_json_to_inner(obj: Dict[str, Any]):
#     """将原始JSON对象转换为 Inner 对象"""
#     if type(obj) is not dict:
#         import pdb; pdb.set_trace()
#         pass
#     inner = Inner(type=obj.get('type', ''),
#                   group_id=obj.get('group_id', ''),
#                   sender_id=obj.get('sender_id', ''),
#                   sender_name=obj.get('sender_name', ''),
#                   content=obj.get('content', '').strip(),
#                   ts=obj.get('ts', 0))
#     return inner

def convert_to_inner(obj: Any):
    """将对象转换为 Inner 对象"""
    if isinstance(obj, Message):
        return convert_wkteam_to_inner(obj)
    elif isinstance(obj, dict):
        return Inner().from_dict(obj)
    else:
        raise ValueError("无法转换为 Inner 对象，类型未知")

def dump_multi_inner_sync(file_path: str, objs: List[Inner], mode='write'):
    """
    同步保存多行JSON文件，逐对象写入
    
    Args:
        file_path: JSON 文件路径
        objs: List 对象
        mode: 'write' 或 'append'
        
    Example:
        dump_multi_inner_sync('data.jsonl', [Inner, Inner, ...])
    """
    # 创建父目录
    Path(file_path).parent.mkdir(parents=True, exist_ok=True)
    
    symbol = 'w' if mode == 'write' else 'a'
    if 'append' == mode and not os.path.exists(file_path):
        # 如果文件不存在，改为写入模式
        symbol = 'w'

    with open(file_path, symbol, encoding='utf-8') as f:
        for obj in objs:
            f.write(obj.to_json(ensure_ascii=False, indent=2) + '\n')
        f.flush()

async def dump_multi_inner_async(file_path: str, objs: List[Inner], mode='write'):
    """
    异步保存多行JSON文件，逐对象写入
    
    Args:
        file_path: JSON 文件路径
        objs: List 对象
        
    Yields:
        解析成功的JSON对象
        
    Example:
        await dump_multi_inner_async('data.jsonl', [Inner, Inner, ...]):
    """
    # os.makedirs(os.path.dirname(file_path), exist_ok=True)
    await anyio.Path(file_path).parent.mkdir(parents=True, exist_ok=True)
    
    symbol = 'w' if mode == 'write' else 'a'
    if 'append' == mode and not os.path.exists(file_path):
        # 如果文件不存在，改为写入模式
        symbol = 'w'

    async with aiofiles.open(file_path, symbol, encoding='utf-8') as f:
        for obj in objs:
            json_str = obj.to_json(ensure_ascii=False, indent=2)
            await f.write(json_str + '\n')
        await f.flush()



async def parse_multi_inner_async(file_path: str, output='inner') -> AsyncGenerator[Any, None]:
    """
    异步解析多行JSON文件，逐对象输出
    
    Args:
        file_path: JSON文件路径
        
    Yields:
        解析成功的JSON对象
        
    Example:
        async for obj in parse_multi_inner_async('data.jsonl'):
            print(obj)
    """
    if not os.path.exists(file_path):
        return
    
    try:
        async with aiofiles.open(file_path, 'r', encoding='utf-8') as f:
            content = await f.read()
        
        # logger.debug(f"开始解析文件: {file_path}")
        
        # 使用栈的方式来正确匹配嵌套的大括号
        current_obj = ""
        brace_count = 0
        in_string = False
        escape_next = False
        line_num = 1
        obj_count = 0
        error_count = 0
        
        for char in content:
            current_obj += char
            
            if escape_next:
                escape_next = False
                continue
                
            if char == '\\':
                escape_next = True
                continue
                
            if char == '"' and not in_string:
                in_string = True
            elif char == '"' and in_string:
                in_string = False
            elif not in_string:
                if char == '{':
                    brace_count += 1
                elif char == '}':
                    brace_count -= 1
                    
                    if brace_count == 0 and current_obj.strip():
                        # 找到一个完整的JSON对象
                        try:
                            obj = json.loads(current_obj)
                            if 'inner' in output:
                                obj = Inner().from_dict(obj)
                            obj_count += 1
                            yield obj
                            
                            # 每1000个对象打印一次进度
                            if obj_count % 1000 == 0:
                                logger.info(f"已解析 {obj_count} 个JSON对象...")
                                
                        except json.JSONDecodeError as e:
                            error_count += 1
                            logger.warning(f"JSON解析失败 (位置约第{line_num}行): {str(e)}")
                            logger.warning(f"问题JSON片段前200字符: {current_obj[:200]}...")
                        
                        # 重置状态
                        current_obj = ""
            
            if char == '\n':
                line_num += 1
        
        # 处理最后可能残留的JSON片段
        if current_obj.strip() and brace_count == 0:
            try:
                obj = json.loads(current_obj)
                if 'inner' in output:
                    obj = Inner().from_dict(obj)
                obj_count += 1
                yield obj
            except json.JSONDecodeError as e:
                error_count += 1
                logger.warning(f"最后一个 Inner 对象解析失败: {str(e)}")
        
    except Exception as e:
        logger.error(f"解析文件失败: {file_path}, 错误: {str(e)}")
        raise

