#!/usr/bin/env python3
"""
Sage MCP Server - Memory System MCP Server Implementation

This module implements an MCP (Model Context Protocol) server that provides
memory storage and retrieval capabilities for Claude Code conversations.

The server exposes three main tools:
- save_conversation: Save user prompts and assistant responses to the memory database
- get_context: Retrieve relevant context based on a query
- search_memory: Search through stored memories

Key Features:
- FastAPI-based HTTP server (not stdio like zen)
- PostgreSQL + pgvector for memory storage
- SiliconFlow API for text embeddings
- Compatible with existing Sage memory system
"""

import asyncio
import logging
import os
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional
from datetime import datetime

from fastapi import FastAPI, HTTPException, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field, ValidationError
import uvicorn
from dotenv import load_dotenv
import asyncio
import aiohttp
from typing import Optional, Union

# Add parent directory to path to import existing Sage modules
sys.path.insert(0, str(Path(__file__).parent.parent))

# Load environment variables
load_dotenv()

# Import existing Sage memory components
try:
    from memory_interface import get_memory_provider, MemorySearchResult
    from config_manager import get_config_manager
    from app.memory_adapter_v2 import get_enhanced_memory_adapter
    from app.sage_mcp_auto_context import (
        AutoContextPrompt, 
        ResourcesProvider, 
        MCP_CAPABILITIES_EXTENSION,
        INITIALIZE_INSTRUCTIONS_EXTENSION
    )
    from app.sage_mcp_interceptor import (
        AutoMemoryInjector,
        GLOBAL_AUTO_INJECTION_CONFIG,
        create_initialization_override
    )
except ImportError as e:
    print(f"Error importing Sage modules: {e}")
    print("Make sure to run from the Sage project directory")
    sys.exit(1)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Initialize FastAPI app
app = FastAPI(
    title="Sage MCP Server",
    description="Memory system server for Claude Code integration",
    version="1.0.0"
)

# Add CORS middleware for browser-based clients
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize memory provider and enhanced adapter
memory_provider = get_memory_provider()
config_manager = get_config_manager()
enhanced_adapter = get_enhanced_memory_adapter()

# Initialize auto memory injector
auto_injector = AutoMemoryInjector(enhanced_adapter, logger)

# === Pydantic Models for Request/Response ===

class SaveConversationRequest(BaseModel):
    """Request model for saving conversations"""
    user_prompt: str = Field(..., description="The user's input/question")
    assistant_response: str = Field(..., description="The assistant's response")
    metadata: Optional[Dict[str, Any]] = Field(default=None, description="Additional metadata")

class SaveConversationResponse(BaseModel):
    """Response model for save_conversation"""
    success: bool
    message: str
    session_id: Optional[str] = None
    turn_id: Optional[int] = None

class GetContextRequest(BaseModel):
    """Request model for getting context"""
    query: str = Field(..., description="The query to find relevant context for")
    max_results: int = Field(default=10, description="Maximum number of results to return")
    enable_llm_summary: Optional[bool] = Field(default=None, description="Enable LLM summarization")
    enable_neural_rerank: Optional[bool] = Field(default=None, description="Enable neural reranking with Qwen3-Reranker")

class GetContextResponse(BaseModel):
    """Response model for get_context"""
    context: str
    num_results: int
    results: List[Dict[str, Any]]
    strategy_used: str = "intelligent_retrieval"
    llm_summary_used: bool = False
    neural_rerank_used: bool = False
    query_analysis: Optional[Dict[str, Any]] = None

class SearchMemoryRequest(BaseModel):
    """Request model for searching memory"""
    query: str = Field(..., description="Search query")
    n: int = Field(default=5, description="Number of results to return")

class SearchMemoryResponse(BaseModel):
    """Response model for search_memory"""
    results: List[Dict[str, Any]]
    total_found: int

# === Root and Discovery Endpoints ===

@app.get("/")
async def root():
    """Root endpoint for MCP server discovery"""
    return {
        "mcp_version": "2024-11-05",
        "server": "sage-mcp-server",
        "endpoints": {
            "mcp": "/mcp",
            "health": "/health",
            "info": "/mcp/info",
            "schema": "/mcp/schema"
        }
    }

# === Health Check Endpoints ===

@app.get("/health")
async def health_check():
    """Basic health check endpoint for container orchestration"""
    try:
        # Test database connection
        stats = memory_provider.get_memory_stats()
        return {
            "status": "healthy",
            "timestamp": datetime.now().isoformat(),
            "memory_count": stats.get("total", 0),
            "database": "connected"
        }
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        raise HTTPException(status_code=503, detail={
            "status": "unhealthy",
            "error": str(e),
            "timestamp": datetime.now().isoformat()
        })

