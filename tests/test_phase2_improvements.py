#!/usr/bin/env python3
"""
Phase 2 改进测试：去重算法和思维链捕获
"""
import asyncio
import pytest
import asyncpg
import numpy as np
import json
from datetime import datetime, timezone
from unittest.mock import AsyncMock, patch
import sys
import os

# 添加项目根目录到路径
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from sage_core.memory.storage import MemoryStorage
from sage_core.database import DatabaseConnection
from sage_core.interfaces import MemoryContent


async def test_enhanced_deduplication():
    """测试增强的去重算法"""
    print("测试增强的去重算法...")
    
    try:
        # 连接数据库
        pool = await asyncpg.create_pool(
            host=os.getenv("DB_HOST", "localhost"),
            port=int(os.getenv("DB_PORT", "5432")),
            database=os.getenv("DB_NAME", "sage_memory"),
            user=os.getenv("DB_USER", "sage"),
            password=os.getenv("DB_PASSWORD", "sage123"),
            min_size=1,
            max_size=5
        )
        
        # 创建数据库连接包装器
        class PoolWrapper:
            def __init__(self, pool):
                self.pool = pool
            
            async def fetchval(self, query, *args):
                async with self.pool.acquire() as conn:
                    return await conn.fetchval(query, *args)
            
            async def fetchrow(self, query, *args):
                async with self.pool.acquire() as conn:
                    return await conn.fetchrow(query, *args)
            
            async def fetch(self, query, *args):
                async with self.pool.acquire() as conn:
                    return await conn.fetch(query, *args)
            
            async def execute(self, query, *args):
                async with self.pool.acquire() as conn:
                    return await conn.execute(query, *args)
        
        db_wrapper = PoolWrapper(pool)
        storage = MemoryStorage(db_wrapper, None)
        
        # 生成测试向量
        test_embedding = np.random.randn(4096).astype(np.float32)
        
        # 测试1：保存第一条记录
        memory_id_1 = await storage.save(
            user_input="测试用户输入",
            assistant_response="测试助手回复",
            embedding=test_embedding,
            metadata={"test": "phase2", "message_count": 5},
            session_id="test_dedup_session"
        )
        print(f"✓ 第一条记录保存成功: {memory_id_1}")
        
        # 测试2：保存相同内容（应该被去重）
        memory_id_2 = await storage.save(
            user_input="测试用户输入",
            assistant_response="测试助手回复",
            embedding=test_embedding,
            metadata={"test": "phase2", "message_count": 5},
            session_id="test_dedup_session"
        )
        
        if memory_id_1 == memory_id_2:
            print("✓ 相同内容去重测试通过")
        else:
            print("✗ 相同内容去重测试失败")
        
        # 测试3：保存相似内容但有新元数据（应该被保存）
        memory_id_3 = await storage.save(
            user_input="测试用户输入",
            assistant_response="测试助手回复",
            embedding=test_embedding,
            metadata={"test": "phase2", "message_count": 10, "tool_calls": [{"name": "test_tool"}]},
            session_id="test_dedup_session"
        )
        
        if memory_id_1 != memory_id_3:
            print("✓ 有新信息的相似内容保存测试通过")
        else:
            print("✗ 有新信息的相似内容保存测试失败")
        
        # 验证数据库中的记录
        async with pool.acquire() as conn:
            count = await conn.fetchval(
                "SELECT COUNT(*) FROM memories WHERE session_id = $1",
                "test_dedup_session"
            )
            print(f"✓ 数据库中共有 {count} 条记录（预期2条）")
        
    except Exception as e:
        print(f"去重测试失败: {e}")
        import traceback
        traceback.print_exc()
    finally:
        if 'pool' in locals():
            await pool.close()


def test_thinking_chain_parsing():
    """测试思维链解析逻辑"""
    print("测试思维链解析逻辑...")
    
    # 模拟用户消息中包含thinking的情况
    user_message_with_thinking = {
        "type": "user",
        "message": {
            "content": [
                {"type": "text", "text": "用户的问题"},
                {"type": "thinking", "thinking": "用户的思考过程..."}
            ]
        }
    }
    
    # 模拟助手消息中包含thinking的情况
    assistant_message_with_thinking = {
        "type": "assistant",
        "message": {
            "content": [
                {"type": "thinking", "thinking": "助手的思考过程..."},
                {"type": "text", "text": "助手的回复"}
            ]
        }
    }
    
    # 模拟解析函数（简化版）
    def parse_content(entry):
        entry_type = entry.get('type', '')
        message = entry.get('message', {})
        content = message.get('content', [])
        content_parts = []
        
        if isinstance(content, list):
            for item in content:
                if isinstance(item, dict):
                    if item.get('type') == 'text':
                        content_parts.append(item.get('text', ''))
                    elif item.get('type') == 'thinking':
                        thinking_content = item.get('thinking', '')
                        if entry_type == 'user':
                            content_parts.append(f"[用户思维链]\n{thinking_content}")
                        else:
                            content_parts.append(f"[思维链]\n{thinking_content}")
        
        return '\n'.join(content_parts)
    
    # 测试用户思维链解析
    user_parsed = parse_content(user_message_with_thinking)
    if "[用户思维链]" in user_parsed:
        print("✓ 用户思维链解析测试通过")
    else:
        print("✗ 用户思维链解析测试失败")
    
    # 测试助手思维链解析
    assistant_parsed = parse_content(assistant_message_with_thinking)
    if "[思维链]" in assistant_parsed:
        print("✓ 助手思维链解析测试通过")
    else:
        print("✗ 助手思维链解析测试失败")
    
    print(f"用户解析结果: {user_parsed}")
    print(f"助手解析结果: {assistant_parsed}")


def test_text_truncation_improvements():
    """测试文本截断改进"""
    print("测试文本截断改进...")
    
    # 模拟安全工具类
    class MockSecurityUtils:
        def sanitize_string(self, text: str, max_length: int = 200000, enable_chunking: bool = True) -> str:
            if not text:
                return ""
            
            if enable_chunking and len(text) > max_length:
                # 启用分块时不截断
                pass
            elif len(text) > max_length:
                # 禁用分块时才截断
                text = text[:max_length] + "...[truncated]"
            
            return text
    
    security_utils = MockSecurityUtils()
    
    # 测试长文本（启用分块）
    long_text = "测试" * 100000  # 400K字符
    result_chunking = security_utils.sanitize_string(long_text, max_length=200000, enable_chunking=True)
    
    if not result_chunking.endswith("...[truncated]"):
        print("✓ 启用分块时长文本不截断测试通过")
    else:
        print("✗ 启用分块时长文本不截断测试失败")
    
    # 测试长文本（禁用分块）
    result_no_chunking = security_utils.sanitize_string(long_text, max_length=200000, enable_chunking=False)
    
    if result_no_chunking.endswith("...[truncated]"):
        print("✓ 禁用分块时长文本截断测试通过")
    else:
        print("✗ 禁用分块时长文本截断测试失败")


async def main():
    """运行所有Phase 2测试"""
    print("=== Phase 2 改进测试开始 ===\n")
    
    # 测试去重算法改进
    await test_enhanced_deduplication()
    print()
    
    # 测试思维链捕获改进
    test_thinking_chain_parsing()
    print()
    
    # 测试文本截断改进
    test_text_truncation_improvements()
    
    print("\n=== Phase 2 改进测试完成 ===")


if __name__ == "__main__":
    asyncio.run(main())