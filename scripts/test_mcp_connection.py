#!/usr/bin/env python3
"""
测试 Sage MCP Server 连接
用于调试 stdio 模式的 MCP 服务器连接问题
"""

import asyncio
import json
import subprocess
import sys
from pathlib import Path

async def test_mcp_connection():
    """测试 MCP Server 连接"""
    print("开始测试 Sage MCP Server 连接...")
    
    # 启动 MCP 服务器进程
    start_script = Path(__file__).parent.parent / "start_sage_mcp.sh"
    
    try:
        # 启动进程
        process = subprocess.Popen(
            [str(start_script)],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            bufsize=0
        )
        
        print(f"进程已启动，PID: {process.pid}")
        
        # 发送初始化请求
        init_request = {
            "id": 1,
            "method": "initialize",
            "params": {
                "protocolVersion": "2024-11-05",
                "capabilities": {},
                "clientInfo": {
                    "name": "test-client",
                    "version": "1.0.0"
                }
            }
        }
        
        print("发送初始化请求...")
        process.stdin.write(json.dumps(init_request) + "\n")
        process.stdin.flush()
        
        # 读取响应
        response = process.stdout.readline()
        if response:
            print(f"收到响应: {response.strip()}")
            try:
                resp_data = json.loads(response)
                if resp_data.get("id") == 1:
                    print("✓ 初始化成功")
                else:
                    print("✗ 初始化失败")
            except json.JSONDecodeError:
                print(f"✗ 响应格式错误: {response}")
        else:
            print("✗ 没有收到响应")
        
        # 测试工具列表
        tools_request = {
            "id": 2,
            "method": "tools/list",
            "params": {}
        }
        
        print("发送工具列表请求...")
        process.stdin.write(json.dumps(tools_request) + "\n")
        process.stdin.flush()
        
        response = process.stdout.readline()
        if response:
            print(f"工具列表响应: {response.strip()}")
            try:
                resp_data = json.loads(response)
                tools = resp_data.get("result", {}).get("tools", [])
                print(f"✓ 找到 {len(tools)} 个工具")
                for tool in tools[:3]:  # 只显示前3个
                    print(f"  - {tool.get('name', 'unknown')}")
            except json.JSONDecodeError:
                print(f"✗ 工具列表响应格式错误")
        else:
            print("✗ 没有收到工具列表响应")
        
    except Exception as e:
        print(f"✗ 连接测试失败: {e}")
    finally:
        if 'process' in locals():
            process.terminate()
            try:
                process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                process.kill()
            print("进程已清理")

if __name__ == "__main__":
    asyncio.run(test_mcp_connection())