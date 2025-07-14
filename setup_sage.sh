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

# 3. 创建管理脚本
echo "📝 创建管理脚本..."
if [ ! -f sage_manage ]; then
    cat > sage_manage << 'EOF'
#!/bin/bash
export SILICONFLOW_API_KEY="sk-xtjxdvdwjfiiggwxkojmiryhcfjliywfzurbtsorwvgkimdg"
export SAGE_HOME="/Users/jet/sage"
cd "$SAGE_HOME"
python3 sage_memory_cli.py "$@"
EOF
    chmod +x sage_manage
fi

echo ""
echo "🎉 设置完成！使用方法："
echo ""
echo "1. MCP服务已经准备就绪，可在Claude Code中使用"
echo ""
echo "2. 管理记忆系统："
echo "   ./sage_manage status          # 查看状态"
echo "   ./sage_manage search \"关键词\"  # 搜索记忆"
echo "   ./sage_manage clear --force   # 清除记忆"
echo ""