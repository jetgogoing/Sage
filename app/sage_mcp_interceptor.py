"""
Sage MCP Interceptor - 自动拦截和注入记忆
这个模块通过MCP协议的特殊机制实现完全自动的记忆注入
"""

import json
import asyncio
from typing import Dict, Any, Optional, List
from datetime import datetime
import hashlib

class AutoMemoryInjector:
    """自动记忆注入器"""
    
    def __init__(self, enhanced_adapter, logger):
        self.enhanced_adapter = enhanced_adapter
        self.logger = logger
        self.last_query_hash = None
        self.context_cache = {}
        
    async def intercept_and_inject(self, request: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        拦截所有请求并自动注入相关记忆
        这个方法会在每个MCP请求之前被调用
        """
        # 检查是否是需要注入上下文的请求
        if not self._should_inject_context(request):
            return None
            
        # 提取用户查询
        query = self._extract_query(request)
        if not query:
            return None
            
        # 检查是否是重复查询
        query_hash = hashlib.md5(query.encode()).hexdigest()
        if query_hash == self.last_query_hash:
            return None
        self.last_query_hash = query_hash
        
        # 获取相关上下文
        try:
            context = await self._get_relevant_context(query)
            if context:
                # 自动保存当前对话（如果有响应）
                await self._auto_save_if_needed(request)
                
                # 返回注入的上下文
                return {
                    "injected_context": context,
                    "timestamp": datetime.now().isoformat()
                }
        except Exception as e:
            self.logger.error(f"Auto-injection failed: {e}")
            
        return None
    
    def _should_inject_context(self, request: Dict[str, Any]) -> bool:
        """判断是否应该注入上下文"""
        # 对所有非记忆系统的请求都注入上下文
        method = request.get("method", "")
        
        # 跳过记忆系统自身的调用，避免循环
        if method in ["tools/call", "save_conversation", "get_context", "search_memory"]:
            params = request.get("params", {})
            tool_name = params.get("name", "")
            if tool_name in ["save_conversation", "get_context", "search_memory", "get_memory_stats"]:
                return False
                
        # 对其他所有请求都注入上下文
        return True
    
    def _extract_query(self, request: Dict[str, Any]) -> Optional[str]:
        """从请求中提取查询文本"""
        # 尝试多种方式提取查询
        params = request.get("params", {})
        
        # 从不同的参数位置提取
        query = (
            params.get("query") or
            params.get("prompt") or
            params.get("message") or
            params.get("text") or
            params.get("input") or
            ""
        )
        
        # 如果是工具调用，尝试从arguments中提取
        if request.get("method") == "tools/call":
            args = params.get("arguments", {})
            query = (
                args.get("query") or
                args.get("prompt") or
                args.get("user_prompt") or
                query
            )
            
        return query.strip() if query else None
    
    async def _get_relevant_context(self, query: str) -> Optional[str]:
        """获取相关上下文"""
        try:
            # 使用智能检索获取上下文
            result = await self.enhanced_adapter.get_intelligent_context(
                query=query,
                enable_llm_summary=True,
                max_results=3,
                enable_neural_rerank=True
            )
            
            if result and result.get('context'):
                context = result['context']
                # 添加标记表明这是自动注入的上下文
                return f"[自动注入的相关记忆]\n{context}\n[记忆结束]"
                
        except Exception as e:
            self.logger.error(f"Failed to get context: {e}")
            
        return None
    
    async def _auto_save_if_needed(self, request: Dict[str, Any]):
        """如果有完整的对话，自动保存"""
        # 这里可以实现自动保存逻辑
        pass

# 全局注入器配置
GLOBAL_AUTO_INJECTION_CONFIG = {
    "enabled": True,
    "inject_on_every_request": True,
    "max_context_length": 2000,
    "cache_duration": 300,  # 5分钟缓存
    "auto_save_enabled": True
}

def create_initialization_override():
    """
    创建初始化覆盖响应
    这个响应会告诉Claude Code始终使用我们的记忆系统
    """
    return {
        "systemPrompt": """
You are Claude with access to a persistent memory system. 

IMPORTANT: For EVERY user message, you MUST:
1. Automatically search for relevant historical context using the memory system
2. Consider all relevant past conversations when formulating responses
3. Save important information for future reference

The memory system works transparently - you don't need to mention it unless specifically asked.
All conversations are automatically enhanced with relevant historical context.

When responding:
- Draw upon relevant past discussions naturally
- Build on previous conversations when applicable
- Maintain consistency with historical context
- Update your understanding based on accumulated knowledge

The memory system is ALWAYS active and enhances every interaction.
""",
        "autoExecutePrompts": ["auto_context_injection"],
        "defaultContext": {
            "memory_enabled": True,
            "auto_injection": True
        }
    }