#!/bin/bash
# Sage MCP Server Docker entrypoint script

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${GREEN}🚀 Starting Sage MCP Server...${NC}"

# Configuration validation
echo -e "${YELLOW}📋 Validating configuration...${NC}"

# Check required environment variables
REQUIRED_VARS=(
    "SILICONFLOW_API_KEY"
    "DB_HOST"
    "DB_NAME" 
    "DB_USER"
    "DB_PASSWORD"
)

missing_vars=()
for var in "${REQUIRED_VARS[@]}"; do
    if [ -z "${!var}" ]; then
        missing_vars+=("$var")
    fi
done

if [ ${#missing_vars[@]} -ne 0 ]; then
    echo -e "${RED}❌ Missing required environment variables:${NC}"
    printf "${RED}   - %s${NC}\n" "${missing_vars[@]}"
    echo -e "${YELLOW}💡 Please check your .env file or Docker environment variables${NC}"
    exit 1
fi

# Set default values
export MCP_SERVER_HOST=${MCP_SERVER_HOST:-"0.0.0.0"}
export MCP_SERVER_PORT=${MCP_SERVER_PORT:-"17800"}
export LOG_LEVEL=${LOG_LEVEL:-"INFO"}
export SAGE_MEMORY_ENABLED=${SAGE_MEMORY_ENABLED:-"true"}
export SAGE_RETRIEVAL_COUNT=${SAGE_RETRIEVAL_COUNT:-"10"}
export ENABLE_LLM_SUMMARY=${ENABLE_LLM_SUMMARY:-"true"}
export ENABLE_NEURAL_RERANK=${ENABLE_NEURAL_RERANK:-"true"}

echo -e "${GREEN}✅ Configuration validation passed${NC}"

# Wait for database to be ready
echo -e "${YELLOW}🔄 Waiting for database to be ready...${NC}"
max_attempts=30
attempt=0

while [ $attempt -lt $max_attempts ]; do
    # Simple connectivity test using built-in tools
    if timeout 2 bash -c "echo > /dev/tcp/$DB_HOST/$DB_PORT" 2>/dev/null; then
        echo -e "${GREEN}✅ Database port is reachable${NC}"
        # Try a simple Python import test
        if python -c "import sys; sys.path.insert(0, '/app')" 2>/dev/null; then
            echo -e "${GREEN}✅ Python environment is ready${NC}"
            break
        fi
    fi
    
    attempt=$((attempt + 1))
    echo -e "${YELLOW}   Attempt $attempt/$max_attempts - Database not ready, waiting 2 seconds...${NC}"
    sleep 2
done

if [ $attempt -eq $max_attempts ]; then
    echo -e "${RED}❌ Database connection failed after $max_attempts attempts${NC}"
    exit 1
fi

# Run configuration validation
echo -e "${YELLOW}🔍 Running configuration validation...${NC}"
if python -c "
import sys
sys.path.insert(0, '/app')
from config_manager import get_config_manager
manager = get_config_manager()
errors = manager.validate()
if errors:
    print('Configuration errors:')
    for error in errors:
        print(f'  - {error}')
    sys.exit(1)
else:
    print('Configuration validation passed')
"; then
    echo -e "${GREEN}✅ Configuration validation passed${NC}"
else
    echo -e "${RED}❌ Configuration validation failed${NC}"
    exit 1
fi

# Display startup information
echo -e "${GREEN}📊 Startup Information:${NC}"
echo -e "   Host: ${MCP_SERVER_HOST}"
echo -e "   Port: ${MCP_SERVER_PORT}"
echo -e "   Database: ${DB_HOST}:${DB_PORT}/${DB_NAME}"
echo -e "   Memory System: ${SAGE_MEMORY_ENABLED}"
echo -e "   Neural Reranking: ${ENABLE_NEURAL_RERANK}"
echo -e "   LLM Summary: ${ENABLE_LLM_SUMMARY}"
echo -e "   Log Level: ${LOG_LEVEL}"

# Start the server
echo -e "${GREEN}🚀 Starting Sage MCP Server...${NC}"
cd /app
export PYTHONPATH=/app:$PYTHONPATH
exec python -m app.sage_mcp_server \
    || exec python app/sage_mcp_server.py