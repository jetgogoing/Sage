#!/bin/bash
# Sage 记忆系统服务停止脚本
# 🛑 安全停止所有服务

echo "🛑 Sage 记忆系统服务停止"
echo "================================="

# 进入项目目录
PROJECT_DIR="/Volumes/1T HDD/Sage"
cd "$PROJECT_DIR"

echo "📂 当前目录: $(pwd)"

# 1. 停止 Docker Compose 服务
echo ""
echo "--- 停止数据库服务 ---"
if [ -f docker-compose.yml ]; then
    echo "🔄 停止 PostgreSQL 容器..."
    docker compose down
    echo "✅ 数据库服务已停止"
else
    echo "⚠️  未找到 docker-compose.yml 文件"
fi

# 2. 检查并停止可能的后台 Python 进程
echo ""
echo "--- 检查后台进程 ---"
PYTHON_PROCESSES=$(ps aux | grep -E "(sage_mem\.py|claude_mem.*\.py)" | grep -v grep | awk '{print $2}' || true)

if [ -n "$PYTHON_PROCESSES" ]; then
    echo "🔄 发现相关 Python 进程，正在停止..."
    echo "$PYTHON_PROCESSES" | xargs -r kill
    echo "✅ Python 进程已停止"
else
    echo "ℹ️  未发现运行中的相关 Python 进程"
fi

# 3. 清理临时文件
echo ""
echo "--- 清理临时文件 ---"
if [ -f app.log ]; then
    echo "🗑️  清理应用日志文件..."
    > app.log  # 清空而不删除
    echo "✅ 日志文件已清空"
fi

if [ -f nohup.out ]; then
    echo "🗑️  清理 nohup 输出文件..."
    rm -f nohup.out
    echo "✅ nohup 文件已删除"
fi

# 4. 显示最终状态
echo ""
echo "--- 最终状态检查 ---"
echo "📊 Docker 容器状态:"
docker compose ps 2>/dev/null || echo "ℹ️  无运行中的容器"

echo ""
echo "🎉 Sage 记忆系统已完全停止！"
echo "================================="
echo ""
echo "📋 重新启动请使用:"
echo "  ./start_all_services.sh"
echo ""