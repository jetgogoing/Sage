#!/usr/bin/env python3
"""
测试 MCP 协议交互
模拟 Claude Code 发送的 MCP 协议消息
"""

import subprocess
import json
import time
import sys

def send_request(proc, request):
    """发送 JSON-RPC 请求到 stdio 服务器"""
    request_str = json.dumps(request)
    print(f"→ 发送: {request_str}")
    proc.stdin.write(request_str + '\n')
    proc.stdin.flush()
    
    # 读取响应
    response_line = proc.stdout.readline()
    if response_line:
        response = json.loads(response_line)
        print(f"← 响应: {json.dumps(response, ensure_ascii=False, indent=2)}")
        return response
    return None

def test_mcp_protocol():
    """测试 MCP 协议完整流程"""
    print("🧪 启动 MCP 协议测试...\n")
    
    # 启动 stdio 服务器
    proc = subprocess.Popen(
        ['python', 'sage_mcp_stdio_v2.py'],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        bufsize=1
    )
    
    # 等待服务器启动
    time.sleep(1)
    
    try:
        # 1. 初始化请求
        print("1️⃣ 测试初始化...")
        init_request = {
            "jsonrpc": "2.0",
            "method": "initialize",
            "params": {
                "protocolVersion": "2025-03-26",
                "capabilities": {},
                "clientInfo": {
                    "name": "test-client",
                    "version": "1.0.0"
                }
            },
            "id": 1
        }
        init_response = send_request(proc, init_request)
        
        # 2. 初始化完成通知
        print("\n2️⃣ 发送初始化完成通知...")
        initialized_notif = {
            "jsonrpc": "2.0",
            "method": "notifications/initialized"
        }
        send_request(proc, initialized_notif)
        
        # 3. 列出工具
        print("\n3️⃣ 测试列出工具...")
        list_tools_request = {
            "jsonrpc": "2.0",
            "method": "tools/list",
            "params": {},
            "id": 2
        }
        tools_response = send_request(proc, list_tools_request)
        
        # 4. 调用工具 - 保存对话
        print("\n4️⃣ 测试保存对话...")
        save_request = {
            "jsonrpc": "2.0",
            "method": "tools/call",
            "params": {
                "name": "save_conversation",
                "arguments": {
                    "user_prompt": "测试用户输入",
                    "assistant_response": "测试助手回复"
                }
            },
            "id": 3
        }
        save_response = send_request(proc, save_request)
        
        # 5. 调用工具 - 获取上下文
        print("\n5️⃣ 测试获取上下文...")
        context_request = {
            "jsonrpc": "2.0",
            "method": "tools/call",
            "params": {
                "name": "get_context",
                "arguments": {
                    "query": "测试"
                }
            },
            "id": 4
        }
        context_response = send_request(proc, context_request)
        
        # 6. 列出提示模板
        print("\n6️⃣ 测试列出提示模板...")
        list_prompts_request = {
            "jsonrpc": "2.0",
            "method": "prompts/list",
            "params": {},
            "id": 5
        }
        prompts_response = send_request(proc, list_prompts_request)
        
        # 7. 获取提示模板
        print("\n7️⃣ 测试获取提示模板...")
        get_prompt_request = {
            "jsonrpc": "2.0",
            "method": "prompts/get",
            "params": {
                "name": "auto_context_injection",
                "arguments": {
                    "user_input": "如何配置 MCP 服务器？"
                }
            },
            "id": 6
        }
        prompt_response = send_request(proc, get_prompt_request)
        
        print("\n✅ 所有测试完成！")
        
    except Exception as e:
        print(f"\n❌ 测试失败: {e}")
        # 读取 stderr
        stderr_output = proc.stderr.read()
        if stderr_output:
            print(f"stderr: {stderr_output}")
    finally:
        # 关闭进程
        proc.terminate()
        proc.wait()

if __name__ == "__main__":
    test_mcp_protocol()