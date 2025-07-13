#!/usr/bin/env python3
"""
测试记忆系统性能
"""

import time
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from memory_interface import get_memory_provider

def test_search_performance():
    """测试搜索性能"""
    memory_provider = get_memory_provider()
    
    print("测试搜索性能...")
    
    # 测试search_memory
    print("\n1. 测试 search_memory:")
    start = time.time()
    results = memory_provider.search_memory("Python", n=5)
    end = time.time()
    print(f"   搜索耗时: {end - start:.2f}秒")
    print(f"   结果数量: {len(results)}")
    
    # 测试get_context
    print("\n2. 测试 get_context:")
    start = time.time()
    context = memory_provider.get_context("Python list comprehension")
    end = time.time()
    print(f"   获取上下文耗时: {end - start:.2f}秒")
    print(f"   上下文长度: {len(context)} 字符")
    
    # 测试save_conversation
    print("\n3. 测试 save_conversation:")
    start = time.time()
    memory_provider.save_conversation(
        user_prompt="Performance test question",
        assistant_response="Performance test response",
        metadata={"test": True}
    )
    end = time.time()
    print(f"   保存耗时: {end - start:.2f}秒")

if __name__ == "__main__":
    test_search_performance()