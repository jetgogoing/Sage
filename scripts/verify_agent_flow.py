#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
验证Agent数据流完整性
"""

import asyncio
import os
import sys
import json
import uuid
from datetime import datetime
from pathlib import Path

# 添加项目路径
sys.path.insert(0, str(Path(__file__).parent.parent))

from dotenv import load_dotenv
from sage_core.singleton_manager import get_sage_core
from sage_core import MemoryContent
import asyncpg

async def verify_agent_flow():
    """验证完整的Agent数据流"""
    load_dotenv()
    
    # 初始化Sage Core
    sage_core = await get_sage_core({})
    config = {
        'database': {
            'host': os.getenv('DB_HOST', 'localhost'),
            'port': int(os.getenv('DB_PORT', 5432)),
            'database': os.getenv('DB_NAME', 'sage_memory'),
            'user': os.getenv('DB_USER', 'sage'),
            'password': os.getenv('DB_PASSWORD')
        },
        'embedding': {
            'model': 'Qwen/Qwen3-Embedding-8B',
            'device': 'cpu'
        }
    }
    await sage_core.initialize(config)
    
    # 创建测试数据
    test_id = str(uuid.uuid4())[:8]
    agent_metadata = {
        'agent_name': f'test_agent_{test_id}',
        'task_id': f'task_{test_id}',
        'execution_id': f'exec_{test_id}',
        'quality_score': 98.5,
        'error_count': 0,
        'warning_count': 1,
        'performance_metrics': {
            'execution_time': 2.5,
            'tokens_used': 1200
        }
    }
    
    # 创建并保存Agent报告
    content = MemoryContent(
        user_input=f'/agents test_agent_{test_id}',
        assistant_response=f'=== Report by @test_agent_{test_id} ===\n测试任务完成',
        metadata={
            'session_id': f'test_session_{test_id}',
            'timestamp': datetime.now().isoformat(),
            'is_agent_report': True,
            'agent_name': f'test_agent_{test_id}'
        },
        is_agent_report=True,
        agent_metadata=agent_metadata,
        session_id=f'test_session_{test_id}'
    )
    
    print(f'保存Agent报告...')
    memory_id = await sage_core.save_memory(content)
    print(f'✓ 保存成功，ID: {memory_id}')
    
    # 验证数据库存储
    conn = await asyncpg.connect(**config['database'])
    try:
        # 将UUID转换为字符串
        memory_id_str = str(memory_id) if hasattr(memory_id, 'hex') else memory_id
        
        record = await conn.fetchrow(
            "SELECT * FROM memories WHERE id = $1::uuid",
            memory_id_str
        )
        
        if record:
            print(f'✓ 数据库记录已创建')
            print(f'  - is_agent_report: {record["is_agent_report"]}')
            if record['agent_metadata']:
                metadata = json.loads(record['agent_metadata'])
                print(f'  - agent_name: {metadata.get("agent_name")}')
                print(f'  - quality_score: {metadata.get("quality_score")}')
                print(f'  - task_id: {metadata.get("task_id")}')
            else:
                print('  ✗ agent_metadata为空')
        else:
            print('✗ 未找到数据库记录')
            
        # 测试函数查询
        print('\n测试Agent执行历史函数...')
        results = await conn.fetch(
            "SELECT * FROM get_agent_execution_history($1)",
            f'test_agent_{test_id}'
        )
        
        if results:
            print(f'✓ 找到 {len(results)} 条Agent报告')
            for r in results:
                print(f'  - Task: {r["task_id"]}, Score: {r["quality_score"]}')
        else:
            print('✗ 未找到Agent报告')
            
        # 测试视图查询
        print('\n测试Agent报告统计视图...')
        stats = await conn.fetchrow(
            """
            SELECT * FROM agent_reports_summary 
            WHERE agent_name = $1
            """,
            f'test_agent_{test_id}'
        )
        
        if stats:
            print(f'✓ 视图查询成功')
            print(f'  - Agent: {stats["agent_name"]}')
            print(f'  - Report Count: {stats["report_count"]}')
            print(f'  - Avg Score: {stats["avg_quality_score"]}')
        else:
            print('⚠ 视图中未找到数据（可能需要时间同步）')
            
    finally:
        await conn.close()
    
    await sage_core.cleanup()
    print('\n✓ 验证完成')

if __name__ == "__main__":
    asyncio.run(verify_agent_flow())