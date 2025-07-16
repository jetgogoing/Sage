#!/bin/bash
# Sage MCP 完整部署脚本
# 包含错误处理和自动修复

set -e  # 遇到错误立即停止

echo "======================================"
echo "   Sage MCP 完整部署脚本"
echo "======================================"
echo ""

# 1. 检查环境
echo "步骤 1: 检查环境..."
if ! command -v docker &> /dev/null; then
    echo "❌ Docker 未安装或未运行"
    exit 1
fi
echo "✅ Docker 已就绪"

# 检查 .env 文件
if [ -f .env ]; then
    echo "✅ 找到 .env 文件"
    export $(cat .env | grep -v '^#' | xargs)
else
    echo "⚠️  未找到 .env 文件"
    echo "创建示例 .env 文件..."
    cat > .env << EOF
# SiliconFlow API 密钥
SILICONFLOW_API_KEY=your_api_key_here

# Sage 配置
SAGE_LOG_LEVEL=INFO
SAGE_MAX_RESULTS=5
SAGE_ENABLE_RERANK=true
SAGE_ENABLE_SUMMARY=true
EOF
    echo "✅ 已创建 .env 文件模板，请编辑并设置 SILICONFLOW_API_KEY"
fi

# 2. 清理旧容器和镜像
echo ""
echo "步骤 2: 清理旧容器..."
docker rm -f sage-mcp 2>/dev/null || true
docker rm -f sage-test 2>/dev/null || true
echo "✅ 清理完成"

# 3. 构建镜像
echo ""
echo "步骤 3: 构建 Docker 镜像..."
echo "使用 Dockerfile.ubuntu.fixed"
echo ""

if ! docker build -f Dockerfile.ubuntu.fixed -t sage-mcp:ubuntu .; then
    echo "❌ 构建失败，尝试解决常见问题..."
    
    # 检查是否是网络问题
    echo "检查网络连接..."
    if ! ping -c 1 google.com &> /dev/null; then
        echo "❌ 网络连接问题，请检查网络"
        exit 1
    fi
    
    # 重试构建
    echo "重试构建..."
    docker build --no-cache -f Dockerfile.ubuntu.fixed -t sage-mcp:ubuntu . || {
        echo "❌ 构建仍然失败，请检查错误信息"
        exit 1
    }
fi

echo "✅ 镜像构建成功"

# 4. 测试容器启动
echo ""
echo "步骤 4: 测试容器启动..."

# 首先测试基本功能
echo "测试基本功能..."
docker run --rm sage-mcp:ubuntu echo "Container OK" || {
    echo "❌ 容器无法启动"
    exit 1
}

# 5. 测试完整启动
echo ""
echo "步骤 5: 测试完整服务启动..."

# 启动测试容器
docker run -d \
    --name sage-test \
    -e SILICONFLOW_API_KEY="${SILICONFLOW_API_KEY}" \
    -e SAGE_LOG_LEVEL=INFO \
    sage-mcp:ubuntu

# 等待服务启动
echo "等待服务启动..."
sleep 10

# 检查容器状态
if ! docker ps | grep sage-test > /dev/null; then
    echo "❌ 容器启动失败"
    echo "查看日志..."
    docker logs sage-test
    docker rm -f sage-test
    
    echo ""
    echo "尝试交互式调试..."
    docker run -it --rm \
        -e SILICONFLOW_API_KEY="${SILICONFLOW_API_KEY}" \
        sage-mcp:ubuntu bash
    exit 1
fi

# 检查 PostgreSQL
echo "检查 PostgreSQL 状态..."
if docker exec sage-test pg_isready -h localhost -p 5432 > /dev/null 2>&1; then
    echo "✅ PostgreSQL 运行正常"
else
    echo "❌ PostgreSQL 未正常运行"
    echo "查看 PostgreSQL 日志..."
    docker exec sage-test cat /var/log/sage/postgresql.log 2>/dev/null || echo "无法读取日志"
fi

# 检查数据库连接
echo "检查数据库连接..."
if docker exec sage-test sh -c 'PGPASSWORD=sage psql -h localhost -U sage -d sage -c "SELECT 1;"' > /dev/null 2>&1; then
    echo "✅ 数据库连接正常"
else
    echo "⚠️  数据库连接有问题，尝试修复..."
    docker exec sage-test su - postgres -c "psql -c \"CREATE USER sage WITH PASSWORD 'sage';\"" 2>/dev/null || true
    docker exec sage-test su - postgres -c "psql -c \"CREATE DATABASE sage OWNER sage;\"" 2>/dev/null || true
fi

# 检查 Python 环境
echo "检查 Python 环境..."
if docker exec sage-test python3 -c "import sage_core; print('OK')" > /dev/null 2>&1; then
    echo "✅ Python 环境正常"
else
    echo "❌ Python 模块导入失败"
fi

# 清理测试容器
docker rm -f sage-test

# 6. 测试 STDIO 通信
echo ""
echo "步骤 6: 测试 MCP STDIO 通信..."

# 测试工具列表
echo '{"jsonrpc":"2.0","method":"tools/list","id":1}' | \
docker run -i --rm \
    -e SILICONFLOW_API_KEY="${SILICONFLOW_API_KEY}" \
    sage-mcp:ubuntu | head -10 || {
    echo "⚠️  STDIO 通信可能有问题"
}

# 7. 配置 Claude Code
echo ""
echo "步骤 7: 配置 Claude Code..."

# 确保运行脚本可执行
chmod +x run_sage_ubuntu.sh

echo ""
echo "======================================"
echo "   部署完成！"
echo "======================================"
echo ""
echo "下一步操作："
echo ""
echo "1. 如果还未设置 API 密钥："
echo "   编辑 .env 文件，设置 SILICONFLOW_API_KEY"
echo ""
echo "2. 注册到 Claude Code:"
echo "   claude mcp add sage ./run_sage_ubuntu.sh"
echo ""
echo "3. 验证连接:"
echo "   claude mcp list"
echo ""
echo "4. 手动测试运行:"
echo "   ./run_sage_ubuntu.sh"
echo ""
echo "5. 交互式调试（如需要）:"
echo "   docker run -it --rm -e SILICONFLOW_API_KEY=\"\${SILICONFLOW_API_KEY}\" sage-mcp:ubuntu bash"
echo ""