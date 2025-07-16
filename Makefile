# Sage MCP Server Makefile
.PHONY: build run stop clean logs shell test help

# Default target
help:
	@echo "Sage MCP Server Management Commands:"
	@echo "  make build    - Build the Docker image"
	@echo "  make run      - Start the MCP server (persistent)"
	@echo "  make stop     - Stop the MCP server"
	@echo "  make clean    - Remove containers and volumes"
	@echo "  make logs     - View server logs"
	@echo "  make shell    - Open shell in container"
	@echo "  make test     - Test MCP connection"

# Build Docker image
build:
	@echo "🔨 Building Sage MCP Docker image..."
	docker build -t sage-mcp-single:minimal -f docker/single/Dockerfile.single.minimal .

# Run MCP server
run:
	@echo "🚀 Starting Sage MCP Server..."
	@./start_sage_mcp.sh

# Stop MCP server
stop:
	@echo "🛑 Stopping Sage MCP Server..."
	@if [ -f "docker-compose.yml" ] && command -v docker-compose &> /dev/null; then \
		docker-compose down; \
	else \
		docker rm -f sage-mcp || true; \
	fi

# Clean up everything
clean: stop
	@echo "🧹 Cleaning up containers and volumes..."
	@docker volume rm sage-mcp-data sage-mcp-logs 2>/dev/null || true
	@docker volume rm sage_sage-data sage_sage-logs 2>/dev/null || true
	@echo "✅ Cleanup complete"

# View logs
logs:
	@if docker ps | grep -q sage-mcp; then \
		docker logs -f sage-mcp; \
	else \
		echo "❌ Container is not running"; \
	fi

# Open shell in container
shell:
	@if docker ps | grep -q sage-mcp; then \
		docker exec -it sage-mcp /bin/bash; \
	else \
		echo "❌ Container is not running"; \
	fi

# Test MCP connection
test:
	@echo "🧪 Testing MCP connection..."
	@if docker ps | grep -q sage-mcp; then \
		echo "✅ Container is running"; \
		echo "📡 Checking MCP readiness..."; \
		docker exec sage-mcp ps aux | grep python || echo "⚠️  MCP process not found"; \
	else \
		echo "❌ Container is not running"; \
		exit 1; \
	fi