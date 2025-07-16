#!/usr/bin/env python3
"""
Sage MCP stdio server v2 - 符合 MCP 协议规范的实现
This implements a proper MCP server that acts as a proxy to the HTTP backend
"""

import asyncio
import json
import logging
import os
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional
import aiohttp

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
    PromptsCapability
)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[logging.FileHandler('/tmp/sage_mcp_stdio_v2.log')]
)
logger = logging.getLogger(__name__)

# HTTP backend configuration
HTTP_SERVER_URL = os.getenv("SAGE_HTTP_URL", "http://localhost:17800")
MCP_ENDPOINT = f"{HTTP_SERVER_URL}/mcp"


class SageMCPStdioServer:
    """MCP stdio server that proxies to HTTP backend"""
    
    def __init__(self):
        self.server = Server("sage")
        self.http_session = None
        self._connector = None
        self._register_handlers()
        logger.info(f"Sage MCP stdio server v2 initialized, backend: {HTTP_SERVER_URL}")
        
    async def _get_http_session(self) -> aiohttp.ClientSession:
        """获取或创建 HTTP 会话（带连接池）"""
        if not self.http_session or self.http_session.closed:
            # 创建连接器以复用连接
            self._connector = aiohttp.TCPConnector(
                limit=100,  # 最大连接数
                ttl_dns_cache=300,  # DNS 缓存时间
                keepalive_timeout=30,  # 保持连接超时
                enable_cleanup_closed=True
            )
            self.http_session = aiohttp.ClientSession(
                connector=self._connector,
                timeout=aiohttp.ClientTimeout(total=30)
            )
            logger.info("Created new HTTP session with connection pooling")
        return self.http_session
        
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
                            },
                            "strategy": {
                                "type": "string",
                                "description": "检索策略",
                                "enum": ["default", "recent", "semantic"],
                                "default": "default"
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
                            "session_id": {
                                "type": "string",
                                "description": "可选的会话ID过滤"
                            }
                        },
                        "required": ["query"]
                    }
                )
            ]
            
        @self.server.call_tool()
        async def handle_call_tool(name: str, arguments: Dict[str, Any]) -> List[TextContent]:
            """调用工具 - 转发到 HTTP 服务器"""
            logger.info(f"Handling call_tool request: {name}")
            
            try:
                session = await self._get_http_session()
                
                # 构造 MCP 请求 - 使用正确的方法名 tools/call
                mcp_request = {
                    "jsonrpc": "2.0",
                    "method": "tools/call",
                    "params": {
                        "name": name,
                        "arguments": arguments
                    },
                    "id": "1"
                }
                
                logger.debug(f"Sending request to HTTP backend: {mcp_request}")
                
                # 转发到 HTTP 服务器
                async with session.post(MCP_ENDPOINT, json=mcp_request) as response:
                    if response.status != 200:
                        error_text = await response.text()
                        logger.error(f"HTTP backend error: {response.status} - {error_text}")
                        raise Exception(f"Backend error: {response.status}")
                        
                    result = await response.json()
                    logger.debug(f"Received response from HTTP backend: {result}")
                
                # 处理错误响应
                if "error" in result:
                    error_msg = result["error"].get("message", "Unknown error")
                    logger.error(f"Tool execution error: {error_msg}")
                    raise Exception(error_msg)
                
                # 提取结果
                tool_result = result.get("result", {})
                output_text = ""
                
                # 处理不同的响应格式
                if isinstance(tool_result, dict):
                    output_text = tool_result.get("output", str(tool_result))
                elif isinstance(tool_result, str):
                    output_text = tool_result
                else:
                    output_text = json.dumps(tool_result, ensure_ascii=False)
                
                logger.info(f"Tool {name} executed successfully")
                return [TextContent(type="text", text=output_text)]
                
            except aiohttp.ClientError as e:
                logger.error(f"HTTP client error: {e}")
                raise Exception(f"Failed to connect to backend: {str(e)}")
            except Exception as e:
                logger.error(f"Tool execution failed: {e}")
                raise
                
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
                )
            ]
            
        @self.server.get_prompt()
        async def handle_get_prompt(name: str, arguments: Dict[str, Any]) -> GetPromptResult:
            """获取提示模板内容"""
            logger.info(f"Handling get_prompt request: {name}")
            
            if name == "auto_context_injection":
                user_input = arguments.get("user_input", "")
                
                # 调用 get_context 工具获取相关上下文
                try:
                    context_result = await handle_call_tool("get_context", {"query": user_input})
                    context_text = context_result[0].text if context_result else ""
                    
                    messages = []
                    if context_text:
                        messages.append(
                            PromptMessage(
                                role="system",
                                content=TextContent(
                                    type="text",
                                    text=f"基于以下相关历史记忆：\n\n{context_text}\n\n请回答用户的问题。"
                                )
                            )
                        )
                    
                    messages.append(
                        PromptMessage(
                            role="user",
                            content=TextContent(type="text", text=user_input)
                        )
                    )
                    
                    return GetPromptResult(
                        description="已注入相关历史上下文",
                        messages=messages
                    )
                except Exception as e:
                    logger.error(f"Failed to get context: {e}")
                    # 如果获取上下文失败，返回原始输入
                    return GetPromptResult(
                        description="获取上下文失败，使用原始输入",
                        messages=[
                            PromptMessage(
                                role="user",
                                content=TextContent(type="text", text=user_input)
                            )
                        ]
                    )
            
            raise ValueError(f"Unknown prompt: {name}")
    
    async def run(self):
        """运行 MCP 服务器"""
        logger.info("Starting Sage MCP stdio server v2...")
        
        # 确保 HTTP 后端可用
        await self._check_backend_health()
        
        # 运行 stdio 服务器
        async with stdio_server() as (read_stream, write_stream):
            await self.server.run(
                read_stream,
                write_stream,
                InitializationOptions(
                    server_name="sage",
                    server_version="2.0.0",
                    capabilities=ServerCapabilities(
                        tools=ToolsCapability(
                            # 支持的工具功能
                        ),
                        prompts=PromptsCapability(
                            # 支持提示模板
                        )
                    )
                )
            )
            
    async def _check_backend_health(self):
        """检查 HTTP 后端健康状态"""
        try:
            session = await self._get_http_session()
            async with session.get(f"{HTTP_SERVER_URL}/health") as response:
                if response.status == 200:
                    health_data = await response.json()
                    logger.info(f"Backend health check passed: {health_data}")
                else:
                    logger.warning(f"Backend health check returned {response.status}")
        except Exception as e:
            logger.warning(f"Backend health check failed: {e}")
            logger.warning("Continuing anyway - backend may become available")
            
    async def cleanup(self):
        """清理资源"""
        if self.http_session:
            await self.http_session.close()
            logger.info("Closed HTTP session")
        if self._connector:
            await self._connector.close()


async def main():
    """主函数"""
    server = SageMCPStdioServer()
    try:
        await server.run()
    except KeyboardInterrupt:
        logger.info("Server stopped by user")
    except Exception as e:
        logger.error(f"Server error: {e}")
        raise
    finally:
        await server.cleanup()


if __name__ == "__main__":
    # 确保在正确的目录运行
    if not os.path.exists("sage_mcp_stdio.py"):
        logger.warning("Not running from Sage directory, some features may not work")
    
    # 运行服务器
    asyncio.run(main())