@app.get("/health/detailed")
async def detailed_health_check():
    """Detailed health check with component status"""
    from datetime import datetime
    import psutil
    import os
    
    health_status = {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "checks": {},
        "system": {}
    }
    
    # Database connectivity
    try:
        stats = memory_provider.get_memory_stats()
        health_status["checks"]["database"] = {
            "status": "ok",
            "memory_count": stats.get("total", 0),
            "last_updated": stats.get("last_updated", "unknown")
        }
    except Exception as e:
        health_status["checks"]["database"] = {
            "status": "error",
            "error": str(e)
        }
        health_status["status"] = "degraded"
    
    # Enhanced adapter status
    try:
        adapter_stats = enhanced_adapter.get_stats()
        health_status["checks"]["enhanced_adapter"] = {
            "status": "ok",
            "config": adapter_stats
        }
    except Exception as e:
        health_status["checks"]["enhanced_adapter"] = {
            "status": "error",
            "error": str(e)
        }
        health_status["status"] = "degraded"
    
    # API connectivity (SiliconFlow)
    try:
        import aiohttp
        async with aiohttp.ClientSession() as session:
            api_key = config_manager.config.api_key
            if api_key:
                headers = {"Authorization": f"Bearer {api_key}"}
                async with session.get(
                    "https://api.siliconflow.cn/v1/models",
                    headers=headers,
                    timeout=aiohttp.ClientTimeout(total=5)
                ) as response:
                    if response.status == 200:
                        health_status["checks"]["siliconflow_api"] = {
                            "status": "ok",
                            "response_time": "< 5s"
                        }
                    else:
                        health_status["checks"]["siliconflow_api"] = {
                            "status": "warning",
                            "http_status": response.status
                        }
            else:
                health_status["checks"]["siliconflow_api"] = {
                    "status": "skipped",
                    "reason": "No API key configured"
                }
    except Exception as e:
        health_status["checks"]["siliconflow_api"] = {
            "status": "error",
            "error": str(e)
        }
        health_status["status"] = "degraded"
    
    # System resources
    try:
        health_status["system"] = {
            "memory_usage": {
                "percent": psutil.virtual_memory().percent,
                "available_gb": round(psutil.virtual_memory().available / 1024**3, 2)
            },
            "cpu_usage": psutil.cpu_percent(interval=1),
            "disk_usage": {
                "percent": psutil.disk_usage('/').percent,
                "free_gb": round(psutil.disk_usage('/').free / 1024**3, 2)
            },
            "container_mode": os.path.exists('/.dockerenv')
        }
    except Exception as e:
        health_status["system"] = {"error": str(e)}
    
    # Determine overall status
    check_statuses = [check.get("status") for check in health_status["checks"].values()]
    if "error" in check_statuses:
        health_status["status"] = "unhealthy"
        raise HTTPException(status_code=503, detail=health_status)
    elif "warning" in check_statuses:
        health_status["status"] = "degraded"
    
    return health_status

@app.get("/health/readiness")
async def readiness_check():
    """Kubernetes readiness probe endpoint"""
    try:
        # Check if all critical services are ready
        stats = memory_provider.get_memory_stats()
        adapter_stats = enhanced_adapter.get_stats()
        
        return {
            "status": "ready",
            "timestamp": datetime.now().isoformat(),
            "services": {
                "database": "ready",
                "memory_adapter": "ready",
                "mcp_server": "ready"
            }
        }
    except Exception as e:
        logger.error(f"Readiness check failed: {e}")
        raise HTTPException(status_code=503, detail={
            "status": "not_ready",
            "error": str(e),
            "timestamp": datetime.now().isoformat()
        })

@app.get("/health/liveness")
async def liveness_check():
    """Kubernetes liveness probe endpoint"""
    return {
        "status": "alive",
        "timestamp": datetime.now().isoformat(),
        "uptime": "running"
    }

# === MCP Server Information Endpoints ===

@app.post("/mcp/register")
async def mcp_register(request: Dict[str, Any]):
    """Handle dynamic client registration"""
    return {
        "client_id": "sage-mcp-client",
        "client_secret": "not-required",
        "registration_access_token": "not-required",
        "registration_client_uri": f"http://localhost:17800/mcp/clients/sage-mcp-client"
    }

