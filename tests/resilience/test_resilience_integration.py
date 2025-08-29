#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
弹性机制集成测试 - 验证重试和断路器功能
"""
import asyncio
import pytest
import logging
import time
from unittest.mock import patch, MagicMock
import asyncpg

from sage_core.resilience import (
    retry, circuit_breaker, CircuitBreakerOpenError,
    breaker_manager
)
from sage_core.database.connection import DatabaseConnection
from sage_core.memory.manager import MemoryManager
from sage_core.memory.storage import MemoryStorage
from sage_core.memory.vectorizer import TextVectorizer
from sage_core.interfaces import MemoryContent, SearchOptions

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class TestResilienceIntegration:
    """弹性机制集成测试"""
    
    @pytest.mark.asyncio
    async def test_database_retry_mechanism(self):
        """测试数据库连接重试机制"""
        # 模拟失败的数据库连接
        mock_config = {
            'host': 'localhost',
            'port': 5432,
            'database': 'test',
            'user': 'test',
            'password': 'test'
        }
        
        db_conn = DatabaseConnection(mock_config)
        
        # 模拟前两次失败，第三次成功
        call_count = 0
        
        async def mock_create_pool(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise asyncpg.exceptions.PostgresConnectionError("Connection failed")
            return MagicMock()
        
        with patch('asyncpg.create_pool', side_effect=mock_create_pool):
            # 应该在第三次成功
            await db_conn.connect()
            assert call_count == 3
            logger.info(f"数据库连接在第 {call_count} 次尝试时成功")
    
    @pytest.mark.asyncio
    async def test_circuit_breaker_protection(self):
        """测试断路器保护机制"""
        # 重置所有断路器
        breaker_manager.reset_all()
        
        # 创建一个会持续失败的函数
        failure_count = 0
        
        @circuit_breaker("test_function", failure_threshold=3, recovery_timeout=1)
        async def failing_function():
            nonlocal failure_count
            failure_count += 1
            raise ConnectionError("Simulated failure")
        
        # 测试断路器打开
        for i in range(3):
            try:
                await failing_function()
            except ConnectionError:
                pass
        
        # 第4次调用应该抛出断路器异常
        with pytest.raises(CircuitBreakerOpenError):
            await failing_function()
        
        logger.info(f"断路器在 {failure_count} 次失败后打开")
        
        # 等待恢复时间
        await asyncio.sleep(1.5)
        
        # 测试半开状态
        try:
            await failing_function()
        except ConnectionError:
            pass
        
        # 再次失败后应该立即打开
        with pytest.raises(CircuitBreakerOpenError):
            await failing_function()
    
    @pytest.mark.asyncio
    async def test_memory_save_resilience(self):
        """测试记忆保存的弹性机制"""
        # 创建模拟的依赖
        mock_db = MagicMock()
        mock_vectorizer = MagicMock()
        
        # 创建 MemoryManager
        manager = MemoryManager(mock_db, mock_vectorizer)
        
        # 模拟 storage 的 connect 方法
        async def mock_connect():
            pass
        manager.storage.connect = mock_connect
        
        # 模拟向量化失败然后恢复
        call_count = 0
        
        async def mock_vectorize(text):
            nonlocal call_count
            call_count += 1
            if call_count < 2:
                raise RuntimeError("Vectorization failed")
            return [0.1] * 4096
        
        mock_vectorizer.vectorize = mock_vectorize
        
        async def mock_initialize():
            pass
        mock_vectorizer.initialize = mock_initialize
        
        # 模拟存储操作
        manager.storage = MagicMock()
        
        async def mock_save(**kwargs):
            return "test-id"
        manager.storage.save = mock_save
        
        await manager.initialize()
        
        # 保存应该在重试后成功
        content = MemoryContent(
            user_input="test input",
            assistant_response="test response"
        )
        
        memory_id = await manager.save(content)
        assert memory_id == "test-id"
        assert call_count == 2  # 第一次失败，第二次成功
        logger.info(f"记忆保存在第 {call_count} 次尝试时成功")
    
    @pytest.mark.asyncio
    async def test_cascading_failure_prevention(self):
        """测试级联故障防护"""
        # 重置断路器
        breaker_manager.reset_all()
        
        # 模拟多个相互依赖的服务
        service_a_calls = 0
        service_b_calls = 0
        
        @circuit_breaker("service_a", failure_threshold=2, recovery_timeout=1)
        async def service_a():
            nonlocal service_a_calls
            service_a_calls += 1
            # 调用 service_b
            return await service_b()
        
        @circuit_breaker("service_b", failure_threshold=2, recovery_timeout=1)
        async def service_b():
            nonlocal service_b_calls
            service_b_calls += 1
            raise ConnectionError("Service B is down")
        
        # 测试级联保护
        for i in range(2):
            try:
                await service_a()
            except ConnectionError:
                pass
        
        # service_b 的断路器应该打开
        with pytest.raises(CircuitBreakerOpenError):
            await service_b()
        
        # service_a 仍然可以调用，但会因为 service_b 的断路器而失败
        with pytest.raises(CircuitBreakerOpenError):
            await service_a()
        
        logger.info(f"Service A 调用次数: {service_a_calls}, Service B 调用次数: {service_b_calls}")
        logger.info("级联故障被成功阻止")
    
    @pytest.mark.asyncio
    async def test_performance_under_failures(self):
        """测试失败情况下的性能"""
        # 创建一个偶尔失败的函数
        success_count = 0
        failure_count = 0
        
        @retry(max_attempts=3, initial_delay=0.1)
        async def occasionally_failing_function():
            nonlocal success_count, failure_count
            if asyncio.get_event_loop().time() % 2 < 1:
                failure_count += 1
                raise RuntimeError("Random failure")
            success_count += 1
            return "success"
        
        # 执行多次调用
        start_time = time.time()
        tasks = []
        
        for i in range(10):
            await asyncio.sleep(0.2)  # 分散调用时间
            tasks.append(asyncio.create_task(occasionally_failing_function()))
        
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        end_time = time.time()
        duration = end_time - start_time
        
        # 统计结果
        successful_calls = sum(1 for r in results if r == "success")
        failed_calls = sum(1 for r in results if isinstance(r, Exception))
        
        logger.info(f"执行时间: {duration:.2f}秒")
        logger.info(f"成功调用: {successful_calls}, 失败调用: {failed_calls}")
        logger.info(f"总成功次数: {success_count}, 总失败次数: {failure_count}")
        
        # 即使有失败，整体执行时间应该是可控的
        assert duration < 10  # 假设最多10秒完成
    
    @pytest.mark.asyncio
    async def test_breaker_stats_monitoring(self):
        """测试断路器状态监控"""
        # 重置断路器
        breaker_manager.reset_all()
        
        # 创建测试函数
        @circuit_breaker("monitored_service", failure_threshold=3, recovery_timeout=2)
        async def monitored_service(should_fail=True):
            if should_fail:
                raise RuntimeError("Service error")
            return "success"
        
        # 触发一些失败
        for i in range(3):
            try:
                await monitored_service(should_fail=True)
            except RuntimeError:
                pass
        
        # 获取断路器状态
        stats = monitored_service.breaker.get_stats()
        
        assert stats['name'] == 'monitored_service'
        assert stats['state'] == 'open'
        assert stats['failure_count'] == 3
        
        logger.info(f"断路器状态: {stats}")
        
        # 获取所有断路器的状态
        all_stats = breaker_manager.get_all_stats()
        logger.info(f"所有断路器状态数量: {len(all_stats)}")


if __name__ == "__main__":
    # 运行测试
    async def run_tests():
        test = TestResilienceIntegration()
        
        logger.info("=== 开始弹性机制集成测试 ===")
        
        try:
            logger.info("\n1. 测试数据库重试机制...")
            await test.test_database_retry_mechanism()
            
            logger.info("\n2. 测试断路器保护...")
            await test.test_circuit_breaker_protection()
            
            logger.info("\n3. 测试记忆保存弹性...")
            await test.test_memory_save_resilience()
            
            logger.info("\n4. 测试级联故障防护...")
            await test.test_cascading_failure_prevention()
            
            logger.info("\n5. 测试失败情况下的性能...")
            await test.test_performance_under_failures()
            
            logger.info("\n6. 测试断路器状态监控...")
            await test.test_breaker_stats_monitoring()
            
            logger.info("\n=== 所有测试通过！ ===")
            
        except Exception as e:
            logger.error(f"测试失败: {e}")
            raise
    
    asyncio.run(run_tests())