# Sage MCP Server 数据库Docker部署指南

> **版本**: v1.0  
> **创建时间**: 2025-08-02  
> **适用版本**: Sage MCP Server v2.x+  

## 概述

本指南提供了Sage MCP Server数据库（PostgreSQL + pgvector）的完整Docker部署方案。系统支持向量存储与检索、记忆管理、会话管理等核心功能，专为MCP协议优化。

## 1. 部署前准备

### 环境要求

- **Docker Engine**: >= 20.x
- **Docker Compose**: V2 (推荐)
- **操作系统**: Linux / macOS / Windows
- **内存**: 最少2GB，推荐4GB+
- **磁盘空间**: 最少10GB用于数据存储
- **网络**: 端口5432未被占用

### 依赖检查

```bash
# 检查Docker版本
docker --version
docker-compose --version

# 检查端口占用
netstat -tlnp | grep :5432

# 检查磁盘空间
df -h
```

## 2. 快速部署步骤

### 2.1 克隆项目并切换到项目目录

```bash
cd /path/to/Sage
```

### 2.2 一键启动数据库

```bash
# 拉取镜像
docker-compose -f docker-compose-db.yml pull

# 启动容器（后台运行）
docker-compose -f docker-compose-db.yml up -d

# 查看运行状态
docker-compose -f docker-compose-db.yml ps
```

### 2.3 验证部署

```bash
# 检查容器状态
docker ps | grep sage-db

# 检查健康状态
docker-compose -f docker-compose-db.yml logs sage-db

# 测试数据库连接
docker exec -it sage-db psql -U sage -d sage_memory -c "SELECT version();"
```

## 3. 详细配置说明

### 3.1 Docker Compose配置

当前的`docker-compose-db.yml`配置：

```yaml
version: '3.8'

services:
  sage-db:
    image: pgvector/pgvector:pg15
    container_name: sage-db
    ports:
      - "5432:5432"
    environment:
      POSTGRES_USER: sage
      POSTGRES_PASSWORD: sage123
      POSTGRES_DB: sage_memory
    volumes:
      - sage-db-data:/var/lib/postgresql/data
      - ./docker/init.sql:/docker-entrypoint-initdb.d/init.sql
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U sage -d sage_memory"]
      interval: 10s
      timeout: 5s
      retries: 5

volumes:
  sage-db-data:
    driver: local
```

### 3.2 环境变量配置

核心环境变量说明：

| 变量名 | 默认值 | 说明 |
|--------|--------|------|
| `POSTGRES_USER` | sage | 数据库用户名 |
| `POSTGRES_PASSWORD` | sage123 | 数据库密码 |
| `POSTGRES_DB` | sage_memory | 数据库名称 |
| `DB_HOST` | localhost | 数据库主机地址 |
| `DB_PORT` | 5432 | 数据库端口 |

### 3.3 数据卷配置

- **数据持久化**: `sage-db-data` 卷确保数据在容器重启后保持
- **初始化脚本**: `./docker/init.sql` 自动执行数据库初始化

## 4. 数据库初始化详解

### 4.1 表结构

系统创建两个核心表：

#### memories表 - 记忆存储
```sql
CREATE TABLE IF NOT EXISTS memories (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    session_id VARCHAR(255),
    user_input TEXT NOT NULL,
    assistant_response TEXT NOT NULL,
    embedding vector(4096),  -- 4096维向量存储
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);
```

#### sessions表 - 会话管理
```sql
CREATE TABLE IF NOT EXISTS sessions (
    id VARCHAR(255) PRIMARY KEY,
    name VARCHAR(255),
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    last_active TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);
```

### 4.2 索引优化

```sql
-- 查询性能索引
CREATE INDEX IF NOT EXISTS idx_memories_session_id ON memories(session_id);
CREATE INDEX IF NOT EXISTS idx_memories_created_at ON memories(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_sessions_last_active ON sessions(last_active DESC);

-- 注意：4096维向量暂不创建向量索引，使用顺序扫描
-- HNSW索引需要额外配置，ivfflat限制2000维
```

