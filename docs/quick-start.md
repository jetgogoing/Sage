# Sage MCP 快速开始指南

本指南将帮助您在5分钟内完成Sage MCP的安装和配置。

## 前置要求

- Docker Desktop 或 Docker Engine
- macOS、Linux 或 Windows (WSL2)
- 至少2GB可用内存

## 安装步骤

### 1. 克隆项目

```bash
git clone https://github.com/yourusername/sage.git
cd sage
```

### 2. 配置API密钥

访问 [SiliconFlow](https://siliconflow.cn) 获取免费API密钥，然后创建`.env`文件：

```bash
cat > .env << EOF
SILICONFLOW_API_KEY=sk-your-api-key-here
DB_HOST=localhost
DB_PORT=5432
DB_NAME=mem
DB_USER=mem
DB_PASSWORD=mem
EOF
```

### 3. 启动服务

```bash
# 使用优化的启动脚本（推荐）
./start_optimized.sh

# 或者使用docker-compose
docker compose -f docker-compose.optimized.yml up -d
```

### 4. 验证服务

```bash
# 检查健康状态
curl http://localhost:17800/health

# 应该看到类似输出：
# {"status":"healthy","timestamp":"2025-07-14T16:45:00","memory_count":0,"database":"connected"}
```

### 5. 配置Claude Code

#### macOS
```bash
mkdir -p ~/Library/Application\ Support/claude-code
cp claude-code-mcp-config.json ~/Library/Application\ Support/claude-code/mcp.json
```

#### Linux
```bash
mkdir -p ~/.config/claude-code
cp claude-code-mcp-config.json ~/.config/claude-code/mcp.json
```

#### Windows
```powershell
mkdir %APPDATA%\claude-code
copy claude-code-mcp-config.json %APPDATA%\claude-code\mcp.json
```

### 6. 重启Claude Code

关闭并重新打开Claude Code，记忆系统会自动开始工作。

## 验证安装

在Claude Code中测试：

1. 问一个技术问题，例如："什么是Docker容器？"
2. 关闭Claude Code
3. 重新打开并问："刚才我们讨论了什么？"
4. Claude应该能记起之前的对话

## 常用命令

```bash
# 查看服务状态
docker compose -f docker-compose.optimized.yml ps

# 查看日志
docker compose -f docker-compose.optimized.yml logs -f

# 停止服务
docker compose -f docker-compose.optimized.yml down

# 查看记忆统计
./sage_manage status

# 搜索记忆
./sage_manage search "Docker"
```

## 故障排查

### 服务无法启动
```bash
# 检查端口占用
lsof -i :17800
lsof -i :5432

# 查看详细日志
docker compose -f docker-compose.optimized.yml logs sage-mcp-server
```

### Claude Code无法连接
1. 确认服务健康：`curl http://localhost:17800/health`
2. 检查配置文件路径是否正确
3. 确认Docker容器正在运行：`docker ps`

### 记忆功能不工作
1. 检查API密钥是否正确
2. 查看容器日志寻找错误
3. 确认数据库连接正常

## 下一步

- 阅读[使用指南](usage-guide.md)了解更多功能
- 查看[API文档](api-reference.md)进行二次开发
- 加入[社区讨论](https://github.com/yourusername/sage/discussions)