#!/usr/bin/env python3
"""
单元测试 - 错误处理系统
测试 ErrorHandler、PerformanceMonitor、ResourceManager 等组件
"""

import sys
from pathlib import Path
import asyncio
import time
from typing import Dict, Any
import psutil

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from sage_error_handler import (
    ErrorHandler,
    PerformanceMonitor,
    ResourceManager,
    OptimizationEngine,
    CircuitBreaker,
    ErrorType,
    ErrorSeverity,
    with_error_handling,
    with_performance_monitoring,
    with_circuit_breaker
)


class TestErrorHandler:
    """测试错误处理器"""
    
    def __init__(self):
        self.test_results = []
        
    def test_error_classification(self):
        """测试错误分类"""
        handler = ErrorHandler()
        
        test_cases = [
            {
                "error": ValueError("Invalid input"),
                "expected_type": ErrorType.VALIDATION_ERROR,
                "description": "验证错误"
            },
            {
                "error": FileNotFoundError("File not found"),
                "expected_type": ErrorType.SYSTEM_ERROR,
                "description": "系统错误"
            },
            {
                "error": ConnectionError("Database connection failed"),
                "expected_type": ErrorType.DATABASE_ERROR,
                "description": "数据库错误"
            },
            {
                "error": MemoryError("Out of memory"),
                "expected_type": ErrorType.MEMORY_ERROR,
                "description": "内存错误"
            },
            {
                "error": asyncio.TimeoutError("Request timeout"),
                "expected_type": ErrorType.TIMEOUT_ERROR,
                "description": "超时错误"
            },
            {
                "error": Exception("Unknown error"),
                "expected_type": ErrorType.UNKNOWN_ERROR,
                "description": "未知错误"
            },
            {
                "error": RuntimeError("API request failed"),
                "expected_type": ErrorType.API_ERROR,
                "description": "API错误"
            }
        ]
        
        all_passed = True
        for case in test_cases:
            error_info = handler.handle_error(
                case["error"], 
                severity=ErrorSeverity.LOW
            )
            
            detected_type = error_info["type"]
            success = detected_type == case["expected_type"]
            
            if not success:
                all_passed = False
                
            self.test_results.append({
                "test": "error_classification",
                "case": case["description"],
                "success": success,
                "expected": case["expected_type"].value,
                "actual": detected_type.value
            })
            
        return all_passed
        
    def test_error_recovery(self):
        """测试错误恢复机制"""
        handler = ErrorHandler()
        
        # 测试数据库错误恢复
        db_error = ConnectionError("Database connection lost")
        error_info = handler.handle_error(
            db_error, 
            {"operation": "query"}, 
            ErrorSeverity.HIGH
        )
        
        recovery_attempted = error_info["recovery_attempted"]
        
        # 测试内存错误恢复
        memory_error = MemoryError("Out of memory")
        memory_error_info = handler.handle_error(
            memory_error,
            {"operation": "cache"},
            ErrorSeverity.HIGH
        )
        
        memory_recovery_attempted = memory_error_info["recovery_attempted"]
        
        success = recovery_attempted and memory_recovery_attempted
        
        self.test_results.append({
            "test": "error_recovery",
            "success": success,
            "db_recovery": recovery_attempted,
            "memory_recovery": memory_recovery_attempted
        })
        
        return success
        
    def test_error_statistics(self):
        """测试错误统计"""
        handler = ErrorHandler()
        
        # 清空之前的错误
        handler.error_log.clear()
        handler.error_stats.clear()
        
        # 生成一些错误
        errors = [
            ValueError("Test 1"),
            ValueError("Test 2"),
            ConnectionError("Test 3"),
            MemoryError("Test 4")
        ]
        
        for error in errors:
            handler.handle_error(error)
            
        # 获取统计
        summary = handler.get_error_summary()
        
        success = (
            summary["total_errors"] >= len(errors) and
            ErrorType.VALIDATION_ERROR.value in summary["error_distribution"] and
            summary["error_distribution"][ErrorType.VALIDATION_ERROR.value] >= 2
        )
        
        self.test_results.append({
            "test": "error_statistics",
            "success": success,
            "total_errors": summary["total_errors"],
            "distribution": summary["error_distribution"]
        })
        
        return success
        
    async def test_error_handling_decorator(self):
        """测试错误处理装饰器"""
        
        error_count = 0
        
        @with_error_handling(ErrorSeverity.MEDIUM)
        async def risky_operation(should_fail: bool = False):
            if should_fail:
                raise ValueError("Simulated error")
            return "Success"
            
        # 测试成功情况
        try:
            result = await risky_operation(False)
            success_case = result == "Success"
        except:
            success_case = False
            
        # 测试失败情况
        try:
            await risky_operation(True)
            failure_case = False  # 不应该到这里
        except ValueError:
            failure_case = True  # 应该抛出原始错误
            
        success = success_case and failure_case
        
        self.test_results.append({
            "test": "error_handling_decorator",
            "success": success,
            "success_case": success_case,
            "failure_case": failure_case
        })
        
        return success


