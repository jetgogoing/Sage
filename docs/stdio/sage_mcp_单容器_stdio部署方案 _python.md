# 🧱 Sage MCP 单容器部署方案（仅使用 STDIO + Claude Code）

> 本文档旨在清晰表达用户的部署需求：将 Sage MCP 的核心功能模块与数据库整合进同一个 Docker 容器，并**仅通过 STDIO 与 Claude Code 通讯**，实现真正意义上的最小化、本地化、一致性部署体验。

---

## 🎯 目标

- ✅ 所有核心功能模块（业务逻辑 + 记忆系统）与 PostgreSQL 数据库整合在一个容器内
- ✅ Claude Code 仅通过 STDIO 与该容器通信
- ✅ 无需 HTTP 服务、无端口暴露
- ✅ 可跨平台部署（Windows/macOS/Linux 环境下 Claude Code 均可调用）
- ✅ 启动命令只有一个脚本

---

## 🧠 理想架构图

```
┌─────────────────────────────────────────────────────┐
│                Claude Code 插件（IDE 内）            │
│   ┌─────────────┐                                    │
│   │ MCP 注册     │───── STDIO ─────▶  🧠 sage-mcp 容器     │
│   └─────────────┘                                    │
│                                                     │
└─────────────────────────────────────────────────────┘
                                                │
                                   内部通信（Unix Socket/Localhost）
                                                ▼
                                   ┌────────────────────────────┐
                                   │ PostgreSQL + pgvector 数据库 │
                                   └────────────────────────────┘
```

---

## 📦 构建方案说明

### 核心原则

- 所有服务打进同一个容器：
  - PostgreSQL + 初始化脚本（建库、建表、pgvector）
  - Sage MCP 服务（含 `sage_core/`, `sage_mcp_stdio.py`）
- 容器启动后：
  - 自动启动 PostgreSQL（127.0.0.1）
  - 自动运行 MCP 服务（STDIO 模式，绑定 `stdin/stdout`）

---

## ⚙️ 精简版 Dockerfile（推荐使用 python:3.10-slim）

```Dockerfile
FROM python:3.10-slim

# 安装 PostgreSQL client + server（可用于本地嵌入式 pg）
RUN apt-get update && \
    apt-get install -y postgresql postgresql-contrib postgresql-client curl gnupg && \
    pip install --upgrade pip && \
    apt-get clean

# 安装 pgvector 扩展（通过 SQL 初始化，不编译源码）

# 创建工作目录
WORKDIR /app

# 拷贝核心代码与依赖
COPY ./sage_core /app/sage_core
COPY ./sage_mcp_stdio.py /app/
COPY ./init-db.sql /docker-entrypoint-initdb.d/
COPY requirements-lite.txt ./

# 安装 Python 依赖（无 transformers/torch）
RUN pip install --no-cache-dir -r requirements-lite.txt

# 拷贝入口脚本
COPY ./entrypoint-lite.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

ENTRYPOINT ["/entrypoint.sh"]
```

---

### 🔧 requirements-lite.txt（示例内容）

```
psycopg2-binary
pgvector
sentence-transformers-lite
python-dotenv
loguru
```

> ❗ 无 `transformers` / `torch`，使用轻量 embedding/摘要策略（可定制）

---

### 🚀 entrypoint-lite.sh 示例

```bash
#!/bin/bash

# 启动 PostgreSQL（后台）
service postgresql start
sleep 2

# 初始化数据库（如果首次）
su - postgres -c "psql -c 'CREATE DATABASE sage_memory;'"
su - postgres -c "psql -d sage_memory -c 'CREATE EXTENSION IF NOT EXISTS vector;'"

# 启动 STDIO MCP 服务
exec python /app/sage_mcp_stdio.py --stdio
```

---

### 🧪 启动脚本 run\_sage\_single.sh

```bash
#!/usr/bin/env bash

docker run --rm -i \
  --name sage-mcp-stdio \
  ghcr.io/jetgogoing/sage-mcp-single:lite
```

---

## ✅ 最终部署结果

- 镜像大小控制在 **<1GB**
- 可用于快速开发、调试、本地部署
- Claude Code 与容器无缝 STDIO 通讯
- 无任何 HTTP 或网络端口暴露

---

## 🧪 验证命令

```bash
claude mcp add sage ./run_sage_single.sh
claude mcp list       # 应为 connected
claude /status        # 返回上下文状态
claude /save          # 可成功写入记忆
```

---

## 📌 总结

本方案实现了：

> **“使用 python:3.10-slim 精简镜像，将智能记忆模块与数据库打入同一容器，使用 STDIO 协议与 Claude Code 对接，完全不依赖 HTTP 与远程部署。”**

它大幅优化了：

- 🧩 构建体积与部署速度
- 🔐 本地开发安全性（无端口）
- 🔁 跨平台一致性（Win/macOS/Linux 均可）

如需我输出 `.dockerignore`、`.env` 模板与构建脚本，请继续告诉我。

