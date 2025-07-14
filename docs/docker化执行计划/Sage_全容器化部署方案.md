# Sage 全容器化部署方案文档

> 🗓️ 日期：2025-07-14  
> 🧠 目标：将 Sage MCP 服务与数据库全部打包进 Docker 容器，实现跨平台部署、MCP 稳定注册、无平台差异的生产部署

---

## 🏗️ 架构概览

```text
┌────────────────────┐
│ Claude Code (macOS/Windows/Linux) ─┐
└────────────────────┘              │
                                    ▼
                        ┌─────────────────────────────┐
                        │   Sage MCP Server (Docker)   │◄─── tools_endpoint: /mcp
                        │  • POST /mcp/token            │
                        │  • POST /mcp/auth             │
                        │  • POST /mcp                  │
                        │  • GET /.well-known/mcp...    │
                        └──────────────┬────────────────┘
                                       │
                                       ▼
                        ┌─────────────────────────────┐
                        │ PostgreSQL + pgvector (Docker) │
                        └─────────────────────────────┘
```

---

## 🚀 为何要容器化整个服务？

| 问题 | 容器化解决方式 |
|------|----------------|
| MCP 端口在 macOS 上随机失败 | 映射固定端口，暴露给本机 |
| FastAPI 后台运行不稳定 | 容器中自动重启 |
| Claude Code 无法识别路径 | 容器中结构固定，路径稳定 |
| 多平台部署困难（Windows） | 容器中一键打包跨平台运行 |
| 依赖版本不一致 | Docker 镜像封装所有依赖 |

---

## 📁 项目结构建议

```bash
Sage/
├── app/
│   └── sage_mcp_server.py
├── prompts/
├── db/                    # 向量存储 & 缓存目录
├── requirements.txt
├── Dockerfile             ✅ [由我生成]
├── docker-compose.yml     ✅ [由我生成]
├── .env.example           ✅ [推荐后续添加]
└── ...
```

---

## 🛠️ 构建文件说明

### 🔧 Dockerfile

```dockerfile
FROM python:3.10-slim

WORKDIR /app
COPY . .

RUN pip install --no-cache-dir -r requirements.txt

EXPOSE 17800
CMD ["python3", "app/sage_mcp_server.py"]
```

用于构建 Sage MCP Server 镜像，运行时监听 `17800` 端口。

---

### 🔧 docker-compose.yml

```yaml
version: "3.8"
services:
  sage:
    build: .
    ports:
      - "17800:17800"
    volumes:
      - ./db:/app/db
    depends_on:
      - pg

  pg:
    image: pgvector/pgvector:pg16
    restart: always
    ports:
      - "5432:5432"
    environment:
      POSTGRES_USER: sage
      POSTGRES_PASSWORD: sage
      POSTGRES_DB: sage_memory

volumes:
  pg_data:
```

提供 PostgreSQL 向量数据库服务，并与 MCP 容器共享网络。

---

## 📦 一键部署步骤

### 1️⃣ 准备项目目录（含本文件）

放入生成的：

- `Dockerfile`
- `docker-compose.yml`

### 2️⃣ 构建镜像并启动服务

```bash
docker compose up --build -d
```

成功后，Sage MCP Server 会自动监听 `http://localhost:17800/mcp`

---

## 🔗 与 Claude Code 集成

### 1. 注册 MCP 服务（一次性）

```bash
claude mcp add sage http://localhost:17800/mcp
```

> 成功后可通过 `claude mcp list` 查看注册状态应为 ✔ connected

### 2. 日常使用

```bash
claude                      # 进入对话，自动触发 get_context 注入
sage_manage search "记忆"
sage_manage status
```

无需额外配置或命令，自动记忆功能将全程无感接入。

---

## ✅ 容器部署后效果预期

| 功能 | 预期 |
|------|------|
| MCP 注册 | ✔ 不再 404，动态注册成功 |
| 记忆注入 | ✔ 自动注入触发成功 |
| 多轮对话 | ✔ 自动保存，每轮对话均存入数据库 |
| 多系统兼容 | ✔ Windows / macOS / Linux 一致运行体验 |
| 重启容错 | ✔ docker compose restart 即可恢复所有服务 |

---

## 🧩 后续可选增强

- 添加 `.env.example` 供 API KEY / 模型配置管理  
- 添加 `.dockerignore` 忽略模型缓存文件避免构建臃肿  
- 添加 `Makefile` 简化启动与调试  
- 添加 Web 控制台可视化配置（如 RAG 路径）  

---

完成以上部署后，您的 Sage 系统将具备全平台、全自动、稳定的 Claude Code 记忆系统支持。
