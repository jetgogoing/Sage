#!/usr/bin/env python3
"""
测试 MCP 连接流程，模拟 Claude Code 的行为
"""
import requests
import json

BASE_URL = "http://localhost:17800"

def test_mcp_connection():
    print("🔍 测试 MCP 连接流程")
    print("=" * 50)
    
    # 1. 测试基本连接
    print("\n1️⃣ 测试基本连接...")
    try:
        resp = requests.get(f"{BASE_URL}/")
        print(f"✅ 根路径响应: {resp.status_code}")
        print(f"   内容: {resp.json()}")
    except Exception as e:
        print(f"❌ 错误: {e}")
    
    # 2. 测试健康检查
    print("\n2️⃣ 测试健康检查...")
    try:
        resp = requests.get(f"{BASE_URL}/health")
        print(f"✅ 健康检查: {resp.status_code}")
        print(f"   内容: {resp.json()}")
    except Exception as e:
        print(f"❌ 错误: {e}")
    
    # 3. 测试 .well-known 配置
    print("\n3️⃣ 测试 .well-known 配置...")
    try:
        resp = requests.get(f"{BASE_URL}/mcp/.well-known/mcp-configuration")
        print(f"✅ Well-known 配置: {resp.status_code}")
        print(f"   内容: {json.dumps(resp.json(), indent=2)}")
    except Exception as e:
        print(f"❌ 错误: {e}")
    
    # 4. 测试客户端注册
    print("\n4️⃣ 测试客户端注册...")
    try:
        data = {
            "client_name": "claude-code-test",
            "grant_types": ["client_credentials"],
            "response_types": ["token"]
        }
        resp = requests.post(f"{BASE_URL}/mcp/register", json=data)
        print(f"✅ 客户端注册: {resp.status_code}")
        print(f"   内容: {resp.json()}")
    except Exception as e:
        print(f"❌ 错误: {e}")
    
    # 5. 测试 MCP 初始化
    print("\n5️⃣ 测试 MCP 初始化...")
    try:
        data = {
            "jsonrpc": "2.0",
            "id": "init-1",
            "method": "initialize",
            "params": {
                "protocolVersion": "2024-11-05",
                "capabilities": {
                    "roots": {"listChanged": True},
                    "sampling": {}
                },
                "clientInfo": {
                    "name": "claude-code",
                    "version": "1.0.0"
                }
            }
        }
        resp = requests.post(f"{BASE_URL}/mcp", json=data)
        print(f"✅ MCP 初始化: {resp.status_code}")
        result = resp.json()
        if "result" in result:
            print(f"   协议版本: {result['result']['protocolVersion']}")
            print(f"   服务器名称: {result['result']['serverInfo']['name']}")
            print(f"   支持的功能: {list(result['result']['capabilities'].keys())}")
    except Exception as e:
        print(f"❌ 错误: {e}")
    
    # 6. 测试可能的其他路径
    print("\n6️⃣ 测试其他可能的路径...")
    paths = [
        "/mcp/clients",
        "/mcp/clients/claude-code",
        "/mcp/auth",
        "/mcp/token",
        "/.well-known/mcp-configuration"  # 根路径下的 well-known
    ]
    
    for path in paths:
        try:
            resp = requests.get(f"{BASE_URL}{path}")
            print(f"   {path}: {resp.status_code}")
            if resp.status_code == 404:
                print(f"   ⚠️  找到 404 错误！")
        except Exception as e:
            print(f"   {path}: 错误 - {e}")

if __name__ == "__main__":
    test_mcp_connection()