#!/bin/bash

# 测试 Sage MCP 容器

echo "1. 检查容器状态..."
docker ps -a --filter "name=sage-mcp" --format "table {{.ID}}\t{{.Names}}\t{{.Status}}"

echo -e "\n2. 尝试在前台运行容器..."
docker rm -f sage-mcp 2>/dev/null

echo -e "\n3. 启动容器并检查数据库..."
docker run -d --name sage-mcp \
    -e POSTGRES_PASSWORD=sage \
    -e SILICONFLOW_API_KEY=$SILICONFLOW_API_KEY \
    sage-mcp-single:latest \
    tail -f /dev/null  # 保持容器运行

sleep 10

echo -e "\n4. 检查 PostgreSQL 状态..."
docker exec sage-mcp psql -U postgres -c "SELECT version();"

echo -e "\n5. 检查 pgvector 扩展..."
docker exec sage-mcp psql -U postgres -d sage_memory -c "SELECT * FROM pg_extension WHERE extname = 'vector';"

echo -e "\n6. 检查表结构..."
docker exec sage-mcp psql -U postgres -d sage_memory -c "\d+ memories"

echo -e "\n7. 测试向量存储..."
docker exec sage-mcp psql -U postgres -d sage_memory -c "
INSERT INTO memories (session_id, user_input, assistant_response, embedding, metadata)
VALUES ('test', 'Hello', 'Hi there', array_fill(0.1, ARRAY[4096])::vector, '{}')
RETURNING id;
"

echo -e "\n8. 清理测试容器..."
# docker rm -f sage-mcp

echo "测试完成！"