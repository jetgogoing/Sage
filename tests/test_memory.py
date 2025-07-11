#!/usr/bin/env python3
"""测试 memory.py 模块的功能"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from memory import embed_text, get_db_connection, SILICONFLOW_API_KEY

def test_db_connection():
    """测试数据库连接"""
    try:
        conn = get_db_connection()
        print("✓ 数据库连接成功")
        conn.close()
        return True
    except Exception as e:
        print(f"✗ 数据库连接失败: {e}")
        return False

def test_embedding():
    """测试文本向量化功能"""
    try:
        test_text = "这是一个测试文本"
        print(f"正在向量化文本: '{test_text}'")
        
        embedding = embed_text(test_text)
        
        if isinstance(embedding, list) and len(embedding) == 4096:
            print(f"✓ 向量化成功，维度: {len(embedding)}")
            print(f"  前5个值: {embedding[:5]}")
            return True
        else:
            print(f"✗ 向量维度错误: {len(embedding) if embedding else 'None'}")
            return False
            
    except Exception as e:
        print(f"✗ 向量化失败: {e}")
        return False

def test_get_context():
    """测试上下文获取功能"""
    try:
        from memory import get_context
        
        test_query = "如何使用 Python 排序列表？"
        print(f"\n测试查询: '{test_query}'")
        
        context = get_context(test_query)
        
        if context:
            print(f"✓ 获取上下文成功")
            print(f"  上下文内容: {context[:100]}...")
        else:
            print("✓ 获取上下文成功（无相关历史）")
        
        return True
        
    except Exception as e:
        print(f"✗ 获取上下文失败: {e}")
        return False

if __name__ == "__main__":
    print("=== 测试 memory.py 模块功能 ===")
    print(f"API Key 设置: {'已设置' if SILICONFLOW_API_KEY else '未设置'}")
    
    print("\n1. 测试数据库连接")
    test_db_connection()
    
    print("\n2. 测试文本向量化")
    test_embedding()
    
    print("\n3. 测试上下文获取")
    test_get_context()