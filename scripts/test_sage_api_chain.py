#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试 Sage MCP 系统的 API 调用链路
验证向量存储和AI压缩功能是否正常工作
"""
import asyncio
import logging
import os
import sys
from pathlib import Path
import time
from datetime import datetime

# 添加项目路径
sys.path.insert(0, str(Path(__file__).parent.parent))

from sage_core.memory.vectorizer import TextVectorizer
from sage_core.memory.text_generator import TextGenerator
from sage_core.config.manager import ConfigManager

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


async def test_embedding_api():
    """测试向量化 API"""
    logger.info("=" * 60)
    logger.info("测试 Qwen/Qwen3-Embedding-8B API")
    logger.info("=" * 60)
    
    try:
        vectorizer = TextVectorizer()
        await vectorizer.initialize()
        
        # 测试文本
        test_texts = [
            "这是一个测试文本，用于验证向量化功能是否正常工作。",
            "Sage MCP 系统使用 SiliconFlow API 进行文本向量化。",
            "向量化后的结果应该是 4096 维的浮点数组。"
        ]
        
        for i, text in enumerate(test_texts, 1):
            logger.info(f"\n测试 {i}: {text[:50]}...")
            start_time = time.time()
            
            # 调用向量化 API
            embedding = await vectorizer.vectorize(text)
            
            elapsed = time.time() - start_time
            logger.info(f"✓ 向量化成功!")
            logger.info(f"  - 维度: {len(embedding)}")
            logger.info(f"  - 类型: {type(embedding)}")
            logger.info(f"  - 耗时: {elapsed:.3f}秒")
            logger.info(f"  - 前5个值: {embedding[:5].tolist()}")
            
            # 验证维度
            assert len(embedding) == 4096, f"期望 4096 维，实际 {len(embedding)} 维"
        
        logger.info("\n✅ 向量化 API 测试通过!")
        return True
        
    except Exception as e:
        logger.error(f"❌ 向量化 API 测试失败: {e}")
        return False


async def test_text_generation_api():
    """测试文本生成 API (AI压缩)"""
    logger.info("=" * 60)
    logger.info("测试 Tongyi-Zhiwen/QwenLong-L1-32B API")
    logger.info("=" * 60)
    
    try:
        generator = TextGenerator()
        await generator.initialize()
        
        # 测试消息
        test_cases = [
            {
                "name": "简单对话",
                "messages": [
                    {"role": "system", "content": "你是一个有帮助的助手。"},
                    {"role": "user", "content": "请简单介绍一下 Sage MCP 系统。"}
                ],
                "max_tokens": 500
            },
            {
                "name": "记忆压缩",
                "messages": [
                    {"role": "system", "content": "请将以下对话历史压缩成一个简短的摘要：\n\n用户：如何配置 Sage？\n助手：首先需要设置环境变量...\n用户：向量化功能正常吗？\n助手：是的，系统使用 SiliconFlow API..."},
                    {"role": "user", "content": "请生成摘要"}
                ],
                "max_tokens": 300
            }
        ]
        
        for test_case in test_cases:
            logger.info(f"\n测试: {test_case['name']}")
            start_time = time.time()
            
            # 调用生成 API
            response = await generator.generate(
                messages=test_case['messages'],
                max_tokens=test_case['max_tokens'],
                temperature=0.3
            )
            
            elapsed = time.time() - start_time
            logger.info(f"✓ 生成成功!")
            logger.info(f"  - 响应长度: {len(response)} 字符")
            logger.info(f"  - 耗时: {elapsed:.3f}秒")
            logger.info(f"  - 响应预览: {response[:200]}...")
            
            # 验证响应
            assert len(response) > 0, "响应为空"
        
        logger.info("\n✅ 文本生成 API 测试通过!")
        return True
        
    except Exception as e:
        logger.error(f"❌ 文本生成 API 测试失败: {e}")
        return False


async def test_ai_compression():
    """测试 AI 压缩功能"""
    logger.info("=" * 60)
    logger.info("测试 AI 压缩功能 (compress 方法)")
    logger.info("=" * 60)
    
    try:
        generator = TextGenerator()
        await generator.initialize()
        
        # 准备测试数据
        memories = [
            {
                "user_input": "如何安装 Sage MCP？",
                "assistant_response": "首先需要克隆仓库，然后安装依赖..."
            },
            {
                "user_input": "配置文件在哪里？",
                "assistant_response": "配置文件位于 .env 文件中..."
            },
            {
                "user_input": "如何测试功能？",
                "assistant_response": "可以运行 pytest 进行测试..."
            }
        ]
        
        logger.info(f"压缩 {len(memories)} 条记忆...")
        start_time = time.time()
        
        # 调用压缩方法
        compressed = await generator.compress(
            memories=memories,
            max_tokens=500
        )
        
        elapsed = time.time() - start_time
        logger.info(f"✓ 压缩成功!")
        logger.info(f"  - 原始记忆数: {len(memories)}")
        logger.info(f"  - 压缩后长度: {len(compressed)} 字符")
        logger.info(f"  - 耗时: {elapsed:.3f}秒")
        logger.info(f"  - 压缩内容: {compressed[:300]}...")
        
        logger.info("\n✅ AI 压缩功能测试通过!")
        return True
        
    except Exception as e:
        logger.error(f"❌ AI 压缩功能测试失败: {e}")
        return False


async def check_api_usage():
    """检查 API 使用情况"""
    logger.info("=" * 60)
    logger.info("API 配置检查")
    logger.info("=" * 60)
    
    # 检查环境变量
    api_key = os.getenv('SILICONFLOW_API_KEY')
    if api_key:
        logger.info(f"✓ SILICONFLOW_API_KEY 已设置")
        logger.info(f"  - 前8位: {api_key[:8]}...")
    else:
        logger.error("❌ SILICONFLOW_API_KEY 未设置")
    
    # 检查配置
    config = ConfigManager()
    logger.info("\n配置信息:")
    logger.info(f"  - Embedding模型: {config.get('embedding.model', 'Qwen/Qwen3-Embedding-8B')}")
    logger.info(f"  - AI压缩模型: {config.get('ai_compression.model', 'Tongyi-Zhiwen/QwenLong-L1-32B')}")
    logger.info(f"  - AI压缩启用: {config.get('ai_compression.enable', True)}")
    logger.info(f"  - 降级处理: {config.get('ai_compression.fallback_on_error', True)}")


async def main():
    """主测试函数"""
    logger.info("🚀 开始测试 Sage MCP API 调用链路")
    logger.info(f"时间: {datetime.now().isoformat()}")
    
    # 检查配置
    await check_api_usage()
    
    # 测试结果
    results = {}
    
    # 1. 测试向量化 API
    results['embedding'] = await test_embedding_api()
    await asyncio.sleep(1)  # 避免请求过快
    
    # 2. 测试文本生成 API
    results['generation'] = await test_text_generation_api()
    await asyncio.sleep(1)
    
    # 3. 测试 AI 压缩
    results['compression'] = await test_ai_compression()
    
    # 总结
    logger.info("\n" + "=" * 60)
    logger.info("测试总结")
    logger.info("=" * 60)
    
    for name, passed in results.items():
        status = "✅ 通过" if passed else "❌ 失败"
        logger.info(f"  - {name}: {status}")
    
    all_passed = all(results.values())
    if all_passed:
        logger.info("\n🎉 所有测试通过! API 调用链路正常工作。")
        logger.info("💡 提示: 如果 SiliconFlow 后台没有显示 token 消耗，")
        logger.info("   可能是因为 API 调用失败并降级到了本地处理。")
        logger.info("   请检查上面的日志中是否有降级处理的警告信息。")
    else:
        logger.error("\n⚠️ 部分测试失败，请检查错误信息。")
    
    return all_passed


if __name__ == "__main__":
    result = asyncio.run(main())
    sys.exit(0 if result else 1)