# Sage MCP 部署指南

## 概述

本指南将帮助您在不同环境中部署 Sage MCP 记忆系统。Sage MCP 基于 Model Context Protocol (MCP) 标准，通过 stdio 模式与 Claude Code 通信。

## 系统要求

### 最低配置
- **操作系统**: Linux, macOS, Windows (WSL2)
- **Python**: 3.11 或更高版本
- **内存**: 4GB RAM
- **存储**: 2GB 可用空间
- **数据库**: PostgreSQL 15+ with pgvector 扩展

### 推荐配置
- **操作系统**: Ubuntu 22.04 LTS 或 macOS 13+
- **Python**: 3.11+
- **内存**: 8GB RAM
- **存储**: 10GB SSD
- **数据库**: PostgreSQL 16 with pgvector 0.5+

## 快速部署

### 1. 克隆项目

```bash
git clone https://github.com/yourusername/sage-mcp.git
cd sage-mcp
```

### 2. 设置 Python 环境

```bash
# 创建虚拟环境
python3 -m venv venv

# 激活虚拟环境
# Linux/macOS:
source venv/bin/activate
# Windows:
# venv\Scripts\activate

# 安装依赖
pip install -r requirements.txt
```

### 3. 配置数据库

#### 安装 PostgreSQL 和 pgvector

**Ubuntu/Debian:**
```bash
# 安装 PostgreSQL
sudo apt update
sudo apt install postgresql postgresql-contrib

# 安装 pgvector
sudo apt install postgresql-16-pgvector
```

**macOS (使用 Homebrew):**
```bash
# 安装 PostgreSQL
brew install postgresql@16

# 安装 pgvector
brew install pgvector
```

#### 初始化数据库

```bash
# 创建数据库用户和数据库
sudo -u postgres psql << EOF
CREATE USER sage WITH PASSWORD 'your_secure_password';
CREATE DATABASE sage_memory OWNER sage;
\c sage_memory
CREATE EXTENSION vector;
EOF

# 运行初始化脚本
psql -U sage -d sage_memory -f init.sql
```

### 4. 配置环境变量

创建 `.env` 文件：

```bash
# 必需的环境变量
SILICONFLOW_API_KEY=your_siliconflow_api_key
DATABASE_URL=postgresql://sage:your_secure_password@localhost:5432/sage_memory

# 可选配置
SAGE_DATA_DIR=~/.sage
SAGE_MAX_RESULTS=5
SAGE_DEBUG=false
SAGE_MAX_MEMORY_MB=2048
```

### 5. 启动服务

```bash
# 使用启动脚本
./start_sage_mcp_stdio.sh

# 或直接运行
python app/sage_mcp_server.py
```

## Docker 部署

### 使用预构建镜像

```bash
# 拉取镜像
docker pull yourusername/sage-mcp:latest

# 运行容器
docker run -d \
  --name sage-mcp \
  -e SILICONFLOW_API_KEY=your_api_key \
  -e DATABASE_URL=postgresql://sage:password@db:5432/sage_memory \
  -v ~/.sage:/root/.sage \
  yourusername/sage-mcp:latest
```

### 使用 Docker Compose

创建 `docker-compose.yml`:

```yaml
version: '3.8'

services:
  postgres:
    image: pgvector/pgvector:pg16
    environment:
      POSTGRES_USER: sage
      POSTGRES_PASSWORD: your_secure_password
      POSTGRES_DB: sage_memory
    volumes:
      - postgres_data:/var/lib/postgresql/data
      - ./init.sql:/docker-entrypoint-initdb.d/init.sql
    ports:
      - "5432:5432"

  sage-mcp:
    build: .
    depends_on:
      - postgres
    environment:
      SILICONFLOW_API_KEY: ${SILICONFLOW_API_KEY}
      DATABASE_URL: postgresql://sage:your_secure_password@postgres:5432/sage_memory
    volumes:
      - sage_data:/root/.sage
    ports:
      - "17800:17800"

volumes:
  postgres_data:
  sage_data:
```

