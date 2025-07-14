#!/usr/bin/env python3
"""
Sage MCP Server V2 - 标准 stdio 实现
半自动记忆系统，提供强大的命令接口
"""

import asyncio
import json
import sys
import os
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime
import logging
from enum import Enum

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent))

# MCP SDK imports
from mcp.server import Server, NotificationOptions
from mcp.server.models import InitializationOptions
import mcp.server.stdio
import mcp.types as types

# Import existing Sage modules
from memory_interface import get_memory_provider
from config_manager import get_config_manager
from app.memory_adapter_v2 import EnhancedMemoryAdapter
from intelligent_retrieval import (
    IntelligentRetrievalEngine,
    RetrievalStrategy,
    QueryType
)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[logging.FileHandler('/tmp/sage_mcp_v2.log')]
)
logger = logging.getLogger(__name__)


class SageMode(Enum):
    """Sage 操作模式"""
    DEFAULT = "default"          # 默认模式，手动操作
    SMART = "smart"             # 智能模式，自动记忆增强
    SESSION = "session"         # 会话模式，主题管理


class CommandType(Enum):
    """命令类型枚举"""
    SAGE = "SAGE"                    # 单次智能查询
    SAGE_MODE = "SAGE-MODE"          # 全自动模式
    SAGE_SESSION = "SAGE-SESSION"    # 会话管理
    SAGE_RECALL = "SAGE-RECALL"      # 记忆回溯
    SAGE_ANALYZE = "SAGE-ANALYZE"    # 记忆分析
    SAGE_STRATEGY = "SAGE-STRATEGY"  # 检索策略
    SAGE_CONFIG = "SAGE-CONFIG"      # 配置管理
    SAGE_EXPORT = "SAGE-EXPORT"      # 导出功能


class SageCommandParser:
    """Sage 命令解析器"""
    
    def __init__(self):
        self.command_patterns = {
            "/SAGE": CommandType.SAGE,
            "/SAGE-MODE": CommandType.SAGE_MODE,
            "/SAGE-SESSION": CommandType.SAGE_SESSION,
            "/SAGE-RECALL": CommandType.SAGE_RECALL,
            "/SAGE-ANALYZE": CommandType.SAGE_ANALYZE,
            "/SAGE-STRATEGY": CommandType.SAGE_STRATEGY,
            "/SAGE-CONFIG": CommandType.SAGE_CONFIG,
            "/SAGE-EXPORT": CommandType.SAGE_EXPORT,
        }
    
    def parse(self, input_text: str) -> Tuple[Optional[CommandType], Dict[str, Any]]:
        """解析命令和参数"""
        input_text = input_text.strip()
        
        # 查找匹配的命令
        for pattern, cmd_type in self.command_patterns.items():
            if input_text.upper().startswith(pattern):
                # 提取参数部分
                args_text = input_text[len(pattern):].strip()
                args = self._parse_args(cmd_type, args_text)
                return cmd_type, args
        
        return None, {}
    
    def _parse_args(self, cmd_type: CommandType, args_text: str) -> Dict[str, Any]:
        """解析命令参数"""
        args = {}
        
        if cmd_type == CommandType.SAGE:
            # /SAGE <query>
            args["query"] = args_text
            
        elif cmd_type == CommandType.SAGE_MODE:
            # /SAGE-MODE [on|off]
            if args_text.lower() in ["on", "off", ""]:
                args["action"] = args_text.lower() or "on"
            else:
                args["action"] = "on"
                
        elif cmd_type == CommandType.SAGE_SESSION:
            # /SAGE-SESSION <action> [topic]
            parts = args_text.split(maxsplit=1)
            if parts:
                args["action"] = parts[0].lower()
                if len(parts) > 1:
                    args["topic"] = parts[1]
                    
        elif cmd_type == CommandType.SAGE_RECALL:
            # /SAGE-RECALL <type> [params]
            parts = args_text.split(maxsplit=1)
            if parts:
                args["type"] = parts[0].lower()
                if len(parts) > 1:
                    args["params"] = parts[1]
                    
        elif cmd_type == CommandType.SAGE_STRATEGY:
            # /SAGE-STRATEGY <strategy>
            args["strategy"] = args_text.lower()
            
        elif cmd_type == CommandType.SAGE_CONFIG:
            # /SAGE-CONFIG <key> <value>
            parts = args_text.split(maxsplit=1)
            if len(parts) >= 2:
                args["key"] = parts[0].lower()
                args["value"] = parts[1]
                
        elif cmd_type == CommandType.SAGE_EXPORT:
            # /SAGE-EXPORT <type> [params]
            parts = args_text.split(maxsplit=1)
            if parts:
                args["type"] = parts[0].lower()
                if len(parts) > 1:
                    args["params"] = parts[1]
        
        return args


