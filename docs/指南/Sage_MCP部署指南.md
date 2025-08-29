# Sage MCP Server 部署指南

## 🚀 给Claude Code CLI用户的快速指南

如果你正在使用Claude Code CLI，可以直接让Claude帮你完成部署：

```bash
# 在Claude Code CLI中说：
"请帮我部署Sage MCP Server到本地环境"

# Claude会自动执行：
1. 检查环境（Docker、Python）
2. 配置.env文件
3. 启动服务
4. 更新Claude配置文件
```

## 1. 概述

本指南旨在指导开发者在本地环境中成功部署、配置并运行 Sage MCP（Memory-Conversation-Persistence）服务器。该服务器通过 MCP 协议与 Claude 桌面应用集成，为 AI 对话提供长期记忆和上下文管理能力。

部署流程主要包括：环境准备、配置、启动服务、以及与 Claude 应用的集成。

**技术栈概览：**
- **后端服务**: Python (基于 `mcp-sdk`)
- **数据库**: PostgreSQL + pgvector (通过 Docker 运行)
- **运行环境**: Python 虚拟环境  
- **客户端**: Claude 桌面应用

## 2. 系统环境要求

### 最简要求清单

✅ **必装软件**：
- Python 3.9+（检查：`python --version`）
- Docker Desktop（检查：`docker --version`）
- Claude 桌面应用

✅ **Windows额外要求**：
- WSL2（检查：`wsl --list`）
- 在Docker Desktop设置中启用WSL2

### 详细要求

在开始部署前，请确保你的系统已安装以下软件：

- **Python**: 3.9 或更高版本
- **Docker Desktop**: 用于运行数据库容器
- **Git**: 用于获取项目代码
- **Claude 桌面应用**: 用于与 MCP 服务交互

## 3. 部署步骤

### 🎯 最快部署路径（推荐）

如果你想最快速地部署，跳过所有细节：

```bash
# 1. 进入项目目录
cd Sage

# 2. 复制配置文件
cp .env.example .env

# 3. 编辑.env - 只改这两行：
# DB_PASSWORD=设置一个密码
# SILICONFLOW_API_KEY=你的API密钥

# 4. 启动！
python start_sage.py
```

完成！现在配置Claude（跳到步骤7）。

### 步骤 1: 获取项目代码

克隆项目仓库到你的本地工作区。

```bash
# 替换为你的项目仓库地址
git clone <your-sage-mcp-project-repository-url>
cd <project-directory> # 例如 cd Sage
```

### 步骤 2: 创建并激活 Python 虚拟环境

为项目创建一个独立的 Python 虚拟环境，以隔离依赖。

```bash
# 在项目根目录下执行
python3 -m venv .venv

# 激活虚拟环境
# macOS / Linux
source .venv/bin/activate

# Windows (Git Bash)
source .venv/Scripts/activate

# Windows (Command Prompt)
.venv\Scripts\activate.bat
```

**注意**: `start_sage_mcp.sh` 脚本会自动检测并使用项目内的 `.venv` 虚拟环境。配置系统通过 `config/settings.py` 智能处理路径，无需手动设置 `SAGE_HOME`。

### 步骤 3: 安装依赖

激活虚拟环境后，使用 `requirements.txt` 文件安装所有必需的 Python 包。

```bash
pip install -r requirements.txt
```

这会安装 `mcp`, `asyncpg`, `python-dotenv` 等核心依赖。

### 步骤 4: 配置环境变量

项目采用集中化的配置管理系统，通过 `.env` 文件和 `config/settings.py` 模块统一管理所有配置。系统会自动检测项目路径，支持跨平台部署。

#### 4.1 配置系统架构

```
Sage/
├── config/
│   ├── __init__.py      # 配置导出
│   └── settings.py      # 配置中心（智能路径检测）
├── .env.example         # 配置模板
├── .env                 # 用户配置（git忽略）
└── start_sage_mcp.sh    # 支持环境变量覆盖
```

#### 4.2 创建配置文件

```bash
# 复制模板文件
cp .env.example .env

# 编辑配置文件
nano .env  # 或使用您喜欢的编辑器
```

#### 4.3 核心配置项

