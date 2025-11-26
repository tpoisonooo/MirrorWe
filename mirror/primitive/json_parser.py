#!/usr/bin/env python3
"""
多行JSON解析工具函数
用于异步解析多行格式的JSON文件
"""

import json
import asyncio
import aiofiles
from typing import AsyncGenerator, Optional
from typing import Any, List  # 为了兼容性单独导入
from loguru import logger


async def parse_multiline_json_objects_async(file_path: str) -> AsyncGenerator[Any, None]:
    """
    异步解析多行JSON文件，逐对象输出
    
    Args:
        file_path: JSON文件路径
        
    Yields:
        解析成功的JSON对象
        
    Example:
        async for obj in parse_multiline_json_objects_async('data.jsonl'):
            print(obj)
    """
    import os
    if not os.path.exists(file_path):
        logger.error(f"文件不存在: {file_path}")
        return
    
    try:
        async with aiofiles.open(file_path, 'r', encoding='utf-8') as f:
            content = await f.read()
        
        logger.debug(f"开始解析文件: {file_path}")
        
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
                obj_count += 1
                yield obj
            except json.JSONDecodeError as e:
                error_count += 1
                logger.warning(f"最后一个JSON对象解析失败: {str(e)}")
        
        logger.info(f"文件解析完成: {file_path}")
        logger.info(f"成功解析: {obj_count} 个对象, 失败: {error_count} 个")
        
    except Exception as e:
        logger.error(f"解析文件失败: {file_path}, 错误: {str(e)}")
        raise


async def parse_multiline_json_objects_async_with_batch(
    file_path: str, 
    batch_size: int = 100
) -> AsyncGenerator[List[Any], None]:
    """
    异步解析多行JSON文件，按批次输出对象
    
    Args:
        file_path: JSON文件路径
        batch_size: 每批次的对象数量
        
    Yields:
        包含多个JSON对象的列表
        
    Example:
        async for batch in parse_multiline_json_objects_async_with_batch('data.jsonl', batch_size=50):
            for obj in batch:
                process(obj)
    """
    batch = []
    
    async for obj in parse_multiline_json_objects_async(file_path):
        batch.append(obj)
        
        if len(batch) >= batch_size:
            yield batch
            batch = []
    
    # 处理最后剩余的批次
    if batch:
        yield batch


def parse_multiline_json_objects_sync(file_path: str):
    """
    同步版本的多行JSON解析函数
    
    Args:
        file_path: JSON文件路径
        
    Yields:
        解析成功的JSON对象
        
    Example:
        for obj in parse_multiline_json_objects_sync('data.jsonl'):
            print(obj)
    """
    import os
    
    if not os.path.exists(file_path):
        logger.error(f"文件不存在: {file_path}")
        return
    
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        logger.debug(f"开始解析文件: {file_path}")
        
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
                obj_count += 1
                yield obj
            except json.JSONDecodeError as e:
                error_count += 1
                logger.warning(f"最后一个JSON对象解析失败: {str(e)}")
        
        logger.info(f"文件解析完成: {file_path}")
        logger.info(f"成功解析: {obj_count} 个对象, 失败: {error_count} 个")
        
    except Exception as e:
        logger.error(f"解析文件失败: {file_path}, 错误: {str(e)}")
        raise


# 向后兼容的别名
parse_jsonl_file_async = parse_multiline_json_objects_async
parse_jsonl_file = parse_multiline_json_objects_sync


if __name__ == '__main__':
    # 测试异步版本
    async def test_async():
        test_file = "test_sample.jsonl"
        count = 0
        async for obj in parse_multiline_json_objects_async(test_file):
            count += 1
            print(f"Object {count}: {type(obj)}")
            if count >= 3:  # 只测试前3个
                break
    
    # 测试同步版本
    def test_sync():
        test_file = "test_sample.jsonl"
        count = 0
        for obj in parse_multiline_json_objects_sync(test_file):
            count += 1
            print(f"Object {count}: {type(obj)}")
            if count >= 3:  # 只测试前3个
                break
    
    # 运行测试
    import sys
    if len(sys.argv) > 1:
        test_file = sys.argv[1]
        print(f"测试同步解析: {test_file}")
        test_sync()
    else:
        print("请提供测试文件路径")
        print("示例: python json_parser.py your_file.jsonl")