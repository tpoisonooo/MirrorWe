#!/usr/bin/env python3
"""
重新整理微信消息日志文件
将原始的 jsonl 文件按照消息类型分类保存
适用于多行JSON格式的日志文件
"""

import json
import os
import sys
import re
from pathlib import Path
from loguru import logger


def save_message_to_file(file_path: str, message: dict):
    """保存消息到指定的jsonl文件"""
    try:
        with open(file_path, 'a', encoding='utf-8') as f:
            json_str = json.dumps(message, indent=2, ensure_ascii=False)
            f.write(json_str + '\n')
    except Exception as e:
        logger.error(f"保存消息到文件失败 {file_path}: {str(e)}")


def get_message_log_path(logdir: str, message_type: str, sender_id: str, group_id: str = '') -> str:
    """根据消息类型和发送者获取对应的日志文件路径"""
    try:
        # 私聊消息 (600开头)
        if message_type.startswith('6'):
            # 为每个好友创建目录
            friend_dir = os.path.join(logdir, 'friends', sender_id)
            if not os.path.exists(friend_dir):
                os.makedirs(friend_dir)
            return os.path.join(friend_dir, 'message.jsonl')
        
        # 群聊消息 (800开头)
        elif message_type.startswith('8'):
            # 为每个群创建目录
            group_dir = os.path.join(logdir, 'groups', group_id)
            if not os.path.exists(group_dir):
                os.makedirs(group_dir)
            return os.path.join(group_dir, 'message.jsonl')
        
        # 其他类型的消息，保存在原始日志目录
        else:
            other_dir = os.path.join(logdir, 'others')
            if not os.path.exists(other_dir):
                os.makedirs(other_dir)
            return os.path.join(other_dir, 'message.jsonl')
            
    except Exception as e:
        logger.error(f"获取消息日志路径失败: {str(e)}")
        # 如果出错，返回一个默认路径
        default_dir = os.path.join(logdir, 'default')
        if not os.path.exists(default_dir):
            os.makedirs(default_dir)
        return os.path.join(default_dir, 'message.jsonl')


def parse_multiline_json_objects(content: str):
    """
    从多行文本中解析JSON对象
    使用正则表达式匹配完整的JSON对象
    """
    # 使用正则表达式找到所有完整的JSON对象
    # 这个模式会匹配以{开头，以}结尾的完整JSON对象
    json_pattern = r'\{(?:[^{}]|(?:\{[^{}]*\}))*\}'
    
    # 更精确的模式，考虑嵌套大括号
    brace_pattern = r'\{[^}]*\}'
    
    # 使用栈的方式来正确匹配嵌套的大括号
    objects = []
    current_obj = ""
    brace_count = 0
    in_string = False
    escape_next = False
    
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
                        objects.append(obj)
                        current_obj = ""
                    except json.JSONDecodeError as e:
                        logger.warning(f"JSON解析失败，跳过这个对象: {str(e)}")
                        logger.warning(f"问题对象前200字符: {current_obj[:200]}...")
                        current_obj = ""
                        continue
    
    # 处理最后一个可能的对象
    if current_obj.strip() and brace_count == 0:
        try:
            obj = json.loads(current_obj)
            objects.append(obj)
        except json.JSONDecodeError as e:
            logger.warning(f"最后一个JSON对象解析失败: {str(e)}")
    
    return objects


def reorganize_logs(input_jsonl_path: str, output_dir: str):
    """
    重新整理日志文件
    
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
    
    logger.info(f"开始处理文件: {input_jsonl_path}")
    
    try:
        # 读取整个文件内容
        with open(input_jsonl_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        logger.info("正在解析多行JSON对象...")
        # 解析多行JSON对象
        messages = parse_multiline_json_objects(content)
        
        logger.info(f"共解析到 {len(messages)} 条消息")
        total_messages = len(messages)
        
        # 处理每条消息
        for i, message in enumerate(messages):
            try:
                # 1. 首先记录原始消息到 origin.jsonl
                # save_message_to_file(origin_logpath, message)
                
                # 2. 根据消息类型分别记录到对应的文件
                message_type = str(message.get('messageType', ''))
                data = message.get('data', {})
                
                if data and type(data) is dict and message_type:
                    if 'self' in data and data['self']:
                        # 私聊消息，不记录分类日志
                        sender_id = data.get('toUser', '')
                    else:
                        sender_id = data.get('fromUser', '')
            
                    group_id = data.get('fromGroup', '')
                    
                    # 获取对应的消息日志文件路径
                    specific_logpath = get_message_log_path(output_dir, message_type, sender_id, group_id)
                    
                    # 保存到对应的分类日志文件
                    save_message_to_file(specific_logpath, message)
                    
                    # 统计消息类型
                    if message_type.startswith('6'):
                        friend_messages += 1
                    elif message_type.startswith('8'):
                        group_messages += 1
                    else:
                        other_messages += 1
                
                processed_messages += 1
                
                # 每1000条消息打印一次进度
                if (i + 1) % 1000 == 0:
                    logger.info(f"已处理 {i + 1} / {total_messages} 条消息...")
                    
            except Exception as e:
                logger.error(f"处理第 {i + 1} 条消息失败: {str(e)}")
                error_messages += 1
                continue
    
    except Exception as e:
        logger.error(f"读取文件失败: {str(e)}")
        return False
    
    # 打印统计信息
    logger.info(f"处理完成!")
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


def main():
    """主函数"""
    if len(sys.argv) != 3:
        print("用法: python reorganize_logs.py <输入jsonl文件路径> <输出目录路径>")
        print("示例: python reorganize_logs.py /path/to/old_messages.jsonl /path/to/output_dir")
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
    
    logger.info(f"开始重新整理日志文件...")
    logger.info(f"输入文件: {input_path}")
    logger.info(f"输出目录: {output_path}")
    
    success = reorganize_logs(input_path, str(output_path))
    
    if success:
        logger.info("日志重新整理完成!")
    else:
        logger.error("日志重新整理失败!")
        sys.exit(1)


if __name__ == '__main__':
    main()