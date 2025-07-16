#!/bin/bash
set -e

echo "=== Sage MCP Ubuntu Edition Starting ==="
echo "Time: $(date)"
echo "Environment: Production with Cloud API"

# 函数：等待 PostgreSQL 启动
wait_for_postgres() {
    echo "Waiting for PostgreSQL to start..."
    for i in {1..30}; do
        if pg_isready -h localhost -p 5432 -U postgres > /dev/null 2>&1; then
            echo "✓ PostgreSQL is ready!"
            return 0
        fi
        echo "  Waiting... ($i/30)"
        sleep 1
    done
    echo "✗ PostgreSQL failed to start!"
    return 1
}

# 函数：初始化数据库
init_database() {
    echo "Checking database initialization..."
    
    if [ -f "/var/lib/postgresql/data/.initialized" ]; then
        echo "✓ Database already initialized"
        return 0
    fi
    
    echo "Initializing database..."
    
    # 创建用户和数据库
    su - postgres -c "psql -c \"CREATE USER sage WITH PASSWORD 'sage';\""
    su - postgres -c "psql -c \"CREATE DATABASE sage OWNER sage;\""
    
    # 运行初始化脚本
    su - postgres -c "psql -d sage -f /docker-entrypoint-initdb.d/init-db.sql"
    
    # 标记为已初始化
    touch /var/lib/postgresql/data/.initialized
    echo "✓ Database initialized successfully"
}

# 1. 修复权限
echo "Setting up permissions..."
chown -R postgres:postgres /var/lib/postgresql
chown -R postgres:postgres /var/run/postgresql
chmod 755 /var/run/postgresql

# 2. 初始化 PostgreSQL 数据目录（如果需要）
if [ ! -d "/var/lib/postgresql/data/base" ]; then
    echo "Initializing PostgreSQL data directory..."
    su - postgres -c "/usr/lib/postgresql/15/bin/initdb -D /var/lib/postgresql/data"
fi

# 3. 启动 PostgreSQL
echo "Starting PostgreSQL 15..."
su - postgres -c "/usr/lib/postgresql/15/bin/pg_ctl -D /var/lib/postgresql/data -l /var/log/sage/postgresql.log start"

# 4. 等待 PostgreSQL 启动
wait_for_postgres || exit 1

# 5. 初始化数据库
init_database

# 6. 验证数据库连接
echo "Verifying database connection..."
PGPASSWORD=sage psql -h localhost -U sage -d sage -c "SELECT version();" || {
    echo "✗ Failed to connect to database!"
    exit 1
}

# 7. 检查 pgvector 扩展
echo "Checking pgvector extension..."
PGPASSWORD=sage psql -h localhost -U sage -d sage -c "SELECT * FROM pg_extension WHERE extname = 'vector';" || {
    echo "Creating pgvector extension..."
    PGPASSWORD=sage psql -h localhost -U sage -d sage -c "CREATE EXTENSION IF NOT EXISTS vector;"
}

# 8. 设置环境变量
export PYTHONPATH=/app:$PYTHONPATH
export DB_HOST=localhost
export DB_PORT=5432
export DB_NAME=sage
export DB_USER=sage
export DB_PASSWORD=sage

# 9. 检查 API 密钥
if [ -z "$SILICONFLOW_API_KEY" ]; then
    echo "⚠️  WARNING: SILICONFLOW_API_KEY not set!"
    echo "  The system will use hash-based vectorization as fallback."
    echo "  For full functionality, please set SILICONFLOW_API_KEY environment variable."
fi

# 10. 显示系统信息
echo ""
echo "=== System Information ==="
echo "PostgreSQL: $(su - postgres -c '/usr/lib/postgresql/15/bin/postgres --version')"
echo "Python: $(python3 --version)"
echo "MCP SDK: $(pip3 show mcp | grep Version)"
echo "Working Directory: $(pwd)"
echo "PYTHONPATH: $PYTHONPATH"
echo ""

# 11. 启动 Sage MCP STDIO 服务
echo "Starting Sage MCP STDIO Server v3..."
echo "Mode: Anthropic MCP Protocol over STDIO"
echo "========================================"
echo ""

# 切换到应用目录
cd /app

# 使用 exec 确保信号正确传递
exec python3 sage_mcp_stdio_v3.py