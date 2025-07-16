#!/bin/bash
set -e

echo "=== Sage MCP Single Container Starting ==="
echo "Time: $(date)"

# 设置 PostgreSQL 数据目录
export PGDATA="${PGDATA:-/var/lib/postgresql/data}"

# 修复权限
echo "Setting up permissions..."
mkdir -p "$PGDATA" /var/run/postgresql /var/log/sage
chown -R postgres:postgres "$PGDATA" /var/run/postgresql
chown -R sage:sage /var/log/sage /app 2>/dev/null || true
chmod 755 /var/run/postgresql

# 检查并初始化 PostgreSQL 数据目录
if [ ! -f "$PGDATA/PG_VERSION" ]; then
    echo "Initializing PostgreSQL database..."
    su - postgres -c "/usr/lib/postgresql/15/bin/initdb -D $PGDATA --encoding=UTF8 --locale=C"
    echo "Database initialization complete."
else
    echo "PostgreSQL data directory already exists."
fi

# 配置 PostgreSQL（如果需要）
if [ ! -f "$PGDATA/.configured" ]; then
    echo "Configuring PostgreSQL..."
    
    # 修改 postgresql.conf
    echo "listen_addresses = '*'" >> "$PGDATA/postgresql.conf"
    echo "max_connections = 100" >> "$PGDATA/postgresql.conf"
    echo "shared_buffers = 128MB" >> "$PGDATA/postgresql.conf"
    
    # 修改 pg_hba.conf 允许本地连接
    echo "# Allow local connections" >> "$PGDATA/pg_hba.conf"
    echo "local   all             all                                     trust" >> "$PGDATA/pg_hba.conf"
    echo "host    all             all             127.0.0.1/32            trust" >> "$PGDATA/pg_hba.conf"
    echo "host    all             all             ::1/128                 trust" >> "$PGDATA/pg_hba.conf"
    
    touch "$PGDATA/.configured"
    echo "PostgreSQL configuration complete."
fi

# 启动 PostgreSQL
echo "Starting PostgreSQL..."
su - postgres -c "/usr/lib/postgresql/15/bin/pg_ctl -D $PGDATA -l /var/log/sage/postgresql.log start"

# 等待 PostgreSQL 启动
echo "Waiting for PostgreSQL to start..."
for i in {1..30}; do
    if pg_isready -h localhost -p 5432 -U postgres > /dev/null 2>&1; then
        echo "PostgreSQL is ready!"
        break
    fi
    echo "  Waiting... ($i/30)"
    sleep 1
done

# 确保 PostgreSQL 真的准备好了
sleep 2

# 初始化数据库和用户（如果需要）
if [ ! -f "$PGDATA/.sage_initialized" ]; then
    echo "Creating Sage database and user..."
    
    su - postgres -c "psql -c \"CREATE USER sage WITH PASSWORD 'sage';\"" || true
    su - postgres -c "psql -c \"CREATE DATABASE sage OWNER sage;\"" || true
    su - postgres -c "psql -c \"GRANT ALL PRIVILEGES ON DATABASE sage TO sage;\"" || true
    
    # 创建 pgvector 扩展
    su - postgres -c "psql -d sage -c \"CREATE EXTENSION IF NOT EXISTS vector;\"" || true
    
    # 运行初始化 SQL（如果存在）
    if [ -f "/docker-entrypoint-initdb.d/init-db.sql" ]; then
        echo "Running initialization SQL..."
        su - postgres -c "PGPASSWORD=sage psql -h localhost -U sage -d sage -f /docker-entrypoint-initdb.d/init-db.sql"
    fi
    
    touch "$PGDATA/.sage_initialized"
    echo "Database initialization complete."
fi

# 验证数据库连接
echo "Verifying database connection..."
PGPASSWORD=sage psql -h localhost -U sage -d sage -c "SELECT 1;" || {
    echo "ERROR: Failed to connect to database!"
    echo "PostgreSQL log:"
    tail -20 /var/log/sage/postgresql.log
    exit 1
}

# 检查 pgvector
echo "Checking pgvector extension..."
PGPASSWORD=sage psql -h localhost -U sage -d sage -c "SELECT extname, extversion FROM pg_extension WHERE extname = 'vector';"

# 设置 Python 环境
export PYTHONPATH=/app:$PYTHONPATH

# 检查环境
echo ""
echo "=== Environment Check ==="
echo "PostgreSQL: OK"
echo "Python: $(python3 --version)"
echo "PYTHONPATH: $PYTHONPATH"
echo "SILICONFLOW_API_KEY: ${SILICONFLOW_API_KEY:+SET}"
echo ""

# 启动 Sage MCP
echo "Starting Sage MCP STDIO Server..."
cd /app

# 如果是交互式模式，启动 bash
if [ "$1" = "bash" ]; then
    exec /bin/bash
fi

# 否则启动 MCP 服务器
exec python3 sage_mcp_stdio_v3.py