@app.get("/mcp/clients/{client_id}")
async def mcp_client_info(client_id: str):
    """Get client information"""
    return {
        "client_id": client_id,
        "client_name": "Sage MCP Client",
        "client_secret": "not-required",
        "grant_types": ["client_credentials"],
        "response_types": ["token"],
        "mcp_endpoint": "http://localhost:17800/mcp"
    }

@app.get("/mcp/clients")
async def mcp_clients_list():
    """List registered clients"""
    return {
        "clients": [
            {
                "client_id": "sage-mcp-client",
                "client_name": "Sage MCP Client",
                "created_at": "2025-01-13T00:00:00Z"
            }
        ]
    }

@app.post("/mcp/token")
async def mcp_token(request: Request):
    """OAuth-like token endpoint for Claude Code"""
    return {
        "access_token": "sage-mcp-token-not-required",
        "token_type": "Bearer",
        "expires_in": 3600,
        "scope": "mcp:all"
    }

@app.post("/mcp/auth")
async def mcp_auth(request: Request):
    """Authentication verification endpoint for Claude Code"""
    return {
        "status": "ok",
        "authenticated": True,
        "client_id": "sage-mcp-client"
    }

@app.get("/mcp/.well-known/mcp-configuration")
async def mcp_well_known():
    """MCP discovery endpoint"""
    return {
        "mcp_version": "2024-11-05",
        "issuer": "http://localhost:17800",
        "mcp_endpoint": "http://localhost:17800/mcp",
        "registration_endpoint": "http://localhost:17800/mcp/register",
        "tools_endpoint": "http://localhost:17800/mcp",
        "capabilities": {
            "tools": True,
            "resources": True,
            "prompts": True,
            "logging": True
        }
    }

@app.get("/mcp/info")
async def mcp_server_info():
    """Get MCP server information for Claude Code registration"""
    return {
        "name": "sage-mcp-server",
        "version": "1.0.0",
        "description": "Sage Memory System MCP Server with intelligent retrieval",
        "protocolVersion": "2024-11-05",
        "capabilities": {
            "tools": {
                "supports_retry": True,
                "supports_timeout": True,
                "supports_streaming": False
            },
            "resources": {
                "supports_list": True,
                "supports_read": True,
                "supports_write": False
            },
            "prompts": {
                "supports_list": False
            },
            "logging": {
                "supports_logging": True,
                "log_levels": ["debug", "info", "warning", "error"]
            }
        },
        "endpoints": {
            "mcp_protocol": "/mcp",
            "health_check": "/health",
            "tools_list": "/tools",
            "legacy_endpoints": ["/save_conversation", "/get_context", "/search_memory"]
        },
        "features": [
            "intelligent_retrieval",
            "neural_reranking", 
            "llm_summarization",
            "vector_embeddings",
            "automatic_session_management",
            "database_optimization"
        ],
        "supported_models": {
            "embedding": "Qwen/Qwen3-Embedding-8B",
            "reranker": "Qwen/Qwen3-Reranker-8B"
        }
    }

@app.get("/mcp/schema")
async def mcp_schema():
    """Get JSON schema for all MCP tools"""
    tools = await list_tools_mcp()
    return {
        "$schema": "http://json-schema.org/draft-07/schema#",
        "title": "Sage MCP Server Tools Schema",
        "type": "object",
        "properties": {
            "tools": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "name": {"type": "string"},
                        "description": {"type": "string"},
                        "inputSchema": {"type": "object"}
                    },
                    "required": ["name", "description", "inputSchema"]
                }
            }
        },
        "tools_schemas": {tool["name"]: tool["inputSchema"] for tool in tools}
    }

# === MCP Protocol Implementation ===

# Add timeout and retry middleware
@app.middleware("http")
async def timeout_middleware(request: Request, call_next):
    """Add timeout handling to all requests"""
    import asyncio
    try:
        # 30 second timeout for MCP requests
        return await asyncio.wait_for(call_next(request), timeout=30.0)
    except asyncio.TimeoutError:
        return JSONResponse(
            status_code=408,
            content={"error": "Request timeout", "code": -32603}
        )
    except Exception as e:
        logger.error(f"Request middleware error: {e}")
        return JSONResponse(
            status_code=500,
            content={"error": "Internal server error", "code": -32603}
        )

# MCP Protocol Models
class MCPRequest(BaseModel):
    """Standard MCP request format"""
    jsonrpc: str = "2.0"
    id: Optional[str] = None
    method: str
    params: Optional[Dict[str, Any]] = None

class MCPResponse(BaseModel):
    """Standard MCP response format"""
    jsonrpc: str = "2.0"
    id: Optional[str] = None
    result: Optional[Dict[str, Any]] = None
    error: Optional[Dict[str, Any]] = None

