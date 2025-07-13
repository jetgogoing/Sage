# Sage Docker 部署版架构设计方案（MCP Server）

> 🧠 目标：打造一个跨平台、即开即用、支持 Claude Code 的个人记忆系统（Sage），支持模型与供应商自由配置，并通过 MCP 协议实现“无感记忆”。

---

## 🎯 项目愿景

- ✅ 跨平台（macOS / Windows / Linux）统一部署体验
- ✅ Claude Code 无缝集成，支持自动记忆保存与上下文注入
- ✅ 支持主流中文向量模型 / 摘要模型 / 重排序模型（可配置）
- ✅ 用户通过 `.env` 文件简单配置 API KEY 和模型选择
- ✅ 不使用 alias、不依赖路径，不嵌套启动脚本

---

## 🧱 架构概览

```
╭───────────────╮
│ Claude Code   │
│ (MCP Client)  │
╰────┬──────────╯
     │ MCP 调用（HTTP）
╭────▼────────────────────────╮
│ Sage MCP Server (FastAPI)   │
│ ├─ POST /get_context        │
│ ├─ POST /save_conversation  │
│ ├─ POST /search_memory      │
│ └─ 使用向量数据库 + 摘要模型 │
╰────┬────────────────────────╯
     │
╭────▼────────────────────────────────────╮
│ PostgreSQL + pgvector                   │
│ ├─ conversations 表（带 4096维 embedding） │
╰─────────────────────────────────────────╯
```

---

## ⚙️ 模块组成

### 1. Sage MCP Server（容器中主服务）

- 实现 MCP 标准接口：
  - `POST /get_context`
  - `POST /save_conversation`
  - `POST /search_memory`
- 使用 FastAPI + Uvicorn 监听端口（默认 17800）
- 读取 `.env` 配置动态选择嵌入模型 / 摘要模型
- 支持异步嵌入、摘要压缩、缓存策略

### 2. PostgreSQL + pgvector（向量数据库）

- 存储所有对话（user + assistant）
- 支持余弦距离检索
- 初始化 SQL 自动创建表 + 索引

### 3. 配置文件（.env）

```dotenv
# API Provider
SILICONFLOW_API_KEY=sk-xxx

# Embedding Model
EMBEDDING_MODEL=Qwen/Qwen3-Embedding-8B

# Reranker Model（可选）
RERANKER_MODEL=Qwen/Qwen3-Reranker-8B

# Summarization Model（可选）
SUMMARY_MODEL=deepseek-ai/DeepSeek-V2.5
```

---

## 🐳 Docker 部署说明

### 项目结构：

```
Sage/
├─ docker-compose.yml
├─ Dockerfile
├─ .env.example
├─ app/
│  ├─ sage_mcp_server.py
│  ├─ memory.py
│  ├─ config_loader.py
│  └─ ...
```

### 一键部署：

```bash
git clone https://github.com/jetgogoing/Sage.git
cd Sage
cp .env.example .env      # 配置模型与 API_KEY
docker compose up -d      # 启动 MCP Server + Postgres
```

---

## 🧩 Claude Code 集成

### 一次性注册 MCP 服务：

```bash
claude mcp add sage http://localhost:17800
```

之后 Claude Code 会自动调用 Sage 的上下文注入与保存功能，无需任何额外操作。

---

## 💡 扩展性与维护建议

- 日志记录：可挂载 `/logs` 并集成 Prometheus / Loki 等
- Web UI 配置（可选）：未来可引入前端界面修改 `.env` 并动态 reload
- 支持 SQLite Lite 模式（低功耗场景）
- 支持 token 预算策略 + 自动摘要截断

---

## ✅ 结论

该方案将 Sage 架构完整重构为：

- 开箱即用（Docker 一键部署）
- 跨平台稳定（Win/macOS/Linux 通用）
- 可配置、可观测、可升级
- 与 Claude Code 完整对接（MCP 标准协议）

是适合长期维护与对外交付的**标准化智能记忆系统架构**。
