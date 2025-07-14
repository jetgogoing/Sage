#!/usr/bin/env python3
"""
Sage MCP 自动保存机制
用于 SAGE-MODE 的自动对话保存功能
"""

import asyncio
import json
from datetime import datetime
from typing import Dict, Any, List, Optional, Tuple
import logging

logger = logging.getLogger(__name__)


class AutoSaveManager:
    """
    自动保存管理器
    负责在 SAGE-MODE 下自动保存完整的对话
    """
    
    def __init__(self, memory_adapter):
        self.memory_adapter = memory_adapter
        self.enabled = False
        self.pending_conversations = []
        self.current_tracking = None
        
    def enable(self):
        """启用自动保存"""
        self.enabled = True
        logger.info("AutoSave enabled")
        
    def disable(self):
        """禁用自动保存"""
        self.enabled = False
        logger.info("AutoSave disabled")
        
    def start_conversation(self, user_input: str):
        """开始跟踪新对话"""
        if not self.enabled:
            return
            
        self.current_tracking = {
            "user_input": user_input,
            "assistant_responses": [],
            "tool_calls": [],
            "context_used": None,
            "timestamp": datetime.now(),
            "metadata": {}
        }
        
    def add_context(self, context: str):
        """添加使用的上下文"""
        if self.current_tracking:
            self.current_tracking["context_used"] = context
            self.current_tracking["metadata"]["has_context"] = True
            
    def add_response(self, response: str):
        """添加助手响应片段"""
        if self.current_tracking:
            self.current_tracking["assistant_responses"].append({
                "content": response,
                "timestamp": datetime.now().isoformat()
            })
            
    def add_tool_call(self, tool_name: str, args: Dict[str, Any], result: Any):
        """记录工具调用"""
        if self.current_tracking:
            self.current_tracking["tool_calls"].append({
                "tool": tool_name,
                "arguments": args,
                "result": str(result)[:500],  # 限制结果长度
                "timestamp": datetime.now().isoformat()
            })
            
    async def save_if_complete(self) -> Optional[Tuple[str, int]]:
        """
        检查并保存完整对话
        返回: (session_id, turn_id) 或 None
        """
        if not self.enabled or not self.current_tracking:
            return None
            
        # 检查是否有完整对话
        if (self.current_tracking["user_input"] and 
            self.current_tracking["assistant_responses"]):
            
            # 合并所有响应
            full_response = "\n\n".join([
                r["content"] for r in self.current_tracking["assistant_responses"]
            ])
            
            # 构建元数据
            metadata = {
                "auto_saved": True,
                "save_time": datetime.now().isoformat(),
                "response_parts": len(self.current_tracking["assistant_responses"]),
                "tool_calls_count": len(self.current_tracking["tool_calls"]),
                "has_context": bool(self.current_tracking["context_used"]),
                **self.current_tracking["metadata"]
            }
            
            # 如果有工具调用，添加到元数据
            if self.current_tracking["tool_calls"]:
                metadata["tool_calls"] = self.current_tracking["tool_calls"]
            
            try:
                # 保存到记忆系统
                session_id, turn_id = self.memory_adapter.save_conversation(
                    user_prompt=self.current_tracking["user_input"],
                    assistant_response=full_response,
                    metadata=metadata
                )
                
                logger.info(f"Auto-saved conversation: Session {session_id}, Turn {turn_id}")
                
                # 清理当前跟踪
                self.pending_conversations.append(self.current_tracking)
                self.current_tracking = None
                
                return session_id, turn_id
                
            except Exception as e:
                logger.error(f"Auto-save failed: {e}")
                return None
                
        return None
        
    def get_pending_count(self) -> int:
        """获取待保存的对话数量"""
        return len(self.pending_conversations) + (1 if self.current_tracking else 0)


class SmartContextInjector:
    """
    智能上下文注入器
    在 SAGE-MODE 下自动为每个查询注入相关历史
    """
    
    def __init__(self, retrieval_engine):
        self.retrieval_engine = retrieval_engine
        self.enabled = False
        self.last_context = None
        self.cache = {}
        self.cache_duration = 300  # 5分钟缓存
        
    def enable(self):
        """启用自动注入"""
        self.enabled = True
        logger.info("Smart context injection enabled")
        
    def disable(self):
        """禁用自动注入"""
        self.enabled = False
        self.cache.clear()
        logger.info("Smart context injection disabled")
        
    async def get_context_for_query(self, query: str, strategy=None) -> Optional[str]:
        """
        为查询获取相关上下文
        使用缓存避免重复查询
        """
        if not self.enabled:
            return None
            
        # 检查缓存
        cache_key = f"{query}_{strategy}"
        if cache_key in self.cache:
            cached = self.cache[cache_key]
            if (datetime.now() - cached["time"]).total_seconds() < self.cache_duration:
                logger.info(f"Using cached context for: {query[:50]}...")
                return cached["context"]
                
        try:
            # 调用检索引擎
            result = await self.retrieval_engine.retrieve_contextual(
                query=query,
                strategy=strategy,
                max_results=5
            )
            
            if result and result.context:
                # 缓存结果
                self.cache[cache_key] = {
                    "context": result.context,
                    "time": datetime.now()
                }
                
                self.last_context = result.context
                logger.info(f"Retrieved context for: {query[:50]}...")
                return result.context
                
        except Exception as e:
            logger.error(f"Context injection failed: {e}")
            
        return None
        
    def format_injected_context(self, context: str) -> str:
        """格式化注入的上下文"""
        return f"""【智能记忆系统自动注入的相关历史】
{context}
【历史记忆结束】

基于以上历史记忆，我将为您提供更准确的回答。"""