### 4.3 权限设置

```sql
-- 为sage用户分配权限
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO sage;
GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public TO sage;
GRANT EXECUTE ON ALL FUNCTIONS IN SCHEMA public TO sage;
```

## 5. 安全配置

### 5.1 密码管理

**开发环境**:
```bash
# 使用默认密码
export POSTGRES_PASSWORD=sage123
```

**生产环境**:
```bash
# 使用环境变量文件
echo "POSTGRES_PASSWORD=your_strong_password_here" > .env
docker-compose -f docker-compose-db.yml --env-file .env up -d
```

### 5.2 网络安全

```yaml
# 仅内部网络访问
services:
  sage-db:
    # 移除端口映射，仅允许Docker内部访问
    # ports:
    #   - "5432:5432"
    networks:
      - sage-internal

networks:
  sage-internal:
    driver: bridge
    internal: true
```

### 5.3 数据加密

```bash
# 使用加密卷（示例，需要根据具体环境配置）
docker volume create --driver local \
  --opt type=tmpfs \
  --opt device=tmpfs \
  --opt o=encryption=aes256 \
  sage-db-data-encrypted
```

## 6. 性能优化

### 6.1 PostgreSQL参数调优

创建`docker/postgresql.conf`：

```conf
# 内存配置
shared_buffers = 256MB
work_mem = 64MB
maintenance_work_mem = 128MB

# 连接配置
max_connections = 100

# 日志配置
log_statement = 'mod'
log_duration = on
log_min_duration_statement = 1000

# 向量查询优化
random_page_cost = 1.1
effective_cache_size = 1GB
```

然后在docker-compose.yml中挂载：

```yaml
volumes:
  - ./docker/postgresql.conf:/etc/postgresql/postgresql.conf
command: ["postgres", "-c", "config_file=/etc/postgresql/postgresql.conf"]
```

### 6.2 连接池配置

使用pgBouncer作为连接池：

```yaml
services:
  pgbouncer:
    image: pgbouncer/pgbouncer:latest
    environment:
      DATABASES_HOST: sage-db
      DATABASES_PORT: 5432
      DATABASES_USER: sage
      DATABASES_PASSWORD: sage123
      DATABASES_DBNAME: sage_memory
      POOL_MODE: transaction
      MAX_CLIENT_CONN: 100
      DEFAULT_POOL_SIZE: 20
    ports:
      - "6432:5432"
    depends_on:
      - sage-db
```

### 6.3 向量查询优化

```sql
-- 为向量查询创建HNSW索引（如支持）
CREATE INDEX ON memories USING hnsw (embedding vector_cosine_ops);

-- 调整向量查询参数
SET hnsw.ef_search = 100;
```

## 7. 监控与日志

### 7.1 健康检查

当前配置的健康检查：

```yaml
healthcheck:
  test: ["CMD-SHELL", "pg_isready -U sage -d sage_memory"]
  interval: 10s
  timeout: 5s
  retries: 5
```

### 7.2 日志配置

```bash
# 查看容器日志
docker-compose -f docker-compose-db.yml logs -f sage-db

# 配置日志轮转
docker-compose -f docker-compose-db.yml up -d --log-opt max-size=10m --log-opt max-file=3
```

### 7.3 性能监控

添加Prometheus监控：

```yaml
services:
  postgres-exporter:
    image: prometheuscommunity/postgres-exporter
    environment:
      DATA_SOURCE_NAME: postgresql://sage:sage123@sage-db:5432/sage_memory?sslmode=disable
    ports:
      - "9187:9187"
    depends_on:
      - sage-db
```

## 8. 故障排除

### 8.1 常见问题

#### 问题1: 容器启动失败
```bash
# 检查日志
docker-compose -f docker-compose-db.yml logs sage-db

# 常见原因：
# - 端口被占用
# - 数据卷权限问题
# - 内存不足
```

