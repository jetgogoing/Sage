#!/bin/bash

echo "🔧 Claude CLI + Sage MCP 诊断与启动脚本"
echo "========================================"
echo

# 1. 检查 Claude CLI 版本
echo "📌 Claude CLI 信息:"
/Users/jet/.claude/local/node_modules/.bin/claude --version
echo

# 2. 检查 MCP 配置
echo "📌 MCP 服务器配置:"
/Users/jet/.claude/local/node_modules/.bin/claude mcp list
echo

# 3. 检查 Sage 服务状态
echo "📌 Sage Docker 服务状态:"
if docker ps --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}" | grep sage; then
    echo
    echo "✅ Docker 服务运行中"
    
    # 检查健康状态
    echo
    echo "📌 Sage MCP 健康检查:"
    if curl -s http://localhost:17800/health | python3 -m json.tool; then
        echo "✅ HTTP 服务正常"
    else
        echo "❌ HTTP 服务异常"
    fi
else
    echo "❌ Docker 服务未运行"
    echo
    read -p "是否启动 Docker 服务? (y/n) " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        cd /Users/jet/sage
        docker-compose -f docker-compose.optimized.yml up -d
        echo "等待服务启动..."
        sleep 5
    fi
fi

# 4. 测试 stdio 包装器
echo
echo "📌 测试 Sage MCP stdio 包装器:"
echo '{"jsonrpc":"2.0","method":"initialize","params":{"protocolVersion":"1.0.0"},"id":"test"}' | \
    /Users/jet/sage/start_sage_mcp_stdio.sh 2>/dev/null | head -1 | python3 -m json.tool || echo "❌ stdio 包装器异常"

# 5. 检查日志
echo
echo "📌 最近的错误日志:"
for log in /tmp/sage_mcp*.log; do
    if [ -f "$log" ]; then
        echo "📄 $log (最后5行):"
        tail -5 "$log" | grep -E "(ERROR|error|Error)" || echo "  无错误"
    fi
done

echo
echo "========================================"
echo "📌 使用说明:"
echo "1. 在 Claude 中测试 MCP 工具:"
echo "   - 输入: 'What tools are available?'"
echo "   - 输入: 'List all available tools'"
echo "   - 输入: 'Show me the sage tools'"
echo
echo "2. 如果看不到工具，尝试:"
echo "   - 重启 Claude CLI"
echo "   - 使用 --mcp-config 参数: claude --mcp-config /Users/jet/sage/claude_mcp_config.json"
echo
echo "3. 测试记忆功能:"
echo "   - 保存: 'Save this memory: test from Claude CLI'"
echo "   - 搜索: 'Search memories for: test'"
echo "   - 统计: 'Show memory statistics'"
echo

read -p "按回车键启动 Claude CLI..."
echo

# 启动 Claude CLI
/Users/jet/.claude/local/node_modules/.bin/claude "$@"