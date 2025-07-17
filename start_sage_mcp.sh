#!/bin/bash
# Sage MCP Startup Script
# This script activates the zen-mcp-server virtual environment and starts Sage MCP

export SAGE_LOG_DIR="/Users/jet/sage/logs"
export DB_HOST="localhost"
export DB_PORT="5432"
export DB_NAME="sage_memory"
export DB_USER="sage"
export DB_PASSWORD="sage123"
export EMBEDDING_MODEL="Qwen/Qwen3-Embedding-8B"
export EMBEDDING_DEVICE="cpu"
export SILICONFLOW_API_KEY="sk-xtjxdvdwjfiiggwxkojmiryhcfjliywfzurbtsorwvgkimdg"
export PYTHONPATH="/Users/jet/sage"

# Use the zen-mcp-server virtual environment where we installed the dependencies
exec /Users/jet/zen-mcp-server/.zen_venv/bin/python /Users/jet/sage/sage_mcp_stdio_single.py