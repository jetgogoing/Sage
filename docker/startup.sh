#!/bin/bash
set -euo pipefail

# 导入环境变量默认值
export PGDATA="${PGDATA:-/var/lib/postgresql/data}"
export DB_USER="${DB_USER:-sage}"
export DB_PASSWORD="${DB_PASSWORD:-sage123}"
export DB_NAME="${DB_NAME:-sage_memory}"
export POSTGRES_PASSWORD="${POSTGRES_PASSWORD:-sage123}"

echo "[STARTUP] Sage MCP Server starting..."
echo "[STARTUP] Environment: SAGE_ENV=${SAGE_ENV:-production}, LOG_LEVEL=${SAGE_LOG_LEVEL:-INFO}"

# 错误处理函数
error_exit() {
    echo "[ERROR] $1" >&2
    exit 1
}

# 初始化 PostgreSQL
init_postgresql() {
    # 确保数据目录存在并设置正确权限
    mkdir -p "$PGDATA"
    chown -R postgres:postgres "$PGDATA"
    chmod 700 "$PGDATA"
    
    if [ ! -f "$PGDATA/postgresql.conf" ]; then
        echo "[STARTUP] Initializing PostgreSQL at $PGDATA..."
        
        # 初始化数据库
        su - postgres -c "/usr/lib/postgresql/15/bin/initdb -D $PGDATA" || error_exit "Failed to initialize PostgreSQL"
        
        # 配置 PostgreSQL
        echo "host    all             all             127.0.0.1/32            md5" >> "$PGDATA/pg_hba.conf"
        echo "local   all             all                                     md5" >> "$PGDATA/pg_hba.conf"
        echo "host    all             all             ::1/128                 md5" >> "$PGDATA/pg_hba.conf"
        echo "listen_addresses = '*'" >> "$PGDATA/postgresql.conf"
        echo "port = 5432" >> "$PGDATA/postgresql.conf"
        
        echo "[STARTUP] PostgreSQL initialized successfully"
    else
        echo "[STARTUP] PostgreSQL data directory already exists, skipping initialization"
    fi
}

# 启动服务
start_services() {
    echo "[STARTUP] Starting Supervisor..."
    /usr/bin/supervisord -c /etc/supervisor/conf.d/supervisord.conf -n &
    SUPERVISOR_PID=$!
    
    # 等待 PostgreSQL 就绪
    echo "[STARTUP] Waiting for PostgreSQL to be ready..."
    local max_attempts=30
    local attempt=1
    
    while [ $attempt -le $max_attempts ]; do
        if su - postgres -c "pg_isready -q -h localhost -p 5432"; then
            echo "[STARTUP] PostgreSQL is ready (attempt $attempt)"
            break
        fi
        echo "[STARTUP] Attempt $attempt/$max_attempts: PostgreSQL not ready, waiting..."
        sleep 2
        attempt=$((attempt + 1))
    done
    
    if [ $attempt -gt $max_attempts ]; then
        error_exit "PostgreSQL failed to start after $max_attempts attempts"
    fi
}

# 设置数据库
setup_database() {
    echo "[STARTUP] Setting up database and user..."
    
    # 设置 postgres 用户密码
    su - postgres -c "psql -c \"ALTER USER postgres PASSWORD '$POSTGRES_PASSWORD';\""
    
    # 创建数据库和用户
    su - postgres -c "psql -tc \"SELECT 1 FROM pg_database WHERE datname = '$DB_NAME'\" | grep -q 1 || createdb $DB_NAME" || error_exit "Failed to create database"
    su - postgres -c "psql -tc \"SELECT 1 FROM pg_user WHERE usename = '$DB_USER'\" | grep -q 1 || createuser $DB_USER" || error_exit "Failed to create user"
    su - postgres -c "psql -c \"ALTER USER $DB_USER PASSWORD '$DB_PASSWORD';\"" || error_exit "Failed to set user password"
    su - postgres -c "psql -c \"GRANT ALL PRIVILEGES ON DATABASE $DB_NAME TO $DB_USER;\"" || error_exit "Failed to grant privileges"
    
    # 运行初始化 SQL
    if [ -f /docker-entrypoint-initdb.d/init.sql ]; then
        echo "[STARTUP] Running initialization SQL..."
        su - postgres -c "psql -d $DB_NAME -f /docker-entrypoint-initdb.d/init.sql" || error_exit "Failed to run initialization SQL"
    fi
    
    echo "[STARTUP] Database setup completed"
}

# 启动 MCP 服务
start_mcp_service() {
    echo "[STARTUP] Starting MCP STDIO service..."
    
    # 验证 sage_core 模块
    cd /app
    python3 -c "import sage_core; print('✓ sage_core module loaded successfully')" || error_exit "Failed to load sage_core module"
    
    # 确保sage用户对可写目录有权限（避免修改只读挂载卷）
    mkdir -p /var/log/sage
    mkdir -p /app/data
    mkdir -p /app/tmp
    
    # 只对可写目录设置权限，避免修改挂载的配置目录
    chown -R sage:sage /var/log/sage 2>/dev/null || true
    chown -R sage:sage /app/data 2>/dev/null || true
    chown -R sage:sage /app/tmp 2>/dev/null || true
    
    # 确保sage用户对核心应用文件有读取权限（但不修改配置目录）
    find /app -maxdepth 1 -name "*.py" -exec chown sage:sage {} \; 2>/dev/null || true
    
    # 启动 MCP 服务
    supervisorctl start sage-mcp || error_exit "Failed to start MCP service"
    
    echo "[STARTUP] MCP service started successfully"
}

# 信号处理
cleanup() {
    echo "[SHUTDOWN] Received shutdown signal, stopping services..."
    supervisorctl stop all
    kill $SUPERVISOR_PID 2>/dev/null || true
    exit 0
}

trap cleanup SIGTERM SIGINT

# 主启动流程
main() {
    init_postgresql
    start_services
    setup_database
    start_mcp_service
    
    echo "[STARTUP] All services started successfully"
    echo "[STARTUP] Container ready to accept MCP connections"
    
    # 保持容器运行
    wait $SUPERVISOR_PID
}

# 执行主流程
main "$@"