#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Database Transaction Manager - 数据库事务管理
确保记忆保存操作的原子性和一致性
"""
import asyncio
import logging
from typing import Optional, TypeVar, Callable, Any
from contextlib import asynccontextmanager
import asyncpg
from functools import wraps

logger = logging.getLogger(__name__)

T = TypeVar('T')


class TransactionManager:
    """数据库事务管理器"""
    
    def __init__(self, connection_pool: asyncpg.Pool):
        """
        初始化事务管理器
        
        Args:
            connection_pool: asyncpg连接池
        """
        self.pool = connection_pool
        self._active_transactions = set()
        self._lock = asyncio.Lock()
    
    @asynccontextmanager
    async def transaction(self, isolation_level: str = 'read_committed'):
        """
        创建事务上下文
        
        Args:
            isolation_level: 事务隔离级别
                - 'read_uncommitted'
                - 'read_committed' (默认)
                - 'repeatable_read'
                - 'serializable'
                
        Yields:
            事务连接对象
        """
        conn = None
        trans = None
        trans_id = id(asyncio.current_task())
        
        try:
            # 获取连接
            conn = await self.pool.acquire()
            
            # 开始事务
            trans = conn.transaction(isolation=isolation_level)
            await trans.start()
            
            # 记录活跃事务
            async with self._lock:
                self._active_transactions.add(trans_id)
            
            logger.debug(f"事务开始 (ID: {trans_id}, 隔离级别: {isolation_level})")
            
            yield conn
            
            # 提交事务
            await trans.commit()
            logger.debug(f"事务提交成功 (ID: {trans_id})")
            
        except Exception as e:
            # 回滚事务
            if trans:
                try:
                    await trans.rollback()
                    logger.warning(f"事务回滚 (ID: {trans_id}): {e}")
                except Exception as rollback_error:
                    logger.error(f"事务回滚失败 (ID: {trans_id}): {rollback_error}")
            raise
            
        finally:
            # 清理资源
            async with self._lock:
                self._active_transactions.discard(trans_id)
            
            if conn:
                await self.pool.release(conn)
    
    async def execute_in_transaction(self, func: Callable, *args, **kwargs):
        """
        在事务中执行函数
        
        Args:
            func: 要执行的异步函数
            *args: 函数参数
            **kwargs: 函数关键字参数
            
        Returns:
            函数执行结果
        """
        async with self.transaction() as conn:
            # 将连接注入到kwargs中
            kwargs['_transaction_conn'] = conn
            return await func(*args, **kwargs)
    
    def transactional(self, isolation_level: str = 'read_committed'):
        """
        事务装饰器
        
        使用示例：
            @transaction_manager.transactional()
            async def save_with_transaction(data):
                # 函数内的所有数据库操作都在同一个事务中
                await db.execute(...)
                await db.execute(...)
        """
        def decorator(func):
            @wraps(func)
            async def wrapper(*args, **kwargs):
                # 检查是否已在事务中
                if '_transaction_conn' in kwargs:
                    # 已在事务中，直接执行
                    return await func(*args, **kwargs)
                
                # 创建新事务
                async with self.transaction(isolation_level) as conn:
                    kwargs['_transaction_conn'] = conn
                    return await func(*args, **kwargs)
            
            return wrapper
        return decorator
    
    async def get_active_transaction_count(self) -> int:
        """获取活跃事务数量"""
        async with self._lock:
            return len(self._active_transactions)
    
    async def wait_for_all_transactions(self, timeout: float = 30.0):
        """
        等待所有事务完成
        
        Args:
            timeout: 超时时间（秒）
        """
        start_time = asyncio.get_event_loop().time()
        
        while True:
            count = await self.get_active_transaction_count()
            if count == 0:
                logger.info("所有事务已完成")
                return
            
            if asyncio.get_event_loop().time() - start_time > timeout:
                logger.warning(f"等待事务超时，仍有 {count} 个活跃事务")
                raise TimeoutError(f"等待事务完成超时，活跃事务数: {count}")
            
            logger.debug(f"等待 {count} 个事务完成...")
            await asyncio.sleep(0.1)


class TransactionalStorage:
    """支持事务的存储基类"""
    
    def __init__(self, transaction_manager: TransactionManager):
        """
        初始化事务存储
        
        Args:
            transaction_manager: 事务管理器
        """
        self.transaction_manager = transaction_manager
    
    async def _get_connection(self, **kwargs) -> asyncpg.Connection:
        """
        获取数据库连接
        
        如果在事务中，使用事务连接；否则从连接池获取
        """
        if '_transaction_conn' in kwargs:
            return kwargs['_transaction_conn']
        
        # 如果不在事务中，从池中获取连接
        return await self.transaction_manager.pool.acquire()
    
    async def _release_connection(self, conn: asyncpg.Connection, **kwargs):
        """
        释放数据库连接
        
        如果不在事务中，将连接返回池
        """
        if '_transaction_conn' not in kwargs:
            await self.transaction_manager.pool.release(conn)


# 使用示例
if __name__ == "__main__":
    async def test_transaction_manager():
        """测试事务管理器"""
        # 模拟连接池
        import os
        
        pool = await asyncpg.create_pool(
            host=os.getenv("DB_HOST", "localhost"),
            port=int(os.getenv("DB_PORT", "5432")),
            database=os.getenv("DB_NAME", "sage_memory"),
            user=os.getenv("DB_USER", "sage"),
            password=os.getenv("DB_PASSWORD", "sage123")
        )
        
        # 创建事务管理器
        tm = TransactionManager(pool)
        
        # 测试基本事务
        async with tm.transaction() as conn:
            # 在事务中执行操作
            await conn.execute("SELECT 1")
            print("事务测试成功")
        
        # 测试事务回滚
        try:
            async with tm.transaction() as conn:
                await conn.execute("SELECT 1")
                raise Exception("模拟错误")
        except Exception as e:
            print(f"事务回滚测试成功: {e}")
        
        # 测试装饰器
        @tm.transactional()
        async def test_function(**kwargs):
            conn = kwargs.get('_transaction_conn')
            result = await conn.fetchval("SELECT 1")
            return result
        
        result = await test_function()
        print(f"装饰器测试成功: {result}")
        
        # 清理
        await pool.close()
    
    # 运行测试
    logging.basicConfig(level=logging.DEBUG)
    asyncio.run(test_transaction_manager())