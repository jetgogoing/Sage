#!/usr/bin/env python3
"""
验证 MCP 完整修复是否正常工作
"""
import requests
import json

BASE_URL = "http://localhost:17800"

def test_complete_fix():
    print("🔍 测试 Sage MCP 完整修复")
    print("=" * 50)
    
    results = []
    
    # 1. 测试新添加的 token 端点
    print("\n1️⃣ 测试 /mcp/token 端点...")
    try:
        resp = requests.post(f"{BASE_URL}/mcp/token", json={})
        if resp.status_code == 200:
            data = resp.json()
            if "access_token" in data:
                print(f"✅ Token 端点正常: {resp.status_code}")
                print(f"   Access Token: {data['access_token'][:20]}...")
                results.append(("token", True))
            else:
                print(f"❌ Token 响应格式错误")
                results.append(("token", False))
        else:
            print(f"❌ Token 端点错误: {resp.status_code}")
            results.append(("token", False))
    except Exception as e:
        print(f"❌ 错误: {e}")
        results.append(("token", False))
    
    # 2. 测试新添加的 auth 端点
    print("\n2️⃣ 测试 /mcp/auth 端点...")
    try:
        resp = requests.post(f"{BASE_URL}/mcp/auth", json={})
        if resp.status_code == 200:
            data = resp.json()
            if data.get("status") == "ok":
                print(f"✅ Auth 端点正常: {resp.status_code}")
                print(f"   认证状态: {data}")
                results.append(("auth", True))
            else:
                print(f"❌ Auth 响应格式错误")
                results.append(("auth", False))
        else:
            print(f"❌ Auth 端点错误: {resp.status_code}")
            results.append(("auth", False))
    except Exception as e:
        print(f"❌ 错误: {e}")
        results.append(("auth", False))
    
    # 3. 测试 .well-known 配置
    print("\n3️⃣ 测试 .well-known 配置...")
    try:
        resp = requests.get(f"{BASE_URL}/mcp/.well-known/mcp-configuration")
        if resp.status_code == 200:
            data = resp.json()
            tools_endpoint = data.get("tools_endpoint", "")
            if tools_endpoint.endswith("/mcp"):
                print(f"✅ Tools endpoint 配置正确: {tools_endpoint}")
                results.append(("tools_endpoint", True))
            else:
                print(f"❌ Tools endpoint 配置错误: {tools_endpoint}")
                results.append(("tools_endpoint", False))
        else:
            print(f"❌ Well-known 端点错误: {resp.status_code}")
            results.append(("tools_endpoint", False))
    except Exception as e:
        print(f"❌ 错误: {e}")
        results.append(("tools_endpoint", False))
    
    # 4. 模拟完整的注册流程
    print("\n4️⃣ 模拟 Claude Code 注册流程...")
    flow_success = True
    
    # 4.1 获取 .well-known 配置
    try:
        resp = requests.get(f"{BASE_URL}/mcp/.well-known/mcp-configuration")
        config = resp.json()
        print("   ✅ 获取配置成功")
    except:
        print("   ❌ 获取配置失败")
        flow_success = False
    
    # 4.2 注册客户端
    if flow_success:
        try:
            resp = requests.post(f"{BASE_URL}/mcp/register", json={
                "client_name": "claude-code-test"
            })
            print("   ✅ 客户端注册成功")
        except:
            print("   ❌ 客户端注册失败")
            flow_success = False
    
    # 4.3 获取 token
    if flow_success:
        try:
            resp = requests.post(f"{BASE_URL}/mcp/token", json={})
            token_data = resp.json()
            token = token_data.get("access_token")
            print(f"   ✅ 获取 Token 成功")
        except:
            print("   ❌ 获取 Token 失败")
            flow_success = False
    
    # 4.4 验证认证
    if flow_success:
        try:
            resp = requests.post(f"{BASE_URL}/mcp/auth", json={
                "token": token
            })
            auth_data = resp.json()
            if auth_data.get("status") == "ok":
                print("   ✅ 认证验证成功")
            else:
                print("   ❌ 认证验证失败")
                flow_success = False
        except:
            print("   ❌ 认证请求失败")
            flow_success = False
    
    # 4.5 初始化 MCP
    if flow_success:
        try:
            resp = requests.post(f"{BASE_URL}/mcp", json={
                "jsonrpc": "2.0",
                "id": "init",
                "method": "initialize",
                "params": {
                    "protocolVersion": "2024-11-05"
                }
            })
            if resp.status_code == 200:
                print("   ✅ MCP 初始化成功")
            else:
                print("   ❌ MCP 初始化失败")
                flow_success = False
        except:
            print("   ❌ MCP 初始化请求失败")
            flow_success = False
    
    results.append(("registration_flow", flow_success))
    
    # 总结
    print("\n" + "=" * 50)
    print("📊 测试结果总结：")
    
    all_passed = all(result[1] for result in results)
    
    for name, passed in results:
        status = "✅" if passed else "❌"
        print(f"   {status} {name}")
    
    if all_passed:
        print("\n🎉 所有测试通过！Sage MCP 应该可以正常注册了。")
        print("\n下一步：")
        print("1. 重启 MCP 服务器")
        print("2. 运行: claude mcp remove sage")
        print("3. 运行: claude mcp add sage http://localhost:17800/mcp")
    else:
        print("\n⚠️  仍有测试失败，请检查服务器日志。")

if __name__ == "__main__":
    test_complete_fix()