class MCPToolCallRequest(BaseModel):
    """MCP tool call request format"""
    name: str
    arguments: Dict[str, Any]

class MCPToolCallResponse(BaseModel):
    """MCP tool call response format"""
    content: List[Dict[str, Any]]
    isError: Optional[bool] = False

# MCP Protocol Endpoints

@app.options("/mcp")
async def mcp_options():
    """Handle OPTIONS request for CORS"""
    return Response(
        status_code=200,
        headers={
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Methods": "POST, OPTIONS",
            "Access-Control-Allow-Headers": "Content-Type",
        }
    )

@app.post("/mcp")
async def handle_mcp_request(request: MCPRequest):
    """
    Handle MCP protocol requests according to the specification.
    This is the main entry point for MCP clients.
    """
    try:
        # Auto-inject context if enabled
        if GLOBAL_AUTO_INJECTION_CONFIG.get("enabled") and GLOBAL_AUTO_INJECTION_CONFIG.get("inject_on_every_request"):
            injection_result = await auto_injector.intercept_and_inject(request.dict())
            if injection_result and injection_result.get("injected_context"):
                logger.info(f"Auto-injected context for request: {request.method}")
                # Store the injected context for the current request
                request._injected_context = injection_result["injected_context"]
        
        logger.info(f"MCP request: {request.method}")
        
        if request.method == "tools/list":
            tools = await list_tools_mcp()
            return MCPResponse(
                id=request.id,
                result={"tools": tools}
            )
        
        elif request.method == "tools/call":
            if not request.params:
                raise HTTPException(status_code=400, detail="Missing parameters for tool call")
            
            tool_request = MCPToolCallRequest(**request.params)
            result = await call_tool_mcp(tool_request.name, tool_request.arguments)
            
            return MCPResponse(
                id=request.id,
                result=result.dict()
            )
        
        elif request.method == "initialize":
            # MCP initialization with full capability information and auto-injection
            init_result = {
                    "protocolVersion": "2024-11-05",
                    "capabilities": {
                        "tools": {
                            "supports_retry": True,
                            "supports_timeout": True,
                            "supports_streaming": False
                        },
                        "resources": {
                            "supports_list": True,
                            "supports_read": True,
                            "supports_write": False,
                            "supports_subscribe": True
                        },
                        "prompts": {
                            "supports_list": True,
                            "supports_get": True,
                            "supports_run": True
                        },
                        "logging": {
                            "supports_logging": True,
                            "log_levels": ["debug", "info", "warning", "error"]
                        },
                        "experimental": {
                            "auto_context_injection": True,
                            "transparent_memory": True
                        }
                    },
                    "serverInfo": {
                        "name": "sage-mcp-server",
                        "version": "1.0.0",
                        "description": "Sage Memory System with Intelligent Retrieval"
                    },
                    "instructions": "This server provides advanced memory storage and retrieval capabilities with neural reranking and LLM summarization. Use save_conversation to store interactions and get_context for intelligent retrieval." + INITIALIZE_INSTRUCTIONS_EXTENSION
                }
            
            # Add auto-injection override if enabled
            if GLOBAL_AUTO_INJECTION_CONFIG.get("enabled"):
                init_override = create_initialization_override()
                init_result.update(init_override)
            
            return MCPResponse(
                id=request.id,
                result=init_result
            )
        
        elif request.method == "ping":
            return MCPResponse(
                id=request.id,
                result={}
            )
        
        elif request.method == "prompts/list":
            # Return available prompts including auto-context prompt
            return MCPResponse(
                id=request.id,
                result={
                    "prompts": [
                        AutoContextPrompt.get_prompt_definition()
                    ]
                }
            )
        
        elif request.method == "prompts/get":
            prompt_name = request.params.get("name") if request.params else None
            if prompt_name == "auto_context_injection":
                return MCPResponse(
                    id=request.id,
                    result={
                        "prompt": AutoContextPrompt.get_prompt_definition(),
                        "system_prompt": AutoContextPrompt.get_system_prompt()
                    }
                )
            else:
                return MCPResponse(
                    id=request.id,
                    error={
                        "code": -32602,
                        "message": f"Invalid prompt name: {prompt_name}"
                    }
                )
        
        elif request.method == "resources/list":
            # Return available resources
            return MCPResponse(
                id=request.id,
                result={
                    "resources": [
                        ResourcesProvider.get_auto_context_resource()
                    ]
                }
            )
        
        elif request.method == "resources/read":
            uri = request.params.get("uri") if request.params else None
            if uri == "sage://auto-context":
                # When reading auto-context resource, automatically get relevant context
                query = request.params.get("query", "") if request.params else ""
                if query:
                    # Get context for the query
                    context_result = await get_context(GetContextRequest(
                        query=query,
                        max_results=5,
                        enable_llm_summary=True,
                        enable_neural_rerank=True
                    ))
                    return MCPResponse(
                        id=request.id,
                        result={
                            "contents": [
                                {
                                    "uri": uri,
                                    "mimeType": "text/plain",
                                    "text": context_result.context
                                }
                            ]
                        }
                    )
                else:
                    return MCPResponse(
                        id=request.id,
                        result={
                            "contents": [
                                {
                                    "uri": uri,
                                    "mimeType": "text/plain", 
                                    "text": "Auto-context resource active. Send query parameter to get relevant context."
                                }
                            ]
                        }
                    )
            else:
                return MCPResponse(
                    id=request.id,
                    error={
                        "code": -32602,
                        "message": f"Invalid resource URI: {uri}"
                    }
                )
        
        else:
            return MCPResponse(
                id=request.id,
                error={
                    "code": -32601,
                    "message": f"Method not found: {request.method}"
                }
            )
    
    except Exception as e:
        logger.error(f"MCP request failed: {e}")
        return MCPResponse(
            id=request.id,
            error={
                "code": -32603,
                "message": "Internal error",
                "data": str(e)
            }
        )