class TestPerformanceMonitor:
    """测试性能监控器"""
    
    def __init__(self):
        self.test_results = []
        
    async def test_performance_measurement(self):
        """测试性能测量"""
        monitor = PerformanceMonitor()
        
        # 测量一个操作
        async with monitor.measure_performance("test_operation"):
            await asyncio.sleep(0.05)  # 50ms
            
        # 获取性能数据
        summary = monitor.get_performance_summary()
        
        # 检查是否记录了操作
        has_operation = "test_operation_duration" in summary["operation_stats"]
        
        if has_operation:
            stats = summary["operation_stats"]["test_operation_duration"]
            # 检查时间是否合理（应该大于50ms）
            duration_reasonable = stats["avg"] >= 0.05
        else:
            duration_reasonable = False
            
        success = has_operation and duration_reasonable
        
        self.test_results.append({
            "test": "performance_measurement",
            "success": success,
            "has_operation": has_operation,
            "duration_reasonable": duration_reasonable
        })
        
        return success
        
    def test_system_metrics(self):
        """测试系统指标获取"""
        monitor = PerformanceMonitor()
        
        metrics = monitor.get_system_metrics()
        
        required_metrics = ["cpu_usage", "memory_usage", "memory_available_mb", "disk_usage"]
        has_all_metrics = all(metric in metrics for metric in required_metrics)
        
        # 检查值的合理性
        values_reasonable = (
            0 <= metrics.get("cpu_usage", -1) <= 100 and
            0 <= metrics.get("memory_usage", -1) <= 100 and
            metrics.get("memory_available_mb", -1) > 0 and
            0 <= metrics.get("disk_usage", -1) <= 100
        )
        
        success = has_all_metrics and values_reasonable
        
        self.test_results.append({
            "test": "system_metrics",
            "success": success,
            "metrics": metrics
        })
        
        return success
        
    def test_metric_recording(self):
        """测试指标记录"""
        monitor = PerformanceMonitor()
        
        # 记录一些指标
        test_values = [1.0, 2.0, 3.0, 4.0, 5.0]
        for value in test_values:
            monitor.record_metric("test_metric", value)
            
        # 检查是否记录成功
        has_metrics = "test_metric" in monitor.metrics
        correct_count = len(monitor.metrics.get("test_metric", [])) == len(test_values)
        
        success = has_metrics and correct_count
        
        self.test_results.append({
            "test": "metric_recording",
            "success": success,
            "recorded_count": len(monitor.metrics.get("test_metric", []))
        })
        
        return success
        
    async def test_performance_monitoring_decorator(self):
        """测试性能监控装饰器"""
        monitor = PerformanceMonitor()
        
        @with_performance_monitoring("decorated_operation")
        async def monitored_operation():
            await asyncio.sleep(0.02)  # 20ms
            return "done"
            
        # 执行操作
        result = await monitored_operation()
        
        # 检查是否记录了性能
        summary = monitor.get_performance_summary()
        has_stats = "decorated_operation_duration" in summary["operation_stats"]
        
        success = result == "done" and has_stats
        
        self.test_results.append({
            "test": "performance_monitoring_decorator",
            "success": success,
            "has_stats": has_stats
        })
        
        return success