```dotenv
# ===== 路径配置（跨平台支持）=====
# 留空则自动检测，支持手动指定
SAGE_HOME=                          # Windows: C:\Projects\Sage
                                   # macOS: /Users/yourname/Sage
                                   # Linux: /home/yourname/Sage

# ===== 必需配置项 =====
DB_PASSWORD=your_secure_password_here      # 数据库密码（必须修改）
SILICONFLOW_API_KEY=your_api_key_here      # API密钥

# ===== 端口配置（支持自定义）=====
DB_PORT=5432                       # PostgreSQL端口
MCP_PORT=17800                     # MCP服务端口
WEB_PORT=3000                      # Web服务端口

# ===== 记忆检索配置 =====
SAGE_MAX_RESULTS=100               # 检索记忆条数
SAGE_SIMILARITY_THRESHOLD=0.3      # 相似度阈值
```

#### 4.4 配置优先级

系统支持多层配置覆盖，优先级从高到低：
1. **环境变量**：`export DB_PORT=5433`
2. **.env文件**：`DB_PORT=5432`
3. **默认值**：`config/settings.py` 中定义

#### 4.5 跨平台特性

- **智能路径检测**：自动识别项目根目录
- **路径分隔符处理**：使用 `pathlib` 自动适配
- **环境隔离**：每个开发者可以有独立的 `.env` 配置

**关于启动脚本**

`start_sage_mcp.sh` 脚本已经优化，会自动：
- 检测并使用项目内的虚拟环境
- 从 `.env` 文件加载配置
- 智能处理跨平台路径差异

**脚本核心功能:**

```bash
#!/bin/bash
# Sage MCP Startup Script - Enhanced for Security and Portability

# 项目根目录 (自动检测)
SAGE_HOME="$( cd "$( dirname "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )"
DB_COMPOSE_FILE="${SAGE_HOME}/docker-compose-db.yml"
SAGE_LOGS="${SAGE_HOME}/logs"
VENV_PATH="${SAGE_HOME}/.venv/bin/python" # 使用项目内的虚拟环境

# 创建日志目录
mkdir -p "${SAGE_LOGS}"

# --- 数据库启动逻辑 (保持不变) ---
if ! docker info > /dev/null 2>&1; then
    echo "Docker is not running. Please start Docker Desktop first." >&2
    exit 1
fi
if ! docker ps -a | grep -q "sage-db"; then
    echo "Creating PostgreSQL container with pgvector..." >&2
    cd "${SAGE_HOME}" && docker-compose -f "${DB_COMPOSE_FILE}" up -d
    sleep 5
elif ! docker ps | grep -q "sage-db.*Up"; then
    echo "Starting existing PostgreSQL container..." >&2
    docker start sage-db
    sleep 3
fi
echo "Checking PostgreSQL readiness..." >&2
for i in {1..30}; do
    if docker exec sage-db pg_isready -U sage -d sage_memory 2>/dev/null; then
        echo "PostgreSQL is ready!" >&2
        break
    fi
    if [ $i -eq 30 ]; then
        echo "PostgreSQL failed to start within 30 seconds" >&2
        exit 1
    fi
    sleep 1
done
# --- 数据库启动逻辑结束 ---

# -- 安全地加载环境变量 --
export SAGE_LOG_DIR="${SAGE_LOGS}"
export PYTHONPATH="${SAGE_HOME}"

# 从 .env 文件加载配置
if [ -f "${SAGE_HOME}/.env" ]; then
  set -a # 自动导出后续变量
  source "${SAGE_HOME}/.env"
  set +a
else
  echo "Error: .env file not found!" >&2
  exit 1
fi

# 检查关键变量是否已加载
if [ -z "$DB_PASSWORD" ] || [ -z "$SILICONFLOW_API_KEY" ]; then
    echo "Error: DB_PASSWORD or SILICONFLOW_API_KEY is not set in .env file." >&2
    exit 1
fi

# 启动 Sage MCP 服务器
echo "Starting Sage MCP Server..." >&2
exec "${VENV_PATH}" "${SAGE_HOME}/sage_mcp_stdio_single.py"
```

### 步骤 5: 理解配置文件体系

Sage MCP 使用两个配置文件：

#### 5.1 项目级配置 (.mcp.json)

位于项目根目录，定义MCP服务器的基本信息：

```json
{
  "mcpServers": {
    "sage": {
      "type": "stdio",
      "command": "/path/to/your/project/start_sage_mcp.sh",
      "args": [],
      "env": {}
    }
  }
}
```

**重要**: 确保 `command` 路径使用绝对路径，指向实际的启动脚本。

#### 5.2 Claude客户端配置 (claude_desktop_config.json)

这是Claude桌面应用的配置文件，需要手动配置（详见步骤7）。

### 步骤 6: 启动 Sage MCP 服务器

现在，你可以选择以下方式启动服务器：

