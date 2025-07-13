"""
Sage MCP Auto Context Injection Module
自动上下文注入模块 - 让Claude Code自动使用记忆功能
"""

from typing import Dict, Any, List, Optional
from pydantic import BaseModel

class MCPPromptDefinition(BaseModel):
    """MCP Prompt定义"""
    name: str
    description: str
    arguments: List[Dict[str, Any]]
    
class AutoContextPrompt:
    """自动上下文注入提示"""
    
    @staticmethod
    def get_prompt_definition() -> Dict[str, Any]:
        """获取自动上下文提示定义"""
        return {
            "name": "auto_context_injection",
            "description": "Automatically inject relevant context from memory for every conversation",
            "arguments": [
                {
                    "name": "query",
                    "description": "The current user input to find relevant context for",
                    "required": True
                },
                {
                    "name": "auto_inject",
                    "description": "Whether to automatically inject context",
                    "required": False,
                    "default": True
                }
            ]
        }
    
    @staticmethod
    def get_system_prompt() -> str:
        """获取系统提示"""
        return """
# Automatic Context Injection

This conversation has access to a memory system. For EVERY user message:
1. Automatically search for relevant historical context
2. Include relevant memories in your response consideration
3. Save important conversations for future reference

You don't need to explicitly mention using these tools unless asked.
The memory system works transparently in the background.
"""

class ResourcesProvider:
    """MCP Resources提供器"""
    
    @staticmethod
    def get_auto_context_resource() -> Dict[str, Any]:
        """获取自动上下文资源定义"""
        return {
            "uri": "sage://auto-context",
            "name": "Automatic Context Injection",
            "description": "Automatically provides relevant context for every conversation",
            "mimeType": "application/x-sage-auto-context"
        }

# MCP协议扩展：添加到capabilities
MCP_CAPABILITIES_EXTENSION = {
    "prompts": {
        "supports_list": True,
        "supports_get": True,
        "supports_run": True
    },
    "resources": {
        "supports_list": True,
        "supports_read": True,
        "supports_write": False,
        "supports_subscribe": True
    },
    "experimental": {
        "auto_context_injection": True,
        "transparent_memory": True
    }
}

# 初始化指令扩展
INITIALIZE_INSTRUCTIONS_EXTENSION = """

## Automatic Memory Integration

This MCP server provides automatic memory integration. Every conversation will:
- Automatically retrieve relevant historical context
- Save important information for future reference
- Work transparently without explicit tool calls

The memory system is always active and enhances every interaction.
"""