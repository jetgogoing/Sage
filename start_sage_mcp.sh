#!/bin/bash
# Sage MCP Startup Script - Enhanced for Cross-Project Support
# This script ensures pgvector database is running and starts Sage MCP service

# Fixed absolute paths for cross-project usage
SAGE_HOME="/Users/jet/Sage"
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
    docker start sage-db
    sleep 3  # Give it time to start
fi

# Wait for PostgreSQL to be ready
echo "Checking PostgreSQL readiness..." >&2
for i in {1..30}; do
    if docker exec sage-db pg_isready -U sage -d sage_memory 2>/dev/null; then
        echo "PostgreSQL is ready!" >&2
        break
    fi
    if [ $i -eq 30 ]; then
        echo "PostgreSQL failed to start within 30 seconds" >&2
        exit 1
    fi
    sleep 1
done

# Export environment variables
export SAGE_LOG_DIR="${SAGE_LOGS}"
export DB_HOST="localhost"
export DB_PORT="5432"
export DB_NAME="sage_memory"
export DB_USER="sage"
export DB_PASSWORD="sage123"
export EMBEDDING_MODEL="Qwen/Qwen3-Embedding-8B"
export EMBEDDING_DEVICE="cpu"
export SILICONFLOW_API_KEY="sk-xtjxdvdwjfiiggwxkojmiryhcfjliywfzurbtsorwvgkimdg"
export PYTHONPATH="${SAGE_HOME}"

# Load additional config from .env if exists
if [ -f "${SAGE_HOME}/.env" ]; then
    export SAGE_MAX_RESULTS=$(grep SAGE_MAX_RESULTS "${SAGE_HOME}/.env" | cut -d '=' -f2)
    export SAGE_SIMILARITY_THRESHOLD=$(grep SAGE_SIMILARITY_THRESHOLD "${SAGE_HOME}/.env" | cut -d '=' -f2)
fi

# Use the zen-mcp-server virtual environment
exec /Users/jet/zen-mcp-server/.zen_venv/bin/python "${SAGE_HOME}/sage_mcp_stdio_single.py"