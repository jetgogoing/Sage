#!/usr/bin/env python3
"""
事务一致性测试
验证修复后的 MemoryManager 能够确保向量化和数据库保存的原子性
"""
import asyncio
import pytest
import asyncpg
import numpy as np
from unittest.mock import AsyncMock, patch
import sys
import os

# 添加项目根目录到路径
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from sage_core.memory.manager import MemoryManager
from sage_core.memory.storage import MemoryStorage
from sage_core.memory.vectorizer import TextVectorizer
from sage_core.database import DatabaseConnection
from sage_core.database.transaction import TransactionManager
from sage_core.interfaces import MemoryContent


class TestTransactionConsistency:
    """事务一致性测试类"""
    
    @pytest.fixture
    async def mock_setup(self):
        """模拟设置"""
        # 模拟数据库连接
        mock_db = AsyncMock(spec=DatabaseConnection)
        mock_pool = AsyncMock(spec=asyncpg.Pool)
        
        # 模拟向量化器
        mock_vectorizer = AsyncMock(spec=TextVectorizer)
        mock_vectorizer.vectorize.return_value = np.random.randn(4096).astype(np.float32)
        
        # 创建事务管理器
        transaction_manager = TransactionManager(mock_pool)
        
        # 创建存储
        storage = MemoryStorage(mock_db, transaction_manager)
        
        # 创建管理器
        manager = MemoryManager(mock_db, mock_vectorizer, transaction_manager)
        
        return {
            'manager': manager,
            'storage': storage,
            'vectorizer': mock_vectorizer,
            'db': mock_db,
            'pool': mock_pool,
            'transaction_manager': transaction_manager
        }
    
    async def test_transaction_rollback_on_vectorizer_failure(self, mock_setup):
        """测试向量化失败时的事务回滚"""
        setup = await mock_setup
        manager = setup['manager']
        
        # 模拟向量化失败
        setup['vectorizer'].vectorize.side_effect = Exception("向量化失败")
        
        # 模拟事务
        with patch.object(manager.transaction_manager, 'transaction') as mock_transaction:
            mock_conn = AsyncMock()
            mock_transaction.return_value.__aenter__.return_value = mock_conn
            mock_transaction.return_value.__aexit__.return_value = None
            
            content = MemoryContent(
                user_input="测试用户输入",
                assistant_response="测试助手回复",
                session_id="test_session"
            )
            
            # 验证异常被正确抛出
            with pytest.raises(Exception, match="向量化失败"):
                await manager.save(content)
            
            # 验证事务被创建
            mock_transaction.assert_called_once()
            
            # 验证没有调用存储保存（因为向量化失败）
            assert not hasattr(setup['storage'], 'save') or not setup['storage'].save.called
    
    async def test_transaction_rollback_on_storage_failure(self, mock_setup):
        """测试存储失败时的事务回滚"""
        setup = await mock_setup
        manager = setup['manager']
        
        # 模拟存储失败
        with patch.object(setup['storage'], 'save', side_effect=Exception("存储失败")):
            with patch.object(manager.transaction_manager, 'transaction') as mock_transaction:
                mock_conn = AsyncMock()
                mock_transaction.return_value.__aenter__.return_value = mock_conn
                mock_transaction.return_value.__aexit__.return_value = None
                
                content = MemoryContent(
                    user_input="测试用户输入",
                    assistant_response="测试助手回复",
                    session_id="test_session"
                )
                
                # 验证异常被正确抛出
                with pytest.raises(Exception, match="存储失败"):
                    await manager.save(content)
                
                # 验证事务被创建
                mock_transaction.assert_called_once()
    
    async def test_successful_transaction_commit(self, mock_setup):
        """测试成功情况下的事务提交"""
        setup = await mock_setup
        manager = setup['manager']
        
        # 模拟成功的存储
        with patch.object(setup['storage'], 'save', return_value="test_memory_id"):
            with patch.object(manager.transaction_manager, 'transaction') as mock_transaction:
                mock_conn = AsyncMock()
                mock_transaction.return_value.__aenter__.return_value = mock_conn
                mock_transaction.return_value.__aexit__.return_value = None
                
                content = MemoryContent(
                    user_input="测试用户输入",
                    assistant_response="测试助手回复",
                    session_id="test_session"
                )
                
                # 执行保存
                memory_id = await manager.save(content)
                
                # 验证返回正确的ID
                assert memory_id == "test_memory_id"
                
                # 验证事务被创建
                mock_transaction.assert_called_once()
                
                # 验证存储被调用，且传递了事务连接
                setup['storage'].save.assert_called_once()
                call_kwargs = setup['storage'].save.call_args[1]
                assert '_transaction_conn' in call_kwargs
                assert call_kwargs['_transaction_conn'] == mock_conn
    
    async def test_fallback_without_transaction_manager(self, mock_setup):
        """测试没有事务管理器时的降级处理"""
        setup = await mock_setup
        
        # 创建没有事务管理器的管理器
        manager_no_tx = MemoryManager(setup['db'], setup['vectorizer'], None)
        
        # 模拟成功的存储
        with patch.object(manager_no_tx.storage, 'save', return_value="test_memory_id"):
            content = MemoryContent(
                user_input="测试用户输入",
                assistant_response="测试助手回复",
                session_id="test_session"
            )
            
            # 执行保存
            memory_id = await manager_no_tx.save(content)
            
            # 验证返回正确的ID
            assert memory_id == "test_memory_id"
            
            # 验证存储被调用，但没有事务连接
            manager_no_tx.storage.save.assert_called_once()
            call_kwargs = manager_no_tx.storage.save.call_args[1]
            assert '_transaction_conn' not in call_kwargs


