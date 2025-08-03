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
    Resource,
    ResourcesCapability,
    ResourceContents
)

# Import sage_core
from sage_core import MemoryContent, SearchOptions
from sage_core.singleton_manager import get_sage_core
from sage_core.resilience import breaker_manager

# Configure logging - use local log path
log_dir = os.environ.get('SAGE_LOG_DIR', '/Users/jet/Sage/logs')
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
        self.sage_core = None  # 延迟初始化
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
                    name="S",
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
                                "default": int(os.getenv("SAGE_MAX_RESULTS", "10"))
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
                    name="get_status",
                    description="获取 Sage 服务状态",
                    inputSchema={
                        "type": "object",
                        "properties": {}
                    }
                ),
                Tool(
                    name="reset_circuit_breaker",
                    description="手动重置断路器状态",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "all": {
                                "type": "boolean",
                                "description": "是否重置所有断路器",
                                "default": True
                            },
                            "breaker_name": {
                                "type": "string",
                                "description": "指定断路器名称（all为False时生效）"
                            }
                        }
                    }
                )
            ]
            
        @self.server.call_tool()
        async def handle_call_tool(name: str, arguments: Dict[str, Any]) -> List[TextContent]:
            """调用工具"""
            logger.info(f"Handling call_tool request: {name}")
            
            try:
                # 确保获取单例实例
                if self.sage_core is None:
                    self.sage_core = await get_sage_core({})
                
                if name == "S":
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
                    # 从环境变量读取默认值
                    default_max_results = int(os.getenv("SAGE_MAX_RESULTS", "10"))
                    context = await self.sage_core.get_context(
                        query=arguments["query"],
                        max_results=arguments.get("max_results", default_max_results)
                    )
                    return [TextContent(type="text", text=context)]
                
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
                
                elif name == "generate_prompt":
                    prompt = await self.sage_core.generate_prompt(
                        context=arguments["context"],
                        style=arguments.get("style", "default")
                    )
                    return [TextContent(type="text", text=prompt)]
                
                elif name == "get_status":
                    status = await self.sage_core.get_status()
                    output = json.dumps(status, indent=2, ensure_ascii=False)
                    return [TextContent(type="text", text=output)]
                
                elif name == "reset_circuit_breaker":
                    # 获取参数
                    reset_all = arguments.get("all", True)
                    breaker_name = arguments.get("breaker_name")
                    
                    # 记录操作前状态
                    stats_before = breaker_manager.get_all_stats()
                    
                    # 执行重置
                    if reset_all:
                        breaker_manager.reset_all()
                        operation = "重置所有断路器"
                    elif breaker_name:
                        breaker = breaker_manager.get(breaker_name)
                        if breaker:
                            breaker.reset()
                            operation = f"重置断路器: {breaker_name}"
                        else:
                            return [TextContent(
                                type="text",
                                text=f"错误: 断路器 '{breaker_name}' 不存在"
                            )]
                    else:
                        return [TextContent(
                            type="text",
                            text="错误: 必须指定 all=True 或提供 breaker_name"
                        )]
                    
                    # 记录操作后状态
                    stats_after = breaker_manager.get_all_stats()
                    
                    # 记录到日志文件
                    import datetime
                    log_entry = f"[{datetime.datetime.now()}] {operation}\n"
                    log_file = os.path.join(log_dir, 'circuit_breaker_reset.log')
                    with open(log_file, 'a', encoding='utf-8') as f:
                        f.write(log_entry)
                    
                    # 构建响应
                    response = [f"✅ {operation}已完成\n"]
                    response.append("断路器状态:")
                    for stat in stats_after:
                        state_emoji = {"closed": "🟢", "open": "🔴", "half_open": "🟡"}
                        emoji = state_emoji.get(stat['state'], "⚪")
                        response.append(f"  {emoji} {stat['name']}: {stat['state']}")
                    
                    response.append(f"\n操作已记录到: {log_file}")
                    
                    return [TextContent(type="text", text="\n".join(response))]
                
                else:
                    raise ValueError(f"未知的工具: {name}")
                    
            except Exception as e:
                logger.error(f"Tool execution failed: {e}")
                return [TextContent(
                    type="text",
                    text=f"执行失败: {str(e)}"
                )]
                
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
        # 确保必要的数据库配置已设置
        db_password = os.getenv("DB_PASSWORD")
        if not db_password:
            logger.error("DB_PASSWORD environment variable is required")
            raise ValueError("数据库密码未配置，请设置 DB_PASSWORD 环境变量")
        
        config = {
            "database": {
                "host": os.getenv("DB_HOST", "localhost"),
                "port": int(os.getenv("DB_PORT", "5432")),
                "database": os.getenv("DB_NAME", "sage_memory"),
                "user": os.getenv("DB_USER", "sage"),
                "password": db_password
            },
            "embedding": {
                "model": os.getenv("EMBEDDING_MODEL", "Qwen/Qwen3-Embedding-8B"),
                "device": os.getenv("EMBEDDING_DEVICE", "cpu")
            }
        }
        
        try:
            # 确保获取 sage_core 实例再初始化
            if self.sage_core is None:
                self.sage_core = await get_sage_core({})
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
                        resources=ResourcesCapability(
                            # 支持资源访问
                        )
                    )
                )
            )
            
    async def cleanup(self):
        """清理资源"""
        if self.sage_core is not None and hasattr(self.sage_core, '_initialized') and self.sage_core._initialized:
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