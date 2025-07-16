# Sage MCP 完整部署步骤

## 自动部署（推荐）

```bash
# 1. 添加执行权限
chmod +x complete-deployment.sh run_sage_ubuntu.sh

# 2. 运行部署脚本
./complete-deployment.sh
```

这个脚本会自动：
- ✅ 检查 Docker 环境
- ✅ 创建/检查 .env 文件
- ✅ 构建 Docker 镜像
- ✅ 测试容器启动
- ✅ 验证各项服务
- ✅ 提供下一步指导

## 手动部署步骤

### 1. 准备环境

```bash
# 创建 .env 文件
cat > .env << EOF
SILICONFLOW_API_KEY=your_actual_api_key_here
SAGE_LOG_LEVEL=INFO
EOF
```

### 2. 构建镜像

```bash
docker build -f Dockerfile.ubuntu.fixed -t sage-mcp:ubuntu .
```

### 3. 测试运行

```bash
# 基本测试
docker run --rm sage-mcp:ubuntu echo "OK"

# 完整测试
docker run -it --rm \
    -e SILICONFLOW_API_KEY="${SILICONFLOW_API_KEY}" \
    sage-mcp:ubuntu
```

### 4. 调试（如果需要）

```bash
# 进入容器调试
docker run -it --rm \
    -e SILICONFLOW_API_KEY="${SILICONFLOW_API_KEY}" \
    sage-mcp:ubuntu bash

# 在容器内：
# 检查 PostgreSQL
pg_isready -h localhost -p 5432

# 查看日志
cat /var/log/sage/postgresql.log

# 测试数据库连接
PGPASSWORD=sage psql -h localhost -U sage -d sage -c "SELECT 1;"

# 测试 Python
python3 -c "import sage_core; print('OK')"
```

### 5. 注册到 Claude Code

```bash
# 确保脚本可执行
chmod +x run_sage_ubuntu.sh

# 注册
claude mcp add sage ./run_sage_ubuntu.sh

# 验证
claude mcp list
```

## 常见问题解决

### PostgreSQL 启动失败
- 问题：`could not access the server configuration file`
- 解决：数据目录未初始化，entrypoint.sh 已包含自动初始化

### Python 模块导入失败
- 问题：`ModuleNotFoundError: No module named 'sage_core'`
- 解决：检查 PYTHONPATH，确保设置为 `/app`

### STDIO 通信失败
- 测试命令：
  ```bash
  echo '{"jsonrpc":"2.0","method":"tools/list","id":1}' | \
  docker run -i --rm -e SILICONFLOW_API_KEY="${SILICONFLOW_API_KEY}" sage-mcp:ubuntu
  ```

### API 密钥问题
- 确保 .env 文件中设置了正确的 SILICONFLOW_API_KEY
- 系统会降级到哈希向量化，但功能受限

## 验证部署成功

1. **Docker 镜像构建成功**
   ```bash
   docker images | grep sage-mcp
   ```

2. **容器能正常启动**
   ```bash
   docker run --rm sage-mcp:ubuntu echo "OK"
   ```

3. **MCP 工具列表可用**
   ```bash
   echo '{"jsonrpc":"2.0","method":"tools/list","id":1}' | \
   docker run -i --rm -e SILICONFLOW_API_KEY="${SILICONFLOW_API_KEY}" sage-mcp:ubuntu | \
   grep -E "get_context|save_conversation"
   ```

4. **Claude Code 显示已连接**
   ```bash
   claude mcp list
   # 应该看到 sage: connected
   ```

## 部署完成后

在 Claude Code 中正常对话，系统会自动：
- 🔍 检索相关历史记忆
- 💡 注入上下文到当前对话
- 💾 保存新的对话内容
- 🚀 使用 4096 维向量进行语义搜索

享受拥有永恒记忆的 Claude！