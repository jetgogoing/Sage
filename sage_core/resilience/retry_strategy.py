#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
重试策略模块 - 提供灵活的重试机制
支持指数退避、最大重试次数、自定义重试条件等
"""
import asyncio
import random
import time
import logging
from typing import TypeVar, Callable, Optional, Union, List, Type, Any
from functools import wraps
from dataclasses import dataclass
from enum import Enum

logger = logging.getLogger(__name__)

T = TypeVar('T')


class RetryStrategy(Enum):
    """重试策略类型"""
    FIXED = "fixed"  # 固定延迟
    LINEAR = "linear"  # 线性增长
    EXPONENTIAL = "exponential"  # 指数退避
    FIBONACCI = "fibonacci"  # 斐波那契数列


@dataclass
class RetryConfig:
    """重试配置"""
    max_attempts: int = 3  # 最大重试次数
    initial_delay: float = 1.0  # 初始延迟（秒）
    max_delay: float = 60.0  # 最大延迟（秒）
    exponential_base: float = 2.0  # 指数基数
    jitter: bool = True  # 是否添加随机抖动
    strategy: RetryStrategy = RetryStrategy.EXPONENTIAL  # 重试策略
    
    # 可重试的异常类型
    retryable_exceptions: List[Type[Exception]] = None
    
    # 不可重试的异常类型（优先级高于可重试）
    non_retryable_exceptions: List[Type[Exception]] = None
    
    # 自定义重试条件
    retry_condition: Optional[Callable[[Exception], bool]] = None
    
    # 重试前的回调
    before_retry: Optional[Callable[[int, Exception], None]] = None
    
    # 所有重试失败后的回调
    on_exhausted: Optional[Callable[[Exception], None]] = None
    
    def __post_init__(self):
        """初始化后处理"""
        if self.retryable_exceptions is None:
            # 默认重试所有异常
            self.retryable_exceptions = [Exception]
        
        if self.non_retryable_exceptions is None:
            self.non_retryable_exceptions = []


class RetryManager:
    """重试管理器"""
    
    def __init__(self, config: RetryConfig):
        """
        初始化重试管理器
        
        Args:
            config: 重试配置
        """
        self.config = config
        self._fibonacci_cache = [0, 1]  # 斐波那契数列缓存
    
    def should_retry(self, exception: Exception) -> bool:
        """
        判断是否应该重试
        
        Args:
            exception: 发生的异常
            
        Returns:
            是否应该重试
        """
        # 检查不可重试的异常
        for exc_type in self.config.non_retryable_exceptions:
            if isinstance(exception, exc_type):
                return False
        
        # 检查自定义重试条件
        if self.config.retry_condition:
            if not self.config.retry_condition(exception):
                return False
        
        # 检查可重试的异常
        for exc_type in self.config.retryable_exceptions:
            if isinstance(exception, exc_type):
                return True
        
        return False
    
    def get_delay(self, attempt: int) -> float:
        """
        获取重试延迟时间
        
        Args:
            attempt: 当前重试次数（从1开始）
            
        Returns:
            延迟时间（秒）
        """
        if self.config.strategy == RetryStrategy.FIXED:
            delay = self.config.initial_delay
        
        elif self.config.strategy == RetryStrategy.LINEAR:
            delay = self.config.initial_delay * attempt
        
        elif self.config.strategy == RetryStrategy.EXPONENTIAL:
            delay = self.config.initial_delay * (self.config.exponential_base ** (attempt - 1))
        
        elif self.config.strategy == RetryStrategy.FIBONACCI:
            delay = self.config.initial_delay * self._get_fibonacci(attempt)
        
        else:
            delay = self.config.initial_delay
        
        # 限制最大延迟
        delay = min(delay, self.config.max_delay)
        
        # 添加随机抖动
        if self.config.jitter:
            delay = delay * (0.5 + random.random() * 0.5)
        
        return delay
    
    def _get_fibonacci(self, n: int) -> int:
        """获取斐波那契数列第n项"""
        while len(self._fibonacci_cache) <= n:
            self._fibonacci_cache.append(
                self._fibonacci_cache[-1] + self._fibonacci_cache[-2]
            )
        return self._fibonacci_cache[n]
    
    async def execute_with_retry(self, func: Callable, *args, **kwargs) -> Any:
        """
        执行函数并自动重试
        
        Args:
            func: 要执行的函数（可以是异步或同步函数）
            *args: 函数参数
            **kwargs: 函数关键字参数
            
        Returns:
            函数执行结果
            
        Raises:
            最后一次重试的异常
        """
        last_exception = None
        
        for attempt in range(1, self.config.max_attempts + 1):
            try:
                # 执行函数
                if asyncio.iscoroutinefunction(func):
                    result = await func(*args, **kwargs)
                else:
                    result = func(*args, **kwargs)
                
                # 成功则返回结果
                return result
                
            except Exception as e:
                last_exception = e
                
                # 判断是否应该重试
                if not self.should_retry(e) or attempt == self.config.max_attempts:
                    # 不重试或已达最大次数
                    if self.config.on_exhausted and attempt == self.config.max_attempts:
                        self.config.on_exhausted(e)
                    raise
                
                # 计算延迟
                delay = self.get_delay(attempt)
                
                # 执行重试前回调
                if self.config.before_retry:
                    self.config.before_retry(attempt, e)
                
                logger.warning(
                    f"第 {attempt}/{self.config.max_attempts} 次执行失败: {e}, "
                    f"{delay:.2f}秒后重试..."
                )
                
                # 等待
                await asyncio.sleep(delay)
        
        # 理论上不会到达这里
        raise last_exception


def retry(
    max_attempts: int = 3,
    initial_delay: float = 1.0,
    max_delay: float = 60.0,
    strategy: RetryStrategy = RetryStrategy.EXPONENTIAL,
    retryable_exceptions: List[Type[Exception]] = None,
    **kwargs
):
    """
    重试装饰器
    
    Args:
        max_attempts: 最大重试次数
        initial_delay: 初始延迟
        max_delay: 最大延迟
        strategy: 重试策略
        retryable_exceptions: 可重试的异常类型
        **kwargs: 其他 RetryConfig 参数
        
    使用示例：
        @retry(max_attempts=3, initial_delay=1.0)
        async def flaky_function():
            # 可能失败的操作
            pass
    """
    def decorator(func):
        @wraps(func)
        async def async_wrapper(*args, **func_kwargs):
            config = RetryConfig(
                max_attempts=max_attempts,
                initial_delay=initial_delay,
                max_delay=max_delay,
                strategy=strategy,
                retryable_exceptions=retryable_exceptions,
                **kwargs
            )
            manager = RetryManager(config)
            return await manager.execute_with_retry(func, *args, **func_kwargs)
        
        @wraps(func)
        def sync_wrapper(*args, **func_kwargs):
            config = RetryConfig(
                max_attempts=max_attempts,
                initial_delay=initial_delay,
                max_delay=max_delay,
                strategy=strategy,
                retryable_exceptions=retryable_exceptions,
                **kwargs
            )
            manager = RetryManager(config)
            # 在同步函数中运行异步重试
            loop = asyncio.get_event_loop()
            return loop.run_until_complete(
                manager.execute_with_retry(func, *args, **func_kwargs)
            )
        
        # 根据函数类型返回相应的包装器
        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        else:
            return sync_wrapper
    
    return decorator


# 预定义的重试配置
DEFAULT_RETRY_CONFIG = RetryConfig()

# 数据库操作重试配置
DATABASE_RETRY_CONFIG = RetryConfig(
    max_attempts=5,
    initial_delay=0.5,
    max_delay=30.0,
    strategy=RetryStrategy.EXPONENTIAL,
    retryable_exceptions=[
        ConnectionError,
        TimeoutError,
    ]
)

# 网络请求重试配置
NETWORK_RETRY_CONFIG = RetryConfig(
    max_attempts=3,
    initial_delay=1.0,
    max_delay=10.0,
    strategy=RetryStrategy.EXPONENTIAL,
    exponential_base=2.0,
    jitter=True
)


if __name__ == "__main__":
    # 测试代码
    import random
    
    # 设置日志
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # 模拟可能失败的函数
    call_count = 0
    
    @retry(max_attempts=3, initial_delay=1.0)
    async def flaky_function():
        global call_count
        call_count += 1
        
        if call_count < 3:
            raise ConnectionError(f"连接失败 (尝试 {call_count})")
        
        return f"成功! (第 {call_count} 次尝试)"
    
    # 测试重试机制
    async def test_retry():
        try:
            result = await flaky_function()
            logger.info(f"函数执行结果: {result}")
        except Exception as e:
            logger.error(f"函数最终失败: {e}")
    
    # 运行测试
    asyncio.run(test_retry())