#### 方式1：使用跨平台Python启动器（推荐）

最简单且跨平台的方式，适用于Windows/macOS/Linux：

```bash
python start_sage.py
```

该启动器会自动：
1. 检查并启动 Docker 数据库容器
2. 加载 `.env` 文件中的配置
3. 处理跨平台路径差异
4. 启动 MCP 服务器

#### 方式2：使用传统Shell脚本（仅Linux/macOS）

```bash
bash start_sage_mcp.sh
```

#### 方式3：Windows批处理脚本

```cmd
start_sage_mcp.bat
```

服务器启动后，它将等待来自 Claude 桌面应用的连接，此时终端不会有太多输出。

### 步骤 7: 配置 Claude 桌面应用

要让 Claude 应用能够与你的 Sage MCP 服务器通信，需要配置其 MCP 服务器列表。

#### 7.1 找到配置文件

- **macOS**: `~/Library/Application Support/Claude/claude_desktop_config.json`
- **Windows**: `%APPDATA%\Claude\claude_desktop_config.json` (通常是 `C:\Users\<YourUser>\AppData\Roaming\Claude\claude_desktop_config.json`)

#### 7.2 编辑配置文件

打开 `claude_desktop_config.json` 文件，在 `mcpServers` 对象中添加或更新 `sage` 的配置。确保 `command` 和 `args` 指向你本地的 `start_sage_mcp.sh` 脚本。

**重要**: 路径必须是**绝对路径**。

```json
{
  "mcpServers": {
    "sage": {
      "command": "python",
      "args": ["/path/to/your/project/start_sage.py"],
      "startupTimeout": 30000
    }
  }
}
```

**路径说明**:
- 将 `/path/to/your/project/start_sage.py` 替换为你本地项目中 `start_sage.py` 的**绝对路径**
- `"command": "python"` 确保使用系统Python解释器（跨平台兼容）
- `startupTimeout` (单位：毫秒) 建议设置为 30000 (30秒)，因为启动脚本需要等待数据库

**其他配置方式**（根据操作系统选择）:

对于传统Shell脚本（Linux/macOS）：
```json
{
  "mcpServers": {
    "sage": {
      "command": "/bin/bash",
      "args": ["/path/to/your/project/start_sage_mcp.sh"],
      "startupTimeout": 30000
    }
  }
}
```

对于Windows批处理：
```json
{
  "mcpServers": {
    "sage": {
      "command": "cmd.exe",
      "args": ["/c", "C:\\path\\to\\your\\project\\start_sage_mcp.bat"],
      "startupTimeout": 30000
    }
  }
}
```

#### 7.3 重启 Claude 应用

保存配置文件后，完全退出并重新启动 Claude 桌面应用以使更改生效。

## 4. 验证部署

完成以上步骤后，通过以下方式验证部署是否成功：

### 4.1 检查服务器日志

查看项目 `logs/sage_mcp_stdio.log` 文件。你应该能看到类似以下的日志信息，表明服务器已初始化。

```
INFO - __main__ - Sage MCP stdio server v3 initialized
INFO - __main__ - Starting Sage MCP stdio server v3...
INFO - __main__ - Sage core initialized successfully
```

### 4.2 在 Claude 中调用工具

在 Claude 桌面应用的任意对话框中，输入以下命令来调用 `get_status` 工具：

```
@sage get_status
```

如果一切正常，Sage MCP 服务器将返回其当前状态的 JSON 信息，例如：

```json
{
  "status": "ok",
  "version": "3.0.0",
  "database": {
    "status": "connected",
    "current_session": "some-session-uuid",
    "total_memories": 123
  },
  "embedding_service": {
    "status": "ready",
    "model": "Qwen/Qwen3-Embedding-8B"
  }
}
```

看到此输出，即表示 Sage MCP 服务器已成功部署并与 Claude 集成。

### 4.3 测试其他功能

你还可以测试其他工具：

1. **保存对话**：
   ```
   @sage S user_prompt="测试消息" assistant_response="测试回复"
   ```

2. **获取上下文**：
   ```
   @sage get_context query="测试" max_results=5
   ```

3. **管理会话**：
   ```
   @sage manage_session action="list"
   ```

4. **断路器重置**（故障恢复后使用）：
   ```
   @sage reset_circuit_breaker all=true
   ```

## 4.4 断路器手动重置功能

Sage MCP Server 内置了断路器保护机制，在数据库连接或API调用持续失败时会自动"断路"以保护系统。当您手动修复故障后，可以使用以下命令立即恢复服务：

