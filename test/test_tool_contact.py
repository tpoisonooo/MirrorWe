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
from mirror.tool.contact import ListPrivateFriend, ListPrivateFriendParams
from mirror.tool.contact import ListGroup, ListGroupParams
from mirror.tool.contact import GroupChatFriend, GroupChatFriendParams


async def main():
    print("=== 工具测试开始 ===\n")

    private_friend_result = await ListPrivateFriend()(
        ListPrivateFriendParams())

    group_result = await ListGroup()(ListGroupParams())

    friend_in_group_result = await GroupChatFriend()(GroupChatFriendParams())


if __name__ == '__main__':
    # 运行测试
    success = asyncio.run(main())
    sys.exit(0 if success else 1)
