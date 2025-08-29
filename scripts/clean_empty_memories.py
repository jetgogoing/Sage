#!/usr/bin/env python3
"""
安全清理空记忆记录脚本
- 备份数据
- 预览将要删除的记录
- 确认后执行删除
"""
import asyncio
import asyncpg
import json
from datetime import datetime
import sys
import os

async def clean_empty_memories(dry_run=True, skip_confirmation=False):
    conn = await asyncpg.connect(
        host=os.getenv('DB_HOST', 'localhost'),
        port=int(os.getenv('DB_PORT', '5432')),
        user=os.getenv('DB_USER', 'sage'),
        password=os.getenv('DB_PASSWORD', 'sage123'),
        database=os.getenv('DB_NAME', 'sage_memory')
    )
    
    try:
        print(f'=== 清理空记忆记录 {"(预览模式)" if dry_run else "(执行模式)"} ===\n')
        
        # 1. 备份提醒
        if not dry_run:
            print('⚠️  警告：即将删除数据！请确保已备份数据库。')
            print('备份命令: docker exec sage-postgres pg_dump -U sage sage_memory > backup.sql')
            if not skip_confirmation:
                confirm = input('\n确认已备份？(yes/no): ')
                if confirm.lower() != 'yes':
                    print('已取消操作')
                    return
            else:
                print('\n跳过确认步骤（--yes参数）')
        
        # 2. 识别垃圾记录
        print('\n识别垃圾记录...')
        
        # 定义垃圾记录的SQL条件
        garbage_query = '''
            SELECT id, user_input, assistant_response, metadata, created_at
            FROM memories
            WHERE 
                -- 条件1: 双空记录
                (user_input = '' AND assistant_response = '')
                
                -- 条件2: 空用户输入 + 无价值的短助手回复（排除工具结果）
                OR (user_input = '' 
                    AND assistant_response != ''
                    AND assistant_response NOT LIKE 'Tool execution result:%'
                    AND LENGTH(assistant_response) < 50
                    AND (metadata IS NULL 
                         OR (metadata->>'tool_calls' IS NULL 
                             AND metadata->>'session_id' IS NULL)))
                
                -- 条件3: 空助手回复 + 无价值的短用户输入
                OR (assistant_response = '' 
                    AND user_input != ''
                    AND LENGTH(user_input) < 50
                    AND (metadata IS NULL 
                         OR (metadata->>'tool_calls' IS NULL 
                             AND metadata->>'session_id' IS NULL)))
                
                -- 条件4: 测试记录（metadata中包含test字段）
                OR (metadata->>'test' IS NOT NULL)
        '''
        
        garbage_records = await conn.fetch(garbage_query)
        
        print(f'\n找到 {len(garbage_records)} 条垃圾记录')
        
        # 3. 显示将删除的记录
        if len(garbage_records) > 0:
            print('\n将删除的记录预览:')
            print('-' * 80)
            
            for i, row in enumerate(garbage_records[:10], 1):  # 只显示前10条
                print(f'\n记录 {i} (ID: {row["id"]}):')
                print(f'  用户输入: "{row["user_input"][:50]}{"..." if len(row["user_input"]) > 50 else ""}"')
                print(f'  助手回复: "{row["assistant_response"][:50]}{"..." if len(row["assistant_response"]) > 50 else ""}"')
                
                if row["metadata"]:
                    metadata = json.loads(row["metadata"])
                    print(f'  元数据: {list(metadata.keys())[:5]}{"..." if len(metadata.keys()) > 5 else ""}')
                print(f'  创建时间: {row["created_at"]}')
            
            if len(garbage_records) > 10:
                print(f'\n... 还有 {len(garbage_records) - 10} 条记录未显示')
            
            print('-' * 80)
        
        # 4. 统计将保留的有价值记录
        valuable_count = await conn.fetchval('''
            SELECT COUNT(*) FROM memories
            WHERE 
                -- 有实质内容
                (LENGTH(user_input) > 50 OR LENGTH(assistant_response) > 50)
                -- 或包含工具调用
                OR metadata->>'tool_calls' IS NOT NULL
                -- 或是工具执行结果
                OR assistant_response LIKE 'Tool execution result:%'
        ''')
        
        total_count = await conn.fetchval('SELECT COUNT(*) FROM memories')
        
        print(f'\n统计信息:')
        print(f'  总记录数: {total_count}')
        print(f'  将删除: {len(garbage_records)} ({len(garbage_records)/total_count*100:.1f}%)')
        print(f'  将保留: {total_count - len(garbage_records)} ({(total_count - len(garbage_records))/total_count*100:.1f}%)')
        print(f'  有价值记录: {valuable_count}')
        
        # 5. 执行删除
        if not dry_run and len(garbage_records) > 0:
            print('\n执行删除操作...')
            
            # 开始事务
            async with conn.transaction():
                # 批量删除，每批100条
                batch_size = 100
                deleted_total = 0
                
                for i in range(0, len(garbage_records), batch_size):
                    batch = garbage_records[i:i+batch_size]
                    ids = [record['id'] for record in batch]
                    
                    deleted = await conn.execute('''
                        DELETE FROM memories 
                        WHERE id = ANY($1::uuid[])
                    ''', ids)
                    
                    deleted_count = int(deleted.split()[-1])
                    deleted_total += deleted_count
                    print(f'  已删除 {deleted_total}/{len(garbage_records)} 条记录...')
            
            print(f'\n✅ 成功删除 {deleted_total} 条垃圾记录')
            
            # 验证删除结果
            new_total = await conn.fetchval('SELECT COUNT(*) FROM memories')
            print(f'\n删除后总记录数: {new_total}')
            
        elif dry_run and len(garbage_records) > 0:
            print('\n💡 提示：这是预览模式。要执行删除，请运行:')
            print('   python clean_empty_memories.py --execute')
            
    finally:
        await conn.close()

if __name__ == '__main__':
    # 检查命令行参数
    dry_run = '--execute' not in sys.argv
    skip_confirmation = '--yes' in sys.argv
    
    # 修改函数调用，传递skip_confirmation参数
    asyncio.run(clean_empty_memories(dry_run, skip_confirmation))