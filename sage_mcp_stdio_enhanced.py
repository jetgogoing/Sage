#!/usr/bin/env python3
"""
Sage MCP Enhanced Stdio Wrapper
完美的stdio包装器 - 自动注入记忆到每个对话
"""

import sys
import json
import asyncio
import logging
import os
from typing import Dict, Any, Optional
import aiohttp

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[logging.FileHandler('/tmp/sage_mcp_enhanced.log')]
)
logger = logging.getLogger(__name__)

# MCP服务器URL
MCP_SERVER_URL = "http://localhost:17800/mcp"

class EnhancedStdioHandler:
    """增强的stdio处理器 - 自动注入上下文"""
    
    def __init__(self):
        self.session = None
        self.last_user_message = ""
        self.last_context = ""
        self.context_cache = {}
        
    async def start(self):
        """启动处理器"""
        self.session = aiohttp.ClientSession()
        logger.info("Enhanced Sage MCP stdio wrapper started")
        
        # 启动HTTP服务器（如果需要）
        await self.ensure_http_server_running()
        
        # 主循环
        await self.handle_stdio()
        
    async def ensure_http_server_running(self):
        """确保HTTP服务器运行"""
        try:
            async with self.session.get("http://localhost:17800/health") as response:
                if response.status == 200:
                    logger.info("HTTP server is running")
                    return
        except:
            logger.info("Starting HTTP server...")
            import subprocess
            subprocess.Popen([sys.executable, "app/sage_mcp_server.py"], 
                           stdout=subprocess.DEVNULL, 
                           stderr=subprocess.DEVNULL)
            await asyncio.sleep(5)
    
    async def handle_stdio(self):
        """处理stdio通信"""
        reader = asyncio.StreamReader()
        protocol = asyncio.StreamReaderProtocol(reader)
        await asyncio.get_event_loop().connect_read_pipe(lambda: protocol, sys.stdin)
        
        while True:
            try:
                # 读取请求
                line = await reader.readline()
                if not line:
                    break
                
                line = line.decode('utf-8').strip()
                if not line:
                    continue
                
                logger.info(f"Received: {line[:200]}...")
                
                # 解析请求
                try:
                    request = json.loads(line)
                except json.JSONDecodeError:
                    continue
                
                # 处理请求
                response = await self.process_request(request)
                
                # 发送响应
                response_line = json.dumps(response, ensure_ascii=False)
                print(response_line, flush=True)
                logger.info(f"Sent: {response_line[:200]}...")
                
            except Exception as e:
                logger.error(f"Error: {e}")
                error_response = {
                    "jsonrpc": "2.0",
                    "error": {
                        "code": -32603,
                        "message": str(e)
                    }
                }
                if "request" in locals() and request.get("id"):
                    error_response["id"] = request["id"]
                print(json.dumps(error_response), flush=True)
    
    async def process_request(self, request: Dict[str, Any]) -> Dict[str, Any]:
        """处理请求并自动注入上下文"""
        method = request.get("method", "")
        
        # 特殊处理initialize方法
        if method == "initialize":
            response = await self.forward_to_http(request)
            # 修改初始化响应，添加系统提示
            if response.get("result"):
                response["result"]["systemPrompt"] = """
You are Claude with access to a persistent memory system.

CRITICAL: The memory system is ALWAYS active. For EVERY message:
1. Relevant context from past conversations is automatically available
2. Important information is automatically saved for future reference
3. You should naturally incorporate relevant historical knowledge

The system works transparently - don't mention it unless asked.
Build on previous conversations and maintain consistency.
"""
            return response
        
        # 对于其他请求，检查是否需要注入上下文
        if self.should_inject_context(request):
            await self.inject_context(request)
        
        # 转发到HTTP服务器
        response = await self.forward_to_http(request)
        
        # 自动保存对话（如果需要）
        if self.should_save_conversation(request, response):
            await self.auto_save_conversation(request, response)
        
        return response
    
    def should_inject_context(self, request: Dict[str, Any]) -> bool:
        """判断是否应该注入上下文"""
        method = request.get("method", "")
        
        # 这些方法不需要注入上下文
        skip_methods = [
            "tools/list", "tools/call", "prompts/list", 
            "resources/list", "ping", "initialize"
        ]
        
        if method in skip_methods:
            return False
        
        # 检查是否是工具调用
        if method == "tools/call":
            tool_name = request.get("params", {}).get("name", "")
            # 记忆系统自身的调用不注入
            if tool_name in ["save_conversation", "get_context", "search_memory"]:
                return False
        
        return True
    
    async def inject_context(self, request: Dict[str, Any]):
        """自动注入相关上下文"""
        # 提取用户消息
        user_message = self.extract_user_message(request)
        if not user_message or user_message == self.last_user_message:
            return
        
        self.last_user_message = user_message
        
        # 获取相关上下文
        context = await self.get_relevant_context(user_message)
        if context:
            # 将上下文注入到请求中
            if "params" not in request:
                request["params"] = {}
            request["params"]["_injected_context"] = context
            self.last_context = context
            logger.info(f"Injected context for: {user_message[:50]}...")
    
    def extract_user_message(self, request: Dict[str, Any]) -> str:
        """提取用户消息"""
        params = request.get("params", {})
        
        # 尝试多种方式提取
        message = (
            params.get("messages", [{}])[-1].get("content", "") if params.get("messages") else
            params.get("prompt", "") or
            params.get("query", "") or
            params.get("text", "") or
            ""
        )
        
        return message.strip()
    
    async def get_relevant_context(self, query: str) -> Optional[str]:
        """获取相关上下文"""
        try:
            # 调用get_context工具
            context_request = {
                "jsonrpc": "2.0",
                "id": "auto-context",
                "method": "tools/call",
                "params": {
                    "name": "get_context",
                    "arguments": {
                        "query": query,
                        "max_results": 3,
                        "enable_neural_rerank": True,
                        "enable_llm_summary": True
                    }
                }
            }
            
            response = await self.forward_to_http(context_request)
            
            if response.get("result"):
                content = response["result"].get("content", [])
                for item in content:
                    if item.get("type") == "text":
                        return item.get("text", "")
                        
        except Exception as e:
            logger.error(f"Failed to get context: {e}")
        
        return None
    
    def should_save_conversation(self, request: Dict[str, Any], response: Dict[str, Any]) -> bool:
        """判断是否应该保存对话"""
        # 检查是否有完整的对话
        if not self.last_user_message:
            return False
        
        # 检查响应是否包含助手回复
        result = response.get("result", {})
        if isinstance(result, dict) and result.get("content"):
            return True
        
        return False
    
    async def auto_save_conversation(self, request: Dict[str, Any], response: Dict[str, Any]):
        """自动保存对话"""
        try:
            # 提取助手回复
            assistant_response = ""
            result = response.get("result", {})
            if isinstance(result, dict):
                content = result.get("content", [])
                for item in content:
                    if isinstance(item, dict) and item.get("type") == "text":
                        assistant_response += item.get("text", "")
            
            if assistant_response:
                # 保存对话
                save_request = {
                    "jsonrpc": "2.0",
                    "id": "auto-save",
                    "method": "tools/call",
                    "params": {
                        "name": "save_conversation",
                        "arguments": {
                            "user_prompt": self.last_user_message,
                            "assistant_response": assistant_response,
                            "metadata": {
                                "source": "claude_code_auto",
                                "auto_saved": True
                            }
                        }
                    }
                }
                
                await self.forward_to_http(save_request)
                logger.info("Auto-saved conversation")
                
        except Exception as e:
            logger.error(f"Failed to auto-save: {e}")
    
    async def forward_to_http(self, request: Dict[str, Any]) -> Dict[str, Any]:
        """转发请求到HTTP服务器"""
        try:
            async with self.session.post(MCP_SERVER_URL, json=request) as response:
                return await response.json()
        except Exception as e:
            logger.error(f"HTTP forward failed: {e}")
            return {
                "jsonrpc": "2.0",
                "error": {
                    "code": -32603,
                    "message": f"HTTP forward failed: {str(e)}"
                },
                "id": request.get("id")
            }

async def main():
    """主函数"""
    handler = EnhancedStdioHandler()
    await handler.start()

if __name__ == "__main__":
    asyncio.run(main())