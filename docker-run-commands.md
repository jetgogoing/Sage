# Docker 运行命令汇总

## 立即修复并运行

```bash
# 1. 使修复脚本可执行
chmod +x fix-and-rebuild.sh docker/ubuntu/entrypoint-fixed.sh

# 2. 运行修复脚本
./fix-and-rebuild.sh
```

## 各种运行方式

### 1. 标准运行（STDIO 模式）
```bash
docker run -it --rm \
    -e SILICONFLOW_API_KEY="${SILICONFLOW_API_KEY}" \
    sage-mcp:ubuntu
```

### 2. 调试模式（进入 bash）
```bash
docker run -it --rm \
    -e SILICONFLOW_API_KEY="${SILICONFLOW_API_KEY}" \
    sage-mcp:ubuntu bash
```

### 3. 后台运行
```bash
docker run -d \
    --name sage-mcp \
    -e SILICONFLOW_API_KEY="${SILICONFLOW_API_KEY}" \
    sage-mcp:ubuntu
    
# 查看日志
docker logs -f sage-mcp
```

### 4. 使用数据持久化
```bash
# 创建数据卷
docker volume create sage-pgdata
docker volume create sage-logs

# 运行时挂载
docker run -it --rm \
    -v sage-pgdata:/var/lib/postgresql/data \
    -v sage-logs:/var/log/sage \
    -e SILICONFLOW_API_KEY="${SILICONFLOW_API_KEY}" \
    sage-mcp:ubuntu
```

### 5. 完整配置运行
```bash
docker run -it --rm \
    --name sage-mcp \
    -e SILICONFLOW_API_KEY="${SILICONFLOW_API_KEY}" \
    -e SAGE_LOG_LEVEL=INFO \
    -e SAGE_MAX_RESULTS=5 \
    -e SAGE_ENABLE_RERANK=true \
    -e SAGE_ENABLE_SUMMARY=true \
    -e SAGE_CACHE_SIZE=500 \
    -e SAGE_CACHE_TTL=300 \
    -v sage-data:/var/lib/postgresql/data \
    -v sage-logs:/var/log/sage \
    sage-mcp:ubuntu
```

## 故障排查命令

### 查看容器内部状态
```bash
# PostgreSQL 状态
docker exec -it sage-mcp pg_isready -h localhost -p 5432

# 数据库内容
docker exec -it sage-mcp su - postgres -c "psql -l"

# Python 环境
docker exec -it sage-mcp python3 -c "import sage_core; print('OK')"

# 查看日志
docker exec -it sage-mcp cat /var/log/sage/postgresql.log
```

### 手动初始化（在容器内）
```bash
# 进入容器
docker run -it --rm sage-mcp:ubuntu bash

# 手动初始化 PostgreSQL
su - postgres -c "/usr/lib/postgresql/15/bin/initdb -D /var/lib/postgresql/data"
su - postgres -c "/usr/lib/postgresql/15/bin/pg_ctl -D /var/lib/postgresql/data start"

# 创建数据库
su - postgres -c "psql -c 'CREATE DATABASE sage;'"
su - postgres -c "psql -c \"CREATE USER sage WITH PASSWORD 'sage';\""
```

## MCP 测试

### 直接测试 STDIO 通信
```bash
# 列出工具
echo '{"jsonrpc":"2.0","method":"tools/list","id":1}' | \
docker run -i --rm -e SILICONFLOW_API_KEY="${SILICONFLOW_API_KEY}" sage-mcp:ubuntu

# 获取提示
echo '{"jsonrpc":"2.0","method":"prompts/list","id":1}' | \
docker run -i --rm -e SILICONFLOW_API_KEY="${SILICONFLOW_API_KEY}" sage-mcp:ubuntu
```

## Claude Code 集成

确保 `run_sage_ubuntu.sh` 正确配置：

```bash
#!/usr/bin/env bash
# 加载环境变量
if [ -f "$(dirname "$0")/.env" ]; then
    export $(cat "$(dirname "$0")/.env" | grep -v '^#' | xargs)
fi

# 运行容器
docker run --rm -i \
    -e SILICONFLOW_API_KEY="${SILICONFLOW_API_KEY}" \
    sage-mcp:ubuntu
```

注册到 Claude Code：
```bash
claude mcp add sage ./run_sage_ubuntu.sh
```