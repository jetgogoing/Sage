#!/bin/bash
# Sage MCP stdio v2 wrapper startup script

# 设置颜色
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}🚀 Starting Sage MCP stdio server v2...${NC}"

# 确保 Docker 容器正在运行
echo -e "${YELLOW}Checking Sage Docker container...${NC}"
if ! docker ps | grep -q sage-mcp-server; then
    echo -e "${YELLOW}Starting Sage Docker container...${NC}"
    cd "$(dirname "$0")"
    docker-compose -f docker-compose.optimized.yml up -d
    
    # 等待服务启动
    echo -e "${YELLOW}Waiting for services to be ready...${NC}"
    for i in {1..30}; do
        if curl -s http://localhost:17800/health > /dev/null 2>&1; then
            echo -e "${GREEN}✅ Docker services are ready${NC}"
            break
        fi
        echo -n "."
        sleep 2
    done
    echo ""
fi

# 检查服务健康状态
echo -e "${YELLOW}Checking MCP service health...${NC}"
HEALTH_RESPONSE=$(curl -s http://localhost:17800/health 2>/dev/null)
if [ $? -eq 0 ] && echo "$HEALTH_RESPONSE" | grep -q "healthy"; then
    echo -e "${GREEN}✅ MCP service is healthy${NC}"
    echo -e "${BLUE}Health status:${NC}"
    echo "$HEALTH_RESPONSE" | python3 -m json.tool 2>/dev/null || echo "$HEALTH_RESPONSE"
else
    echo -e "${RED}❌ Error: MCP service is not healthy${NC}"
    echo -e "${YELLOW}Please check Docker logs:${NC}"
    echo "docker logs sage-mcp-server"
    exit 1
fi

# 激活虚拟环境（如果存在）
if [ -f "venv/bin/activate" ]; then
    echo -e "${YELLOW}Activating virtual environment...${NC}"
    source venv/bin/activate
fi

# 检查 Python 依赖
echo -e "${YELLOW}Checking Python dependencies...${NC}"
if ! python3 -c "import mcp.server" 2>/dev/null; then
    echo -e "${RED}❌ Error: MCP SDK not installed${NC}"
    echo -e "${YELLOW}Please run: pip install mcp${NC}"
    exit 1
fi

if ! python3 -c "import aiohttp" 2>/dev/null; then
    echo -e "${YELLOW}Installing aiohttp...${NC}"
    pip install aiohttp
fi

# 启动 stdio 服务器
echo -e "${GREEN}✅ Starting Sage MCP stdio server v2...${NC}"
echo -e "${BLUE}═══════════════════════════════════════${NC}"
echo -e "${BLUE}This server implements the MCP protocol${NC}"
echo -e "${BLUE}and proxies requests to the HTTP backend${NC}"
echo -e "${BLUE}═══════════════════════════════════════${NC}"
echo ""

# 设置环境变量（可选）
export SAGE_HTTP_URL=${SAGE_HTTP_URL:-"http://localhost:17800"}

# 启动服务器
exec python3 "$(dirname "$0")/sage_mcp_stdio_v2.py"