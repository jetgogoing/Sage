#!/bin/bash
# Sage 记忆系统快速设置脚本

echo "🚀 Sage 记忆系统设置开始..."

# 1. 检查Docker服务
echo "📦 检查Docker服务..."
cd "/Users/jet/sage"
docker compose ps | grep "Up" > /dev/null
if [ $? -eq 0 ]; then
    echo "✅ PostgreSQL数据库运行正常"
else
    echo "🔄 启动PostgreSQL数据库..."
    docker compose up -d
    sleep 5
fi

# 2. 验证API密钥
echo "🔑 验证API密钥..."
export SILICONFLOW_API_KEY="sk-xtjxdvdwjfiiggwxkojmiryhcfjliywfzurbtsorwvgkimdg"
python3 -c "
from memory import embed_text
try:
    embed_text('测试')
    print('✅ API密钥验证成功')
except Exception as e:
    print(f'❌ API密钥验证失败: {e}')
    exit(1)
"

# 3. 查找Claude CLI路径
echo "🔍 查找Claude CLI..."
CLAUDE_PATH=""
if command -v claude &> /dev/null; then
    CLAUDE_PATH=$(which claude)
    echo "✅ 找到Claude CLI: $CLAUDE_PATH"
elif [ -f "/usr/local/bin/claude" ]; then
    CLAUDE_PATH="/usr/local/bin/claude"
    echo "✅ 找到Claude CLI: $CLAUDE_PATH"
elif [ -f "$HOME/.claude/local/node_modules/.bin/claude" ]; then
    CLAUDE_PATH="$HOME/.claude/local/node_modules/.bin/claude"
    echo "✅ 找到Claude CLI: $CLAUDE_PATH"
else
    echo "❌ 未找到Claude CLI，请手动指定路径"
    exit 1
fi

# 4. 创建便捷脚本
echo "📝 创建便捷使用脚本..."
cat > sage_cli << 'EOF'
#!/bin/bash
export SILICONFLOW_API_KEY="sk-xtjxdvdwjfiiggwxkojmiryhcfjliywfzurbtsorwvgkimdg"
export CLAUDE_CLI_PATH="CLAUDE_PATH_PLACEHOLDER"
export SAGE_HOME="/Users/jet/sage"
cd "$SAGE_HOME"
python3 sage_mem.py "$@"
EOF

# 替换占位符
sed -i '' "s|CLAUDE_PATH_PLACEHOLDER|$CLAUDE_PATH|g" sage_cli
chmod +x sage_cli

# 5. 创建管理脚本
cat > sage_manage << 'EOF'
#!/bin/bash
export SILICONFLOW_API_KEY="sk-xtjxdvdwjfiiggwxkojmiryhcfjliywfzurbtsorwvgkimdg"
export SAGE_HOME="/Users/jet/sage"
cd "$SAGE_HOME"
python3 sage_memory_cli.py "$@"
EOF
chmod +x sage_manage

echo ""
echo "🎉 设置完成！使用方法："
echo ""
echo "1. 带记忆的Claude对话："
echo "   ./sage_cli \"你的问题\""
echo ""
echo "2. 管理记忆系统："
echo "   ./sage_manage status          # 查看状态"
echo "   ./sage_manage search \"关键词\"  # 搜索记忆"
echo "   ./sage_manage clear --force   # 清除记忆"
echo ""
echo "3. 或者设置别名到PATH中："
echo "   export PATH=\"/Users/jet/sage:\$PATH\""
echo "   echo 'alias claude=\"/Users/jet/sage/sage_cli\"' >> ~/.zshrc"
echo ""