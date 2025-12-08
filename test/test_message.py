#!/usr/bin/env python3
"""
改进的联系人测试文件 - 展示不同的导入方式
"""

import sys
import os
import asyncio
from pathlib import Path

# 方法1: 将项目根目录添加到 Python 路径 (推荐用于测试)
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# 现在可以顺利导入
from mirror import APIMessage  # 通过包的 __init__.py 导入

async def test_revert_all():
    """测试发送一条消息，10s后撤回"""
    api_message = APIMessage()
    await api_message.send_user_text(user_id='wxid_raxq4pq3emg212', text='你好！')
    await api_message.revert_all()

async def main():
    """主测试函数"""
    print("=== 消息API测试开始 ===\n")
    
    # 运行测试
    test_results = []
    
    print("\n1. 撤回所有消息:")
    test_results.append(await test_revert_all())
    
if __name__ == '__main__':
    # 运行测试
    success = asyncio.run(main())
    sys.exit(0 if success else 1)