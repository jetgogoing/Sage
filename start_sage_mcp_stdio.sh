#!/bin/bash
# Sage MCP stdio wrapper startup script

# 确保 Docker 容器正在运行
echo "Checking Sage Docker container..." >&2
if ! docker ps | grep -q sage-docker-app; then
    echo "Starting Sage Docker container..." >&2
    cd "$(dirname "$0")"
    docker-compose -f docker-compose-sage.yml up -d
    sleep 5
fi

# 检查服务健康状态
echo "Checking MCP service health..." >&2
if ! curl -s http://localhost:17800/health > /dev/null; then
    echo "Error: MCP service is not healthy" >&2
    exit 1
fi

# 启动 stdio 包装器
echo "Starting Sage MCP stdio wrapper..." >&2
exec python3 "$(dirname "$0")/sage_mcp_stdio.py"