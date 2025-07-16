#!/bin/bash
# Sage MCP Docker 测试和调试脚本

echo "=== Sage MCP Docker 测试脚本 ==="
echo ""

# 1. 先清理可能存在的容器
echo "清理旧容器..."
docker rm -f sage-test 2>/dev/null || true

# 2. 交互式运行容器以查看启动过程
echo ""
echo "方式1: 交互式运行（查看实时日志）"
echo "命令: docker run -it --rm -e SILICONFLOW_API_KEY=\"\$SILICONFLOW_API_KEY\" sage-mcp:ubuntu"
echo ""

# 3. 后台运行并查看日志
echo "方式2: 后台运行并查看日志"
echo "启动容器..."
docker run -d \
    --name sage-test \
    -e SILICONFLOW_API_KEY="${SILICONFLOW_API_KEY}" \
    -e SAGE_LOG_LEVEL=DEBUG \
    sage-mcp:ubuntu

echo "等待 5 秒..."
sleep 5

echo ""
echo "容器状态:"
docker ps -a | grep sage-test

echo ""
echo "容器日志:"
docker logs sage-test

echo ""
echo "=== 调试命令 ==="
echo ""
echo "1. 进入容器 bash shell（调试模式）:"
echo "   docker run -it --entrypoint /bin/bash sage-mcp:ubuntu"
echo ""
echo "2. 查看容器内进程:"
echo "   docker exec sage-test ps aux"
echo ""
echo "3. 检查 PostgreSQL 状态:"
echo "   docker exec sage-test pg_isready -h localhost -p 5432"
echo ""
echo "4. 查看 PostgreSQL 日志:"
echo "   docker exec sage-test cat /var/log/sage/postgresql.log"
echo ""
echo "5. 手动在容器内启动服务:"
echo "   docker exec -it sage-test /bin/bash"
echo "   # 然后在容器内执行:"
echo "   su - postgres -c \"/usr/lib/postgresql/15/bin/pg_ctl -D /var/lib/postgresql/data start\""
echo "   python3 /app/sage_mcp_stdio_v3.py"
echo ""