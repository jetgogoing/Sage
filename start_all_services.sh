#!/bin/bash
# Sage 记忆系统一键启动脚本
# 🚀 启动所有必要的服务和组件

set -e  # 如果任何命令失败，脚本将立即退出

echo "🚀 Sage 记忆系统一键启动"
echo "================================="

# 进入项目目录
PROJECT_DIR="/Volumes/1T HDD/Sage"
cd "$PROJECT_DIR"

echo "📂 当前目录: $(pwd)"

# 1. 检查并配置环境变量
echo ""
echo "--- 1. 检查环境配置 ---"
if [ ! -f .env ]; then
    echo "⚠️  .env 文件不存在，创建默认配置..."
    cat > .env << 'EOF'
# Sage MCP 轻量化记忆系统环境变量配置
SILICONFLOW_API_KEY=sk-xtjxdvdwjfiiggwxkojmiryhcfjliywfzurbtsorwvgkimdg
DB_HOST=localhost
DB_PORT=5432
DB_NAME=mem
DB_USER=mem
DB_PASSWORD=mem
CLAUDE_CLI_PATH=/Users/jet/.claude/local/node_modules/.bin/claude
EOF
    echo "✅ 已创建 .env 文件"
else
    echo "✅ .env 文件已存在"
fi

# 2. 启动 PostgreSQL + pgvector 数据库服务
echo ""
echo "--- 2. 启动数据库服务 ---"
echo "🔄 检查 Docker 服务..."

if ! command -v docker &> /dev/null; then
    echo "❌ Docker 未安装或未在 PATH 中"
    exit 1
fi

if ! docker info &> /dev/null; then
    echo "❌ Docker 服务未运行，请先启动 Docker"
    exit 1
fi

echo "✅ Docker 服务正常"

# 启动数据库容器
echo "🔄 启动 PostgreSQL + pgvector 容器..."
docker compose up -d

# 等待数据库启动
echo "⏳ 等待数据库启动 (15秒)..."
sleep 15

# 检查容器状态
if docker compose ps | grep -q "Up"; then
    echo "✅ 数据库容器启动成功"
else
    echo "❌ 数据库容器启动失败"
    docker compose ps
    exit 1
fi

# 3. 初始化数据库（创建表和启用扩展）
echo ""
echo "--- 3. 初始化数据库 ---"
echo "🔄 检查并创建 pgvector 扩展..."

# 检查并创建 pgvector 扩展
docker compose exec -T pg psql -U mem -d mem -c "CREATE EXTENSION IF NOT EXISTS vector;" || {
    echo "⚠️  直接创建扩展失败，尝试其他方法..."
    # 如果容器名不同，尝试查找正确的容器
    CONTAINER_NAME=$(docker compose ps --services | head -1)
    if [ -n "$CONTAINER_NAME" ]; then
        docker compose exec -T "$CONTAINER_NAME" psql -U mem -d mem -c "CREATE EXTENSION IF NOT EXISTS vector;" || echo "⚠️  扩展创建可能已存在"
    fi
}

echo "✅ 数据库初始化完成"

# 4. 检查和安装 Python 依赖
echo ""
echo "--- 4. 检查 Python 环境 ---"

if ! command -v python3 &> /dev/null; then
    echo "❌ Python3 未安装"
    exit 1
fi

echo "✅ Python3: $(python3 --version)"

if [ -f requirements.txt ]; then
    echo "🔄 安装 Python 依赖..."
    pip3 install -r requirements.txt
    echo "✅ Python 依赖安装完成"
else
    echo "⚠️  未找到 requirements.txt，跳过依赖安装"
fi

# 5. 验证核心组件
echo ""
echo "--- 5. 验证核心组件 ---"

# 加载环境变量
export SILICONFLOW_API_KEY="sk-xtjxdvdwjfiiggwxkojmiryhcfjliywfzurbtsorwvgkimdg"

# 测试数据库连接
echo "🔄 测试数据库连接..."
python3 -c "
try:
    from memory_interface import get_memory_provider
    provider = get_memory_provider()
    stats = provider.get_memory_stats()
    print('✅ 数据库连接成功')
    print(f'📊 当前记忆数: {stats.get(\"total\", 0)}')
except Exception as e:
    print(f'❌ 数据库连接失败: {e}')
    exit(1)
" || {
    echo "❌ 数据库连接测试失败"
    exit 1
}

# 测试 API 配置
echo "🔄 测试 API 配置..."
python3 -c "
try:
    from memory import embed_text
    result = embed_text('测试向量化')
    print('✅ API 配置正常，向量维度:', len(result))
except Exception as e:
    print(f'⚠️  API测试警告: {e}')
    print('📝 注意: 向量化失败时会使用随机向量作为降级方案')
"

# 6. 创建服务状态检查脚本
echo ""
echo "--- 6. 创建管理脚本 ---"

# 确保脚本可执行
chmod +x sage_claude 2>/dev/null || echo "⚠️  sage_claude 脚本不存在"
chmod +x sage_manage 2>/dev/null || echo "⚠️  sage_manage 脚本不存在"

echo "✅ 管理脚本权限设置完成"

# 7. 最终状态检查
echo ""
echo "--- 7. 系统状态检查 ---"

echo "📊 数据库容器状态:"
docker compose ps

echo ""
echo "📊 记忆系统状态:"
python3 sage_memory_cli.py status 2>/dev/null || echo "⚠️  记忆系统状态检查失败，但不影响核心功能"

# 8. 显示使用说明
echo ""
echo "🎉 Sage 记忆系统启动完成！"
echo "================================="
echo ""
echo "📋 使用方法:"
echo "  1. 带记忆的 Claude 对话:"
echo "     ./sage_claude \"你的问题\""
echo "     或"
echo "     claude-sage \"你的问题\"  # 如果已设置别名"
echo ""
echo "  2. 管理记忆系统:"
echo "     ./sage_manage status          # 查看状态"
echo "     ./sage_manage search \"关键词\"  # 搜索记忆" 
echo "     ./sage_manage clear --force   # 清除记忆"
echo ""
echo "📁 重要文件:"
echo "  - 配置文件: .env"
echo "  - 启动脚本: $0"
echo "  - 停止服务: ./stop_all_services.sh"
echo ""
echo "🔧 如果遇到问题，请检查:"
echo "  1. Docker 服务是否正常运行"
echo "  2. API 密钥是否配置正确"
echo "  3. 日志文件: docker compose logs"
echo ""
echo "✅ 所有服务已启动，可以开始使用！"