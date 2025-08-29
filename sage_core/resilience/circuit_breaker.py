#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
断路器模式实现 - 防止级联故障
当服务持续失败时自动断开，避免无效请求
"""
import asyncio
import time
import logging
from typing import TypeVar, Callable, Optional, List, Type, Any
from functools import wraps
from dataclasses import dataclass, field
from enum import Enum
from datetime import datetime, timedelta
import threading

logger = logging.getLogger(__name__)

T = TypeVar('T')


class CircuitState(Enum):
    """断路器状态"""
    CLOSED = "closed"  # 正常工作
    OPEN = "open"  # 断路，拒绝请求
    HALF_OPEN = "half_open"  # 半开，尝试恢复


@dataclass
class CircuitBreakerConfig:
    """断路器配置"""
    failure_threshold: int = 5  # 失败阈值
    recovery_timeout: float = 60.0  # 恢复超时（秒）
    expected_exception: Type[Exception] = Exception  # 期望的异常类型
    success_threshold: int = 2  # 半开状态下成功阈值
    
    # 监控窗口
    monitoring_window: float = 60.0  # 监控窗口大小（秒）
    
    # 回调函数
    on_open: Optional[Callable[[], None]] = None  # 断路器打开时
    on_close: Optional[Callable[[], None]] = None  # 断路器关闭时
    on_half_open: Optional[Callable[[], None]] = None  # 断路器半开时


class CircuitBreaker:
    """断路器实现"""
    
    def __init__(self, name: str, config: CircuitBreakerConfig):
        """
        初始化断路器
        
        Args:
            name: 断路器名称
            config: 断路器配置
        """
        self.name = name
        self.config = config
        self._state = CircuitState.CLOSED
        self._failure_count = 0
        self._success_count = 0
        self._last_failure_time: Optional[float] = None
        self._last_attempt_time: Optional[float] = None
        self._lock = threading.Lock()
        
        # 失败记录（用于计算失败率）
        self._failure_timestamps: List[float] = []
        
        logger.info(f"断路器 '{name}' 已初始化")
    
    @property
    def state(self) -> CircuitState:
        """获取当前状态"""
        with self._lock:
            self._update_state()
            return self._state
    
    def _update_state(self):
        """更新断路器状态（内部方法，需要在锁内调用）"""
        current_time = time.time()
        
        # 清理过期的失败记录
        cutoff_time = current_time - self.config.monitoring_window
        self._failure_timestamps = [
            t for t in self._failure_timestamps if t > cutoff_time
        ]
        
        if self._state == CircuitState.OPEN:
            # 检查是否可以尝试恢复
            if self._last_failure_time and \
               current_time - self._last_failure_time >= self.config.recovery_timeout:
                self._transition_to_half_open()
        
        elif self._state == CircuitState.HALF_OPEN:
            # 检查是否可以完全恢复
            if self._success_count >= self.config.success_threshold:
                self._transition_to_closed()
    
    def _transition_to_open(self):
        """转换到开路状态"""
        if self._state != CircuitState.OPEN:
            logger.warning(f"断路器 '{self.name}' 已打开（失败次数: {self._failure_count}）")
            self._state = CircuitState.OPEN
            self._last_failure_time = time.time()
            
            if self.config.on_open:
                try:
                    self.config.on_open()
                except Exception as e:
                    logger.error(f"执行 on_open 回调失败: {e}")
    
    def _transition_to_closed(self):
        """转换到闭路状态"""
        if self._state != CircuitState.CLOSED:
            logger.info(f"断路器 '{self.name}' 已关闭（恢复正常）")
            self._state = CircuitState.CLOSED
            self._failure_count = 0
            self._success_count = 0
            self._failure_timestamps.clear()
            
            if self.config.on_close:
                try:
                    self.config.on_close()
                except Exception as e:
                    logger.error(f"执行 on_close 回调失败: {e}")
    
    def _transition_to_half_open(self):
        """转换到半开状态"""
        if self._state != CircuitState.HALF_OPEN:
            logger.info(f"断路器 '{self.name}' 进入半开状态（尝试恢复）")
            self._state = CircuitState.HALF_OPEN
            self._success_count = 0
            self._failure_count = 0
            
            if self.config.on_half_open:
                try:
                    self.config.on_half_open()
                except Exception as e:
                    logger.error(f"执行 on_half_open 回调失败: {e}")
    
    def call(self, func: Callable, *args, **kwargs) -> Any:
        """
        通过断路器调用函数
        
        Args:
            func: 要调用的函数
            *args: 函数参数
            **kwargs: 函数关键字参数
            
        Returns:
            函数执行结果
            
        Raises:
            CircuitBreakerOpenError: 断路器开路时
            原始异常: 函数执行失败时
        """
        with self._lock:
            self._update_state()
            
            if self._state == CircuitState.OPEN:
                raise CircuitBreakerOpenError(
                    f"断路器 '{self.name}' 已开路，拒绝请求"
                )
            
            self._last_attempt_time = time.time()
        
        try:
            # 执行函数
            result = func(*args, **kwargs)
            
            # 记录成功
            with self._lock:
                self._record_success()
            
            return result
            
        except self.config.expected_exception as e:
            # 记录失败
            with self._lock:
                self._record_failure()
            raise
    
    async def async_call(self, func: Callable, *args, **kwargs) -> Any:
        """
        通过断路器调用异步函数
        
        Args:
            func: 要调用的异步函数
            *args: 函数参数
            **kwargs: 函数关键字参数
            
        Returns:
            函数执行结果
        """
        with self._lock:
            self._update_state()
            
            if self._state == CircuitState.OPEN:
                raise CircuitBreakerOpenError(
                    f"断路器 '{self.name}' 已开路，拒绝请求"
                )
            
            self._last_attempt_time = time.time()
        
        try:
            # 执行异步函数
            result = await func(*args, **kwargs)
            
            # 记录成功
            with self._lock:
                self._record_success()
            
            return result
            
        except self.config.expected_exception as e:
            # 记录失败
            with self._lock:
                self._record_failure()
            raise
    
    def _record_success(self):
        """记录成功（内部方法，需要在锁内调用）"""
        if self._state == CircuitState.HALF_OPEN:
            self._success_count += 1
            logger.debug(
                f"断路器 '{self.name}' 半开状态成功 "
                f"({self._success_count}/{self.config.success_threshold})"
            )
            
            if self._success_count >= self.config.success_threshold:
                self._transition_to_closed()
    
    def _record_failure(self):
        """记录失败（内部方法，需要在锁内调用）"""
        current_time = time.time()
        self._failure_timestamps.append(current_time)
        self._last_failure_time = current_time
        
        if self._state == CircuitState.CLOSED:
            self._failure_count = len(self._failure_timestamps)
            
            if self._failure_count >= self.config.failure_threshold:
                self._transition_to_open()
        
        elif self._state == CircuitState.HALF_OPEN:
            # 半开状态下失败，立即开路
            self._transition_to_open()
    
    def get_stats(self) -> dict:
        """获取断路器统计信息"""
        with self._lock:
            self._update_state()
            
            # 计算失败率
            failure_rate = 0.0
            if self._failure_timestamps:
                window_size = min(
                    self.config.monitoring_window,
                    time.time() - self._failure_timestamps[0]
                )
                if window_size > 0:
                    failure_rate = len(self._failure_timestamps) / window_size * 60  # 每分钟失败次数
            
            return {
                'name': self.name,
                'state': self._state.value,
                'failure_count': len(self._failure_timestamps),
                'success_count': self._success_count,
                'failure_rate_per_minute': round(failure_rate, 2),
                'last_failure_time': self._last_failure_time,
                'last_attempt_time': self._last_attempt_time
            }
    
    def reset(self):
        """重置断路器"""
        with self._lock:
            logger.info(f"重置断路器 '{self.name}'")
            self._state = CircuitState.CLOSED
            self._failure_count = 0
            self._success_count = 0
            self._failure_timestamps.clear()
            self._last_failure_time = None
            self._last_attempt_time = None


class CircuitBreakerOpenError(Exception):
    """断路器开路异常"""
    pass


def circuit_breaker(
    name: str,
    failure_threshold: int = 5,
    recovery_timeout: float = 60.0,
    expected_exception: Type[Exception] = Exception,
    **kwargs
):
    """
    断路器装饰器
    
    Args:
        name: 断路器名称
        failure_threshold: 失败阈值
        recovery_timeout: 恢复超时
        expected_exception: 期望的异常类型
        **kwargs: 其他配置参数
        
    使用示例：
        @circuit_breaker("database", failure_threshold=3, recovery_timeout=30)
        async def query_database():
            # 可能失败的数据库操作
            pass
    """
    # 全局断路器注册表
    _breakers = {}
    
    def decorator(func):
        # 创建或获取断路器
        if name not in _breakers:
            config = CircuitBreakerConfig(
                failure_threshold=failure_threshold,
                recovery_timeout=recovery_timeout,
                expected_exception=expected_exception,
                **kwargs
            )
            _breakers[name] = CircuitBreaker(name, config)
        
        breaker = _breakers[name]
        
        @wraps(func)
        async def async_wrapper(*args, **func_kwargs):
            return await breaker.async_call(func, *args, **func_kwargs)
        
        @wraps(func)
        def sync_wrapper(*args, **func_kwargs):
            return breaker.call(func, *args, **func_kwargs)
        
        # 添加获取断路器的方法
        wrapper = async_wrapper if asyncio.iscoroutinefunction(func) else sync_wrapper
        wrapper.breaker = breaker
        
        return wrapper
    
    return decorator


# 全局断路器管理器
class CircuitBreakerManager:
    """断路器管理器"""
    
    def __init__(self):
        self._breakers: dict[str, CircuitBreaker] = {}
        self._lock = threading.Lock()
    
    def register(self, breaker: CircuitBreaker):
        """注册断路器"""
        with self._lock:
            self._breakers[breaker.name] = breaker
    
    def get(self, name: str) -> Optional[CircuitBreaker]:
        """获取断路器"""
        return self._breakers.get(name)
    
    def get_all_stats(self) -> List[dict]:
        """获取所有断路器状态"""
        with self._lock:
            return [breaker.get_stats() for breaker in self._breakers.values()]
    
    def reset_all(self):
        """重置所有断路器"""
        with self._lock:
            for breaker in self._breakers.values():
                breaker.reset()


# 全局断路器管理器实例
breaker_manager = CircuitBreakerManager()


if __name__ == "__main__":
    # 测试代码
    import random
    
    # 设置日志
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # 模拟不稳定的服务
    failure_count = 0
    
    @circuit_breaker("test_service", failure_threshold=3, recovery_timeout=5)
    async def unstable_service():
        global failure_count
        failure_count += 1
        
        # 前3次失败，之后随机
        if failure_count <= 3 or random.random() < 0.3:
            raise ConnectionError("服务不可用")
        
        return "服务调用成功"
    
    # 测试断路器
    async def test_circuit_breaker():
        for i in range(20):
            try:
                result = await unstable_service()
                logger.info(f"调用 {i+1}: {result}")
            except CircuitBreakerOpenError as e:
                logger.warning(f"调用 {i+1}: {e}")
            except Exception as e:
                logger.error(f"调用 {i+1}: {e}")
            
            # 获取断路器状态
            stats = unstable_service.breaker.get_stats()
            logger.info(f"断路器状态: {stats}")
            
            await asyncio.sleep(1)
    
    # 运行测试
    asyncio.run(test_circuit_breaker())