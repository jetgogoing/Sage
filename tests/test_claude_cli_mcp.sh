#!/bin/bash

echo "=== 测试 Claude CLI MCP 集成 ==="
echo

echo "1. 检查 Sage MCP 服务状态:"
curl -s http://localhost:17800/health | python3 -m json.tool || echo "HTTP 服务未响应"
echo

echo "2. 当前 MCP 配置:"
/Users/jet/.claude/local/node_modules/.bin/claude mcp list
echo

echo "3. 创建测试日志目录:"
mkdir -p /tmp/sage_mcp_logs
echo

echo "4. 使用 Claude CLI 测试 MCP:"
echo "请在 Claude 中输入以下命令测试："
echo "  - 保存记忆: 'Please save this memory: Claude CLI MCP test successful'"
echo "  - 搜索记忆: 'Search for: Claude CLI MCP test'"
echo "  - 查看统计: 'Show memory statistics'"
echo

echo "启动 Claude CLI..."
echo "提示: 如果看不到 MCP 工具，尝试输入 'What tools are available?' 或 'List all available tools'"
echo

# 启动 Claude CLI
/Users/jet/.claude/local/node_modules/.bin/claude