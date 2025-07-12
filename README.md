# Sage MCP 轻量化记忆系统

为 Claude CLI 添加企业级持久化记忆功能的轻量级解决方案。

## 🌟 核心特性

### 智能记忆管理
- 🧠 **上下文感知**：自动保存和智能检索历史对话
- 🔍 **语义搜索**：基于向量相似度的高精度检索
- 💾 **持久化存储**：使用 PostgreSQL + pgvector 存储对话和向量
- 🚀 **无感集成**：通过命令别名透明替换原生 claude 命令

### 性能优化（V3版本）
- ⚡ **快速启动**：延迟导入和模块预编译，启动时间 < 500ms
- 🏎️ **高速检索**：LRU缓存 + 批处理优化，检索延迟 < 100ms
- 💪 **资源高效**：智能内存管理，峰值使用 < 200MB
- 🔧 **并发支持**：线程安全设计，支持多进程并发

### 企业级可靠性
- 🛡️ **错误恢复**：智能重试策略，指数退避算法
- 🔌 **断路器保护**：防止级联故障，自动熔断恢复
- 📊 **健康监控**：实时性能指标和健康状态追踪
- 🎯 **优雅降级**：服务异常时自动切换降级方案

## 📋 系统要求

- Python 3.8+
- PostgreSQL 12+ 和 pgvector 扩展
- Docker 和 Docker Compose（可选）
- 至少 512MB 可用内存

## 🚀 快速开始

### 1. 克隆仓库

```bash
git clone https://github.com/yourusername/sage-mcp.git
cd sage-mcp
```

### 2. 创建虚拟环境（推荐）

```bash
python -m venv .venv
source .venv/bin/activate  # Linux/Mac
# 或
.venv\Scripts\activate  # Windows
```

### 3. 安装依赖

```bash
pip install -r requirements.txt
```

### 4. 启动数据库服务

```bash
# 使用 Docker Compose（推荐）
docker-compose up -d

# 或手动安装 PostgreSQL 并启用 pgvector
```

### 5. 配置环境变量

```bash
cp .env.example .env
```

编辑 `.env` 文件，设置必需的配置：

```bash
# API配置（必需）
SILICONFLOW_API_KEY=sk-xxxxxxxxxxxxxxxx  # 从 https://siliconflow.cn 获取

# 数据库配置（可选，使用默认值即可）
DB_HOST=localhost
DB_PORT=5432
DB_NAME=mem
DB_USER=mem
DB_PASSWORD=mem

# 性能配置（可选）
SAGE_CACHE_SIZE=500          # 查询缓存大小
SAGE_CACHE_TTL=300           # 缓存过期时间（秒）
SAGE_MAX_WORKERS=4           # 最大工作线程数
SAGE_BATCH_SIZE=10           # 批处理大小
```

### 6. 初始化数据库

```bash
python setup_database.py
```

### 7. 设置命令别名

在 `~/.bashrc` 或 `~/.zshrc` 中添加：

```bash
alias claude='python /path/to/sage-mcp/claude_mem_v3.py'
```

然后重新加载配置：

```bash
source ~/.bashrc  # 或 source ~/.zshrc
```

## 📖 使用指南

### 基本用法

```bash
# 像平常一样使用 claude
claude "如何实现快速排序？"

# 系统会自动搜索相关历史并增强回答
```

### 高级功能

```bash
# 查看记忆统计
claude --stats

# 禁用记忆功能（仅本次）
claude "查询内容" --no-memory

# 限制记忆上下文长度
claude "查询内容" --max-memory-chars 1000

# 导出记忆数据
python sage_memory_cli.py export my_memories.json

# 搜索历史记忆
python sage_memory_cli.py search "关键词"

# 清理旧记忆
python sage_memory_cli.py cleanup --days 30
```

### 性能监控

```bash
# 查看系统健康状态
python sage_memory_cli.py health

# 运行性能基准测试
python tests/test_performance.py

# 查看实时性能指标
python monitor_dashboard.py  # 在浏览器中打开 http://localhost:8080
```

## 🏗️ 系统架构

