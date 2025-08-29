#!/usr/bin/env python3
"""
MCP协议测试工具
测试MCP over HTTP协议实现、工具发现、JSON Schema验证等
"""

import asyncio
import json
import logging
import sys
import time
from pathlib import Path
from typing import Dict, List, Any, Tuple
import aiohttp
from datetime import datetime
import uuid

# 添加项目路径
sys.path.insert(0, str(Path(__file__).parent.parent))

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class MCPProtocolTest:
    """MCP协议测试类"""
    
    def __init__(self, base_url: str = "http://localhost:17800"):
        self.base_url = base_url
        self.session = None
        
    async def __aenter__(self):
        self.session = aiohttp.ClientSession()
        return self
        
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.session:
            await self.session.close()
    
    async def test_server_health(self) -> Dict[str, Any]:
        """测试服务器健康状态"""
        logger.info("测试服务器健康状态...")
        
        test_result = {
            'status': 'success',
            'server_available': False,
            'response_time': 0,
            'health_details': {},
            'error': None
        }
        
        try:
            start_time = time.time()
            
            async with self.session.get(f"{self.base_url}/health") as response:
                end_time = time.time()
                test_result['response_time'] = end_time - start_time
                
                if response.status == 200:
                    test_result['server_available'] = True
                    test_result['health_details'] = await response.json()
                else:
                    test_result['status'] = 'error'
                    test_result['error'] = f'Health check failed: {response.status}'
            
            logger.info(f"服务器健康检查完成: {test_result['status']}")
            return test_result
            
        except Exception as e:
            test_result['status'] = 'error'
            test_result['error'] = str(e)
            logger.error(f"服务器健康检查失败: {e}")
            return test_result
    
    async def test_mcp_info(self) -> Dict[str, Any]:
        """测试MCP服务器信息端点"""
        logger.info("测试MCP服务器信息...")
        
        test_result = {
            'status': 'success',
            'info_available': False,
            'server_info': {},
            'capabilities_valid': False,
            'error': None
        }
        
        try:
            async with self.session.get(f"{self.base_url}/mcp/info") as response:
                if response.status == 200:
                    info = await response.json()
                    test_result['info_available'] = True
                    test_result['server_info'] = info
                    
                    # 验证必要字段
                    required_fields = ['name', 'version', 'protocolVersion', 'capabilities']
                    test_result['capabilities_valid'] = all(field in info for field in required_fields)
                    
                    if not test_result['capabilities_valid']:
                        test_result['status'] = 'warning'
                        test_result['error'] = 'Missing required server info fields'
                else:
                    test_result['status'] = 'error'
                    test_result['error'] = f'MCP info request failed: {response.status}'
            
            logger.info(f"MCP服务器信息测试完成: {test_result['status']}")
            return test_result
            
        except Exception as e:
            test_result['status'] = 'error'
            test_result['error'] = str(e)
            logger.error(f"MCP服务器信息测试失败: {e}")
            return test_result
    
    async def test_mcp_initialize(self) -> Dict[str, Any]:
        """测试MCP初始化协议"""
        logger.info("测试MCP初始化协议...")
        
        test_result = {
            'status': 'success',
            'initialize_successful': False,
            'protocol_version': None,
            'capabilities': {},
            'server_info': {},
            'error': None
        }
        
        try:
            mcp_request = {
                "jsonrpc": "2.0",
                "id": str(uuid.uuid4()),
                "method": "initialize",
                "params": {
                    "protocolVersion": "2024-11-05",
                    "capabilities": {
                        "tools": {},
                        "resources": {}
                    },
                    "clientInfo": {
                        "name": "mcp-test-client",
                        "version": "1.0.0"
                    }
                }
            }
            
            async with self.session.post(
                f"{self.base_url}/mcp",
                json=mcp_request,
                headers={"Content-Type": "application/json"}
            ) as response:
                if response.status == 200:
                    result = await response.json()
                    
                    if 'result' in result:
                        test_result['initialize_successful'] = True
                        result_data = result['result']
                        test_result['protocol_version'] = result_data.get('protocolVersion')
                        test_result['capabilities'] = result_data.get('capabilities', {})
                        test_result['server_info'] = result_data.get('serverInfo', {})
                    else:
                        test_result['status'] = 'error'
                        test_result['error'] = f'Invalid MCP response: {result}'
                else:
                    test_result['status'] = 'error'
                    test_result['error'] = f'MCP initialize failed: {response.status}'
            
            logger.info(f"MCP初始化测试完成: {test_result['status']}")
            return test_result
            
        except Exception as e:
            test_result['status'] = 'error'
            test_result['error'] = str(e)
            logger.error(f"MCP初始化测试失败: {e}")
            return test_result
    
    async def test_tools_discovery(self) -> Dict[str, Any]:
        """测试工具发现"""
        logger.info("测试工具发现...")
        
        test_result = {
            'status': 'success',
            'tools_discovered': False,
            'tools_count': 0,
            'tool_names': [],
            'schema_validation': {},
            'error': None
        }
        
        try:
            mcp_request = {
                "jsonrpc": "2.0",
                "id": str(uuid.uuid4()),
                "method": "tools/list",
                "params": {}
            }
            
            async with self.session.post(
                f"{self.base_url}/mcp",
                json=mcp_request,
                headers={"Content-Type": "application/json"}
            ) as response:
                if response.status == 200:
                    result = await response.json()
                    
                    if 'result' in result and 'tools' in result['result']:
                        tools = result['result']['tools']
                        test_result['tools_discovered'] = True
                        test_result['tools_count'] = len(tools)
                        test_result['tool_names'] = [tool.get('name') for tool in tools]
                        
                        # 验证每个工具的schema
                        for tool in tools:
                            tool_name = tool.get('name', 'unknown')
                            schema_valid = self._validate_tool_schema(tool)
                            test_result['schema_validation'][tool_name] = schema_valid
                    else:
                        test_result['status'] = 'error'
                        test_result['error'] = f'Invalid tools response: {result}'
                else:
                    test_result['status'] = 'error'
                    test_result['error'] = f'Tools discovery failed: {response.status}'
            
            logger.info(f"工具发现测试完成: {test_result['tools_count']} 个工具")
            return test_result
            
        except Exception as e:
            test_result['status'] = 'error'
            test_result['error'] = str(e)
            logger.error(f"工具发现测试失败: {e}")
            return test_result
    
    def _validate_tool_schema(self, tool: Dict[str, Any]) -> bool:
        """验证工具schema格式"""
        required_fields = ['name', 'description', 'inputSchema']
        if not all(field in tool for field in required_fields):
            return False
        
        input_schema = tool.get('inputSchema', {})
        if not isinstance(input_schema, dict):
            return False
        
        # 检查是否有type和properties
        return 'type' in input_schema and input_schema['type'] == 'object'
    
    async def test_tool_execution(self) -> Dict[str, Any]:
        """测试工具执行"""
        logger.info("测试工具执行...")
        
        test_result = {
            'status': 'success',
            'save_conversation_test': {},
            'get_context_test': {},
            'search_memory_test': {},
            'get_stats_test': {},
            'error': None
        }
        
        try:
            # 测试save_conversation
            save_result = await self._test_save_conversation()
            test_result['save_conversation_test'] = save_result
            
            # 测试get_context
            context_result = await self._test_get_context()
            test_result['get_context_test'] = context_result
            
            # 测试search_memory
            search_result = await self._test_search_memory()
            test_result['search_memory_test'] = search_result
            
            # 测试get_memory_stats
            stats_result = await self._test_get_memory_stats()
            test_result['get_stats_test'] = stats_result
            
            # 检查是否有任何测试失败
            all_tests = [save_result, context_result, search_result, stats_result]
            if any(test.get('status') == 'error' for test in all_tests):
                test_result['status'] = 'warning'
                test_result['error'] = 'Some tool tests failed'
            
            logger.info(f"工具执行测试完成: {test_result['status']}")
            return test_result
            
        except Exception as e:
            test_result['status'] = 'error'
            test_result['error'] = str(e)
            logger.error(f"工具执行测试失败: {e}")
            return test_result
    
    async def _test_save_conversation(self) -> Dict[str, Any]:
        """测试保存对话功能"""
        test_result = {'status': 'success', 'response_time': 0, 'session_id': None}
        
        try:
            start_time = time.time()
            
            mcp_request = {
                "jsonrpc": "2.0",
                "id": str(uuid.uuid4()),
                "method": "tools/call",
                "params": {
                    "name": "save_conversation",
                    "arguments": {
                        "user_prompt": "测试用户输入：什么是MCP协议？",
                        "assistant_response": "测试助手回复：MCP（Model Context Protocol）是一种标准化的协议...",
                        "metadata": {
                            "source": "mcp_test",
                            "timestamp": datetime.now().isoformat(),
                            "model": "test-model"
                        }
                    }
                }
            }
            
            async with self.session.post(
                f"{self.base_url}/mcp",
                json=mcp_request,
                headers={"Content-Type": "application/json"}
            ) as response:
                end_time = time.time()
                test_result['response_time'] = end_time - start_time
                
                if response.status == 200:
                    result = await response.json()
                    if 'result' in result:
                        # 从响应中提取会话ID
                        content = result['result'].get('content', [])
                        if content and len(content) > 0:
                            text_content = content[0].get('text', '')
                            # 简单解析会话ID
                            if 'Session:' in text_content:
                                session_part = text_content.split('Session:')[1].split(',')[0].strip()
                                test_result['session_id'] = session_part
                    else:
                        test_result['status'] = 'error'
                        test_result['error'] = f'Save conversation failed: {result}'
                else:
                    test_result['status'] = 'error'
                    test_result['error'] = f'Save conversation failed: {response.status}'
            
        except Exception as e:
            test_result['status'] = 'error'
            test_result['error'] = str(e)
        
        return test_result
    
    async def _test_get_context(self) -> Dict[str, Any]:
        """测试获取上下文功能"""
        test_result = {'status': 'success', 'response_time': 0, 'context_length': 0}
        
        try:
            start_time = time.time()
            
            mcp_request = {
                "jsonrpc": "2.0",
                "id": str(uuid.uuid4()),
                "method": "tools/call",
                "params": {
                    "name": "get_context",
                    "arguments": {
                        "query": "MCP协议",
                        "max_results": 5,
                        "enable_llm_summary": True,
                        "enable_neural_rerank": True
                    }
                }
            }
            
            async with self.session.post(
                f"{self.base_url}/mcp",
                json=mcp_request,
                headers={"Content-Type": "application/json"}
            ) as response:
                end_time = time.time()
                test_result['response_time'] = end_time - start_time
                
                if response.status == 200:
                    result = await response.json()
                    if 'result' in result:
                        content = result['result'].get('content', [])
                        if content and len(content) > 0:
                            context_text = content[0].get('text', '')
                            test_result['context_length'] = len(context_text)
                    else:
                        test_result['status'] = 'error'
                        test_result['error'] = f'Get context failed: {result}'
                else:
                    test_result['status'] = 'error'
                    test_result['error'] = f'Get context failed: {response.status}'
            
        except Exception as e:
            test_result['status'] = 'error'
            test_result['error'] = str(e)
        
        return test_result
    
    async def _test_search_memory(self) -> Dict[str, Any]:
        """测试内存搜索功能"""
        test_result = {'status': 'success', 'response_time': 0, 'results_count': 0}
        
        try:
            start_time = time.time()
            
            mcp_request = {
                "jsonrpc": "2.0",
                "id": str(uuid.uuid4()),
                "method": "tools/call",
                "params": {
                    "name": "search_memory",
                    "arguments": {
                        "query": "协议",
                        "n": 3,
                        "similarity_threshold": 0.6
                    }
                }
            }
            
            async with self.session.post(
                f"{self.base_url}/mcp",
                json=mcp_request,
                headers={"Content-Type": "application/json"}
            ) as response:
                end_time = time.time()
                test_result['response_time'] = end_time - start_time
                
                if response.status == 200:
                    result = await response.json()
                    if 'result' in result:
                        content = result['result'].get('content', [])
                        if content and len(content) > 0:
                            text_content = content[0].get('text', '')
                            # 简单解析结果数量
                            if 'Found' in text_content:
                                try:
                                    count_str = text_content.split('Found')[1].split('memories')[0].strip()
                                    test_result['results_count'] = int(count_str)
                                except:
                                    pass
                    else:
                        test_result['status'] = 'error'
                        test_result['error'] = f'Search memory failed: {result}'
                else:
                    test_result['status'] = 'error'
                    test_result['error'] = f'Search memory failed: {response.status}'
            
        except Exception as e:
            test_result['status'] = 'error'
            test_result['error'] = str(e)
        
        return test_result
    
    async def _test_get_memory_stats(self) -> Dict[str, Any]:
        """测试获取内存统计功能"""
        test_result = {'status': 'success', 'response_time': 0, 'stats_available': False}
        
        try:
            start_time = time.time()
            
            mcp_request = {
                "jsonrpc": "2.0",
                "id": str(uuid.uuid4()),
                "method": "tools/call",
                "params": {
                    "name": "get_memory_stats",
                    "arguments": {
                        "include_performance": True
                    }
                }
            }
            
            async with self.session.post(
                f"{self.base_url}/mcp",
                json=mcp_request,
                headers={"Content-Type": "application/json"}
            ) as response:
                end_time = time.time()
                test_result['response_time'] = end_time - start_time
                
                if response.status == 200:
                    result = await response.json()
                    if 'result' in result:
                        content = result['result'].get('content', [])
                        if content and len(content) > 0:
                            text_content = content[0].get('text', '')
                            test_result['stats_available'] = 'Total conversations' in text_content
                    else:
                        test_result['status'] = 'error'
                        test_result['error'] = f'Get memory stats failed: {result}'
                else:
                    test_result['status'] = 'error'
                    test_result['error'] = f'Get memory stats failed: {response.status}'
            
        except Exception as e:
            test_result['status'] = 'error'
            test_result['error'] = str(e)
        
        return test_result
    
    async def test_error_handling(self) -> Dict[str, Any]:
        """测试错误处理"""
        logger.info("测试错误处理...")
        
        test_result = {
            'status': 'success',
            'invalid_method_test': {},
            'invalid_params_test': {},
            'malformed_request_test': {},
            'error': None
        }
        
        try:
            # 测试无效方法
            invalid_method_result = await self._test_invalid_method()
            test_result['invalid_method_test'] = invalid_method_result
            
            # 测试无效参数
            invalid_params_result = await self._test_invalid_params()
            test_result['invalid_params_test'] = invalid_params_result
            
            # 测试格式错误的请求
            malformed_result = await self._test_malformed_request()
            test_result['malformed_request_test'] = malformed_result
            
            logger.info(f"错误处理测试完成")
            return test_result
            
        except Exception as e:
            test_result['status'] = 'error'
            test_result['error'] = str(e)
            logger.error(f"错误处理测试失败: {e}")
            return test_result
    
    async def _test_invalid_method(self) -> Dict[str, Any]:
        """测试无效方法错误处理"""
        test_result = {'status': 'success', 'error_code': None, 'error_message': ''}
        
        try:
            mcp_request = {
                "jsonrpc": "2.0",
                "id": str(uuid.uuid4()),
                "method": "invalid_method",
                "params": {}
            }
            
            async with self.session.post(
                f"{self.base_url}/mcp",
                json=mcp_request,
                headers={"Content-Type": "application/json"}
            ) as response:
                if response.status == 200:
                    result = await response.json()
                    if 'error' in result:
                        test_result['error_code'] = result['error'].get('code')
                        test_result['error_message'] = result['error'].get('message', '')
                    else:
                        test_result['status'] = 'error'
                        test_result['error'] = 'Expected error response but got success'
                else:
                    test_result['status'] = 'error'
                    test_result['error'] = f'Unexpected HTTP status: {response.status}'
            
        except Exception as e:
            test_result['status'] = 'error'
            test_result['error'] = str(e)
        
        return test_result
    
    async def _test_invalid_params(self) -> Dict[str, Any]:
        """测试无效参数错误处理"""
        test_result = {'status': 'success', 'validation_error': False}
        
        try:
            mcp_request = {
                "jsonrpc": "2.0",
                "id": str(uuid.uuid4()),
                "method": "tools/call",
                "params": {
                    "name": "save_conversation",
                    "arguments": {
                        "user_prompt": "",  # 无效：空字符串
                        "assistant_response": None  # 无效：空值
                    }
                }
            }
            
            async with self.session.post(
                f"{self.base_url}/mcp",
                json=mcp_request,
                headers={"Content-Type": "application/json"}
            ) as response:
                if response.status == 200:
                    result = await response.json()
                    if 'result' in result and 'isError' in result['result']:
                        test_result['validation_error'] = result['result']['isError']
                    elif 'error' in result:
                        test_result['validation_error'] = True
                else:
                    test_result['status'] = 'warning'
                    test_result['error'] = f'Expected validation error handling: {response.status}'
            
        except Exception as e:
            test_result['status'] = 'error'
            test_result['error'] = str(e)
        
        return test_result
    
    async def _test_malformed_request(self) -> Dict[str, Any]:
        """测试格式错误的请求"""
        test_result = {'status': 'success', 'error_handled': False}
        
        try:
            # 发送无效JSON
            async with self.session.post(
                f"{self.base_url}/mcp",
                data="invalid json",
                headers={"Content-Type": "application/json"}
            ) as response:
                # 应该返回400或500错误
                if response.status in [400, 422, 500]:
                    test_result['error_handled'] = True
                else:
                    test_result['status'] = 'warning'
                    test_result['error'] = f'Malformed request not handled: {response.status}'
            
        except Exception as e:
            test_result['status'] = 'error'
            test_result['error'] = str(e)
        
        return test_result
    
    async def run_comprehensive_test(self) -> Dict[str, Any]:
        """运行综合MCP协议测试"""
        logger.info("开始综合MCP协议测试...")
        
        comprehensive_result = {
            'test_timestamp': datetime.now().isoformat(),
            'overall_status': 'success',
            'test_results': {},
            'summary': {},
            'recommendations': []
        }
        
        # 运行所有测试
        tests = [
            ('server_health', self.test_server_health),
            ('mcp_info', self.test_mcp_info),
            ('mcp_initialize', self.test_mcp_initialize),
            ('tools_discovery', self.test_tools_discovery),
            ('tool_execution', self.test_tool_execution),
            ('error_handling', self.test_error_handling)
        ]
        
        for test_name, test_func in tests:
            try:
                logger.info(f"执行测试: {test_name}")
                result = await test_func()
                comprehensive_result['test_results'][test_name] = result
                
                if result['status'] == 'error':
                    comprehensive_result['overall_status'] = 'error'
                elif result['status'] == 'warning' and comprehensive_result['overall_status'] != 'error':
                    comprehensive_result['overall_status'] = 'warning'
                    
            except Exception as e:
                logger.error(f"测试 {test_name} 执行失败: {e}")
                comprehensive_result['test_results'][test_name] = {
                    'status': 'error',
                    'error': str(e)
                }
                comprehensive_result['overall_status'] = 'error'
        
        # 生成总结和建议
        comprehensive_result['summary'] = self._generate_test_summary(comprehensive_result['test_results'])
        comprehensive_result['recommendations'] = self._generate_recommendations(comprehensive_result['test_results'])
        
        logger.info(f"综合MCP协议测试完成，总体状态: {comprehensive_result['overall_status']}")
        return comprehensive_result
    
    def _generate_test_summary(self, test_results: Dict[str, Any]) -> Dict[str, Any]:
        """生成测试总结"""
        summary = {
            'tests_passed': 0,
            'tests_warning': 0,
            'tests_failed': 0,
            'mcp_compliance': 'unknown',
            'key_features': {}
        }
        
        for test_name, result in test_results.items():
            if result['status'] == 'success':
                summary['tests_passed'] += 1
            elif result['status'] == 'warning':
                summary['tests_warning'] += 1
            else:
                summary['tests_failed'] += 1
        
        # 评估MCP兼容性
        if summary['tests_failed'] == 0:
            if summary['tests_warning'] == 0:
                summary['mcp_compliance'] = 'fully_compliant'
            else:
                summary['mcp_compliance'] = 'mostly_compliant'
        else:
            summary['mcp_compliance'] = 'partial_compliance'
        
        # 提取关键特性状态
        if 'tools_discovery' in test_results:
            td_result = test_results['tools_discovery']
            summary['key_features']['tools_discovered'] = td_result.get('tools_discovered', False)
            summary['key_features']['tools_count'] = td_result.get('tools_count', 0)
        
        if 'tool_execution' in test_results:
            te_result = test_results['tool_execution']
            summary['key_features']['tool_execution_working'] = te_result.get('status') == 'success'
        
        return summary
    
    def _generate_recommendations(self, test_results: Dict[str, Any]) -> List[str]:
        """生成改进建议"""
        recommendations = []
        
        # 服务器健康检查建议
        if 'server_health' in test_results:
            health_result = test_results['server_health']
            if health_result['status'] == 'error':
                recommendations.append("服务器无法访问，检查服务器是否正在运行并且端口配置正确")
            elif health_result.get('response_time', 0) > 1.0:
                recommendations.append("服务器响应时间较慢，考虑优化服务器性能或网络连接")
        
        # 工具发现建议
        if 'tools_discovery' in test_results:
            td_result = test_results['tools_discovery']
            if not td_result.get('tools_discovered', False):
                recommendations.append("工具发现失败，检查MCP协议实现和工具注册")
            elif td_result.get('tools_count', 0) < 4:
                recommendations.append("发现的工具数量少于预期，检查是否所有工具都已正确注册")
        
        # 工具执行建议
        if 'tool_execution' in test_results:
            te_result = test_results['tool_execution']
            if te_result.get('status') != 'success':
                recommendations.append("工具执行测试失败，检查工具实现和数据库连接")
        
        # 错误处理建议
        if 'error_handling' in test_results:
            eh_result = test_results['error_handling']
            if eh_result.get('status') != 'success':
                recommendations.append("错误处理机制需要改进，确保正确返回JSON-RPC错误代码")
        
        if not recommendations:
            recommendations.append("所有MCP协议测试通过，系统已准备好与Claude Code集成")
        
        return recommendations

# CLI接口
async def main():
    """命令行接口"""
    import argparse
    
    parser = argparse.ArgumentParser(description='MCP协议测试')
    parser.add_argument('--url', default='http://localhost:17800', help='MCP服务器URL')
    parser.add_argument('--output', '-o', help='输出结果到文件')
    parser.add_argument('--verbose', '-v', action='store_true', help='详细输出')
    
    args = parser.parse_args()
    
    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)
    
    async with MCPProtocolTest(args.url) as tester:
        result = await tester.run_comprehensive_test()
    
    # 输出结果
    if args.output:
        with open(args.output, 'w', encoding='utf-8') as f:
            json.dump(result, f, indent=2, ensure_ascii=False)
        print(f"测试结果已保存到: {args.output}")
    else:
        print(json.dumps(result, indent=2, ensure_ascii=False))
    
    # 返回适当的退出码
    if result['overall_status'] == 'error':
        sys.exit(1)
    elif result['overall_status'] == 'warning':
        sys.exit(2)
    else:
        sys.exit(0)

if __name__ == '__main__':
    asyncio.run(main())