#!/usr/bin/env python3
"""
Sage MCP Server V3 Advanced - 集成高级会话管理和记忆分析
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

# Import V2 components
from sage_mcp_v2_enhanced import EnhancedSageMCPServer
from sage_mcp_stdio_v2 import CommandType

# Import V3 components
from sage_session_manager_v2 import (
    EnhancedSessionManager, 
    SessionStatus, 
    SessionSearchType
)
from sage_memory_analyzer import (
    MemoryAnalyzer,
    AnalysisType
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
    handlers=[logging.FileHandler('/tmp/sage_mcp_v3_advanced.log')]
)
logger = logging.getLogger(__name__)


class AdvancedSageMCPServer(EnhancedSageMCPServer):
    """高级版 Sage MCP 服务器 - 支持完善的会话管理和记忆分析"""
    
    def __init__(self):
        # 初始化父类
        super().__init__()
        
        # 初始化增强组件
        self.enhanced_session_manager = EnhancedSessionManager(self.memory_adapter)
        self.memory_analyzer = MemoryAnalyzer(self.memory_provider, self.retrieval_engine)
        
        # 更新服务器信息
        self.server = Server("sage-memory-v3-advanced")
        
        # 重新注册处理器以添加新功能
        self._register_advanced_handlers()
        
        logger.info("Advanced Sage MCP Server V3 initialized")
        
    def _register_advanced_handlers(self):
        """注册高级处理器"""
        # 首先调用父类的注册
        super()._register_handlers()
        
        # 覆盖工具列表以添加新工具
        @self.server.list_tools()
        async def handle_list_tools() -> list[types.Tool]:
            """列出所有可用工具（包括V3新增）"""
            base_tools = await super().handle_list_tools()
            
            # 添加V3工具
            advanced_tools = [
                types.Tool(
                    name="sage_session_advanced",
                    description="高级会话管理功能 - 搜索、导出、分析会话",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "action": {
                                "type": "string",
                                "enum": ["search", "export", "analyze", "archive"],
                                "description": "操作类型"
                            },
                            "params": {
                                "type": "object",
                                "description": "操作参数"
                            }
                        },
                        "required": ["action"]
                    }
                ),
                types.Tool(
                    name="sage_memory_analysis",
                    description="记忆深度分析 - 话题聚类、时间模式、知识图谱等",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "analysis_type": {
                                "type": "string",
                                "enum": ["topic_clustering", "temporal_patterns", 
                                        "interaction_flow", "knowledge_graph", 
                                        "sentiment_analysis"],
                                "description": "分析类型"
                            },
                            "params": {
                                "type": "object",
                                "description": "分析参数（可选）"
                            }
                        },
                        "required": ["analysis_type"]
                    }
                )
            ]
            
            return base_tools + advanced_tools
        
        # 扩展工具调用处理
        original_handle_call_tool = self.server._tool_handlers.get("call_tool")
        
        @self.server.call_tool()
        async def handle_call_tool(name: str, arguments: dict) -> list[types.TextContent]:
            """处理工具调用（包括V3新增）"""
            
            # 处理V3特有的工具
            if name == "sage_session_advanced":
                return await self._handle_advanced_session_tool(arguments)
            elif name == "sage_memory_analysis":
                return await self._handle_memory_analysis_tool(arguments)
            else:
                # 调用父类处理
                return await super().handle_call_tool(name, arguments)
    
    async def handle_command(self, command_text: str) -> list[types.TextContent]:
        """处理 Sage 命令（扩展V3功能）"""
        
        # 解析命令
        cmd_type, args = self.command_parser.parse(command_text)
        
        # 处理V3增强的命令
        if cmd_type == CommandType.SAGE_SESSION:
            return await self._handle_enhanced_session_command(args)
        elif cmd_type == CommandType.SAGE_ANALYZE:
            return await self._handle_enhanced_analyze_command(args)
        elif cmd_type == CommandType.SAGE_RECALL:
            return await self._handle_enhanced_recall_command(args)
        elif cmd_type == CommandType.SAGE_EXPORT:
            return await self._handle_enhanced_export_command(args)
        else:
            # 其他命令调用父类处理
            return await super().handle_command(command_text)
    
    async def _handle_enhanced_session_command(self, args: Dict[str, Any]) -> list[types.TextContent]:
        """处理增强的会话命令"""
        action = args.get("action", "")
        
        if action == "start":
            topic = args.get("topic", "")
            if not topic:
                return [types.TextContent(
                    type="text",
                    text="请提供会话主题。用法：/SAGE-SESSION start <主题>"
                )]
                
            # 创建新会话
            session = self.enhanced_session_manager.create_session(topic)
            
            # 同步到对话流程管理器
            if self.flow_manager.mode_enabled:
                self.flow_manager.auto_save.current_tracking["metadata"]["session_id"] = session["id"]
            
            return [types.TextContent(
                type="text",
                text=f"""🎯 高级会话已创建！

