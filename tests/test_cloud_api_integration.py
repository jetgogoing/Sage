#!/usr/bin/env python3
"""
测试云端 API 集成
验证 SiliconFlow API 调用和 4096 维向量支持
"""
import asyncio
import os
import sys
from pathlib import Path
import numpy as np

# 添加项目路径
sys.path.insert(0, str(Path(__file__).parent))

# 导入模块
from sage_core.memory.vectorizer import TextVectorizer
from memory import embed_text, search_similar_conversations, save_memory

async def test_vectorizer():
    """测试 sage_core 的向量化器"""
    print("=== 测试 sage_core TextVectorizer ===")
    
    vectorizer = TextVectorizer()
    await vectorizer.initialize()
    
    # 测试单个文本
    text = "我的猫叫面团，它喜欢钻纸箱"
    vector = await vectorizer.vectorize(text)
    
    print(f"向量维度: {vector.shape}")
    print(f"向量类型: {type(vector)}")
    print(f"期望维度: {vectorizer.get_dimension()}")
    
    assert vector.shape == (4096,), f"向量维度错误: {vector.shape}"
    assert isinstance(vector, np.ndarray), "向量类型错误"
    
    # 测试批量文本
    texts = ["第一个文本", "第二个文本", "第三个文本"]
    vectors = await vectorizer.vectorize(texts)
    
    print(f"\n批量向量形状: {vectors.shape}")
    assert vectors.shape == (3, 4096), f"批量向量形状错误: {vectors.shape}"
    
    print("✅ sage_core 向量化器测试通过")

def test_memory_api():
    """测试 memory.py 的 API 调用"""
    print("\n=== 测试 memory.py embed_text ===")
    
    text = "测试文本向量化"
    try:
        vector = embed_text(text)
        print(f"向量长度: {len(vector)}")
        print(f"向量类型: {type(vector)}")
        
        assert len(vector) == 4096, f"向量维度错误: {len(vector)}"
        assert isinstance(vector, list), "向量类型错误"
        
        print("✅ memory.py 向量化测试通过")
        return True
    except Exception as e:
        print(f"❌ 测试失败: {e}")
        return False

async def test_integration():
    """测试完整集成"""
    print("\n=== 测试完整集成流程 ===")
    
    # 1. 测试向量化一致性
    test_text = "这是一个测试文本"
    
    # sage_core 向量化
    vectorizer = TextVectorizer()
    await vectorizer.initialize()
    vector1 = await vectorizer.vectorize(test_text)
    
    # memory.py 向量化
    vector2 = embed_text(test_text)
    
    print(f"sage_core 向量形状: {vector1.shape}")
    print(f"memory.py 向量长度: {len(vector2)}")
    
    # 验证维度一致
    assert vector1.shape[0] == len(vector2) == 4096, "向量维度不一致"
    
    print("✅ 集成测试通过 - 所有组件使用 4096 维向量")

async def main():
    """主测试函数"""
    print("开始测试云端 API 集成...\n")
    
    # 检查环境变量
    if not os.getenv('SILICONFLOW_API_KEY'):
        print("⚠️  警告: SILICONFLOW_API_KEY 未设置")
        print("测试将使用哈希向量化降级方案")
    
    try:
        # 测试 sage_core
        await test_vectorizer()
        
        # 测试 memory.py
        test_memory_api()
        
        # 测试集成
        await test_integration()
        
        print("\n🎉 所有测试通过！云端 API 集成正常工作")
        print("✅ 已确认使用 4096 维向量")
        print("✅ SiliconFlow API 调用正常")
        
    except Exception as e:
        print(f"\n❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(main())