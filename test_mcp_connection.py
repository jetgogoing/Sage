#!/usr/bin/env python3
"""测试 Sage MCP 连接"""

import subprocess
import json
import sys

def test_mcp_connection():
    """测试 MCP 连接是否正常"""
    
    print("=== Sage MCP 连接测试 ===\n")
    
    # 1. 测试健康检查
    print("1. 测试健康检查...")
    try:
        result = subprocess.run(
            ["curl", "-s", "http://localhost:17800/health"],
            capture_output=True,
            text=True
        )
        health = json.loads(result.stdout)
        print(f"   ✅ 服务状态: {health['status']}")
        print(f"   ✅ 记忆数量: {health['memory_count']}")
        print(f"   ✅ 数据库: {health['database']}")
    except Exception as e:
        print(f"   ❌ 健康检查失败: {e}")
        return False
    
    # 2. 测试 stdio 包装器
    print("\n2. 测试 stdio 包装器...")
    test_request = {
        "jsonrpc": "2.0",
        "method": "initialize",
        "params": {
            "protocolVersion": "1.0.0",
            "capabilities": {
                "tools": {"call": True}
            }
        },
        "id": "test-1"
    }
    
    try:
        # 启动 stdio 包装器进程
        process = subprocess.Popen(
            ["python", "/Users/jet/sage/sage_mcp_stdio.py"],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
        
        # 发送请求
        request_str = json.dumps(test_request) + "\n"
        stdout, stderr = process.communicate(input=request_str, timeout=5)
        
        # 解析响应
        response = json.loads(stdout.strip())
        if "result" in response:
            print(f"   ✅ 协议版本: {response['result']['protocolVersion']}")
            print(f"   ✅ 服务器名称: {response['result']['serverInfo']['name']}")
            if 'experimental' in response['result']:
                print(f"   ✅ 自动记忆: {response['result']['experimental'].get('auto_context_injection', False)}")
            else:
                print(f"   ✅ 服务器初始化成功")
        else:
            print(f"   ❌ 响应错误: {response}")
            return False
            
    except Exception as e:
        print(f"   ❌ stdio 测试失败: {e}")
        return False
    
    # 3. 测试记忆功能
    print("\n3. 测试记忆功能...")
    save_request = {
        "jsonrpc": "2.0",
        "method": "tools/call",
        "params": {
            "name": "save_conversation",
            "arguments": {
                "user_prompt": "MCP 连接测试",
                "assistant_response": "连接测试成功，系统工作正常。"
            }
        },
        "id": "test-2"
    }
    
    try:
        process = subprocess.Popen(
            ["python", "/Users/jet/sage/sage_mcp_stdio.py"],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
        
        request_str = json.dumps(save_request) + "\n"
        stdout, stderr = process.communicate(input=request_str, timeout=5)
        
        response = json.loads(stdout.strip())
        if "result" in response and response['result'].get('content'):
            print(f"   ✅ 记忆保存成功")
        else:
            print(f"   ❌ 记忆保存失败: {response}")
            
    except Exception as e:
        print(f"   ❌ 记忆测试失败: {e}")
    
    print("\n=== 测试完成 ===")
    print("\n下一步:")
    print("1. 重启 Claude Code 应用")
    print("2. 在对话中测试记忆功能")
    print("3. 使用 /save 命令保存对话")
    print("4. 使用 /recall 命令查看历史")
    
    return True

if __name__ == "__main__":
    test_mcp_connection()