### 核心组件

```
sage-mcp/
├── claude_mem_v3.py        # 主入口，命令行拦截器
├── memory_interface.py     # 抽象记忆接口定义
├── memory.py              # 核心记忆实现（V1）
├── intelligent_retrieval.py # 智能检索引擎
├── prompt_enhancer.py      # 提示词增强器
├── performance_optimizer.py # 性能优化模块
├── error_recovery.py       # 错误恢复机制
├── config_adapter.py       # 配置适配器
└── exceptions.py          # 异常定义
```

### 数据流

```
用户输入 → 命令拦截 → 智能检索 → 上下文增强 → Claude API → 响应优化 → 记忆存储
    ↑                                                                    ↓
    └────────────────────── 持久化存储 (PostgreSQL) ←──────────────────┘
```

### 技术栈

- **语言**：Python 3.8+
- **数据库**：PostgreSQL 12+ with pgvector
- **向量模型**：Qwen/Qwen3-Embedding-8B (8192维)
- **缓存**：内存 LRU 缓存 + TTL
- **并发**：asyncio + threading
- **监控**：自定义健康检查 + 性能指标

## 🔧 配置说明

### 环境变量

| 变量名 | 说明 | 默认值 | 必需 |
|-------|------|--------|------|
| SILICONFLOW_API_KEY | SiliconFlow API密钥 | - | ✓ |
| DB_HOST | 数据库主机 | localhost | ✗ |
| DB_PORT | 数据库端口 | 5432 | ✗ |
| DB_NAME | 数据库名称 | sage_memory | ✗ |
| SAGE_DEBUG | 调试模式 | false | ✗ |
| SAGE_CACHE_SIZE | 缓存大小 | 500 | ✗ |
| SAGE_CACHE_TTL | 缓存过期时间 | 300 | ✗ |

### 配置文件

系统支持多层配置：

1. **全局配置**：`~/.sage-mcp/config.json`
2. **项目配置**：`./sage_config.json`
3. **环境变量**：优先级最高

## 🧪 测试

### 运行所有测试

```bash
# 单元测试
pytest tests/

# 集成测试
python tests/test_e2e_integration.py

# 性能测试
python tests/test_performance.py

# 错误恢复测试
python tests/test_error_recovery.py
```

### 性能基准

在 M1 MacBook Pro 上的测试结果：

| 指标 | 目标 | 实际 |
|-----|------|------|
| 启动时间 | < 500ms | ~350ms |
| 检索延迟 | < 100ms | ~65ms |
| 保存延迟 | < 50ms | ~30ms |
| 内存增长 | < 200MB | ~120MB |
| 并发成功率 | > 95% | 98% |

## 🛠️ 故障排除

### 常见问题

1. **API密钥错误**
   ```
   错误：API key not found
   解决：确保 .env 文件中设置了 SILICONFLOW_API_KEY
   ```

2. **数据库连接失败**
   ```
   错误：could not connect to server
   解决：检查 PostgreSQL 是否运行，docker-compose ps
   ```

3. **权限问题**
   ```
   错误：Permission denied
   解决：chmod +x claude_mem_v3.py
   ```

### 调试模式

```bash
# 启用调试输出
export SAGE_DEBUG=1
claude "测试查询"

# 查看详细日志
tail -f ~/.sage-mcp/logs/sage-mcp-*.log
```

## 🤝 贡献指南

欢迎贡献代码！请查看 [CONTRIBUTING.md](CONTRIBUTING.md) 了解详情。

## 📄 许可证

本项目采用 MIT 许可证。查看 [LICENSE](LICENSE) 文件了解详情。

## 🙏 致谢

- Claude (Anthropic) - 强大的 AI 助手
- SiliconFlow - 高质量的模型 API 服务
- pgvector - PostgreSQL 向量扩展
- 所有贡献者和使用者

## 📞 联系方式

- 问题反馈：[GitHub Issues](https://github.com/yourusername/sage-mcp/issues)
- 功能建议：[GitHub Discussions](https://github.com/yourusername/sage-mcp/discussions)