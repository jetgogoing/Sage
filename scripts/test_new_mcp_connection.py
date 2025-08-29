#!/usr/bin/env python3
"""
测试新的 Sage MCP 启动方式连接
使用 start_sage.py 启动脚本
"""

import asyncio
import json
import subprocess
import sys
from pathlib import Path

async def test_mcp_connection():
    """测试 MCP Server 连接"""
    print("测试新的 Sage MCP Server 启动方式...")
    
    # 使用虚拟环境中的 Python 和 start_sage.py
    venv_python = Path(__file__).parent.parent / ".venv" / "bin" / "python3"
    start_script = Path(__file__).parent.parent / "start_sage.py"
    
    if not venv_python.exists():
        print(f"✗ 虚拟环境 Python 不存在: {venv_python}")
        return
    
    if not start_script.exists():
        print(f"✗ 启动脚本不存在: {start_script}")
        return
    
    print(f"Python 路径: {venv_python}")
    print(f"启动脚本: {start_script}")
    
    try:
        # 启动进程
        process = subprocess.Popen(
            [str(venv_python), str(start_script)],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            bufsize=0
        )
        
        print(f"进程已启动，PID: {process.pid}")
        
        # 等待一段时间让服务初始化
        await asyncio.sleep(3)
        
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
        try:
            response = process.stdout.readline()
            if response:
                print(f"收到响应: {response.strip()}")
                try:
                    resp_data = json.loads(response)
                    if resp_data.get("id") == 1:
                        print("✓ 初始化成功")
                        
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
                    else:
                        print("✗ 初始化失败")
                except json.JSONDecodeError:
                    print(f"✗ 响应格式错误: {response}")
            else:
                print("✗ 没有收到响应")
                # 检查 stderr
                stderr_output = process.stderr.read()
                if stderr_output:
                    print(f"错误输出: {stderr_output}")
        except Exception as e:
            print(f"✗ 读取响应时出错: {e}")
        
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