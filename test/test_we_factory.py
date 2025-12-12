#!/usr/bin/env python3
"""
测试 WeFactory 工厂类
"""

import asyncio
import sys
from pathlib import Path

# 添加项目根目录到Python路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))


async def test_factory():
    """测试工厂类的基本功能"""
    print("=== 测试 WeFactory ===")

    try:
        # 导入工厂类
        from mirror.core.we import get_factory

        # 获取工厂实例
        factory = get_factory(max_cache_size=10)
        print(f"✓ 工厂创建成功，缓存大小: {factory.max_cache_size}")

        # 测试获取Person对象
        test_wxid = "wxid_test_user_123"
        person = await factory.get_person(test_wxid)

        if person:
            print(f"✓ 成功创建Person对象: {test_wxid}")
            print(f"  - 对象类型: {type(person).__name__}")
            print(f"  - wxid: {person.wxid}")
        else:
            print(f"✗ 创建Person对象失败: {test_wxid}")

        # 测试获取Group对象
        test_group_id = "199933xxx@chatroom"
        group = await factory.get_group(test_group_id)

        if group:
            print(f"✓ 成功创建Group对象: {test_group_id}")
            print(f"  - 对象类型: {type(group).__name__}")
            print(f"  - group_id: {group.group_id}")
        else:
            print(f"✗ 创建Group对象失败: {test_group_id}")

        # 测试智能实体获取
        test_cases = [
            "wxid_normal_user", "1234567890@chatroom", "test_user_123",
            "group_123@chatroom"
        ]

        print("\n=== 测试智能实体识别 ===")
        for test_id in test_cases:
            entity = await factory.get_entity(test_id)
            if entity:
                entity_type = "Group" if hasattr(entity,
                                                 'group_id') else "Person"
                print(f"✓ {test_id} -> {entity_type}")
            else:
                print(f"✗ {test_id} -> 失败")

        # 测试缓存统计
        stats = factory.get_cache_stats()
        print(f"\n=== 缓存统计 ===")
        print(f"Person缓存: {stats['person_cache_size']}")
        print(f"Group缓存: {stats['group_cache_size']}")
        print(f"总缓存: {stats['total_cached']}")
        print(f"Person命中: {stats['person_hits']}")
        print(f"Person未命中: {stats['person_misses']}")
        print(f"Group命中: {stats['group_hits']}")
        print(f"Group未命中: {stats['group_misses']}")

        # 测试缓存命中
        print(f"\n=== 测试缓存命中 ===")
        person2 = await factory.get_person(test_wxid)
        if person2 is person:
            print("✓ 缓存命中成功（同一对象）")
        else:
            print("✗ 缓存未命中")

        # 清理
        await factory.cleanup()
        print(f"\n✓ 清理完成")

        return True

    except Exception as e:
        print(f"✗ 测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == '__main__':
    try:
        loop = asyncio.get_event_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
    success = loop.run_until_complete(test_factory())
    sys.exit(0 if success else 1)
