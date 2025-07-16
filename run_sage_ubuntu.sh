#!/usr/bin/env bash
# Sage MCP Ubuntu 版本运行脚本
# 用于 Claude Code 注册

# 检查是否有 .env 文件
if [ -f "$(dirname "$0")/.env" ]; then
    export $(cat "$(dirname "$0")/.env" | grep -v '^#' | xargs)
fi

# 确保传递必要的环境变量
docker run --rm -i \
    -e SILICONFLOW_API_KEY="${SILICONFLOW_API_KEY}" \
    -e SAGE_LOG_LEVEL="${SAGE_LOG_LEVEL:-INFO}" \
    -e SAGE_MAX_RESULTS="${SAGE_MAX_RESULTS:-5}" \
    -e SAGE_ENABLE_RERANK="${SAGE_ENABLE_RERANK:-true}" \
    -e SAGE_ENABLE_SUMMARY="${SAGE_ENABLE_SUMMARY:-true}" \
    -e SAGE_CACHE_SIZE="${SAGE_CACHE_SIZE:-500}" \
    -e SAGE_CACHE_TTL="${SAGE_CACHE_TTL:-300}" \
    sage-mcp:ubuntu