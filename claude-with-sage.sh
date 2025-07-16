#!/bin/bash

# Claude CLI with Sage MCP
# 这个脚本确保 Sage MCP 正确加载

echo "🚀 启动 Claude CLI with Sage MCP..."
echo

# 检查 Docker 服务
if docker ps | grep -q sage-mcp-server; then
    echo "✅ Sage MCP Docker 服务运行中"
else
    echo "⚠️  Sage MCP Docker 服务未运行，正在启动..."
    cd /Users/jet/sage
    docker-compose -f docker-compose.optimized.yml up -d
    sleep 3
fi

# 验证健康状态
echo
echo "🔍 检查 Sage MCP 健康状态:"
curl -s http://localhost:17800/health | python3 -m json.tool || echo "❌ 服务未响应"

echo
echo "📋 当前 MCP 服务器列表:"
/Users/jet/.claude/local/node_modules/.bin/claude mcp list

echo
echo "💡 提示:"
echo "  1. 输入 'What tools are available?' 查看可用工具"
echo "  2. 使用 'Save this memory: ...' 保存记忆"
echo "  3. 使用 'Search memory for: ...' 搜索记忆"
echo "  4. 使用 'Show memory stats' 查看统计"
echo
echo "启动 Claude CLI..."
echo "---"

# 启动 Claude CLI
exec /Users/jet/.claude/local/node_modules/.bin/claude "$@"