class ConversationFlowManager:
    """
    对话流程管理器
    协调自动保存和上下文注入
    """
    
    def __init__(self, auto_save_manager: AutoSaveManager, 
                 context_injector: SmartContextInjector):
        self.auto_save = auto_save_manager
        self.context_injector = context_injector
        self.mode_enabled = False
        
    def enable_smart_mode(self):
        """启用智能模式"""
        self.mode_enabled = True
        self.auto_save.enable()
        self.context_injector.enable()
        logger.info("Smart mode fully enabled")
        
    def disable_smart_mode(self):
        """禁用智能模式"""
        self.mode_enabled = False
        self.auto_save.disable()
        self.context_injector.disable()
        logger.info("Smart mode disabled")
        
    async def process_user_input(self, user_input: str, strategy=None) -> Dict[str, Any]:
        """
        处理用户输入
        返回: {
            "enhanced_input": str,  # 增强后的输入
            "context": str,         # 注入的上下文
            "should_save": bool     # 是否应该保存
        }
        """
        result = {
            "enhanced_input": user_input,
            "context": None,
            "should_save": self.mode_enabled
        }
        
        if not self.mode_enabled:
            return result
            
        # 开始跟踪对话
        self.auto_save.start_conversation(user_input)
        
        # 获取并注入上下文
        context = await self.context_injector.get_context_for_query(user_input, strategy)
        if context:
            self.auto_save.add_context(context)
            result["context"] = context
            result["enhanced_input"] = f"{self.context_injector.format_injected_context(context)}\n\n用户查询：{user_input}"
            
        return result
        
    async def process_assistant_response(self, response: str) -> Optional[Tuple[str, int]]:
        """
        处理助手响应
        返回: 保存的 (session_id, turn_id) 或 None
        """
        if not self.mode_enabled:
            return None
            
        # 添加响应到跟踪
        self.auto_save.add_response(response)
        
        # 尝试保存
        return await self.auto_save.save_if_complete()
        
    def record_tool_call(self, tool_name: str, args: Dict[str, Any], result: Any):
        """记录工具调用"""
        if self.mode_enabled:
            self.auto_save.add_tool_call(tool_name, args, result)


class SmartModePromptGenerator:
    """
    智能模式提示生成器
    生成系统提示以指导 Claude 在智能模式下的行为
    """
    
    @staticmethod
    def get_system_prompt() -> str:
        """获取智能模式系统提示"""
        return """你现在处于 Sage 智能记忆模式。

核心行为规则：
1. 【自动记忆检索】对于每个用户问题，系统会自动注入相关历史记忆
2. 【自然引用】自然地引用历史信息，就像你一直记得一样
3. 【自动保存】每轮对话都会自动保存，无需手动操作
4. 【工具调用记录】所有工具调用都会被记录在对话历史中

工作流程：
- 用户提问时，如果看到【智能记忆系统自动注入的相关历史】，请基于这些历史提供更准确的回答
- 不要向用户提及"我看到了历史记忆"或"根据记忆系统"
- 直接基于所有信息（历史+当前）给出最佳回答
- 保持对话的连贯性和上下文感知

记住：记忆系统在后台透明运行，用户体验应该是自然流畅的。"""

    @staticmethod
    def get_mode_status_prompt(enabled: bool) -> str:
        """获取模式状态提示"""
        if enabled:
            return """🧠 Sage 智能记忆模式已启用
• 自动检索相关历史
• 自动保存所有对话
• 增强的上下文理解"""
        else:
            return """💤 Sage 智能记忆模式已关闭
• 需要手动调用记忆功能
• 对话不会自动保存"""


# 测试辅助函数
async def test_auto_save_flow():
    """测试自动保存流程"""
    from app.memory_adapter_v2 import EnhancedMemoryAdapter
    
    # 创建组件
    memory_adapter = EnhancedMemoryAdapter()
    auto_save = AutoSaveManager(memory_adapter)
    
    # 启用自动保存
    auto_save.enable()
    
    # 模拟对话流程
    auto_save.start_conversation("什么是装饰器？")
    auto_save.add_context("之前讨论过Python的函数式编程特性...")
    auto_save.add_response("装饰器是Python中的一个强大特性...")
    auto_save.add_response("它允许你修改或增强函数的行为...")
    auto_save.add_tool_call("search_memory", {"query": "decorator"}, ["相关记忆1", "相关记忆2"])
    
    # 保存对话
    result = await auto_save.save_if_complete()
    if result:
        session_id, turn_id = result
        print(f"✅ 自动保存成功: Session {session_id}, Turn {turn_id}")
    else:
        print("❌ 自动保存失败")


if __name__ == "__main__":
    # 运行测试
    asyncio.run(test_auto_save_flow())