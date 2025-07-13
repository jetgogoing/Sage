#!/bin/bash
# Sage MCP Server Quick Start Script

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}🧠 Sage MCP Server - Quick Start${NC}"
echo -e "${BLUE}=================================${NC}"

# Check if .env file exists
if [ ! -f ".env" ]; then
    echo -e "${YELLOW}⚠️  .env file not found. Creating from template...${NC}"
    
    if [ -f ".env.example" ]; then
        cp .env.example .env
        echo -e "${YELLOW}📋 Please edit .env file with your configuration:${NC}"
        echo -e "   - SILICONFLOW_API_KEY=your-api-key"
        echo -e "   - Database settings (if needed)"
        echo ""
        echo -e "${YELLOW}After configuring .env, run this script again.${NC}"
        exit 1
    else
        echo -e "${RED}❌ .env.example template not found${NC}"
        exit 1
    fi
fi

# Load environment variables
source .env

# Check required variables
if [ -z "$SILICONFLOW_API_KEY" ] || [ "$SILICONFLOW_API_KEY" = "sk-your-siliconflow-api-key-here" ]; then
    echo -e "${RED}❌ Please set SILICONFLOW_API_KEY in .env file${NC}"
    exit 1
fi

echo -e "${GREEN}✅ Environment configuration loaded${NC}"

# Check if Docker is running
if ! docker info > /dev/null 2>&1; then
    echo -e "${RED}❌ Docker is not running. Please start Docker first.${NC}"
    exit 1
fi

echo -e "${GREEN}✅ Docker is running${NC}"

# Stop existing containers
echo -e "${YELLOW}🛑 Stopping existing containers...${NC}"
docker-compose down 2>/dev/null || true

# Build and start services
echo -e "${YELLOW}🔨 Building Sage MCP Server...${NC}"
docker-compose build sage-mcp

echo -e "${YELLOW}🚀 Starting services...${NC}"
docker-compose up -d

# Wait for services to be healthy
echo -e "${YELLOW}🔄 Waiting for services to be ready...${NC}"
max_attempts=60
attempt=0

while [ $attempt -lt $max_attempts ]; do
    if docker-compose ps | grep -q "healthy"; then
        echo -e "${GREEN}✅ Services are healthy${NC}"
        break
    fi
    
    attempt=$((attempt + 1))
    echo -e "${YELLOW}   Waiting... ($attempt/$max_attempts)${NC}"
    sleep 2
done

if [ $attempt -eq $max_attempts ]; then
    echo -e "${RED}❌ Services failed to start properly${NC}"
    echo -e "${YELLOW}📋 Checking logs...${NC}"
    docker-compose logs sage-mcp
    exit 1
fi

# Test the service
echo -e "${YELLOW}🧪 Testing MCP server...${NC}"
HEALTH_RESPONSE=$(curl -s http://localhost:17800/health || echo "failed")

if echo "$HEALTH_RESPONSE" | grep -q "healthy"; then
    echo -e "${GREEN}✅ Sage MCP Server is running successfully!${NC}"
    echo ""
    echo -e "${BLUE}📊 Service Information:${NC}"
    echo -e "   🌐 MCP Server: http://localhost:17800"
    echo -e "   🏥 Health Check: http://localhost:17800/health"
    echo -e "   📋 Detailed Health: http://localhost:17800/health/detailed"
    echo -e "   🗄️  PostgreSQL: localhost:5432"
    echo ""
    echo -e "${BLUE}🛠️  Management Commands:${NC}"
    echo -e "   📊 View logs: docker-compose logs -f sage-mcp"
    echo -e "   ⏹️  Stop services: docker-compose down"
    echo -e "   🔄 Restart: docker-compose restart sage-mcp"
    echo ""
    echo -e "${GREEN}🎉 Ready to use with Claude Code!${NC}"
    echo -e "${YELLOW}💡 Configure Claude Code to use: http://localhost:17800${NC}"
else
    echo -e "${RED}❌ Service health check failed${NC}"
    echo -e "${YELLOW}📋 Response: $HEALTH_RESPONSE${NC}"
    echo -e "${YELLOW}📋 Checking logs...${NC}"
    docker-compose logs --tail=20 sage-mcp
    exit 1
fi