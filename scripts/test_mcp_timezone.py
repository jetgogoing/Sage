#!/usr/bin/env python3
"""
测试 Sage MCP Server 查询历史数据时的时间格式
"""

import asyncio
import json
from datetime import datetime
import asyncpg
import os

async def test_direct_db_query():
    """直接查询数据库"""
    db_url = os.getenv('DATABASE_URL', 'postgresql://sage:sage123@localhost:5432/sage_memory')
    conn = await asyncpg.connect(db_url)
    
    try:
        # 查询最新的记忆
        query = "SELECT id, created_at, user_input FROM memories ORDER BY created_at DESC LIMIT 3"
        rows = await conn.fetch(query)
        
        print("=== 直接数据库查询结果 ===")
        for row in rows:
            print(f"ID: {row['id']}")
            print(f"Created at (raw): {row['created_at']}")
            print(f"Created at (type): {type(row['created_at'])}")
            print(f"User input: {row['user_input'][:50]}...")
            print("-" * 50)
            
    finally:
        await conn.close()

async def test_sage_core_query():
    """通过 Sage Core 查询"""
    from sage_core.memory.storage import MemoryStorage
    from sage_core.config.manager import ConfigManager
    
    config = ConfigManager()
    storage = MemoryStorage(config)
    
    try:
        await storage.initialize()
        
        # 搜索记忆
        results = await storage.search_by_embedding(
            query_text="测试",
            limit=3
        )
        
        print("\n=== Sage Core 查询结果 ===")
        for result in results:
            print(f"ID: {result['id']}")
            print(f"Created at: {result['created_at']}")
            print(f"Time format check: Is ISO format? {result['created_at'].endswith('+08:00')}")
            print(f"User input: {result['user_input'][:50]}...")
            print("-" * 50)
            
    finally:
        await storage.close()

async def parse_time_format():
    """解析时间格式"""
    # 模拟 Sage MCP Server 返回的时间
    test_times = [
        "2025-08-03T23:26:24.575796+08:00",  # 带时区的 ISO 格式
        "2025-08-03T15:26:24.575796+00:00",  # UTC 格式
        "2025-08-03T23:26:24.575796"         # 无时区格式
    ]
    
    print("\n=== 时间格式解析测试 ===")
    for time_str in test_times:
        try:
            # 尝试解析
            dt = datetime.fromisoformat(time_str)
            print(f"时间字符串: {time_str}")
            print(f"解析结果: {dt}")
            print(f"时区信息: {dt.tzinfo}")
            print(f"UTC偏移: {dt.utcoffset()}")
            print("-" * 50)
        except Exception as e:
            print(f"解析失败: {time_str} - {e}")
            print("-" * 50)

async def main():
    """主函数"""
    await test_direct_db_query()
    await test_sage_core_query()
    await parse_time_format()

if __name__ == "__main__":
    asyncio.run(main())