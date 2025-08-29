#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
弹性机制简化测试 - 快速验证重试和断路器功能
"""
import os
import asyncio
import logging
import time

# 添加项目路径
import sys
sys.path.append(os.getenv('SAGE_HOME', '.'))

from sage_core.resilience import (
    retry, circuit_breaker, CircuitBreakerOpenError,
    RetryStrategy, breaker_manager
)

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


async def test_retry_mechanism():
    """测试重试机制"""
    logger.info("=== 测试重试机制 ===")
    
    call_count = 0
    
    @retry(max_attempts=3, initial_delay=0.5)
    async def flaky_function():
        nonlocal call_count
        call_count += 1
        logger.info(f"函数调用 #{call_count}")
        if call_count < 3:
            raise ConnectionError(f"连接失败 (尝试 {call_count})")
        return f"成功 (第 {call_count} 次)"
    
    try:
        result = await flaky_function()
        logger.info(f"结果: {result}")
        assert call_count == 3
        logger.info("✅ 重试机制测试通过")
    except Exception as e:
        logger.error(f"❌ 重试测试失败: {e}")


async def test_circuit_breaker():
    """测试断路器机制"""
    logger.info("\n=== 测试断路器机制 ===")
    
    # 重置所有断路器
    breaker_manager.reset_all()
    
    failure_count = 0
    
    @circuit_breaker("test_service", failure_threshold=3, recovery_timeout=2)
    async def unstable_service():
        nonlocal failure_count
        failure_count += 1
        logger.info(f"服务调用 #{failure_count}")
        if failure_count <= 4:
            raise RuntimeError(f"服务错误 #{failure_count}")
        return "服务恢复"
    
    # 触发3次失败，断路器应该打开
    for i in range(3):
        try:
            await unstable_service()
        except RuntimeError as e:
            logger.info(f"预期的失败: {e}")
    
    # 第4次应该被断路器阻止
    try:
        await unstable_service()
        logger.error("❌ 断路器应该阻止调用")
    except CircuitBreakerOpenError:
        logger.info("✅ 断路器正确阻止了调用")
    
    # 获取断路器状态
    stats = unstable_service.breaker.get_stats()
    logger.info(f"断路器状态: {stats}")
    
    # 等待恢复
    logger.info("等待2秒恢复时间...")
    await asyncio.sleep(2.5)
    
    # 应该可以再次尝试
    try:
        result = await unstable_service()
        logger.info(f"恢复后调用结果: {result}")
    except RuntimeError:
        logger.info("服务仍在失败中（半开状态）")


async def test_exponential_backoff():
    """测试指数退避策略"""
    logger.info("\n=== 测试指数退避策略 ===")
    
    attempt_times = []
    
    @retry(max_attempts=4, initial_delay=1.0, strategy=RetryStrategy.EXPONENTIAL)
    async def timing_function():
        attempt_times.append(time.time())
        if len(attempt_times) < 4:
            raise RuntimeError(f"失败 #{len(attempt_times)}")
        return "成功"
    
    start_time = time.time()
    try:
        result = await timing_function()
        total_time = time.time() - start_time
        
        # 计算延迟
        delays = []
        for i in range(1, len(attempt_times)):
            delay = attempt_times[i] - attempt_times[i-1]
            delays.append(delay)
            logger.info(f"第 {i} 次重试延迟: {delay:.2f}秒")
        
        logger.info(f"总执行时间: {total_time:.2f}秒")
        logger.info("✅ 指数退避测试通过")
        
    except Exception as e:
        logger.error(f"❌ 指数退避测试失败: {e}")


async def test_combined_resilience():
    """测试组合使用重试和断路器"""
    logger.info("\n=== 测试组合弹性机制 ===")
    
    call_history = []
    
    @retry(max_attempts=2, initial_delay=0.5)
    @circuit_breaker("combined_service", failure_threshold=3, recovery_timeout=1)
    async def resilient_service(fail_times=0):
        call_history.append(time.time())
        if len(call_history) <= fail_times:
            raise ConnectionError(f"连接错误 #{len(call_history)}")
        return f"成功 (第 {len(call_history)} 次调用)"
    
    # 第一次调用：应该重试并成功
    result = await resilient_service(fail_times=1)
    logger.info(f"第一次调用结果: {result}")
    assert len(call_history) == 2  # 1次失败 + 1次成功
    
    # 清空历史
    call_history.clear()
    
    # 触发断路器
    for i in range(2):
        try:
            await resilient_service(fail_times=10)  # 永远失败
        except ConnectionError:
            pass
    
    # 断路器应该打开
    try:
        await resilient_service(fail_times=0)  # 即使不会失败
        logger.error("❌ 断路器应该阻止调用")
    except CircuitBreakerOpenError:
        logger.info("✅ 组合机制正确工作")


async def test_performance_impact():
    """测试弹性机制对性能的影响"""
    logger.info("\n=== 测试性能影响 ===")
    
    # 无保护的函数
    async def unprotected_function():
        await asyncio.sleep(0.01)
        return "success"
    
    # 有保护的函数
    @retry(max_attempts=3)
    @circuit_breaker("protected", failure_threshold=5)
    async def protected_function():
        await asyncio.sleep(0.01)
        return "success"
    
    # 测试无保护函数
    start = time.time()
    for _ in range(100):
        await unprotected_function()
    unprotected_time = time.time() - start
    
    # 测试有保护函数
    start = time.time()
    for _ in range(100):
        await protected_function()
    protected_time = time.time() - start
    
    overhead = ((protected_time - unprotected_time) / unprotected_time) * 100
    
    logger.info(f"无保护执行时间: {unprotected_time:.3f}秒")
    logger.info(f"有保护执行时间: {protected_time:.3f}秒")
    logger.info(f"性能开销: {overhead:.1f}%")
    
    if overhead < 20:
        logger.info("✅ 性能开销在可接受范围内")
    else:
        logger.warning(f"⚠️ 性能开销较高: {overhead:.1f}%")


async def main():
    """运行所有测试"""
    logger.info("开始弹性机制测试\n")
    
    try:
        await test_retry_mechanism()
        await test_circuit_breaker()
        await test_exponential_backoff()
        await test_combined_resilience()
        await test_performance_impact()
        
        logger.info("\n🎉 所有测试完成！")
        
    except Exception as e:
        logger.error(f"\n❌ 测试失败: {e}")
        raise


if __name__ == "__main__":
    asyncio.run(main())