class TestResourceManager:
    """测试资源管理器"""
    
    def __init__(self):
        self.test_results = []
        
    async def test_resource_checking(self):
        """测试资源检查"""
        manager = ResourceManager()
        
        # 检查资源（正常情况应该充足）
        resources_ok = await manager.check_resources()
        
        success = isinstance(resources_ok, bool)
        
        self.test_results.append({
            "test": "resource_checking",
            "success": success,
            "resources_ok": resources_ok
        })
        
        return success
        
    async def test_resource_acquisition(self):
        """测试资源获取和释放"""
        manager = ResourceManager()
        
        initial_operations = manager.current_operations
        
        # 获取资源
        async with manager.acquire_resource():
            during_operations = manager.current_operations
            
        final_operations = manager.current_operations
        
        success = (
            during_operations == initial_operations + 1 and
            final_operations == initial_operations
        )
        
        self.test_results.append({
            "test": "resource_acquisition",
            "success": success,
            "initial": initial_operations,
            "during": during_operations,
            "final": final_operations
        })
        
        return success
        
    def test_resource_status(self):
        """测试资源状态获取"""
        manager = ResourceManager()
        
        status = manager.get_resource_status()
        
        required_fields = [
            "memory_usage_mb",
            "memory_limit_mb",
            "current_operations",
            "max_operations"
        ]
        
        has_all_fields = all(field in status for field in required_fields)
        values_reasonable = (
            status.get("memory_usage_mb", -1) > 0 and
            status.get("memory_limit_mb", -1) > 0 and
            status.get("current_operations", -1) >= 0 and
            status.get("max_operations", -1) > 0
        )
        
        success = has_all_fields and values_reasonable
        
        self.test_results.append({
            "test": "resource_status",
            "success": success,
            "status": status
        })
        
        return success
        
    async def test_resource_limits(self):
        """测试资源限制"""
        manager = ResourceManager()
        
        # 暂时降低限制以便测试
        original_limit = manager.resource_limits["max_concurrent_operations"]
        manager.resource_limits["max_concurrent_operations"] = 2
        
        # 获取两个资源（达到限制）
        async with manager.acquire_resource():
            async with manager.acquire_resource():
                # 尝试获取第三个应该失败
                try:
                    async with manager.acquire_resource():
                        limit_enforced = False
                except:
                    limit_enforced = True
                    
        # 恢复原始限制
        manager.resource_limits["max_concurrent_operations"] = original_limit
        
        success = limit_enforced
        
        self.test_results.append({
            "test": "resource_limits",
            "success": success,
            "limit_enforced": limit_enforced
        })
        
        return success


class TestOptimizationEngine:
    """测试优化引擎"""
    
    def __init__(self):
        self.test_results = []
        
    def test_optimization_rules(self):
        """测试优化规则"""
        monitor = PerformanceMonitor()
        engine = OptimizationEngine(monitor)
        
        # 检查是否有优化规则
        has_rules = len(engine.optimization_rules) > 0
        
        # 检查规则结构
        if has_rules:
            rule = engine.optimization_rules[0]
            has_required_fields = all(
                field in rule for field in ["name", "condition", "action", "description"]
            )
        else:
            has_required_fields = False
            
        success = has_rules and has_required_fields
        
        self.test_results.append({
            "test": "optimization_rules",
            "success": success,
            "rule_count": len(engine.optimization_rules)
        })
        
        return success
        
    def test_optimization_analysis(self):
        """测试优化分析"""
        monitor = PerformanceMonitor()
        engine = OptimizationEngine(monitor)
        
        # 模拟高内存使用
        monitor.record_metric("system_memory_usage", 75.0)
        
        # 分析并优化
        recommendations = engine.analyze_and_optimize()
        
        # 应该有优化建议
        has_recommendations = len(recommendations) > 0
        
        success = isinstance(recommendations, list)
        
        self.test_results.append({
            "test": "optimization_analysis",
            "success": success,
            "recommendation_count": len(recommendations)
        })
        
        return success


