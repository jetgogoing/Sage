#!/usr/bin/env python3
"""
完整测试时区转换闭环
"""

from datetime import datetime, timezone
import asyncpg
import asyncio
import os

async def test_complete_flow():
    """测试完整的时区转换流程"""
    db_url = os.getenv('DATABASE_URL', 'postgresql://sage:sage123@localhost:5432/sage_memory')
    conn = await asyncpg.connect(db_url)
    
    try:
        # 1. 查看现有数据的时间格式
        print("=== 1. 查看现有数据 ===")
        rows = await conn.fetch("""
            SELECT id, created_at, 
                   created_at::text as text_format,
                   extract(timezone from created_at) as tz_offset
            FROM memories 
            ORDER BY created_at DESC 
            LIMIT 2
        """)
        
        for row in rows:
            print(f"ID: {str(row['id'])[:8]}...")
            print(f"created_at (Python): {row['created_at']}")
            print(f"created_at (SQL text): {row['text_format']}")
            print(f"Timezone offset (seconds): {row['tz_offset']}")
            
            # 测试 astimezone()
            py_time = row['created_at']
            local_time = py_time.astimezone()
            print(f"After astimezone(): {local_time}")
            print(f"ISO format: {local_time.isoformat()}")
            print("-" * 50)
        
        # 2. 写入新数据并立即读取
        print("\n=== 2. 写入新数据测试 ===")
        result = await conn.fetchrow("""
            INSERT INTO memories (session_id, user_input, assistant_response, embedding)
            VALUES ('test-tz', '时区测试', '测试响应', ARRAY[0.1]::vector)
            RETURNING id, created_at, created_at::text as text_format
        """)
        
        print(f"新插入数据 ID: {result['id']}")
        print(f"created_at (Python): {result['created_at']}")
        print(f"created_at (SQL text): {result['text_format']}")
        print(f"After astimezone(): {result['created_at'].astimezone()}")
        print(f"ISO format: {result['created_at'].astimezone().isoformat()}")
        
        # 3. 测试不同时区的时间戳
        print("\n=== 3. 时区转换测试 ===")
        # UTC 时间
        utc_time = datetime.now(timezone.utc)
        print(f"UTC time: {utc_time}")
        print(f"astimezone(): {utc_time.astimezone()}")
        
        # CST 时间 (+08:00)
        cst_time = datetime.now().astimezone()
        print(f"\nCST time: {cst_time}")
        print(f"astimezone() again: {cst_time.astimezone()}")
        
        # 清理测试数据
        await conn.execute("DELETE FROM memories WHERE id = $1", result['id'])
        
    finally:
        await conn.close()

async def main():
    await test_complete_flow()

if __name__ == "__main__":
    asyncio.run(main())