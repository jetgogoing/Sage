#!/bin/bash
set -e # Exit immediately if a command exits with a non-zero status.
set -o pipefail # Return value of a pipeline is the value of the last command to exit with a non-zero status

# === 配置 ===
OLD_PG_CONTAINER="sage-postgres"
OLD_MCP_SERVICE_PORT="17801"
BACKUP_DIR="./backups"
LATEST_BACKUP=""
COMPOSE_FILE="docker-compose-sage.yml"
PROJECT_NAME="sage-docker"

# 从 .env 文件读取配置
if [ -f .env ]; then
    export $(cat .env | grep -v '^#' | xargs)
fi

# === 函数定义 ===

function print_section() {
    echo ""
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo "  $1"
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
}

function backup_database() {
    print_section "1. 备份现有数据库"
    
    if [ "$(docker ps -q -f name=^/${OLD_PG_CONTAINER}$)" ]; then
        mkdir -p "$BACKUP_DIR"
        local backup_file="$BACKUP_DIR/sage-db-backup-$(date +%F-%H-%M-%S).sql"
        echo "📦 正在备份数据库到: $backup_file"
        
        # 获取旧容器的数据库凭据 - 只备份 sage_memory 数据库
        docker exec "$OLD_PG_CONTAINER" pg_dump -U sage_user -d sage_memory > "$backup_file"
        
        LATEST_BACKUP="$backup_file"
        echo "✅ 备份成功: $LATEST_BACKUP"
        echo "   文件大小: $(du -h "$LATEST_BACKUP" | cut -f1)"
    else
        echo "⚠️  警告: 未找到运行中的 PostgreSQL 容器 '$OLD_PG_CONTAINER'"
        echo "   跳过数据库备份步骤"
    fi
}

function stop_old_services() {
    print_section "2. 停止旧服务"
    
    # 停止旧的 MCP 服务
    echo "🔍 检查端口 $OLD_MCP_SERVICE_PORT 上的服务..."
    OLD_MCP_PID=$(lsof -t -i:$OLD_MCP_SERVICE_PORT || true)
    
    if [ -n "$OLD_MCP_PID" ]; then
        echo "⏹️  停止 MCP 服务 (PID: $OLD_MCP_PID)..."
        kill "$OLD_MCP_PID" 2>/dev/null || true
        sleep 2
        # 强制终止（如果还在运行）
        kill -9 "$OLD_MCP_PID" 2>/dev/null || true
        echo "✅ MCP 服务已停止"
    else
        echo "ℹ️  端口 $OLD_MCP_SERVICE_PORT 上没有运行的服务"
    fi
    
    # 停止并移除旧的 PostgreSQL 容器
    if [ "$(docker ps -q -f name=^/${OLD_PG_CONTAINER}$)" ]; then
        echo "⏹️  停止容器 '$OLD_PG_CONTAINER'..."
        docker stop "$OLD_PG_CONTAINER"
        echo "🗑️  移除容器 '$OLD_PG_CONTAINER'..."
        docker rm "$OLD_PG_CONTAINER"
        echo "✅ 旧容器已停止并移除"
    else
        echo "ℹ️  容器 '$OLD_PG_CONTAINER' 未在运行"
    fi
    
    # 清理可能存在的孤立容器
    echo "🧹 清理可能的孤立容器..."
    docker container prune -f
}

function build_and_start() {
    print_section "3. 构建并启动新的 Docker 栈"
    
    echo "🏗️  构建 Docker 镜像..."
    docker-compose -f "$COMPOSE_FILE" -p "$PROJECT_NAME" build
    
    echo "🚀 启动服务..."
    docker-compose -f "$COMPOSE_FILE" -p "$PROJECT_NAME" up -d
    
    echo "⏳ 等待数据库健康检查通过..."
    local max_attempts=30
    local attempt=0
    
    while [ $attempt -lt $max_attempts ]; do
        if [ "$(docker inspect --format='{{.State.Health.Status}}' sage-docker-db 2>/dev/null)" = "healthy" ]; then
            echo ""
            echo "✅ 数据库已就绪"
            break
        fi
        echo -n "."
        sleep 2
        ((attempt++))
    done
    
    if [ $attempt -eq $max_attempts ]; then
        echo ""
        echo "❌ 数据库健康检查超时"
        exit 1
    fi
    
    # 等待应用启动
    echo "⏳ 等待应用启动..."
    sleep 5
    
    # 检查应用健康状态
    if curl -s http://localhost:17800/health > /dev/null; then
        echo "✅ 应用已成功启动"
    else
        echo "⚠️  应用可能还在启动中..."
    fi
}