### 重置所有断路器
```
@sage reset_circuit_breaker all=true
```

### 重置指定断路器
```
@sage reset_circuit_breaker all=false breaker_name="database_connection"
```

### 常见断路器名称
- `database_connection` - 数据库连接
- `database_execute` - 数据库执行
- `memory_save` - 记忆保存
- `vectorizer` - 向量化服务

### 使用场景
1. **数据库修复后**：重启PostgreSQL服务后立即重置
2. **API密钥更新后**：更新SILICONFLOW_API_KEY后重置相关服务
3. **网络问题解决后**：网络连接恢复后重置所有服务

操作会自动记录到 `logs/circuit_breaker_reset.log` 文件中。

## 5. 故障排查

### 5.1 日志与故障排查

- **服务器日志**: 位于项目根目录下的 `logs/sage_mcp_stdio.log`。当 `@sage` 命令无响应或出错时，请首先检查此文件
- **Claude 日志**: 可以在 Claude 应用的开发者工具 (通常通过 `Cmd/Ctrl+Option+I` 打开) 的 Console 中查看与 MCP 相关的通信日志
- **数据库问题**: 如果启动脚本卡在 "Checking PostgreSQL readiness..."，请使用 `docker logs sage-db` 查看数据库容器的日志

### 5.2 常见问题

#### 问题1: 虚拟环境路径错误

**症状**: 脚本报错找不到 Python 解释器

**解决方案**: 
- 确保已创建 `.venv` 虚拟环境
- 检查 `start_sage_mcp.sh` 中的 `VENV_PATH` 是否正确

#### 问题2: .env 文件未找到

**症状**: "Error: .env file not found!"

**解决方案**: 
- 确保在项目根目录创建了 `.env` 文件
- 检查文件名是否正确（不是 `.env.txt`）

#### 问题3: API 密钥无效

**症状**: embedding 服务或智能提示功能异常

**解决方案**: 
- 检查 `.env` 文件中的 `SILICONFLOW_API_KEY` 是否有效
- 确认 API 密钥有足够的配额

#### 问题4: Claude 无法连接到 Sage MCP

**症状**: `@sage` 命令无响应

**解决方案**: 
1. 检查 `claude_desktop_config.json` 中的路径是否正确
2. 确认使用的是绝对路径
3. 重启 Claude 应用
4. 检查 `start_sage_mcp.sh` 脚本是否有执行权限：`chmod +x start_sage_mcp.sh`

#### 问题5: 数据库连接失败

**症状**: 服务器启动时数据库连接错误

**解决方案**:
1. 确保 Docker Desktop 正在运行
2. 检查数据库容器状态：`docker ps -a | grep sage-db`
3. 重启数据库容器：`docker restart sage-db`
4. 查看数据库日志：`docker logs sage-db`
5. **数据库修复后立即重置断路器**：`@sage reset_circuit_breaker all=true`

#### 问题6: 断路器持续阻塞请求

**症状**: 修复故障后，系统仍然报告"断路器已打开"错误

**解决方案**:
1. 确认底层问题已真正解决（数据库可访问、API密钥有效等）
2. 使用断路器重置命令：`@sage reset_circuit_breaker all=true`
3. 检查断路器重置日志：`tail -f logs/circuit_breaker_reset.log`
4. 如果问题仍然存在，重启整个MCP服务器

#### 问题7: API调用失败

**症状**: 向量化或AI压缩功能报错

**解决方案**:
1. 检查 `.env` 文件中的 `SILICONFLOW_API_KEY` 是否正确
2. 验证API密钥是否有足够配额
3. 测试网络连接：`curl -H "Authorization: Bearer $SILICONFLOW_API_KEY" https://api.siliconflow.cn/v1/models`
4. **API修复后重置相关断路器**：`@sage reset_circuit_breaker breaker_name="vectorizer"`

## 6. 安全注意事项

### 6.1 环境变量安全

- **不要**将 `.env` 文件提交到版本控制系统
- 在 `.gitignore` 中添加 `.env` 条目
- 定期轮换 API 密钥
- 使用强密码作为数据库密码

### 6.2 生产环境部署

如果需要在生产环境部署，请考虑：

- 使用更安全的密钥管理方案（如 HashiCorp Vault）
- 配置防火墙规则限制数据库访问
- 启用数据库连接加密
- 定期备份数据库数据
- 监控服务器性能和日志

---

**注意**: 本指南专注于 Sage MCP Server 的部署。关于数据库的详细 Docker 部署配置，请参考单独的"数据库 Docker 部署指南"。