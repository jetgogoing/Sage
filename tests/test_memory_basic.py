#!/usr/bin/env python3
"""基础测试 memory.py 模块"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

def test_imports():
    """测试模块导入"""
    try:
        import memory
        print("✓ memory.py 模块导入成功")
        
        # 检查关键函数
        funcs = ['get_context', 'save_memory', 'embed_text', 'get_db_connection']
        for func in funcs:
            if hasattr(memory, func):
                print(f"  ✓ 函数 {func} 存在")
            else:
                print(f"  ✗ 函数 {func} 不存在")
                
        return True
    except Exception as e:
        print(f"✗ 模块导入失败: {e}")
        return False

def test_db_config():
    """测试数据库配置"""
    from memory import DB_CONFIG
    print("\n数据库配置:")
    for key, value in DB_CONFIG.items():
        print(f"  {key}: {value}")
    return True

def test_api_config():
    """测试 API 配置"""
    from memory import SILICONFLOW_API_KEY, EMBEDDING_MODEL, LLM_MODEL
    print("\nAPI 配置:")
    print(f"  API Key: {'已设置' if SILICONFLOW_API_KEY else '未设置'}")
    print(f"  嵌入模型: {EMBEDDING_MODEL}")
    print(f"  LLM 模型: {LLM_MODEL}")
    return True

if __name__ == "__main__":
    print("=== 基础测试 memory.py 模块 ===")
    test_imports()
    test_db_config()
    test_api_config()
    print("\n基础配置验证完成")