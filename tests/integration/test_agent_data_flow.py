#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
集成测试：Agent数据流完整性验证
验证从hooks捕获到数据库存储的完整链路
"""

import asyncio
import json
import os
import sys
import tempfile
import uuid
from datetime import datetime
from pathlib import Path
from typing import Dict, Any

import pytest
import pytest_asyncio
import asyncpg
from dotenv import load_dotenv

# 添加项目路径
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from sage_core import MemoryContent
from sage_core.singleton_manager import get_sage_core
from sage_mcp_stdio_single import SageMCPStdioServerV3


class TestAgentDataFlow:
    """Agent数据流集成测试"""
    
    @pytest_asyncio.fixture(autouse=True)
    async def setup(self):
        """测试准备"""
        load_dotenv()
        
        # 数据库配置
        self.db_config = {
            'host': os.getenv('DB_HOST', 'localhost'),
            'port': int(os.getenv('DB_PORT', 5432)),
            'database': os.getenv('DB_NAME', 'sage_memory'),
            'user': os.getenv('DB_USER', 'sage'),
            'password': os.getenv('DB_PASSWORD')
        }
        
        # 测试数据
        self.test_session_id = f"test_agent_{uuid.uuid4()}"
        self.test_agent_name = "test_agent"
        self.test_task_id = f"task_{uuid.uuid4()}"
        self.test_execution_id = f"exec_{uuid.uuid4()}"
        
        yield
        
        # 清理测试数据
        await self.cleanup_test_data()
    
    async def cleanup_test_data(self):
        """清理测试数据"""
        conn = await asyncpg.connect(**self.db_config)
        try:
            await conn.execute(
                "DELETE FROM memories WHERE session_id = $1",
                self.test_session_id
            )
        finally:
            await conn.close()
    
    @pytest.mark.asyncio
    async def test_agent_metadata_save_via_mcp(self):
        """测试通过MCP保存Agent元数据"""
        # 1. 初始化MCP服务器
        server = SageMCPStdioServerV3()
        server.sage_core = await get_sage_core({})
        
        # 初始化配置
        config = {
            "database": self.db_config,
            "embedding": {
                "model": "Qwen/Qwen3-Embedding-8B",
                "device": "cpu"
            }
        }
        await server.sage_core.initialize(config)
        
        # 2. 准备Agent报告数据
        agent_metadata = {
            "agent_name": self.test_agent_name,
            "task_id": self.test_task_id,
            "execution_id": self.test_execution_id,
            "performance_metrics": {
                "execution_time": 3.14,
                "tokens_used": 1500
            },
            "error_count": 0,
            "warning_count": 2,
            "quality_score": 95.5
        }
        
        # 3. 直接调用Sage Core保存（模拟MCP调用）
        content = MemoryContent(
            user_input="/agents test_agent",
            assistant_response=f"=== Test Report by @{self.test_agent_name} ===\n任务执行成功",
            metadata={
                "session_id": self.test_session_id,
                "timestamp": datetime.now().isoformat(),
                "is_agent_report": True,
                "agent_name": self.test_agent_name,
                "agent_task_id": self.test_task_id,
                "agent_execution_id": self.test_execution_id
            },
            is_agent_report=True,
            agent_metadata=agent_metadata,
            session_id=self.test_session_id
        )
        
        # 打印MemoryContent内容以验证
        print(f"MemoryContent.is_agent_report: {content.is_agent_report}")
        print(f"MemoryContent.agent_metadata: {content.agent_metadata}")
        
        memory_id = await server.sage_core.save_memory(content)
        
        # 验证保存成功
        assert memory_id is not None
        print(f"Memory saved with ID: {memory_id}")
        
        # 4. 直接查询数据库验证
        conn = await asyncpg.connect(**self.db_config)
        try:
            # 查询保存的记录
            record = await conn.fetchrow(
                """
                SELECT * FROM memories 
                WHERE session_id = $1 
                  AND is_agent_report = TRUE
                ORDER BY created_at DESC
                LIMIT 1
                """,
                self.test_session_id
            )
            
            assert record is not None
            assert record['is_agent_report'] is True
            assert record['agent_metadata'] is not None
            
            # 验证agent_metadata内容
            saved_metadata = json.loads(record['agent_metadata'])
            assert saved_metadata['agent_name'] == self.test_agent_name
            assert saved_metadata['task_id'] == self.test_task_id
            assert saved_metadata['execution_id'] == self.test_execution_id
            assert saved_metadata['quality_score'] == 95.5
            
            # 验证通用metadata中的向后兼容字段
            general_metadata = json.loads(record['metadata'])
            assert general_metadata['is_agent_report'] is True
            assert general_metadata['agent_name'] == self.test_agent_name
            
        finally:
            await conn.close()
        
        # 清理
        await server.cleanup()
    
    @pytest.mark.asyncio
    async def test_agent_report_retrieval(self):
        """测试Agent报告检索"""
        # 1. 先保存一个Agent报告
        sage_core = await get_sage_core({})
        config = {
            "database": self.db_config,
            "embedding": {
                "model": "Qwen/Qwen3-Embedding-8B",
                "device": "cpu"
            }
        }
        await sage_core.initialize(config)
        
        # 保存Agent报告
        content = MemoryContent(
            user_input="/agents code_reviewer",
            assistant_response="=== Code Review Report by @code_reviewer ===\n代码审查完成",
            metadata={
                "session_id": self.test_session_id,
                "is_agent_report": True,
                "agent_name": "code_reviewer"
            },
            is_agent_report=True,
            agent_metadata={
                "agent_name": "code_reviewer",
                "task_id": self.test_task_id,
                "quality_score": 90.0
            }
        )
        
        memory_id = await sage_core.save_memory(content)
        assert memory_id is not None
        
        # 2. 通过数据库函数检索
        conn = await asyncpg.connect(**self.db_config)
        try:
            # 使用get_agent_execution_history函数
            records = await conn.fetch(
                "SELECT * FROM get_agent_execution_history($1)",
                "code_reviewer"
            )
            
            assert len(records) > 0
            found = False
            for record in records:
                if record['task_id'] == self.test_task_id:
                    found = True
                    assert record['agent_name'] == 'code_reviewer'
                    assert record['quality_score'] == 90.0
                    break
            
            assert found, "未找到测试的Agent报告"
            
            # 3. 使用视图查询统计
            stats = await conn.fetchrow(
                """
                SELECT * FROM agent_reports_summary 
                WHERE agent_name = 'code_reviewer'
                """
            )
            
            if stats:
                assert stats['agent_name'] == 'code_reviewer'
                assert stats['report_count'] >= 1
                
        finally:
            await conn.close()
        
        await sage_core.cleanup()
    
    @pytest.mark.asyncio
    async def test_backward_compatibility(self):
        """测试向后兼容性"""
        sage_core = await get_sage_core({})
        config = {
            "database": self.db_config,
            "embedding": {
                "model": "Qwen/Qwen3-Embedding-8B",
                "device": "cpu"
            }
        }
        await sage_core.initialize(config)
        
        # 1. 保存普通对话（非Agent报告）
        normal_content = MemoryContent(
            user_input="什么是Python？",
            assistant_response="Python是一种高级编程语言",
            metadata={
                "session_id": self.test_session_id,
                "message_count": 1
            }
        )
        
        normal_id = await sage_core.save_memory(normal_content)
        assert normal_id is not None
        
        # 2. 验证普通对话未被标记为Agent报告
        conn = await asyncpg.connect(**self.db_config)
        try:
            # normal_id可能是UUID对象，转换为字符串
            if hasattr(normal_id, 'hex'):
                normal_id_str = str(normal_id)
            else:
                normal_id_str = normal_id
                
            record = await conn.fetchrow(
                "SELECT * FROM memories WHERE id = $1::uuid",
                normal_id_str
            )
            
            assert record is not None
            assert record['is_agent_report'] is False
            assert record['agent_metadata'] is None
            
        finally:
            await conn.close()
        
        await sage_core.cleanup()
    
    @pytest.mark.asyncio
    async def test_agent_metadata_indexing(self):
        """测试Agent元数据索引性能"""
        conn = await asyncpg.connect(**self.db_config)
        try:
            # 验证索引存在
            indexes = await conn.fetch(
                """
                SELECT indexname FROM pg_indexes 
                WHERE tablename = 'memories' 
                  AND indexname LIKE 'idx_memories_%agent%'
                """
            )
            
            expected_indexes = [
                'idx_memories_is_agent_report',
                'idx_memories_agent_metadata',
                'idx_memories_agent_name'
            ]
            
            index_names = [idx['indexname'] for idx in indexes]
            for expected in expected_indexes:
                assert expected in index_names, f"缺少索引: {expected}"
            
            # 执行查询计划分析
            plan = await conn.fetch(
                """
                EXPLAIN (FORMAT JSON) 
                SELECT * FROM memories 
                WHERE is_agent_report = TRUE 
                  AND agent_metadata->>'agent_name' = 'test'
                """
            )
            
            # 验证使用了索引
            plan_json = json.loads(plan[0]['QUERY PLAN'])
            plan_text = json.dumps(plan_json, indent=2)
            
            # 检查是否使用了索引扫描
            assert 'Index Scan' in plan_text or 'Bitmap Index Scan' in plan_text
            
        finally:
            await conn.close()


if __name__ == "__main__":
    # 运行测试
    pytest.main([__file__, "-v", "-s"])