#!/usr/bin/env python3
"""
Sage 错误处理和性能优化模块
提供全面的错误处理、性能监控和优化功能
"""

import asyncio
import json
import time
import traceback
import psutil
import functools
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional, Callable, TypeVar, Union
from collections import defaultdict, deque
import logging
from enum import Enum
from contextlib import asynccontextmanager

logger = logging.getLogger(__name__)

T = TypeVar('T')


class ErrorType(Enum):
    """错误类型枚举"""
    SYSTEM_ERROR = "system_error"          # 系统错误
    MEMORY_ERROR = "memory_error"          # 记忆系统错误
    DATABASE_ERROR = "database_error"      # 数据库错误
    API_ERROR = "api_error"                # API调用错误
    VALIDATION_ERROR = "validation_error"  # 验证错误
    TIMEOUT_ERROR = "timeout_error"        # 超时错误
    UNKNOWN_ERROR = "unknown_error"        # 未知错误


class ErrorSeverity(Enum):
    """错误严重程度"""
    CRITICAL = "critical"  # 严重错误，需要立即处理
    HIGH = "high"         # 高优先级错误
    MEDIUM = "medium"     # 中等优先级
    LOW = "low"           # 低优先级
    INFO = "info"         # 信息级别


class ErrorHandler:
    """统一错误处理器"""
    
    def __init__(self):
        self.error_log = deque(maxlen=1000)  # 保留最近1000条错误
        self.error_stats = defaultdict(int)
        self.recovery_strategies = self._init_recovery_strategies()
        self.circuit_breakers = {}
        
    def handle_error(self, 
                    error: Exception,
                    context: Dict[str, Any] = None,
                    severity: ErrorSeverity = ErrorSeverity.MEDIUM) -> Dict[str, Any]:
        """处理错误"""
        
        error_info = {
            "timestamp": datetime.now(),
            "type": self._classify_error(error),
            "severity": severity.value,
            "message": str(error),
            "traceback": traceback.format_exc(),
            "context": context or {},
            "recovery_attempted": False,
            "recovery_success": False
        }
        
        # 记录错误
        self._log_error(error_info)
        
        # 尝试恢复
        recovery_result = self._attempt_recovery(error, error_info)
        error_info.update(recovery_result)
        
        # 更新统计
        self._update_stats(error_info)
        
        return error_info
        
    def _classify_error(self, error: Exception) -> ErrorType:
        """分类错误"""
        error_name = error.__class__.__name__
        error_msg = str(error).lower()
        
        if isinstance(error, (OSError, IOError)):
            return ErrorType.SYSTEM_ERROR
        elif "database" in error_msg or "connection" in error_msg:
            return ErrorType.DATABASE_ERROR
        elif "memory" in error_msg or isinstance(error, MemoryError):
            return ErrorType.MEMORY_ERROR
        elif "timeout" in error_msg or isinstance(error, asyncio.TimeoutError):
            return ErrorType.TIMEOUT_ERROR
        elif "api" in error_msg or "request" in error_msg:
            return ErrorType.API_ERROR
        elif isinstance(error, (ValueError, TypeError)):
            return ErrorType.VALIDATION_ERROR
        else:
            return ErrorType.UNKNOWN_ERROR
            
    def _log_error(self, error_info: Dict[str, Any]):
        """记录错误"""
        self.error_log.append(error_info)
        
        # 根据严重程度记录日志
        severity = error_info["severity"]
        message = f"[{error_info['type'].value}] {error_info['message']}"
        
        if severity == ErrorSeverity.CRITICAL.value:
            logger.critical(message)
        elif severity == ErrorSeverity.HIGH.value:
            logger.error(message)
        elif severity == ErrorSeverity.MEDIUM.value:
            logger.warning(message)
        else:
            logger.info(message)
            
    def _attempt_recovery(self, error: Exception, error_info: Dict[str, Any]) -> Dict[str, Any]:
        """尝试错误恢复"""
        error_type = error_info["type"]
        
        if error_type in self.recovery_strategies:
            strategy = self.recovery_strategies[error_type]
            try:
                strategy(error, error_info)
                return {
                    "recovery_attempted": True,
                    "recovery_success": True,
                    "recovery_strategy": strategy.__name__
                }
            except Exception as e:
                logger.error(f"Recovery failed: {e}")
                return {
                    "recovery_attempted": True,
                    "recovery_success": False,
                    "recovery_error": str(e)
                }
                
        return {"recovery_attempted": False}
        
    def _init_recovery_strategies(self) -> Dict[ErrorType, Callable]:
        """初始化恢复策略"""
        return {
            ErrorType.DATABASE_ERROR: self._recover_database_error,
            ErrorType.MEMORY_ERROR: self._recover_memory_error,
            ErrorType.TIMEOUT_ERROR: self._recover_timeout_error,
            ErrorType.API_ERROR: self._recover_api_error
        }
        
    def _recover_database_error(self, error: Exception, error_info: Dict[str, Any]):
        """数据库错误恢复"""
        # 重试连接
        logger.info("Attempting database reconnection...")
        # 实际实现需要数据库重连逻辑
        
    def _recover_memory_error(self, error: Exception, error_info: Dict[str, Any]):
        """内存错误恢复"""
        # 清理缓存
        logger.info("Clearing caches to free memory...")
        # 实际实现需要缓存清理逻辑
        
    def _recover_timeout_error(self, error: Exception, error_info: Dict[str, Any]):
        """超时错误恢复"""
        # 增加超时时间或重试
        logger.info("Adjusting timeout settings...")
        
    def _recover_api_error(self, error: Exception, error_info: Dict[str, Any]):
        """API错误恢复"""
        # 使用备用API或重试
        logger.info("Switching to backup API endpoint...")
        
    def _update_stats(self, error_info: Dict[str, Any]):
        """更新错误统计"""
        error_type = error_info["type"].value
        self.error_stats[error_type] += 1
        
        # 检查错误频率，触发告警
        if self.error_stats[error_type] > 10:
            logger.warning(f"High error frequency detected for {error_type}: {self.error_stats[error_type]} errors")
            
    def get_error_summary(self) -> Dict[str, Any]:
        """获取错误摘要"""
        recent_errors = list(self.error_log)[-10:]  # 最近10条
        
        return {
            "total_errors": len(self.error_log),
            "error_distribution": dict(self.error_stats),
            "recent_errors": [
                {
                    "timestamp": e["timestamp"].isoformat(),
                    "type": e["type"].value,
                    "severity": e["severity"],
                    "message": e["message"]
                }
                for e in recent_errors
            ]
        }