class SageSessionManager:
    """会话管理器"""
    
    def __init__(self):
        self.active_session = None
        self.session_history = []
        self.paused_sessions = {}
    
    def start_session(self, topic: str) -> Dict[str, Any]:
        """开始新会话"""
        if self.active_session:
            # 自动暂停当前会话
            self.pause_session()
        
        session_id = f"session_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        self.active_session = {
            "id": session_id,
            "topic": topic,
            "start_time": datetime.now(),
            "messages": [],
            "context": []
        }
        
        logger.info(f"Started session: {session_id} - Topic: {topic}")
        return self.active_session
    
    def pause_session(self) -> Optional[Dict[str, Any]]:
        """暂停当前会话"""
        if self.active_session:
            session_id = self.active_session["id"]
            self.paused_sessions[session_id] = self.active_session
            self.active_session = None
            logger.info(f"Paused session: {session_id}")
            return self.paused_sessions[session_id]
        return None
    
    def resume_session(self, session_id: str = None) -> Optional[Dict[str, Any]]:
        """恢复会话"""
        if session_id and session_id in self.paused_sessions:
            self.active_session = self.paused_sessions.pop(session_id)
            logger.info(f"Resumed session: {session_id}")
            return self.active_session
        elif not session_id and self.paused_sessions:
            # 恢复最近的会话
            session_id = list(self.paused_sessions.keys())[-1]
            return self.resume_session(session_id)
        return None
    
    def end_session(self) -> Optional[Dict[str, Any]]:
        """结束会话并生成总结"""
        if self.active_session:
            session = self.active_session
            session["end_time"] = datetime.now()
            session["duration"] = (session["end_time"] - session["start_time"]).total_seconds()
            
            # 生成会话总结
            session["summary"] = self._generate_summary(session)
            
            self.session_history.append(session)
            self.active_session = None
            
            logger.info(f"Ended session: {session['id']}")
            return session
        return None
    
    def _generate_summary(self, session: Dict[str, Any]) -> str:
        """生成会话总结"""
        summary_parts = [
            f"会话主题：{session['topic']}",
            f"持续时间：{session['duration']:.1f} 秒",
            f"消息数量：{len(session['messages'])}",
            f"开始时间：{session['start_time'].strftime('%Y-%m-%d %H:%M:%S')}",
        ]
        
        # 提取关键信息
        if session['messages']:
            summary_parts.append("\n关键讨论点：")
            # TODO: 使用 LLM 生成更智能的总结
            for i, msg in enumerate(session['messages'][:3], 1):
                summary_parts.append(f"{i}. {msg.get('content', '')[:100]}...")
        
        return "\n".join(summary_parts)