📌 会话信息：
• ID: {session['id']}
• 主题: {topic}
• 状态: 活动中
• 开始时间: {session['start_time'].strftime('%Y-%m-%d %H:%M:%S')}

✨ 新功能：
• 自动统计消息和工具调用
• 支持会话搜索和导出
• 智能会话分析
• 上下文链跟踪

使用 /SAGE-SESSION search <关键词> 搜索会话历史"""
            )]
            
        elif action == "search":
            # 搜索会话
            query = args.get("topic", "")  # 兼容旧参数名
            if not query:
                return [types.TextContent(
                    type="text",
                    text="请提供搜索关键词。用法：/SAGE-SESSION search <关键词>"
                )]
                
            results = self.enhanced_session_manager.search_sessions(
                SessionSearchType.BY_KEYWORD, query
            )
            
            if not results:
                return [types.TextContent(
                    type="text",
                    text=f"没有找到包含 '{query}' 的会话。"
                )]
                
            # 格式化搜索结果
            response_parts = [f"🔍 搜索 '{query}' 的结果（找到 {len(results)} 个会话）：\n"]
            
            for i, session in enumerate(results[:5], 1):  # 最多显示5个
                duration = session['duration'] / 60 if session['duration'] else 0
                response_parts.append(
                    f"{i}. **{session['topic']}**\n"
                    f"   ID: {session['id']}\n"
                    f"   状态: {session['status']}\n"
                    f"   消息数: {session['statistics']['message_count']}\n"
                    f"   持续时间: {duration:.1f} 分钟\n"
                )
                
            return [types.TextContent(type="text", text="\n".join(response_parts))]
            
        elif action == "analyze":
            # 分析当前会话
            if not self.enhanced_session_manager.active_session:
                return [types.TextContent(
                    type="text",
                    text="没有活动的会话。请先开始一个会话。"
                )]
                
            analytics = self.enhanced_session_manager.get_session_analytics(
                self.enhanced_session_manager.active_session["id"]
            )
            
            return [types.TextContent(
                type="text",
                text=f"""📊 当前会话分析

基础统计：
• 总消息数: {analytics['total_messages']}
• 平均消息数: {analytics['average_messages_per_session']:.1f}
• 持续时间: {analytics['total_duration_seconds']:.1f} 秒
• 上下文注入: {analytics['total_context_injections']} 次

活跃时段：
{self._format_activity_hours(analytics.get('activity_by_hour', {}))}

