#!/usr/bin/env python3
"""
Sage MCP 记忆接口定义
为记忆系统提供抽象接口，支持不同实现和版本
"""

from abc import ABC, abstractmethod
from typing import List, Dict, Optional, Any
from dataclasses import dataclass
import logging

# 尝试导入错误恢复模块
try:
    from error_recovery import (
        retry_with_backoff,
        db_retry_policy,
        monitored_operation,
        graceful_degradation
    )
    ERROR_RECOVERY_AVAILABLE = True
except ImportError:
    ERROR_RECOVERY_AVAILABLE = False
    # 定义空装饰器
    def retry_with_backoff(policy=None):
        def decorator(func):
            return func
        return decorator
    
    def monitored_operation(name):
        class DummyContext:
            def __enter__(self):
                return self
            def __exit__(self, *args):
                pass
        return DummyContext()
    
    def graceful_degradation(fallback):
        def decorator(func):
            return func
        return decorator
    
    db_retry_policy = None

logger = logging.getLogger('SageMemoryInterface')


@dataclass
class MemorySearchResult:
    """记忆搜索结果"""
    content: str
    role: str  # 'user' or 'assistant'
    score: float
    metadata: Dict[str, Any]
    

class IMemoryProvider(ABC):
    """记忆提供者接口"""
    
    @abstractmethod
    def get_context(self, query: str, **kwargs) -> str:
        """
        获取与查询相关的上下文
        
        Args:
            query: 用户查询
            **kwargs: 额外参数
            
        Returns:
            相关上下文字符串
        """
        pass
    
    @abstractmethod
    def save_conversation(self, user_prompt: str, assistant_response: str, metadata: Optional[Dict] = None):
        """
        保存对话轮次
        
        Args:
            user_prompt: 用户输入
            assistant_response: 助手响应
            metadata: 额外元数据
        """
        pass
    
    @abstractmethod
    def search_memory(self, query: str, n: int = 5) -> List[MemorySearchResult]:
        """
        搜索相关记忆
        
        Args:
            query: 搜索查询
            n: 返回结果数量
            
        Returns:
            搜索结果列表
        """
        pass
    
    @abstractmethod
    def get_memory_stats(self) -> Dict[str, Any]:
        """
        获取记忆统计信息
        
        Returns:
            统计信息字典
        """
        pass
    
    @abstractmethod
    def clear_all_memories(self) -> int:
        """
        清除所有记忆
        
        Returns:
            清除的记忆数量
        """
        pass
    
    @abstractmethod
    def add_memory(self, content: str, metadata: Optional[Dict[str, Any]] = None):
        """
        添加单条记忆
        
        Args:
            content: 记忆内容
            metadata: 元数据
        """
        pass
    
    # 阶段2需要的新接口
    def retrieve_relevant_context(
        self, 
        query: str, 
        num_results: int = 5,
        similarity_threshold: float = 0.7,
        time_decay: bool = True,
        max_age_days: int = 30,
        **kwargs
    ) -> List[Dict[str, Any]]:
        """
        智能检索相关上下文（阶段2接口）
        
        Args:
            query: 当前查询
            num_results: 返回结果数量
            similarity_threshold: 相似度阈值
            time_decay: 是否应用时间衰减
            max_age_days: 最大历史天数
            **kwargs: 其他参数
            
        Returns:
            相关上下文列表
        """
        # 默认实现：调用基础搜索并过滤
        results = self.search_memory(query, n=num_results * 2)
        filtered_results = []
        
        for result in results:
            if result.score >= similarity_threshold:
                filtered_results.append({
                    'content': result.content,
                    'role': result.role,
                    'score': result.score,
                    'metadata': result.metadata,
                    'final_score': result.score  # 简化实现，不应用时间衰减
                })
        
        return filtered_results[:num_results]
    
    def format_context_for_prompt(self, contexts: List[Dict[str, Any]], max_tokens: int = 2000) -> str:
        """
        格式化上下文为提示文本（阶段2接口）
        
        Args:
            contexts: 检索到的上下文列表
            max_tokens: 最大token数
            
        Returns:
            格式化的上下文字符串
        """
        if not contexts:
            return ""
        
        formatted_parts = []
        estimated_tokens = 0
        
        for ctx in contexts:
            role = ctx.get('role', 'unknown')
            content = ctx.get('content', '')
            
            # 格式化单条记录
            if role == 'user':
                formatted = f"[用户]: {content}"
            elif role == 'assistant':
                formatted = f"[助手]: {content}"
            else:
                formatted = f"[{role}]: {content}"
            
            # 粗略估计 tokens（4个字符约等于1个token）
            part_tokens = len(formatted) // 4
            
            if estimated_tokens + part_tokens > max_tokens:
                # 如果超出限制，截断
                remaining_tokens = max_tokens - estimated_tokens
                if remaining_tokens > 100:
                    max_chars = remaining_tokens * 4
                    formatted = formatted[:max_chars] + "..."
                    formatted_parts.append(formatted)
                break
            
            formatted_parts.append(formatted)
            estimated_tokens += part_tokens
        
        return "\n".join(formatted_parts)


