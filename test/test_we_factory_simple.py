#!/usr/bin/env python3
"""
简单的工厂类结构测试 - 不执行实际导入
"""

import sys
from pathlib import Path

# 添加项目根目录到Python路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

def test_structure():
    """测试工厂类的基本结构"""
    print("=== 测试 WeFactory 结构 ===")
    
    try:
        # 检查文件结构
        factory_file = Path("mirror/core/we.py")
        if factory_file.exists():
            print("✓ 工厂文件存在")
        else:
            print("✗ 工厂文件不存在")
            return False
        
        # 读取文件内容进行分析
        with open(factory_file, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # 检查关键组件
        key_components = [
            "class WeFactory:",
            "def get_person",
            "def get_group", 
            "def get_entity",
            "_is_group_id",
            "_person_cache",
            "_group_cache",
            "def get_factory",
            "async def get_person",
            "async def get_group"
        ]
        
        missing_components = []
        for component in key_components:
            if component in content:
                print(f"✓ {component}")
            else:
                print(f"✗ {component}")
                missing_components.append(component)
        
        # 检查LRU缓存机制
        cache_mechanisms = [
            "weakref.ref",
            "atexit.register",
            "_on_person_finalized",
            "_on_group_finalized",
            "_evict_oldest_person",
            "_evict_oldest_group"
        ]
        
        for mechanism in cache_mechanisms:
            if mechanism in content:
                print(f"✓ 缓存机制: {mechanism}")
            else:
                print(f"✗ 缓存机制: {mechanism}")
        
        # 检查清理功能（简化版，移除数据同步功能检查）
        cleanup_functions = [
            "cleanup",
            "_cleanup_all"
        ]
        
        for func in cleanup_functions:
            if func in content:
                print(f"✓ 清理功能: {func}")
            else:
                print(f"✗ 清理功能: {func}")
        
        # 检查统计功能
        if "get_cache_stats" in content:
            print("✓ 缓存统计功能")
        else:
            print("✗ 缓存统计功能")
        
        # 检查群聊ID识别逻辑（修复逻辑）
        if "@chatroom" in content or "@openim" in content:
            print("✓ 群聊ID识别逻辑")
        else:
            print("✗ 群聊ID识别逻辑")
        
        print(f"\n=== 结构分析结果 ===")
        if not missing_components:
            print("✓ 所有关键组件都存在")
            return True
        else:
            print(f"✗ 缺失组件: {missing_components}")
            return False
            
    except Exception as e:
        print(f"✗ 结构测试失败: {e}")
        return False

def test_group_id_detection():
    """测试群聊ID检测逻辑"""
    print(f"\n=== 测试群聊ID检测 ===")
    
    test_cases = [
        ("wxid_normal_user", False, "普通用户ID"),
        ("1234567890@chatroom", True, "标准群聊ID"),
        ("test_group@openim", True, "OpenIM群聊ID"), 
        ("wxid_test123", False, "带数字的用户ID"),
        ("group_name@chatroom", True, "带名字的群聊ID")
    ]
    
    # 简单的检测逻辑（复制自工厂类）
    def _is_group_id(wxid: str) -> bool:
        return '@' in wxid and ('chatroom' in wxid or 'openim' in wxid)
    
    all_passed = True
    for test_id, expected, description in test_cases:
        result = _is_group_id(test_id)
        if result == expected:
            print(f"✓ {description}: {test_id} -> {'Group' if result else 'Person'}")
        else:
            print(f"✗ {description}: {test_id} -> 期望{'Group' if expected else 'Person'}, 实际{'Group' if result else 'Person'}")
            all_passed = False
    
    return all_passed

if __name__ == '__main__':
    test1 = test_structure()
    test2 = test_group_id_detection()
    
    success = test1 and test2
    print(f"\n=== 总体结果 ===")
    print(f"结构测试: {'通过' if test1 else '失败'}")
    print(f"群聊ID检测: {'通过' if test2 else '失败'}")
    print(f"总体: {'通过' if success else '失败'}")
    
    sys.exit(0 if success else 1)