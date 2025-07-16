#!/bin/bash

echo "Testing MCP STDIO service..."

# 清理旧容器
docker rm -f sage-mcp-debug 2>/dev/null

# 启动容器但保持运行
docker run -d --name sage-mcp-debug \
    -e POSTGRES_PASSWORD=sage \
    -e SILICONFLOW_API_KEY=$SILICONFLOW_API_KEY \
    sage-mcp-single:latest \
    tail -f /dev/null

echo "Waiting for PostgreSQL to start..."
sleep 10

echo "Starting PostgreSQL manually..."
docker exec sage-mcp-debug su - postgres -c "/usr/lib/postgresql/15/bin/pg_ctl -D /var/lib/postgresql/data start"
sleep 5

echo "Creating database..."
docker exec sage-mcp-debug su - postgres -c "createdb sage_memory"
docker exec sage-mcp-debug su - postgres -c "psql -d sage_memory -c 'CREATE EXTENSION IF NOT EXISTS vector;'"

echo "Running init SQL..."
docker exec sage-mcp-debug su - postgres -c "psql -d sage_memory -f /docker-entrypoint-initdb.d/init.sql"

echo "Testing MCP service directly..."
docker exec -it sage-mcp-debug bash -c '
export DB_HOST="localhost"
export DB_PORT="5432"
export DB_NAME="sage_memory"
export DB_USER="sage"
export DB_PASSWORD="sage"
export SAGE_LOG_LEVEL="DEBUG"
cd /app
echo "Starting MCP service..."
python3 sage_mcp_stdio_single.py
'