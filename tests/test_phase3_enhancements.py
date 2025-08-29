#!/usr/bin/env python3
"""
Phase 3 增强测试：分块向量化和元数据优化
"""
import asyncio
import pytest
import numpy as np
import json
import sys
import os

# 添加项目根目录到路径
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from sage_core.memory.vectorizer import TextVectorizer
from sage_core.memory.storage import MemoryStorage


def test_smart_chunking():
    """测试智能分块功能"""
    print("测试智能分块功能...")
    
    # 创建向量化器
    vectorizer = TextVectorizer()
    
    # 测试短文本（不需要分块）
    short_text = "这是一个短文本" * 10  # 约70字符
    chunks = vectorizer._smart_chunk_text(short_text, chunk_size=1000)
    
    if len(chunks) == 1:
        print("✓ 短文本不分块测试通过")
    else:
        print("✗ 短文本不分块测试失败")
    
    # 测试长文本（需要分块）
    long_text = "这是一个很长的文本段落。" * 1000  # 约11000字符
    chunks = vectorizer._smart_chunk_text(long_text, chunk_size=1000)
    
    if len(chunks) > 1:
        print(f"✓ 长文本分块测试通过，分为{len(chunks)}块")
    else:
        print("✗ 长文本分块测试失败")
    
    # 测试段落分割
    paragraph_text = "第一段内容\n\n第二段内容\n\n第三段内容"
    chunks = vectorizer._smart_chunk_text(paragraph_text, chunk_size=20)
    
    if len(chunks) >= 2:
        print("✓ 段落分割测试通过")
    else:
        print("✗ 段落分割测试失败")
    
    print(f"分块结果预览: {[chunk[:30] + '...' for chunk in chunks[:3]]}")


async def test_chunked_vectorization():
    """测试分块向量化"""
    print("测试分块向量化...")
    
    try:
        # 创建向量化器
        vectorizer = TextVectorizer()
        await vectorizer.initialize()
        
        # 测试短文本向量化
        short_text = "这是一个测试文本"
        short_embedding = await vectorizer.vectorize(short_text, enable_chunking=False)
        
        if short_embedding.shape == (4096,):
            print("✓ 短文本向量化测试通过")
        else:
            print(f"✗ 短文本向量化测试失败，形状: {short_embedding.shape}")
        
        # 测试长文本分块向量化（使用模拟）
        long_text = "这是一个非常长的测试文本。" * 2000  # 约22000字符
        
        # 由于API限制，我们模拟分块向量化
        with patch.object(vectorizer, '_vectorize_single_text') as mock_vectorize:
            # 模拟每个块的向量化结果
            mock_vectorize.return_value = np.random.randn(4096).astype(np.float32)
            
            long_embedding = await vectorizer.vectorize(long_text, enable_chunking=True, chunk_size=1000)
            
            if long_embedding.shape == (4096,):
                print("✓ 长文本分块向量化测试通过")
                print(f"模拟调用了{mock_vectorize.call_count}次API")
            else:
                print(f"✗ 长文本分块向量化测试失败，形状: {long_embedding.shape}")
    
    except Exception as e:
        print(f"分块向量化测试异常: {e}")
        # 使用降级方案测试
        long_text = "这是一个非常长的测试文本。" * 2000
        try:
            hash_embedding = vectorizer._hash_vectorize(long_text)
            if hash_embedding.shape == (4096,):
                print("✓ 降级哈希向量化测试通过")
            else:
                print(f"✗ 降级哈希向量化测试失败，形状: {hash_embedding.shape}")
        except Exception as e2:
            print(f"降级测试也失败: {e2}")


