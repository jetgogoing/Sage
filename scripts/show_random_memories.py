#!/usr/bin/env python3
"""
随机展示记忆记录的脚本
"""
import asyncio
import asyncpg
import json
import random
from datetime import datetime
import os

async def show_random_memories(count=3):
    conn = await asyncpg.connect(
        host=os.getenv('DB_HOST', 'localhost'),
        port=int(os.getenv('DB_PORT', '5432')),
        user=os.getenv('DB_USER', 'sage'),
        password=os.getenv('DB_PASSWORD', 'sage123'),
        database=os.getenv('DB_NAME', 'sage_memory')
    )
    
    try:
        # 获取所有有价值的记录ID
        valuable_ids = await conn.fetch('''
            SELECT id FROM memories
            WHERE 
                -- 有实质内容
                (LENGTH(user_input) > 50 OR LENGTH(assistant_response) > 50)
                -- 或包含工具调用
                OR metadata->>'tool_calls' IS NOT NULL
                -- 或是工具执行结果
                OR assistant_response LIKE 'Tool execution result:%'
            ORDER BY created_at DESC
        ''')
        
        if not valuable_ids:
            print("没有找到有价值的记录")
            return
        
        # 随机选择指定数量的记录
        selected_ids = random.sample(valuable_ids, min(count, len(valuable_ids)))
        
        print(f"=== 随机展示 {len(selected_ids)} 条完整记录 ===\n")
        
        for i, id_row in enumerate(selected_ids, 1):
            # 获取完整记录
            record = await conn.fetchrow('''
                SELECT id, session_id, user_input, assistant_response, 
                       metadata, created_at, embedding
                FROM memories
                WHERE id = $1
            ''', id_row['id'])
            
            print(f"{'='*80}")
            print(f"记录 {i} / {len(selected_ids)}")
            print(f"{'='*80}")
            print(f"\n📋 基本信息:")
            print(f"  ID: {record['id']}")
            print(f"  会话ID: {record['session_id']}")
            print(f"  创建时间: {record['created_at']}")
            
            print(f"\n💬 用户输入:")
            print("-" * 40)
            if record['user_input']:
                print(record['user_input'])
            else:
                print("(无用户输入)")
            
            print(f"\n🤖 助手回复:")
            print("-" * 40)
            if record['assistant_response']:
                # 如果内容很长，显示前1000个字符
                if len(record['assistant_response']) > 1000:
                    print(record['assistant_response'][:1000])
                    print(f"\n... (省略 {len(record['assistant_response']) - 1000} 字符)")
                else:
                    print(record['assistant_response'])
            else:
                print("(无助手回复)")
            
            print(f"\n📊 元数据:")
            print("-" * 40)
            if record['metadata']:
                metadata = json.loads(record['metadata'])
                print(json.dumps(metadata, indent=2, ensure_ascii=False))
            else:
                print("(无元数据)")
            
            print(f"\n🔢 向量信息:")
            print(f"  向量维度: {len(record['embedding']) if record['embedding'] else '无'}")
            if record['embedding']:
                # 显示向量的前10个元素
                print(f"  向量预览: {record['embedding'][:10]}...")
            
            print(f"\n{'='*80}\n")
        
        # 显示统计信息
        total_count = await conn.fetchval('SELECT COUNT(*) FROM memories')
        valuable_count = len(valuable_ids)
        
        print(f"📈 数据库统计:")
        print(f"  总记录数: {total_count}")
        print(f"  有价值记录数: {valuable_count}")
        print(f"  有价值记录占比: {valuable_count/total_count*100:.1f}%")
        
    finally:
        await conn.close()

if __name__ == '__main__':
    import sys
    count = int(sys.argv[1]) if len(sys.argv) > 1 else 3
    asyncio.run(show_random_memories(count))