启动服务：

```bash
# 设置 API 密钥
export SILICONFLOW_API_KEY=your_api_key

# 启动所有服务
docker-compose up -d

# 查看日志
docker-compose logs -f sage-mcp
```

## Claude Code 集成

### 1. 安装 Claude Code

确保您已经安装了最新版本的 Claude Code。

### 2. 配置 MCP 服务器

在 Claude Code 的 MCP 配置中添加 Sage：

**macOS/Linux:**
`~/.config/claude/claude_mcp_config.json`

**Windows:**
`%APPDATA%\claude\claude_mcp_config.json`

```json
{
  "mcpServers": {
    "sage": {
      "command": "/path/to/sage/start_sage_mcp_stdio.sh",
      "env": {
        "SILICONFLOW_API_KEY": "your_api_key",
        "DATABASE_URL": "postgresql://sage:password@localhost:5432/sage_memory"
      }
    }
  }
}
```

### 3. 重启 Claude Code

重启 Claude Code 以加载新的 MCP 配置。

## 生产环境部署

### 1. 安全配置

#### 使用环境变量管理敏感信息

```bash
# 创建 .env.production
SILICONFLOW_API_KEY=your_production_api_key
DATABASE_URL=postgresql://sage:strong_password@db.example.com:5432/sage_memory
SAGE_SECRET_KEY=your_secret_key
SAGE_ENCRYPTION_KEY=your_encryption_key
```

#### 设置文件权限

```bash
chmod 600 .env.production
chmod 700 ~/.sage
```

### 2. 性能优化

#### PostgreSQL 优化

编辑 `postgresql.conf`:

```conf
# 内存设置
shared_buffers = 256MB
effective_cache_size = 1GB
work_mem = 4MB

# 连接池
max_connections = 100

# 向量索引优化
ivfflat.probes = 10
```

#### 应用级优化

在 `~/.sage/config.json` 中：

```json
{
  "retrieval": {
    "strategy": "HYBRID_ADVANCED",
    "max_results": 5,
    "enable_cache": true
  },
  "embedding": {
    "batch_size": 100,
    "cache_embeddings": true
  },
  "performance": {
    "max_concurrent_operations": 10,
    "connection_pool_size": 20,
    "cache_ttl": 300
  }
}
```

### 3. 监控和日志

#### 启用日志

```bash
# 设置日志级别
export SAGE_LOG_LEVEL=INFO
export SAGE_LOG_FILE=/var/log/sage/sage-mcp.log

# 创建日志目录
sudo mkdir -p /var/log/sage
sudo chown $USER:$USER /var/log/sage
```

#### 使用 systemd 服务

创建 `/etc/systemd/system/sage-mcp.service`:

```ini
[Unit]
Description=Sage MCP Memory System
After=network.target postgresql.service

[Service]
Type=simple
User=sage
Group=sage
WorkingDirectory=/opt/sage-mcp
Environment="PATH=/opt/sage-mcp/venv/bin:/usr/local/bin:/usr/bin:/bin"
EnvironmentFile=/opt/sage-mcp/.env.production
ExecStart=/opt/sage-mcp/venv/bin/python /opt/sage-mcp/app/sage_mcp_server.py
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

启用和启动服务：

```bash
sudo systemctl daemon-reload
sudo systemctl enable sage-mcp
sudo systemctl start sage-mcp
sudo systemctl status sage-mcp
```

### 4. 备份策略

#### 数据库备份

创建备份脚本 `/opt/sage-mcp/scripts/backup.sh`:

```bash
#!/bin/bash
BACKUP_DIR="/var/backups/sage"
DATE=$(date +%Y%m%d_%H%M%S)
DB_NAME="sage_memory"

# 创建备份目录
mkdir -p $BACKUP_DIR

