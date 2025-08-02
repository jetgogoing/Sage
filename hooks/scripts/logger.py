#!/usr/bin/env python3
"""
结构化日志模块
为 Sage Hooks 提供统一的结构化日志功能

特性：
1. JSON 格式的结构化日志输出
2. 多级日志等级支持
3. 自动日志轮转和归档
4. 敏感信息过滤
5. 性能指标记录
6. 分布式追踪支持
"""

import json
import logging
import logging.handlers
import os
import re
import time
import uuid
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, Optional, Union, List
import threading
import traceback

from config_manager import get_config
from security_utils import path_validator, SecurityError


class SensitiveDataFilter:
    """敏感数据过滤器"""
    
    # 常见敏感信息的正则表达式模式
    SENSITIVE_PATTERNS = [
        (r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b', '[EMAIL]'),  # 邮箱
        (r'\b\d{4}[-\s]?\d{4}[-\s]?\d{4}[-\s]?\d{4}\b', '[CARD]'),  # 信用卡号
        (r'\b\d{3}[-\s]?\d{2}[-\s]?\d{4}\b', '[SSN]'),  # 美国社会保障号
        (r'\b(?:sk-|pk_|rk_)[a-zA-Z0-9]{32,}\b', '[API_KEY]'),  # API 密钥
        (r'\b[A-Fa-f0-9]{64}\b', '[HASH]'),  # SHA256 哈希
        (r'\b(?:password|passwd|pwd|secret|key|token)["\']?\s*[:=]\s*["\']?([^\s"\']+)', '[CREDENTIAL]'),  # 密码字段
    ]
    
    @classmethod
    def sanitize(cls, text: str) -> str:
        """清理文本中的敏感信息"""
        if not isinstance(text, str):
            return str(text)
        
        sanitized = text
        for pattern, replacement in cls.SENSITIVE_PATTERNS:
            sanitized = re.sub(pattern, replacement, sanitized, flags=re.IGNORECASE)
        
        return sanitized


class StructuredFormatter(logging.Formatter):
    """结构化 JSON 日志格式化器"""
    
    def __init__(self, sanitize_enabled: bool = True):
        super().__init__()
        self.sanitize_enabled = sanitize_enabled
    
    def format(self, record: logging.LogRecord) -> str:
        """格式化日志记录为 JSON"""
        # 基础日志结构
        log_entry = {
            'timestamp': datetime.fromtimestamp(record.created).isoformat() + 'Z',
            'level': record.levelname,
            'logger': record.name,
            'message': record.getMessage(),
            'module': record.module,
            'function': record.funcName,
            'line': record.lineno,
            'thread_id': record.thread,
            'process_id': record.process
        }
        
        # 添加异常信息
        if record.exc_info:
            log_entry['exception'] = {
                'type': record.exc_info[0].__name__ if record.exc_info[0] else None,
                'message': str(record.exc_info[1]) if record.exc_info[1] else None,
                'traceback': traceback.format_exception(*record.exc_info)
            }
        
        # 添加自定义字段
        extra_fields = {}
        for key, value in record.__dict__.items():
            if key not in ['name', 'msg', 'args', 'levelname', 'levelno', 'pathname', 
                          'filename', 'module', 'exc_info', 'exc_text', 'stack_info',
                          'lineno', 'funcName', 'created', 'msecs', 'relativeCreated',
                          'thread', 'threadName', 'processName', 'process', 'getMessage']:
                extra_fields[key] = value
        
        if extra_fields:
            log_entry['extra'] = extra_fields
        
        # 敏感信息过滤
        if self.sanitize_enabled:
            log_entry = self._sanitize_log_entry(log_entry)
        
        return json.dumps(log_entry, ensure_ascii=False, default=str)
    
    def _sanitize_log_entry(self, log_entry: Dict[str, Any]) -> Dict[str, Any]:
        """递归清理日志条目中的敏感信息"""
        if isinstance(log_entry, dict):
            return {k: self._sanitize_log_entry(v) for k, v in log_entry.items()}
        elif isinstance(log_entry, list):
            return [self._sanitize_log_entry(item) for item in log_entry]
        elif isinstance(log_entry, str):
            return SensitiveDataFilter.sanitize(log_entry)
        else:
            return log_entry


class PerformanceLogger:
    """性能日志记录器"""
    
    def __init__(self, logger: logging.Logger):
        self.logger = logger
        self._metrics = {}
    
    def start_timer(self, operation: str) -> str:
        """开始计时"""
        timer_id = str(uuid.uuid4())
        self._metrics[timer_id] = {
            'operation': operation,
            'start_time': time.time(),
            'thread_id': threading.get_ident()
        }
        return timer_id
    
    def end_timer(self, timer_id: str, **extra_data) -> float:
        """结束计时并记录性能指标"""
        if timer_id not in self._metrics:
            self.logger.warning(f"Timer {timer_id} not found")
            return 0.0
        
        metric = self._metrics.pop(timer_id)
        duration = time.time() - metric['start_time']
        
        # 记录性能日志
        self.logger.info(
            f"Performance: {metric['operation']} completed",
            extra={
                'performance': {
                    'operation': metric['operation'],
                    'duration_ms': round(duration * 1000, 2),
                    'thread_id': metric['thread_id'],
                    **extra_data
                }
            }
        )
        
        return duration
    
    def record_metric(self, metric_name: str, value: Union[int, float], unit: str = '', **extra_data):
        """记录自定义指标"""
        self.logger.info(
            f"Metric: {metric_name} = {value}{unit}",
            extra={
                'metric': {
                    'name': metric_name,
                    'value': value,
                    'unit': unit,
                    'timestamp': time.time(),
                    **extra_data
                }
            }
        )


class SageLogger:
    """Sage Hooks 统一日志管理器"""
    
    def __init__(self, name: str, config_section: str = 'logging'):
        self.name = name
        self.config_section = config_section
        self._logger = None
        self._performance_logger = None
        self._setup_logger()
    
    def _setup_logger(self):
        """设置日志器"""
        # 获取配置
        log_level = get_config(self.config_section, 'level', 'INFO')
        file_enabled = get_config(self.config_section, 'file_enabled', True)
        console_enabled = get_config(self.config_section, 'console_enabled', True)
        max_file_size = get_config(self.config_section, 'max_file_size', '10MB')
        backup_count = get_config(self.config_section, 'backup_count', 5)
        sanitize_enabled = get_config('security', 'sanitize_logs', True)
        
        # 创建日志器
        self._logger = logging.getLogger(self.name)
        self._logger.setLevel(getattr(logging, log_level.upper()))
        
        # 清除现有处理器（避免重复添加）
        self._logger.handlers.clear()
        
        # 创建格式化器
        formatter = StructuredFormatter(sanitize_enabled=sanitize_enabled)
        
        # 文件处理器
        if file_enabled:
            try:
                log_dir = Path("/Users/jet/Sage/logs/Hooks")
                log_dir.mkdir(exist_ok=True)
                
                # 验证日志目录路径安全性
                validated_log_dir = path_validator.validate_path(str(log_dir))
                log_file = validated_log_dir / f"{self.name}.log"
                
                # 验证日志文件路径
                validated_log_file = path_validator.validate_path(str(log_file))
            except SecurityError as e:
                # 如果路径验证失败，使用临时目录
                import tempfile
                log_dir = Path(tempfile.gettempdir()) / "sage_hooks_logs"
                log_dir.mkdir(exist_ok=True)
                log_file = log_dir / f"{self.name}.log"
                self._logger.warning(f"Log path validation failed, using temp directory: {e}")
            
            # 解析文件大小配置
            size_bytes = self._parse_size(max_file_size)
            
            file_handler = logging.handlers.RotatingFileHandler(
                str(log_file),
                maxBytes=size_bytes,
                backupCount=backup_count,
                encoding='utf-8'
            )
            file_handler.setFormatter(formatter)
            self._logger.addHandler(file_handler)
        
        # 控制台处理器
        if console_enabled:
            console_handler = logging.StreamHandler()
            console_handler.setFormatter(formatter)
            self._logger.addHandler(console_handler)
        
        # 创建性能日志器
        self._performance_logger = PerformanceLogger(self._logger)
    
    def _parse_size(self, size_str: str) -> int:
        """解析大小字符串为字节数"""
        size_str = size_str.upper()
        if size_str.endswith('KB'):
            return int(size_str[:-2]) * 1024
        elif size_str.endswith('MB'):
            return int(size_str[:-2]) * 1024 * 1024
        elif size_str.endswith('GB'):
            return int(size_str[:-2]) * 1024 * 1024 * 1024
        else:
            return int(size_str)
    
    @property
    def logger(self) -> logging.Logger:
        """获取原生日志器"""
        return self._logger
    
    @property
    def perf(self) -> PerformanceLogger:
        """获取性能日志器"""
        return self._performance_logger
    
    def debug(self, message: str, **extra):
        """记录 DEBUG 级别日志"""
        self._logger.debug(message, extra=extra)
    
    def info(self, message: str, **extra):
        """记录 INFO 级别日志"""
        self._logger.info(message, extra=extra)
    
    def warning(self, message: str, **extra):
        """记录 WARNING 级别日志"""
        self._logger.warning(message, extra=extra)
    
    def error(self, message: str, **extra):
        """记录 ERROR 级别日志"""
        self._logger.error(message, extra=extra)
    
    def critical(self, message: str, **extra):
        """记录 CRITICAL 级别日志"""
        self._logger.critical(message, extra=extra)
    
    def exception(self, message: str, **extra):
        """记录异常日志"""
        self._logger.exception(message, extra=extra)
    
    def log_hook_start(self, hook_type: str, session_id: str, **extra):
        """记录 Hook 开始执行"""
        self.info(
            f"{hook_type} hook started",
            extra={
                'hook': {
                    'type': hook_type,
                    'session_id': session_id,
                    'start_time': time.time(),
                    **extra
                }
            }
        )
    
    def log_hook_end(self, hook_type: str, session_id: str, success: bool, duration: float, **extra):
        """记录 Hook 执行结束"""
        level = self.info if success else self.error
        level(
            f"{hook_type} hook {'completed' if success else 'failed'}",
            extra={
                'hook': {
                    'type': hook_type,
                    'session_id': session_id,
                    'success': success,
                    'duration_ms': round(duration * 1000, 2),
                    'end_time': time.time(),
                    **extra
                }
            }
        )
    
    def log_mcp_call(self, tool_name: str, success: bool, duration: float, **extra):
        """记录 MCP 工具调用"""
        level = self.info if success else self.error
        level(
            f"MCP call {tool_name} {'succeeded' if success else 'failed'}",
            extra={
                'mcp': {
                    'tool': tool_name,
                    'success': success,
                    'duration_ms': round(duration * 1000, 2),
                    'timestamp': time.time(),
                    **extra
                }
            }
        )


# 全局日志器实例缓存
_logger_instances = {}
_lock = threading.Lock()


def get_logger(name: str, config_section: str = 'logging') -> SageLogger:
    """获取日志器实例（单例模式）"""
    key = f"{name}:{config_section}"
    
    if key not in _logger_instances:
        with _lock:
            if key not in _logger_instances:
                _logger_instances[key] = SageLogger(name, config_section)
    
    return _logger_instances[key]


class LogContext:
    """日志上下文管理器，用于自动记录操作开始和结束"""
    
    def __init__(self, logger: SageLogger, operation: str, **extra_data):
        self.logger = logger
        self.operation = operation
        self.extra_data = extra_data
        self.timer_id = None
        self.start_time = None
    
    def __enter__(self):
        self.start_time = time.time()
        self.timer_id = self.logger.perf.start_timer(self.operation)
        self.logger.info(f"Starting {self.operation}", extra=self.extra_data)
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        duration = time.time() - self.start_time
        success = exc_type is None
        
        if success:
            self.logger.perf.end_timer(self.timer_id, **self.extra_data)
            self.logger.info(f"Completed {self.operation}", extra={
                'duration_ms': round(duration * 1000, 2),
                **self.extra_data
            })
        else:
            self.logger.error(f"Failed {self.operation}: {exc_val}", extra={
                'duration_ms': round(duration * 1000, 2),
                'error_type': exc_type.__name__ if exc_type else None,
                **self.extra_data
            })


if __name__ == "__main__":
    # 测试日志功能
    print("=== Sage Logger 测试 ===")
    
    # 创建测试日志器
    logger = get_logger("test_logger")
    
    # 测试各种日志级别
    logger.debug("这是一个调试消息")
    logger.info("这是一个信息消息", user_id="test_user", operation="test")
    logger.warning("这是一个警告消息")
    logger.error("这是一个错误消息")
    
    # 测试性能日志
    timer_id = logger.perf.start_timer("test_operation")
    time.sleep(0.1)  # 模拟操作
    logger.perf.end_timer(timer_id, input_size=100, output_size=50)
    
    # 测试自定义指标
    logger.perf.record_metric("memory_usage", 85.5, "MB", component="enhancer")
    
    # 测试 Hook 日志
    logger.log_hook_start("UserPromptSubmit", "session_123", prompt_length=150)
    logger.log_hook_end("UserPromptSubmit", "session_123", True, 1.25, output_length=200)
    
    # 测试 MCP 调用日志
    logger.log_mcp_call("generate_prompt", True, 0.8, input_tokens=50, output_tokens=30)
    
    # 测试上下文管理器
    with LogContext(logger, "complex_operation", task_id="task_456"):
        time.sleep(0.05)  # 模拟操作
    
    # 测试异常处理
    try:
        raise ValueError("这是一个测试异常")
    except Exception:
        logger.exception("捕获到异常")
    
    print("✓ 日志测试完成")
    print("检查日志文件: /Users/jet/Sage/logs/Hooks/test_logger.log")