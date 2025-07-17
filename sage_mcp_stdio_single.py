#\!/usr/bin/env python3
# -*- coding: utf-8 -*-
#!/usr/bin/env python3
"""
Sage MCP stdio server (Single Container Version)
基于 sage_core 的纯 STDIO 实现，专为单容器部署优化
完全符合 MCP 协议规范，不依赖 HTTP 后端
"""

import asyncio
import json
import logging
import os
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent))

# Import MCP SDK components
from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.server.models import InitializationOptions
from mcp.types import (
    Tool,
    TextContent,
    ServerCapabilities,
    ToolsCapability,
    PromptMessage,
    Prompt,
    GetPromptResult,
    PromptsCapability,
    Resource,
    ResourcesCapability,
    ResourceContents
)

# Import sage_core
from sage_core import SageCore, MemoryContent, SearchOptions

# Configure logging - use container log path
log_dir = os.environ.get('SAGE_LOG_DIR', '/var/log/sage')
os.makedirs(log_dir, exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[logging.FileHandler(os.path.join(log_dir, 'sage_mcp_stdio.log'))]
)
logger = logging.getLogger(__name__)


class SageMCPStdioServerV3:
    """MCP stdio server 基于 sage_core 的实现"""
    
    def __init__(self):
        self.server = Server("sage")
        self.sage_core = SageCore()
        self._register_handlers()
        logger.info("Sage MCP stdio server v3 initialized")
        
    def _register_handlers(self):
        """注册 MCP 协议处理器"""
        
        @self.server.list_tools()
        async def handle_list_tools() -> List[Tool]:
            """列出可用工具"""
            logger.info("Handling list_tools request")
            
            return [
                Tool(
                    name="save_conversation",
                    description="保存用户和助手的对话到记忆系统",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "user_prompt": {
                                "type": "string",
                                "description": "用户的输入内容"
                            },
                            "assistant_response": {
                                "type": "string",
                                "description": "助手的回复内容"
                            },
                            "metadata": {
                                "type": "object",
                                "description": "可选的元数据",
                                "properties": {}
                            }
                        },
                        "required": ["user_prompt", "assistant_response"]
                    }
                ),
                Tool(
                    name="get_context",
                    description="根据查询获取相关的历史上下文",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "query": {
                                "type": "string",
                                "description": "查询内容"
                            },
                            "max_results": {
                                "type": "integer",
                                "description": "最大返回结果数",
                                "default": 10
                            }
                        },
                        "required": ["query"]
                    }
                ),
                Tool(
                    name="search_memory",
                    description="搜索记忆库中的历史对话",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "query": {
                                "type": "string",
                                "description": "搜索查询"
                            },
                            "limit": {
                                "type": "integer",
                                "description": "返回结果数量限制",
                                "default": 10
                            },
                            "strategy": {
                                "type": "string",
                                "description": "搜索策略",
                                "enum": ["default", "semantic", "recent"],
                                "default": "default"
                            },
                            "session_id": {
                                "type": "string",
                                "description": "可选的会话ID过滤"
                            }
                        },
                        "required": ["query"]
                    }
                ),
                Tool(
                    name="manage_session",
                    description="管理会话（创建、切换、查看）",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "action": {
                                "type": "string",
                                "description": "操作类型",
                                "enum": ["create", "switch", "info", "list"]
                            },
                            "session_id": {
                                "type": "string",
                                "description": "会话ID（switch和info操作需要）"
                            }
                        },
                        "required": ["action"]
                    }
                ),
                Tool(
                    name="analyze_memory",
                    description="分析记忆库，生成洞察和模式",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "session_id": {
                                "type": "string",
                                "description": "要分析的会话ID（可选）"
                            },
                            "analysis_type": {
                                "type": "string",
                                "description": "分析类型",
                                "enum": ["general", "patterns", "insights"],
                                "default": "general"
                            }
                        }
                    }
                ),
                Tool(
                    name="generate_prompt",
                    description="基于上下文生成智能提示",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "context": {
                                "type": "string",
                                "description": "上下文信息"
                            },
                            "style": {
                                "type": "string",
                                "description": "提示风格",
                                "enum": ["default", "question", "suggestion"],
                                "default": "default"
                            }
                        },
                        "required": ["context"]
                    }
                ),
                Tool(
                    name="export_session",
                    description="导出会话数据",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "session_id": {
                                "type": "string",
                                "description": "要导出的会话ID"
                            },
                            "format": {
                                "type": "string",
                                "description": "导出格式",
                                "enum": ["json", "markdown"],
                                "default": "json"
                            }
                        },
                        "required": ["session_id"]
                    }
                ),
                Tool(
                    name="get_status",
                    description="获取 Sage 服务状态",
                    inputSchema={
                        "type": "object",
                        "properties": {}
                    }
                )
            ]
            
        @self.server.call_tool()
        async def handle_call_tool(name: str, arguments: Dict[str, Any]) -> List[TextContent]:
            """调用工具"""
            logger.info(f"Handling call_tool request: {name}")
            
            try:
                # 确保服务已初始化
                if not self.sage_core._initialized:
                    await self.sage_core.initialize({})
                
                if name == "save_conversation":
                    content = MemoryContent(
                        user_input=arguments["user_prompt"],
                        assistant_response=arguments["assistant_response"],
                        metadata=arguments.get("metadata", {})
                    )
                    memory_id = await self.sage_core.save_memory(content)
                    return [TextContent(
                        type="text",
                        text=f"对话已保存，记忆ID: {memory_id}"
                    )]
                
                elif name == "get_context":
                    context = await self.sage_core.get_context(
                        query=arguments["query"],
                        max_results=arguments.get("max_results", 10)
                    )
                    return [TextContent(type="text", text=context)]
                
                elif name == "search_memory":
                    options = SearchOptions(
                        limit=arguments.get("limit", 10),
                        strategy=arguments.get("strategy", "default"),
                        session_id=arguments.get("session_id")
                    )
                    results = await self.sage_core.search_memory(
                        query=arguments["query"],
                        options=options
                    )
                    
                    # 格式化结果
                    if results:
                        output_lines = [f"找到 {len(results)} 条相关记忆：\n"]
                        for i, memory in enumerate(results, 1):
                            output_lines.append(f"\n[记忆 {i}]")
                            output_lines.append(f"时间: {memory['created_at']}")
                            if 'similarity' in memory:
                                output_lines.append(f"相关度: {memory['similarity']:.2f}")
                            output_lines.append(f"用户: {memory['user_input']}")
                            output_lines.append(f"助手: {memory['assistant_response']}")
                            output_lines.append("-" * 40)
                        output = "\n".join(output_lines)
                    else:
                        output = "没有找到相关记忆"
                    
                    return [TextContent(type="text", text=output)]
                
                elif name == "manage_session":
                    session_info = await self.sage_core.manage_session(
                        action=arguments["action"],
                        session_id=arguments.get("session_id")
                    )
                    
                    output_lines = [f"会话操作: {arguments['action']}\n"]
                    output_lines.append(f"会话ID: {session_info.session_id}")
                    output_lines.append(f"记忆数量: {session_info.memory_count}")
                    output_lines.append(f"创建时间: {session_info.created_at}")
                    output_lines.append(f"最后活跃: {session_info.last_active}")
                    
                    if arguments['action'] == 'list' and 'all_sessions' in session_info.metadata:
                        output_lines.append("\n所有会话:")
                        for sess in session_info.metadata['all_sessions']:
                            status = "当前" if sess['is_current'] else ""
                            output_lines.append(f"  - {sess['session_id']} ({sess['memory_count']}条记忆) {status}")
                    
                    output = "\n".join(output_lines)
                    return [TextContent(type="text", text=output)]
                
                elif name == "analyze_memory":
                    analysis = await self.sage_core.analyze_memory(
                        session_id=arguments.get("session_id"),
                        analysis_type=arguments.get("analysis_type", "general")
                    )
                    
                    output_lines = ["记忆分析结果:\n"]
                    
                    if analysis.patterns:
                        output_lines.append("\n发现的模式:")
                        for pattern in analysis.patterns:
                            output_lines.append(f"  - {pattern['description']}: {pattern['data']}")
                    
                    if analysis.insights:
                        output_lines.append("\n洞察:")
                        for insight in analysis.insights:
                            output_lines.append(f"  - {insight}")
                    
                    if analysis.suggestions:
                        output_lines.append("\n建议:")
                        for suggestion in analysis.suggestions:
                            output_lines.append(f"  - {suggestion}")
                    
                    output = "\n".join(output_lines)
                    return [TextContent(type="text", text=output)]
                
                elif name == "generate_prompt":
                    prompt = await self.sage_core.generate_prompt(
                        context=arguments["context"],
                        style=arguments.get("style", "default")
                    )
                    return [TextContent(type="text", text=prompt)]
                
                elif name == "export_session":
                    data = await self.sage_core.export_session(
                        session_id=arguments["session_id"],
                        format=arguments.get("format", "json")
                    )
                    
                    # 将字节数据转换为字符串
                    output = data.decode('utf-8')
                    
                    if arguments.get("format") == "json":
                        # 格式化 JSON 输出
                        try:
                            json_data = json.loads(output)
                            output = json.dumps(json_data, indent=2, ensure_ascii=False)
                        except:
                            pass
                    
                    return [TextContent(type="text", text=output)]
                
                elif name == "get_status":
                    status = await self.sage_core.get_status()
                    output = json.dumps(status, indent=2, ensure_ascii=False)
                    return [TextContent(type="text", text=output)]
                
                else:
                    raise ValueError(f"未知的工具: {name}")
                    
            except Exception as e:
                logger.error(f"Tool execution failed: {e}")
                return [TextContent(
                    type="text",
                    text=f"执行失败: {str(e)}"
                )]
                
        @self.server.list_prompts()
        async def handle_list_prompts() -> List[Prompt]:
            """列出可用的提示模板"""
            logger.info("Handling list_prompts request")
            
            return [
                Prompt(
                    name="auto_context_injection",
                    description="自动注入相关历史上下文的提示模板",
                    arguments=[
                        {
                            "name": "user_input",
                            "description": "用户的输入内容",
                            "required": True
                        }
                    ]
                ),
                Prompt(
                    name="smart_suggestion",
                    description="基于历史记忆生成智能建议",
                    arguments=[
                        {
                            "name": "topic",
                            "description": "话题或主题",
                            "required": True
                        }
                    ]
                ),
                Prompt(
                    name="memory_summary",
                    description="生成记忆摘要",
                    arguments=[
                        {
                            "name": "session_id",
                            "description": "会话ID（可选）",
                            "required": False
                        },
                        {
                            "name": "limit",
                            "description": "摘要的记忆数量",
                            "required": False
                        }
                    ]
                )
            ]
            
        @self.server.get_prompt()
        async def handle_get_prompt(name: str, arguments: Dict[str, Any]) -> GetPromptResult:
            """获取提示模板内容"""
            logger.info(f"Handling get_prompt request: {name}")
            
            # 确保服务已初始化
            if not self.sage_core._initialized:
                await self.sage_core.initialize({})
            
            if name == "auto_context_injection":
                user_input = arguments.get("user_input", "")
                
                # 获取相关上下文
                context = await self.sage_core.get_context(user_input, max_results=5)
                
                messages = []
                messages.append(
                    PromptMessage(
                        role="user",
                        content=TextContent(type="text", text=user_input)
                    )
                )
                
                if context and context != "没有找到相关的历史记忆。":
                    messages.append(
                        PromptMessage(
                            role="assistant",
                            content=TextContent(
                                type="text",
                                text=f"基于以下相关历史记忆：\n\n{context}\n\n请回答用户的问题。"
                            )
                        )
                    )
                
                return GetPromptResult(
                    description="已注入相关历史上下文",
                    messages=messages
                )
            
            elif name == "smart_suggestion":
                topic = arguments.get("topic", "")
                
                # 搜索相关记忆
                options = SearchOptions(limit=10, strategy="semantic")
                memories = await self.sage_core.search_memory(topic, options)
                
                # 生成建议
                suggestion_text = f"关于\"{topic}\"的智能建议：\n\n"
                
                if memories:
                    # 分析记忆中的模式
                    topics_discussed = set()
                    for memory in memories:
                        # 简单的主题提取
                        words = memory['user_input'].split() + memory['assistant_response'].split()
                        topics_discussed.update(w for w in words if len(w) > 3)
                    
                    suggestion_text += "基于历史对话，您可能对以下方面感兴趣：\n"
                    for i, topic_word in enumerate(list(topics_discussed)[:5], 1):
                        suggestion_text += f"{i}. 深入了解{topic_word}\n"
                else:
                    suggestion_text += "这是一个新话题，让我们开始探索吧！"
                
                # 添加通用建议
                prompt = await self.sage_core.generate_prompt(topic, style="suggestion")
                suggestion_text += f"\n{prompt}"
                
                return GetPromptResult(
                    description="基于历史记忆的智能建议",
                    messages=[
                        PromptMessage(
                            role="assistant",
                            content=TextContent(type="text", text=suggestion_text)
                        )
                    ]
                )
            
            elif name == "memory_summary":
                session_id = arguments.get("session_id")
                limit = arguments.get("limit", 10)
                
                # 获取记忆
                if session_id:
                    memories = await self.sage_core.memory_manager.storage.get_session_memories(
                        session_id, limit=limit
                    )
                else:
                    # 获取最近的记忆
                    options = SearchOptions(limit=limit, strategy="recent")
                    memories = await self.sage_core.search_memory("", options)
                
                # 生成摘要
                summary_lines = ["记忆摘要：\n"]
                
                if memories:
                    for i, memory in enumerate(memories, 1):
                        summary_lines.append(f"{i}. {memory['created_at'][:10]}")
                        summary_lines.append(f"   Q: {memory['user_input'][:50]}...")
                        summary_lines.append(f"   A: {memory['assistant_response'][:50]}...")
                        summary_lines.append("")
                else:
                    summary_lines.append("暂无记忆记录")
                
                summary_text = "\n".join(summary_lines)
                
                return GetPromptResult(
                    description="记忆摘要",
                    messages=[
                        PromptMessage(
                            role="assistant",
                            content=TextContent(type="text", text=summary_text)
                        )
                    ]
                )
            
            raise ValueError(f"Unknown prompt: {name}")
        
        @self.server.list_resources()
        async def handle_list_resources() -> List[Resource]:
            """列出可用资源"""
            logger.info("Handling list_resources request")
            
            # 确保服务已初始化
            if not self.sage_core._initialized:
                await self.sage_core.initialize({})
            
            resources = []
            
            # 添加当前会话资源
            session_info = await self.sage_core.memory_manager.get_session_info()
            resources.append(
                Resource(
                    uri=f"sage://session/{session_info['session_id']}",
                    name=f"当前会话 ({session_info['memory_count']} 条记忆)",
                    description="当前活跃的会话",
                    mimeType="application/json"
                )
            )
            
            # 添加所有会话列表资源
            resources.append(
                Resource(
                    uri="sage://sessions/list",
                    name="所有会话列表",
                    description="系统中所有会话的列表",
                    mimeType="application/json"
                )
            )
            
            # 添加系统状态资源
            resources.append(
                Resource(
                    uri="sage://system/status",
                    name="系统状态",
                    description="Sage 系统的当前状态",
                    mimeType="application/json"
                )
            )
            
            return resources
        
        @self.server.read_resource()
        async def handle_read_resource(uri: str) -> ResourceContents:
            """读取资源内容"""
            logger.info(f"Handling read_resource request: {uri}")
            
            # 确保服务已初始化
            if not self.sage_core._initialized:
                await self.sage_core.initialize({})
            
            if uri.startswith("sage://session/"):
                # 读取特定会话
                session_id = uri.split("/")[-1]
                memories = await self.sage_core.memory_manager.storage.get_session_memories(session_id)
                
                content = {
                    "session_id": session_id,
                    "memory_count": len(memories),
                    "memories": memories[:10]  # 限制返回数量
                }
                
                return ResourceContents(
                    uri=uri,
                    mimeType="application/json",
                    text=json.dumps(content, indent=2, ensure_ascii=False)
                )
            
            elif uri == "sage://sessions/list":
                # 读取会话列表
                sessions = await self.sage_core.memory_manager.list_sessions()
                
                return ResourceContents(
                    uri=uri,
                    mimeType="application/json",
                    text=json.dumps(sessions, indent=2, ensure_ascii=False)
                )
            
            elif uri == "sage://system/status":
                # 读取系统状态
                status = await self.sage_core.get_status()
                
                return ResourceContents(
                    uri=uri,
                    mimeType="application/json",
                    text=json.dumps(status, indent=2, ensure_ascii=False)
                )
            
            else:
                raise ValueError(f"Unknown resource URI: {uri}")
    
    async def run(self):
        """运行 MCP 服务器"""
        logger.info("Starting Sage MCP stdio server v3...")
        print("Initializing Sage MCP server...", file=sys.stderr)
        sys.stderr.flush()
        
        # 初始化 sage_core
        config = {
            "database": {
                "host": os.getenv("DB_HOST", "localhost"),
                "port": int(os.getenv("DB_PORT", "5432")),
                "database": os.getenv("DB_NAME", "sage_memory"),
                "user": os.getenv("DB_USER", "sage"),
                "password": os.getenv("DB_PASSWORD", "sage123")
            },
            "embedding": {
                "model": os.getenv("EMBEDDING_MODEL", "Qwen/Qwen3-Embedding-8B"),
                "device": os.getenv("EMBEDDING_DEVICE", "cpu")
            }
        }
        
        try:
            await self.sage_core.initialize(config)
            logger.info("Sage core initialized successfully")
        except Exception as e:
            logger.warning(f"Sage core initialization warning: {e}")
            # 继续运行，某些功能可能受限
        
        # 运行 stdio 服务器
        print("Starting STDIO server...", file=sys.stderr)
        sys.stderr.flush()
        
        async with stdio_server() as (read_stream, write_stream):
            print("STDIO server streams created, running MCP server...", file=sys.stderr)
            sys.stderr.flush()
            
            # 输出 ready 信号给 Claude CLI
            print('{"type": "ready"}', flush=True)
            
            await self.server.run(
                read_stream,
                write_stream,
                InitializationOptions(
                    server_name="sage",
                    server_version="3.0.0",
                    capabilities=ServerCapabilities(
                        tools=ToolsCapability(
                            # 支持工具调用
                        ),
                        prompts=PromptsCapability(
                            # 支持提示模板
                        ),
                        resources=ResourcesCapability(
                            # 支持资源访问
                        )
                    )
                )
            )
            
    async def cleanup(self):
        """清理资源"""
        if self.sage_core._initialized:
            await self.sage_core.cleanup()
            logger.info("Sage core cleaned up")


async def main():
    """主函数"""
    print("Starting Sage MCP STDIO server...", file=sys.stderr)
    sys.stderr.flush()
    
    server = SageMCPStdioServerV3()
    try:
        await server.run()
    except KeyboardInterrupt:
        logger.info("Server stopped by user")
        print("Server stopped by user", file=sys.stderr)
    except Exception as e:
        logger.error(f"Server error: {e}")
        print(f"Server error: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc(file=sys.stderr)
        raise
    finally:
        await server.cleanup()


if __name__ == "__main__":
    # 运行服务器
    asyncio.run(main())