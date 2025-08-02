#!/usr/bin/env python3
import asyncio
import asyncpg
import json

async def analyze_empty_memories():
    conn = await asyncpg.connect(
        host='localhost',
        port=5432,
        user='sage',
        password='sage123',
        database='sage_memory'
    )
    
    try:
        print('=== 分析空记忆记录 ===\n')
        
        # 1. 统计总记录数
        total = await conn.fetchval('SELECT COUNT(*) FROM memories')
        print(f'总记录数: {total}')
        
        # 2. 统计各种空记录情况
        stats = []
        
        # 完全空记录
        empty_both = await conn.fetchval('''
            SELECT COUNT(*) FROM memories 
            WHERE user_input = '' AND assistant_response = ''
        ''')
        stats.append(('双空记录', empty_both))
        
        # 只有用户输入空
        empty_user = await conn.fetchval('''
            SELECT COUNT(*) FROM memories 
            WHERE user_input = '' AND assistant_response != ''
        ''')
        stats.append(('空用户输入', empty_user))
        
        # 只有助手回复空
        empty_assistant = await conn.fetchval('''
            SELECT COUNT(*) FROM memories 
            WHERE user_input != '' AND assistant_response = ''
        ''')
        stats.append(('空助手回复', empty_assistant))
        
        # 工具执行结果记录
        tool_results = await conn.fetchval('''
            SELECT COUNT(*) FROM memories 
            WHERE user_input = '' 
            AND assistant_response LIKE 'Tool execution result:%'
        ''')
        stats.append(('工具执行结果', tool_results))
        
        print('\n空记录类型分布:')
        for name, count in stats:
            percentage = (count / total * 100) if total > 0 else 0
            print(f'  {name}: {count} ({percentage:.1f}%)')
        
        # 3. 查看空记录的metadata特征
        print('\n空记录的元数据特征:')
        
        # 含有tool_calls的空记录
        with_tools = await conn.fetchval('''
            SELECT COUNT(*) FROM memories 
            WHERE (user_input = '' OR assistant_response = '')
            AND metadata->'tool_calls' IS NOT NULL
        ''')
        print(f'  含工具调用元数据: {with_tools}')
        
        # 含有content_hash的空记录
        with_hash = await conn.fetchval('''
            SELECT COUNT(*) FROM memories 
            WHERE (user_input = '' OR assistant_response = '')
            AND metadata->>'content_hash' IS NOT NULL
        ''')
        print(f'  含content_hash: {with_hash}')
        
        # 4. 查看一些空记录示例
        print('\n空记录示例:')
        samples = await conn.fetch('''
            SELECT id, user_input, assistant_response, 
                   metadata, created_at
            FROM memories
            WHERE user_input = '' OR assistant_response = ''
            ORDER BY created_at DESC
            LIMIT 5
        ''')
        
        for i, row in enumerate(samples, 1):
            print(f'\n示例 {i} (ID: {row["id"]}):')
            print(f'  用户输入: "{row["user_input"]}"')
            resp = row["assistant_response"]
            if len(resp) > 100:
                print(f'  助手回复: "{resp[:100]}..."')
            else:
                print(f'  助手回复: "{resp}"')
            if row["metadata"]:
                metadata = json.loads(row["metadata"])
                print(f'  元数据字段: {list(metadata.keys())}')
                if 'tool_calls' in metadata:
                    print(f'  工具调用数: {len(metadata["tool_calls"])}')
            print(f'  创建时间: {row["created_at"]}')
        
        # 5. 识别真正的垃圾记录
        print('\n\n=== 垃圾记录识别 ===')
        
        # 查找可能的垃圾记录
        garbage_candidates = await conn.fetch('''
            SELECT id, user_input, assistant_response, metadata
            FROM memories
            WHERE (user_input = '' AND assistant_response = '')
               OR (user_input = '' AND assistant_response NOT LIKE '%Tool execution result:%' 
                   AND LENGTH(assistant_response) < 50)
               OR (assistant_response = '' AND LENGTH(user_input) < 50)
            LIMIT 20
        ''')
        
        print(f'\n发现 {len(garbage_candidates)} 条可疑垃圾记录')
        
        # 分析垃圾记录特征
        garbage_count = 0
        for row in garbage_candidates:
            metadata = json.loads(row["metadata"]) if row["metadata"] else {}
            # 如果没有有价值的元数据，且内容也空或很短
            if (not metadata.get('tool_calls') and 
                not metadata.get('session_id') and
                len(row["user_input"]) < 20 and 
                len(row["assistant_response"]) < 20):
                garbage_count += 1
                
        print(f'确认垃圾记录数: {garbage_count}')
        
        # 6. 生成清理建议
        print('\n=== 清理建议 ===')
        print('建议删除的记录类型:')
        print('1. 双空记录（user_input和assistant_response都为空）')
        print('2. 无有价值元数据的短内容记录')
        print('\n建议保留的记录:')
        print('1. 包含tool_calls的记录（即使内容为空）')
        print('2. 包含完整session_id的记录')
        print('3. Tool execution result开头的记录')
        
    finally:
        await conn.close()

if __name__ == '__main__':
    asyncio.run(analyze_empty_memories())