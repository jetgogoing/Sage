#!/bin/bash
# 调试版本的启动脚本 - 显示详细信息

set -e  # 遇到错误立即退出
set -x  # 显示执行的每个命令

echo "=== Sage MCP Debug Entrypoint ==="
echo "Current user: $(whoami)"
echo "Current directory: $(pwd)"
echo "Environment variables:"
env | grep -E "SAGE|DB_|PGDATA|SILICONFLOW" | sort

# 检查必要的目录
echo ""
echo "Checking directories..."
ls -la /var/lib/postgresql/ || echo "PostgreSQL data dir not found"
ls -la /var/run/ || echo "Run dir not found"
ls -la /app/ || echo "App dir not found"

# 修复权限
echo ""
echo "Fixing permissions..."
chown -R postgres:postgres /var/lib/postgresql || echo "Failed to chown postgresql"
chown -R postgres:postgres /var/run/postgresql || echo "Failed to chown run/postgresql"
mkdir -p /var/run/postgresql || echo "Failed to create run/postgresql"
chmod 755 /var/run/postgresql

# 检查 PostgreSQL 安装
echo ""
echo "PostgreSQL installation check:"
which postgres || echo "postgres binary not found"
which pg_ctl || echo "pg_ctl not found"
ls -la /usr/lib/postgresql/ || echo "PostgreSQL lib dir not found"

# 尝试初始化数据库
echo ""
echo "Initializing PostgreSQL data..."
export PGDATA=/var/lib/postgresql/data

if [ ! -d "$PGDATA/base" ]; then
    echo "Running initdb..."
    su - postgres -c "/usr/lib/postgresql/15/bin/initdb -D $PGDATA" || {
        echo "initdb failed!"
        exit 1
    }
else
    echo "Database already initialized"
fi

# 尝试启动 PostgreSQL
echo ""
echo "Starting PostgreSQL..."
su - postgres -c "/usr/lib/postgresql/15/bin/pg_ctl -D $PGDATA -l /tmp/postgresql.log start" || {
    echo "PostgreSQL start failed!"
    echo "Log contents:"
    cat /tmp/postgresql.log
    exit 1
}

# 等待 PostgreSQL 启动
echo ""
echo "Waiting for PostgreSQL..."
for i in {1..30}; do
    if pg_isready -h localhost -p 5432; then
        echo "PostgreSQL is ready!"
        break
    fi
    echo "Waiting... $i/30"
    sleep 1
done

# 检查 Python 环境
echo ""
echo "Python environment check:"
python3 --version
pip3 --version
echo "PYTHONPATH: $PYTHONPATH"

# 列出已安装的 Python 包
echo ""
echo "Installed Python packages:"
pip3 list | grep -E "mcp|numpy|asyncpg|pgvector|requests"

# 检查应用文件
echo ""
echo "Application files:"
ls -la /app/

# 尝试导入核心模块
echo ""
echo "Testing Python imports..."
python3 -c "import sys; print('Python path:', sys.path)"
python3 -c "import sage_core; print('sage_core OK')" || echo "Failed to import sage_core"
python3 -c "import memory; print('memory OK')" || echo "Failed to import memory"
python3 -c "from mcp.server import Server; print('mcp OK')" || echo "Failed to import mcp"

# 如果一切正常，启动应用
echo ""
echo "Starting application..."
cd /app
python3 sage_mcp_stdio_v3.py || {
    echo "Application failed to start!"
    exit 1
}