#!/usr/bin/env bash

# Sage MCP STDIO 启动脚本
# 用于 Claude Code 集成的最小化部署

# 设置颜色输出
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${GREEN}🚀 启动 Sage MCP STDIO 服务...${NC}"

# 检查 Docker 是否运行
if ! docker info >/dev/null 2>&1; then
    echo -e "${RED}❌ Docker 未运行，请先启动 Docker Desktop${NC}"
    exit 1
fi

# 启动数据库（如尚未启动）
echo -e "${YELLOW}📦 检查数据库状态...${NC}"
if docker-compose -f docker-compose.minimal.yml ps postgres 2>/dev/null | grep -q "Up"; then
    echo -e "${GREEN}✅ 数据库已运行${NC}"
else
    echo -e "${YELLOW}🔄 启动数据库...${NC}"
    docker-compose -f docker-compose.minimal.yml up -d postgres
    
    # 等待数据库健康检查通过
    echo -e "${YELLOW}⏳ 等待数据库就绪...${NC}"
    sleep 5
    
    # 最多等待30秒
    COUNTER=0
    while ! docker-compose -f docker-compose.minimal.yml ps postgres 2>/dev/null | grep -q "healthy"; do
        if [ $COUNTER -gt 30 ]; then
            echo -e "${RED}❌ 数据库启动超时${NC}"
            exit 1
        fi
        echo -n "."
        sleep 1
        COUNTER=$((COUNTER+1))
    done
    echo ""
    echo -e "${GREEN}✅ 数据库就绪${NC}"
fi

# 获取当前目录
SAGE_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# 启动 STDIO MCP 服务（直接运行，不使用 Docker）
echo -e "${GREEN}🎯 启动 STDIO 服务...${NC}"
echo -e "${YELLOW}提示：这将在前台运行，使用 Ctrl+C 停止${NC}"

# 设置环境变量并运行
export DB_HOST=localhost
export DB_PORT=5432
export DB_NAME=sage_memory
export DB_USER=sage
export DB_PASSWORD=sage123
export EMBEDDING_MODEL=Qwen/Qwen3-Embedding-8B
export EMBEDDING_DEVICE=cpu

# 进入项目目录并运行
cd "$SAGE_DIR"
exec python sage_mcp_stdio_v3.py