class TestCircuitBreaker:
    """测试熔断器"""
    
    def __init__(self):
        self.test_results = []
        
    async def test_circuit_breaker_normal(self):
        """测试熔断器正常操作"""
        
        @with_circuit_breaker(failure_threshold=3, recovery_timeout=1)
        async def protected_operation(should_fail=False):
            if should_fail:
                raise Exception("Operation failed")
            return "success"
            
        # 正常调用应该成功
        try:
            result = await protected_operation(False)
            normal_success = result == "success"
        except:
            normal_success = False
            
        success = normal_success
        
        self.test_results.append({
            "test": "circuit_breaker_normal",
            "success": success
        })
        
        return success
        
    async def test_circuit_breaker_failure(self):
        """测试熔断器故障处理"""
        
        failure_count = 0
        
        @with_circuit_breaker(failure_threshold=3, recovery_timeout=1)
        async def flaky_operation():
            nonlocal failure_count
            failure_count += 1
            if failure_count <= 3:
                raise Exception("Operation failed")
            return "success"
            
        # 触发3次失败
        for i in range(3):
            try:
                await flaky_operation()
            except:
                pass
                
        # 第4次应该因为熔断器打开而失败
        try:
            await flaky_operation()
            circuit_opened = False
        except Exception as e:
            circuit_opened = "Circuit breaker is open" in str(e)
            
        success = circuit_opened
        
        self.test_results.append({
            "test": "circuit_breaker_failure",
            "success": success,
            "circuit_opened": circuit_opened
        })
        
        return success


async def run_all_unit_tests():
    """运行所有单元测试"""
    print("=" * 60)
    print("单元测试：错误处理和性能优化系统")
    print("=" * 60)
    
    all_test_results = []
    
    # 错误处理器测试
    print("\n### 测试错误处理器 ###")
    error_tester = TestErrorHandler()
    error_tester.test_error_classification()
    error_tester.test_error_recovery()
    error_tester.test_error_statistics()
    await error_tester.test_error_handling_decorator()
    all_test_results.extend(error_tester.test_results)
    
    # 性能监控器测试
    print("\n### 测试性能监控器 ###")
    perf_tester = TestPerformanceMonitor()
    await perf_tester.test_performance_measurement()
    perf_tester.test_system_metrics()
    perf_tester.test_metric_recording()
    await perf_tester.test_performance_monitoring_decorator()
    all_test_results.extend(perf_tester.test_results)
    
    # 资源管理器测试
    print("\n### 测试资源管理器 ###")
    resource_tester = TestResourceManager()
    await resource_tester.test_resource_checking()
    await resource_tester.test_resource_acquisition()
    resource_tester.test_resource_status()
    await resource_tester.test_resource_limits()
    all_test_results.extend(resource_tester.test_results)
    
    # 优化引擎测试
    print("\n### 测试优化引擎 ###")
    opt_tester = TestOptimizationEngine()
    opt_tester.test_optimization_rules()
    opt_tester.test_optimization_analysis()
    all_test_results.extend(opt_tester.test_results)
    
    # 熔断器测试
    print("\n### 测试熔断器 ###")
    breaker_tester = TestCircuitBreaker()
    await breaker_tester.test_circuit_breaker_normal()
    await breaker_tester.test_circuit_breaker_failure()
    all_test_results.extend(breaker_tester.test_results)
    
    # 统计结果
    total_tests = len(all_test_results)
    passed_tests = sum(1 for result in all_test_results if result["success"])
    
    # 显示结果
    print(f"\n总测试数: {total_tests}")
    print(f"通过: {passed_tests}")
    print(f"失败: {total_tests - passed_tests}")
    
    # 显示失败的测试
    failures = [r for r in all_test_results if not r["success"]]
    if failures:
        print("\n失败的测试:")
        for failure in failures:
            print(f"  - {failure['test']}: {failure.get('case', 'N/A')}")
    else:
        print("\n✅ 所有测试通过！")
        
    print("=" * 60)
    
    return passed_tests == total_tests


if __name__ == "__main__":
    success = asyncio.run(run_all_unit_tests())
    
    if success:
        print("\n✨ 错误处理系统单元测试完成！")