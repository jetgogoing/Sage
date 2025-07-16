# Docker 启动调试指南

## 单独启动 Docker 镜像的方法

### 1. 交互式调试模式（推荐）

进入容器的 bash shell，手动启动服务：

```bash
# 进入容器 bash（不执行默认启动脚本）
docker run -it --entrypoint /bin/bash \
  -e SILICONFLOW_API_KEY="$SILICONFLOW_API_KEY" \
  sage-mcp:ubuntu

# 在容器内手动执行：
# 1. 启动 PostgreSQL
su - postgres -c "/usr/lib/postgresql/15/bin/pg_ctl -D /var/lib/postgresql/data initdb"
su - postgres -c "/usr/lib/postgresql/15/bin/pg_ctl -D /var/lib/postgresql/data start"

# 2. 检查 PostgreSQL 状态
pg_isready -h localhost -p 5432

# 3. 创建数据库和用户
su - postgres -c "psql -c \"CREATE USER sage WITH PASSWORD 'sage';\""
su - postgres -c "psql -c \"CREATE DATABASE sage OWNER sage;\""

# 4. 启动应用
cd /app
python3 sage_mcp_stdio_v3.py
```

### 2. 使用调试启动脚本

```bash
# 复制调试脚本
cp docker/ubuntu/entrypoint-debug.sh docker/ubuntu/entrypoint.sh

# 重新构建镜像
docker build -f Dockerfile.ubuntu.fixed -t sage-mcp:ubuntu-debug .

# 运行并查看详细输出
docker run -it --rm \
  -e SILICONFLOW_API_KEY="$SILICONFLOW_API_KEY" \
  -e SAGE_LOG_LEVEL=DEBUG \
  sage-mcp:ubuntu-debug
```

### 3. 后台运行并查看日志

```bash
# 启动容器
docker run -d --name sage-test \
  -e SILICONFLOW_API_KEY="$SILICONFLOW_API_KEY" \
  sage-mcp:ubuntu

# 查看日志
docker logs -f sage-test

# 检查容器状态
docker ps -a

# 进入运行中的容器
docker exec -it sage-test /bin/bash
```

### 4. 分步骤测试

```bash
# 只测试 PostgreSQL
docker run -it --rm sage-mcp:ubuntu \
  su - postgres -c "/usr/lib/postgresql/15/bin/postgres --version"

# 只测试 Python 环境
docker run -it --rm sage-mcp:ubuntu \
  python3 -c "import sage_core; print('OK')"
```

## 常见问题和解决方案

### 问题 1: PostgreSQL 启动失败

**症状**: 
```
FATAL: could not create lock file "/var/run/postgresql/.s.PGSQL.5432.lock": No such file or directory
```

**解决**:
```bash
# 在容器内执行
mkdir -p /var/run/postgresql
chown postgres:postgres /var/run/postgresql
chmod 755 /var/run/postgresql
```

### 问题 2: 权限问题

**症状**:
```
initdb: error: could not change permissions of directory "/var/lib/postgresql/data": Operation not permitted
```

**解决**:
```bash
# 在 Dockerfile 中添加
RUN usermod -a -G postgres root
```

### 问题 3: Python 模块导入失败

**症状**:
```
ModuleNotFoundError: No module named 'sage_core'
```

**解决**:
```bash
# 检查 PYTHONPATH
export PYTHONPATH=/app:$PYTHONPATH

# 或在容器内
cd /app
python3 -m sage_mcp_stdio_v3
```

### 问题 4: STDIO 通信测试

```bash
# 测试 MCP 协议通信
echo '{"jsonrpc":"2.0","method":"tools/list","id":1}' | \
  docker run -i --rm \
  -e SILICONFLOW_API_KEY="$SILICONFLOW_API_KEY" \
  sage-mcp:ubuntu
```

## 使用测试脚本

运行提供的测试脚本：

```bash
./test-docker.sh
```

这会：
1. 清理旧容器
2. 启动新容器
3. 显示容器状态和日志
4. 提供各种调试命令

## 最小化测试

创建一个简单的测试 Dockerfile：

```dockerfile
FROM ubuntu:22.04
RUN apt-get update && apt-get install -y python3 python3-pip
WORKDIR /app
COPY requirements-cloud.txt .
RUN pip3 install -r requirements-cloud.txt
COPY sage_mcp_stdio_v3.py .
COPY sage_core /app/sage_core
COPY memory.py .
CMD ["python3", "-c", "print('Container started successfully')"]
```

如果这个能运行，再逐步添加 PostgreSQL 相关的部分。