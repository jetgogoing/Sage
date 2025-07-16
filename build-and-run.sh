#!/bin/bash
# Sage MCP 快速构建和运行脚本

echo "=== Sage MCP Docker 构建脚本 ==="
echo ""

# 检查 Docker 是否运行
if ! docker info > /dev/null 2>&1; then
    echo "❌ Docker 未运行，请先启动 Docker Desktop"
    exit 1
fi

# 加载环境变量
if [ -f .env ]; then
    echo "✓ 加载 .env 文件"
    export $(cat .env | grep -v '^#' | xargs)
else
    echo "⚠️  未找到 .env 文件"
    echo "   请创建 .env 文件并设置 SILICONFLOW_API_KEY"
fi

# 检查 API 密钥
if [ -z "$SILICONFLOW_API_KEY" ]; then
    echo ""
    echo "⚠️  警告: SILICONFLOW_API_KEY 未设置"
    echo "   系统将使用哈希向量化作为降级方案"
    echo ""
    read -p "是否继续? (y/n) " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        exit 1
    fi
fi

# 使用修复后的 entrypoint
echo "更新启动脚本..."
cp docker/ubuntu/entrypoint-mcp.sh docker/ubuntu/entrypoint.sh
chmod +x docker/ubuntu/entrypoint.sh

# 构建镜像
echo ""
echo "开始构建 Docker 镜像..."
echo "使用文件: Dockerfile.ubuntu.fixed"
echo ""

docker build -f Dockerfile.ubuntu.fixed -t sage-mcp:ubuntu . || {
    echo "❌ 构建失败"
    exit 1
}

echo ""
echo "✅ 镜像构建成功!"
echo ""

# 显示镜像信息
docker images sage-mcp:ubuntu

# 测试运行
echo ""
echo "测试运行容器..."
echo ""

# 先清理可能存在的旧容器
docker rm -f sage-test 2>/dev/null || true

# 测试运行
docker run -d \
    --name sage-test \
    -e SILICONFLOW_API_KEY="$SILICONFLOW_API_KEY" \
    sage-mcp:ubuntu \
    sleep 30

# 等待容器启动
sleep 5

# 检查容器状态
if docker ps | grep sage-test > /dev/null; then
    echo "✅ 容器运行正常"
    
    # 检查 PostgreSQL
    echo "检查 PostgreSQL..."
    docker exec sage-test pg_isready -h localhost -p 5432 && echo "✅ PostgreSQL 正常"
    
    # 检查 Python 环境
    echo "检查 Python 环境..."
    docker exec sage-test python3 -c "import sage_core; print('✅ sage_core 导入成功')"
    
    # 清理测试容器
    docker rm -f sage-test
else
    echo "❌ 容器启动失败"
    docker logs sage-test
    docker rm -f sage-test
    exit 1
fi

echo ""
echo "=== 构建完成 ==="
echo ""
echo "下一步:"
echo "1. 确保 run_sage_ubuntu.sh 有执行权限:"
echo "   chmod +x run_sage_ubuntu.sh"
echo ""
echo "2. 注册到 Claude Code:"
echo "   claude mcp add sage ./run_sage_ubuntu.sh"
echo ""
echo "3. 或者使用配置文件:"
echo "   将 claude-config.json 的内容添加到 Claude Code 设置中"
echo ""
echo "4. 验证连接:"
echo "   claude mcp list"
echo ""