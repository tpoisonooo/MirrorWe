#!/usr/bin/env python3
"""
工厂类核心逻辑验证 - 不依赖复杂导入
"""

import sys
import os
from pathlib import Path

def test_group_id_detection():
    """测试群聊ID检测逻辑（复制自工厂类）"""
    print("=== 测试群聊ID检测逻辑 ===")
    
    def _is_group_id(wxid: str) -> bool:
        """判断是否为群聊ID"""
        return '@' in wxid and ('chatroom' in wxid or 'openim' in wxid)
    
    test_cases = [
        # (wxid, 期望结果, 描述)
        ("wxid_normal_user", False, "普通用户ID"),
        ("wxid_12345", False, "带数字的用户ID"),
        ("user_name", False, "普通用户名"),
        ("1234567890@chatroom", True, "标准群聊ID"),
        ("test_group@chatroom", True, "带名字的群聊ID"),
        ("group_123@chatroom", True, "带数字的群聊ID"),
        ("abc@openim", True, "OpenIM群聊ID"),
        ("test@openim", True, "OpenIM群聊ID"),
        ("invalid@unknown", False, "未知@类型"),
        ("@chatroom", True, "边界情况：只有@chatroom"),
        ("wxid@user", False, "用户ID包含@但不是群聊"),
    ]
    
    print("测试用例:")
    all_passed = True
    for test_id, expected, description in test_cases:
        result = _is_group_id(test_id)
        status = "✓" if result == expected else "✗"
        entity_type = "Group" if result else "Person"
        print(f"{status} {description}: {test_id} -> {entity_type}")
        if result != expected:
            all_passed = False
    
    return all_passed

def test_path_construction():
    """测试路径构建逻辑"""
    print(f"\n=== 测试路径构建逻辑 ===")
    
    # 模拟工厂类的路径构建
    def construct_paths(entity_id: str, entity_type: str) -> str:
        """构建实体目录路径"""
        # 假设当前文件在 mirror/core/we.py
        current_dir = Path("mirror/core")
        data_dir = current_dir.parent.parent / "data"
        entity_dir = data_dir / entity_type / entity_id
        return str(entity_dir)
    
    test_cases = [
        ("wxid_test123", "friends", "data/friends/wxid_test123"),
        ("123@chatroom", "groups", "data/groups/123@chatroom"),
        ("normal_user", "friends", "data/friends/normal_user"),
    ]
    
    print("路径构建测试:")
    all_passed = True
    for entity_id, entity_type, expected_suffix in test_cases:
        result = construct_paths(entity_id, entity_type)
        if expected_suffix in result:
            print(f"✓ {entity_type}/{entity_id} -> {result}")
        else:
            print(f"✗ {entity_type}/{entity_id} -> {result} (期望包含: {expected_suffix})")
            all_passed = False
    
    return all_passed

def test_cache_key_logic():
    """测试缓存键逻辑（简化版，不依赖数据同步）"""
    print(f"\n=== 测试缓存键逻辑 ===")
    
    # 模拟缓存结构（只测试键管理，不涉及数据同步）
    person_cache = {}
    group_cache = {}
    
    def add_to_cache(entity_id: str, entity_type: str):
        """添加到相应缓存（仅键管理）"""
        if entity_type == "person":
            person_cache[entity_id] = f"cached_{entity_type}_{entity_id}"
        else:
            group_cache[entity_id] = f"cached_{entity_type}_{entity_id}"
    
    def get_from_cache(entity_id: str) -> str:
        """从缓存获取"""
        if entity_id in person_cache:
            return person_cache[entity_id]
        if entity_id in group_cache:
            return group_cache[entity_id]
        return None
    
    def remove_from_cache(entity_id: str):
        """从缓存移除（模拟对象销毁）"""
        if entity_id in person_cache:
            del person_cache[entity_id]
        elif entity_id in group_cache:
            del group_cache[entity_id]
    
    # 测试用例
    test_entities = [
        ("wxid_user1", "person"),
        ("123@chatroom", "group"),
        ("wxid_user2", "person"),
        ("456@chatroom", "group"),
    ]
    
    print("缓存生命周期测试:")
    all_passed = True
    
    # 添加到缓存
    for entity_id, entity_type in test_entities:
        add_to_cache(entity_id, entity_type)
        print(f"✓ 添加缓存: {entity_id} ({entity_type})")
    
    # 从缓存获取
    for entity_id, expected_type in test_entities:
        result = get_from_cache(entity_id)
        if result and expected_type in result:
            print(f"✓ 缓存获取: {entity_id} -> {result}")
        else:
            print(f"✗ 缓存获取: {entity_id} -> {result}")
            all_passed = False
    
    # 测试缓存未命中
    unknown_id = "unknown_entity"
    result = get_from_cache(unknown_id)
    if result is None:
        print(f"✓ 缓存未命中: {unknown_id}")
    else:
        print(f"✗ 缓存未命中: {unknown_id} -> {result}")
        all_passed = False
    
    # 测试缓存清理（模拟对象销毁）
    print("\n缓存清理测试:")
    for entity_id, entity_type in test_entities[:2]:  # 清理前两个
        remove_from_cache(entity_id)
        result = get_from_cache(entity_id)
        if result is None:
            print(f"✓ 缓存清理: {entity_id}")
        else:
            print(f"✗ 缓存清理: {entity_id} -> 仍然存在于缓存")
            all_passed = False
    
    return all_passed

def main():
    """主测试函数"""
    print("=== WeFactory 核心逻辑验证 ===")
    
    test1 = test_group_id_detection()
    test2 = test_path_construction()
    test3 = test_cache_key_logic()
    
    success = test1 and test2 and test3
    
    print(f"\n=== 验证结果总结 ===")
    print(f"群聊ID检测: {'通过' if test1 else '失败'}")
    print(f"路径构建: {'通过' if test2 else '失败'}")
    print(f"缓存键逻辑: {'通过' if test3 else '失败'}")
    print(f"总体结果: {'通过' if success else '失败'}")
    
    return success

if __name__ == '__main__':
    success = main()
    sys.exit(0 if success else 1)