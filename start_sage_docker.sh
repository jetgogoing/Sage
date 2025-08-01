#!/bin/bash
# Sage MCP Docker 智能启动脚本
# 支持手动启动和 Claude Code CLI 自动启动模式

CONTAINER_NAME="sage-mcp"
PROJECT_DIR="/Users/jet/Sage"

# 智能检测模式：如果有 stdin 输入或运行环境非交互，则为 CLI 模式
if [ ! -t 0 ] || [ ! -t 1 ]; then
    # CLI 模式：完全静默检查和启动
    if ! docker ps | grep -q "$CONTAINER_NAME.*Up"; then
        cd "$PROJECT_DIR" && docker-compose up -d > /dev/null 2>&1
        sleep 3
        if ! docker ps | grep -q "$CONTAINER_NAME.*Up"; then
            exit 1
        fi
    fi
    # 执行 MCP 服务
    exec docker exec -i "$CONTAINER_NAME" python3 /app/sage_mcp_stdio_single.py "$@"
else
    # 手动模式：完整启动流程和状态显示
    echo "🚀 启动 Sage MCP Docker 服务..."
    
    # 检查Docker是否运行
    if ! docker info > /dev/null 2>&1; then
        echo "❌ Docker未运行，请先启动Docker Desktop"
        exit 1
    fi
    
    # 进入项目目录
    cd "$PROJECT_DIR" || exit 1
    
    # 启动服务
    docker-compose up -d
    
    # 等待服务就绪
    echo "⏳ 等待服务启动..."
    sleep 5
    
    # 检查服务状态
    if docker ps | grep -q "sage-mcp.*healthy"; then
        echo "✅ Sage MCP服务启动成功！"
        echo "📊 服务状态："
        docker ps | grep sage
        echo ""
        echo "🔗 现在可以在Claude Code CLI中使用Sage MCP功能"
    else
        echo "❌ 服务启动失败，检查日志："
        docker logs sage-mcp --tail 10
    fi
fi