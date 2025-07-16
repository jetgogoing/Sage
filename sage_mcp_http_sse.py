#\!/usr/bin/env python3
# -*- coding: utf-8 -*-
#!/usr/bin/env python3
"""
Sage MCP HTTP/SSE Server - 支持 MCP Connector 的 HTTP 实现
支持 Server-Sent Events (SSE) 和标准 HTTP
"""

import asyncio
import json
import logging
import os
import sys
import uuid
from pathlib import Path
from typing import Any, Dict, List, Optional, AsyncIterator
from datetime import datetime

from fastapi import FastAPI, Request, Response, HTTPException, Header
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse, JSONResponse
from pydantic import BaseModel
import uvicorn

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent))

# Import sage_core
from sage_core import SageCore, MemoryContent, SearchOptions
from sage_core.auth import OAuth2Provider

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


# Pydantic models for MCP protocol
class MCPRequest(BaseModel):
    jsonrpc: str = "2.0"
    id: Optional[str] = None
    method: str
    params: Optional[Dict[str, Any]] = None


class MCPError(BaseModel):
    code: int
    message: str
    data: Optional[Any] = None


class MCPResponse(BaseModel):
    jsonrpc: str = "2.0"
    id: Optional[str] = None
    result: Optional[Any] = None
    error: Optional[MCPError] = None


# FastAPI app
app = FastAPI(title="Sage MCP HTTP/SSE Server", version="1.0.0")

# CORS configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 生产环境应该限制
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Global instances
sage_core: Optional[SageCore] = None
oauth_provider: Optional[OAuth2Provider] = None


async def get_sage_core() -> SageCore:
    """获取或初始化 sage_core 实例"""
    global sage_core
    
    if sage_core is None:
        sage_core = SageCore()
        
        config = {
            "database": {
                "host": os.getenv("DB_HOST", "localhost"),
                "port": int(os.getenv("DB_PORT", "5432")),
                "database": os.getenv("DB_NAME", "sage_memory"),
                "user": os.getenv("DB_USER", "sage"),
                "password": os.getenv("DB_PASSWORD", "sage123")
            },
            "embedding": {
                "model": os.getenv("EMBEDDING_MODEL", "Qwen/Qwen3-Embedding-8B"),
                "device": os.getenv("EMBEDDING_DEVICE", "cpu")
            }
        }
        
        await sage_core.initialize(config)
        logger.info("Sage core initialized for HTTP/SSE server")
    
    return sage_core


def create_tool_definitions() -> List[Dict[str, Any]]:
    """创建工具定义"""
    return [
        {
            "name": "save_conversation",
            "description": "保存用户和助手的对话到记忆系统",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "user_prompt": {
                        "type": "string",
                        "description": "用户的输入内容"
                    },
                    "assistant_response": {
                        "type": "string",
                        "description": "助手的回复内容"
                    },
                    "metadata": {
                        "type": "object",
                        "description": "可选的元数据",
                        "properties": {}
                    }
                },
                "required": ["user_prompt", "assistant_response"]
            }
        },
        {
            "name": "get_context",
            "description": "根据查询获取相关的历史上下文",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "查询内容"
                    },
                    "max_results": {
                        "type": "integer",
                        "description": "最大返回结果数",
                        "default": 10
                    }
                },
                "required": ["query"]
            }
        },
        {
            "name": "search_memory",
            "description": "搜索记忆库中的历史对话",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "搜索查询"
                    },
                    "limit": {
                        "type": "integer",
                        "description": "返回结果数量限制",
                        "default": 10
                    },
                    "strategy": {
                        "type": "string",
                        "description": "搜索策略",
                        "enum": ["default", "semantic", "recent"],
                        "default": "default"
                    },
                    "session_id": {
                        "type": "string",
                        "description": "可选的会话ID过滤"
                    }
                },
                "required": ["query"]
            }
        }
    ]