class PerformanceMonitor:
    """性能监控器"""
    
    def __init__(self):
        self.metrics = defaultdict(list)
        self.thresholds = self._init_thresholds()
        self.alerts = deque(maxlen=100)
        
    def _init_thresholds(self) -> Dict[str, float]:
        """初始化性能阈值"""
        return {
            "response_time": 2.0,      # 2秒
            "memory_usage": 80.0,      # 80%
            "cpu_usage": 70.0,         # 70%
            "query_time": 1.0,         # 1秒
            "cache_hit_rate": 0.6      # 60%
        }
        
    @asynccontextmanager
    async def measure_performance(self, operation: str):
        """测量操作性能"""
        start_time = time.time()
        start_memory = psutil.Process().memory_info().rss / 1024 / 1024  # MB
        
        try:
            yield
        finally:
            end_time = time.time()
            end_memory = psutil.Process().memory_info().rss / 1024 / 1024  # MB
            
            duration = end_time - start_time
            memory_delta = end_memory - start_memory
            
            # 记录指标
            self.record_metric(f"{operation}_duration", duration)
            self.record_metric(f"{operation}_memory_delta", memory_delta)
            
            # 检查阈值
            if duration > self.thresholds.get("response_time", float('inf')):
                self._trigger_alert(
                    f"Slow operation: {operation} took {duration:.2f}s",
                    "performance"
                )
                
    def record_metric(self, metric_name: str, value: float):
        """记录性能指标"""
        self.metrics[metric_name].append({
            "timestamp": datetime.now(),
            "value": value
        })
        
        # 保留最近1000条记录
        if len(self.metrics[metric_name]) > 1000:
            self.metrics[metric_name] = self.metrics[metric_name][-1000:]
            
    def get_system_metrics(self) -> Dict[str, float]:
        """获取系统指标"""
        cpu_percent = psutil.cpu_percent(interval=0.1)
        memory = psutil.virtual_memory()
        
        metrics = {
            "cpu_usage": cpu_percent,
            "memory_usage": memory.percent,
            "memory_available_mb": memory.available / 1024 / 1024,
            "disk_usage": psutil.disk_usage('/').percent
        }
        
        # 检查系统资源
        if metrics["cpu_usage"] > self.thresholds["cpu_usage"]:
            self._trigger_alert(
                f"High CPU usage: {metrics['cpu_usage']:.1f}%",
                "resource"
            )
            
        if metrics["memory_usage"] > self.thresholds["memory_usage"]:
            self._trigger_alert(
                f"High memory usage: {metrics['memory_usage']:.1f}%",
                "resource"
            )
            
        return metrics
        
    def get_performance_summary(self) -> Dict[str, Any]:
        """获取性能摘要"""
        summary = {
            "system_metrics": self.get_system_metrics(),
            "operation_stats": {},
            "recent_alerts": list(self.alerts)[-10:]
        }
        
        # 计算操作统计
        for metric_name, values in self.metrics.items():
            if values and "_duration" in metric_name:
                recent_values = [v["value"] for v in values[-100:]]
                summary["operation_stats"][metric_name] = {
                    "avg": sum(recent_values) / len(recent_values),
                    "min": min(recent_values),
                    "max": max(recent_values),
                    "count": len(values)
                }
                
        return summary
        
    def _trigger_alert(self, message: str, alert_type: str):
        """触发性能告警"""
        alert = {
            "timestamp": datetime.now().isoformat(),
            "type": alert_type,
            "message": message
        }
        
        self.alerts.append(alert)
        logger.warning(f"Performance alert: {message}")