热门话题词：
{self._format_top_topics(analytics.get('top_topics', []))}"""
            )]
            
        # 其他动作保持原有逻辑
        else:
            return await super()._handle_sage_session(args)
    
    async def _handle_enhanced_analyze_command(self, args: Dict[str, Any]) -> list[types.TextContent]:
        """处理增强的分析命令"""
        
        # 获取基础统计
        try:
            base_stats = self.memory_provider.get_memory_stats()
        except:
            base_stats = {"total": "N/A", "error": "无法获取基础统计"}
            
        # 获取会话统计
        session_analytics = self.enhanced_session_manager.get_session_analytics()
        
        # 执行快速记忆分析
        try:
            # 话题分析
            topic_analysis = await self.memory_analyzer.analyze_memory_patterns(
                AnalysisType.TOPIC_CLUSTERING,
                limit=100  # 限制数量以提高速度
            )
            
            # 时间模式
            temporal_analysis = await self.memory_analyzer.analyze_memory_patterns(
                AnalysisType.TEMPORAL_PATTERNS,
                limit=100
            )
        except Exception as e:
            logger.error(f"Memory analysis failed: {e}")
            topic_analysis = {"error": str(e)}
            temporal_analysis = {"error": str(e)}
            
        # 构建报告
        response_parts = ["📊 Sage 记忆系统综合分析报告\n"]
        
        # 基础统计
        response_parts.extend([
            "**1. 记忆库统计**",
            f"• 总记忆数: {base_stats.get('total', 'N/A')}",
            f"• 总会话数: {session_analytics['total_sessions']}",
            f"• 平均会话长度: {session_analytics['average_messages_per_session']:.1f} 条消息",
            ""
        ])
        
        # 话题分析
        if not topic_analysis.get("error"):
            response_parts.extend([
                "**2. 热门话题**",
                self._format_top_keywords(topic_analysis.get("top_keywords", {})),
                ""
            ])
            
        # 时间模式
        if not temporal_analysis.get("error"):
            response_parts.extend([
                "**3. 活动模式**",
                f"• 活跃天数: {temporal_analysis.get('temporal_span', {}).get('total_days', 0)}",
                f"• 平均交互间隔: {temporal_analysis.get('interaction_gaps', {}).get('average_seconds', 0) / 60:.1f} 分钟",
                ""
            ])
            
        # 会话分布
        response_parts.extend([
            "**4. 会话状态分布**",
            self._format_status_distribution(session_analytics.get("status_distribution", {})),
            ""
        ])
        
        response_parts.append("💡 使用 /SAGE-ANALYZE deep 进行深度分析（需要更多时间）")
        
        return [types.TextContent(type="text", text="\n".join(response_parts))]
    
    async def _handle_enhanced_recall_command(self, args: Dict[str, Any]) -> list[types.TextContent]:
        """处理增强的回忆命令"""
        recall_type = args.get("type", "")
        
        if recall_type == "session":
            # 回忆特定会话
            session_id = args.get("params", "")
            if not session_id:
                # 列出最近的会话
                sessions = self.enhanced_session_manager.search_sessions(
                    SessionSearchType.BY_STATUS, "completed", limit=5
                )
                
                if not sessions:
                    return [types.TextContent(
                        type="text",
                        text="没有已完成的会话。"
                    )]
                    
                response_parts = ["📚 最近完成的会话：\n"]
                for i, session in enumerate(sessions, 1):
                    response_parts.append(
                        f"{i}. {session['topic']} (ID: {session['id']})\n"
                        f"   消息数: {session['statistics']['message_count']}\n"
                        f"   {session.get('summary', '无摘要')[:100]}...\n"
                    )
                    
                return [types.TextContent(type="text", text="\n".join(response_parts))]
                
            # 获取特定会话的详情
            session = self.enhanced_session_manager.sessions.get(session_id)
            if not session:
                return [types.TextContent(
                    type="text",
                    text=f"未找到会话: {session_id}"
                )]
                
            # 显示会话详情
            return [types.TextContent(
                type="text",
                text=self._format_session_details(session)
            )]
            
        # 其他类型调用父类处理
        else:
            return await super()._handle_sage_recall(args)
    
    async def _handle_enhanced_export_command(self, args: Dict[str, Any]) -> list[types.TextContent]:
        """处理增强的导出命令"""
        export_type = args.get("type", "")
        params = args.get("params", "")
        
        if export_type == "session":
            # 导出会话
            if not params:
                # 导出当前会话
                if not self.enhanced_session_manager.active_session:
                    return [types.TextContent(
                        type="text",
                        text="没有活动的会话。请指定会话ID或先开始一个会话。"
                    )]
                session_id = self.enhanced_session_manager.active_session["id"]
            else:
                session_id = params
                
            # 导出为Markdown
            export_content = self.enhanced_session_manager.export_session(
                session_id, "markdown"
            )
            
            if not export_content:
                return [types.TextContent(
                    type="text",
                    text=f"无法导出会话: {session_id}"
                )]
                
            # 保存到文件
            export_path = f"/tmp/sage_session_{session_id}.md"
            try:
                with open(export_path, "w", encoding="utf-8") as f:
                    f.write(export_content)
                    
                return [types.TextContent(
                    type="text",
                    text=f"✅ 会话已导出到: {export_path}\n\n预览:\n{export_content[:500]}..."
                )]
            except Exception as e:
                return [types.TextContent(
                    type="text",
                    text=f"导出失败: {str(e)}"
                )]
                
        elif export_type == "analysis":
            # 导出分析报告
            # TODO: 实现完整的分析报告导出
            return [types.TextContent(
                type="text",
                text="分析报告导出功能正在开发中..."
            )]
            
        else:
            return [types.TextContent(
                type="text",
                text="支持的导出类型：session（会话）, analysis（分析报告）"
            )]
    
    async def _handle_advanced_session_tool(self, arguments: Dict[str, Any]) -> list[types.TextContent]:
        """处理高级会话工具调用"""
        action = arguments.get("action")
        params = arguments.get("params", {})
        
        if action == "search":
            # 会话搜索
            search_type = params.get("type", "keyword")
            query = params.get("query", "")
            
            if search_type == "topic":
                results = self.enhanced_session_manager.search_sessions(
                    SessionSearchType.BY_TOPIC, query
                )
            elif search_type == "date":
                results = self.enhanced_session_manager.search_sessions(
                    SessionSearchType.BY_DATE, query
                )
            else:
                results = self.enhanced_session_manager.search_sessions(
                    SessionSearchType.BY_KEYWORD, query
                )
                
            return [types.TextContent(
                type="text",
                text=f"找到 {len(results)} 个相关会话"
            )]
            
        elif action == "export":
            # 会话导出
            session_id = params.get("session_id", "")
            format = params.get("format", "json")
            
            export_content = self.enhanced_session_manager.export_session(
                session_id, format
            )
            
            return [types.TextContent(
                type="text",
                text=f"会话已导出（{len(export_content)} 字符）"
            )]
            
        elif action == "analyze":
            # 会话分析
            session_id = params.get("session_id")
            analytics = self.enhanced_session_manager.get_session_analytics(session_id)
            
            return [types.TextContent(
                type="text",
                text=f"会话分析完成：{analytics['total_sessions']} 个会话，{analytics['total_messages']} 条消息"
            )]
            
        elif action == "archive":
            # 归档旧会话
            days = params.get("days", 30)
            count = self.enhanced_session_manager.archive_old_sessions(days)
            
            return [types.TextContent(
                type="text",
                text=f"已归档 {count} 个超过 {days} 天的会话"
            )]
            
        else:
            return [types.TextContent(
                type="text",
                text=f"未知的会话操作: {action}"
            )]
    
    async def _handle_memory_analysis_tool(self, arguments: Dict[str, Any]) -> list[types.TextContent]:
        """处理记忆分析工具调用"""
        analysis_type_str = arguments.get("analysis_type")
        params = arguments.get("params", {})
        
        # 转换为枚举类型
        try:
            analysis_type = AnalysisType(analysis_type_str)
        except ValueError:
            return [types.TextContent(
                type="text",
                text=f"未知的分析类型: {analysis_type_str}"
            )]
            
        # 执行分析
        try:
            result = await self.memory_analyzer.analyze_memory_patterns(
                analysis_type,
                time_range=params.get("time_range"),
                limit=params.get("limit", 500)
            )
            
            # 格式化结果
            if analysis_type == AnalysisType.TOPIC_CLUSTERING:
                summary = f"识别到 {result['identified_topics']} 个话题，{result['total_memories']} 条记忆"
            elif analysis_type == AnalysisType.TEMPORAL_PATTERNS:
                summary = f"时间跨度 {result['temporal_span']['total_days']} 天，活动趋势: {result['activity_trends']['trend']}"
            elif analysis_type == AnalysisType.KNOWLEDGE_GRAPH:
                summary = f"构建知识图谱：{result['graph_stats']['total_nodes']} 个节点，{result['graph_stats']['total_edges']} 条边"
            else:
                summary = f"分析完成，返回 {len(str(result))} 字符的数据"
                
            return [types.TextContent(
                type="text",
                text=summary
            )]
            
        except Exception as e:
            logger.error(f"Memory analysis error: {e}")
            return [types.TextContent(
                type="text",
                text=f"分析失败: {str(e)}"
            )]
    
    # 辅助格式化方法
    def _format_activity_hours(self, hour_distribution: Dict[int, int]) -> str:
        """格式化活动时段"""
        if not hour_distribution:
            return "无数据"
            
        sorted_hours = sorted(hour_distribution.items(), key=lambda x: x[1], reverse=True)[:3]
        return "\n".join([f"  • {h}:00 - {count} 次交互" for h, count in sorted_hours])
    
    def _format_top_topics(self, topics: List[Tuple[str, int]]) -> str:
        """格式化热门话题"""
        if not topics:
            return "无数据"
            
        return "\n".join([f"  • {topic}: {count} 次" for topic, count in topics[:5]])
    
    def _format_top_keywords(self, keywords: Dict[str, int]) -> str:
        """格式化热门关键词"""
        if not keywords:
            return "无数据"
            
        sorted_keywords = sorted(keywords.items(), key=lambda x: x[1], reverse=True)[:5]
        return "\n".join([f"  • {kw}: {count} 次" for kw, count in sorted_keywords])
    
    def _format_status_distribution(self, distribution: Dict[str, int]) -> str:
        """格式化状态分布"""
        if not distribution:
            return "无数据"
            
        return "\n".join([f"  • {status}: {count} 个" for status, count in distribution.items()])
    
    def _format_session_details(self, session: Dict[str, Any]) -> str:
        """格式化会话详情"""
        duration = session['duration'] / 60 if session['duration'] else 0
        
        details = [
            f"📋 会话详情：{session['topic']}\n",
            f"**基本信息**",
            f"• ID: {session['id']}",
            f"• 状态: {session['status']}",
            f"• 开始时间: {session['start_time'].strftime('%Y-%m-%d %H:%M:%S')}",
            f"• 持续时间: {duration:.1f} 分钟",
            "",
            f"**统计信息**",
            f"• 总消息数: {session['statistics']['message_count']}",
            f"• 用户消息: {session['statistics']['user_message_count']}",
            f"• 助手消息: {session['statistics']['assistant_message_count']}",
            f"• 工具调用: {session['statistics']['tool_call_count']}",
            f"• 上下文注入: {session['statistics']['context_injections']}",
            ""
        ]
        
        # 添加摘要
        if session.get('summary'):
            details.extend([
                "**会话摘要**",
                session['summary'],
                ""
            ])
            
        # 添加最近的消息
        if session['messages']:
            details.append("**最近消息**")
            for msg in session['messages'][-3:]:  # 最后3条
                timestamp = msg['timestamp'].strftime("%H:%M:%S")
                content_preview = msg['content'][:100] + "..." if len(msg['content']) > 100 else msg['content']
                details.append(f"[{timestamp}] {msg['role']}: {content_preview}")
                
        return "\n".join(details)
    
    async def run(self):
        """运行 MCP 服务器"""
        async with mcp.server.stdio.stdio_server() as (read_stream, write_stream):
            await self.server.run(
                read_stream,
                write_stream,
                InitializationOptions(
                    server_name="sage-memory-v3-advanced",
                    server_version="3.0.0",
                    capabilities=self.server.get_capabilities(
                        notification_options=NotificationOptions(),
                        experimental_capabilities={
                            "auto_context_injection": True,
                            "auto_save": True,
                            "conversation_tracking": True,
                            "advanced_session_management": True,
                            "memory_analysis": True
                        }
                    )
                )
            )


async def main():
    """主函数"""
    try:
        # 创建并运行高级服务器
        sage_server = AdvancedSageMCPServer()
        await sage_server.run()
    except Exception as e:
        logger.error(f"Server error: {e}")
        raise


if __name__ == "__main__":
    asyncio.run(main())