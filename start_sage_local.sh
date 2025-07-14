#!/bin/bash
# Sage MCP 本地启动脚本

# 加载环境变量
export $(cat /Users/jet/sage/.env | grep -v '^#' | xargs)

# 验证必需的环境变量
if [ -z "$SILICONFLOW_API_KEY" ]; then
    echo "错误: SILICONFLOW_API_KEY 未设置"
    exit 1
fi

if [ -z "$DATABASE_URL" ]; then
    echo "错误: DATABASE_URL 未设置"
    exit 1
fi

# 显示配置信息
echo "==================================="
echo "Sage MCP 本地部署配置"
echo "==================================="
echo "数据库: $DATABASE_URL"
echo "API密钥: ${SILICONFLOW_API_KEY:0:10}..."
echo "==================================="

# 启动 Sage MCP 服务器
echo "启动 Sage MCP 服务器..."
python /Users/jet/sage/app/sage_mcp_server.py