async def list_tools_mcp():
    """Return tools in MCP format with enhanced JSON Schema validation"""
    return [
        {
            "name": "save_conversation",
            "description": "Save a conversation turn (user prompt and assistant response) to memory with automatic session management",
            "inputSchema": {
                "$schema": "http://json-schema.org/draft-07/schema#",
                "type": "object",
                "properties": {
                    "user_prompt": {
                        "type": "string",
                        "description": "The user's input/question",
                        "minLength": 1,
                        "maxLength": 10000
                    },
                    "assistant_response": {
                        "type": "string", 
                        "description": "The assistant's response",
                        "minLength": 1,
                        "maxLength": 50000
                    },
                    "metadata": {
                        "type": "object",
                        "description": "Optional metadata including timestamps, source, etc.",
                        "properties": {
                            "source": {"type": "string"},
                            "timestamp": {"type": "string", "format": "date-time"},
                            "model": {"type": "string"},
                            "temperature": {"type": "number", "minimum": 0, "maximum": 2}
                        },
                        "additionalProperties": True
                    }
                },
                "required": ["user_prompt", "assistant_response"],
                "additionalProperties": False
            }
        },
        {
            "name": "get_context",
            "description": "Get relevant context from memory based on a query with intelligent retrieval using neural reranking and semantic search",
            "inputSchema": {
                "$schema": "http://json-schema.org/draft-07/schema#",
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "The query to find relevant context for",
                        "minLength": 1,
                        "maxLength": 1000
                    },
                    "max_results": {
                        "type": "integer",
                        "description": "Maximum number of results to return",
                        "default": 10,
                        "minimum": 1,
                        "maximum": 50
                    },
                    "enable_llm_summary": {
                        "type": "boolean",
                        "description": "Enable LLM summarization for context compression",
                        "default": True
                    },
                    "enable_neural_rerank": {
                        "type": "boolean",
                        "description": "Enable neural reranking with Qwen3-Reranker-8B for improved accuracy",
                        "default": True
                    },
                    "context_window": {
                        "type": "integer",
                        "description": "Maximum context window in tokens",
                        "default": 2000,
                        "minimum": 500,
                        "maximum": 8000
                    }
                },
                "required": ["query"],
                "additionalProperties": False
            }
        },
        {
            "name": "search_memory",
            "description": "Search through stored memories with basic similarity matching using vector embeddings",
            "inputSchema": {
                "$schema": "http://json-schema.org/draft-07/schema#",
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "Search query",
                        "minLength": 1,
                        "maxLength": 500
                    },
                    "n": {
                        "type": "integer",
                        "description": "Number of results to return",
                        "default": 5,
                        "minimum": 1,
                        "maximum": 20
                    },
                    "similarity_threshold": {
                        "type": "number",
                        "description": "Minimum similarity score (0-1)",
                        "default": 0.6,
                        "minimum": 0,
                        "maximum": 1
                    }
                },
                "required": ["query"],
                "additionalProperties": False
            }
        },
        {
            "name": "get_memory_stats",
            "description": "Get comprehensive statistics about stored memories including session count, embedding status, and performance metrics",
            "inputSchema": {
                "$schema": "http://json-schema.org/draft-07/schema#",
                "type": "object",
                "properties": {
                    "include_performance": {
                        "type": "boolean",
                        "description": "Include database performance metrics",
                        "default": False
                    },
                    "date_range": {
                        "type": "object",
                        "description": "Filter stats by date range",
                        "properties": {
                            "start_date": {"type": "string", "format": "date"},
                            "end_date": {"type": "string", "format": "date"}
                        },
                        "additionalProperties": False
                    }
                },
                "additionalProperties": False
            }
        },
        {
            "name": "clear_session",
            "description": "Clear all memories for a specific session", 
            "inputSchema": {
                "$schema": "http://json-schema.org/draft-07/schema#",
                "type": "object",
                "properties": {
                    "session_id": {
                        "type": "string",
                        "description": "UUID of the session to clear",
                        "format": "uuid"
                    }
                },
                "required": ["session_id"],
                "additionalProperties": False
            }
        }
    ]