#### 问题2: 数据库连接失败
```bash
# 验证数据库状态
docker exec -it sage-db pg_isready -U sage

# 检查网络连接
docker exec -it sage-db netstat -tlnp

# 验证用户权限
docker exec -it sage-db psql -U sage -d sage_memory -c "\du"
```

#### 问题3: pgvector扩展问题
```bash
# 检查扩展状态
docker exec -it sage-db psql -U sage -d sage_memory -c "SELECT * FROM pg_extension WHERE extname='vector';"

# 手动创建扩展
docker exec -it sage-db psql -U sage -d sage_memory -c "CREATE EXTENSION IF NOT EXISTS vector;"
```

### 8.2 诊断命令

```bash
# 容器状态诊断
docker inspect sage-db

# 资源使用情况
docker stats sage-db

# 数据库连接测试
docker exec -it sage-db psql -U sage -d sage_memory -c "
SELECT 
    count(*) as total_memories,
    count(DISTINCT session_id) as unique_sessions
FROM memories;
"
```

## 9. 生产环境建议

### 9.1 高可用部署

#### 主从复制配置

**主库配置** (`postgresql-master.conf`):
```conf
wal_level = replica
max_wal_senders = 3
wal_keep_segments = 64
```

**从库配置**:
```yaml
services:
  sage-db-replica:
    image: pgvector/pgvector:pg15
    environment:
      PGUSER: replicator
      POSTGRES_PASSWORD: replica_password
      POSTGRES_MASTER_SERVICE: sage-db
    command: |
      bash -c "
      until PGPASSWORD=$$POSTGRES_PASSWORD pg_basebackup -h $$POSTGRES_MASTER_SERVICE -D /var/lib/postgresql/data -U replicator -v -P -W
      do
        echo 'Waiting for master to connect...'
        sleep 1s
      done
      echo 'Backup done, starting replica...'
      postgres
      "
```

### 9.2 备份策略

#### 自动备份脚本

```bash
#!/bin/bash
# backup-sage-db.sh

BACKUP_DIR="/backup/sage-db"
DATE=$(date +%Y%m%d_%H%M%S)
BACKUP_FILE="sage_memory_backup_${DATE}.sql"

# 创建备份目录
mkdir -p $BACKUP_DIR

# 执行备份
docker exec sage-db pg_dump -U sage -d sage_memory > "$BACKUP_DIR/$BACKUP_FILE"

# 压缩备份文件
gzip "$BACKUP_DIR/$BACKUP_FILE"

# 清理7天前的备份
find $BACKUP_DIR -name "*.gz" -mtime +7 -delete

echo "Backup completed: $BACKUP_FILE.gz"
```

#### 定时备份（crontab）

```bash
# 每天凌晨2点执行备份
0 2 * * * /path/to/backup-sage-db.sh >> /var/log/sage-backup.log 2>&1
```

### 9.3 升级策略

#### 蓝绿部署示例

```yaml
# docker-compose-blue-green.yml
services:
  sage-db-blue:
    image: pgvector/pgvector:pg15
    # ... 当前生产配置

  sage-db-green:
    image: pgvector/pgvector:pg16  # 新版本
    # ... 升级后配置
    
  nginx:
    image: nginx:alpine
    # 负载均衡，切换流量
```

### 9.4 监控告警

#### Grafana Dashboard配置

```json
{
  "dashboard": {
    "title": "Sage PostgreSQL Monitoring",
    "panels": [
      {
        "title": "Active Connections",
        "targets": [
          {
            "expr": "pg_stat_database_numbackends{datname=\"sage_memory\"}"
          }
        ]
      },
      {
        "title": "Memory Usage",
        "targets": [
          {
            "expr": "pg_stat_database_tup_inserted{datname=\"sage_memory\"}"
          }
        ]
      }
    ]
  }
}
```

## 10. 附录

### 10.1 完整docker-compose生产环境配置

