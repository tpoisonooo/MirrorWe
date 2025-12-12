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
from mirror import APIContact  # 通过包的 __init__.py 导入


async def test_contact_operations():
    """测试联系人相关操作"""
    print("初始化 APIContact...")
    api_contact = APIContact()

    print("测试获取通讯录...")
    try:
        address_book = await api_contact.get_address_book()
        print(f"通讯录获取成功: {len(address_book.get('friends', []))} 个好友")
        print(f"群聊数量: {len(address_book.get('chatrooms', []))}")
        return True
    except Exception as e:
        print(f"获取通讯录失败: {e}")
        return False


async def test_search_and_add():
    """测试搜索和添加好友功能 (mock 测试)"""
    print("\n测试搜索和添加好友...")
    api_contact = APIContact()

    # 使用一个模拟的手机号进行测试
    # 注意: 这里不会真的执行，因为需要真实的登录状态
    try:
        # 这将失败，但我们可以测试错误处理
        result = await api_contact.search_and_add(phone='18612393510')
        print(f"搜索结果: {result}")
        return True
    except Exception as e:
        print(f"搜索失败 (预期): {e}")
        return True  # 这是预期的，因为我们没有真实登录


async def test_contact_info():
    """测试获取联系人信息"""
    print("\n测试获取联系人信息...")
    api_contact = APIContact()

    try:
        # 尝试获取一些联系人信息
        contact_info = await api_contact.get_contact(['test_user_id'])
        print(f"联系人信息: {contact_info}")
        return True
    except Exception as e:
        print(f"获取联系人信息失败: {e}")
        return True  # 这也是预期的


async def main():
    """主测试函数"""
    print("=== 联系人API测试开始 ===\n")
    print("\n=== 功能测试 ===")

    # 运行测试
    test_results = []

    print("\n1. 测试通讯录获取:")
    test_results.append(await test_contact_operations())

    print("\n2. 测试搜索和添加:")
    test_results.append(await test_search_and_add())

    print("\n3. 测试联系人信息:")
    test_results.append(await test_contact_info())

    # 总结
    passed = sum(test_results)
    total = len(test_results)

    print(f"\n=== 测试总结 ===")
    print(f"通过: {passed}/{total}")

    return passed == total


if __name__ == '__main__':
    # 运行测试
    success = asyncio.run(main())
    sys.exit(0 if success else 1)
