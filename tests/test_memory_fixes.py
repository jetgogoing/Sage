#!/usr/bin/env python3
"""测试记忆系统修复效果"""

import asyncio
import json
import os
import sys
from pathlib import Path

# 添加项目路径
sys.path.insert(0, str(Path(__file__).parent.parent))

from sage_core.interfaces import MemoryContent
from sage_core.core_service import SageCore

async def test_memory_fixes():
    """测试三个修复：1) 记忆返回质量 2) 去重机制 3) 用户输入存储"""
    
    # 初始化Sage Core
    sage = SageCore()
    config = {
        'database': {
            'host': os.getenv('DB_HOST', 'localhost'),
            'port': int(os.getenv('DB_PORT', '5432')),
            'database': os.getenv('DB_NAME', 'sage_memory'),
            'user': os.getenv('DB_USER', 'sage'),
            'password': os.getenv('DB_PASSWORD', 'sage123')
        }
    }
    
    await sage.initialize(config)
    
    print("=== 测试1: 记忆返回质量 ===")
    # 保存一条包含丰富元数据的记忆
    content1 = MemoryContent(
        user_input="如何实现Sage的prompt enhancer功能？",
        assistant_response="Prompt enhancer是一个智能提示增强系统，使用向量检索和AI压缩技术。",
        metadata={
            'session_id': 'test-session-001',
            'message_count': 2,
            'tool_call_count': 3,
            'tool_calls': [
                {'tool_name': 'mcp__zen__debug'},
                {'tool_name': 'Read'},
                {'tool_name': 'Edit'}
            ],
            'format': 'test_script'
        }
    )
    
    memory_id1 = await sage.save_memory(content1)
    print(f"保存记忆1: {memory_id1}")
    
    # 测试get_context返回的格式
    context = await sage.get_context("prompt enhancer", max_results=5)
    print(f"\n返回的上下文格式化内容:\n{context}")
    
    print("\n=== 测试2: 去重机制 ===")
    # 尝试保存相同内容
    memory_id2 = await sage.save_memory(content1)
    print(f"尝试重复保存: {memory_id2}")
    print(f"是否去重成功: {'是' if memory_id1 == memory_id2 else '否'}")
    
    # 保存略有不同的内容
    content2 = MemoryContent(
        user_input="如何实现Sage的prompt enhancer功能？",  # 相同问题
        assistant_response="这是一个不同的回答。",  # 不同回答
        metadata={'session_id': 'test-session-001'}
    )
    memory_id3 = await sage.save_memory(content2)
    print(f"保存不同内容: {memory_id3}")
    print(f"是否创建新记录: {'是' if memory_id3 != memory_id1 else '否'}")
    
    print("\n=== 测试3: 用户输入存储 ===")
    # 保存只有用户输入的记忆
    content3 = MemoryContent(
        user_input="这是一个只有用户输入的测试消息",
        assistant_response="",
        metadata={'session_id': 'test-session-002'}
    )
    memory_id4 = await sage.save_memory(content3)
    print(f"保存只有用户输入的记忆: {memory_id4}")
    
    # 保存只有助手回复的记忆（工具调用结果）
    content4 = MemoryContent(
        user_input="",
        assistant_response="Tool execution result: Success",
        metadata={'session_id': 'test-session-002'}
    )
    memory_id5 = await sage.save_memory(content4)
    print(f"保存只有工具结果的记忆: {memory_id5}")
    
    # 获取并显示会话2的记忆
    context2 = await sage.get_context("测试消息", max_results=5)
    print(f"\n会话2的上下文:\n{context2}")
    
    # 清理资源
    await sage.cleanup()
    print("\n测试完成！")

if __name__ == "__main__":
    asyncio.run(test_memory_fixes())