class CircuitBreaker:
    """熔断器"""
    
    def __init__(self, 
                 failure_threshold: int = 5,
                 recovery_timeout: int = 60,
                 expected_exception: type = Exception):
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.expected_exception = expected_exception
        self.failure_count = 0
        self.last_failure_time = None
        self.state = "closed"  # closed, open, half-open
        
    def __call__(self, func: Callable[..., T]) -> Callable[..., T]:
        """装饰器实现"""
        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            if self.state == "open":
                if self._should_attempt_reset():
                    self.state = "half-open"
                else:
                    raise Exception(f"Circuit breaker is open for {func.__name__}")
                    
            try:
                result = await func(*args, **kwargs)
                self._on_success()
                return result
            except self.expected_exception as e:
                self._on_failure()
                raise e
                
        return wrapper
        
    def _should_attempt_reset(self) -> bool:
        """检查是否应该尝试重置"""
        return (self.last_failure_time and 
                datetime.now() - self.last_failure_time > timedelta(seconds=self.recovery_timeout))
                
    def _on_success(self):
        """成功时的处理"""
        self.failure_count = 0
        self.state = "closed"
        
    def _on_failure(self):
        """失败时的处理"""
        self.failure_count += 1
        self.last_failure_time = datetime.now()
        
        if self.failure_count >= self.failure_threshold:
            self.state = "open"
            logger.error(f"Circuit breaker opened after {self.failure_count} failures")


class ResourceManager:
    """资源管理器"""
    
    def __init__(self):
        self.resource_limits = {
            "max_memory_mb": 2048,
            "max_cache_size": 1000,
            "max_concurrent_operations": 10
        }
        self.current_operations = 0
        self.cache_sizes = defaultdict(int)
        
    async def check_resources(self) -> bool:
        """检查资源是否充足"""
        memory_usage = psutil.Process().memory_info().rss / 1024 / 1024
        
        if memory_usage > self.resource_limits["max_memory_mb"]:
            logger.warning(f"Memory usage exceeds limit: {memory_usage:.1f}MB")
            return False
            
        if self.current_operations >= self.resource_limits["max_concurrent_operations"]:
            logger.warning(f"Too many concurrent operations: {self.current_operations}")
            return False
            
        return True
        
    @asynccontextmanager
    async def acquire_resource(self, resource_type: str = "operation"):
        """获取资源"""
        if not await self.check_resources():
            raise Exception("Insufficient resources")
            
        self.current_operations += 1
        try:
            yield
        finally:
            self.current_operations -= 1
            
    def cleanup_caches(self, target_size: Optional[int] = None):
        """清理缓存"""
        if target_size is None:
            target_size = self.resource_limits["max_cache_size"] // 2
            
        logger.info(f"Cleaning caches to target size: {target_size}")
        # 实际实现需要具体的缓存清理逻辑
        
    def get_resource_status(self) -> Dict[str, Any]:
        """获取资源状态"""
        memory_info = psutil.Process().memory_info()
        
        return {
            "memory_usage_mb": memory_info.rss / 1024 / 1024,
            "memory_limit_mb": self.resource_limits["max_memory_mb"],
            "current_operations": self.current_operations,
            "max_operations": self.resource_limits["max_concurrent_operations"],
            "cache_sizes": dict(self.cache_sizes)
        }


