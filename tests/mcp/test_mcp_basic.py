#!/usr/bin/env python3
"""
测试 MCP SDK 基本功能
"""

import asyncio
import sys
import json
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent))

from mcp.server import Server
from mcp.server.models import InitializationOptions
from mcp.types import Tool, TextContent

# 创建一个简单的测试服务器
server = Server("test-server")

@server.list_tools()
async def handle_list_tools():
    """列出工具"""
    return [
        Tool(
            name="test_tool",
            description="测试工具",
            inputSchema={
                "type": "object",
                "properties": {
                    "message": {
                        "type": "string",
                        "description": "测试消息"
                    }
                },
                "required": ["message"]
            }
        )
    ]

@server.call_tool()
async def handle_call_tool(name: str, arguments: dict):
    """调用工具"""
    if name == "test_tool":
        message = arguments.get("message", "")
        return [TextContent(text=f"工具响应: {message}")]
    raise ValueError(f"Unknown tool: {name}")

async def test_server():
    """测试服务器功能"""
    print("测试 MCP 服务器基本功能...")
    
    # 测试工具列表
    tools = await handle_list_tools()
    print(f"工具列表: {[tool.name for tool in tools]}")
    
    # 测试工具调用
    result = await handle_call_tool("test_tool", {"message": "Hello MCP!"})
    print(f"工具调用结果: {result[0].text}")
    
    print("✅ 基本功能测试通过")

if __name__ == "__main__":
    asyncio.run(test_server())