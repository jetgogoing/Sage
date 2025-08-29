#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
调试Agent元数据保存问题
"""

import asyncio
import json
import os
import sys
import uuid
from datetime import datetime
from pathlib import Path
import logging

# 添加项目路径
sys.path.insert(0, str(Path(__file__).parent.parent))

from sage_core import MemoryContent
from sage_core.singleton_manager import get_sage_core
import asyncpg
from dotenv import load_dotenv

# 配置详细日志
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

async def test_agent_metadata():
    """测试Agent元数据保存"""
    load_dotenv()
    
    # 数据库配置
    db_config = {
        'host': os.getenv('DB_HOST', 'localhost'),
        'port': int(os.getenv('DB_PORT', 5432)),
        'database': os.getenv('DB_NAME', 'sage_memory'),
        'user': os.getenv('DB_USER', 'sage'),
        'password': os.getenv('DB_PASSWORD')
    }
    
    # 测试数据
    test_session_id = f"debug_test_{uuid.uuid4()}"
    test_agent_name = "debug_agent"
    test_task_id = f"task_{uuid.uuid4()}"
    test_execution_id = f"exec_{uuid.uuid4()}"
    
    try:
        # 1. 初始化Sage Core
        print("初始化Sage Core...")
        sage_core = await get_sage_core({})
        config = {
            "database": db_config,
            "embedding": {
                "model": "Qwen/Qwen3-Embedding-8B",
                "device": "cpu"
            }
        }
        await sage_core.initialize(config)
        
        # 2. 准备Agent元数据
        agent_metadata = {
            "agent_name": test_agent_name,
            "task_id": test_task_id,
            "execution_id": test_execution_id,
            "performance_metrics": {
                "execution_time": 3.14,
                "tokens_used": 1500
            },
            "error_count": 0,
            "warning_count": 2,
            "quality_score": 95.5
        }
        
        # 3. 创建MemoryContent
        print("\n创建MemoryContent...")
        content = MemoryContent(
            user_input="/agents debug_agent",
            assistant_response=f"=== Test Report by @{test_agent_name} ===\n任务执行成功",
            metadata={
                "session_id": test_session_id,
                "timestamp": datetime.now().isoformat(),
                "is_agent_report": True,
                "agent_name": test_agent_name
            },
            is_agent_report=True,
            agent_metadata=agent_metadata,
            session_id=test_session_id
        )
        
        print(f"MemoryContent.is_agent_report: {content.is_agent_report}")
        print(f"MemoryContent.agent_metadata: {json.dumps(content.agent_metadata, indent=2)}")
        
        # 4. 保存记忆
        print("\n保存记忆...")
        memory_id = await sage_core.save_memory(content)
        print(f"Memory saved with ID: {memory_id}")
        
        # 5. 查询数据库验证
        print("\n查询数据库验证...")
        conn = await asyncpg.connect(**db_config)
        try:
            # memory_id可能是UUID对象，转换为字符串
            if hasattr(memory_id, 'hex'):
                memory_id_str = str(memory_id)
            else:
                memory_id_str = memory_id
                
            record = await conn.fetchrow(
                """
                SELECT * FROM memories 
                WHERE id = $1::uuid
                """,
                memory_id_str
            )
            
            if record:
                print(f"记录找到！")
                print(f"  - is_agent_report: {record['is_agent_report']}")
                print(f"  - agent_metadata是否为空: {record['agent_metadata'] is None}")
                
                if record['agent_metadata']:
                    agent_meta = json.loads(record['agent_metadata'])
                    print(f"  - agent_metadata内容: {json.dumps(agent_meta, indent=4)}")
                else:
                    print("  - agent_metadata为NULL！这是问题所在。")
                    
                # 也检查metadata字段
                if record['metadata']:
                    meta = json.loads(record['metadata'])
                    print(f"\n  - metadata中的is_agent_report: {meta.get('is_agent_report')}")
                    print(f"  - metadata中的agent_name: {meta.get('agent_name')}")
            else:
                print("记录未找到！")
                
        finally:
            await conn.close()
        
        # 6. 清理
        await sage_core.cleanup()
        
        # 清理测试数据
        conn = await asyncpg.connect(**db_config)
        try:
            await conn.execute(
                "DELETE FROM memories WHERE session_id = $1",
                test_session_id
            )
        finally:
            await conn.close()
        
        print("\n测试完成！")
        
    except Exception as e:
        print(f"\n错误: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_agent_metadata())