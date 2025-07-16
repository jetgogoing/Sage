#!/usr/bin/env python3
"""
交互式测试 MCP 协议
"""

import json
import sys

def send_request(request):
    """发送请求到 stdout"""
    print(json.dumps(request), flush=True)

def main():
    # 1. 初始化请求
    init_request = {
        "jsonrpc": "2.0",
        "method": "initialize",
        "params": {
            "protocolVersion": "2025-06-18",
            "capabilities": {},
            "clientInfo": {
                "name": "test-client",
                "version": "1.0.0"
            }
        },
        "id": 1
    }
    send_request(init_request)
    
    # 2. 等待响应
    response = sys.stdin.readline()
    print(f"← 初始化响应: {response}", file=sys.stderr)
    
    # 3. 发送初始化完成通知
    initialized_notif = {
        "jsonrpc": "2.0",
        "method": "notifications/initialized"
    }
    send_request(initialized_notif)
    
    # 4. 列出工具
    list_tools_request = {
        "jsonrpc": "2.0",
        "method": "tools/list",
        "params": {},
        "id": 2
    }
    send_request(list_tools_request)
    
    # 等待响应
    response = sys.stdin.readline()
    print(f"← 工具列表响应: {response}", file=sys.stderr)

if __name__ == "__main__":
    main()