class ConversationTracker:
    """对话跟踪器 - 用于自动保存完整对话"""
    
    def __init__(self, memory_adapter: EnhancedMemoryAdapter):
        self.memory_adapter = memory_adapter
        self.current_conversation = None
        self.conversation_buffer = []
    
    def start_tracking(self, user_input: str):
        """开始跟踪新的对话"""
        self.current_conversation = {
            "user_input": user_input,
            "assistant_responses": [],
            "tool_calls": [],
            "context_used": None,
            "timestamp": datetime.now()
        }
    
    def add_context(self, context: str):
        """添加使用的上下文"""
        if self.current_conversation:
            self.current_conversation["context_used"] = context
    
    def add_response(self, response: str):
        """添加助手响应"""
        if self.current_conversation:
            self.current_conversation["assistant_responses"].append(response)
    
    def add_tool_call(self, tool_name: str, args: Dict[str, Any], result: Any):
        """添加工具调用记录"""
        if self.current_conversation:
            self.current_conversation["tool_calls"].append({
                "tool": tool_name,
                "arguments": args,
                "result": str(result)[:200],  # 限制长度
                "timestamp": datetime.now().isoformat()
            })
    
    async def save_conversation(self) -> Tuple[str, int]:
        """保存完整对话"""
        if not self.current_conversation:
            return None, None
        
        # 合并所有助手响应
        full_response = "\n\n".join(self.current_conversation["assistant_responses"])
        
        # 构建元数据
        metadata = {
            "tool_calls": self.current_conversation["tool_calls"],
            "context_used": bool(self.current_conversation["context_used"]),
            "response_parts": len(self.current_conversation["assistant_responses"]),
            "timestamp": self.current_conversation["timestamp"].isoformat()
        }
        
        # 保存到记忆系统
        session_id, turn_id = self.memory_adapter.save_conversation(
            user_prompt=self.current_conversation["user_input"],
            assistant_response=full_response,
            metadata=metadata
        )
        
        # 清理当前对话
        self.conversation_buffer.append(self.current_conversation)
        self.current_conversation = None
        
        return session_id, turn_id


