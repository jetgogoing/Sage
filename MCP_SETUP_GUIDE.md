# Sage MCP 完整配置指南

## 🚀 快速开始

### 1. 构建 Docker 镜像

```bash
# 使用修复后的 Dockerfile
docker build -f Dockerfile.ubuntu.fixed -t sage-mcp:ubuntu .

# 或使用一键构建脚本
./build-and-run.sh
```

### 2. 配置 Claude Code

有两种方式配置 MCP 服务：

#### 方式一：使用命令行（推荐）

```bash
# 确保脚本有执行权限
chmod +x run_sage_ubuntu.sh

# 注册到 Claude Code
claude mcp add sage ./run_sage_ubuntu.sh

# 验证注册
claude mcp list
```

#### 方式二：手动配置

1. 打开 Claude Code 设置
2. 找到 MCP Servers 配置
3. 添加以下配置：

```json
{
  "mcpServers": {
    "sage": {
      "command": "bash",
      "args": ["/Users/jet/sage/run_sage_ubuntu.sh"],
      "env": {
        "SILICONFLOW_API_KEY": "your_api_key_here",
        "SAGE_LOG_LEVEL": "INFO"
      }
    }
  }
}
```

### 3. 环境变量设置

创建 `.env` 文件：

```bash
# SiliconFlow API 密钥（必需）
SILICONFLOW_API_KEY=sk-your-api-key-here

# 可选配置
SAGE_LOG_LEVEL=INFO
SAGE_MAX_RESULTS=5
SAGE_ENABLE_RERANK=true
SAGE_ENABLE_SUMMARY=true
SAGE_CACHE_SIZE=500
SAGE_CACHE_TTL=300
```

## 🔧 故障排查

### 1. Docker 构建失败

如果遇到 PostgreSQL 包找不到的错误：

```bash
# 使用修复后的 Dockerfile
docker build -f Dockerfile.ubuntu.fixed -t sage-mcp:ubuntu .
```

### 2. MCP 连接测试

```bash
# 测试 STDIO 通信
echo '{"jsonrpc":"2.0","method":"tools/list","id":1}' | docker run -i sage-mcp:ubuntu

# 期望看到工具列表响应
```

### 3. 查看容器日志

```bash
# 如果使用 docker-compose
docker-compose -f docker-compose.ubuntu.yml logs -f

# 直接运行时
docker logs <container_id>
```

### 4. 验证数据库连接

```bash
# 进入容器
docker run -it sage-mcp:ubuntu /bin/bash

# 在容器内测试
pg_isready -h localhost -p 5432
PGPASSWORD=sage psql -h localhost -U sage -d sage -c "SELECT 1;"
```

## 📋 功能验证

### 1. 测试向量化功能

在 Claude Code 中输入：

```
测试一下记忆功能
```

系统应该能够：
- 自动保存这次对话
- 在后续对话中回忆起这次内容

### 2. 查看系统状态

```
/status
```

或

```
/SAGE-STATUS
```

### 3. 搜索历史记忆

```
/search 测试
```

## 🎯 核心功能说明

### 包含的工具

1. **get_context** - 获取相关上下文
2. **save_conversation** - 保存对话
3. **search_memory** - 搜索记忆
4. **get_memory_stats** - 获取统计信息
5. **analyze_memory** - 分析记忆模式
6. **manage_sessions** - 管理会话

### 自动功能

- ✅ 每次对话自动保存
- ✅ 智能上下文注入
- ✅ 相关记忆自动检索
- ✅ 4096维向量语义搜索

## 🔍 调试技巧

### 1. 启用详细日志

```bash
export SAGE_LOG_LEVEL=DEBUG
./run_sage_ubuntu.sh
```

### 2. 查看 MCP 通信

```bash
# 在容器内查看日志
docker exec -it <container_id> tail -f /var/log/sage/sage-mcp.log
```

### 3. 测试 API 连接

```bash
# 测试 SiliconFlow API
curl https://api.siliconflow.cn/v1/embeddings \
  -H "Authorization: Bearer $SILICONFLOW_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "model": "Qwen/Qwen3-Embedding-8B",
    "input": "test"
  }'
```

## 🎉 完成！

现在您的 Sage MCP 服务应该已经完全配置好了。在 Claude Code 中正常对话，系统会自动：

1. 检索相关历史记忆
2. 注入到当前对话上下文
3. 保存新的对话内容
4. 使用 4096 维向量进行高精度语义搜索

享受拥有永恒记忆的 Claude 体验！