function restore_database() {
    print_section "4. 恢复数据库"
    
    if [ -f "$LATEST_BACKUP" ]; then
        echo "📥 恢复数据从: $LATEST_BACKUP"
        
        # 首先创建数据库和扩展
        echo "🔧 准备数据库..."
        docker exec sage-docker-db psql -U "$POSTGRES_USER" -c "CREATE DATABASE IF NOT EXISTS $POSTGRES_DB;"
        docker exec sage-docker-db psql -U "$POSTGRES_USER" -d "$POSTGRES_DB" -c "CREATE EXTENSION IF NOT EXISTS vector;"
        
        # 恢复数据
        echo "📝 恢复数据..."
        cat "$LATEST_BACKUP" | docker exec -i sage-docker-db psql -U "$POSTGRES_USER" 2>&1 | grep -v "already exists" || true
        
        echo "✅ 数据恢复完成"
    else
        echo "ℹ️  没有找到备份文件，将使用全新数据库"
        
        # 创建必要的扩展
        echo "🔧 初始化新数据库..."
        docker exec sage-docker-db psql -U "$POSTGRES_USER" -d "$POSTGRES_DB" -c "CREATE EXTENSION IF NOT EXISTS vector;"
        echo "✅ 数据库初始化完成"
    fi
}

function show_status() {
    print_section "5. 部署状态"
    
    echo "📊 容器状态:"
    docker-compose -f "$COMPOSE_FILE" -p "$PROJECT_NAME" ps
    
    echo ""
    echo "🔗 服务访问地址:"
    echo "   - MCP 服务: http://localhost:17800/mcp"
    echo "   - 健康检查: http://localhost:17800/health"
    echo "   - 数据库: localhost:5433 (用户: $POSTGRES_USER)"
    
    echo ""
    echo "📝 日志查看命令:"
    echo "   - 应用日志: docker logs -f sage-docker-app"
    echo "   - 数据库日志: docker logs -f sage-docker-db"
    
    echo ""
    echo "🛠️  管理命令:"
    echo "   - 停止服务: docker-compose -f $COMPOSE_FILE -p $PROJECT_NAME down"
    echo "   - 重启服务: docker-compose -f $COMPOSE_FILE -p $PROJECT_NAME restart"
    echo "   - 查看日志: docker-compose -f $COMPOSE_FILE -p $PROJECT_NAME logs -f"
}

function create_rollback_script() {
    cat > rollback-sage-docker.sh << 'EOF'
#!/bin/bash
# Sage Docker 回滚脚本

echo "⚠️  准备回滚到旧环境..."

# 停止新的 Docker 栈
docker-compose -f docker-compose-sage.yml -p sage-docker down

# 重新启动旧的 PostgreSQL 容器
echo "启动旧的 PostgreSQL 容器..."
docker run -d \
    --name sage-postgres \
    -e POSTGRES_USER=sage_user \
    -e POSTGRES_PASSWORD=sage_password \
    -e POSTGRES_DB=sage_memory \
    -p 5432:5432 \
    pgvector/pgvector:pg16

echo "✅ 回滚完成"
echo "请手动重启旧的 MCP 服务"
EOF
    
    chmod +x rollback-sage-docker.sh
    echo "ℹ️  已创建回滚脚本: ./rollback-sage-docker.sh"
}

# === 主程序执行 ===

echo "🚀 Sage Docker 部署脚本"
echo "========================"
echo "配置文件: $COMPOSE_FILE"
echo "项目名称: $PROJECT_NAME"
echo ""

# 检查必要文件
if [ ! -f .env ]; then
    echo "❌ 错误: 未找到 .env 文件"
    echo "   请先创建 .env 文件"
    exit 1
fi

if [ ! -f "$COMPOSE_FILE" ]; then
    echo "❌ 错误: 未找到 $COMPOSE_FILE 文件"
    exit 1
fi

# 设置错误处理
trap 'echo ""; echo "❌ 发生错误，正在清理..."; docker-compose -f "$COMPOSE_FILE" -p "$PROJECT_NAME" down -v; exit 1' ERR

# 执行部署流程
backup_database
stop_old_services
build_and_start
restore_database
show_status
create_rollback_script

print_section "✅ 部署完成！"

echo "下一步操作:"
echo "1. 测试 MCP 连接: curl http://localhost:17800/health"
echo "2. 在 Claude Code 中注册:"
echo "   claude mcp remove sage"
echo "   claude mcp add sage http://localhost:17800/mcp"
echo ""
echo "如需回滚，请运行: ./rollback-sage-docker.sh"