```yaml
version: '3.8'

services:
  sage-db:
    image: pgvector/pgvector:pg15
    container_name: sage-db-prod
    restart: unless-stopped
    environment:
      POSTGRES_USER: ${DB_USER:-sage}
      POSTGRES_PASSWORD_FILE: /run/secrets/db_password
      POSTGRES_DB: ${DB_NAME:-sage_memory}
    volumes:
      - sage-db-data:/var/lib/postgresql/data
      - ./docker/init.sql:/docker-entrypoint-initdb.d/init.sql
      - ./docker/postgresql.conf:/etc/postgresql/postgresql.conf
    networks:
      - sage-internal
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U ${DB_USER:-sage} -d ${DB_NAME:-sage_memory}"]
      interval: 30s
      timeout: 10s
      retries: 5
      start_period: 60s
    logging:
      driver: "json-file"
      options:
        max-size: "10m"
        max-file: "3"
    deploy:
      resources:
        limits:
          memory: 2G
          cpus: '1.0'
    secrets:
      - db_password

  pgbouncer:
    image: pgbouncer/pgbouncer:latest
    container_name: sage-pgbouncer
    restart: unless-stopped
    environment:
      DATABASES_HOST: sage-db
      DATABASES_PORT: 5432
      DATABASES_USER: ${DB_USER:-sage}
      DATABASES_PASSWORD_FILE: /run/secrets/db_password
      DATABASES_DBNAME: ${DB_NAME:-sage_memory}
      POOL_MODE: transaction
      MAX_CLIENT_CONN: 100
      DEFAULT_POOL_SIZE: 20
    ports:
      - "5432:5432"
    networks:
      - sage-internal
    depends_on:
      sage-db:
        condition: service_healthy
    secrets:
      - db_password

networks:
  sage-internal:
    driver: bridge

volumes:
  sage-db-data:
    driver: local

secrets:
  db_password:
    file: ./secrets/db_password.txt
```

### 10.2 环境变量模板

```bash
# .env.production
DB_USER=sage
DB_NAME=sage_memory
DB_HOST=sage-db
DB_PORT=5432

# 日志配置
LOG_LEVEL=INFO
LOG_DIR=/var/log/sage

# 性能配置
DB_POOL_SIZE=20
DB_MAX_CONNECTIONS=100

# 监控配置
ENABLE_MONITORING=true
METRICS_PORT=9187
```

### 10.3 初始化检查脚本

```bash
#!/bin/bash
# check-sage-db.sh

echo "=== Sage MCP Server 数据库状态检查 ==="

# 检查容器状态
echo "1. 检查容器状态..."
docker ps | grep sage-db

# 检查健康状态
echo "2. 检查健康状态..."
docker inspect sage-db | jq '.[0].State.Health.Status'

# 检查数据库连接
echo "3. 检查数据库连接..."
docker exec sage-db pg_isready -U sage -d sage_memory

# 检查表结构
echo "4. 检查表结构..."
docker exec sage-db psql -U sage -d sage_memory -c "
\dt
SELECT count(*) as total_memories FROM memories;
SELECT count(*) as total_sessions FROM sessions;
"

# 检查pgvector扩展
echo "5. 检查pgvector扩展..."
docker exec sage-db psql -U sage -d sage_memory -c "
SELECT * FROM pg_extension WHERE extname='vector';
"

echo "=== 检查完成 ==="
```

---

## 总结

本指南提供了Sage MCP Server数据库的完整Docker部署方案，涵盖了从开发环境到生产环境的各种场景。关键点包括：

1. **快速启动**: 使用`docker-compose -f docker-compose-db.yml up -d`一键部署
2. **数据持久化**: 通过`sage-db-data`卷确保数据安全
3. **向量支持**: 集成pgvector扩展，支持4096维向量存储
4. **健康监控**: 内置健康检查和日志管理
5. **生产就绪**: 提供高可用、备份、监控等生产环境配置

建议在部署前先在测试环境验证配置，确保所有功能正常运行后再推向生产环境。

---

**文档版本**: v1.0  
**最后更新**: 2025-08-02  
**维护者**: Sage Development Team