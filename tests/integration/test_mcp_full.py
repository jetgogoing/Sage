#!/usr/bin/env python3
"""
测试完整的MCP调用流程
"""
import subprocess
import json
import time
import sys

def test_mcp_full_workflow():
    """测试完整的MCP工作流程"""
    try:
        print("🔍 启动MCP服务器进行完整测试...")
        
        # 启动MCP服务器进程
        process = subprocess.Popen(
            ['python3', 'sage_mcp_stdio_single.py'],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            bufsize=0
        )
        
        # 等待服务器启动
        time.sleep(2)
        
        print("✅ MCP服务器已启动")
        
        # 1. 初始化请求
        init_request = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "initialize",
            "params": {
                "protocolVersion": "2024-11-05",
                "capabilities": {"tools": {}},
                "clientInfo": {"name": "test-client", "version": "1.0.0"}
            }
        }
        
        print("🔧 发送初始化请求...")
        process.stdin.write(json.dumps(init_request) + '\n')
        process.stdin.flush()
        
        # 读取响应
        response_line = process.stdout.readline().strip()
        if response_line:
            print(f"📦 初始化响应: {response_line}")
        
        # 2. 发送initialized通知
        initialized_notification = {
            "jsonrpc": "2.0",
            "method": "notifications/initialized"
        }
        
        print("📢 发送initialized通知...")
        process.stdin.write(json.dumps(initialized_notification) + '\n')
        process.stdin.flush()
        
        # 3. 列出工具
        list_tools_request = {
            "jsonrpc": "2.0",
            "id": 2,
            "method": "tools/list",
            "params": {}
        }
        
        print("🛠️ 请求工具列表...")
        process.stdin.write(json.dumps(list_tools_request) + '\n')
        process.stdin.flush()
        
        response_line = process.stdout.readline().strip()
        if response_line:
            print(f"📋 工具列表响应: {response_line}")
        
        # 4. 测试generate_prompt工具
        generate_prompt_request = {
            "jsonrpc": "2.0",
            "id": 3,
            "method": "tools/call",
            "params": {
                "name": "generate_prompt",
                "arguments": {
                    "context": "我需要优化Python代码性能，特别是数据库查询方面",
                    "style": "suggestion"
                }
            }
        }
        
        print("🧠 测试generate_prompt工具...")
        process.stdin.write(json.dumps(generate_prompt_request) + '\n')
        process.stdin.flush()
        
        response_line = process.stdout.readline().strip()
        if response_line:
            print(f"💡 generate_prompt响应: {response_line}")
        
        # 5. 测试记忆功能
        get_context_request = {
            "jsonrpc": "2.0",
            "id": 4,
            "method": "tools/call",
            "params": {
                "name": "get_context",
                "arguments": {
                    "query": "Python性能优化",
                    "max_results": 5
                }
            }
        }
        
        print("🧠 测试get_context工具...")
        process.stdin.write(json.dumps(get_context_request) + '\n')
        process.stdin.flush()
        
        response_line = process.stdout.readline().strip()
        if response_line:
            print(f"📚 get_context响应: {response_line}")
        
        print("✅ MCP完整工作流程测试完成")
        
        # 关闭进程
        process.terminate()
        time.sleep(1)
        if process.poll() is None:
            process.kill()
            
        return True
        
    except Exception as e:
        print(f"❌ MCP测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = test_mcp_full_workflow()
    sys.exit(0 if success else 1)