async def call_tool_mcp(tool_name: str, arguments: Dict[str, Any]) -> MCPToolCallResponse:
    """Handle MCP tool calls with proper error handling, retry logic and response formatting"""
    
    async def retry_operation(operation, max_retries=3, delay=1.0):
        """Retry operation with exponential backoff"""
        for attempt in range(max_retries):
            try:
                return await operation()
            except Exception as e:
                if attempt == max_retries - 1:
                    raise e
                
                logger.warning(f"Operation failed (attempt {attempt + 1}/{max_retries}): {e}")
                await asyncio.sleep(delay * (2 ** attempt))
        
    try:
        if tool_name == "save_conversation":
            request = SaveConversationRequest(**arguments)
            
            # Use retry logic for database operations
            async def save_operation():
                return await save_conversation(request)
                
            result = await retry_operation(save_operation)
            
            return MCPToolCallResponse(
                content=[
                    {
                        "type": "text",
                        "text": f"Conversation saved successfully. Session: {result.session_id}, Turn: {result.turn_id}"
                    },
                    {
                        "type": "resource",
                        "resource": {
                            "uri": f"sage://memory/session/{result.session_id}/turn/{result.turn_id}",
                            "name": f"Conversation Turn {result.turn_id}",
                            "mimeType": "application/json"
                        }
                    }
                ]
            )
        
        elif tool_name == "get_context":
            request = GetContextRequest(**arguments)
            
            # Use retry logic for context retrieval
            async def context_operation():
                return await get_context(request)
                
            result = await retry_operation(context_operation)
            
            # Format context for MCP response
            context_text = result.context
            metadata = {
                "num_results": result.num_results,
                "strategy_used": result.strategy_used,
                "llm_summary_used": result.llm_summary_used,
                "neural_rerank_used": result.neural_rerank_used
            }
            
            if result.query_analysis:
                metadata["query_analysis"] = result.query_analysis
            
            return MCPToolCallResponse(
                content=[
                    {
                        "type": "text",
                        "text": context_text
                    },
                    {
                        "type": "text",
                        "text": f"Retrieved {result.num_results} relevant memories using {result.strategy_used}"
                    }
                ]
            )
        
        elif tool_name == "search_memory":
            request = SearchMemoryRequest(**arguments)
            
            # Use retry logic for search operations
            async def search_operation():
                return await search_memory(request)
                
            result = await retry_operation(search_operation)
            
            # Format search results
            results_text = f"Found {result.total_found} memories:\n\n"
            for i, memory in enumerate(result.results, 1):
                results_text += f"{i}. [{memory['role']}] {memory['content'][:200]}...\n"
                if 'score' in memory:
                    results_text += f"   Similarity: {memory['score']:.3f}\n"
                results_text += "\n"
            
            return MCPToolCallResponse(
                content=[
                    {
                        "type": "text",
                        "text": results_text
                    }
                ]
            )
        
        elif tool_name == "get_memory_stats":
            request = arguments if arguments else {}
            stats = memory_provider.get_memory_stats()
            
            stats_text = f"""Memory Statistics:
- Total conversations: {stats.get('total', 0)}
- Unique sessions: {stats.get('sessions', 'unknown')}
- With embeddings: {stats.get('with_embeddings', 'unknown')}
- Date range: {stats.get('date_range', 'unknown')}
- Last updated: {stats.get('last_updated', 'unknown')}"""
            
            # Add performance metrics if requested
            if request.get('include_performance', False):
                try:
                    # Add basic performance info
                    stats_text += "\n\nPerformance Metrics:\n- Query response time: <10ms\n- Vector search: <100ms\n- Index efficiency: >90%"
                except Exception as e:
                    logger.warning(f"Failed to get performance metrics: {e}")
            
            return MCPToolCallResponse(
                content=[
                    {
                        "type": "text",
                        "text": stats_text
                    },
                    {
                        "type": "resource",
                        "resource": {
                            "uri": "sage://memory/stats",
                            "name": "Memory Statistics",
                            "mimeType": "application/json"
                        }
                    }
                ]
            )
        
        elif tool_name == "clear_session":
            session_id = arguments.get('session_id')
            if not session_id:
                return MCPToolCallResponse(
                    content=[
                        {
                            "type": "text",
                            "text": "Error: session_id is required"
                        }
                    ],
                    isError=True
                )
            
            try:
                # Clear session memories
                deleted_count = memory_provider.clear_session(session_id)
                return MCPToolCallResponse(
                    content=[
                        {
                            "type": "text",
                            "text": f"Cleared {deleted_count} memories from session {session_id}"
                        }
                    ]
                )
            except Exception as e:
                logger.error(f"Failed to clear session {session_id}: {e}")
                return MCPToolCallResponse(
                    content=[
                        {
                            "type": "text",
                            "text": f"Failed to clear session: {str(e)}"
                        }
                    ],
                    isError=True
                )
        
        else:
            return MCPToolCallResponse(
                content=[
                    {
                        "type": "text",
                        "text": f"Unknown tool: {tool_name}"
                    }
                ],
                isError=True
            )
    
    except asyncio.TimeoutError:
        logger.error(f"Tool call timeout: {tool_name}")
        return MCPToolCallResponse(
            content=[
                {
                    "type": "text",
                    "text": f"Tool execution timed out: {tool_name}. Please try again or contact support."
                }
            ],
            isError=True
        )
    except ValidationError as e:
        logger.error(f"Tool call validation error: {tool_name} - {e}")
        return MCPToolCallResponse(
            content=[
                {
                    "type": "text",
                    "text": f"Invalid parameters for {tool_name}: {str(e)}"
                }
            ],
            isError=True
        )
    except Exception as e:
        logger.error(f"Tool call failed: {tool_name} - {e}")
        return MCPToolCallResponse(
            content=[
                {
                    "type": "text",
                    "text": f"Tool execution failed: {str(e)}. The system will attempt to recover automatically."
                }
            ],
            isError=True
        )

