"""
Sage Claude Code Integration
完美集成方案 - 确保Claude Code在任何项目下都自动使用Sage记忆
"""

# Claude Code配置文件内容
# 这个配置应该添加到 ~/.config/claude/mcp.json 或类似位置
CLAUDE_CODE_MCP_CONFIG = {
    "sage": {
        "url": "http://localhost:17800/mcp",
        "transport": "http",
        "auto_start": True,
        "initialization": {
            "system_prompt_prepend": """
# Memory System Active

You have access to a persistent memory system that automatically:
1. Retrieves relevant context from past conversations
2. Saves important information for future reference
3. Works transparently across all projects

Always consider relevant historical context when responding.
""",
            "auto_tools": [
                {
                    "trigger": "on_user_message",
                    "tool": "get_context",
                    "params_template": {
                        "query": "${user_message}",
                        "max_results": 5,
                        "enable_neural_rerank": True
                    }
                },
                {
                    "trigger": "on_conversation_end",
                    "tool": "save_conversation",
                    "params_template": {
                        "user_prompt": "${last_user_message}",
                        "assistant_response": "${last_assistant_response}"
                    }
                }
            ]
        }
    }
}

# MCP服务器端配置增强
MCP_SERVER_ENHANCEMENTS = {
    "prompts": {
        "system_integration": {
            "name": "system_integration",
            "description": "System-level integration prompt that runs automatically",
            "auto_execute": True,
            "trigger": "on_every_request",
            "template": """
Before responding to the user's message: "${user_message}"

1. Search for relevant historical context using get_context
2. Consider all relevant past conversations
3. Provide a response that builds on accumulated knowledge
4. Save important information if this conversation contains new insights

The memory system enhances every interaction transparently.
"""
        }
    },
    "hooks": {
        "pre_request": """
async def pre_request_hook(request):
    # 自动为每个请求注入上下文
    if request.get("method") != "tools/call":
        # 提取用户消息
        user_message = extract_user_message(request)
        if user_message:
            # 获取相关上下文
            context = await get_relevant_context(user_message)
            # 注入到请求中
            inject_context(request, context)
""",
        "post_response": """
async def post_response_hook(request, response):
    # 自动保存重要对话
    if should_save_conversation(request, response):
        await save_conversation_auto(request, response)
"""
    }
}

# 安装脚本
INSTALLATION_SCRIPT = """
#!/bin/bash
# Sage MCP 自动集成安装脚本

echo "🚀 正在配置Sage MCP自动集成..."

# 1. 确保MCP配置目录存在
mkdir -p ~/.config/claude

# 2. 创建或更新MCP配置
cat > ~/.config/claude/sage_auto_integration.json << 'EOF'
{
  "sage_memory": {
    "enabled": true,
    "auto_inject": true,
    "transparent_mode": true
  }
}
EOF

# 3. 创建Claude Code启动包装器
cat > ~/.local/bin/claude-with-memory << 'EOF'
#!/bin/bash
# Claude Code with Sage Memory

# 确保Sage MCP服务器运行
if ! curl -s http://localhost:17800/health > /dev/null; then
    echo "启动Sage MCP服务器..."
    cd "/Volumes/1T HDD/Sage" && python3 app/sage_mcp_server.py &
    sleep 5
fi

# 启动Claude Code
claude "$@"
EOF

chmod +x ~/.local/bin/claude-with-memory

echo "✅ 安装完成！"
echo "使用 'claude-with-memory' 命令启动带记忆功能的Claude Code"
"""