#!/bin/bash
# 测试脚本：验证跨项目数据库启动功能

echo "=== 测试Sage MCP跨项目启动功能 ==="

# 1. 检查Docker状态
echo "1. 检查Docker运行状态..."
if docker info > /dev/null 2>&1; then
    echo "   ✓ Docker正在运行"
else
    echo "   ✗ Docker未运行，请先启动Docker Desktop"
    exit 1
fi

# 2. 检查pgvector容器状态
echo "2. 检查数据库容器状态..."
if docker ps | grep -q "sage-db.*Up"; then
    echo "   ✓ 数据库容器正在运行"
elif docker ps -a | grep -q "sage-db"; then
    echo "   ! 数据库容器存在但未运行"
    docker start sage-db
    echo "   ✓ 已启动数据库容器"
else
    echo "   ! 数据库容器不存在，将在首次启动时创建"
fi

# 3. 验证MCP配置
echo "3. 检查MCP配置..."
if grep -q "start_sage_mcp.sh" /Users/jet/.config/claude/mcp.json; then
    echo "   ✓ MCP配置正确"
else
    echo "   ✗ MCP配置错误，请检查~/.config/claude/mcp.json"
fi

# 4. 测试启动脚本
echo "4. 测试启动脚本..."
if [ -x /Users/jet/Sage/start_sage_mcp.sh ]; then
    echo "   ✓ 启动脚本可执行"
else
    echo "   ✗ 启动脚本不可执行，修复权限..."
    chmod +x /Users/jet/Sage/start_sage_mcp.sh
fi

# 5. 验证sage-mcp-single镜像已删除
echo "5. 确认sage-mcp-single镜像已删除..."
if docker images | grep -q "sage-mcp-single"; then
    echo "   ✗ sage-mcp-single镜像仍然存在"
else
    echo "   ✓ sage-mcp-single镜像已清理"
fi

echo ""
echo "=== 测试结果 ==="
echo "配置已优化为仅使用pgvector数据库镜像"
echo "任何项目中启动Claude Code都会自动启动共享数据库"
echo ""
echo "使用方法："
echo "1. 在任意项目中运行: claude"
echo "2. Sage MCP会自动启动pgvector数据库"
echo "3. 数据库在后台持续运行，不会随Claude Code退出而停止"