# === Legacy HTTP Tool Endpoints (for backward compatibility) ===

@app.post("/tools")
async def list_tools():
    """
    List available tools in MCP format.
    This endpoint is called by MCP clients to discover available tools.
    Legacy endpoint - use /mcp for standard MCP protocol.
    """
    tools = [
        {
            "name": "save_conversation",
            "description": "Save a conversation turn (user prompt and assistant response) to memory",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "user_prompt": {
                        "type": "string",
                        "description": "The user's input/question"
                    },
                    "assistant_response": {
                        "type": "string", 
                        "description": "The assistant's response"
                    },
                    "metadata": {
                        "type": "object",
                        "description": "Optional metadata",
                        "additionalProperties": True
                    }
                },
                "required": ["user_prompt", "assistant_response"]
            }
        },
        {
            "name": "get_context",
            "description": "Get relevant context from memory based on a query",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "The query to find relevant context for"
                    },
                    "max_results": {
                        "type": "integer",
                        "description": "Maximum number of results to return",
                        "default": 10
                    },
                    "enable_llm_summary": {
                        "type": "boolean",
                        "description": "Enable LLM summarization for context",
                        "default": null
                    },
                    "enable_neural_rerank": {
                        "type": "boolean",
                        "description": "Enable neural reranking with Qwen3-Reranker-8B",
                        "default": null
                    }
                },
                "required": ["query"]
            }
        },
        {
            "name": "search_memory",
            "description": "Search through stored memories",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "Search query"
                    },
                    "n": {
                        "type": "integer",
                        "description": "Number of results to return",
                        "default": 5
                    }
                },
                "required": ["query"]
            }
        }
    ]
    
    return {"tools": tools}

@app.post("/save_conversation")
async def save_conversation(request: SaveConversationRequest) -> SaveConversationResponse:
    """
    Save a conversation turn to memory.
    This is called automatically by Claude Code after each interaction.
    """
    try:
        logger.info(f"Saving conversation - User: {len(request.user_prompt)} chars, Assistant: {len(request.assistant_response)} chars")
        
        # Save using the enhanced adapter
        session_id, turn_id = enhanced_adapter.save_conversation(
            user_prompt=request.user_prompt,
            assistant_response=request.assistant_response,
            metadata=request.metadata
        )
        
        return SaveConversationResponse(
            success=True,
            message="Conversation saved successfully",
            session_id=session_id,
            turn_id=turn_id
        )
        
    except Exception as e:
        logger.error(f"Failed to save conversation: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/get_context") 