class MemoryProviderV1(IMemoryProvider):
    """
    记忆提供者V1实现（适配现有memory.py）
    """
    
    def __init__(self):
        self._memory_module = None
        self._import_error = None
        
    @property
    def memory(self):
        """延迟导入memory模块"""
        if self._memory_module is None and self._import_error is None:
            try:
                import memory
                self._memory_module = memory
            except ImportError as e:
                self._import_error = e
                logger.error(f"无法导入memory模块: {e}")
                
        if self._import_error:
            raise self._import_error
            
        return self._memory_module
    
    @retry_with_backoff(policy=db_retry_policy)
    def get_context(self, query: str, **kwargs) -> str:
        """获取上下文"""
        with monitored_operation("memory_get_context"):
            try:
                return self.memory.get_context(query)
            except Exception as e:
                logger.error(f"获取上下文失败: {e}")
                return ""
    
    @retry_with_backoff(policy=db_retry_policy)
    def save_conversation(self, user_prompt: str, assistant_response: str, metadata: Optional[Dict] = None):
        """保存对话"""
        with monitored_operation("memory_save_conversation"):
            try:
                self.memory.save_conversation_turn(user_prompt, assistant_response, metadata)
            except Exception as e:
                logger.error(f"保存对话失败: {e}")
    
    @retry_with_backoff(policy=db_retry_policy)
    @graceful_degradation(lambda *args, **kwargs: [])
    def search_memory(self, query: str, n: int = 5) -> List[MemorySearchResult]:
        """搜索记忆"""
        with monitored_operation("memory_search"):
            try:
                results = self.memory.search_memory(query, n)
                
                # 转换为标准格式
                search_results = []
                for r in results:
                    search_results.append(MemorySearchResult(
                        content=r.get('content', ''),
                        role=r.get('role', 'unknown'),
                        score=r.get('score', 0.0),
                        metadata=r.get('metadata', {})
                    ))
                
                return search_results
                
            except Exception as e:
                logger.error(f"搜索记忆失败: {e}")
                return []
    
    @retry_with_backoff(policy=db_retry_policy)
    @graceful_degradation(lambda *args, **kwargs: {'total': 0, 'today': 0, 'this_week': 0, 'size_mb': 0})
    def get_memory_stats(self) -> Dict[str, Any]:
        """获取统计信息"""
        with monitored_operation("memory_get_stats"):
            try:
                return self.memory.get_memory_stats()
            except Exception as e:
                logger.error(f"获取统计失败: {e}")
                return {
                    'total': 0,
                    'today': 0,
                    'this_week': 0,
                    'size_mb': 0
                }
    
    @retry_with_backoff(policy=db_retry_policy)
    @graceful_degradation(lambda *args, **kwargs: 0)
    def clear_all_memories(self) -> int:
        """清除所有记忆"""
        with monitored_operation("memory_clear_all"):
            try:
                return self.memory.clear_all_memories()
            except Exception as e:
                logger.error(f"清除记忆失败: {e}")
                return 0
    
    @retry_with_backoff(policy=db_retry_policy)
    def add_memory(self, content: str, metadata: Optional[Dict[str, Any]] = None):
        """添加单条记忆"""
        with monitored_operation("memory_add"):
            try:
                self.memory.add_memory(content, metadata)
            except Exception as e:
                logger.error(f"添加记忆失败: {e}")


class NullMemoryProvider(IMemoryProvider):
    """
    空记忆提供者（用于禁用记忆或降级场景）
    """
    
    def get_context(self, query: str, **kwargs) -> str:
        """返回空上下文"""
        return ""
    
    def save_conversation(self, user_prompt: str, assistant_response: str, metadata: Optional[Dict] = None):
        """不保存任何内容"""
        logger.debug("记忆已禁用，不保存对话")
    
    def search_memory(self, query: str, n: int = 5) -> List[MemorySearchResult]:
        """返回空结果"""
        return []
    
    def get_memory_stats(self) -> Dict[str, Any]:
        """返回空统计"""
        return {
            'total': 0,
            'today': 0,
            'this_week': 0,
            'size_mb': 0
        }
    
    def clear_all_memories(self) -> int:
        """无需清除"""
        return 0
    
    def add_memory(self, content: str, metadata: Optional[Dict[str, Any]] = None):
        """不添加任何内容"""
        logger.debug("记忆已禁用，不添加记忆")


# 工厂函数
def get_memory_provider(provider_type: str = "v1") -> IMemoryProvider:
    """
    获取记忆提供者实例
    
    Args:
        provider_type: 提供者类型 ("v1", "null")
        
    Returns:
        记忆提供者实例
    """
    if provider_type == "null":
        return NullMemoryProvider()
    else:
        return MemoryProviderV1()