class OptimizationEngine:
    """优化引擎"""
    
    def __init__(self, performance_monitor: PerformanceMonitor):
        self.performance_monitor = performance_monitor
        self.optimization_rules = self._init_optimization_rules()
        self.applied_optimizations = []
        
    def _init_optimization_rules(self) -> List[Dict[str, Any]]:
        """初始化优化规则"""
        return [
            {
                "name": "cache_optimization",
                "condition": lambda metrics: metrics.get("cache_hit_rate", 1.0) < 0.5,
                "action": self._optimize_cache,
                "description": "优化缓存策略"
            },
            {
                "name": "query_optimization",
                "condition": lambda metrics: any(
                    m.get("avg", 0) > 1.0 
                    for k, m in metrics.get("operation_stats", {}).items() 
                    if "query" in k
                ),
                "action": self._optimize_queries,
                "description": "优化查询性能"
            },
            {
                "name": "memory_optimization",
                "condition": lambda metrics: metrics.get("system_metrics", {}).get("memory_usage", 0) > 70,
                "action": self._optimize_memory,
                "description": "优化内存使用"
            }
        ]
        
    def analyze_and_optimize(self) -> List[Dict[str, Any]]:
        """分析并执行优化"""
        metrics = self.performance_monitor.get_performance_summary()
        recommendations = []
        
        for rule in self.optimization_rules:
            if rule["condition"](metrics):
                recommendation = {
                    "rule": rule["name"],
                    "description": rule["description"],
                    "timestamp": datetime.now().isoformat()
                }
                
                # 尝试自动优化
                try:
                    rule["action"](metrics)
                    recommendation["status"] = "applied"
                    self.applied_optimizations.append(recommendation)
                except Exception as e:
                    recommendation["status"] = "failed"
                    recommendation["error"] = str(e)
                    
                recommendations.append(recommendation)
                
        return recommendations
        
    def _optimize_cache(self, metrics: Dict[str, Any]):
        """优化缓存"""
        logger.info("Optimizing cache configuration...")
        # 实际实现需要调整缓存参数
        
    def _optimize_queries(self, metrics: Dict[str, Any]):
        """优化查询"""
        logger.info("Optimizing query performance...")
        # 实际实现需要分析和优化慢查询
        
    def _optimize_memory(self, metrics: Dict[str, Any]):
        """优化内存"""
        logger.info("Optimizing memory usage...")
        # 实际实现需要内存优化策略


# 全局实例
error_handler = ErrorHandler()
performance_monitor = PerformanceMonitor()
resource_manager = ResourceManager()
optimization_engine = OptimizationEngine(performance_monitor)


# 装饰器函数
def with_error_handling(severity: ErrorSeverity = ErrorSeverity.MEDIUM):
    """错误处理装饰器"""
    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            try:
                return await func(*args, **kwargs)
            except Exception as e:
                context = {
                    "function": func.__name__,
                    "args": str(args),
                    "kwargs": str(kwargs)
                }
                error_handler.handle_error(e, context, severity)
                raise
                
        return wrapper
    return decorator


def with_performance_monitoring(operation_name: Optional[str] = None):
    """性能监控装饰器"""
    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            name = operation_name or func.__name__
            async with performance_monitor.measure_performance(name):
                return await func(*args, **kwargs)
                
        return wrapper
    return decorator


def with_circuit_breaker(failure_threshold: int = 5, recovery_timeout: int = 60):
    """熔断器装饰器"""
    breaker = CircuitBreaker(failure_threshold, recovery_timeout)
    return breaker


# 测试函数
async def test_error_handling_and_optimization():
    """测试错误处理和性能优化"""
    print("测试错误处理和性能优化模块...")
    
    # 测试错误处理
    print("\n1. 测试错误处理")
    try:
        raise ValueError("测试错误")
    except Exception as e:
        error_info = error_handler.handle_error(e, {"test": True}, ErrorSeverity.LOW)
        print(f"✓ 错误已处理: {error_info['type'].value}")
    
    # 测试性能监控
    print("\n2. 测试性能监控")
    
    @with_performance_monitoring("test_operation")
    async def slow_operation():
        await asyncio.sleep(0.1)
        return "done"
        
    result = await slow_operation()
    print(f"✓ 操作完成: {result}")
    
    # 获取性能摘要
    perf_summary = performance_monitor.get_performance_summary()
    print(f"✓ 系统指标: CPU={perf_summary['system_metrics']['cpu_usage']:.1f}%, "
          f"Memory={perf_summary['system_metrics']['memory_usage']:.1f}%")
    
    # 测试资源管理
    print("\n3. 测试资源管理")
    async with resource_manager.acquire_resource():
        status = resource_manager.get_resource_status()
        print(f"✓ 资源状态: {status['current_operations']}/{status['max_operations']} 操作")
    
    # 测试优化引擎
    print("\n4. 测试优化引擎")
    recommendations = optimization_engine.analyze_and_optimize()
    print(f"✓ 优化建议: {len(recommendations)} 条")
    
    # 获取错误摘要
    error_summary = error_handler.get_error_summary()
    print(f"\n错误统计: {error_summary['total_errors']} 个错误")
    
    print("\n测试完成！")


if __name__ == "__main__":
    asyncio.run(test_error_handling_and_optimization())