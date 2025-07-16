#!/usr/bin/env python3
"""
Sage MCP 集成测试套件
"""

import asyncio
import json
import subprocess
import sys
import os
import time
import aiohttp
from datetime import datetime
from pathlib import Path

# 添加项目路径
sys.path.insert(0, str(Path(__file__).parent.parent))

# 配置
HTTP_SERVER_URL = "http://localhost:17800"
MCP_ENDPOINT = f"{HTTP_SERVER_URL}/mcp"

class SageMCPTester:
    """Sage MCP 集成测试器"""
    
    def __init__(self):
        self.session = None
        self.test_results = []
        self.test_session_id = f"test-{int(time.time())}"
        
    async def setup(self):
        """设置测试环境"""
        self.session = aiohttp.ClientSession()
        
    async def teardown(self):
        """清理测试环境"""
        if self.session:
            await self.session.close()
            
    async def send_mcp_request(self, method, params=None, request_id="test-1"):
        """发送 MCP 请求"""
        request = {
            "jsonrpc": "2.0",
            "method": method,
            "params": params or {},
            "id": request_id
        }
        
        async with self.session.post(MCP_ENDPOINT, json=request) as response:
            return await response.json()
            
    async def test_health_check(self):
        """测试健康检查端点"""
        print("\n🏥 测试健康检查...")
        try:
            async with self.session.get(f"{HTTP_SERVER_URL}/health") as response:
                if response.status == 200:
                    data = await response.json()
                    self.test_results.append({
                        "test": "health_check",
                        "status": "passed",
                        "details": data
                    })
                    print(f"✅ 健康检查通过: {data['status']}")
                    return True
                else:
                    self.test_results.append({
                        "test": "health_check",
                        "status": "failed",
                        "error": f"HTTP {response.status}"
                    })
                    print(f"❌ 健康检查失败: HTTP {response.status}")
                    return False
        except Exception as e:
            self.test_results.append({
                "test": "health_check",
                "status": "failed",
                "error": str(e)
            })
            print(f"❌ 健康检查异常: {e}")
            return False
            
    async def test_initialize(self):
        """测试 MCP 初始化"""
        print("\n🚀 测试 MCP 初始化...")
        try:
            response = await self.send_mcp_request(
                "initialize",
                {
                    "protocolVersion": "2025-06-18",
                    "capabilities": {},
                    "clientInfo": {
                        "name": "sage-test-client",
                        "version": "1.0.0"
                    }
                }
            )
            
            if "result" in response:
                self.test_results.append({
                    "test": "initialize",
                    "status": "passed",
                    "details": response["result"]
                })
                print(f"✅ 初始化成功: 协议版本 {response['result'].get('protocolVersion')}")
                return True
            else:
                self.test_results.append({
                    "test": "initialize",
                    "status": "failed",
                    "error": response.get("error")
                })
                print(f"❌ 初始化失败: {response.get('error')}")
                return False
        except Exception as e:
            self.test_results.append({
                "test": "initialize",
                "status": "failed",
                "error": str(e)
            })
            print(f"❌ 初始化异常: {e}")
            return False
            
    async def test_list_tools(self):
        """测试工具列表"""
        print("\n🔧 测试工具列表...")
        try:
            response = await self.send_mcp_request("tools/list")
            
            if "result" in response:
                tools = response["result"].get("tools", [])
                self.test_results.append({
                    "test": "list_tools",
                    "status": "passed",
                    "tool_count": len(tools),
                    "tools": [t["name"] for t in tools]
                })
                print(f"✅ 获取工具列表成功: {len(tools)} 个工具")
                for tool in tools:
                    print(f"   - {tool['name']}: {tool['description']}")
                return True
            else:
                self.test_results.append({
                    "test": "list_tools",
                    "status": "failed",
                    "error": response.get("error")
                })
                print(f"❌ 获取工具列表失败: {response.get('error')}")
                return False
        except Exception as e:
            self.test_results.append({
                "test": "list_tools",
                "status": "failed",
                "error": str(e)
            })
            print(f"❌ 获取工具列表异常: {e}")
            return False
            
    async def test_save_conversation(self):
        """测试保存对话"""
        print("\n💾 测试保存对话...")
        try:
            test_data = {
                "user_prompt": f"测试用户输入 - {datetime.now().isoformat()}",
                "assistant_response": f"测试助手响应 - 这是一个集成测试",
                "metadata": {
                    "test_session": self.test_session_id,
                    "test_type": "integration"
                }
            }
            
            response = await self.send_mcp_request(
                "tools/call",
                {
                    "name": "save_conversation",
                    "arguments": test_data
                }
            )
            
            if "result" in response:
                self.test_results.append({
                    "test": "save_conversation",
                    "status": "passed",
                    "details": response["result"]
                })
                print(f"✅ 保存对话成功")
                if "content" in response["result"]:
                    for content in response["result"]["content"]:
                        if content["type"] == "text":
                            print(f"   {content['text']}")
                return True
            else:
                self.test_results.append({
                    "test": "save_conversation",
                    "status": "failed",
                    "error": response.get("error")
                })
                print(f"❌ 保存对话失败: {response.get('error')}")
                return False
        except Exception as e:
            self.test_results.append({
                "test": "save_conversation",
                "status": "failed",
                "error": str(e)
            })
            print(f"❌ 保存对话异常: {e}")
            return False
            
    async def test_get_context(self):
        """测试获取上下文"""
        print("\n🔍 测试获取上下文...")
        try:
            response = await self.send_mcp_request(
                "tools/call",
                {
                    "name": "get_context",
                    "arguments": {
                        "query": "测试",
                        "max_results": 5
                    }
                }
            )
            
            if "result" in response:
                self.test_results.append({
                    "test": "get_context",
                    "status": "passed",
                    "details": response["result"]
                })
                print(f"✅ 获取上下文成功")
                if "content" in response["result"]:
                    for content in response["result"]["content"]:
                        if content["type"] == "text":
                            # 打印前100个字符
                            text = content['text'][:100] + "..." if len(content['text']) > 100 else content['text']
                            print(f"   {text}")
                return True
            else:
                self.test_results.append({
                    "test": "get_context",
                    "status": "failed",
                    "error": response.get("error")
                })
                print(f"❌ 获取上下文失败: {response.get('error')}")
                return False
        except Exception as e:
            self.test_results.append({
                "test": "get_context",
                "status": "failed",
                "error": str(e)
            })
            print(f"❌ 获取上下文异常: {e}")
            return False
            
    async def test_search_memory(self):
        """测试搜索记忆"""
        print("\n🔎 测试搜索记忆...")
        try:
            response = await self.send_mcp_request(
                "tools/call",
                {
                    "name": "search_memory",
                    "arguments": {
                        "query": "测试",
                        "limit": 3
                    }
                }
            )
            
            if "result" in response:
                self.test_results.append({
                    "test": "search_memory",
                    "status": "passed",
                    "details": response["result"]
                })
                print(f"✅ 搜索记忆成功")
                return True
            else:
                self.test_results.append({
                    "test": "search_memory",
                    "status": "failed",
                    "error": response.get("error")
                })
                print(f"❌ 搜索记忆失败: {response.get('error')}")
                return False
        except Exception as e:
            self.test_results.append({
                "test": "search_memory",
                "status": "failed",
                "error": str(e)
            })
            print(f"❌ 搜索记忆异常: {e}")
            return False
            
    async def test_stdio_server(self):
        """测试 stdio 服务器"""
        print("\n📡 测试 stdio 服务器...")
        
        # 检查启动脚本
        script_path = Path(__file__).parent.parent / "start_sage_mcp_stdio_v2.sh"
        if not script_path.exists():
            self.test_results.append({
                "test": "stdio_server",
                "status": "failed",
                "error": "启动脚本不存在"
            })
            print(f"❌ 启动脚本不存在: {script_path}")
            return False
            
        # 测试启动脚本（使用 timeout 限制运行时间）
        try:
            result = subprocess.run(
                ["timeout", "3", str(script_path)],
                capture_output=True,
                text=True
            )
            
            # 检查日志文件
            log_path = "/tmp/sage_mcp_stdio_v2.log"
            if Path(log_path).exists():
                with open(log_path, 'r') as f:
                    log_content = f.read()
                    if "Starting Sage MCP stdio server v2" in log_content:
                        self.test_results.append({
                            "test": "stdio_server",
                            "status": "passed",
                            "details": "服务器可以启动"
                        })
                        print("✅ stdio 服务器测试通过")
                        return True
                        
            self.test_results.append({
                "test": "stdio_server",
                "status": "warning",
                "details": "无法验证服务器启动状态"
            })
            print("⚠️  stdio 服务器启动状态不明")
            return True
            
        except Exception as e:
            self.test_results.append({
                "test": "stdio_server",
                "status": "failed",
                "error": str(e)
            })
            print(f"❌ stdio 服务器测试异常: {e}")
            return False
            
    async def run_all_tests(self):
        """运行所有测试"""
        print("🧪 开始 Sage MCP 集成测试...")
        print("=" * 50)
        
        await self.setup()
        
        try:
            # 运行各项测试
            await self.test_health_check()
            await self.test_initialize()
            await self.test_list_tools()
            await self.test_save_conversation()
            await self.test_get_context()
            await self.test_search_memory()
            await self.test_stdio_server()
            
            # 生成测试报告
            self.generate_report()
            
        finally:
            await self.teardown()
            
    def generate_report(self):
        """生成测试报告"""
        print("\n" + "=" * 50)
        print("📊 测试报告")
        print("=" * 50)
        
        total = len(self.test_results)
        passed = sum(1 for r in self.test_results if r["status"] == "passed")
        failed = sum(1 for r in self.test_results if r["status"] == "failed")
        warnings = sum(1 for r in self.test_results if r["status"] == "warning")
        
        print(f"\n总计: {total} 项测试")
        print(f"✅ 通过: {passed}")
        print(f"❌ 失败: {failed}")
        print(f"⚠️  警告: {warnings}")
        
        if failed > 0:
            print("\n失败的测试:")
            for result in self.test_results:
                if result["status"] == "failed":
                    print(f"  - {result['test']}: {result.get('error', 'Unknown error')}")
                    
        # 保存详细报告
        report_path = Path(__file__).parent / f"test_report_{self.test_session_id}.json"
        with open(report_path, 'w', encoding='utf-8') as f:
            json.dump({
                "timestamp": datetime.now().isoformat(),
                "summary": {
                    "total": total,
                    "passed": passed,
                    "failed": failed,
                    "warnings": warnings
                },
                "results": self.test_results
            }, f, ensure_ascii=False, indent=2)
            
        print(f"\n📄 详细报告已保存至: {report_path}")
        
        # 返回测试是否全部通过
        return failed == 0

async def main():
    """主函数"""
    tester = SageMCPTester()
    await tester.run_all_tests()

if __name__ == "__main__":
    asyncio.run(main())