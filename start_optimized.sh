#!/bin/bash
# Sage MCP 优化启动脚本

set -e

echo "🚀 Sage MCP 快速启动"
echo "====================="

# 检查Docker
if ! docker info &> /dev/null; then
    echo "❌ Docker未运行"
    exit 1
fi

# 检查环境变量
if [ -z "$SILICONFLOW_API_KEY" ] && [ ! -f .env ]; then
    echo "⚠️  未设置SILICONFLOW_API_KEY"
    echo "请设置环境变量或创建.env文件"
    exit 1
fi

# 使用优化的配置启动
echo "🔄 启动优化的容器..."
docker compose -f docker-compose.optimized.yml up -d

# 等待服务就绪
echo "⏳ 等待服务启动..."
for i in {1..30}; do
    if curl -s http://localhost:17800/health > /dev/null; then
        echo "✅ Sage MCP服务已就绪！"
        echo ""
        echo "📊 服务状态:"
        docker compose -f docker-compose.optimized.yml ps
        echo ""
        echo "🔗 MCP服务地址: http://localhost:17800"
        echo "📝 健康检查: http://localhost:17800/health"
        exit 0
    fi
    sleep 1
    echo -n "."
done

echo ""
echo "❌ 服务启动超时"
docker compose -f docker-compose.optimized.yml logs
exit 1