async def run_integration_test():
    """集成测试 - 使用真实数据库连接"""
    try:
        # 连接数据库
        pool = await asyncpg.create_pool(
            host=os.getenv("DB_HOST", "localhost"),
            port=int(os.getenv("DB_PORT", "5432")),
            database=os.getenv("DB_NAME", "sage_memory"),
            user=os.getenv("DB_USER", "sage"),
            password=os.getenv("DB_PASSWORD", "sage123"),
            min_size=1,
            max_size=5
        )
        
        # 创建事务管理器
        transaction_manager = TransactionManager(pool)
        
        # 模拟向量化器
        mock_vectorizer = AsyncMock(spec=TextVectorizer)
        mock_vectorizer.vectorize.return_value = np.random.randn(4096).astype(np.float32)
        
        # 创建数据库连接包装器
        class PoolWrapper:
            def __init__(self, pool):
                self.pool = pool
            
            async def fetchval(self, query, *args):
                async with self.pool.acquire() as conn:
                    return await conn.fetchval(query, *args)
            
            async def fetch(self, query, *args):
                async with self.pool.acquire() as conn:
                    return await conn.fetch(query, *args)
            
            async def execute(self, query, *args):
                async with self.pool.acquire() as conn:
                    return await conn.execute(query, *args)
            
            async def connect(self):
                pass
            
            async def disconnect(self):
                pass
        
        db_wrapper = PoolWrapper(pool)
        
        # 创建存储和管理器
        storage = MemoryStorage(db_wrapper, transaction_manager)
        manager = MemoryManager(db_wrapper, mock_vectorizer, transaction_manager)
        
        print("开始集成测试...")
        
        # 测试1：正常保存
        content = MemoryContent(
            user_input="集成测试用户输入",
            assistant_response="集成测试助手回复",
            session_id="integration_test_session",
            metadata={"test": "integration"}
        )
        
        memory_id = await manager.save(content)
        print(f"✓ 正常保存测试通过，memory_id: {memory_id}")
        
        # 测试2：模拟向量化失败
        original_vectorize = mock_vectorizer.vectorize
        mock_vectorizer.vectorize = AsyncMock(side_effect=Exception("模拟向量化失败"))
        
        try:
            await manager.save(content)
            print("✗ 向量化失败测试未通过 - 应该抛出异常")
        except Exception as e:
            print(f"✓ 向量化失败测试通过，异常: {e}")
        
        # 恢复向量化器
        mock_vectorizer.vectorize = original_vectorize
        
        # 测试3：验证数据一致性
        # 查询刚才保存的记录
        async with pool.acquire() as conn:
            result = await conn.fetchrow(
                "SELECT * FROM memories WHERE id = $1", 
                memory_id
            )
            if result:
                print("✓ 数据一致性测试通过 - 记录已正确保存")
            else:
                print("✗ 数据一致性测试失败 - 记录未找到")
        
        print("集成测试完成!")
        
    except Exception as e:
        print(f"集成测试失败: {e}")
        import traceback
        traceback.print_exc()
    finally:
        if 'pool' in locals():
            await pool.close()


if __name__ == "__main__":
    # 运行集成测试
    asyncio.run(run_integration_test())