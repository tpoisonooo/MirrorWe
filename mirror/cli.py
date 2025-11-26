#!/usr/bin/env python3
"""
MirrorWe CLI 入口点
"""

import argparse
import sys
from loguru import logger


def main():
    """主CLI函数"""
    parser = argparse.ArgumentParser(
        description='MirrorWe - 微信镜像',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  # 启动微信服务
   wechat --serve
  
  # 重新整理日志
   reorganize input.jsonl output_dir --async
  
  # 测试JSON解析器
   test-parser sample.jsonl
        """
    )
    
    subparsers = parser.add_subparsers(dest='command', help='可用命令')
    
    # 微信服务子命令
    wechat_parser = subparsers.add_parser('wechat', help='微信服务相关命令')
    wechat_parser.add_argument('--login', action='store_true', help='登录微信')
    wechat_parser.add_argument('--serve', action='store_true', help='启动消息服务')
    wechat_parser.add_argument('--forward', action='store_true', help='启用消息转发')
    
    # 日志整理子命令
    reorganize_parser = subparsers.add_parser('reorganize', help='重新整理日志文件')
    reorganize_parser.add_argument('input', help='输入的JSONL文件路径')
    reorganize_parser.add_argument('output', help='输出目录路径')
    reorganize_parser.add_argument('--async', action='store_true', help='使用异步模式')
    
    # 测试工具子命令
    test_parser = subparsers.add_parser('test-parser', help='测试JSON解析器')
    test_parser.add_argument('file', help='要解析的JSONL文件')
    test_parser.add_argument('--async', action='store_true', help='使用异步模式')
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        return
    
    try:
        if args.command == 'wechat':
            handle_wechat_command(args)
        elif args.command == 'reorganize':
            handle_reorganize_command(args)
        elif args.command == 'test-parser':
            handle_test_parser_command(args)
    except KeyboardInterrupt:
        logger.info("用户中断操作")
        sys.exit(1)
    except Exception as e:
        logger.error(f"命令执行失败: {e}")
        sys.exit(1)


def handle_wechat_command(args):
    """处理微信服务命令"""
    from .wechat.proxy import WkteamManager
    
    manager = WkteamManager()
    
    if args.login:
        logger.info("开始登录微信...")
        err = manager.login()
        if err:
            logger.error(f"登录失败: {err}")
            sys.exit(1)
        logger.info("登录成功！")
        
    if args.serve:
        logger.info("启动微信消息服务...")
        manager.serve(forward=args.forward)


def handle_reorganize_command(args):
    """处理日志整理命令"""
    import asyncio
    from .wechat.reorganize import reorganize_logs_async, reorganize_logs_sync
    from pathlib import Path
    
    input_path = Path(args.input)
    output_path = Path(args.output)
    
    if not input_path.exists():
        logger.error(f"输入文件不存在: {input_path}")
        sys.exit(1)
    
    output_path.mkdir(parents=True, exist_ok=True)
    
    logger.info(f"开始整理日志文件: {input_path} -> {output_path}")
    
    if args.async:
        logger.info("使用异步模式...")
        loop = asyncio.get_event_loop()
        success = loop.run_until_complete(reorganize_logs_async(str(input_path), str(output_path)))
    else:
        logger.info("使用同步模式...")
        success = reorganize_logs_sync(str(input_path), str(output_path))
    
    if success:
        logger.info("日志整理完成！")
    else:
        logger.error("日志整理失败！")
        sys.exit(1)


def handle_test_parser_command(args):
    """处理JSON解析器测试命令"""
    import asyncio
    from .wechat.json_parser import parse_multiline_json_objects_async, parse_multiline_json_objects_sync
    from pathlib import Path
    
    file_path = Path(args.file)
    
    if not file_path.exists():
        logger.error(f"文件不存在: {file_path}")
        sys.exit(1)
    
    logger.info(f"测试JSON解析器: {file_path}")
    
    count = 0
    
    if args.async:
        logger.info("使用异步模式...")
        
        async def test_async():
            nonlocal count
            async for obj in parse_multiline_json_objects_async(str(file_path)):
                count += 1
                if count <= 5:  # 只显示前5个
                    logger.info(f"对象 {count}: messageType={obj.get('messageType', 'unknown')}")
        
        loop = asyncio.get_event_loop()
        loop.run_until_complete(test_async())
    else:
        logger.info("使用同步模式...")
        for obj in parse_multiline_json_objects_sync(str(file_path)):
            count += 1
            if count <= 5:  # 只显示前5个
                logger.info(f"对象 {count}: messageType={obj.get('messageType', 'unknown')}")
    
    logger.info(f"测试完成，共解析 {count} 个对象")


if __name__ == '__main__':
    main()