async def handle_mcp_request(request: MCPRequest) -> MCPResponse:
    """处理 MCP 请求"""
    core = await get_sage_core()
    
    try:
        if request.method == "initialize":
            # 初始化请求
            result = {
                "protocolVersion": "1.0",
                "serverInfo": {
                    "name": "sage",
                    "version": "1.0.0"
                },
                "capabilities": {
                    "tools": {
                        "listTools": {}
                    }
                }
            }
            
        elif request.method == "tools/list":
            # 列出工具
            result = {
                "tools": create_tool_definitions()
            }
            
        elif request.method == "tools/call":
            # 调用工具
            if not request.params or "name" not in request.params:
                raise ValueError("Missing tool name")
            
            tool_name = request.params["name"]
            arguments = request.params.get("arguments", {})
            
            if tool_name == "save_conversation":
                content = MemoryContent(
                    user_input=arguments["user_prompt"],
                    assistant_response=arguments["assistant_response"],
                    metadata=arguments.get("metadata", {})
                )
                memory_id = await core.save_memory(content)
                result = {
                    "content": [
                        {
                            "type": "text",
                            "text": f"对话已保存，记忆ID: {memory_id}"
                        }
                    ]
                }
                
            elif tool_name == "get_context":
                context = await core.get_context(
                    query=arguments["query"],
                    max_results=arguments.get("max_results", 10)
                )
                result = {
                    "content": [
                        {
                            "type": "text",
                            "text": context
                        }
                    ]
                }
                
            elif tool_name == "search_memory":
                options = SearchOptions(
                    limit=arguments.get("limit", 10),
                    strategy=arguments.get("strategy", "default"),
                    session_id=arguments.get("session_id")
                )
                results = await core.search_memory(
                    query=arguments["query"],
                    options=options
                )
                
                # 格式化结果
                if results:
                    output_lines = [f"找到 {len(results)} 条相关记忆：\n"]
                    for i, memory in enumerate(results, 1):
                        output_lines.append(f"\n[记忆 {i}]")
                        output_lines.append(f"时间: {memory['created_at']}")
                        if 'similarity' in memory:
                            output_lines.append(f"相关度: {memory['similarity']:.2f}")
                        output_lines.append(f"用户: {memory['user_input'][:100]}...")
                        output_lines.append(f"助手: {memory['assistant_response'][:100]}...")
                    output = "\n".join(output_lines)
                else:
                    output = "没有找到相关记忆"
                
                result = {
                    "content": [
                        {
                            "type": "text",
                            "text": output
                        }
                    ]
                }
                
            else:
                raise ValueError(f"Unknown tool: {tool_name}")
                
        else:
            raise ValueError(f"Unknown method: {request.method}")
        
        return MCPResponse(
            jsonrpc="2.0",
            id=request.id,
            result=result
        )
        
    except Exception as e:
        logger.error(f"Error handling MCP request: {e}")
        return MCPResponse(
            jsonrpc="2.0",
            id=request.id,
            error=MCPError(
                code=-32603,
                message=str(e)
            )
        )


async def sse_generator(request_data: Dict[str, Any]) -> AsyncIterator[str]:
    """SSE 事件生成器"""
    try:
        # 创建 MCP 请求
        mcp_request = MCPRequest(**request_data)
        
        # 处理请求
        response = await handle_mcp_request(mcp_request)
        
        # 发送响应作为 SSE 事件
        event_data = response.model_dump(exclude_none=True)
        yield f"data: {json.dumps(event_data)}\n\n"
        
        # 发送完成事件
        yield f"data: [DONE]\n\n"
        
    except Exception as e:
        logger.error(f"SSE error: {e}")
        error_response = MCPResponse(
            jsonrpc="2.0",
            id=request_data.get("id"),
            error=MCPError(
                code=-32603,
                message=str(e)
            )
        )
        yield f"data: {json.dumps(error_response.model_dump())}\n\n"


@app.post("/mcp")
async def mcp_endpoint(
    request: Request,
    anthropic_beta: Optional[str] = Header(None, alias="anthropic-beta"),
    authorization: Optional[str] = Header(None)
):
    """MCP HTTP 端点"""
    # 检查 beta header
    if anthropic_beta != "mcp-client-2025-04-04":
        logger.warning(f"Missing or incorrect anthropic-beta header: {anthropic_beta}")
    
    # 检查认证（如果启用）
    if os.getenv("REQUIRE_AUTH", "false").lower() == "true":
        if not authorization or not authorization.startswith("Bearer "):
            return JSONResponse(
                status_code=401,
                content={
                    "jsonrpc": "2.0",
                    "error": {
                        "code": -32001,
                        "message": "Unauthorized"
                    }
                }
            )
        
        token = authorization.split(" ")[1]
        token_payload = oauth_provider.verify_token(token)
        
        if not token_payload:
            return JSONResponse(
                status_code=401,
                content={
                    "jsonrpc": "2.0",
                    "error": {
                        "code": -32001,
                        "message": "Invalid token"
                    }
                }
            )
    
    # 解析请求
    try:
        request_data = await request.json()
    except Exception as e:
        return JSONResponse(
            status_code=400,
            content={
                "jsonrpc": "2.0",
                "error": {
                    "code": -32700,
                    "message": "Parse error"
                }
            }
        )
    
    # 检查是否是 SSE 请求
    accept_header = request.headers.get("accept", "")
    if "text/event-stream" in accept_header:
        # SSE 响应
        return StreamingResponse(
            sse_generator(request_data),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
                "X-Accel-Buffering": "no"
            }
        )
    else:
        # 标准 JSON 响应
        mcp_request = MCPRequest(**request_data)
        response = await handle_mcp_request(mcp_request)
        return response.model_dump(exclude_none=True)


