#!/usr/bin/env python3
"""
重新整理微信消息日志文件
将原始的 jsonl 文件按照消息类型分类保存
适用于多行JSON格式的日志文件

使用方法:
    python reorganize.py <输入文件> <输出目录> [--async]
    
    --async 参数可选，使用异步模式处理大文件更快
"""

import json
import os
import sys
import asyncio
from pathlib import Path
from loguru import logger
from ..primitive.json_parser import parse_multiline_json_objects_async, parse_multiline_json_objects_sync
from .proxy import get_message_log_paths, save_message_to_file  


def reorganize_logs_sync(input_jsonl_path: str, output_dir: str):
    """
    同步重新整理日志文件
    
    Args:
        input_jsonl_path: 输入的原始 jsonl 文件路径 (多行格式化的JSON)
        output_dir: 输出目录路径
    """
    if not os.path.exists(input_jsonl_path):
        logger.error(f"输入文件不存在: {input_jsonl_path}")
        return False
    
    # 创建输出目录
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)
    
    # 创建原始消息日志文件
    origin_logpath = os.path.join(output_dir, 'origin.jsonl')
    
    total_messages = 0
    processed_messages = 0
    error_messages = 0
    
    # 统计各类型消息数量
    friend_messages = 0
    group_messages = 0
    other_messages = 0
    
    logger.info(f"开始同步处理文件: {input_jsonl_path}")
    
    try:
        # 使用同步解析器逐对象处理
        for message in parse_multiline_json_objects_sync(input_jsonl_path):
            try:
                # 1. 首先记录原始消息到 origin.jsonl
                save_message_to_file(origin_logpath, message)
                
                # 2. 根据消息类型分别记录到对应的文件
                message_type = str(message.get('messageType', ''))
                data = message.get('data', {})
                
                if data and isinstance(data, dict) and message_type:
                    sender_id = data.get('fromUser', '')
                    group_id = data.get('fromGroup', '')
                    
                    # 获取对应的消息日志文件路径
                    specific_logpaths = get_message_log_paths(output_dir, message_type, sender_id, group_id)
                    
                    # 保存到对应的分类日志文件
                    save_message_to_file(specific_logpaths, message)
                    
                    # 统计消息类型
                    if message_type.startswith('6'):
                        friend_messages += 1
                    elif message_type.startswith('8'):
                        group_messages += 1
                    else:
                        other_messages += 1
                
                processed_messages += 1
                total_messages += 1
                
                # 每1000条消息打印一次进度
                if processed_messages % 1000 == 0:
                    logger.info(f"已处理 {processed_messages} 条消息...")
                    
            except Exception as e:
                logger.error(f"处理消息失败: {str(e)}")
                error_messages += 1
                continue
    
    except Exception as e:
        logger.error(f"处理文件失败: {input_jsonl_path}, 错误: {str(e)}")
        return False
    
    # 打印统计信息
    logger.info(f"同步处理完成!")
    logger.info(f"总消息数: {total_messages}")
    logger.info(f"成功处理: {processed_messages}")
    logger.info(f"失败消息: {error_messages}")
    logger.info(f"私聊消息: {friend_messages}")
    logger.info(f"群聊消息: {group_messages}")
    logger.info(f"其他消息: {other_messages}")
    
    # 显示目录结构
    logger.info(f"输出目录结构:")
    for root, dirs, files in os.walk(output_dir):
        level = root.replace(output_dir, '').count(os.sep)
        indent = ' ' * 2 * level
        logger.info(f"{indent}{os.path.basename(root)}/")
        subindent = ' ' * 2 * (level + 1)
        for file in files:
            logger.info(f"{subindent}{file}")
    
    return True


def reorganize_logs(input_jsonl_path: str, output_dir: str):
    """
    重新整理日志文件（使用同步版本作为默认）
    
    Args:
        input_jsonl_path: 输入的原始 jsonl 文件路径 (多行格式化的JSON)
        output_dir: 输出目录路径
    """
    return 

def main_sync():
    """同步主函数"""
    if len(sys.argv) != 3:
        print("用法: python reorganize.py <输入jsonl文件路径> <输出目录路径>")
        print("示例: python reorganize.py /path/to/old_messages.jsonl /path/to/output_dir")
        sys.exit(1)
    
    input_path = sys.argv[1]
    output_path = sys.argv[2]
    
    # 检查输入文件是否存在
    if not os.path.exists(input_path):
        print(f"错误: 输入文件不存在: {input_path}")
        sys.exit(1)
    
    # 如果输出目录不存在，创建它
    output_path = Path(output_path)
    output_path.mkdir(parents=True, exist_ok=True)
    
    logger.info(f"开始重新整理日志文件（同步模式）...")
    logger.info(f"输入文件: {input_path}")
    logger.info(f"输出目录: {output_path}")
    
    success = reorganize_logs_sync(str(input_path), str(output_path))
    
    if success:
        logger.info("日志重新整理完成!")
    else:
        logger.error("日志重新整理失败!")
        sys.exit(1)

if __name__ == '__main__':
    main_sync()