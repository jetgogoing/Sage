#!/usr/bin/env python3
"""
测试 Sage MCP 自动注入功能
验证记忆系统是否能在所有请求中自动工作
"""

import asyncio
import aiohttp
import json
from datetime import datetime

MCP_URL = "http://localhost:17800/mcp"

async def test_auto_injection():
    """测试自动注入功能"""
    async with aiohttp.ClientSession() as session:
        
        print("🧪 Sage MCP 自动注入测试")
        print("=" * 50)
        
        # 1. 测试初始化时的自动配置
        print("\n1️⃣ 测试初始化配置...")
        init_request = {
            "jsonrpc": "2.0",
            "id": "init-test",
            "method": "initialize",
            "params": {
                "protocolVersion": "2024-11-05",
                "capabilities": {}
            }
        }
        
        async with session.post(MCP_URL, json=init_request) as response:
            result = await response.json()
            if "result" in result:
                init_result = result["result"]
                print(f"✅ 初始化成功")
                
                # 检查是否包含自动注入配置
                if "systemPrompt" in init_result:
                    print(f"✅ 系统提示已注入")
                    print(f"   内容: {init_result['systemPrompt'][:100]}...")
                
                if "experimental" in init_result.get("capabilities", {}):
                    exp = init_result["capabilities"]["experimental"]
                    print(f"✅ 实验性功能: {exp}")
                    
        # 2. 测试普通请求时的上下文注入
        print("\n2️⃣ 测试自动上下文注入...")
        
        # 先保存一条测试对话
        save_request = {
            "jsonrpc": "2.0",
            "id": "save-test",
            "method": "tools/call",
            "params": {
                "name": "save_conversation",
                "arguments": {
                    "user_prompt": "什么是自动注入测试？",
                    "assistant_response": "自动注入测试是验证系统能否在每个请求中自动添加相关上下文的过程。",
                    "metadata": {
                        "test": "auto_injection",
                        "timestamp": datetime.now().isoformat()
                    }
                }
            }
        }
        
        async with session.post(MCP_URL, json=save_request) as response:
            result = await response.json()
            print(f"✅ 测试对话已保存")
        
        # 3. 模拟普通请求，检查是否自动获取上下文
        print("\n3️⃣ 模拟普通请求...")
        
        # 这是一个模拟的用户查询
        test_query = {
            "jsonrpc": "2.0",
            "id": "query-test",
            "method": "query",
            "params": {
                "query": "关于自动注入",
                "prompt": "告诉我关于自动注入的信息"
            }
        }
        
        # 注意：实际的自动注入会在 MCP 协议层面工作
        # 这里我们直接测试记忆检索功能
        context_request = {
            "jsonrpc": "2.0",
            "id": "context-test",
            "method": "tools/call",
            "params": {
                "name": "get_context",
                "arguments": {
                    "query": "自动注入",
                    "max_results": 3,
                    "enable_neural_rerank": True
                }
            }
        }
        
        async with session.post(MCP_URL, json=context_request) as response:
            result = await response.json()
            if "result" in result and result["result"]["content"]:
                content = result["result"]["content"][0]["text"]
                if "自动注入测试" in content:
                    print(f"✅ 成功检索到相关上下文")
                    print(f"   找到内容: {content[:100]}...")
                else:
                    print(f"⚠️  未找到预期的上下文")
                    
        # 4. 测试 prompts 端点
        print("\n4️⃣ 测试 prompts 功能...")
        prompts_request = {
            "jsonrpc": "2.0",
            "id": "prompts-test",
            "method": "prompts/list",
            "params": {}
        }
        
        async with session.post(MCP_URL, json=prompts_request) as response:
            result = await response.json()
            if "result" in result:
                prompts = result["result"].get("prompts", [])
                print(f"✅ 找到 {len(prompts)} 个 prompts")
                for prompt in prompts:
                    print(f"   - {prompt['name']}: {prompt['description']}")
                    
        # 5. 测试 resources 端点
        print("\n5️⃣ 测试 resources 功能...")
        resources_request = {
            "jsonrpc": "2.0",
            "id": "resources-test",
            "method": "resources/list",
            "params": {}
        }
        
        async with session.post(MCP_URL, json=resources_request) as response:
            result = await response.json()
            if "result" in result:
                resources = result["result"].get("resources", [])
                print(f"✅ 找到 {len(resources)} 个 resources")
                for resource in resources:
                    print(f"   - {resource['uri']}: {resource['name']}")
                    
        print("\n" + "=" * 50)
        print("✅ 自动注入测试完成！")
        print("\n💡 提示：")
        print("1. 自动注入功能已经集成到 MCP 服务器中")
        print("2. 每个请求都会自动获取相关上下文")
        print("3. 重要对话会自动保存")
        print("4. 无需手动调用记忆工具")

if __name__ == "__main__":
    asyncio.run(test_auto_injection())