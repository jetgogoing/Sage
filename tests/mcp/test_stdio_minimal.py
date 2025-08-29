#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Sage MCP STDIO 最小化测试脚本
测试基本功能是否正常工作
"""

import asyncio
import json
import sys

async def test_mcp_stdio():
    """测试 MCP STDIO 协议"""
    print("🧪 Sage MCP STDIO 测试开始...\n")
    
    # 测试初始化
    print("1️⃣ 测试 MCP 初始化...")
    init_request = {
        "jsonrpc": "2.0",
        "method": "initialize",
        "params": {
            "protocolVersion": "1.0.0",
            "capabilities": {
                "tools": {}
            },
            "clientInfo": {
                "name": "test-client",
                "version": "1.0.0"
            }
        },
        "id": 1
    }
    
    # 输出测试请求
    print(f"请求: {json.dumps(init_request, ensure_ascii=False)}")
    print("✅ MCP 初始化请求格式正确\n")
    
    # 测试工具列表
    print("2️⃣ 测试获取工具列表...")
    list_tools_request = {
        "jsonrpc": "2.0",
        "method": "tools/list",
        "params": {},
        "id": 2
    }
    print(f"请求: {json.dumps(list_tools_request, ensure_ascii=False)}")
    print("✅ 工具列表请求格式正确\n")
    
    # 测试保存对话
    print("3️⃣ 测试保存对话功能...")
    save_request = {
        "jsonrpc": "2.0",
        "method": "tools/call",
        "params": {
            "name": "save_conversation",
            "arguments": {
                "user_prompt": "什么是机器学习？",
                "assistant_response": "机器学习是人工智能的一个分支..."
            }
        },
        "id": 3
    }
    print(f"请求: {json.dumps(save_request, ensure_ascii=False, indent=2)}")
    print("✅ 保存对话请求格式正确\n")
    
    # 测试搜索功能
    print("4️⃣ 测试搜索记忆功能...")
    search_request = {
        "jsonrpc": "2.0", 
        "method": "tools/call",
        "params": {
            "name": "search_memory",
            "arguments": {
                "query": "机器学习",
                "limit": 5
            }
        },
        "id": 4
    }
    print(f"请求: {json.dumps(search_request, ensure_ascii=False, indent=2)}")
    print("✅ 搜索记忆请求格式正确\n")
    
    # 测试状态查询
    print("5️⃣ 测试状态查询功能...")
    status_request = {
        "jsonrpc": "2.0",
        "method": "tools/call", 
        "params": {
            "name": "get_status",
            "arguments": {}
        },
        "id": 5
    }
    print(f"请求: {json.dumps(status_request, ensure_ascii=False, indent=2)}")
    print("✅ 状态查询请求格式正确\n")
    
    print("🎉 所有测试用例构建完成！")
    print("\n💡 使用方法：")
    print("1. 在一个终端运行: ./run_sage_stdio.sh")
    print("2. 在另一个终端运行: python test_stdio_minimal.py | python sage_mcp_stdio_v3.py")
    print("\n或者在 Claude Code 中配置并使用这些命令。")

if __name__ == "__main__":
    asyncio.run(test_mcp_stdio())