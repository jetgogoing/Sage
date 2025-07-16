#!/usr/bin/env bash
# Sage MCP Server Startup Script
# This script ensures the MCP service is running and ready for Claude Code CLI
set -e

echo "🚀 Starting Sage MCP Server..."

# Function to check if container is healthy
check_container_health() {
    local container_name="sage-mcp"
    local max_attempts=30
    local attempt=1
    
    while [ $attempt -le $max_attempts ]; do
        if docker ps --format "table {{.Names}}\t{{.Status}}" | grep -q "$container_name.*healthy"; then
            echo "✅ Container is healthy"
            return 0
        fi
        
        echo "⏳ Waiting for container to be healthy... (attempt $attempt/$max_attempts)"
        sleep 2
        attempt=$((attempt + 1))
    done
    
    echo "❌ Container failed to become healthy"
    return 1
}

# Check Docker
if ! command -v docker &> /dev/null; then
    echo "❌ Error: Docker is not installed" >&2
    exit 1
fi

if ! docker info &> /dev/null; then
    echo "❌ Error: Docker daemon is not running" >&2
    exit 1
fi

# Use docker-compose or docker run based on preference
if [ -f "docker-compose.yml" ] && command -v docker-compose &> /dev/null; then
    echo "📦 Using docker-compose..."
    
    # Stop existing container if running
    docker-compose down 2>/dev/null || true
    
    # Build and start in detached mode
    docker-compose build
    docker-compose up -d
    
    # Wait for container to be healthy
    if check_container_health; then
        echo "✅ Sage MCP Server is running in background"
        echo ""
        echo "📋 To view logs: docker-compose logs -f"
        echo "🛑 To stop: docker-compose down"
        echo ""
        echo "🔌 Ready for Claude Code CLI connection!"
    else
        echo "❌ Failed to start Sage MCP Server"
        docker-compose logs
        exit 1
    fi
else
    echo "📦 Using docker run..."
    
    # Check if we need to build the image
    if ! docker images | grep -q "sage-mcp-single.*minimal"; then
        echo "🔨 Building Docker image..."
        docker build -t sage-mcp-single:minimal -f docker/single/Dockerfile.single.minimal .
    fi
    
    # Stop existing container if running
    docker rm -f sage-mcp 2>/dev/null || true
    
    # Start container in background
    docker run -d \
        --name sage-mcp \
        -v sage-mcp-data:/var/lib/postgresql/data \
        -v sage-mcp-logs:/var/log/sage \
        --restart unless-stopped \
        sage-mcp-single:minimal
    
    # Wait a bit for startup
    sleep 5
    
    # Check if container is running
    if docker ps | grep -q sage-mcp; then
        echo "✅ Sage MCP Server is running in background"
        echo ""
        echo "📋 To view logs: docker logs -f sage-mcp"
        echo "🛑 To stop: docker rm -f sage-mcp"
        echo ""
        echo "🔌 Ready for Claude Code CLI connection!"
    else
        echo "❌ Failed to start Sage MCP Server"
        docker logs sage-mcp
        exit 1
    fi
fi