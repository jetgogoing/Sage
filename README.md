# Sage MCP 轻量化记忆系统

为 Claude CLI 添加持久化记忆功能的轻量级解决方案。

## 功能特性

- 🧠 **智能记忆**：自动保存和检索历史对话
- 🔍 **语义搜索**：基于向量相似度的智能检索
- 💾 **本地存储**：使用 PostgreSQL + pgvector 存储对话和向量
- 🚀 **无感注入**：通过命令别名透明替换原生 claude 命令

## 快速开始

### 1. 安装依赖

```bash
# 安装 Python 依赖
pip install -r requirements.txt

# 启动数据库服务
docker-compose up -d
```

### 2. 配置环境变量

复制 `.env` 文件并根据需要修改配置：
- `SILICONFLOW_API_KEY`：用于调用 AI 模型
- 数据库连接参数（默认配置通常无需修改）

### 3. 设置命令别名

在 `~/.bashrc` 或 `~/.zshrc` 中添加：

```bash
alias claude='python /path/to/Sage/claude_mem.py'
```

### 4. 使用

像平常一样使用 claude 命令：

```bash
claude "如何实现快速排序？"
```

系统会自动：
- 搜索相关历史对话
- 注入上下文到查询中
- 保存对话供未来参考

## 架构说明

- **claude_mem.py**：命令行注入器，拦截并增强 claude 命令
- **memory.py**：核心记忆模块，处理向量化、存储和检索
- **PostgreSQL + pgvector**：存储对话历史和 4096 维向量

## 使用的 AI 模型

- **嵌入模型**：Qwen/Qwen3-Embedding-8B（生成向量）
- **对话模型**：deepseek-ai/DeepSeek-V2.5（生成摘要）

所有模型通过 SiliconFlow API 调用。