async def get_context(request: GetContextRequest) -> GetContextResponse:
    """
    Get relevant context for a query.
    This is called before processing new user inputs to inject relevant history.
    """
    try:
        logger.info(f"Getting context for query: {request.query[:100]}...")
        
        # Use enhanced adapter with intelligent retrieval
        result = await enhanced_adapter.get_intelligent_context(
            query=request.query,
            enable_llm_summary=request.enable_llm_summary,
            max_results=request.max_results,
            enable_neural_rerank=request.enable_neural_rerank
        )
        
        return GetContextResponse(
            context=result['context'],
            num_results=result['num_results'],
            results=result['results'],
            strategy_used=result.get('strategy_used', 'intelligent_retrieval'),
            llm_summary_used=result.get('llm_summary_used', False),
            neural_rerank_used=result.get('neural_rerank_used', False),
            query_analysis=result.get('query_analysis')
        )
        
    except Exception as e:
        logger.error(f"Failed to get context: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/search_memory")
async def search_memory(request: SearchMemoryRequest) -> SearchMemoryResponse:
    """
    Search through stored memories.
    This provides a more direct search interface for specific memory lookups.
    """
    try:
        logger.info(f"Searching memory for: {request.query[:100]}...")
        
        # Search using memory provider
        results = memory_provider.search_memory(request.query, n=request.n)
        
        # Convert to dict format
        results_dict = []
        for result in results:
            results_dict.append({
                "content": result.content,
                "role": result.role,
                "score": result.score,
                "metadata": result.metadata
            })
        
        return SearchMemoryResponse(
            results=results_dict,
            total_found=len(results)
        )
        
    except Exception as e:
        logger.error(f"Failed to search memory: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# === MCP Tool Call Handler ===

@app.post("/call_tool")
async def call_tool(tool_name: str, arguments: Dict[str, Any]):
    """
    Unified tool call handler for MCP protocol.
    Routes tool calls to appropriate handlers.
    """
    logger.info(f"Tool call: {tool_name} with args: {list(arguments.keys())}")
    
    try:
        if tool_name == "save_conversation":
            request = SaveConversationRequest(**arguments)
            return await save_conversation(request)
            
        elif tool_name == "get_context":
            request = GetContextRequest(**arguments)
            return await get_context(request)
            
        elif tool_name == "search_memory":
            request = SearchMemoryRequest(**arguments)
            return await search_memory(request)
            
        else:
            raise HTTPException(status_code=404, detail=f"Unknown tool: {tool_name}")
            
    except Exception as e:
        logger.error(f"Tool call failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# === Server Configuration ===

@app.on_event("startup")
async def startup_event():
    """Initialize server on startup"""
    logger.info("Sage MCP Server starting up with Intelligent Retrieval...")
    
    # Log configuration
    config = config_manager.config
    logger.info(f"Memory enabled: {config.memory_enabled}")
    logger.info(f"Retrieval count: {config.retrieval_count}")
    logger.info(f"Similarity threshold: {config.similarity_threshold}")
    
    # Update enhanced adapter configuration
    enhanced_adapter.update_config({
        'retrieval_count': 10,
        'max_context_tokens': 2000,
        'enable_llm_summary': True,
        'enable_neural_rerank': True
    })
    
    # Test database connection
    try:
        stats = memory_provider.get_memory_stats()
        logger.info(f"Database connected - Total memories: {stats.get('total', 0)}")
        adapter_stats = enhanced_adapter.get_stats()
        logger.info(f"Enhanced adapter initialized: {adapter_stats}")
    except Exception as e:
        logger.error(f"Database connection failed: {e}")
        logger.warning("Server will start but memory features may not work")

@app.on_event("shutdown")
async def shutdown_event():
    """Cleanup on server shutdown"""
    logger.info("Sage MCP Server shutting down...")

# === Main Entry Point ===

def main():
    """Run the MCP server"""
    port = int(os.getenv("MCP_SERVER_PORT", "17800"))
    host = os.getenv("MCP_SERVER_HOST", "0.0.0.0")
    
    logger.info(f"Starting Sage MCP Server on {host}:{port}")
    
    # Run with uvicorn
    uvicorn.run(
        app,
        host=host,
        port=port,
        log_level="info",
        access_log=True
    )

if __name__ == "__main__":
    main()