#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
执行数据库迁移
"""

import asyncio
import os
import asyncpg
from pathlib import Path
from dotenv import load_dotenv

async def run_migration():
    """执行数据库迁移"""
    load_dotenv()
    
    # 数据库配置
    db_config = {
        'host': os.getenv('DB_HOST', 'localhost'),
        'port': int(os.getenv('DB_PORT', 5432)),
        'database': os.getenv('DB_NAME', 'sage_memory'),
        'user': os.getenv('DB_USER', 'sage'),
        'password': os.getenv('DB_PASSWORD')
    }
    
    # 读取迁移脚本
    migration_file = Path(__file__).parent / 'database_migration_agent_metadata.sql'
    with open(migration_file, 'r', encoding='utf-8') as f:
        migration_sql = f.read()
    
    # 连接数据库并执行
    conn = await asyncpg.connect(**db_config)
    try:
        print("开始执行数据库迁移...")
        
        # 分割SQL语句并逐个执行
        statements = migration_sql.split(';')
        for statement in statements:
            statement = statement.strip()
            if statement:
                try:
                    await conn.execute(statement)
                    print(f"✓ 执行成功: {statement[:50]}...")
                except asyncpg.exceptions.DuplicateColumnError as e:
                    print(f"⚠ 列已存在，跳过: {e}")
                except asyncpg.exceptions.DuplicateTableError as e:
                    print(f"⚠ 表/视图已存在，跳过: {e}")
                except asyncpg.exceptions.DuplicateFunctionError as e:
                    print(f"⚠ 函数已存在，跳过: {e}")
                except asyncpg.exceptions.DuplicateObjectError as e:
                    print(f"⚠ 对象已存在，跳过: {e}")
                except Exception as e:
                    print(f"✗ 执行失败: {e}")
                    print(f"  语句: {statement[:100]}...")
        
        print("\n数据库迁移完成！")
        
    finally:
        await conn.close()

if __name__ == "__main__":
    asyncio.run(run_migration())