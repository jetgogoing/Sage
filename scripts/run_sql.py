#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
执行SQL脚本
"""

import asyncio
import os
import sys
import asyncpg
from pathlib import Path
from dotenv import load_dotenv

async def run_sql(sql_file):
    """执行SQL脚本"""
    load_dotenv()
    
    # 数据库配置
    db_config = {
        'host': os.getenv('DB_HOST', 'localhost'),
        'port': int(os.getenv('DB_PORT', 5432)),
        'database': os.getenv('DB_NAME', 'sage_memory'),
        'user': os.getenv('DB_USER', 'sage'),
        'password': os.getenv('DB_PASSWORD')
    }
    
    # 读取SQL脚本
    with open(sql_file, 'r', encoding='utf-8') as f:
        sql_content = f.read()
    
    # 连接数据库并执行
    conn = await asyncpg.connect(**db_config)
    try:
        print(f"执行SQL脚本: {sql_file}")
        
        # 执行整个脚本
        result = await conn.execute(sql_content)
        print(f"✓ 执行成功: {result}")
        
        # 验证函数是否存在
        check_func = await conn.fetchval("""
            SELECT COUNT(*) FROM pg_proc 
            WHERE proname = 'get_agent_execution_history'
        """)
        print(f"✓ 函数get_agent_execution_history存在: {check_func > 0}")
        
        check_trigger = await conn.fetchval("""
            SELECT COUNT(*) FROM pg_trigger 
            WHERE tgname = 'trg_auto_detect_agent_report'
        """)
        print(f"✓ 触发器trg_auto_detect_agent_report存在: {check_trigger > 0}")
        
    except Exception as e:
        print(f"✗ 执行失败: {e}")
        import traceback
        traceback.print_exc()
    finally:
        await conn.close()

if __name__ == "__main__":
    if len(sys.argv) < 2:
        sql_file = 'scripts/fix_agent_functions.sql'
    else:
        sql_file = sys.argv[1]
    
    asyncio.run(run_sql(sql_file))