@app.get("/health")
async def health_check():
    """健康检查端点"""
    try:
        core = await get_sage_core()
        status = await core.get_status()
        
        return {
            "status": "healthy",
            "timestamp": datetime.utcnow().isoformat(),
            "sage_core": status.get("initialized", False)
        }
    except Exception as e:
        return JSONResponse(
            status_code=503,
            content={
                "status": "unhealthy",
                "error": str(e)
            }
        )


@app.get("/")
async def root():
    """根端点"""
    return {
        "service": "Sage MCP HTTP/SSE Server",
        "version": "1.0.0",
        "endpoints": {
            "/mcp": "MCP protocol endpoint (POST)",
            "/health": "Health check endpoint (GET)",
            "/oauth/authorize": "OAuth authorization endpoint (GET)",
            "/oauth/token": "OAuth token endpoint (POST)"
        }
    }


# OAuth endpoints
@app.get("/oauth/authorize")
async def oauth_authorize(
    response_type: str,
    client_id: str,
    redirect_uri: str,
    scope: str = "read write",
    state: Optional[str] = None
):
    """OAuth 授权端点"""
    if response_type != "code":
        raise HTTPException(status_code=400, detail="Unsupported response type")
    
    if client_id != oauth_provider.client_id:
        raise HTTPException(status_code=400, detail="Invalid client ID")
    
    # 简化的用户认证（生产环境应该有真实的用户登录）
    user_id = "default_user"
    
    # 生成授权码
    code = oauth_provider.generate_authorization_code(
        user_id=user_id,
        redirect_uri=redirect_uri,
        scope=scope
    )
    
    # 构建重定向URL
    redirect_url = f"{redirect_uri}?code={code}"
    if state:
        redirect_url += f"&state={state}"
    
    return Response(
        status_code=302,
        headers={"Location": redirect_url}
    )


class TokenRequest(BaseModel):
    grant_type: str
    code: Optional[str] = None
    redirect_uri: Optional[str] = None
    client_id: str
    client_secret: str
    refresh_token: Optional[str] = None


@app.post("/oauth/token")
async def oauth_token(request: TokenRequest):
    """OAuth 令牌端点"""
    if request.grant_type == "authorization_code":
        if not request.code or not request.redirect_uri:
            raise HTTPException(status_code=400, detail="Missing required parameters")
        
        token_data = oauth_provider.exchange_code_for_token(
            code=request.code,
            redirect_uri=request.redirect_uri,
            client_id=request.client_id,
            client_secret=request.client_secret
        )
        
        if not token_data:
            raise HTTPException(status_code=400, detail="Invalid authorization code")
        
        return token_data
    
    elif request.grant_type == "refresh_token":
        if not request.refresh_token:
            raise HTTPException(status_code=400, detail="Missing refresh token")
        
        token_data = oauth_provider.refresh_access_token(
            refresh_token=request.refresh_token,
            client_id=request.client_id,
            client_secret=request.client_secret
        )
        
        if not token_data:
            raise HTTPException(status_code=400, detail="Invalid refresh token")
        
        return token_data
    
    else:
        raise HTTPException(status_code=400, detail="Unsupported grant type")


@app.on_event("startup")
async def startup_event():
    """启动事件"""
    logger.info("Starting Sage MCP HTTP/SSE Server...")
    
    # 预初始化 sage_core
    try:
        await get_sage_core()
        logger.info("Sage core pre-initialized")
    except Exception as e:
        logger.warning(f"Failed to pre-initialize sage core: {e}")
    
    # 初始化 OAuth provider
    global oauth_provider
    oauth_provider = OAuth2Provider(
        client_id=os.getenv("OAUTH_CLIENT_ID", "sage-mcp-client"),
        client_secret=os.getenv("OAUTH_CLIENT_SECRET"),
        jwt_secret=os.getenv("JWT_SECRET")
    )
    logger.info("OAuth provider initialized")


@app.on_event("shutdown")
async def shutdown_event():
    """关闭事件"""
    logger.info("Shutting down Sage MCP HTTP/SSE Server...")
    
    global sage_core
    if sage_core and sage_core._initialized:
        await sage_core.cleanup()
        logger.info("Sage core cleaned up")


if __name__ == "__main__":
    # 运行服务器
    port = int(os.getenv("PORT", "17801"))
    host = os.getenv("HOST", "0.0.0.0")
    
    logger.info(f"Starting server on {host}:{port}")
    
    uvicorn.run(
        app,
        host=host,
        port=port,
        log_level="info"
    )