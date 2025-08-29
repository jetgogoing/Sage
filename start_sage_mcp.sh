#!/bin/bash
# Sage MCP Startup Script - Enhanced for Cross-Project Support
# This script ensures pgvector database is running and starts Sage MCP service

# 动态检测项目根目录，支持跨平台部署
SAGE_HOME="$(cd "$(dirname "$0")" && pwd)"
DB_COMPOSE_FILE="${SAGE_HOME}/docker-compose-db.yml"
SAGE_LOGS="${SAGE_HOME}/logs"

# Create logs directory if it doesn't exist
mkdir -p "${SAGE_LOGS}"

# Check if Docker is running
if ! docker info > /dev/null 2>&1; then
    echo "Docker is not running. Please start Docker Desktop first." >&2
    exit 1
fi

# Check if PostgreSQL container exists (running or stopped)
if ! docker ps -a | grep -q "sage-db"; then
    echo "Creating PostgreSQL container with pgvector..." >&2
    cd "${SAGE_HOME}" && docker-compose -f "${DB_COMPOSE_FILE}" up -d
    sleep 5  # Give it time to initialize
elif ! docker ps | grep -q "sage-db.*Up"; then
    echo "Starting existing PostgreSQL container..." >&2
    docker start sage-db >/dev/null 2>&1
    sleep 3  # Give it time to start
fi

# Wait for PostgreSQL to be ready
echo "Checking PostgreSQL readiness..." >&2
for i in {1..30}; do
    if docker exec sage-db pg_isready -U sage -d sage_memory >/dev/null 2>&1; then
        echo "PostgreSQL is ready!" >&2
        break
    fi
    if [ $i -eq 30 ]; then
        echo "PostgreSQL failed to start within 30 seconds" >&2
        exit 1
    fi
    sleep 1
done

# Export environment variables (可以从.env文件或环境变量覆盖)
export SAGE_LOG_DIR="${SAGE_LOGS}"
export DB_HOST="${DB_HOST:-localhost}"
export DB_PORT="${DB_PORT:-5432}"
export DB_NAME="${DB_NAME:-sage_memory}"
export DB_USER="${DB_USER:-sage}"
export DB_PASSWORD="${DB_PASSWORD:-}"
export EMBEDDING_MODEL="Qwen/Qwen3-Embedding-8B"
export EMBEDDING_DEVICE="cpu"
# API密钥从环境变量或.env文件加载，移除明文密钥以提高安全性
export SILICONFLOW_API_KEY="${SILICONFLOW_API_KEY:-}"
export PYTHONPATH="${SAGE_HOME}"

# Load additional config from .env if exists
if [ -f "${SAGE_HOME}/.env" ]; then
    # 安全地加载.env文件，支持所有必需变量
    while IFS='=' read -r key value; do
        # 跳过注释和空行
        [[ $key =~ ^[[:space:]]*# ]] && continue
        [[ -z $key ]] && continue
        
        # 移除引号和首尾空格
        key=$(echo "$key" | xargs)
        value=$(echo "$value" | xargs | sed 's/^["'\'']//' | sed 's/["'\'']*$//')
        
        case "$key" in
            SAGE_MAX_RESULTS|SAGE_SIMILARITY_THRESHOLD|SILICONFLOW_API_KEY|DB_PASSWORD)
                export "$key"="$value"
                ;;
        esac
    done < "${SAGE_HOME}/.env"
fi

# 使用当前Python解释器或项目虚拟环境
PYTHON_EXE="${SAGE_HOME}/.venv/bin/python"
if [ ! -f "$PYTHON_EXE" ]; then
    PYTHON_EXE="python3"
fi

exec "$PYTHON_EXE" "${SAGE_HOME}/sage_mcp_stdio_single.py"