#!/usr/bin/env python3
"""
错误恢复机制测试
"""

import sys
import os
import time
import asyncio
from pathlib import Path

# 添加项目根目录到 Python 路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from error_recovery import (
    RetryPolicy, CircuitBreaker, retry_with_backoff,
    HealthMonitor, ErrorCollector, health_monitor, error_collector,
    monitored_operation, graceful_degradation, ResourceGuard,
    db_retry_policy, api_circuit_breaker, get_system_health
)


class TestRetryPolicy:
    """测试重试策略"""
    
    def test_basic_retry(self):
        """测试基本重试功能"""
        attempt_count = 0
        
        @retry_with_backoff(policy=RetryPolicy(max_attempts=3, initial_delay=0.1))
        def failing_function():
            nonlocal attempt_count
            attempt_count += 1
            if attempt_count < 3:
                raise ValueError("模拟失败")
            return "成功"
        
        result = failing_function()
        assert result == "成功"
        assert attempt_count == 3
    
    def test_async_retry(self):
        """测试异步重试"""
        attempt_count = 0
        
        @retry_with_backoff(policy=RetryPolicy(max_attempts=3, initial_delay=0.1))
        async def async_failing_function():
            nonlocal attempt_count
            attempt_count += 1
            if attempt_count < 3:
                raise ValueError("异步失败")
            return "异步成功"
        
        loop = asyncio.new_event_loop()
        result = loop.run_until_complete(async_failing_function())
        loop.close()
        
        assert result == "异步成功"
        assert attempt_count == 3


class TestCircuitBreaker:
    """测试断路器"""
    
    def test_circuit_breaker_opens(self):
        """测试断路器打开"""
        breaker = CircuitBreaker(failure_threshold=2, recovery_timeout=1)
        
        def failing_function():
            raise ValueError("总是失败")
        
        # 第一次失败
        try:
            breaker.call(failing_function)
        except ValueError:
            pass
        
        # 第二次失败，应该打开断路器
        try:
            breaker.call(failing_function)
        except ValueError:
            pass
        
        # 断路器应该已经打开
        assert breaker.state == 'open'
        
        # 下一次调用应该直接失败
        try:
            breaker.call(failing_function)
            assert False, "断路器打开时应该抛出异常"
        except Exception as e:
            assert "Circuit breaker is OPEN" in str(e)


class TestMonitoring:
    """测试监控功能"""
    
    def test_health_monitor(self):
        """测试健康监控"""
        monitor = HealthMonitor()
        
        # 设置阈值
        monitor.set_threshold('test_metric', 0, 100)
        
        # 记录正常值
        monitor.record_metric('test_metric', 50)
        monitor.record_metric('test_metric', 60)
        
        # 获取状态
        status = monitor.get_health_status()
        assert status['healthy'] == True
        assert 'test_metric' in status['metrics']
        
        # 记录异常值
        monitor.record_metric('test_metric', 150)
        
        # 再次检查状态
        status = monitor.get_health_status()
        assert len(status['recent_alerts']) > 0
    
    def test_error_collector(self):
        """测试错误收集"""
        collector = ErrorCollector(max_errors=10)
        
        # 收集错误
        try:
            raise ValueError("测试错误")
        except Exception as e:
            collector.collect_error(e, {'context': 'test'})
        
        # 获取摘要
        summary = collector.get_error_summary()
        assert summary['total_errors'] == 1
        assert 'ValueError' in summary['error_types']
        assert summary['error_types']['ValueError'] == 1


class TestContextManagers:
    """测试上下文管理器"""
    
    def test_monitored_operation(self):
        """测试监控操作"""
        with monitored_operation('test_operation'):
            time.sleep(0.1)
        
        # 检查指标是否被记录
        status = health_monitor.get_health_status()
        metrics = status['metrics']
        assert any('test_operation' in key for key in metrics.keys())
    
    def test_resource_guard(self):
        """测试资源保护"""
        guard = ResourceGuard(max_concurrent=2)
        
        active_count = 0
        
        def use_resource():
            nonlocal active_count
            with guard.acquire(timeout=1):
                active_count += 1
                assert active_count <= 2
                time.sleep(0.1)
                active_count -= 1
        
        # 并发使用资源
        import threading
        threads = []
        for _ in range(5):
            t = threading.Thread(target=use_resource)
            threads.append(t)
            t.start()
        
        for t in threads:
            t.join()


class TestGracefulDegradation:
    """测试优雅降级"""
    
    def test_graceful_degradation_sync(self):
        """测试同步函数的优雅降级"""
        call_count = {'main': 0, 'fallback': 0}
        
        @graceful_degradation(lambda *args, **kwargs: "降级结果")
        def may_fail(should_fail=False):
            call_count['main'] += 1
            if should_fail:
                raise ValueError("模拟失败")
            return "正常结果"
        
        # 正常情况
        result = may_fail(should_fail=False)
        assert result == "正常结果"
        assert call_count['main'] == 1
        
        # 失败情况
        result = may_fail(should_fail=True)
        assert result == "降级结果"
        assert call_count['main'] == 2
    
    def test_graceful_degradation_async(self):
        """测试异步函数的优雅降级"""
        @graceful_degradation(lambda *args, **kwargs: "异步降级结果")
        async def async_may_fail(should_fail=False):
            if should_fail:
                raise ValueError("异步失败")
            return "异步正常结果"
        
        loop = asyncio.new_event_loop()
        
        # 正常情况
        result = loop.run_until_complete(async_may_fail(should_fail=False))
        assert result == "异步正常结果"
        
        # 失败情况
        result = loop.run_until_complete(async_may_fail(should_fail=True))
        assert result == "异步降级结果"
        
        loop.close()


def test_system_health():
    """测试系统健康状态"""
    health = get_system_health()
    
    assert 'timestamp' in health
    assert 'health' in health
    assert 'errors' in health
    assert 'status' in health
    assert health['status'] in ['healthy', 'degraded']
    
    print(f"\n系统健康状态: {health['status']}")
    print(f"健康指标: {health['health']['healthy']}")
    print(f"错误总数: {health['errors']['total_errors']}")


def run_error_recovery_tests():
    """运行错误恢复测试"""
    print("=" * 60)
    print("错误恢复机制测试")
    print("=" * 60)
    
    import pytest
    pytest.main([__file__, '-v', '--tb=short'])


if __name__ == '__main__':
    run_error_recovery_tests()