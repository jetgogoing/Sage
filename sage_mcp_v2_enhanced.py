#!/usr/bin/env python3
"""
Sage MCP Server V2 Enhanced - 集成自动保存和智能注入
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

# Import auto-save components
from sage_mcp_auto_save import (
    AutoSaveManager,
    SmartContextInjector,
    ConversationFlowManager,
    SmartModePromptGenerator
)

# Import existing components from V2
from sage_mcp_stdio_v2 import (
    SageMode, CommandType, SageCommandParser,
    SageSessionManager, ConversationTracker
)

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
    RetrievalStrategy
)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[logging.FileHandler('/tmp/sage_mcp_v2_enhanced.log')]
)
logger = logging.getLogger(__name__)


class EnhancedSageMCPServer:
    """增强版 Sage MCP 服务器 - 支持自动保存和智能注入"""
    
    def __init__(self):
        # 初始化 MCP 服务器
        self.server = Server("sage-memory-v2-enhanced")
        
        # 初始化核心组件
        self.memory_provider = get_memory_provider()
        self.config_manager = get_config_manager()
        self.memory_adapter = EnhancedMemoryAdapter()
        self.retrieval_engine = IntelligentRetrievalEngine(self.memory_provider)
        
        # 初始化管理器
        self.command_parser = SageCommandParser()
        self.session_manager = SageSessionManager()
        self.conversation_tracker = ConversationTracker(self.memory_adapter)
        
        # 初始化自动保存组件
        self.auto_save_manager = AutoSaveManager(self.memory_adapter)
        self.context_injector = SmartContextInjector(self.retrieval_engine)
        self.flow_manager = ConversationFlowManager(
            self.auto_save_manager,
            self.context_injector
        )
        
        # 状态管理
        self.current_mode = SageMode.DEFAULT
        self.retrieval_strategy = RetrievalStrategy.HYBRID_ADVANCED
        self.config = {
            "auto_save": False,
            "neural_rerank": True,
            "llm_summary": True,
            "max_context": 2000,
            "auto_inject": False
        }
        
        # 注册 MCP 处理器
        self._register_handlers()
        
        logger.info("Enhanced Sage MCP Server V2 initialized")
    
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
                    name="sage_auto",
                    description="Sage 自动模式接口（智能模式下自动调用）",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "query": {
                                "type": "string",
                                "description": "用户查询"
                            },
                            "response": {
                                "type": "string",
                                "description": "助手响应（用于保存）"
                            },
                            "action": {
                                "type": "string",
                                "enum": ["enhance_query", "save_conversation"],
                                "description": "自动操作类型"
                            }
                        },
                        "required": ["action"]
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
                
                elif name == "sage_auto":
                    # 处理自动模式操作
                    action = arguments.get("action")
                    
                    if action == "enhance_query":
                        # 增强查询
                        query = arguments.get("query", "")
                        result = await self.flow_manager.process_user_input(
                            query, 
                            self.retrieval_strategy
                        )
                        
                        if result["context"]:
                            return [types.TextContent(
                                type="text",
                                text=result["enhanced_input"]
                            )]
                        else:
                            return [types.TextContent(
                                type="text",
                                text=f"用户查询：{query}"
                            )]
                    
                    elif action == "save_conversation":
                        # 保存对话
                        response = arguments.get("response", "")
                        saved = await self.flow_manager.process_assistant_response(response)
                        
                        if saved:
                            session_id, turn_id = saved
                            return [types.TextContent(
                                type="text",
                                text=f"✅ 自动保存成功 (Session: {session_id}, Turn: {turn_id})"
                            )]
                        else:
                            return [types.TextContent(
                                type="text",
                                text="⚠️ 自动保存未完成"
                            )]
                    
                    else:
                        return [types.TextContent(
                            type="text",
                            text=f"未知的自动操作: {action}"
                        )]
                
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
                    name="sage_smart_mode",
                    description="启用 Sage 智能记忆模式（增强版）",
                    arguments=[]
                )
            ]
        
        @self.server.get_prompt()
        async def handle_get_prompt(
            name: str,
            arguments: dict
        ) -> types.GetPromptResult:
            """获取提示模板"""
            
            if name == "sage_smart_mode":
                return types.GetPromptResult(
                    description="Sage 智能记忆模式（增强版）",
                    messages=[
                        types.PromptMessage(
                            role="system",
                            content=types.TextContent(
                                type="text",
                                text=self._get_enhanced_sage_mode_prompt()
                            )
                        )
                    ]
                )
            
            raise ValueError(f"未知的提示: {name}")
    
    async def handle_command(self, command_text: str) -> list[types.TextContent]:
        """处理 Sage 命令（继承自 V2）"""
        
        # 解析命令
        cmd_type, args = self.command_parser.parse(command_text)
        
        if not cmd_type:
            return [types.TextContent(
                type="text",
                text="无效的命令。支持的命令：/SAGE, /SAGE-MODE, /SAGE-SESSION, /SAGE-RECALL, /SAGE-ANALYZE"
            )]
        
        # 特殊处理 SAGE-MODE 命令
        if cmd_type == CommandType.SAGE_MODE:
            return await self._handle_enhanced_sage_mode(args)
        
        # 特殊处理 SAGE 查询命令
        elif cmd_type == CommandType.SAGE:
            return await self._handle_enhanced_sage_query(args)
        
        # 其他命令保持原有逻辑
        else:
            # 调用原有的命令处理逻辑
            # （这里可以导入并调用 sage_mcp_stdio_v2.py 中的处理函数）
            return [types.TextContent(
                type="text",
                text=f"命令 {cmd_type.value} 处理中..."
            )]
    
    async def _handle_enhanced_sage_mode(self, args: Dict[str, Any]) -> list[types.TextContent]:
        """处理增强的 /SAGE-MODE 命令"""
        action = args.get("action", "on")
        
        if action == "on":
            self.current_mode = SageMode.SMART
            self.config["auto_save"] = True
            self.config["auto_inject"] = True
            
            # 启用自动功能
            self.flow_manager.enable_smart_mode()
            
            return [types.TextContent(
                type="text",
                text="""✅ Sage 智能记忆模式已启用（增强版）！