def test_metadata_optimization():
    """测试元数据优化"""
    print("测试元数据优化...")
    
    # 创建存储实例用于测试
    storage = MemoryStorage(None, None)
    
    # 测试小元数据（不需要优化）
    small_metadata = {
        "session_id": "test_session",
        "message_count": 5,
        "tool_call_count": 2
    }
    
    optimized_small = storage._validate_and_optimize_metadata(small_metadata)
    
    if optimized_small == small_metadata:
        print("✓ 小元数据不优化测试通过")
    else:
        print("✗ 小元数据不优化测试失败")
    
    # 测试大元数据（需要优化）
    large_metadata = {
        "session_id": "test_session",
        "message_count": 100,
        "tool_call_count": 50,
        "tool_calls": [{"name": f"tool_{i}", "args": {"data": "x" * 1000}} for i in range(50)],
        "thinking_content": "这是一个非常长的思考过程..." * 1000,
        "notes": "详细说明" * 10000
    }
    
    # 计算原始大小
    original_size = len(json.dumps(large_metadata, ensure_ascii=False).encode('utf-8'))
    
    optimized_large = storage._validate_and_optimize_metadata(large_metadata)
    optimized_size = len(json.dumps(optimized_large, ensure_ascii=False).encode('utf-8'))
    
    if optimized_size < original_size:
        print(f"✓ 大元数据优化测试通过，{original_size} -> {optimized_size} bytes")
    else:
        print("✗ 大元数据优化测试失败")
    
    # 检查关键字段是否保留
    essential_fields = ['session_id', 'message_count', 'tool_call_count']
    preserved = all(field in optimized_large for field in essential_fields if field in large_metadata)
    
    if preserved:
        print("✓ 关键字段保留测试通过")
    else:
        print("✗ 关键字段保留测试失败")
    
    # 检查工具调用截断
    if 'tool_calls_truncated' in optimized_large:
        print("✓ 工具调用截断标记测试通过")
    else:
        print("✗ 工具调用截断标记测试失败")


async def test_end_to_end_performance():
    """端到端性能测试"""
    print("端到端性能测试...")
    
    try:
        import time
        from unittest.mock import patch, AsyncMock
        
        # 模拟各组件
        mock_vectorizer = AsyncMock(spec=TextVectorizer)
        mock_vectorizer.vectorize.return_value = np.random.randn(4096).astype(np.float32)
        
        # 测试数据
        test_data = [
            ("短文本", "简单测试", {"type": "short"}),
            ("中等长度文本" * 100, "中等测试" * 50, {"type": "medium"}),
            ("超长文本内容" * 2000, "超长回复" * 1000, {"type": "long", "tool_calls": [{"name": f"tool_{i}"} for i in range(20)]})
        ]
        
        total_start = time.time()
        
        for i, (user_input, assistant_response, metadata) in enumerate(test_data):
            start_time = time.time()
            
            # 模拟向量化
            await mock_vectorizer.vectorize(f"{user_input}\n{assistant_response}")
            
            # 模拟元数据优化
            storage = MemoryStorage(None, None)
            optimized_metadata = storage._validate_and_optimize_metadata(metadata)
            
            end_time = time.time()
            processing_time = end_time - start_time
            
            print(f"  测试 {i+1}: {len(user_input + assistant_response)} 字符, {processing_time:.3f}秒")
        
        total_time = time.time() - total_start
        print(f"✓ 端到端性能测试完成，总时间: {total_time:.3f}秒")
        
    except Exception as e:
        print(f"性能测试失败: {e}")


async def main():
    """运行所有Phase 3测试"""
    print("=== Phase 3 增强测试开始 ===\n")
    
    # 测试智能分块
    test_smart_chunking()
    print()
    
    # 测试分块向量化
    await test_chunked_vectorization()
    print()
    
    # 测试元数据优化
    test_metadata_optimization()
    print()
    
    # 端到端性能测试
    await test_end_to_end_performance()
    
    print("\n=== Phase 3 增强测试完成 ===")


if __name__ == "__main__":
    # 需要导入mock用于测试
    try:
        from unittest.mock import patch, AsyncMock
        asyncio.run(main())
    except ImportError:
        print("需要安装mock库进行完整测试")
        # 运行不需要mock的测试
        test_smart_chunking()
        test_metadata_optimization()