# 备份数据库
pg_dump -U sage -h localhost $DB_NAME | gzip > $BACKUP_DIR/sage_backup_$DATE.sql.gz

# 备份会话文件
tar -czf $BACKUP_DIR/sage_sessions_$DATE.tar.gz ~/.sage/sessions/

# 保留最近30天的备份
find $BACKUP_DIR -name "*.gz" -mtime +30 -delete

echo "Backup completed: $DATE"
```

设置定时任务：

```bash
# 编辑 crontab
crontab -e

# 每天凌晨2点执行备份
0 2 * * * /opt/sage-mcp/scripts/backup.sh >> /var/log/sage/backup.log 2>&1
```

## 故障排除

### 常见问题

#### 1. 数据库连接失败

检查：
- PostgreSQL 服务是否运行
- 数据库用户权限
- 防火墙设置
- DATABASE_URL 格式

```bash
# 测试数据库连接
psql $DATABASE_URL -c "SELECT version();"
```

#### 2. 向量化失败

检查：
- SILICONFLOW_API_KEY 是否有效
- 网络连接
- API 配额

```bash
# 测试 API
curl -X POST https://api.siliconflow.cn/v1/embeddings \
  -H "Authorization: Bearer $SILICONFLOW_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"model": "Qwen/Qwen2.5-7B-Instruct", "input": "test"}'
```

#### 3. 内存不足

优化建议：
- 增加系统内存
- 调整 SAGE_MAX_MEMORY_MB
- 启用缓存淘汰策略
- 定期清理旧数据

### 日志位置

- 应用日志: `/tmp/sage_mcp_v4_final.log`
- 系统日志: `journalctl -u sage-mcp -f`
- 数据库日志: `/var/log/postgresql/`

## 升级指南

### 1. 备份数据

```bash
# 备份数据库
pg_dump -U sage sage_memory > backup_before_upgrade.sql

# 备份配置和会话
tar -czf sage_data_backup.tar.gz ~/.sage/
```

### 2. 更新代码

```bash
git pull origin main
pip install -r requirements.txt --upgrade
```

### 3. 运行迁移

```bash
# 如果有数据库迁移脚本
python scripts/migrate.py
```

### 4. 重启服务

```bash
sudo systemctl restart sage-mcp
```

## 性能调优

### 1. 数据库索引

定期维护索引：

```sql
-- 重建向量索引
REINDEX INDEX idx_conversations_embedding;

-- 分析表统计信息
ANALYZE conversations;

-- 清理死元组
VACUUM ANALYZE conversations;
```

### 2. 缓存策略

启用 Redis 缓存（可选）：

```bash
# 安装 Redis
sudo apt install redis-server

# 配置 Sage 使用 Redis
export SAGE_CACHE_BACKEND=redis
export SAGE_REDIS_URL=redis://localhost:6379/0
```

### 3. 负载均衡

使用多实例部署：

```nginx
upstream sage_mcp {
    server 127.0.0.1:17800;
    server 127.0.0.1:17801;
    server 127.0.0.1:17802;
}

server {
    listen 80;
    server_name sage.example.com;

    location / {
        proxy_pass http://sage_mcp;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
}
```

## 安全建议

1. **API 密钥管理**
   - 使用密钥管理服务
   - 定期轮换密钥
   - 限制密钥权限

2. **网络安全**
   - 使用 HTTPS/TLS
   - 配置防火墙规则
   - 限制数据库访问

3. **数据保护**
   - 启用数据库加密
   - 加密敏感会话数据
   - 实施访问控制

4. **审计日志**
   - 记录所有操作
   - 监控异常行为
   - 定期审查日志

## 支持和资源

- 项目文档: `docs/` 目录
- API 参考: [api-reference.md](api-reference.md)
- 用户指南: [usage-guide.md](usage-guide.md)
- 问题反馈: GitHub Issues
- 社区讨论: GitHub Discussions

## 许可证

本项目遵循 MIT 许可证。详见 LICENSE 文件。