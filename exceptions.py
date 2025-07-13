#!/usr/bin/env python3
"""
Sage MCP 异常层次结构
提供清晰的异常分类，便于错误处理和调试
"""

from typing import Optional, Dict, Any


# 为了向后兼容，创建别名
class SageMemoryError(Exception):
    """Sage记忆系统通用错误（向后兼容）"""
    pass


class DatabaseError(Exception):
    """数据库错误（向后兼容）"""
    pass


class SageBaseException(Exception):
    """Sage MCP 基础异常类"""
    
    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(message)
        self.message = message
        self.details = details or {}
        
    def __str__(self):
        if self.details:
            detail_str = ", ".join(f"{k}={v}" for k, v in self.details.items())
            return f"{self.message} ({detail_str})"
        return self.message


class ConfigurationError(SageBaseException):
    """配置相关错误"""
    
    def __init__(self, message: str, config_key: Optional[str] = None, **kwargs):
        details = {"config_key": config_key} if config_key else {}
        details.update(kwargs)
        super().__init__(message, details)


class MemoryProviderError(SageBaseException):
    """记忆提供者相关错误"""
    
    def __init__(self, message: str, provider_type: Optional[str] = None, **kwargs):
        details = {"provider_type": provider_type} if provider_type else {}
        details.update(kwargs)
        super().__init__(message, details)


class DatabaseConnectionError(MemoryProviderError):
    """数据库连接错误"""
    
    def __init__(self, message: str, db_url: Optional[str] = None, **kwargs):
        super().__init__(message, provider_type="database", db_url=db_url, **kwargs)


class EmbeddingServiceError(MemoryProviderError):
    """嵌入服务错误"""
    
    def __init__(self, message: str, service: Optional[str] = None, **kwargs):
        super().__init__(message, provider_type="embedding", service=service, **kwargs)


class ClaudeExecutionError(SageBaseException):
    """Claude 执行相关错误"""
    
    def __init__(self, message: str, command: Optional[str] = None, 
                 return_code: Optional[int] = None, **kwargs):
        details = {}
        if command:
            details["command"] = command
        if return_code is not None:
            details["return_code"] = return_code
        details.update(kwargs)
        super().__init__(message, details)


class ClaudeNotFoundError(ClaudeExecutionError):
    """Claude CLI 未找到错误"""
    
    def __init__(self, searched_paths: Optional[list] = None):
        message = "未找到 Claude CLI"
        super().__init__(message, searched_paths=searched_paths)


class PlatformCompatibilityError(SageBaseException):
    """平台兼容性错误"""
    
    def __init__(self, message: str, platform: Optional[str] = None, 
                 required_platform: Optional[str] = None, **kwargs):
        details = {}
        if platform:
            details["platform"] = platform
        if required_platform:
            details["required_platform"] = required_platform
        details.update(kwargs)
        super().__init__(message, details)


class AsyncRuntimeError(SageBaseException):
    """异步运行时错误"""
    
    def __init__(self, message: str, loop_state: Optional[str] = None, **kwargs):
        details = {"loop_state": loop_state} if loop_state else {}
        details.update(kwargs)
        super().__init__(message, details)


class ResourceManagementError(SageBaseException):
    """资源管理错误"""
    
    def __init__(self, message: str, resource_type: Optional[str] = None,
                 resource_count: Optional[int] = None, **kwargs):
        details = {}
        if resource_type:
            details["resource_type"] = resource_type
        if resource_count is not None:
            details["resource_count"] = resource_count
        details.update(kwargs)
        super().__init__(message, details)


class MemoryLimitExceededError(ResourceManagementError):
    """内存限制超出错误"""
    
    def __init__(self, used_memory: int, limit: int):
        message = f"内存使用超出限制: {used_memory}/{limit} bytes"
        super().__init__(message, resource_type="memory", 
                        used=used_memory, limit=limit)


class EnhancementError(SageBaseException):
    """提示增强相关错误"""
    
    def __init__(self, message: str, enhancement_level: Optional[str] = None, **kwargs):
        details = {"enhancement_level": enhancement_level} if enhancement_level else {}
        details.update(kwargs)
        super().__init__(message, details)


class RetrievalError(SageBaseException):
    """检索相关错误"""
    
    def __init__(self, message: str, query: Optional[str] = None,
                 strategy: Optional[str] = None, **kwargs):
        details = {}
        if query:
            details["query"] = query
        if strategy:
            details["strategy"] = strategy
        details.update(kwargs)
        super().__init__(message, details)


class ValidationError(SageBaseException):
    """输入验证错误"""
    
    def __init__(self, message: str, field: Optional[str] = None,
                 value: Optional[Any] = None, **kwargs):
        details = {}
        if field:
            details["field"] = field
        if value is not None:
            details["value"] = repr(value)
        details.update(kwargs)
        super().__init__(message, details)


class TimeoutError(SageBaseException):
    """操作超时错误"""
    
    def __init__(self, message: str, operation: Optional[str] = None,
                 timeout_seconds: Optional[float] = None, **kwargs):
        details = {}
        if operation:
            details["operation"] = operation
        if timeout_seconds is not None:
            details["timeout_seconds"] = timeout_seconds
        details.update(kwargs)
        super().__init__(message, details)


# 便捷函数
def handle_exception(exc: Exception, context: str = "") -> str:
    """统一的异常处理函数"""
    if isinstance(exc, SageBaseException):
        error_msg = f"[{exc.__class__.__name__}] {exc}"
    else:
        error_msg = f"[{exc.__class__.__name__}] {str(exc)}"
    
    if context:
        error_msg = f"{context}: {error_msg}"
    
    return error_msg