#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Resilience 模块 - 提供系统弹性和容错能力
包括重试机制、断路器、健康检查等
"""

from .retry_strategy import (
    RetryConfig,
    RetryManager,
    RetryStrategy,
    retry,
    DEFAULT_RETRY_CONFIG,
    DATABASE_RETRY_CONFIG,
    NETWORK_RETRY_CONFIG
)

from .circuit_breaker import (
    CircuitBreaker,
    CircuitBreakerConfig,
    CircuitBreakerOpenError,
    CircuitState,
    circuit_breaker,
    breaker_manager
)

__all__ = [
    # 重试相关
    'RetryConfig',
    'RetryManager', 
    'RetryStrategy',
    'retry',
    'DEFAULT_RETRY_CONFIG',
    'DATABASE_RETRY_CONFIG',
    'NETWORK_RETRY_CONFIG',
    # 断路器相关
    'CircuitBreaker',
    'CircuitBreakerConfig',
    'CircuitBreakerOpenError',
    'CircuitState',
    'circuit_breaker',
    'breaker_manager'
]