class SageMCPServer:
    """Sage MCP 服务器主类"""
    
    def __init__(self):
        # 初始化 MCP 服务器
        self.server = Server("sage-memory-v2")
        
        # 初始化组件
        self.memory_provider = get_memory_provider()
        self.config_manager = get_config_manager()
        self.memory_adapter = EnhancedMemoryAdapter()
        self.retrieval_engine = IntelligentRetrievalEngine(self.memory_provider)
        
        # 初始化管理器
        self.command_parser = SageCommandParser()
        self.session_manager = SageSessionManager()
        self.conversation_tracker = ConversationTracker(self.memory_adapter)
        
        # 状态管理
        self.current_mode = SageMode.DEFAULT
        self.retrieval_strategy = RetrievalStrategy.HYBRID_ADVANCED
        self.config = {
            "auto_save": False,
            "neural_rerank": True,
            "llm_summary": True,
            "max_context": 2000
        }
        
        # 注册 MCP 处理器
        self._register_handlers()
        
        logger.info("Sage MCP Server V2 initialized")
    
    def _register_handlers(self):
        """注册 MCP 处理器"""
        
        @self.server.list_tools()
        async def handle_list_tools() -> list[types.Tool]:
            """列出所有可用工具"""
            return [
                types.Tool(
                    name="sage_command",
                    description="Sage 智能记忆系统命令接口 - 支持 /SAGE, /SAGE-MODE 等命令",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "command": {
                                "type": "string",
                                "description": "命令内容，如 '/SAGE 查询内容' 或 '/SAGE-MODE on'"
                            }
                        },
                        "required": ["command"]
                    }
                ),
                types.Tool(
                    name="sage_direct",
                    description="直接调用 Sage 记忆功能（供内部使用）",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "action": {
                                "type": "string",
                                "enum": ["save", "search", "get_context"],
                                "description": "操作类型"
                            },
                            "params": {
                                "type": "object",
                                "description": "操作参数"
                            }
                        },
                        "required": ["action", "params"]
                    }
                )
            ]
        
        @self.server.call_tool()
        async def handle_call_tool(
            name: str, 
            arguments: dict
        ) -> list[types.TextContent]:
            """处理工具调用"""
            
            try:
                if name == "sage_command":
                    # 处理 Sage 命令
                    command_text = arguments.get("command", "")
                    return await self.handle_command(command_text)
                
                elif name == "sage_direct":
                    # 直接操作
                    action = arguments.get("action")
                    params = arguments.get("params", {})
                    return await self.handle_direct_action(action, params)
                
                else:
                    return [types.TextContent(
                        type="text",
                        text=f"未知工具: {name}"
                    )]
                    
            except Exception as e:
                logger.error(f"Tool call error: {e}")
                return [types.TextContent(
                    type="text",
                    text=f"错误: {str(e)}"
                )]
        
        @self.server.list_prompts()
        async def handle_list_prompts() -> list[types.Prompt]:
            """列出可用的提示模板"""
            return [
                types.Prompt(
                    name="sage_mode",
                    description="启用 Sage 智能记忆模式",
                    arguments=[]
                )
            ]
        
        @self.server.get_prompt()
        async def handle_get_prompt(
            name: str,
            arguments: dict
        ) -> types.GetPromptResult:
            """获取提示模板"""
            
            if name == "sage_mode":
                return types.GetPromptResult(
                    description="Sage 智能记忆模式",
                    messages=[
                        types.PromptMessage(
                            role="system",
                            content=types.TextContent(
                                type="text",
                                text=self._get_sage_mode_prompt()
                            )
                        )
                    ]
                )
            
            raise ValueError(f"未知的提示: {name}")
    
    async def handle_command(self, command_text: str) -> list[types.TextContent]:
        """处理 Sage 命令"""
        
        # 解析命令
        cmd_type, args = self.command_parser.parse(command_text)
        
        if not cmd_type:
            return [types.TextContent(
                type="text",
                text="无效的命令。支持的命令：/SAGE, /SAGE-MODE, /SAGE-SESSION, /SAGE-RECALL, /SAGE-ANALYZE"
            )]
        
        # 路由到相应的处理器
        if cmd_type == CommandType.SAGE:
            return await self._handle_sage_query(args)
        elif cmd_type == CommandType.SAGE_MODE:
            return await self._handle_sage_mode(args)
        elif cmd_type == CommandType.SAGE_SESSION:
            return await self._handle_sage_session(args)
        elif cmd_type == CommandType.SAGE_RECALL:
            return await self._handle_sage_recall(args)
        elif cmd_type == CommandType.SAGE_ANALYZE:
            return await self._handle_sage_analyze(args)
        elif cmd_type == CommandType.SAGE_STRATEGY:
            return await self._handle_sage_strategy(args)
        elif cmd_type == CommandType.SAGE_CONFIG:
            return await self._handle_sage_config(args)
        elif cmd_type == CommandType.SAGE_EXPORT:
            return await self._handle_sage_export(args)
        else:
            return [types.TextContent(
                type="text",
                text=f"命令 {cmd_type.value} 尚未实现"
            )]
    
    async def _handle_sage_query(self, args: Dict[str, Any]) -> list[types.TextContent]:
        """处理 /SAGE 查询命令"""
        query = args.get("query", "")
        
        if not query:
            return [types.TextContent(
                type="text",
                text="请提供查询内容。用法：/SAGE <查询内容>"
            )]
        
        # 开始跟踪对话
        self.conversation_tracker.start_tracking(query)
        
        # 获取相关上下文
        try:
            result = await self.retrieval_engine.retrieve_contextual(
                query=query,
                strategy=self.retrieval_strategy,
                max_results=5
            )
            
            # 添加上下文到跟踪器
            if result.context:
                self.conversation_tracker.add_context(result.context)
            
            # 构建增强的响应
            response_parts = []
            
            if result.context:
                response_parts.append("【相关历史记忆】")
                response_parts.append(result.context)
                response_parts.append("")
            
            response_parts.append("【当前查询】")
            response_parts.append(query)
            response_parts.append("")
            response_parts.append("请基于以上历史记忆回答用户的问题。")
            
            if self.current_mode == SageMode.SMART:
                response_parts.append("\n⚡ 智能模式：回答后将自动保存对话")
            else:
                response_parts.append("\n💡 提示：使用 /SAGE-MODE on 启用自动保存")
            
            response_text = "\n".join(response_parts)
            
            # 添加响应到跟踪器
            self.conversation_tracker.add_response(response_text)
            
            return [types.TextContent(type="text", text=response_text)]
            
        except Exception as e:
            logger.error(f"Query error: {e}")
            return [types.TextContent(
                type="text",
                text=f"查询失败: {str(e)}"
            )]
    
    async def _handle_sage_mode(self, args: Dict[str, Any]) -> list[types.TextContent]:
        """处理 /SAGE-MODE 命令"""
        action = args.get("action", "on")
        
        if action == "on":
            self.current_mode = SageMode.SMART
            self.config["auto_save"] = True
            
            return [types.TextContent(
                type="text",
                text="""✅ Sage 智能记忆模式已启用！

我现在会自动：
• 🔍 为每个问题查找相关历史记忆
• 💾 自动保存所有对话（包括用户输入、我的回答、工具调用）
• 🧠 基于累积的知识提供更准确的回答

您可以正常对话，所有记忆功能都在后台自动运行。
使用 /SAGE-MODE off 可以关闭此模式。"""
            )]
            
        elif action == "off":
            self.current_mode = SageMode.DEFAULT
            self.config["auto_save"] = False
            
            return [types.TextContent(
                type="text",
                text="❌ Sage 智能记忆模式已关闭。对话将不再自动保存。"
            )]
        
        else:
            return [types.TextContent(
                type="text",
                text="用法：/SAGE-MODE [on|off]"
            )]
    
    async def _handle_sage_session(self, args: Dict[str, Any]) -> list[types.TextContent]:
        """处理 /SAGE-SESSION 命令"""
        action = args.get("action", "")
        topic = args.get("topic", "")
        
        if action == "start":
            if not topic:
                return [types.TextContent(
                    type="text",
                    text="请提供会话主题。用法：/SAGE-SESSION start <主题>"
                )]
            
            session = self.session_manager.start_session(topic)
            self.current_mode = SageMode.SESSION
            
            return [types.TextContent(
                type="text",
                text=f"""🎯 会话已开始！
                
主题：{topic}
会话ID：{session['id']}
开始时间：{session['start_time'].strftime('%Y-%m-%d %H:%M:%S')}

此会话中的所有对话都将被关联到主题 "{topic}"。
使用 /SAGE-SESSION end 结束会话并生成总结。"""
            )]
            
        elif action == "end":
            session = self.session_manager.end_session()
            if session:
                self.current_mode = SageMode.DEFAULT
                return [types.TextContent(
                    type="text",
                    text=f"""📝 会话已结束！

{session['summary']}

会话记录已保存，可通过 /SAGE-RECALL topic {session['topic']} 查看。"""
                )]
            else:
                return [types.TextContent(
                    type="text",
                    text="当前没有活动的会话。"
                )]
                
        elif action == "pause":
            session = self.session_manager.pause_session()
            if session:
                return [types.TextContent(
                    type="text",
                    text=f"⏸️ 会话 '{session['topic']}' 已暂停。使用 /SAGE-SESSION resume 恢复。"
                )]
            else:
                return [types.TextContent(
                    type="text",
                    text="当前没有活动的会话。"
                )]
                
        elif action == "resume":
            session = self.session_manager.resume_session()
            if session:
                self.current_mode = SageMode.SESSION
                return [types.TextContent(
                    type="text",
                    text=f"▶️ 会话 '{session['topic']}' 已恢复。"
                )]
            else:
                return [types.TextContent(
                    type="text",
                    text="没有可恢复的会话。"
                )]
        
        else:
            return [types.TextContent(
                type="text",
                text="用法：/SAGE-SESSION <start|end|pause|resume> [topic]"
            )]
    
    async def _handle_sage_recall(self, args: Dict[str, Any]) -> list[types.TextContent]:
        """处理 /SAGE-RECALL 命令"""
        recall_type = args.get("type", "")
        params = args.get("params", "")
        
        if recall_type == "recent":
            # 查看最近的记忆
            try:
                n = int(params) if params else 5
                results = self.memory_provider.search_memory("", n=n)
                
                if results:
                    response_parts = [f"📚 最近的 {len(results)} 条记忆：\n"]
                    for i, result in enumerate(results, 1):
                        response_parts.append(f"{i}. [{result.role}] {result.content[:100]}...")
                        if result.metadata.get("timestamp"):
                            response_parts.append(f"   时间：{result.metadata['timestamp']}")
                        response_parts.append("")
                    
                    return [types.TextContent(
                        type="text",
                        text="\n".join(response_parts)
                    )]
                else:
                    return [types.TextContent(
                        type="text",
                        text="没有找到记忆。"
                    )]
                    
            except Exception as e:
                return [types.TextContent(
                    type="text",
                    text=f"查询失败: {str(e)}"
                )]
                
        elif recall_type == "search":
            # 搜索特定记忆
            if not params:
                return [types.TextContent(
                    type="text",
                    text="请提供搜索关键词。用法：/SAGE-RECALL search <关键词>"
                )]
            
            try:
                results = self.memory_provider.search_memory(params, n=10)
                
                if results:
                    response_parts = [f"🔍 搜索 '{params}' 的结果：\n"]
                    for i, result in enumerate(results, 1):
                        response_parts.append(f"{i}. [{result.role}] {result.content[:150]}...")
                        response_parts.append(f"   相似度：{result.score:.3f}")
                        response_parts.append("")
                    
                    return [types.TextContent(
                        type="text",
                        text="\n".join(response_parts)
                    )]
                else:
                    return [types.TextContent(
                        type="text",
                        text=f"没有找到与 '{params}' 相关的记忆。"
                    )]
                    
            except Exception as e:
                return [types.TextContent(
                    type="text",
                    text=f"搜索失败: {str(e)}"
                )]
                
        elif recall_type == "today":
            # 今天的对话
            # TODO: 实现按日期过滤
            return [types.TextContent(
                type="text",
                text="按日期查询功能正在开发中..."
            )]
            
        elif recall_type == "topic":
            # 特定主题
            if not params:
                return [types.TextContent(
                    type="text",
                    text="请提供主题名称。用法：/SAGE-RECALL topic <主题>"
                )]
            
            # TODO: 实现主题过滤
            return [types.TextContent(
                type="text",
                text=f"主题 '{params}' 的查询功能正在开发中..."
            )]
        
        else:
            return [types.TextContent(
                type="text",
                text="用法：/SAGE-RECALL <recent|search|today|topic> [参数]"
            )]
    
    async def _handle_sage_analyze(self, args: Dict[str, Any]) -> list[types.TextContent]:
        """处理 /SAGE-ANALYZE 命令"""
        # 获取记忆统计
        try:
            stats = self.memory_provider.get_memory_stats()
            
            response_parts = ["📊 记忆系统分析报告\n"]
            response_parts.append(f"总记忆数：{stats.get('total', 0)}")
            response_parts.append(f"会话数：{stats.get('sessions', 'N/A')}")
            response_parts.append(f"有向量嵌入：{stats.get('with_embeddings', 'N/A')}")
            response_parts.append(f"日期范围：{stats.get('date_range', 'N/A')}")
            response_parts.append(f"最后更新：{stats.get('last_updated', 'N/A')}")
            
            # TODO: 添加更多分析功能
            # - 对话模式分析
            # - 热门话题
            # - 知识图谱
            
            return [types.TextContent(
                type="text",
                text="\n".join(response_parts)
            )]
            
        except Exception as e:
            return [types.TextContent(
                type="text",
                text=f"分析失败: {str(e)}"
            )]
    
    async def _handle_sage_strategy(self, args: Dict[str, Any]) -> list[types.TextContent]:
        """处理 /SAGE-STRATEGY 命令"""
        strategy_name = args.get("strategy", "")
        
        strategy_map = {
            "semantic_first": RetrievalStrategy.SEMANTIC_FIRST,
            "temporal_weighted": RetrievalStrategy.TEMPORAL_WEIGHTED,
            "context_aware": RetrievalStrategy.CONTEXT_AWARE,
            "hybrid_advanced": RetrievalStrategy.HYBRID_ADVANCED,
            "adaptive": RetrievalStrategy.ADAPTIVE
        }
        
        if strategy_name in strategy_map:
            self.retrieval_strategy = strategy_map[strategy_name]
            return [types.TextContent(
                type="text",
                text=f"✅ 检索策略已切换为：{self.retrieval_strategy.value}"
            )]
        else:
            return [types.TextContent(
                type="text",
                text=f"支持的策略：{', '.join(strategy_map.keys())}"
            )]
    
    async def _handle_sage_config(self, args: Dict[str, Any]) -> list[types.TextContent]:
        """处理 /SAGE-CONFIG 命令"""
        key = args.get("key", "")
        value = args.get("value", "")
        
        if not key:
            # 显示当前配置
            config_text = "⚙️ 当前配置：\n"
            for k, v in self.config.items():
                config_text += f"• {k}: {v}\n"
            return [types.TextContent(type="text", text=config_text)]
        
        # 更新配置
        if key == "rerank":
            self.config["neural_rerank"] = value.lower() == "on"
            return [types.TextContent(
                type="text",
                text=f"神经网络重排序已{'启用' if self.config['neural_rerank'] else '禁用'}"
            )]
        elif key == "summary":
            self.config["llm_summary"] = value.lower() == "on"
            return [types.TextContent(
                type="text",
                text=f"LLM摘要已{'启用' if self.config['llm_summary'] else '禁用'}"
            )]
        elif key == "auto-save":
            self.config["auto_save"] = value.lower() == "on"
            return [types.TextContent(
                type="text",
                text=f"自动保存已{'启用' if self.config['auto_save'] else '禁用'}"
            )]
        elif key == "context-size":
            try:
                self.config["max_context"] = int(value)
                return [types.TextContent(
                    type="text",
                    text=f"上下文大小已设置为：{self.config['max_context']}"
                )]
            except ValueError:
                return [types.TextContent(
                    type="text",
                    text="请提供有效的数字"
                )]
        else:
            return [types.TextContent(
                type="text",
                text=f"未知的配置项：{key}"
            )]
    
    async def _handle_sage_export(self, args: Dict[str, Any]) -> list[types.TextContent]:
        """处理 /SAGE-EXPORT 命令"""
        export_type = args.get("type", "")
        
        # TODO: 实现导出功能
        return [types.TextContent(
            type="text",
            text="导出功能正在开发中..."
        )]
    
    async def handle_direct_action(self, action: str, params: Dict[str, Any]) -> list[types.TextContent]:
        """处理直接操作（供智能模式内部使用）"""
        
        if action == "save":
            # 保存对话
            user_prompt = params.get("user_prompt", "")
            assistant_response = params.get("assistant_response", "")
            metadata = params.get("metadata", {})
            
            try:
                session_id, turn_id = self.memory_adapter.save_conversation(
                    user_prompt=user_prompt,
                    assistant_response=assistant_response,
                    metadata=metadata
                )
                
                return [types.TextContent(
                    type="text",
                    text=f"✅ 对话已保存 (Session: {session_id}, Turn: {turn_id})"
                )]
                
            except Exception as e:
                return [types.TextContent(
                    type="text",
                    text=f"保存失败: {str(e)}"
                )]
                
        elif action == "get_context":
            # 获取上下文
            query = params.get("query", "")
            
            try:
                result = await self.retrieval_engine.retrieve_contextual(
                    query=query,
                    strategy=self.retrieval_strategy,
                    max_results=params.get("max_results", 5)
                )
                
                return [types.TextContent(
                    type="text",
                    text=result.context or "没有找到相关上下文"
                )]
                
            except Exception as e:
                return [types.TextContent(
                    type="text",
                    text=f"获取上下文失败: {str(e)}"
                )]
                
        else:
            return [types.TextContent(
                type="text",
                text=f"未知的操作: {action}"
            )]
    
    def _get_sage_mode_prompt(self) -> str:
        """获取 Sage 模式的系统提示"""
        return """你现在处于 Sage 智能记忆模式。

重要规则：
1. 对于每个用户输入，首先使用 sage_direct 工具调用 get_context 获取相关历史记忆
2. 基于历史记忆和当前问题提供回答
3. 回答完成后，使用 sage_direct 工具调用 save 保存完整对话

工作流程示例：
1. 用户提问
2. 调用: sage_direct { "action": "get_context", "params": { "query": "用户问题" } }
3. 基于返回的上下文和用户问题进行回答
4. 调用: sage_direct { "action": "save", "params": { "user_prompt": "用户问题", "assistant_response": "你的完整回答" } }

记住：
- 不要向用户提及这些工具调用
- 自然地引用历史信息，就像你一直记得一样
- 确保保存的是完整的对话内容
"""

    async def run(self):
        """运行 MCP 服务器"""
        async with mcp.server.stdio.stdio_server() as (read_stream, write_stream):
            await self.server.run(
                read_stream,
                write_stream,
                InitializationOptions(
                    server_name="sage-memory-v2",
                    server_version="2.0.0",
                    capabilities=self.server.get_capabilities(
                        notification_options=NotificationOptions(),
                        experimental_capabilities={}
                    )
                )
            )


async def main():
    """主函数"""
    try:
        # 创建并运行服务器
        sage_server = SageMCPServer()
        await sage_server.run()
    except Exception as e:
        logger.error(f"Server error: {e}")
        raise


if __name__ == "__main__":
    asyncio.run(main())