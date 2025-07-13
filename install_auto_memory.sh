#!/bin/bash
# Sage MCP 自动记忆集成安装脚本
# 这个脚本会配置Claude Code始终使用Sage记忆系统

echo "🚀 Sage MCP 自动记忆集成安装程序"
echo "================================"

# 检查是否安装了Claude Code
if ! command -v claude &> /dev/null; then
    echo "❌ 错误: 未找到Claude Code命令行工具"
    echo "请先安装Claude Code: https://claude.ai/download"
    exit 1
fi

# 获取Sage项目路径
SAGE_PATH="/Volumes/1T HDD/Sage"
if [ ! -d "$SAGE_PATH" ]; then
    echo "请输入Sage项目的完整路径:"
    read -r SAGE_PATH
fi

echo "📁 Sage项目路径: $SAGE_PATH"

# 创建配置目录
mkdir -p ~/.config/claude/mcp-servers

# 1. 创建增强的MCP服务器启动脚本
cat > ~/.config/claude/mcp-servers/sage-auto-memory.sh << EOF
#!/bin/bash
# Sage自动记忆启动脚本

# 设置环境变量
export SAGE_AUTO_MEMORY=true
export SAGE_PATH="$SAGE_PATH"

# 启动Docker（如果需要）
if command -v docker &> /dev/null; then
    cd "$SAGE_PATH" && docker-compose up -d postgres 2>/dev/null || true
fi

# 启动Sage MCP服务器
cd "$SAGE_PATH" && python3 app/sage_mcp_server.py
EOF

chmod +x ~/.config/claude/mcp-servers/sage-auto-memory.sh

# 2. 更新Claude MCP配置
echo "📝 更新Claude MCP配置..."

# 备份现有配置
if [ -f ~/.config/claude/mcp.json ]; then
    cp ~/.config/claude/mcp.json ~/.config/claude/mcp.json.backup
fi

# 创建新的MCP配置
cat > ~/.config/claude/mcp.json << 'EOF'
{
  "servers": {
    "sage": {
      "command": "~/.config/claude/mcp-servers/sage-auto-memory.sh",
      "transport": "stdio",
      "auto_start": true,
      "required": true,
      "initialization": {
        "retry_attempts": 3,
        "retry_delay": 1000
      }
    }
  },
  "defaults": {
    "auto_inject_context": true,
    "save_conversations": true
  }
}
EOF

# 3. 创建Claude Code别名
echo "🔧 创建命令行别名..."

# 检测shell类型
if [ -n "$ZSH_VERSION" ]; then
    SHELL_RC="$HOME/.zshrc"
elif [ -n "$BASH_VERSION" ]; then
    SHELL_RC="$HOME/.bashrc"
else
    SHELL_RC="$HOME/.profile"
fi

# 添加别名（如果不存在）
if ! grep -q "alias claude=" "$SHELL_RC"; then
    echo "" >> "$SHELL_RC"
    echo "# Sage MCP自动记忆集成" >> "$SHELL_RC"
    echo "alias claude='claude --mcp-server sage'" >> "$SHELL_RC"
fi

# 4. 创建系统级集成脚本
sudo tee /usr/local/bin/claude-memory > /dev/null << 'EOF'
#!/bin/bash
# Claude Code with Automatic Memory

# 确保Sage MCP服务器运行
if ! curl -s http://localhost:17800/health > /dev/null 2>&1; then
    echo "🚀 启动Sage记忆系统..."
    ~/.config/claude/mcp-servers/sage-auto-memory.sh &
    sleep 3
fi

# 启动Claude Code
exec claude "$@"
EOF

sudo chmod +x /usr/local/bin/claude-memory

echo ""
echo "✅ 安装完成！"
echo ""
echo "🎯 使用方法:"
echo "  1. 重新加载shell配置: source $SHELL_RC"
echo "  2. 使用命令 'claude' 启动带自动记忆的Claude Code"
echo "  3. 或使用 'claude-memory' 确保记忆系统运行"
echo ""
echo "🔍 验证安装:"
echo "  claude mcp list  # 应该看到sage服务器"
echo ""
echo "📝 注意事项:"
echo "  - Sage MCP服务器会在后台自动启动"
echo "  - 所有对话会自动保存和检索"
echo "  - 无需手动调用记忆工具"