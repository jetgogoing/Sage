#!/usr/bin/env python3
"""
Sage MCP Server V4 Final - 完整功能集成版
包含智能提示系统、错误处理和性能优化
"""

import asyncio
import json
import sys
import os
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime
import logging

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent))

# Import V3 components
from sage_mcp_v3_advanced import AdvancedSageMCPServer

# Import V4 components
from sage_smart_prompt_system import (
    SmartPromptGenerator,
    PromptType,
    PromptContext
)
from sage_error_handler import (
    error_handler,
    performance_monitor,
    resource_manager,
    optimization_engine,
    with_error_handling,
    with_performance_monitoring,
    ErrorSeverity
)

# MCP SDK imports
from mcp.server import Server, NotificationOptions
from mcp.server.models import InitializationOptions
import mcp.server.stdio
import mcp.types as types

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[logging.FileHandler('/tmp/sage_mcp_v4_final.log')]
)
logger = logging.getLogger(__name__)


class FinalSageMCPServer(AdvancedSageMCPServer):
    """最终版 Sage MCP 服务器 - 完整功能集成"""
    
    def __init__(self):
        # 初始化父类
        super().__init__()
        
        # 初始化V4组件
        self.prompt_generator = SmartPromptGenerator(
            self.memory_analyzer,
            self.enhanced_session_manager
        )
        
        # 更新服务器信息
        self.server = Server("sage-memory-v4-final")
        
        # 启用性能监控
        self._enable_monitoring = True
        
        # 注册最终版处理器
        self._register_final_handlers()
        
        logger.info("Final Sage MCP Server V4 initialized with all features")
        
    def _register_final_handlers(self):
        """注册最终版处理器"""
        # 首先调用父类的注册
        super()._register_advanced_handlers()
        
        # 覆盖工具列表以添加V4工具
        @self.server.list_tools()
        async def handle_list_tools() -> list[types.Tool]:
            """列出所有可用工具（包括V4新增）"""
            base_tools = await super().handle_list_tools()
            
            # 添加V4工具
            final_tools = [
                types.Tool(
                    name="sage_smart_prompt",
                    description="智能提示系统 - 生成上下文感知的智能提示和建议",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "user_input": {
                                "type": "string",
                                "description": "用户输入内容"
                            },
                            "include_suggestions": {
                                "type": "boolean",
                                "description": "是否包含建议",
                                "default": True
                            }
                        },
                        "required": ["user_input"]
                    }
                ),
                types.Tool(
                    name="sage_system_status",
                    description="系统状态监控 - 获取错误统计、性能指标和优化建议",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "include_errors": {
                                "type": "boolean",
                                "description": "包含错误统计",
                                "default": True
                            },
                            "include_performance": {
                                "type": "boolean",
                                "description": "包含性能指标",
                                "default": True
                            },
                            "include_optimization": {
                                "type": "boolean",
                                "description": "包含优化建议",
                                "default": True
                            }
                        }
                    }
                )
            ]
            
            return base_tools + final_tools
        
        # 扩展提示列表
        @self.server.list_prompts()
        async def handle_list_prompts() -> list[types.Prompt]:
            """列出可用的提示模板（包括V4新增）"""
            base_prompts = await super().handle_list_prompts()
            
            final_prompts = [
                types.Prompt(
                    name="sage_intelligent_mode",
                    description="启用 Sage 智能助手模式（完整版）",
                    arguments=[]
                ),
                types.Prompt(
                    name="sage_learning_mode",
                    description="启用 Sage 学习辅导模式",
                    arguments=[]
                ),
                types.Prompt(
                    name="sage_debug_mode",
                    description="启用 Sage 调试助手模式",
                    arguments=[]
                )
            ]
            
            return base_prompts + final_prompts
        
        # 扩展提示获取
        original_get_prompt = self.server._prompt_handlers.get("get_prompt")
        
        @self.server.get_prompt()
        async def handle_get_prompt(name: str, arguments: dict) -> types.GetPromptResult:
            """获取提示模板（包括V4新增）"""
            
            if name == "sage_intelligent_mode":
                return types.GetPromptResult(
                    description="Sage 智能助手模式（完整版）",
                    messages=[
                        types.PromptMessage(
                            role="system",
                            content=types.TextContent(
                                type="text",
                                text=self._get_intelligent_mode_prompt()
                            )
                        )
                    ]
                )
            elif name == "sage_learning_mode":
                return types.GetPromptResult(
                    description="Sage 学习辅导模式",
                    messages=[
                        types.PromptMessage(
                            role="system",
                            content=types.TextContent(
                                type="text",
                                text=self._get_learning_mode_prompt()
                            )
                        )
                    ]
                )
            elif name == "sage_debug_mode":
                return types.GetPromptResult(
                    description="Sage 调试助手模式",
                    messages=[
                        types.PromptMessage(
                            role="system",
                            content=types.TextContent(
                                type="text",
                                text=self._get_debug_mode_prompt()
                            )
                        )
                    ]
                )
            else:
                # 调用父类处理
                return await super().handle_get_prompt(name, arguments)
    
    @with_error_handling(ErrorSeverity.HIGH)
    @with_performance_monitoring("handle_command")
    async def handle_command(self, command_text: str) -> list[types.TextContent]:
        """处理 Sage 命令（带错误处理和性能监控）"""
        
        # 检查资源
        if not await resource_manager.check_resources():
            return [types.TextContent(
                type="text",
                text="⚠️ 系统资源不足，请稍后再试或使用 /SAGE-STATUS 查看详情"
            )]
            
        # 处理新增的状态命令
        if command_text.upper().strip() == "/SAGE-STATUS":
            return await self._handle_status_command()
            
        # 调用父类处理其他命令
        return await super().handle_command(command_text)
    
    @with_error_handling(ErrorSeverity.MEDIUM)
    @with_performance_monitoring("handle_tool_call")
    async def handle_call_tool(self, name: str, arguments: dict) -> list[types.TextContent]:
        """处理工具调用（带错误处理和性能监控）"""
        
        # 处理V4特有的工具
        if name == "sage_smart_prompt":
            return await self._handle_smart_prompt_tool(arguments)
        elif name == "sage_system_status":
            return await self._handle_system_status_tool(arguments)
        else:
            # 调用父类处理
            return await super().handle_call_tool(name, arguments)
    
    async def _handle_smart_prompt_tool(self, arguments: Dict[str, Any]) -> list[types.TextContent]:
        """处理智能提示工具调用"""
        user_input = arguments.get("user_input", "")
        include_suggestions = arguments.get("include_suggestions", True)
        
        if not user_input:
            return [types.TextContent(
                type="text",
                text="请提供用户输入内容"
            )]
            
        # 获取对话历史
        conversation_history = []
        if self.enhanced_session_manager.active_session:
            conversation_history = self.enhanced_session_manager.active_session.get("messages", [])
            
        # 生成智能提示
        try:
            prompt_result = await self.prompt_generator.generate_smart_prompt(
                user_input,
                conversation_history
            )
            
            # 构建响应
            response_parts = []
            
            # 上下文和意图
            response_parts.append(f"🎯 检测到的上下文: {prompt_result['context'].value}")
            response_parts.append(f"💡 用户意图: {prompt_result['intent']['primary']}")
            response_parts.append("")
            
            # 智能提示
            if prompt_result["prompts"]:
                response_parts.append("📝 智能提示:")
                for prompt in prompt_result["prompts"][:3]:
                    emoji = self._get_prompt_emoji(prompt["type"])
                    response_parts.append(f"{emoji} {prompt['text']}")
                response_parts.append("")
                
            # 建议
            if include_suggestions and prompt_result["suggestions"]:
                response_parts.append("💭 建议:")
                for suggestion in prompt_result["suggestions"]:
                    response_parts.append(f"• {suggestion}")
                response_parts.append("")
                
            # 相关话题
            if prompt_result["related_topics"]:
                response_parts.append(f"🔗 相关话题: {', '.join(prompt_result['related_topics'])}")
                
            # 学习路径
            if prompt_result["learning_path"]:
                response_parts.append("\n📚 推荐学习路径:")
                for step in prompt_result["learning_path"]:
                    response_parts.append(
                        f"{step['step']}. {step['topic']} ({step['duration']})"
                    )
                    
            return [types.TextContent(type="text", text="\n".join(response_parts))]
            
        except Exception as e:
            logger.error(f"Smart prompt generation failed: {e}")
            return [types.TextContent(
                type="text",
                text=f"生成智能提示时出错: {str(e)}"
            )]
    
    async def _handle_system_status_tool(self, arguments: Dict[str, Any]) -> list[types.TextContent]:
        """处理系统状态工具调用"""
        include_errors = arguments.get("include_errors", True)
        include_performance = arguments.get("include_performance", True)
        include_optimization = arguments.get("include_optimization", True)
        
        response_parts = ["📊 Sage 系统状态报告\n"]
        
        # 错误统计
        if include_errors:
            error_summary = error_handler.get_error_summary()
            response_parts.extend([
                "**错误统计**",
                f"• 总错误数: {error_summary['total_errors']}",
                f"• 错误分布: {error_summary['error_distribution']}",
                ""
            ])
            
            if error_summary["recent_errors"]:
                response_parts.append("最近错误:")
                for error in error_summary["recent_errors"][-3:]:
                    response_parts.append(
                        f"  - [{error['severity']}] {error['type']}: {error['message']}"
                    )
                response_parts.append("")
                
        # 性能指标
        if include_performance:
            perf_summary = performance_monitor.get_performance_summary()
            sys_metrics = perf_summary["system_metrics"]
            
            response_parts.extend([
                "**系统性能**",
                f"• CPU使用率: {sys_metrics['cpu_usage']:.1f}%",
                f"• 内存使用率: {sys_metrics['memory_usage']:.1f}%",
                f"• 可用内存: {sys_metrics['memory_available_mb']:.1f} MB",
                f"• 磁盘使用率: {sys_metrics['disk_usage']:.1f}%",
                ""
            ])
            
            # 操作统计
            if perf_summary["operation_stats"]:
                response_parts.append("操作性能:")
                for op_name, stats in list(perf_summary["operation_stats"].items())[:3]:
                    response_parts.append(
                        f"  - {op_name}: 平均{stats['avg']:.2f}s "
                        f"(最小{stats['min']:.2f}s, 最大{stats['max']:.2f}s)"
                    )
                response_parts.append("")
                
        # 优化建议
        if include_optimization:
            recommendations = optimization_engine.analyze_and_optimize()
            
            if recommendations:
                response_parts.append("**优化建议**")
                for rec in recommendations:
                    status_emoji = "✅" if rec["status"] == "applied" else "❌"
                    response_parts.append(
                        f"{status_emoji} {rec['description']}"
                    )
                response_parts.append("")
                
        # 资源状态
        resource_status = resource_manager.get_resource_status()
        response_parts.extend([
            "**资源状态**",
            f"• 当前操作数: {resource_status['current_operations']}/{resource_status['max_operations']}",
            f"• 内存使用: {resource_status['memory_usage_mb']:.1f}/{resource_status['memory_limit_mb']} MB",
            ""
        ])
        
        return [types.TextContent(type="text", text="\n".join(response_parts))]
    
    async def _handle_status_command(self) -> list[types.TextContent]:
        """处理 /SAGE-STATUS 命令"""
        # 使用系统状态工具
        return await self._handle_system_status_tool({
            "include_errors": True,
            "include_performance": True,
            "include_optimization": True
        })
    
    def _get_prompt_emoji(self, prompt_type: str) -> str:
        """获取提示类型对应的emoji"""
        emoji_map = {
            PromptType.CONTEXTUAL.value: "🎯",
            PromptType.SUGGESTIVE.value: "💡",
            PromptType.CORRECTIVE.value: "⚠️",
            PromptType.EXPLORATORY.value: "🔍",
            PromptType.EDUCATIONAL.value: "📚"
        }
        return emoji_map.get(prompt_type, "📝")
    
    def _get_intelligent_mode_prompt(self) -> str:
        """获取智能助手模式提示"""
        return """你现在处于 Sage 智能助手模式（完整版）。

这是一个集成了所有高级功能的智能模式：

🧠 **核心能力**
1. 自动记忆管理 - 智能保存和检索对话历史
2. 上下文感知 - 理解用户意图和对话上下文
3. 智能提示 - 提供个性化的建议和引导
4. 性能优化 - 自动监控和优化系统性能
5. 错误恢复 - 智能处理错误并尝试恢复

📋 **工作流程**
1. 分析用户输入，理解意图和上下文
2. 自动注入相关历史记忆
3. 生成智能提示和建议
4. 提供准确、有帮助的回答
5. 自动保存重要对话内容
6. 持续优化响应质量

🎯 **使用原则**
• 主动提供有价值的信息和建议
• 基于历史对话保持连贯性
• 适应用户的技能水平和学习风格
• 在出现问题时提供清晰的解决方案
• 保持友好、专业的交流方式

💡 **可用命令**
• /SAGE-STATUS - 查看系统状态
• /SAGE-MODE off - 退出智能模式
• 其他所有 Sage 命令都可正常使用

记住：所有高级功能都在后台自动运行，为用户提供无缝的智能体验。"""
    
    def _get_learning_mode_prompt(self) -> str:
        """获取学习辅导模式提示"""
        return """你现在处于 Sage 学习辅导模式。

🎓 **模式特点**
• 循序渐进的教学方法
• 提供详细的解释和示例
• 主动推荐学习路径
• 跟踪学习进度
• 适应不同的学习风格

📚 **教学原则**
1. 从基础概念开始，逐步深入
2. 使用生动的例子和类比
3. 鼓励提问和探索
4. 提供练习和实践建议
5. 定期总结和复习要点

💡 **互动方式**
• 主动询问用户的理解程度
• 根据反馈调整教学节奏
• 提供相关资源和拓展阅读
• 创建个性化的学习计划

使用 /SAGE-MODE off 退出学习模式。"""
    
    def _get_debug_mode_prompt(self) -> str:
        """获取调试助手模式提示"""
        return """你现在处于 Sage 调试助手模式。

🔧 **模式特点**
• 系统化的问题诊断
• 逐步引导调试过程
• 提供错误原因分析
• 建议解决方案
• 预防类似问题

🐛 **调试流程**
1. 理解错误症状和上下文
2. 分析可能的原因
3. 提供诊断步骤
4. 指导修复过程
5. 验证问题解决
6. 提供预防建议

💡 **辅助功能**
• 解释错误信息含义
• 提供调试工具使用指南
• 分享常见问题解决方案
• 记录调试历史供参考

使用 /SAGE-MODE off 退出调试模式。"""
    
    async def run(self):
        """运行 MCP 服务器"""
        # 启动性能优化定时任务
        asyncio.create_task(self._optimization_loop())
        
        # 运行服务器
        async with mcp.server.stdio.stdio_server() as (read_stream, write_stream):
            await self.server.run(
                read_stream,
                write_stream,
                InitializationOptions(
                    server_name="sage-memory-v4-final",
                    server_version="4.0.0",
                    capabilities=self.server.get_capabilities(
                        notification_options=NotificationOptions(),
                        experimental_capabilities={
                            "auto_context_injection": True,
                            "auto_save": True,
                            "conversation_tracking": True,
                            "advanced_session_management": True,
                            "memory_analysis": True,
                            "smart_prompts": True,
                            "error_handling": True,
                            "performance_optimization": True
                        }
                    )
                )
            )
    
    async def _optimization_loop(self):
        """优化循环任务"""
        while True:
            try:
                # 每5分钟执行一次优化
                await asyncio.sleep(300)
                
                if self._enable_monitoring:
                    # 分析并优化
                    recommendations = optimization_engine.analyze_and_optimize()
                    
                    if recommendations:
                        logger.info(f"Applied {len(recommendations)} optimizations")
                        
            except Exception as e:
                logger.error(f"Optimization loop error: {e}")


async def main():
    """主函数"""
    try:
        # 检查系统资源
        if not await resource_manager.check_resources():
            logger.warning("System resources are limited, some features may be restricted")
            
        # 创建并运行最终版服务器
        sage_server = FinalSageMCPServer()
        await sage_server.run()
        
    except Exception as e:
        # 记录严重错误
        error_handler.handle_error(e, {"startup": True}, ErrorSeverity.CRITICAL)
        logger.critical(f"Server startup failed: {e}")
        raise


if __name__ == "__main__":
    asyncio.run(main())