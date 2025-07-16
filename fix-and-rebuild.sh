#!/bin/bash
# 快速修复和重建脚本

echo "=== 修复 PostgreSQL 初始化问题 ==="
echo ""

# 使用修复后的 entrypoint
echo "1. 复制修复后的启动脚本..."
cp docker/ubuntu/entrypoint-fixed.sh docker/ubuntu/entrypoint.sh
chmod +x docker/ubuntu/entrypoint.sh

# 重建镜像
echo ""
echo "2. 重建 Docker 镜像..."
docker build -f Dockerfile.ubuntu.fixed -t sage-mcp:ubuntu .

echo ""
echo "3. 测试运行..."
echo ""

# 清理旧容器
docker rm -f sage-test 2>/dev/null || true

# 测试运行
docker run -it --rm \
    --name sage-test \
    -e SILICONFLOW_API_KEY="${SILICONFLOW_API_KEY}" \
    -e SAGE_LOG_LEVEL=INFO \
    sage-mcp:ubuntu

echo ""
echo "如果还有问题，可以尝试："
echo ""
echo "1. 交互式调试模式："
echo "   docker run -it --rm -e SILICONFLOW_API_KEY=\"\$SILICONFLOW_API_KEY\" sage-mcp:ubuntu bash"
echo ""
echo "2. 查看 PostgreSQL 日志："
echo "   docker exec sage-test cat /var/log/sage/postgresql.log"
echo ""