🚀 增强功能：
• 🔍 自动为每个问题注入相关历史记忆
• 💾 自动保存完整对话（包括工具调用）
• 🧠 智能上下文缓存，提升响应速度
• 📊 对话流程全程跟踪

您可以正常对话，所有记忆功能都在后台透明运行。
使用 /SAGE-MODE off 可以关闭此模式。"""
            )]
            
        elif action == "off":
            self.current_mode = SageMode.DEFAULT
            self.config["auto_save"] = False
            self.config["auto_inject"] = False
            
            # 禁用自动功能
            self.flow_manager.disable_smart_mode()
            
            # 检查是否有未保存的对话
            pending = self.auto_save_manager.get_pending_count()
            status_msg = "❌ Sage 智能记忆模式已关闭。"
            if pending > 0:
                status_msg += f"\n⚠️ 有 {pending} 个对话未保存。"
            
            return [types.TextContent(
                type="text",
                text=status_msg
            )]
        
        else:
            return [types.TextContent(
                type="text",
                text="用法：/SAGE-MODE [on|off]"
            )]
    
    async def _handle_enhanced_sage_query(self, args: Dict[str, Any]) -> list[types.TextContent]:
        """处理增强的 /SAGE 查询命令"""
        query = args.get("query", "")
        
        if not query:
            return [types.TextContent(
                type="text",
                text="请提供查询内容。用法：/SAGE <查询内容>"
            )]
        
        # 如果在智能模式下，使用增强流程
        if self.current_mode == SageMode.SMART:
            result = await self.flow_manager.process_user_input(query, self.retrieval_strategy)
            
            response_text = result["enhanced_input"]
            
            # 记录这是一个 SAGE 命令查询
            self.flow_manager.auto_save.current_tracking["metadata"]["command_type"] = "SAGE"
            
            return [types.TextContent(type="text", text=response_text)]
        
        # 否则使用普通流程
        else:
            # 获取相关上下文
            try:
                result = await self.retrieval_engine.retrieve_contextual(
                    query=query,
                    strategy=self.retrieval_strategy,
                    max_results=5
                )
                
                # 构建响应
                response_parts = []
                
                if result.context:
                    response_parts.append("【相关历史记忆】")
                    response_parts.append(result.context)
                    response_parts.append("")
                
                response_parts.append("【当前查询】")
                response_parts.append(query)
                response_parts.append("")
                response_parts.append("💡 提示：使用 /SAGE-MODE on 启用自动保存和智能注入")
                
                return [types.TextContent(
                    type="text",
                    text="\n".join(response_parts)
                )]
                
            except Exception as e:
                logger.error(f"Query error: {e}")
                return [types.TextContent(
                    type="text",
                    text=f"查询失败: {str(e)}"
                )]
    
    def _get_enhanced_sage_mode_prompt(self) -> str:
        """获取增强的 Sage 模式系统提示"""
        return """你现在处于 Sage 智能记忆模式（增强版）。

核心工作流程：
1. 当用户提问时，使用 sage_auto 工具的 enhance_query 操作获取增强的查询
2. 基于增强的查询（包含历史记忆）提供回答
3. 回答完成后，使用 sage_auto 工具的 save_conversation 操作保存对话

示例流程：
用户: "如何优化代码性能？"

你的操作:
1. 调用: sage_auto { "action": "enhance_query", "query": "如何优化代码性能？" }
2. 收到增强的查询（可能包含之前讨论过的性能优化案例）
3. 基于全部信息提供综合回答
4. 调用: sage_auto { "action": "save_conversation", "response": "你的完整回答" }

重要原则：
• 工具调用对用户透明，不要提及
• 自然地引用历史信息
• 确保每轮对话都被保存
• 保持对话的连贯性和上下文感知

记忆系统会自动：
- 检索相关历史
- 注入上下文
- 保存对话
- 跟踪工具调用
"""
    
    async def run(self):
        """运行 MCP 服务器"""
        async with mcp.server.stdio.stdio_server() as (read_stream, write_stream):
            await self.server.run(
                read_stream,
                write_stream,
                InitializationOptions(
                    server_name="sage-memory-v2-enhanced",
                    server_version="2.1.0",
                    capabilities=self.server.get_capabilities(
                        notification_options=NotificationOptions(),
                        experimental_capabilities={
                            "auto_context_injection": True,
                            "auto_save": True,
                            "conversation_tracking": True
                        }
                    )
                )
            )


async def main():
    """主函数"""
    try:
        # 创建并运行增强版服务器
        sage_server = EnhancedSageMCPServer()
        await sage_server.run()
    except Exception as e:
        logger.error(f"Server error: {e}")
        raise


if __name__ == "__main__":
    asyncio.run(main())